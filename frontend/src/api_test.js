import {
  state,
  loadApiBase,
  setApiBase,
  loadWalletId,
  roleLabel,
  isSuperAdmin,
  ensureLoggedIn,
} from "./state.js";
import { ping, fetchApps, fetchKBList, fetchAppIntents } from "./api.js";

const apiBaseInput = document.getElementById("api-base");
const refreshBtn = document.getElementById("refresh-btn");
const statusDot = document.getElementById("api-status-dot");
const statusText = document.getElementById("api-status-text");
const rolePill = document.getElementById("role-pill");
const walletIdDisplay = document.getElementById("wallet-id-display");
const loginBtn = document.getElementById("login-btn");
const backBtn = document.getElementById("back-btn");

const testRefresh = document.getElementById("test-refresh");
const testReset = document.getElementById("test-reset");
const testDocs = document.getElementById("test-docs");
const testHint = document.getElementById("test-hint");

const metricApp = document.getElementById("metric-app");
const metricKbs = document.getElementById("metric-kbs");

const appSelect = document.getElementById("test-app-select");
const kbSelect = document.getElementById("test-kb-select");
const walletInput = document.getElementById("test-wallet-id");
const sessionInput = document.getElementById("test-session-id");
const privateInput = document.getElementById("test-private-db");
const dataWalletInput = document.getElementById("test-data-wallet");
const intentInput = document.getElementById("test-intent");
const targetInput = document.getElementById("test-target");
const companyInput = document.getElementById("test-company");

const testGrid = document.getElementById("test-grid");
const testFilters = document.getElementById("test-filters");
const testSearch = document.getElementById("test-search");
const expandAllBtn = document.getElementById("expand-all");
const collapseAllBtn = document.getElementById("collapse-all");
const clearResponsesBtn = document.getElementById("clear-responses");
const intentGuide = document.getElementById("intent-guide");
const intentGuideBody = document.getElementById("intent-guide-body");

let kbCache = [];
let apiSeeds = { sessionId: "", resumeId: "", jdId: "" };
let activeTestGroup = "all";
let testSearchKeyword = "";
const cardCollapseState = new Map();
const lastResponses = new Map();
const lastRequests = new Map();
let defaultIntent = "";
let currentAppId = new URLSearchParams(window.location.search).get("app_id") || "";

function setStatus(online) {
  statusDot.style.background = online ? "#39d98a" : "#ff6a88";
  statusDot.style.boxShadow = online
    ? "0 0 12px rgba(57, 217, 138, 0.7)"
    : "0 0 12px rgba(255, 106, 136, 0.7)";
  statusText.textContent = online ? "在线" : "离线";
}

function renderIdentity() {
  walletIdDisplay.textContent = state.walletId || "-";
  const superAdmin = isSuperAdmin();
  rolePill.textContent = roleLabel();
  rolePill.classList.toggle("super", superAdmin);
  rolePill.classList.toggle("tenant", !superAdmin);
  if (walletInput && !walletInput.value) {
    walletInput.value = state.walletId || "";
  }
}

function escapeHtml(value) {
  return String(value || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function updateUrl(appId) {
  const url = new URL(window.location.href);
  if (appId) {
    url.searchParams.set("app_id", appId);
  } else {
    url.searchParams.delete("app_id");
  }
  history.replaceState({}, "", url.toString());
}

function resetDefaults() {
  const seed = Math.random().toString(36).slice(2, 6);
  apiSeeds = {
    sessionId: `session_demo_${seed}`,
    resumeId: "",
    jdId: "",
  };
  if (sessionInput) sessionInput.value = apiSeeds.sessionId;
  if (privateInput) privateInput.value = "";
  if (dataWalletInput) dataWalletInput.value = "";
  ensureDefaultIntent();
  if (targetInput) targetInput.value = "";
  if (companyInput) companyInput.value = "";
}

function getContext() {
  const walletId = (walletInput?.value || state.walletId || "").trim();
  return {
    appId: currentAppId || "",
    kbKey: kbSelect?.value || "",
    walletId,
    sessionId: (sessionInput?.value || "").trim(),
    privateDbId: (privateInput?.value || "").trim(),
    dataWalletId: (dataWalletInput?.value || "").trim(),
    intent: (intentInput?.value || "").trim(),
    target: (targetInput?.value || "").trim(),
    company: (companyInput?.value || "").trim(),
    resumeId: apiSeeds.resumeId,
    jdId: apiSeeds.jdId,
  };
}

function ensureDefaultIntent() {
  if (!intentInput) return;
  const current = (intentInput.value || "").trim();
  if (current && current !== "default") return;
  if (defaultIntent) {
    intentInput.value = defaultIntent;
    return;
  }
  if (isInterviewerApp(currentAppId)) {
    intentInput.value = "generate_questions";
  } else {
    intentInput.value = "";
  }
}

function renderIntentGuide() {
  if (!intentGuideBody || !intentGuide) return;
  const appKey = isInterviewerApp(currentAppId) ? "interviewer" : "";
  const intentName = (intentInput?.value || "").trim() || defaultIntent || "";
  const guide = appKey ? INTENT_GUIDES[appKey] : null;
  const fields = guide?.[intentName] || guide?.generate_questions || [];
  if (!fields.length) {
    intentGuideBody.innerHTML = `<div class="form-hint">暂无可用说明。</div>`;
    return;
  }
  intentGuideBody.innerHTML = fields
    .map((item) => {
      return `
        <div class="intent-guide-item">
          <div class="intent-guide-key">${escapeHtml(item.key)}</div>
          <div class="intent-guide-desc">${escapeHtml(item.desc)}</div>
        </div>
      `;
    })
    .join("");
}

const TEST_GROUPS = [
  { id: "all", label: "全部" },
  { id: "interviewer", label: "面试官流程" },
  { id: "core", label: "应用 / KB" },
  { id: "ingestion", label: "摄取" },
  { id: "private", label: "私有库" },
  { id: "memory", label: "记忆" },
];

const INTENT_GUIDES = {
  interviewer: {
    generate_questions: [
      { key: "basic_count", desc: "基础题数量（默认 3）" },
      { key: "project_count", desc: "项目题数量（默认 3）" },
      { key: "scenario_count", desc: "场景题数量（默认 3）" },
      { key: "target_position", desc: "目标岗位（可选）" },
      { key: "company", desc: "公司名（可选）" },
      { key: "resume_text", desc: "简历文本（可选）" },
      { key: "jd_text", desc: "JD 文本（可选）" },
    ],
  },
};

const INTERVIEWER_TEST_IDS = new Set([
  "resume-upload",
  "jd-upload",
  "query",
  "memory-sessions",
  "kb-stats",
  "kb-docs",
  "private-create",
  "private-bind",
  "private-sessions",
  "private-unbind",
]);

const API_TEST_CASES = [
  {
    id: "app-status",
    title: "应用状态",
    method: "GET",
    group: "core",
    buildPath: (ctx) => `/app/${ctx.appId}/status`,
    buildQuery: (ctx) => ({ wallet_id: ctx.walletId }),
    summary: "校验 app 是否已注册并处于 active。",
    details:
      "用于确认 app 的注册状态、插件可用性与最近一次摄取记录。面试官业务通常只需在调试时使用。",
  },
  {
    id: "kb-stats",
    title: "KB 统计",
    method: "GET",
    group: "core",
    buildPath: (ctx) => `/kb/${ctx.appId}/${ctx.kbKey}/stats`,
    buildQuery: (ctx) => ({
      wallet_id: ctx.walletId,
      session_id: ctx.sessionId || undefined,
      private_db_id: ctx.privateDbId || undefined,
      data_wallet_id: ctx.dataWalletId || undefined,
    }),
    summary: "查看 KB 文档量 / 向量量。",
    details:
      "适用于确认 KB 是否有数据。若是 user_upload 类型，可通过 session/private_db/data_wallet 过滤。",
  },
  {
    id: "kb-docs",
    title: "KB 文档列表",
    method: "GET",
    group: "core",
    buildPath: (ctx) => `/kb/${ctx.appId}/${ctx.kbKey}/documents`,
    buildQuery: (ctx) => ({
      wallet_id: ctx.walletId,
      limit: 5,
      offset: 0,
      session_id: ctx.sessionId || undefined,
      private_db_id: ctx.privateDbId || undefined,
      data_wallet_id: ctx.dataWalletId || undefined,
    }),
    summary: "拉取少量文档，验证过滤条件。",
    details:
      "用于排查数据是否被写入到正确的 KB。若选错 kb_key 会导致只看到 JD_KB 等单一 KB。",
  },
  {
    id: "ingestion-create",
    title: "创建摄取作业",
    method: "POST",
    group: "ingestion",
    buildPath: () => "/ingestion/jobs",
    buildQuery: () => ({ run: "true" }),
    buildBody: (ctx) => ({
      wallet_id: ctx.walletId,
      app_id: ctx.appId,
      kb_key: ctx.kbKey,
      session_id: ctx.sessionId || undefined,
      private_db_id: ctx.privateDbId || undefined,
      data_wallet_id: ctx.dataWalletId || undefined,
      content: "Demo content for ingestion job.",
      filename: "demo.txt",
      metadata: { source: "ui-test" },
      options: { max_chars: 8000 },
    }),
    summary: "用内联文本创建并执行摄取作业。",
    details:
      "适合快速测试摄取链路。生产环境一般使用上传文件 + source_url 方式。",
  },
  {
    id: "ingestion-upload",
    title: "上传文件到 MinIO",
    method: "POST",
    group: "ingestion",
    buildPath: () => "/ingestion/upload",
    buildBody: (ctx) => ({
      wallet_id: ctx.walletId,
      app_id: ctx.appId,
      kb_key: ctx.kbKey,
      data_wallet_id: ctx.dataWalletId || undefined,
    }),
    summary: "上传文件到 MinIO，返回 source_url。",
    details:
      "适合上传真实文件后再创建摄取作业。MinIO 采用单桶多前缀方式隔离 app。",
    requiresFile: true,
  },
  {
    id: "resume-upload",
    title: "简历上传",
    method: "POST",
    group: "interviewer",
    buildPath: () => "/resume/upload",
    buildBody: (ctx) => ({
      wallet_id: ctx.walletId,
      app_id: ctx.appId,
      session_id: ctx.sessionId || undefined,
      private_db_id: ctx.privateDbId || undefined,
      metadata: { source: "ui-test" },
      resume: {
        name: "Alex Chen",
        skills: ["python", "golang"],
        text: "Backend engineer with 5 years of experience.",
      },
    }),
    summary: "上传简历 JSON 到 user_upload KB。",
    details:
      "返回 resume_id，用于 query 时拉取简历文本。若使用 private_db_id，会写入该私有库。",
  },
  {
    id: "jd-upload",
    title: "JD 上传",
    method: "POST",
    group: "interviewer",
    buildPath: (ctx) => `/${ctx.appId}/jd/upload`,
    buildBody: (ctx) => ({
      wallet_id: ctx.walletId,
      app_id: ctx.appId,
      session_id: ctx.sessionId || undefined,
      private_db_id: ctx.privateDbId || undefined,
      metadata: { source: "ui-test" },
      jd: {
        title: "Backend Engineer",
        requirements: ["Python", "Distributed Systems"],
        text: "We are looking for a Backend Engineer...",
      },
    }),
    summary: "上传 JD JSON 到 user_upload KB。",
    details:
      "返回 jd_id。若不传 jd_id，query 会尝试从 jd_kb 自动检索文本。",
  },
  {
    id: "query",
    title: "查询",
    method: "POST",
    group: "interviewer",
    buildPath: () => "/query",
    buildBody: (ctx) => ({
      wallet_id: ctx.walletId,
      app_id: ctx.appId,
      session_id: ctx.sessionId || undefined,
      private_db_id: ctx.privateDbId || undefined,
      intent: ctx.intent || defaultIntent || "default",
      resume_id: ctx.resumeId || undefined,
      jd_id: ctx.jdId || undefined,
      target: ctx.target || undefined,
      company: ctx.company || undefined,
      intent_params: {},
      query: "总结候选人的优势。",
    }),
    summary: "核心业务查询入口。",
    details:
      "优先级：intent_params 中的字段 > resume_id/jd_id > query。\n" +
      "只有简历：提供 resume_id 或 intent_params.resume_text；若未传 jd_id，可能触发 JD 自动检索（配置开启）。\n" +
      "简历 + JD：提供 resume_id + jd_id（推荐），或直接用 intent_params.resume_text/jd_text。\n" +
      "简历/JD 都没有：必须提供 query 或 intent_params（否则 400）。\n" +
      "resume_id/jd_id 会从 user_upload 拉文本；target/company 会写入 intent_params。",
  },
  {
    id: "private-create",
    title: "创建私有库",
    method: "POST",
    group: "private",
    buildPath: () => "/private_dbs",
    buildBody: (ctx) => ({
      wallet_id: ctx.walletId,
      app_id: ctx.appId,
    }),
    summary: "创建私有库并返回 private_db_id。",
    details:
      "私有库按 app_id 隔离，可用于跨会话聚合业务用户数据。",
  },
  {
    id: "private-bind",
    title: "绑定会话",
    method: "POST",
    group: "private",
    buildPath: (ctx) => `/private_dbs/${ctx.privateDbId || "PRIVATE_DB_ID"}/bind`,
    buildBody: (ctx) => ({
      wallet_id: ctx.walletId,
      app_id: ctx.appId,
      session_ids: [ctx.sessionId || apiSeeds.sessionId],
    }),
    summary: "将 session_id 绑定到指定私有库。",
    details:
      "绑定后，查询与写入可通过 private_db_id 聚合多个 session。",
  },
  {
    id: "private-sessions",
    title: "私有库会话列表",
    method: "GET",
    group: "private",
    buildPath: (ctx) => `/private_dbs/${ctx.privateDbId || "PRIVATE_DB_ID"}/sessions`,
    buildQuery: (ctx) => ({ wallet_id: ctx.walletId, app_id: ctx.appId }),
    summary: "查看私有库绑定的会话。",
    details:
      "用于审计与排查绑定关系。",
  },
  {
    id: "private-unbind",
    title: "解绑会话",
    method: "DELETE",
    group: "private",
    buildPath: (ctx) =>
      `/private_dbs/${ctx.privateDbId || "PRIVATE_DB_ID"}/sessions/${ctx.sessionId || apiSeeds.sessionId}`,
    buildQuery: (ctx) => ({ wallet_id: ctx.walletId, app_id: ctx.appId }),
    summary: "解绑指定 session。",
    details:
      "解绑后该 session 不再归属该私有库。",
  },
  {
    id: "memory-sessions",
    title: "记忆会话列表",
    method: "GET",
    group: "memory",
    buildPath: () => "/memory/sessions",
    buildQuery: (ctx) => ({
      wallet_id: ctx.walletId,
      app_id: ctx.appId,
      data_wallet_id: ctx.dataWalletId || undefined,
      limit: 10,
      offset: 0,
    }),
    summary: "查看记忆会话列表。",
    details:
      "用于检查记忆是否被写入，支持按 data_wallet_id 过滤业务用户。",
  },
];

function buildUrl(path, query) {
  const params = new URLSearchParams();
  Object.entries(query || {}).forEach(([key, value]) => {
    if (value === undefined || value === null || value === "") return;
    params.set(key, String(value));
  });
  const qs = params.toString();
  return qs ? `${path}?${qs}` : path;
}

function getGroupLabel(groupId) {
  return TEST_GROUPS.find((group) => group.id === groupId)?.label || groupId;
}

function copyToClipboard(text, fallbackMessage) {
  if (!text) return;
  navigator.clipboard
    .writeText(text)
    .then(() => {
      if (testHint) testHint.textContent = fallbackMessage || "已复制到剪贴板。";
    })
    .catch(() => {
      if (testHint) testHint.textContent = "复制失败，请手动复制。";
    });
}

function isInterviewerApp(appId) {
  return String(appId || "").toLowerCase().includes("interviewer");
}

function getVisibleCases() {
  if (isInterviewerApp(currentAppId)) {
    return API_TEST_CASES.filter((item) => INTERVIEWER_TEST_IDS.has(item.id));
  }
  return API_TEST_CASES;
}

function renderTestFilters() {
  if (!testFilters) return;
  const cases = getVisibleCases();
  const groupCounts = cases.reduce((acc, item) => {
    const groupId = item.group || "core";
    acc[groupId] = (acc[groupId] || 0) + 1;
    return acc;
  }, {});
  const visibleGroups = TEST_GROUPS.filter((group) => group.id === "all" || groupCounts[group.id]);
  if (!visibleGroups.some((group) => group.id === activeTestGroup)) {
    activeTestGroup = "all";
  }
  testFilters.innerHTML = visibleGroups
    .map((group) => {
    const active = group.id === activeTestGroup;
    return `<button class="chip${active ? " active" : ""}" data-test-group="${group.id}">${escapeHtml(
      group.label,
    )}</button>`;
  })
    .join("");
  testFilters.querySelectorAll("button[data-test-group]").forEach((btn) => {
    btn.addEventListener("click", () => {
      activeTestGroup = btn.dataset.testGroup || "all";
      renderTestFilters();
      renderTestGrid();
    });
  });
}

function setCardCollapsed(card, collapsed) {
  card.classList.toggle("collapsed", collapsed);
  cardCollapseState.set(card.dataset.testId, collapsed);
  const label = card.querySelector(".api-test-toggle");
  if (label) {
    label.textContent = collapsed ? "点击展开" : "点击收起";
  }
}

function updateTestBody(testId) {
  const item = API_TEST_CASES.find((entry) => entry.id === testId);
  if (!item?.buildBody) return;
  const ctx = getContext();
  const textarea = document.querySelector(`textarea[data-test-body="${item.id}"]`);
  if (textarea) {
    textarea.value = JSON.stringify(item.buildBody(ctx), null, 2);
  }
}

function renderTestGrid() {
  if (!testGrid) return;
  const ctx = getContext();
  const keyword = testSearchKeyword.toLowerCase();
  const filtered = getVisibleCases().filter((item) => {
    if (activeTestGroup !== "all" && item.group !== activeTestGroup) return false;
    if (!keyword) return true;
    const hay = [item.title, item.hint, item.id, item.method, item.buildPath(ctx)]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();
    return hay.includes(keyword);
  });

  if (!filtered.length) {
    testGrid.innerHTML = `
      <div class="empty-state">
        <div class="empty-title">暂无匹配接口</div>
        <div class="empty-subtitle">请调整筛选或搜索条件。</div>
      </div>
    `;
    return;
  }

  const cards = filtered.map((item) => {
    const path = item.buildPath(ctx);
    const query = item.buildQuery ? item.buildQuery(ctx) : {};
    const url = buildUrl(path, query);
    const body = item.buildBody ? JSON.stringify(item.buildBody(ctx), null, 2) : "";
    const bodyBlock = item.buildBody
      ? `
        <div class="form-group">
          <label for="test-body-${item.id}">请求体 (JSON)</label>
          <textarea class="text-mono" id="test-body-${item.id}" rows="5" data-test-body="${item.id}">${body}</textarea>
        </div>
      `
      : `<p class="form-hint">该接口无需请求体。</p>`;
    const fileBlock = item.requiresFile
      ? `
        <div class="form-group">
          <label for="test-file-${item.id}">上传文件</label>
          <input id="test-file-${item.id}" type="file" />
          <p class="form-hint">使用真实文件上传到 MinIO。</p>
        </div>
      `
      : "";
    const collapsed = cardCollapseState.get(item.id) ?? true;
    const groupLabel = getGroupLabel(item.group);
    const summary = item.summary || item.hint || "";
    const details = item.details || "";
    const detailBlock = details
      ? `
        <details class="api-test-details">
          <summary>详细说明</summary>
          <div class="api-test-detail-body">${escapeHtml(details)}</div>
        </details>
      `
      : "";
    return `
      <div class="panel nested api-test-card ${collapsed ? "collapsed" : ""}" data-test-id="${item.id}">
        <div class="panel-header" data-test-toggle="${item.id}">
          <div>
            <h2>${item.title}</h2>
            <div class="api-test-meta">
              <span class="badge">${item.method}</span>
              <span class="badge">${escapeHtml(groupLabel)}</span>
              <span class="api-test-path">${escapeHtml(url)}</span>
              <span class="api-test-status" id="test-status-${item.id}" data-status="idle">未执行</span>
              <span class="api-test-run" id="test-run-${item.id}">-</span>
            </div>
            <p class="form-hint">${escapeHtml(summary)}</p>
            ${detailBlock}
          </div>
          <div class="panel-tools">
            <span class="api-test-toggle">${collapsed ? "点击展开" : "点击收起"}</span>
            <button class="ghost" data-test-send="${item.id}">发送</button>
          </div>
        </div>
        <div class="api-test-body">
          ${fileBlock}
          ${bodyBlock}
          <div class="api-test-response">
            <div class="api-test-response-header">
              <label>响应</label>
              <div class="api-test-response-actions">
                <button class="ghost" data-copy-response="${item.id}">复制响应</button>
                <button class="ghost" data-copy-curl="${item.id}">复制 curl</button>
              </div>
            </div>
            <pre class="detail-log validation-output" id="test-response-${item.id}">尚未发送请求。</pre>
          </div>
        </div>
      </div>
    `;
  }).join("");
  testGrid.innerHTML = cards;

  testGrid.querySelectorAll("button[data-test-send]").forEach((btn) => {
    btn.addEventListener("click", () => runTest(btn.dataset.testSend));
  });

  testGrid.querySelectorAll("button[data-copy-response]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const testId = btn.dataset.copyResponse;
      const cached = lastResponses.get(testId);
      if (!cached) {
        if (testHint) testHint.textContent = "暂无可复制的响应，请先发送请求。";
        return;
      }
      copyToClipboard(cached.text, "响应已复制。");
    });
  });

  testGrid.querySelectorAll("button[data-copy-curl]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const testId = btn.dataset.copyCurl;
      const req = lastRequests.get(testId);
      if (!req) {
        if (testHint) testHint.textContent = "请先发送请求或编辑请求体后再复制 curl。";
        return;
      }
      if (req.isFile) {
        if (testHint) testHint.textContent = "文件上传暂不支持生成 curl。";
        return;
      }
      const parts = [`curl -X ${req.method} '${req.url}'`];
      if (req.method !== "GET") {
        parts.push("-H 'Content-Type: application/json'");
        if (req.body) {
          parts.push(`-d '${req.body}'`);
        }
      }
      copyToClipboard(parts.join(" "), "curl 已复制。");
    });
  });

  testGrid.querySelectorAll("[data-test-toggle]").forEach((header) => {
    header.addEventListener("click", (event) => {
      if (event.target.closest("button")) return;
      const card = header.closest(".api-test-card");
      if (!card) return;
      const next = !card.classList.contains("collapsed");
      setCardCollapsed(card, next);
    });
  });

  lastResponses.forEach((data, testId) => {
    const output = document.getElementById(`test-response-${testId}`);
    if (output && data?.text) {
      output.textContent = data.text;
    }
    const statusNode = document.getElementById(`test-status-${testId}`);
    if (statusNode && data) {
      if (data.error) {
        statusNode.textContent = "请求失败";
        statusNode.dataset.status = "error";
      } else if (data.status !== undefined) {
        statusNode.textContent = data.ok ? `成功 ${data.status}` : `失败 ${data.status}`;
        statusNode.dataset.status = data.ok ? "ok" : "error";
      }
    }
    const runNode = document.getElementById(`test-run-${testId}`);
    if (runNode && data?.durationMs !== undefined) {
      runNode.textContent = `耗时 ${data.durationMs}ms`;
    }
  });
}

async function runTest(testId) {
  if (!testId) return;
  const item = API_TEST_CASES.find((entry) => entry.id === testId);
  if (!item) return;
  const ctx = getContext();
  if (!ctx.appId || !ctx.walletId) {
    if (testHint) testHint.textContent = "请先设置 app_id 与 wallet_id。";
    return;
  }
  if (
    (item.id === "kb-stats" ||
      item.id === "kb-docs" ||
      item.id === "ingestion-create" ||
      item.id === "ingestion-upload") &&
    !ctx.kbKey
  ) {
    if (testHint) testHint.textContent = "请选择 kb_key 后再测试该接口。";
    return;
  }
  const path = item.buildPath(ctx);
  const query = item.buildQuery ? item.buildQuery(ctx) : {};
  const url = buildUrl(path, query);
  const fullUrl = state.apiBase ? `${state.apiBase}${url}` : url;
  const options = { method: item.method };
  const statusNode = document.getElementById(`test-status-${item.id}`);
  const runNode = document.getElementById(`test-run-${item.id}`);
  const requestMeta = {
    method: item.method,
    url: fullUrl,
    isFile: Boolean(item.requiresFile),
    body: "",
  };
  if (item.requiresFile) {
    const fileInput = document.getElementById(`test-file-${item.id}`);
    const file = fileInput?.files?.[0];
    if (!file) {
      if (testHint) testHint.textContent = "请先选择要上传的文件。";
      return;
    }
    const payload = item.buildBody ? item.buildBody(ctx) : {};
    const form = new FormData();
    Object.entries(payload || {}).forEach(([key, value]) => {
      if (value === undefined || value === null || value === "") return;
      form.append(key, String(value));
    });
    form.append("file", file, file.name);
    options.body = form;
  } else {
    options.headers = { "Content-Type": "application/json" };
    if (item.buildBody) {
      const textarea = document.querySelector(`textarea[data-test-body="${item.id}"]`);
      const raw = textarea ? textarea.value.trim() : "";
      if (raw) {
        try {
          options.body = JSON.stringify(JSON.parse(raw));
          requestMeta.body = options.body;
        } catch (err) {
          if (testHint) testHint.textContent = `请求体 JSON 解析失败：${err.message}`;
          return;
        }
      }
    }
  }
  try {
    if (testHint) testHint.textContent = "";
    if (statusNode) {
      statusNode.textContent = "执行中";
      statusNode.dataset.status = "running";
    }
    if (runNode) runNode.textContent = "-";
    lastRequests.set(item.id, requestMeta);
    const startAt = performance.now();
    const res = await fetch(fullUrl, options);
    const endAt = performance.now();
    const durationMs = Math.round(endAt - startAt);
    const text = await res.text();
    let payload = text;
    let dataObj = null;
    try {
      dataObj = JSON.parse(text);
      payload = JSON.stringify(dataObj, null, 2);
    } catch (err) {
      payload = text;
    }
    const output = document.getElementById(`test-response-${item.id}`);
    if (output) {
      output.textContent = `# ${item.method} ${url}\nStatus: ${res.status}\n\n${payload}`;
    }
    lastResponses.set(item.id, {
      text: output?.textContent || payload,
      status: res.status,
      ok: res.ok,
      durationMs,
    });
    const card = document.querySelector(`.api-test-card[data-test-id="${item.id}"]`);
    if (card) {
      setCardCollapsed(card, false);
    }
    if (statusNode) {
      statusNode.textContent = res.ok ? `成功 ${res.status}` : `失败 ${res.status}`;
      statusNode.dataset.status = res.ok ? "ok" : "error";
    }
    if (runNode) {
      runNode.textContent = `耗时 ${durationMs}ms`;
    }
    if (res.ok && dataObj) {
      if (item.id === "resume-upload" && dataObj.resume_id) {
        apiSeeds.resumeId = String(dataObj.resume_id);
        updateTestBody("query");
      }
      if (item.id === "jd-upload" && dataObj.jd_id) {
        apiSeeds.jdId = String(dataObj.jd_id);
        updateTestBody("query");
      }
    }
  } catch (err) {
    const output = document.getElementById(`test-response-${item.id}`);
    if (output) {
      output.textContent = `# ${item.method} ${url}\nError: ${err.message}`;
    }
    lastResponses.set(item.id, {
      text: `# ${item.method} ${url}\nError: ${err.message}`,
      error: true,
    });
    if (statusNode) {
      statusNode.textContent = "请求失败";
      statusNode.dataset.status = "error";
    }
    if (runNode) runNode.textContent = "-";
  }
}

function fillAppOptions(apps) {
  appSelect.innerHTML = (apps || [])
    .map((app) => `<option value="${escapeHtml(app.app_id)}">${escapeHtml(app.app_id)}</option>`)
    .join("");
  if (currentAppId && apps.some((app) => app.app_id === currentAppId)) {
    appSelect.value = currentAppId;
  } else if (apps[0]) {
    currentAppId = apps[0].app_id;
    appSelect.value = currentAppId;
  }
  updateUrl(currentAppId);
}

function fillKbOptions() {
  const rows = kbCache.filter((kb) => kb.app_id === currentAppId);
  if (!rows.length) {
    kbSelect.innerHTML = "<option value=\"\">暂无 KB</option>";
    kbSelect.disabled = true;
    metricKbs.textContent = "0";
    return;
  }
  kbSelect.disabled = false;
  kbSelect.innerHTML = rows
    .map((kb) => {
      const label = kb.kb_type ? `${kb.kb_key} (${kb.kb_type})` : kb.kb_key;
      return `<option value="${kb.kb_key}">${escapeHtml(label)}</option>`;
    })
    .join("");
  metricKbs.textContent = String(rows.length);
}

async function refreshAll() {
  let online = false;
  try {
    await ping();
    online = true;
  } catch (err) {
    online = false;
  }
  setStatus(online);
  renderIdentity();
  if (!online) return;

  try {
    const [apps, kbList, intentsResp] = await Promise.all([
      fetchApps(state.walletId),
      fetchKBList(state.walletId),
      currentAppId ? fetchAppIntents(currentAppId, state.walletId) : Promise.resolve(null),
    ]);
    kbCache = kbList || [];
    fillAppOptions(apps || []);
    fillKbOptions();
    metricApp.textContent = currentAppId || "-";
    if (isInterviewerApp(currentAppId)) {
      activeTestGroup = "all";
    }
    if (intentsResp?.exposed_intents?.length) {
      defaultIntent = intentsResp.exposed_intents[0];
    }
    ensureDefaultIntent();
    renderIntentGuide();
    renderTestFilters();
    renderTestGrid();
  } catch (err) {
    if (testHint) testHint.textContent = `加载失败：${err.message}`;
  }
}

appSelect?.addEventListener("change", () => {
  currentAppId = appSelect.value;
  updateUrl(currentAppId);
  fillKbOptions();
  metricApp.textContent = currentAppId || "-";
  defaultIntent = "";
  if (!isInterviewerApp(currentAppId) && activeTestGroup === "interviewer") {
    activeTestGroup = "all";
  }
  if (isInterviewerApp(currentAppId)) {
    activeTestGroup = "all";
  }
  renderTestFilters();
  renderTestGrid();
  if (currentAppId) {
    fetchAppIntents(currentAppId, state.walletId)
      .then((resp) => {
        const intents = resp?.exposed_intents || [];
        if (!intents.length) return;
        defaultIntent = intents[0];
        ensureDefaultIntent();
        renderIntentGuide();
        renderTestGrid();
      })
      .catch(() => {});
  }
  ensureDefaultIntent();
  renderIntentGuide();
});

const updateContextUI = () => {
  renderTestGrid();
  renderIntentGuide();
};

kbSelect?.addEventListener("change", () => updateContextUI());
walletInput?.addEventListener("change", () => updateContextUI());
sessionInput?.addEventListener("change", () => updateContextUI());
privateInput?.addEventListener("change", () => updateContextUI());
dataWalletInput?.addEventListener("change", () => updateContextUI());
intentInput?.addEventListener("change", () => updateContextUI());
targetInput?.addEventListener("change", () => updateContextUI());
companyInput?.addEventListener("change", () => updateContextUI());

testRefresh?.addEventListener("click", refreshAll);
testReset?.addEventListener("click", () => {
  resetDefaults();
  renderTestGrid();
});
testDocs?.addEventListener("click", () => {
  const target = document.getElementById("test-grid");
  if (target) {
    target.scrollIntoView({ behavior: "smooth", block: "start" });
  }
});
testSearch?.addEventListener("input", (event) => {
  testSearchKeyword = event.target.value || "";
  renderTestGrid();
});

expandAllBtn?.addEventListener("click", () => {
  document.querySelectorAll(".api-test-card").forEach((card) => setCardCollapsed(card, false));
});

collapseAllBtn?.addEventListener("click", () => {
  document.querySelectorAll(".api-test-card").forEach((card) => setCardCollapsed(card, true));
});

clearResponsesBtn?.addEventListener("click", () => {
  lastResponses.clear();
  lastRequests.clear();
  document.querySelectorAll(".validation-output").forEach((node) => {
    node.textContent = "尚未发送请求。";
  });
  document.querySelectorAll(".api-test-status").forEach((node) => {
    node.textContent = "未执行";
    node.dataset.status = "idle";
  });
  document.querySelectorAll(".api-test-run").forEach((node) => {
    node.textContent = "-";
  });
});

apiBaseInput?.addEventListener("change", (event) => {
  setApiBase(event.target.value.trim());
  refreshAll();
});

refreshBtn?.addEventListener("click", () => {
  const value = apiBaseInput.value.trim();
  setApiBase(value);
  refreshAll();
});

loginBtn?.addEventListener("click", () => {
  const next = encodeURIComponent(window.location.pathname + window.location.search);
  window.location.href = `./login.html?next=${next}`;
});

backBtn?.addEventListener("click", () => {
  window.location.href = "./index.html";
});

apiBaseInput.value = loadApiBase();
state.walletId = loadWalletId();
if (ensureLoggedIn()) {
  renderIdentity();
  resetDefaults();
  renderIntentGuide();
  renderTestFilters();
  refreshAll();
}
