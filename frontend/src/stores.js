import {
  state,
  loadApiBase,
  setApiBase,
  loadWalletId,
  roleLabel,
  isSuperAdmin,
  ensureLoggedIn,
} from "./state.js";
import { mockData } from "./mock.js";
import { ping, fetchStoresHealth, fetchApps } from "./api.js";

const apiBaseInput = document.getElementById("api-base");
const refreshBtn = document.getElementById("refresh-btn");
const statusDot = document.getElementById("api-status-dot");
const statusText = document.getElementById("api-status-text");
const rolePill = document.getElementById("role-pill");
const walletIdDisplay = document.getElementById("wallet-id-display");
const backBtn = document.getElementById("back-btn");
const loginBtn = document.getElementById("login-btn");
const storesRefresh = document.getElementById("stores-refresh");
const storesExport = document.getElementById("stores-export");

const metricStores = document.getElementById("metric-stores");
const metricHealthy = document.getElementById("metric-healthy");
const metricStoresTrend = document.getElementById("metric-stores-trend");
const metricHealthyTrend = document.getElementById("metric-healthy-trend");

const storeGrid = document.getElementById("store-grid");
const storeHint = document.getElementById("store-hint");
const storeAppSelect = document.getElementById("store-app-select");
const storeBrowserGrid = document.getElementById("store-browser-grid");
const storeBrowserHint = document.getElementById("store-browser-hint");

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
}

function applyData(data) {
  state.apps = data.apps || [];
  state.stores = (data.stores || []).map(normalizeStore);
  metricStores.textContent = state.stores.length;
  const healthy = state.stores.filter((store) => store.status === "ok" || store.status === "configured").length;
  metricHealthy.textContent = healthy;
  metricStoresTrend.textContent = state.stores.length ? "在线" : "暂无存储";
  metricHealthyTrend.textContent = `${healthy}/${state.stores.length} 正常`;

  renderStores();
  renderAppSelect();
  renderBrowserEntries();
}

async function loadData() {
  let online = false;
  try {
    await ping();
    online = true;
  } catch (err) {
    online = false;
    if (state.apiBase) {
      try {
        const res = await fetch("/health");
        if (res.ok) {
          setApiBase("");
          apiBaseInput.value = "";
          online = true;
        }
      } catch (fallbackErr) {
        online = false;
      }
    }
  }
  setStatus(online);
  renderIdentity();

  if (!online) {
    applyData({ stores: mockData.stores, apps: mockData.apps });
    return;
  }

  try {
    const [storesHealth, apps] = await Promise.all([fetchStoresHealth(), fetchApps(state.walletId)]);
    applyData({
      stores: mapStores(storesHealth) || [],
      apps: apps || [],
    });
  } catch (err) {
    storeHint.textContent = `加载失败: ${err.message}`;
    applyData({ stores: [], apps: [] });
  }
}

function renderStores() {
  storeHint.textContent = "";
  if (!state.stores.length) {
    storeGrid.innerHTML = "<div class=\"detail-label\">暂无存储数据。</div>";
    return;
  }
  storeGrid.innerHTML = state.stores
    .map(
      (store) => `
      <div class="store-card">
        <div class="store-card-header">
          <div>
            <h3>${store.name}</h3>
            <span class="store-desc">${store.description}</span>
          </div>
          <span class="status-pill ${formatStatusClass(store.status)}">${formatStatus(store.status)}</span>
        </div>
        <div class="store-meta">
          <span>诊断: ${store.details}</span>
          <span>延迟: ${store.latency}</span>
        </div>
      </div>
    `
    )
    .join("");
}

function renderAppSelect() {
  if (!storeAppSelect) return;
  if (!state.apps.length) {
    storeAppSelect.innerHTML = "<option value=\"\">暂无应用</option>";
    storeAppSelect.disabled = true;
    state.selectedAppId = null;
    return;
  }

  storeAppSelect.disabled = false;
  storeAppSelect.innerHTML = state.apps
    .map((app) => `<option value="${app.app_id}">${app.app_id}</option>`)
    .join("");

  if (state.selectedAppId && state.apps.some((app) => app.app_id === state.selectedAppId)) {
    storeAppSelect.value = state.selectedAppId;
  } else {
    state.selectedAppId = state.apps[0].app_id;
    storeAppSelect.value = state.selectedAppId;
  }
}

function renderBrowserEntries() {
  if (!storeBrowserGrid) return;
  if (storeBrowserHint) {
    storeBrowserHint.textContent = "";
  }
  const appId = state.selectedAppId || (state.apps[0] && state.apps[0].app_id);
  if (!appId) {
    storeBrowserGrid.innerHTML = "<div class=\"detail-label\">暂无可用应用入口。</div>";
    return;
  }

  const entries = [
    {
      title: "知识库与文档",
      description: "查看当前应用的知识库、文档与字段结构。",
      action: "打开控制台",
      href: `./app.html?app_id=${encodeURIComponent(appId)}`,
    },
    {
      title: "摄取日志",
      description: "查看该应用的摄取时间线与导出。",
      action: "查看日志",
      href: `./app.html?app_id=${encodeURIComponent(appId)}`,
    },
    {
      title: "记忆写入",
      description: "管理会话摘要与长期记忆写入。",
      action: "进入页面",
      href: `./app.html?app_id=${encodeURIComponent(appId)}`,
    },
    {
      title: "全局摄取总览",
      description: "跨应用的摄取事件与统计。",
      action: "打开总览",
      href: "./index.html",
    },
    {
      title: "验证中心",
      description: "可视化运行中台接口验证脚本。",
      action: "打开验证",
      href: "./validation.html",
    },
  ];

  storeBrowserGrid.innerHTML = entries
    .map(
      (entry) => `
      <div class="browser-card">
        <div>
          <h3>${entry.title}</h3>
          <p>${entry.description}</p>
        </div>
        <div class="browser-card-actions">
          <button class="primary" data-open="${entry.href}">${entry.action}</button>
          <button class="ghost" data-copy="${entry.href}">复制链接</button>
        </div>
      </div>
    `
    )
    .join("");

  storeBrowserGrid.querySelectorAll("button[data-open]").forEach((button) => {
    button.addEventListener("click", () => {
      window.location.href = button.dataset.open;
    });
  });

  storeBrowserGrid.querySelectorAll("button[data-copy]").forEach((button) => {
    button.addEventListener("click", () => copyLink(button.dataset.copy));
  });
}

function mapStores(payload) {
  if (!payload || !Array.isArray(payload.stores)) return null;
  return payload.stores.map((store) => ({
    name: store.name.toUpperCase(),
    status: store.status,
    description: store.details || "无详情",
    details: store.details || "无详情",
    latency: "无",
  }));
}

function normalizeStore(store) {
  return {
    name: store.name || "-",
    status: store.status || "unknown",
    description: store.description || store.details || "无详情",
    details: store.details || store.description || "无详情",
    latency: store.latency || "无",
  };
}

function exportStores() {
  if (!state.stores.length) {
    storeHint.textContent = "没有可导出的存储数据。";
    return;
  }
  const blob = new Blob([JSON.stringify(state.stores, null, 2)], {
    type: "application/json",
  });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `stores-${Date.now()}.json`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function copyLink(path) {
  const url = new URL(path, window.location.href).toString();
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(url).then(() => {
      if (storeBrowserHint) {
        storeBrowserHint.textContent = "入口链接已复制。";
      }
    });
    return;
  }
  if (storeBrowserHint) {
    storeBrowserHint.textContent = `请复制链接: ${url}`;
  }
}

function formatStatus(status) {
  const normalized = String(status || "").toLowerCase();
  if (normalized === "ok") return "正常";
  if (normalized === "online") return "正常";
  if (normalized === "configured") return "已配置";
  if (normalized === "disabled") return "未启用";
  if (normalized === "error") return "异常";
  return status || "-";
}

function formatStatusClass(status) {
  const normalized = String(status || "").toLowerCase();
  if (normalized === "ok" || normalized === "online") return "status-ok";
  if (normalized === "configured") return "status-configured";
  if (normalized === "disabled") return "status-disabled";
  if (normalized === "error") return "status-error";
  return "status-unknown";
}

apiBaseInput.addEventListener("change", (event) => {
  setApiBase(event.target.value.trim());
  loadData();
});
refreshBtn.addEventListener("click", () => loadData());
storesRefresh.addEventListener("click", () => loadData());
storesExport.addEventListener("click", () => exportStores());
backBtn.addEventListener("click", () => {
  window.location.href = "./index.html";
});
if (loginBtn) {
  loginBtn.addEventListener("click", () => {
    const next = encodeURIComponent(`${window.location.pathname}${window.location.search}`);
    window.location.href = `./login.html?next=${next}`;
  });
}
if (storeAppSelect) {
  storeAppSelect.addEventListener("change", (event) => {
    state.selectedAppId = event.target.value;
    renderBrowserEntries();
  });
}

apiBaseInput.value = loadApiBase();
loadWalletId();
const loggedIn = ensureLoggedIn();
if (loggedIn) {
  renderIdentity();
  loadData();
}
