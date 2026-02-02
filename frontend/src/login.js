import { getProvider, loginWithChallenge, clearAccessToken } from "../assets/vendor/web3-bs.esm.js";
import { state, loadApiBase, setWalletId } from "./state.js";
import { fetchProfile } from "./api.js";

const AUTH_TOKEN_KEY = "rag_auth_token";

const form = document.getElementById("login-form");
const walletStatus = document.getElementById("wallet-status");
const loginHint = document.getElementById("login-hint");
const clearBtn = document.getElementById("login-clear");

function normalizeBaseUrl(value) {
  return (value || "").replace(/\/+$/, "");
}

function resolveAuthBaseUrl() {
  const base = normalizeBaseUrl(state.apiBase);
  return base ? `${base}/api/v1/public/auth` : "/api/v1/public/auth";
}

function nextTarget() {
  const params = new URLSearchParams(window.location.search);
  const next = params.get("next");
  if (!next) return "./index.html";
  return decodeURIComponent(next);
}

function setStatus(text) {
  if (walletStatus) walletStatus.textContent = text;
}

async function connectAndLogin() {
  loginHint.textContent = "正在连接钱包...";
  setStatus("连接中...");
  try {
    const provider = await getProvider({ timeoutMs: 3000 });
    if (!provider) {
      throw new Error("未检测到钱包 Provider，请先安装/启用钱包扩展。");
    }
    const result = await loginWithChallenge({
      provider,
      baseUrl: resolveAuthBaseUrl(),
      tokenStorageKey: AUTH_TOKEN_KEY,
      storeToken: true,
    });
    const address = (result.address || "").toLowerCase();
    setWalletId(address);
    try {
      await fetchProfile();
    } catch {
    }
    setStatus(address ? `已登录：${address}` : "已登录");
    loginHint.textContent = "登录成功，正在跳转...";
    window.location.href = nextTarget();
  } catch (err) {
    loginHint.textContent = `登录失败: ${err?.message || err}`;
    setStatus("未连接");
  }
}

function clearLogin() {
  clearAccessToken({ tokenStorageKey: AUTH_TOKEN_KEY, storeToken: true });
  localStorage.removeItem("rag_wallet_id");
  localStorage.removeItem("rag_is_super_admin");
  setStatus("未连接");
  loginHint.textContent = "已清理本地登录信息。";
}

loadApiBase();

if (clearBtn) {
  clearBtn.addEventListener("click", () => clearLogin());
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  connectAndLogin();
});
