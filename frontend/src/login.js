import { state, loadWalletId, setWalletId } from "./state.js";

const form = document.getElementById("login-form");
const walletInput = document.getElementById("wallet-id");
const loginHint = document.getElementById("login-hint");
const loginSuper = document.getElementById("login-super");

function nextTarget() {
  const params = new URLSearchParams(window.location.search);
  const next = params.get("next");
  if (!next) return "./index.html";
  return decodeURIComponent(next);
}

function loginWith(walletId) {
  const trimmed = (walletId || "").trim();
  if (!trimmed) {
    loginHint.textContent = "请输入 wallet_id。";
    return;
  }
  setWalletId(trimmed);
  loginHint.textContent = "登录成功，正在跳转...";
  window.location.href = nextTarget();
}

const current = loadWalletId();
if (walletInput) {
  walletInput.value = current || state.superAdminId;
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  loginWith(walletInput.value);
});

if (loginSuper) {
  loginSuper.addEventListener("click", () => {
    walletInput.value = state.superAdminId;
    loginWith(state.superAdminId);
  });
}
