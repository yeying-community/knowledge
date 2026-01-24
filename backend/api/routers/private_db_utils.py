# -*- coding: utf-8 -*-

from __future__ import annotations

from typing import Optional

from fastapi import HTTPException

from api.routers.owner import is_super_admin


def resolve_private_db_id(
    deps,
    *,
    app_id: str,
    wallet_id: str,
    private_db_id: Optional[str],
    session_id: Optional[str],
    allow_create: bool = False,
) -> Optional[str]:
    """
    Resolve private_db_id from session_id with optional create/bind.
    - allow_create=True: if session is new, create private_db and bind.
    - allow_create=False: missing session binding raises 404.
    """
    private_db_id = (private_db_id or "").strip() or None
    session_id = (session_id or "").strip() or None
    super_admin = is_super_admin(deps, wallet_id)

    if session_id:
        if private_db_id:
            deps.datasource.private_dbs.ensure_owner(
                private_db_id=private_db_id,
                app_id=app_id,
                owner_wallet_id=wallet_id,
            )
            row = deps.datasource.private_dbs.get_by_session(
                app_id=app_id,
                owner_wallet_id=wallet_id,
                session_id=session_id,
            )
            if row and row.get("private_db_id") != private_db_id:
                raise HTTPException(
                    status_code=400,
                    detail="session_id does not match private_db_id",
                )
            if not row:
                if not allow_create:
                    raise HTTPException(status_code=404, detail="session_id not bound to private_db")
                deps.datasource.private_dbs.bind_session(
                    private_db_id=private_db_id,
                    app_id=app_id,
                    owner_wallet_id=wallet_id,
                    session_id=session_id,
                )
        else:
            if allow_create:
                private_db_id = deps.datasource.private_dbs.resolve_or_create(
                    app_id=app_id,
                    owner_wallet_id=wallet_id,
                    session_id=session_id,
                )
            else:
                row = deps.datasource.private_dbs.get_by_session(
                    app_id=app_id,
                    owner_wallet_id=wallet_id,
                    session_id=session_id,
                )
                if not row:
                    raise HTTPException(status_code=404, detail="session_id not bound to private_db")
                private_db_id = row.get("private_db_id")

    if private_db_id and not super_admin:
        deps.datasource.private_dbs.ensure_owner(
            private_db_id=private_db_id,
            app_id=app_id,
            owner_wallet_id=wallet_id,
        )
    return private_db_id
