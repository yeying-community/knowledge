import {
  state,
  loadApiBase,
  setApiBase,
  loadWalletId,
  setWalletId,
  roleLabel,
  isSuperAdmin,
  ensureLoggedIn,
} from "./state.js";
import { ping } from "./api.js";

const apiBaseInput = document.getElementById("api-base");
const statusDot = document.getElementById("api-status-dot");
const statusText = document.getElementById("api-status-text");
const rolePill = document.getElementById("role-pill");
const walletIdDisplay = document.getElementById("wallet-id-display");
const backBtn = document.getElementById("back-btn");
const loginBtn = document.getElementById("login-btn");
const settingsForm = document.getElementById("settings-form");
const settingsSave = document.getElementById("settings-save");
const settingsClear = document.getElementById("settings-clear");
const settingsTest = document.getElementById("settings-test");
const settingsHint = document.getElementById("settings-hint");
const metricApiBase = document.getElementById("metric-api-base");
const metricApiBaseTrend = document.getElementById("metric-api-base-trend");
const metricWalletId = document.getElementById("metric-wallet-id");
const metricRoleLabel = document.getElementById("metric-role-label");
const walletIdInput = document.getElementById("wallet-id");

function setStatus(online) {
  statusDot.style.background = online ? "#39d98a" : "#ff6a88";
  statusDot.style.boxShadow = online
    ? "0 0 12px rgba(57, 217, 138, 0.7)"
    : "0 0 12px rgba(255, 106, 136, 0.7)";
  statusText.textContent = online ? "在线" : "离线";
}

function renderIdentity() {
  if (walletIdDisplay) {
    walletIdDisplay.textContent = state.walletId || "-";
  }
  if (rolePill) {
    const superAdmin = isSuperAdmin();
    rolePill.textContent = roleLabel();
    rolePill.classList.toggle("super", superAdmin);
    rolePill.classList.toggle("tenant", !superAdmin);
  }
  if (metricWalletId) {
    metricWalletId.textContent = state.walletId || "-";
  }
  if (metricRoleLabel) {
    metricRoleLabel.textContent = roleLabel();
  }
  if (walletIdInput) {
    walletIdInput.value = state.walletId || "";
  }
}

function renderApiBase() {
  const base = state.apiBase || "/";
  metricApiBase.textContent = base;
  metricApiBaseTrend.textContent = state.apiBase ? "自定义" : "同源";
}

async function testConnection() {
  settingsHint.textContent = "连接测试中...";
  let online = false;
  try {
    await ping();
    online = true;
  } catch (err) {
    online = false;
    settingsHint.textContent = `连接失败: ${err.message}`;
  }
  setStatus(online);
  if (online) {
    settingsHint.textContent = "连接正常。";
  }
}

function saveSettings() {
  if (walletIdInput) {
    setWalletId(walletIdInput.value.trim());
  }
  setApiBase(apiBaseInput.value.trim());
  renderIdentity();
  renderApiBase();
  settingsHint.textContent = "设置已保存。";
  testConnection();
}

function clearSettings() {
  setApiBase("");
  apiBaseInput.value = "";
  renderIdentity();
  renderApiBase();
  settingsHint.textContent = "已清空 API 地址。";
  testConnection();
}

apiBaseInput.value = loadApiBase();
loadWalletId();
const loggedIn = ensureLoggedIn();
if (loggedIn) {
  renderApiBase();
  renderIdentity();
  testConnection();
}
settingsForm.addEventListener("submit", (event) => {
  event.preventDefault();
  saveSettings();
});
settingsSave.addEventListener("click", () => saveSettings());
settingsClear.addEventListener("click", () => clearSettings());
settingsTest.addEventListener("click", () => testConnection());
backBtn.addEventListener("click", () => {
  window.location.href = "./index.html";
});
if (loginBtn) {
  loginBtn.addEventListener("click", () => {
    const next = encodeURIComponent(`${window.location.pathname}${window.location.search}`);
    window.location.href = `./login.html?next=${next}`;
  });
}
