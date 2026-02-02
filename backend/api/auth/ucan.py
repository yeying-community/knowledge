# -*- coding: utf-8 -*-

from __future__ import annotations

import base64
import json
from typing import Any, Dict, List, Optional, Tuple

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from eth_account import Account
from eth_account.messages import encode_defunct

from .envelope import now_ms
from .normalize import normalize_wallet_id


BASE58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def base64url_decode(value: str) -> bytes:
    padding = "=" * ((4 - len(value) % 4) % 4)
    return base64.urlsafe_b64decode(value + padding)


def base58_decode(value: str) -> bytes:
    num = 0
    for char in value:
        num *= 58
        index = BASE58_ALPHABET.find(char)
        if index == -1:
            raise ValueError("invalid base58 character")
        num += index
    combined = num.to_bytes((num.bit_length() + 7) // 8, "big") if num else b""
    n_pad = len(value) - len(value.lstrip("1"))
    return b"\x00" * n_pad + combined


def did_key_to_public_key(did: str) -> bytes:
    if not did or not did.startswith("did:key:z"):
        raise ValueError("invalid did:key format")
    decoded = base58_decode(did[len("did:key:z") :])
    # multicodec prefix for Ed25519 public key is 0xED 0x01
    if len(decoded) < 2 or decoded[0] != 0xED or decoded[1] != 0x01:
        raise ValueError("unsupported did:key type")
    return decoded[2:]


def normalize_epoch_ms(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        value = int(value)
    except (TypeError, ValueError):
        return None
    # seconds → ms
    return value * 1000 if value < 1_000_000_000_000 else value


def match_pattern(pattern: str, value: str) -> bool:
    if pattern == "*":
        return True
    if pattern.endswith("*"):
        return value.startswith(pattern[:-1])
    return pattern == value


def caps_allow(available: Any, required: List[Dict[str, str]]) -> bool:
    if not isinstance(available, list) or not available:
        return False
    for req in required:
        matched = False
        for cap in available:
            if not isinstance(cap, dict):
                continue
            if match_pattern(str(cap.get("resource", "")), str(req.get("resource", ""))) and match_pattern(
                str(cap.get("action", "")), str(req.get("action", ""))
            ):
                matched = True
                break
        if not matched:
            return False
    return True


def extract_ucan_statement(message: str) -> Optional[dict]:
    for line in (message or "").splitlines():
        trimmed = line.strip()
        if trimmed.upper().startswith("UCAN-AUTH"):
            payload = trimmed[len("UCAN-AUTH") :].lstrip(" :")
            try:
                return json.loads(payload)
            except Exception:
                return None
    return None


def verify_root_proof(root: dict) -> dict:
    if not isinstance(root, dict) or root.get("type") != "siwe":
        raise ValueError("invalid root proof")
    siwe = root.get("siwe") or {}
    message = siwe.get("message")
    signature = siwe.get("signature")
    if not message or not signature:
        raise ValueError("missing SIWE message")

    recovered = Account.recover_message(encode_defunct(text=message), signature=signature)
    iss = f"did:pkh:eth:{normalize_wallet_id(recovered)}"
    if root.get("iss") and root.get("iss") != iss:
        raise ValueError("root issuer mismatch")

    statement = extract_ucan_statement(message)
    if not statement:
        raise ValueError("missing UCAN statement")

    aud = statement.get("aud") or root.get("aud")
    cap = statement.get("cap") or root.get("cap")
    exp = normalize_epoch_ms(statement.get("exp") or root.get("exp"))
    nbf = normalize_epoch_ms(statement.get("nbf") or root.get("nbf"))

    if not aud or not isinstance(cap, list) or not exp:
        raise ValueError("invalid root claims")

    if root.get("aud") and root.get("aud") != aud:
        raise ValueError("root audience mismatch")
    if root.get("exp") and normalize_epoch_ms(root.get("exp")) != exp:
        raise ValueError("root expiry mismatch")

    now = now_ms()
    if nbf and now < nbf:
        raise ValueError("root not active")
    if now > exp:
        raise ValueError("root expired")

    return {"iss": iss, "aud": aud, "cap": cap, "exp": exp, "nbf": nbf}


def decode_ucan_token(token: str) -> Tuple[dict, dict, bytes, bytes]:
    parts = (token or "").split(".")
    if len(parts) != 3:
        raise ValueError("invalid UCAN token")
    header = json.loads(base64url_decode(parts[0]))
    payload = json.loads(base64url_decode(parts[1]))
    signature = base64url_decode(parts[2])
    signing_input = f"{parts[0]}.{parts[1]}".encode("utf-8")
    return header, payload, signature, signing_input


def is_ucan_token(token: str) -> bool:
    try:
        header, _, _, _ = decode_ucan_token(token)
        return header.get("typ") == "UCAN" or header.get("alg") == "EdDSA"
    except Exception:
        return False


def verify_ucan_jws(token: str) -> Tuple[dict, Optional[int]]:
    header, payload, signature, signing_input = decode_ucan_token(token)
    if header.get("alg") != "EdDSA":
        raise ValueError("unsupported UCAN alg")
    raw_key = did_key_to_public_key(payload.get("iss", ""))
    try:
        Ed25519PublicKey.from_public_bytes(raw_key).verify(signature, signing_input)
    except InvalidSignature as exc:
        raise ValueError("invalid UCAN signature") from exc

    exp = normalize_epoch_ms(payload.get("exp"))
    nbf = normalize_epoch_ms(payload.get("nbf"))
    now = now_ms()
    if nbf and now < nbf:
        raise ValueError("UCAN not active")
    if exp and now > exp:
        raise ValueError("UCAN expired")
    return payload, exp


def verify_proof_chain(current_did: str, required_caps: List[Dict[str, str]], required_exp: Optional[int], proofs: Any) -> dict:
    if not isinstance(proofs, list) or not proofs:
        raise ValueError("missing UCAN proof chain")

    first = proofs[0]
    if isinstance(first, str):
        payload, exp = verify_ucan_jws(first)
        if payload.get("aud") != current_did:
            raise ValueError("UCAN audience mismatch")
        if not caps_allow(payload.get("cap") or [], required_caps):
            raise ValueError("UCAN capability denied")
        if exp and required_exp and exp < required_exp:
            raise ValueError("UCAN proof expired")
        next_proofs = payload.get("prf") or proofs[1:]
        return verify_proof_chain(payload.get("iss"), payload.get("cap") or [], exp, next_proofs)

    root = verify_root_proof(first)
    if root["aud"] != current_did:
        raise ValueError("root audience mismatch")
    if not caps_allow(root["cap"], required_caps):
        raise ValueError("root capability denied")
    if required_exp and root["exp"] < required_exp:
        raise ValueError("root expired")
    return root


def verify_ucan_invocation(
    token: str,
    *,
    audience: str,
    required_caps: List[Dict[str, str]],
) -> str:
    """
    Verify UCAN invocation and return root EVM address (lowercased).

    The invocation token is an EdDSA-signed JWS whose proof chain ends with a SIWE root proof.
    """
    payload, exp = verify_ucan_jws(token)
    if payload.get("aud") != audience:
        raise ValueError("UCAN audience mismatch")
    if not caps_allow(payload.get("cap") or [], required_caps):
        raise ValueError("UCAN capability denied")
    root = verify_proof_chain(payload.get("iss"), payload.get("cap") or [], exp, payload.get("prf") or [])
    address = str(root["iss"]).replace("did:pkh:eth:", "")
    return normalize_wallet_id(address)

