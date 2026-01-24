import {
  state,
  loadApiBase,
  setApiBase,
  loadWalletId,
  roleLabel,
  isSuperAdmin,
  ensureLoggedIn,
} from "./state.js";
import {
  ping,
  fetchApps,
  fetchAppStatus,
  fetchKBList,
  fetchKBStats,
  fetchIngestionLogs,
  fetchStoresHealth,
  registerApp,
} from "./api.js";

const apiBaseInput = document.getElementById("api-base");
const refreshBtn = document.getElementById("refresh-btn");
const statusDot = document.getElementById("api-status-dot");
const statusText = document.getElementById("api-status-text");
const rolePill = document.getElementById("role-pill");
const walletIdDisplay = document.getElementById("wallet-id-display");
const backBtn = document.getElementById("back-btn");
const loginBtn = document.getElementById("login-btn");

const runAllBtn = document.getElementById("run-all");
const refreshAppsBtn = document.getElementById("refresh-apps");
const resetTestsBtn = document.getElementById("reset-tests");

const appSelect = document.getElementById("validation-app-select");
const validationWallet = document.getElementById("validation-wallet");
const validationRole = document.getElementById("validation-role");
const validationApiBase = document.getElementById("validation-api-base");
const validationAppStatus = document.getElementById("validation-app-status");

const metricTotal = document.getElementById("metric-total");
const metricPass = document.getElementById("metric-pass");
const metricFail = document.getElementById("metric-fail");

const testGrid = document.getElementById("test-grid");
const testHint = document.getElementById("test-hint");
const outputTitle = document.getElementById("output-title");
const outputBody = document.getElementById("validation-output");
const outputCopy = document.getElementById("output-copy");
const outputClear = document.getElementById("output-clear");
const outputHint = document.getElementById("output-hint");

let kbCache = [];
let selectedTestKey = "";

const tests = [
  {
    key: "health",
    title: "/health",
    desc: "服务连通性",
    run: async () => ping(),
  },
  {
    key: "app_register",
    title: "POST /app/register",
    desc: "应用注册/启用",
    run: async (ctx) => registerApp(ctx.appId, ctx.walletId),
    requiresApp: true,
  },
  {
    key: "app_list",
    title: "GET /app/list",
    desc: "租户应用列表",
    run: async (ctx) => fetchApps(ctx.walletId),
  },
  {
    key: "app_status",
    title: "GET /app/{app_id}/status",
    desc: "应用状态与 KB 统计",
    run: async (ctx) => fetchAppStatus(ctx.appId, ctx.walletId),
    requiresApp: true,
  },
  {
    key: "kb_list",
    title: "GET /kb/list",
    desc: "知识库列表",
    run: async (ctx) => fetchKBList(ctx.walletId),
  },
  {
    key: "kb_stats",
    title: "GET /kb/{app_id}/{kb_key}/stats",
    desc: "知识库统计",
    run: async (ctx) => {
      const kbKey = findKbKey(ctx.appId);
      if (!kbKey) {
        return { skipped: true, message: "当前应用暂无 KB" };
      }
      return fetchKBStats(ctx.appId, kbKey, ctx.walletId);
    },
    requiresApp: true,
  },
  {
    key: "ingestion_logs",
    title: "GET /ingestion/logs",
    desc: "摄取日志列表",
    run: async (ctx) => fetchIngestionLogs({ appId: ctx.appId, walletId: ctx.walletId, limit: 5, offset: 0 }),
    requiresApp: true,
  },
  {
    key: "stores_health",
    title: "GET /stores/health",
    desc: "存储健康检查",
    run: async () => fetchStoresHealth(),
  },
];

const testState = new Map();

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
  if (validationWallet) {
    validationWallet.textContent = state.walletId || "-";
  }
  if (validationRole) {
    validationRole.textContent = roleLabel();
  }
  if (validationApiBase) {
    validationApiBase.textContent = state.apiBase || "/";
  }
}

function findKbKey(appId) {
  const item = (kbCache || []).find((kb) => kb.app_id === appId);
  return item ? String(item.kb_key) : "";
}

function currentContext() {
  const appId = appSelect?.value || state.apps?.[0]?.app_id || "";
  return { appId, walletId: state.walletId };
}

function resetTestState() {
  tests.forEach((test) => {
    testState.set(test.key, { status: "idle", detail: "等待执行" });
  });
  selectedTestKey = "";
  renderTests();
  renderSummary();
  renderOutput();
}

function updateTestState(key, status, detail) {
  const existing = testState.get(key) || {};
  testState.set(key, { ...existing, status, detail });
  renderTests();
  renderSummary();
}

function updateTestPayload(key, payload, error = "") {
  const existing = testState.get(key) || {};
  testState.set(key, { ...existing, payload, error });
  renderTests();
}

function renderSummary() {
  const total = tests.length;
  const pass = Array.from(testState.values()).filter((item) => item.status === "pass").length;
  const fail = Array.from(testState.values()).filter((item) => item.status === "fail").length;
  if (metricTotal) metricTotal.textContent = String(total);
  if (metricPass) metricPass.textContent = String(pass);
  if (metricFail) metricFail.textContent = String(fail);
}

function renderTests() {
  if (!testGrid) return;
  const ctx = currentContext();
  testGrid.innerHTML = tests
    .map((test) => {
      const stateInfo = testState.get(test.key) || { status: "idle", detail: "等待执行" };
      const statusLabel = formatStatus(stateInfo.status);
      const canRun = !test.requiresApp || Boolean(ctx.appId);
      return `
        <div class="test-card">
          <div class="test-header">
            <div>
              <h3>${test.title}</h3>
              <p>${test.desc}</p>
            </div>
            <span class="test-status ${statusLabel.className}">${statusLabel.label}</span>
          </div>
          <div class="test-meta">${stateInfo.detail || "-"}</div>
          <div class="panel-tools">
            <button class="ghost" data-test="${test.key}" ${canRun ? "" : "disabled"}>运行</button>
            <button class="ghost" data-detail="${test.key}">详情</button>
          </div>
        </div>
      `;
    })
    .join("");

  testGrid.querySelectorAll("button[data-test]").forEach((btn) => {
    btn.addEventListener("click", () => runSingle(btn.dataset.test));
  });

  testGrid.querySelectorAll("button[data-detail]").forEach((btn) => {
    btn.addEventListener("click", () => {
      selectedTestKey = btn.dataset.detail || "";
      renderOutput();
    });
  });
}

function formatStatus(status) {
  if (status === "running") return { label: "运行中", className: "running" };
  if (status === "pass") return { label: "通过", className: "pass" };
  if (status === "fail") return { label: "失败", className: "fail" };
  if (status === "skip") return { label: "跳过", className: "skip" };
  return { label: "待执行", className: "" };
}

function shortDetail(payload) {
  if (!payload) return "完成。";
  if (payload.skipped) return payload.message || "跳过。";
  if (Array.isArray(payload)) return `返回 ${payload.length} 条。`;
  if (payload.items && Array.isArray(payload.items)) return `返回 ${payload.items.length} 条。`;
  if (payload.status) return `状态 ${payload.status}`;
  return "完成。";
}

function renderOutput() {
  if (!outputBody || !outputTitle) return;
  const key = selectedTestKey || tests[0]?.key || "";
  const test = tests.find((item) => item.key === key);
  const stateInfo = testState.get(key) || {};
  const title = test ? `输出详情 · ${test.title}` : "输出详情";
  outputTitle.textContent = title;
  const payload = {
    test: test ? test.title : key,
    status: stateInfo.status || "idle",
    detail: stateInfo.detail || "",
    error: stateInfo.error || "",
    response: stateInfo.payload ?? null,
  };
  try {
    outputBody.textContent = JSON.stringify(payload, null, 2);
  } catch (err) {
    outputBody.textContent = String(payload);
  }
}

async function runSingle(key) {
  const test = tests.find((item) => item.key === key);
  if (!test) return;
  const ctx = currentContext();
  if (outputHint) {
    outputHint.textContent = "";
  }
  if (test.requiresApp && !ctx.appId) {
    updateTestState(key, "skip", "未选择应用。");
    updateTestPayload(key, null, "未选择应用");
    selectedTestKey = key;
    renderOutput();
    return;
  }
  updateTestState(key, "running", "执行中...");
  try {
    const result = await test.run(ctx);
    if (result && result.skipped) {
      updateTestState(key, "skip", result.message || "跳过。");
      updateTestPayload(key, result, "");
      selectedTestKey = key;
      renderOutput();
      return;
    }
    updateTestState(key, "pass", shortDetail(result));
    updateTestPayload(key, result, "");
    selectedTestKey = key;
    renderOutput();
  } catch (err) {
    updateTestState(key, "fail", err.message || "执行失败");
    updateTestPayload(key, null, err.message || "执行失败");
    selectedTestKey = key;
    renderOutput();
  }
}

async function runAll() {
  if (runAllBtn) runAllBtn.disabled = true;
  testHint.textContent = "正在执行全部测试...";
  for (const test of tests) {
    await runSingle(test.key);
  }
  testHint.textContent = "全部测试已完成。";
  if (runAllBtn) runAllBtn.disabled = false;
}

async function loadApps() {
  try {
    const apps = await fetchApps(state.walletId);
    state.apps = apps || [];
    if (appSelect) {
      appSelect.innerHTML = state.apps
        .map((app) => `<option value="${app.app_id}">${app.app_id}</option>`)
        .join("");
      if (state.apps.length) {
        appSelect.value = state.apps[0].app_id;
        appSelect.disabled = false;
      } else {
        appSelect.disabled = true;
      }
    }
  } catch (err) {
    if (appSelect) {
      appSelect.innerHTML = "<option value=\"\">暂无应用</option>";
      appSelect.disabled = true;
    }
  }
}

async function loadKbList() {
  try {
    kbCache = await fetchKBList(state.walletId);
  } catch (err) {
    kbCache = [];
  }
}

async function refreshAppStatus() {
  const ctx = currentContext();
  if (!ctx.appId) {
    if (validationAppStatus) validationAppStatus.textContent = "-";
    return;
  }
  try {
    const status = await fetchAppStatus(ctx.appId, ctx.walletId);
    if (validationAppStatus) {
      validationAppStatus.textContent = status.status || "unknown";
    }
  } catch (err) {
    if (validationAppStatus) {
      validationAppStatus.textContent = "无法获取";
    }
  }
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
    testHint.textContent = "离线模式，仅显示示例数据。";
    renderTests();
    renderSummary();
    return;
  }

  await loadApps();
  await loadKbList();
  await refreshAppStatus();
  renderTests();
  renderSummary();
}

apiBaseInput.addEventListener("change", (event) => {
  setApiBase(event.target.value.trim());
  loadData();
});
refreshBtn.addEventListener("click", () => loadData());
if (runAllBtn) {
  runAllBtn.addEventListener("click", () => runAll());
}
if (refreshAppsBtn) {
  refreshAppsBtn.addEventListener("click", () => loadData());
}
if (resetTestsBtn) {
  resetTestsBtn.addEventListener("click", () => resetTestState());
}
if (appSelect) {
  appSelect.addEventListener("change", () => {
    resetTestState();
    refreshAppStatus();
  });
}
if (backBtn) {
  backBtn.addEventListener("click", () => {
    window.location.href = "./index.html";
  });
}
if (loginBtn) {
  loginBtn.addEventListener("click", () => {
    const next = encodeURIComponent(`${window.location.pathname}${window.location.search}`);
    window.location.href = `./login.html?next=${next}`;
  });
}
if (outputCopy) {
  outputCopy.addEventListener("click", () => {
    if (!outputBody) return;
    const text = outputBody.textContent || "";
    if (!text) return;
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(() => {
        if (outputHint) outputHint.textContent = "已复制输出内容。";
      });
      return;
    }
    if (outputHint) outputHint.textContent = "当前浏览器不支持复制。";
  });
}
if (outputClear) {
  outputClear.addEventListener("click", () => {
    selectedTestKey = "";
    if (outputBody) outputBody.textContent = "尚未运行测试。";
    if (outputHint) outputHint.textContent = "已清空输出。";
  });
}

apiBaseInput.value = loadApiBase();
loadWalletId();
const loggedIn = ensureLoggedIn();
if (loggedIn) {
  renderIdentity();
  resetTestState();
  renderOutput();
  loadData();
}
