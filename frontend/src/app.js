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
import {
  ping,
  fetchApps,
  fetchAppIntentDetails,
  updateAppIntents,
  fetchAppWorkflows,
  updateAppWorkflows,
  fetchPluginFiles,
  fetchPluginFile,
  updatePluginFile,
  fetchKBList,
  fetchKBStats,
  fetchKBDocuments,
  createKBDocument,
  updateKBDocument,
  deleteKBDocument,
  createKBConfig,
  updateKBConfig,
  deleteKBConfig,
  fetchIngestionLogs,
  fetchMemorySessions,
  fetchMemoryContexts,
  updateMemoryContext,
  fetchAuditLogs,
  fetchPrivateDBs,
  fetchPrivateDBSessions,
  createPrivateDB,
  bindPrivateDBSessions,
  unbindPrivateDBSession,
} from "./api.js";

const apiBaseInput = document.getElementById("api-base");
const refreshBtn = document.getElementById("refresh-btn");
const statusDot = document.getElementById("api-status-dot");
const statusText = document.getElementById("api-status-text");
const rolePill = document.getElementById("role-pill");
const walletIdDisplay = document.getElementById("wallet-id-display");
const backBtn = document.getElementById("back-btn");
const loginBtn = document.getElementById("login-btn");
const appSwitch = document.getElementById("app-switch");

const appTitle = document.getElementById("app-title");
const appHeading = document.getElementById("app-heading");
const appSummary = document.getElementById("app-summary");
const appNewDoc = document.getElementById("app-new-doc");
const appIngestion = document.getElementById("app-ingestion");
const appApiTest = document.getElementById("app-api-test");

const metricKbs = document.getElementById("metric-kbs");
const metricVectors = document.getElementById("metric-vectors");
const metricIngestion = document.getElementById("metric-ingestion");
const metricKbsTrend = document.getElementById("metric-kbs-trend");
const metricVectorsTrend = document.getElementById("metric-vectors-trend");
const metricIngestionTrend = document.getElementById("metric-ingestion-trend");

const kbTable = document.getElementById("kb-table");
const kbSearch = document.getElementById("kb-search");
const kbFilterToggle = document.getElementById("kb-filter-toggle");
const kbFilterPanel = document.getElementById("kb-filter-panel");
const schemaToggle = document.getElementById("kb-schema-toggle");
const schemaPanel = document.getElementById("kb-schema-panel");
const kbViewTabs = document.getElementById("kb-view-tabs");
const kbTabButtons = kbViewTabs ? Array.from(kbViewTabs.querySelectorAll(".tab-button")) : [];
const kbTabPanels = kbViewTabs
  ? Array.from((kbViewTabs.closest(".panel") || document).querySelectorAll(".tab-panel[data-tab-panel]"))
  : [];

const detailTitle = document.getElementById("kb-detail-title");
const detailSubtitle = document.getElementById("kb-detail-subtitle");
const detailCollection = document.getElementById("kb-detail-collection");
const detailDocs = document.getElementById("kb-detail-docs");
const detailChunks = document.getElementById("kb-detail-chunks");
const detailAccess = document.getElementById("kb-detail-access");
const detailLog = document.getElementById("kb-detail-log");

const chartBars = [
  document.getElementById("chart-bar-1"),
  document.getElementById("chart-bar-2"),
  document.getElementById("chart-bar-3"),
  document.getElementById("chart-bar-4"),
];

const docSubtitle = document.getElementById("doc-subtitle");
const docSearch = document.getElementById("doc-search");
const docRefresh = document.getElementById("doc-refresh");
const docTable = document.getElementById("doc-table");
const docPanel = document.getElementById("doc-panel");
const docPanelBody = document.getElementById("doc-panel-body");
const docToggle = document.getElementById("doc-toggle");
const docColumnsToggle = document.getElementById("doc-columns-toggle");
const docColumnsPanel = document.getElementById("doc-columns-panel");
const docExport = document.getElementById("doc-export");
const docPageSize = document.getElementById("doc-page-size");
const docPageInfo = document.getElementById("doc-page-info");
const docPrev = document.getElementById("doc-prev");
const docNext = document.getElementById("doc-next");
const docExportHint = document.getElementById("doc-export-hint");
const docSelectedCount = document.getElementById("doc-selected-count");
const docBulkExport = document.getElementById("doc-bulk-export");
const docBulkDelete = document.getElementById("doc-bulk-delete");
const docDataWalletFilter = document.getElementById("doc-data-wallet-filter");
const docPrivateDbFilter = document.getElementById("doc-private-db-filter");
const docSessionFilter = document.getElementById("doc-session-filter");
const docForm = document.getElementById("doc-form");
const docIdInput = document.getElementById("doc-id");
const docTextInput = document.getElementById("doc-text");
const docPropsInput = document.getElementById("doc-props");
const docReset = document.getElementById("doc-reset");
const docDelete = document.getElementById("doc-delete");
const docHint = document.getElementById("doc-hint");
const docDrawer = document.getElementById("doc-drawer");
const docDrawerBackdrop = document.getElementById("doc-drawer-backdrop");
const docDrawerClose = document.getElementById("drawer-close");
const drawerTitle = document.getElementById("drawer-title");
const drawerSubtitle = document.getElementById("drawer-subtitle");
const drawerDocId = document.getElementById("drawer-doc-id");
const drawerDocUpdated = document.getElementById("drawer-doc-updated");
const drawerDocCreated = document.getElementById("drawer-doc-created");
const drawerDocFields = document.getElementById("drawer-doc-fields");
const drawerDocMeta = document.getElementById("drawer-doc-meta");

const kbConfigForm = document.getElementById("kb-config-form");
const kbConfigNew = document.getElementById("kb-config-new");
const kbConfigSubtitle = document.getElementById("kb-config-subtitle");
const kbConfigKey = document.getElementById("kb-config-key");
const kbConfigType = document.getElementById("kb-config-type");
const kbConfigCollection = document.getElementById("kb-config-collection");
const kbConfigTextField = document.getElementById("kb-config-text-field");
const kbConfigTopk = document.getElementById("kb-config-topk");
const kbConfigWeight = document.getElementById("kb-config-weight");
const kbConfigAllowed = document.getElementById("kb-config-allowed");
const kbConfigSave = document.getElementById("kb-config-save");
const kbConfigDelete = document.getElementById("kb-config-delete");
const kbConfigHint = document.getElementById("kb-config-hint");
const kbSchemaTable = document.getElementById("kb-schema-table");
const kbSchemaAdd = document.getElementById("kb-schema-add");
const kbVectorFields = document.getElementById("kb-vector-fields");
const kbSystemFields = document.getElementById("kb-system-fields");
const kbSchemaHint = document.getElementById("kb-schema-hint");

const memoryWalletFilter = document.getElementById("memory-wallet-filter");
const memorySessionFilter = document.getElementById("memory-session-filter");
const memoryRefresh = document.getElementById("memory-refresh");
const memorySessionTable = document.getElementById("memory-session-table");
const memoryDetailTitle = document.getElementById("memory-detail-title");
const memoryDetailSubtitle = document.getElementById("memory-detail-subtitle");
const memoryDetailKey = document.getElementById("memory-detail-key");
const memoryDetailCount = document.getElementById("memory-detail-count");
const memoryDetailWallet = document.getElementById("memory-detail-wallet");
const memoryDetailSession = document.getElementById("memory-detail-session");
const memoryContextTable = document.getElementById("memory-context-table");
const memoryContextRefresh = document.getElementById("memory-context-refresh");
const memoryContextForm = document.getElementById("memory-context-form");
const memoryContextRole = document.getElementById("memory-context-role");
const memoryContextDesc = document.getElementById("memory-context-desc");
const memoryContextSave = document.getElementById("memory-context-save");
const memoryContextReset = document.getElementById("memory-context-reset");
const memoryContextHint = document.getElementById("memory-context-hint");
const memoryContextText = document.getElementById("memory-context-text");
const memoryDetailPanel = document.getElementById("memory-detail-panel");

const privateDbOwnerFilter = document.getElementById("private-db-owner-filter");
const privateDbRefresh = document.getElementById("private-db-refresh");
const privateDbTable = document.getElementById("private-db-table");
const privateDbDetailTitle = document.getElementById("private-db-detail-title");
const privateDbDetailSubtitle = document.getElementById("private-db-detail-subtitle");
const privateDbDetailId = document.getElementById("private-db-detail-id");
const privateDbDetailOwner = document.getElementById("private-db-detail-owner");
const privateDbDetailStatus = document.getElementById("private-db-detail-status");
const privateDbDetailCreated = document.getElementById("private-db-detail-created");
const privateDbSessionsList = document.getElementById("private-db-sessions-list");
const privateDbSessionsRefresh = document.getElementById("private-db-sessions-refresh");
const privateDbForm = document.getElementById("private-db-form");
const privateDbOwner = document.getElementById("private-db-owner");
const privateDbIdInput = document.getElementById("private-db-id");
const privateDbSessionsInput = document.getElementById("private-db-sessions");
const privateDbCreate = document.getElementById("private-db-create");
const privateDbBind = document.getElementById("private-db-bind");
const privateDbHint = document.getElementById("private-db-hint");

const auditEntityType = document.getElementById("audit-entity-type");
const auditAction = document.getElementById("audit-action");
const auditEntityId = document.getElementById("audit-entity-id");
const auditOperator = document.getElementById("audit-operator");
const auditRefresh = document.getElementById("audit-refresh");
const auditExport = document.getElementById("audit-export");
const auditTable = document.getElementById("audit-table");
const auditDetail = document.getElementById("audit-detail");
const auditHint = document.getElementById("audit-hint");

const navItems = Array.from(document.querySelectorAll("[data-nav]"));
const navActions = Array.from(document.querySelectorAll("[data-action]"));
const sidebarToggle = document.getElementById("sidebar-toggle");
const layoutRoot = document.querySelector(".layout");

const intentTable = document.getElementById("intent-table");
const intentAdd = document.getElementById("intent-add");
const intentSave = document.getElementById("intent-save");
const intentReset = document.getElementById("intent-reset");
const intentHint = document.getElementById("intent-hint");
const intentRefresh = document.getElementById("intent-refresh");

const workflowTable = document.getElementById("workflow-table");
const workflowAdd = document.getElementById("workflow-add");
const workflowSave = document.getElementById("workflow-save");
const workflowReset = document.getElementById("workflow-reset");
const workflowHint = document.getElementById("workflow-hint");
const workflowRefresh = document.getElementById("workflow-refresh");

const pluginFileTable = document.getElementById("plugin-file-table");
const pluginRefresh = document.getElementById("plugin-refresh");
const pluginNewPrompt = document.getElementById("plugin-new-prompt");
const pluginOpenPipeline = document.getElementById("plugin-open-pipeline");
const pluginEditor = document.getElementById("plugin-editor");
const pluginSave = document.getElementById("plugin-save");
const pluginReset = document.getElementById("plugin-reset");
const pluginHint = document.getElementById("plugin-hint");
const pluginFilePath = document.getElementById("plugin-file-path");
const pluginFileKind = document.getElementById("plugin-file-kind");
const pluginFileSize = document.getElementById("plugin-file-size");
const pluginFileUpdated = document.getElementById("plugin-file-updated");
const pluginEditorTitle = document.getElementById("plugin-editor-title");
const pluginEditorSubtitle = document.getElementById("plugin-editor-subtitle");

const timeline = document.getElementById("ingestion-timeline");
const ingestionExport = document.getElementById("ingestion-export");
const ingestionHint = document.getElementById("ingestion-hint");

let currentAppId = new URLSearchParams(window.location.search).get("app_id");
let kbSchemaDraft = [];
let intentDraft = [];
let intentSnapshot = [];
let workflowDraft = [];
let workflowSnapshot = [];
const RESERVED_USER_UPLOAD_FIELDS = [
  "wallet_id",
  "private_db_id",
  "resume_id",
  "jd_id",
  "source_url",
  "file_type",
  "metadata_json",
  "allowed_apps",
];

const SIDEBAR_COLLAPSED_KEY = "rag_sidebar_collapsed";

const KB_TYPE_LABELS = {
  public_kb: "公共知识库",
  static_kb: "公共知识库",
  user_upload: "用户私有数据库",
};

function normalizeKbType(value) {
  const raw = String(value || "").trim();
  if (!raw) return "public_kb";
  if (raw === "static_kb") return "public_kb";
  return raw;
}

function formatKbType(value) {
  const key = normalizeKbType(value);
  return KB_TYPE_LABELS[key] || key;
}

function isUserUploadType(value) {
  return normalizeKbType(value) === "user_upload";
}

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
  if (memoryWalletFilter && !memoryWalletFilter.value) {
    memoryWalletFilter.value = "";
  }
  toggleAdminOnly();
}

function updateUrl(appId) {
  const url = new URL(window.location.href);
  url.searchParams.set("app_id", appId);
  history.replaceState({}, "", url.toString());
}

function renderAppSwitch(apps) {
  appSwitch.innerHTML = apps
    .map((app) => `<option value="${app.app_id}">${app.app_id}</option>`)
    .join("");
  appSwitch.disabled = !apps.length;
  if (currentAppId) {
    appSwitch.value = currentAppId;
  }
}


function applyData(data) {
  state.apps = data.apps || [];
  state.knowledgeBases = data.knowledgeBases || [];
  state.ingestion = data.ingestion || [];
  state.ingestionRaw = data.ingestionRaw || [];
  state.vectors = data.vectors || 0;

  const appInfo = data.appInfo || null;
  const appLabel = appInfo ? appInfo.app_id : "未知应用";
  const statusLabel = appInfo ? appInfo.status || "未知" : "未知";

  appTitle.textContent = appLabel;
  appHeading.textContent = `${appLabel} 控制台`;
  appSummary.textContent = appInfo
    ? `状态 ${statusLabel} · 插件 ${appInfo.has_plugin ? "启用" : "缺失"}`
    : "注册表中未找到该应用。";

  metricKbs.textContent = state.knowledgeBases.length;
  metricVectors.textContent = new Intl.NumberFormat().format(state.vectors);
  metricIngestion.textContent = state.ingestionRaw.length;
  metricKbsTrend.textContent = `状态 ${statusLabel}`;
  metricVectorsTrend.textContent = state.knowledgeBases.length
    ? `${state.knowledgeBases.length} 个知识库`
    : "暂无知识库";
  metricIngestionTrend.textContent = state.ingestionRaw[0]?.created_at || "-";

  renderKbTable();
  renderKbFilters();
  renderTimeline();

  if (state.selectedKb) {
    const exists = state.knowledgeBases.some((kb) => kb.id === state.selectedKb);
    if (exists) {
      selectKb(state.selectedKb);
      return;
    }
    state.selectedKb = null;
  }
  if (state.knowledgeBases.length) {
    selectKb(state.knowledgeBases[0].id);
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
    const fallbackApp = currentAppId || mockData.apps[0]?.app_id || "unknown";
    currentAppId = fallbackApp;
    updateUrl(currentAppId);
    renderAppSwitch(mockData.apps);
    const fallbackKbs = mockData.knowledgeBases.filter((kb) => kb.app_id === currentAppId);
    const totalVectors = fallbackKbs.reduce((sum, kb) => sum + (kb.chunks || 0), 0);
    applyData({
      apps: mockData.apps,
      appInfo: mockData.apps.find((app) => app.app_id === currentAppId),
      knowledgeBases: fallbackKbs,
      ingestion: mockData.ingestion,
      ingestionRaw: mockData.ingestion,
      vectors: totalVectors,
    });
    state.memorySessions = [];
    state.memorySessionTotal = 0;
    state.memoryContexts = [];
    state.memoryContextTotal = 0;
    state.selectedMemoryKey = null;
    state.selectedMemoryContextId = null;
    renderMemorySessionTable();
    renderMemoryContextTable();
    updateMemoryDetail(null);
    resetMemoryContextForm(null);
    state.auditLogs = [];
    state.selectedAuditId = null;
    renderAuditTable();
    updateAuditDetail(null);
    intentDraft = [];
    intentSnapshot = [];
    workflowDraft = [];
    workflowSnapshot = [];
    renderIntentTable();
    renderWorkflowTable();
    state.privateDbs = [];
    state.privateDbSessions = [];
    state.selectedPrivateDbId = null;
    renderPrivateDbTable();
    updatePrivateDbDetail(null);
    renderPrivateDbSessions();
    state.pluginFiles = [];
    state.selectedPluginPath = null;
    state.pluginFileMeta = null;
    state.pluginContentSnapshot = "";
    renderPluginFileTable();
    updatePluginEditorInfo(null);
    return;
  }

  try {
    const walletId = state.walletId;
    const [apps, kbList] = await Promise.all([fetchApps(walletId), fetchKBList(walletId)]);
    if (!currentAppId && apps.length) {
      currentAppId = apps[0].app_id;
      updateUrl(currentAppId);
    }
    renderAppSwitch(apps || []);

    const appInfo = (apps || []).find((app) => app.app_id === currentAppId) || null;
    if (!appInfo) {
      applyData({ apps, appInfo: null, knowledgeBases: [], ingestion: [], ingestionRaw: [], vectors: 0 });
      intentDraft = [];
      intentSnapshot = [];
      workflowDraft = [];
      workflowSnapshot = [];
      renderIntentTable();
      renderWorkflowTable();
      state.pluginFiles = [];
      state.selectedPluginPath = null;
      state.pluginFileMeta = null;
      state.pluginContentSnapshot = "";
      renderPluginFileTable();
      updatePluginEditorInfo(null);
      return;
    }

    const appKbs = (kbList || []).filter((kb) => kb.app_id === currentAppId);
    const kbStats = await Promise.all(
      appKbs.map(async (kb) => {
        try {
          const stat = await fetchKBStats(kb.app_id, kb.kb_key, walletId);
          return {
            key: `${kb.app_id}:${kb.kb_key}`,
            count: stat.total_count,
            chunks: stat.chunk_count,
          };
        } catch (err) {
          return { key: `${kb.app_id}:${kb.kb_key}`, count: "-", chunks: "-" };
        }
      })
    );

    const statsMap = new Map(kbStats.map((item) => [item.key, item]));
    const mappedKbs = appKbs.map((kb) => {
      const id = `${kb.app_id}:${kb.kb_key}`;
      const stat = statsMap.get(id) || { count: "-", chunks: "-" };
      const schema = Array.isArray(kb.schema) ? kb.schema : [];
      const vectorFields = Array.isArray(kb.vector_fields) ? kb.vector_fields : [];
      const normalizedType = normalizeKbType(kb.kb_type || kb.type || "");
      return {
        id,
        app_id: kb.app_id,
        kb_key: kb.kb_key,
        text_field: kb.text_field || "text",
        name: kb.kb_key,
        type: normalizedType,
        collection: kb.collection || "-",
        top_k: kb.top_k ?? 0,
        weight: kb.weight ?? 0,
        use_allowed_apps_filter: Boolean(kb.use_allowed_apps_filter),
        schema,
        vector_fields: vectorFields,
        docs: stat.count,
        chunks: stat.chunks,
        owner: kb.app_id,
        access: isUserUploadType(normalizedType) ? "restricted" : "public",
        updated_at: kb.status ? `应用 ${kb.status}` : "未知",
        log: [
          `类型 ${formatKbType(normalizedType)}`,
          `Top_k ${kb.top_k ?? "-"}`,
          `Weight ${kb.weight ?? "-"}`,
          kb.use_allowed_apps_filter ? "启用应用过滤" : "未启用应用过滤",
          schema.length ? `Schema 字段 ${schema.length}` : "Schema 未配置",
          vectorFields.length ? `向量字段 ${vectorFields.join(", ")}` : "向量字段 未配置",
        ],
        histogram: [40, 56, 32, 48],
      };
    });

    const totalVectors = mappedKbs
      .map((kb) => (typeof kb.chunks === "number" ? kb.chunks : 0))
      .reduce((a, b) => a + b, 0);

    const ingestionLogs = await fetchIngestionLogs({ appId: currentAppId, walletId });
    const ingestionRaw = (ingestionLogs && ingestionLogs.items) || [];

    applyData({
      apps,
      appInfo,
      knowledgeBases: mappedKbs,
      vectors: totalVectors,
      ingestion: mapIngestion(ingestionLogs) || [],
      ingestionRaw,
    });
    await loadPrivateDbs();
    await loadAuditLogs();
    await loadIntentConfigs();
    await loadWorkflowConfigs();
    await loadMemorySessions();
    await loadPluginFiles();
  } catch (err) {
    applyData({ apps: [], appInfo: null, knowledgeBases: [], ingestion: [], ingestionRaw: [], vectors: 0 });
    state.memorySessions = [];
    state.memorySessionTotal = 0;
    state.memoryContexts = [];
    state.memoryContextTotal = 0;
    state.selectedMemoryKey = null;
    state.selectedMemoryContextId = null;
    renderMemorySessionTable();
    renderMemoryContextTable();
    updateMemoryDetail(null);
    resetMemoryContextForm(null);
    state.auditLogs = [];
    state.selectedAuditId = null;
    renderAuditTable();
    updateAuditDetail(null);
    intentDraft = [];
    intentSnapshot = [];
    workflowDraft = [];
    workflowSnapshot = [];
    renderIntentTable();
    renderWorkflowTable();
    state.privateDbs = [];
    state.privateDbSessions = [];
    state.selectedPrivateDbId = null;
    renderPrivateDbTable();
    updatePrivateDbDetail(null);
    renderPrivateDbSessions();
    state.pluginFiles = [];
    state.selectedPluginPath = null;
    state.pluginFileMeta = null;
    state.pluginContentSnapshot = "";
    renderPluginFileTable();
    updatePluginEditorInfo(null);
  }
}

function renderKbTable() {
  const query = (kbSearch.value || "").toLowerCase();
  const filters = state.kbFilters;
  const rows = state.knowledgeBases
    .filter((kb) => {
      if (!query) return true;
      return (
        kb.name.toLowerCase().includes(query) ||
        kb.collection.toLowerCase().includes(query) ||
        kb.owner.toLowerCase().includes(query)
      );
    })
    .filter((kb) => {
      const ownerMatch = !filters.owners.length || filters.owners.includes(kb.owner);
      const typeMatch = !filters.types.length || filters.types.includes(kb.type);
      const accessMatch = !filters.access.length || filters.access.includes(kb.access);
      return ownerMatch && typeMatch && accessMatch;
    });

  if (!rows.length) {
    kbTable.innerHTML = renderEmptyState(
      "暂无知识库",
      "当前应用还没有可用的知识库，请先完成应用注册与数据摄取。"
    );
    resetKbConfigForm();
    return;
  }

  const header = `
    <div class="table-row header">
      <div>名称</div>
      <div>类型</div>
      <div>文档数</div>
      <div>向量数</div>
      <div>集合</div>
      <div>权限</div>
    </div>
  `;

  const body = rows
    .map((kb) => {
      const active = state.selectedKb === kb.id ? "active" : "";
      const badge = kb.access === "restricted" ? "私有" : "公共";
      const typeLabel = formatKbType(kb.type);
      return `
        <div class="table-row ${active}" data-kb="${kb.id}">
          <div>
            <strong>${kb.name}</strong>
            <div class="badge">${kb.owner}</div>
          </div>
          <div>${escapeHtml(typeLabel)}</div>
          <div>${kb.docs}</div>
          <div>${kb.chunks}</div>
          <div>${kb.collection}</div>
          <div>${badge}</div>
        </div>
      `;
    })
    .join("");

  kbTable.innerHTML = header + body;

  kbTable.querySelectorAll(".table-row[data-kb]").forEach((row) => {
    row.addEventListener("click", () => selectKb(row.dataset.kb));
  });
}

function renderKbFilters() {
  if (!kbFilterPanel) return;
  const owners = Array.from(new Set(state.knowledgeBases.map((kb) => kb.owner).filter(Boolean))).sort();
  const types = Array.from(new Set(state.knowledgeBases.map((kb) => kb.type).filter(Boolean))).sort();
  const access = Array.from(new Set(state.knowledgeBases.map((kb) => kb.access).filter(Boolean))).sort();
  const filters = state.kbFilters;

  if (!owners.length && !types.length && !access.length) {
    kbFilterPanel.innerHTML = "<div class=\"detail-label\">暂无可用筛选项。</div>";
    return;
  }

  const buildGroup = (label, items, selected, key) => {
    if (!items.length) return "";
    const chips = items
      .map((item) => {
        const checked = selected.includes(item) ? "checked" : "";
        const label = key === "types" ? formatKbType(item) : item;
        return `<label class="filter-chip"><input type="checkbox" data-filter="${key}" value="${item}" ${checked} />${escapeHtml(label)}</label>`;
      })
      .join("");
    return `<div class="filter-group"><span>${label}</span>${chips}</div>`;
  };

  kbFilterPanel.innerHTML = `
    ${buildGroup("应用", owners, filters.owners, "owners")}
    ${buildGroup("类型", types, filters.types, "types")}
    ${buildGroup("权限", access, filters.access, "access")}
    <div class="filter-group">
      <button class="ghost" id="kb-filter-clear">清空筛选</button>
    </div>
  `;

  kbFilterPanel.querySelectorAll("input[data-filter]").forEach((input) => {
    input.addEventListener("change", () => {
      const next = { owners: [], types: [], access: [] };
      kbFilterPanel.querySelectorAll("input[data-filter]:checked").forEach((checked) => {
        const key = checked.dataset.filter;
        if (key && next[key]) {
          next[key].push(checked.value);
        }
      });
      state.kbFilters = next;
      renderKbTable();
    });
  });

  const clearBtn = kbFilterPanel.querySelector("#kb-filter-clear");
  if (clearBtn) {
    clearBtn.addEventListener("click", () => {
      state.kbFilters = { owners: [], types: [], access: [] };
      renderKbFilters();
      renderKbTable();
    });
  }
}

async function selectKb(id) {
  const kb = state.knowledgeBases.find((item) => item.id === id);
  if (!kb) return;
  state.selectedKb = id;
  state.docPageOffset = 0;
  state.docVisibleColumns = loadDocColumnPreferences(kb);
  state.docSort = null;
  state.selectedDocIds = new Set();
  closeDocDrawer();
  resetDocForm({ render: false });
  if (docColumnsPanel) {
    docColumnsPanel.classList.add("hidden");
  }
  if (docColumnsToggle) {
    docColumnsToggle.textContent = "字段";
  }
  renderKbTable();
  if (schemaPanel) {
    schemaPanel.classList.add("hidden");
    schemaToggle.textContent = "字段结构";
  }

  detailTitle.textContent = kb.name;
  const scopeLabel = isUserUploadType(kb.type) ? "用户隔离" : "公共共享";
  detailSubtitle.textContent = `更新 ${kb.updated_at} · 应用 ${kb.owner} · ${scopeLabel}`;
  detailCollection.textContent = kb.collection;
  detailDocs.textContent = kb.docs;
  detailChunks.textContent = kb.chunks;
  detailAccess.textContent = kb.access === "restricted" ? "用户私有数据库（隔离）" : "公共知识库（共享）";
  detailLog.innerHTML = kb.log.map((line) => `> ${line}`).join("<br>");

  kb.histogram.forEach((value, index) => {
    const height = Math.min(100, Math.max(12, value));
    chartBars[index].style.height = `${height}%`;
  });

  setKbConfigForm(kb);
  await loadDocuments();
}

async function loadDocuments() {
  const kb = getSelectedKb();
  if (!kb) {
    docSubtitle.textContent = "请选择知识库加载文档，点击行查看详情。";
    state.documents = [];
    state.docTotal = 0;
    state.docColumns = [];
    state.docVisibleColumns = [];
    state.selectedDocIds = new Set();
    state.docSort = null;
    renderDocTable();
    renderDocColumnsPanel();
    renderDocToolbar();
    resetDocForm({ render: false });
    updateDocDrawerMeta(null);
    return;
  }

  if (docExportHint) {
    docExportHint.textContent = "";
  }
  docSubtitle.textContent = `集合 ${kb.collection} · 文本字段 ${kb.text_field} · 点击行查看详情`;
  try {
    const { dataWalletId, privateDbId, sessionId } = getDocFilters();
    if (sessionId && !dataWalletId) {
      if (docExportHint) {
        docExportHint.textContent = "使用 session_id 过滤时需先填写业务用户 wallet_id。";
      }
      return;
    }
    const res = await fetchKBDocuments(
      kb.app_id,
      kb.kb_key,
      state.docPageSize,
      state.docPageOffset,
      state.walletId,
      { dataWalletId, privateDbId, sessionId }
    );
    state.documents = res.items || [];
    state.docTotal = res.total ?? 0;
    const pageCount = state.docTotal ? Math.ceil(state.docTotal / state.docPageSize) : 0;
    const maxOffset = pageCount ? (pageCount - 1) * state.docPageSize : 0;
    if (state.docPageOffset > maxOffset) {
      state.docPageOffset = maxOffset;
      await loadDocuments();
      return;
    }
    state.docColumns = buildDocColumns(state.documents, kb.text_field);
    state.docVisibleColumns = normalizeVisibleColumns(state.docVisibleColumns, kb.text_field);
    ensureSelectedDocIds();
    pruneDocSelection(state.documents);
    const labelColumns = state.docColumns.length ? state.docColumns : ["id", kb.text_field || "text"];
    const columnsLabel =
      labelColumns.length > 6
        ? `${labelColumns.slice(0, 6).join(", ")} ...`
        : labelColumns.join(", ");
    const filterNotes = [];
    if (dataWalletId) filterNotes.push(`data_wallet ${dataWalletId}`);
    if (privateDbId) filterNotes.push(`private_db ${privateDbId}`);
    if (sessionId) filterNotes.push(`session ${sessionId}`);
    const filterLabel = filterNotes.length ? ` · 过滤: ${filterNotes.join(" / ")}` : "";
    docSubtitle.textContent = `集合 ${kb.collection} · 文本字段 ${kb.text_field} · 总数 ${state.docTotal} · 列: ${columnsLabel}${filterLabel} · 点击行查看详情`;
    renderDocTable();
    renderDocColumnsPanel();
    renderDocToolbar();
    syncDocSelection();
  } catch (err) {
    docHint.textContent = `加载失败: ${err.message}`;
    state.documents = [];
    state.docTotal = 0;
    state.docColumns = [];
    state.docVisibleColumns = [];
    state.selectedDocIds = new Set();
    state.docSort = null;
    renderDocTable();
    renderDocColumnsPanel();
    renderDocToolbar();
    resetDocForm({ render: false });
    updateDocDrawerMeta(null);
  }
}

function getFilteredDocs() {
  const query = (docSearch.value || "").toLowerCase();
  const rows = state.documents.filter((doc) => {
    if (!query) return true;
    const text = JSON.stringify(doc.properties || {}).toLowerCase();
    return doc.id.toLowerCase().includes(query) || text.includes(query);
  });
  const kb = getSelectedKb();
  const textField = kb?.text_field || "text";
  return sortDocuments(rows, textField);
}

function sortDocuments(rows, textField) {
  if (!state.docSort || !state.docSort.key) return rows;
  const { key, direction } = state.docSort;
  const dir = direction === "desc" ? -1 : 1;
  return rows.sort((a, b) => {
    const left = normalizeSortValue(getDocSortValue(a, key, textField));
    const right = normalizeSortValue(getDocSortValue(b, key, textField));

    if (left == null && right == null) return 0;
    if (left == null) return 1;
    if (right == null) return -1;

    if (typeof left === "number" && typeof right === "number") {
      return (left - right) * dir;
    }
    return String(left).localeCompare(String(right)) * dir;
  });
}

function getDocSortValue(doc, key, textField) {
  if (key === "id") return doc.id;
  if (key === textField) return getDocText(doc);
  return doc.properties ? doc.properties[key] : undefined;
}

function normalizeSortValue(value) {
  if (value === null || value === undefined) return null;
  if (typeof value === "number") return value;
  if (typeof value === "boolean") return value ? 1 : 0;
  if (typeof value === "string") return value.toLowerCase();
  try {
    return JSON.stringify(value);
  } catch (err) {
    return String(value);
  }
}

function toggleDocSort(key) {
  if (!key) return;
  if (state.docSort && state.docSort.key === key) {
    state.docSort.direction = state.docSort.direction === "asc" ? "desc" : "asc";
  } else {
    state.docSort = { key, direction: "asc" };
  }
  renderDocTable();
}

function renderDocTable() {
  const rows = getFilteredDocs();

  const kb = getSelectedKb();
  const textField = kb?.text_field || "text";
  const columns = getVisibleDocColumns(textField);
  const columnTemplate = buildDocGridTemplate(columns.length, true);
  ensureSelectedDocIds();
  pruneDocSelection(rows);

  if (!rows.length) {
    docTable.innerHTML = renderEmptyState("暂无文档", "当前集合没有可展示的数据，请先写入或导入内容。");
    updateDocSelectionSummary(rows);
    return;
  }

  const fieldTypes = collectDocFieldTypes(rows, textField);
  const header = `
    <div class="table-row header" style="--doc-columns: ${columnTemplate}">
      ${renderDocSelectHeaderCell(rows)}
      ${columns.map((col) => renderDocHeaderCell(col, fieldTypes, textField)).join("")}
    </div>
  `;

  const body = rows
    .map((doc) => {
      const active = state.selectedDocId === doc.id ? "active" : "";
      const checked = state.selectedDocIds.has(doc.id) ? "checked" : "";
      const safeDocId = escapeHtml(doc.id);
      const selectCell = `<div class="doc-select"><input type="checkbox" data-doc-select="${safeDocId}" ${checked} /></div>`;
      const cells = columns
        .map((col) => {
          if (col === "id") {
            return `<div class="cell-id" title="${safeDocId}">${safeDocId}</div>`;
          }
          const value = doc.properties ? doc.properties[col] : undefined;
          return `<div>${renderCell(value)}</div>`;
        })
        .join("");
      return `
        <div class="table-row ${active}" data-doc="${doc.id}" style="--doc-columns: ${columnTemplate}">
          ${selectCell}
          ${cells}
        </div>
      `;
    })
    .join("");

  docTable.innerHTML = header + body;

  const selectAll = docTable.querySelector("#doc-select-all");
  if (selectAll) {
    const selectedCount = rows.filter((doc) => state.selectedDocIds.has(doc.id)).length;
    const allSelected = rows.length > 0 && selectedCount === rows.length;
    const anySelected = selectedCount > 0 && !allSelected;
    selectAll.checked = allSelected;
    selectAll.indeterminate = anySelected;
    selectAll.disabled = rows.length === 0;
    selectAll.addEventListener("change", () => toggleSelectAllRows(rows, selectAll.checked));
  }

  docTable.querySelectorAll("input[data-doc-select]").forEach((input) => {
    input.addEventListener("click", (event) => event.stopPropagation());
    input.addEventListener("change", (event) => {
      toggleDocSelection(event.target.dataset.docSelect, event.target.checked);
    });
  });

  docTable.querySelectorAll(".header-button[data-sort]").forEach((button) => {
    button.addEventListener("click", () => toggleDocSort(button.dataset.sort));
  });

  docTable.querySelectorAll(".table-row[data-doc]").forEach((row) => {
    row.addEventListener("click", (event) => {
      if (event.target.closest("input")) return;
      selectDoc(row.dataset.doc);
    });
  });

  updateDocSelectionSummary(rows);
}

function ensureSelectedDocIds() {
  if (!(state.selectedDocIds instanceof Set)) {
    state.selectedDocIds = new Set(state.selectedDocIds || []);
  }
}

function pruneDocSelection(rows) {
  ensureSelectedDocIds();
  const allowed = new Set(rows.map((doc) => doc.id));
  Array.from(state.selectedDocIds).forEach((docId) => {
    if (!allowed.has(docId)) {
      state.selectedDocIds.delete(docId);
    }
  });
}

function updateDocSelectionSummary(rows) {
  ensureSelectedDocIds();
  const selectedCount = state.selectedDocIds.size;
  if (docSelectedCount) {
    docSelectedCount.textContent = String(selectedCount);
  }
  if (docBulkExport) {
    docBulkExport.disabled = selectedCount === 0;
  }
  if (docBulkDelete) {
    docBulkDelete.disabled = selectedCount === 0;
  }
  const selectAll = docTable ? docTable.querySelector("#doc-select-all") : null;
  if (selectAll) {
    const visibleCount = rows.length;
    const selectedVisible = rows.filter((doc) => state.selectedDocIds.has(doc.id)).length;
    const allSelected = visibleCount > 0 && selectedVisible === visibleCount;
    const anySelected = selectedVisible > 0 && !allSelected;
    selectAll.checked = allSelected;
    selectAll.indeterminate = anySelected;
    selectAll.disabled = visibleCount === 0;
  }
  if (docExportHint && rows.length === 0) {
    docExportHint.textContent = "";
  }
}

function toggleDocSelection(docId, checked) {
  ensureSelectedDocIds();
  if (checked) {
    state.selectedDocIds.add(docId);
  } else {
    state.selectedDocIds.delete(docId);
  }
  updateDocSelectionSummary(getFilteredDocs());
}

function toggleSelectAllRows(rows, checked) {
  ensureSelectedDocIds();
  rows.forEach((doc) => {
    if (checked) {
      state.selectedDocIds.add(doc.id);
    } else {
      state.selectedDocIds.delete(doc.id);
    }
  });
  renderDocTable();
}

function collectDocFieldTypes(rows, textField) {
  const map = new Map();
  rows.forEach((doc) => {
    addFieldType(map, "id", doc.id);
    const props = doc.properties || {};
    Object.entries(props).forEach(([key, value]) => {
      addFieldType(map, key, value);
    });
    if (textField && props[textField] === undefined) {
      addFieldType(map, textField, getDocText(doc));
    }
  });
  return map;
}

function addFieldType(map, key, value) {
  const entry = map.get(key) || new Set();
  entry.add(normalizeSchemaType(value));
  map.set(key, entry);
}

function formatTypeHint(types) {
  if (!types.length) {
    return { label: "-", title: "未知" };
  }
  if (types.length === 1) {
    return { label: types[0], title: types[0] };
  }
  return { label: "混合", title: types.join(" / ") };
}

function renderDocSelectHeaderCell(rows) {
  const disabled = rows.length === 0 ? "disabled" : "";
  return `<div class="doc-select"><input type="checkbox" id="doc-select-all" ${disabled} /></div>`;
}

function renderDocHeaderCell(col, fieldTypes) {
  const types = fieldTypes.get(col) ? Array.from(fieldTypes.get(col)) : [];
  const hint = formatTypeHint(types);
  const isSorted = state.docSort && state.docSort.key === col;
  const direction = isSorted ? state.docSort.direction : "";
  const indicator = direction ? `<span class="sort-indicator">${direction.toUpperCase()}</span>` : "";
  const label = col === "id" ? "ID" : escapeHtml(col);
  return `
    <div class="header-cell">
      <button class="header-button ${isSorted ? "active" : ""}" data-sort="${escapeHtml(col)}">
        <span>${label}</span>
        ${indicator}
      </button>
      <span class="type-pill" title="${escapeHtml(hint.title)}">${escapeHtml(hint.label)}</span>
    </div>
  `;
}

function renderEmptyState(title, subtitle) {
  return `
    <div class="empty-state">
      <div class="empty-illustration" aria-hidden="true">
        <svg viewBox="0 0 120 90" role="img" aria-hidden="true">
          <defs>
            <linearGradient id="emptyFill" x1="0" x2="1" y1="0" y2="1">
              <stop offset="0%" stop-color="#2b6ff7" stop-opacity="0.2" />
              <stop offset="100%" stop-color="#5bb3ff" stop-opacity="0.4" />
            </linearGradient>
          </defs>
          <rect x="18" y="18" width="84" height="54" rx="10" fill="url(#emptyFill)" />
          <rect x="28" y="30" width="64" height="6" rx="3" fill="#2b6ff7" opacity="0.6" />
          <rect x="28" y="42" width="44" height="6" rx="3" fill="#2b6ff7" opacity="0.4" />
          <rect x="28" y="54" width="54" height="6" rx="3" fill="#2b6ff7" opacity="0.3" />
        </svg>
      </div>
      <div class="empty-title">${escapeHtml(title)}</div>
      <div class="empty-subtitle">${escapeHtml(subtitle)}</div>
    </div>
  `;
}

function getAvailableDocColumns(textField) {
  const fallback = ["id", textField || "text"];
  return state.docColumns.length ? state.docColumns : fallback;
}

function getDocColumnStorageKey(kb) {
  if (!kb) return "rag_doc_columns:unknown";
  return `rag_doc_columns:${kb.app_id}:${kb.kb_key}`;
}

function loadDocColumnPreferences(kb) {
  if (!kb) return [];
  try {
    const raw = localStorage.getItem(getDocColumnStorageKey(kb));
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch (err) {
    return [];
  }
}

function saveDocColumnPreferences(kb, columns) {
  if (!kb) return;
  try {
    localStorage.setItem(getDocColumnStorageKey(kb), JSON.stringify(columns));
  } catch (err) {
    // Ignore storage errors to avoid breaking the UI.
  }
}

function normalizeVisibleColumns(columns, textField) {
  const available = getAvailableDocColumns(textField);
  const base = ["id", textField || "text"];
  const filtered = (columns || []).filter((col) => available.includes(col));
  const merged = [...base, ...filtered].filter((col, index, arr) => arr.indexOf(col) === index);
  return merged.length ? merged : available;
}

function getVisibleDocColumns(textField) {
  state.docVisibleColumns = normalizeVisibleColumns(state.docVisibleColumns, textField);
  return state.docVisibleColumns.length ? state.docVisibleColumns : getAvailableDocColumns(textField);
}

function renderDocColumnsPanel() {
  if (!docColumnsPanel) return;
  const kb = getSelectedKb();
  const textField = kb?.text_field || "text";
  const columns = getAvailableDocColumns(textField);

  if (!columns.length) {
    docColumnsPanel.innerHTML = "<div class=\"detail-label\">暂无字段信息。</div>";
    return;
  }

  const visible = new Set(getVisibleDocColumns(textField));
  const base = new Set(["id", textField || "text"]);

  const chips = columns
    .map((col) => {
      const safeCol = escapeHtml(col);
      const checked = visible.has(col) ? "checked" : "";
      const disabled = base.has(col) ? "disabled" : "";
      return `<label class="filter-chip"><input type="checkbox" data-col="${safeCol}" ${checked} ${disabled} />${safeCol}</label>`;
    })
    .join("");

  docColumnsPanel.innerHTML = `
    <div class="filter-group">
      <span>列</span>
      ${chips}
    </div>
    <div class="filter-group">
      <button class="ghost" id="doc-columns-reset">恢复默认</button>
    </div>
  `;

  docColumnsPanel.querySelectorAll("input[data-col]").forEach((input) => {
    input.addEventListener("change", () => {
      const selected = [];
      docColumnsPanel.querySelectorAll("input[data-col]:checked").forEach((checked) => {
        selected.push(checked.dataset.col);
      });
      state.docVisibleColumns = normalizeVisibleColumns(selected, textField);
      saveDocColumnPreferences(kb, state.docVisibleColumns);
      renderDocTable();
    });
  });

  const resetBtn = docColumnsPanel.querySelector("#doc-columns-reset");
  if (resetBtn) {
    resetBtn.addEventListener("click", () => {
      state.docVisibleColumns = normalizeVisibleColumns([], textField);
      saveDocColumnPreferences(kb, state.docVisibleColumns);
      renderDocColumnsPanel();
      renderDocTable();
    });
  }
}

function renderDocToolbar() {
  if (!docPageInfo || !docPrev || !docNext) return;
  const total = state.docTotal || 0;
  const size = state.docPageSize || 20;
  const offset = state.docPageOffset || 0;
  const pageCount = total ? Math.ceil(total / size) : 0;
  const current = total ? Math.floor(offset / size) + 1 : 0;

  docPageInfo.textContent = total ? `第 ${current}/${pageCount} 页 · ${total} 条` : "暂无数据";
  docPrev.disabled = offset <= 0;
  docNext.disabled = offset + size >= total;
}

function updateDocPageSize(size) {
  state.docPageSize = size;
  state.docPageOffset = 0;
  loadDocuments();
}

function updateDocPageOffset(offset) {
  state.docPageOffset = Math.max(0, offset);
  loadDocuments();
}

function toggleDocColumnsPanel() {
  if (!docColumnsPanel || !docColumnsToggle) return;
  const isHidden = docColumnsPanel.classList.contains("hidden");
  docColumnsPanel.classList.toggle("hidden");
  docColumnsToggle.textContent = isHidden ? "收起字段" : "字段";
}

function exportDocuments() {
  const rows = getFilteredDocs();
  if (!rows.length) {
    if (docExportHint) {
      docExportHint.textContent = "没有可导出的文档。";
    }
    return;
  }
  if (docExportHint) {
    docExportHint.textContent = "";
  }
  const blob = new Blob([JSON.stringify(rows, null, 2)], {
    type: "application/json",
  });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `documents-${Date.now()}.json`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
  if (docExportHint) {
    docExportHint.textContent = `已导出 ${rows.length} 条文档。`;
  }
}

function getSelectedDocs() {
  ensureSelectedDocIds();
  return getFilteredDocs().filter((doc) => state.selectedDocIds.has(doc.id));
}

function exportSelectedDocuments() {
  const rows = getSelectedDocs();
  if (!rows.length) {
    if (docExportHint) {
      docExportHint.textContent = "请先选择要导出的文档。";
    }
    return;
  }
  if (docExportHint) {
    docExportHint.textContent = "";
  }
  const blob = new Blob([JSON.stringify(rows, null, 2)], {
    type: "application/json",
  });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `documents-selected-${Date.now()}.json`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
  if (docExportHint) {
    docExportHint.textContent = `已导出 ${rows.length} 条已选文档。`;
  }
}

async function deleteSelectedDocuments() {
  const kb = getSelectedKb();
  if (!kb) {
    if (docExportHint) {
      docExportHint.textContent = "请先选择知识库。";
    }
    return;
  }
  const rows = getSelectedDocs();
  if (!rows.length) {
    if (docExportHint) {
      docExportHint.textContent = "请先选择要删除的文档。";
    }
    return;
  }
  const confirmed = window.confirm(`确认删除 ${rows.length} 条文档？此操作不可撤销。`);
  if (!confirmed) return;

  if (docExportHint) {
    docExportHint.textContent = `正在删除 ${rows.length} 条文档...`;
  }
  try {
    for (const doc of rows) {
      await deleteKBDocument(kb.app_id, kb.kb_key, doc.id, state.walletId);
    }
    state.selectedDocIds = new Set();
    if (state.selectedDocId) {
      state.selectedDocId = null;
      resetDocForm({ render: false });
      updateDocDrawerMeta(null);
    }
    await loadDocuments();
    if (docExportHint) {
      docExportHint.textContent = `已删除 ${rows.length} 条文档。`;
    }
  } catch (err) {
    if (docExportHint) {
      docExportHint.textContent = `批量删除失败: ${err.message}`;
    }
  }
}

function setDocPanelCollapsed(collapsed) {
  if (!docPanel || !docPanelBody || !docToggle) return;
  docPanel.classList.toggle("collapsed", collapsed);
  docPanelBody.setAttribute("aria-hidden", collapsed ? "true" : "false");
  docToggle.textContent = collapsed ? "展开" : "收起";
  docToggle.setAttribute("aria-expanded", collapsed ? "false" : "true");
}

function toggleDocPanel() {
  if (!docPanel) return;
  setDocPanelCollapsed(!docPanel.classList.contains("collapsed"));
}

function syncDocSelection() {
  if (!state.selectedDocId) {
    if (docDelete) {
      docDelete.disabled = true;
    }
    return;
  }
  const doc = state.documents.find((item) => item.id === state.selectedDocId);
  if (!doc) {
    resetDocForm({ render: false });
    updateDocDrawerMeta(null);
    return;
  }
  setDocFormFields(doc);
  updateDocDrawerMeta(doc);
}

function getDocText(doc) {
  const kb = getSelectedKb();
  const textField = kb?.text_field || "text";
  const props = doc.properties || {};
  return props[textField] || props.text || props.content || "";
}

function setDrawerOpen(isOpen) {
  if (!docDrawer) return;
  docDrawer.classList.toggle("open", isOpen);
  docDrawer.setAttribute("aria-hidden", isOpen ? "false" : "true");
  document.body.classList.toggle("drawer-open", isOpen);
}

function closeDocDrawer() {
  setDrawerOpen(false);
}

function setDocFormFields(doc) {
  docIdInput.value = doc ? doc.id : "";
  docTextInput.value = doc ? String(getDocText(doc) || "") : "";
  docPropsInput.value = doc ? JSON.stringify(doc.properties || {}, null, 2) : "";
  docHint.textContent = "";
  if (docDelete) {
    docDelete.disabled = !doc;
  }
}

function updateDocDrawerMeta(doc) {
  if (!drawerTitle || !drawerDocMeta) return;
  const kb = getSelectedKb();
  const textField = kb?.text_field || "text";

  if (!doc) {
    drawerTitle.textContent = "新建文档";
    drawerSubtitle.textContent = kb
      ? `集合 ${kb.collection} · 文本字段 ${textField}`
      : "请选择知识库后新建文档。";
    drawerDocId.textContent = "-";
    drawerDocUpdated.textContent = "-";
    drawerDocCreated.textContent = "-";
    drawerDocFields.textContent = "0";
    drawerDocMeta.textContent = "填写字段并保存后可查看文档详情。";
    return;
  }

  const props = doc.properties || {};
  const fieldCount = Object.keys(props).length;
  drawerTitle.textContent = "文档详情";
  drawerSubtitle.textContent = kb ? `集合 ${kb.collection} · 字段 ${fieldCount}` : "文档详情";
  drawerDocId.textContent = doc.id || "-";
  drawerDocUpdated.textContent = doc.updated_at || "-";
  drawerDocCreated.textContent = doc.created_at || "-";
  drawerDocFields.textContent = String(fieldCount);
  drawerDocMeta.innerHTML = renderDocMeta(props, textField);
}

function renderDocMeta(props, textField) {
  const entries = Object.entries(props || {});
  if (!entries.length) {
    return "该文档暂无属性字段。";
  }
  return entries
    .sort((a, b) => a[0].localeCompare(b[0]))
    .map(([key, value]) => {
      const type = normalizeSchemaType(value);
      const sample = escapeHtml(formatSchemaValue(value));
      const label = escapeHtml(key);
      const mark = key === textField ? "（主文本）" : "";
      return `<div><strong>${label}${mark}</strong> (${type})<br /><span>${sample}</span></div>`;
    })
    .join("<br />");
}

function setHint(el, text, tone = "") {
  if (!el) return;
  el.textContent = text || "";
  el.classList.toggle("text-danger", tone === "error");
}

function toggleAdminOnly() {
  const admin = isSuperAdmin();
  document.querySelectorAll("[data-admin-only]").forEach((el) => {
    el.classList.toggle("hidden", !admin);
  });
  renderKbSchemaEditor();
  updateSchemaStatus();
}

function normalizeSchemaEntry(item) {
  const entry = item || {};
  return {
    name: String(entry.name || "").trim(),
    data_type: String(entry.data_type || entry.type || "text").trim() || "text",
    vectorize: Boolean(entry.vectorize),
    description: String(entry.description || "").trim(),
  };
}

function getVectorFieldsFromSchema() {
  return kbSchemaDraft
    .filter((field) => field.name && field.vectorize)
    .map((field) => field.name);
}

function renderVectorFields() {
  if (!kbVectorFields) return;
  const fields = getVectorFieldsFromSchema();
  if (!fields.length) {
    kbVectorFields.innerHTML = "<span class=\"detail-label\">未选择</span>";
    return;
  }
  kbVectorFields.innerHTML = fields.map((field) => `<span class="chip">${escapeHtml(field)}</span>`).join("");
}

function renderSystemFields(kbType) {
  if (!kbSystemFields) return;
  if (!isUserUploadType(kbType)) {
    kbSystemFields.innerHTML = "<span class=\"detail-label\">无</span>";
    return;
  }
  kbSystemFields.innerHTML = RESERVED_USER_UPLOAD_FIELDS.map((field) => `<span class="chip">${field}</span>`).join(
    ""
  );
}

function updateSchemaStatus() {
  renderVectorFields();
  const kbType = (kbConfigType?.value || "").trim();
  renderSystemFields(kbType);
  if (!kbSchemaHint) return;
  const textField = (kbConfigTextField?.value || "text").trim() || "text";
  const schemaPayload = getSchemaPayload();
  const warnings = [];
  const errors = [];
  const seen = new Map();
  const reserved = new Set(RESERVED_USER_UPLOAD_FIELDS.map((field) => field.toLowerCase()));

  schemaPayload.forEach((field) => {
    const key = field.name.toLowerCase();
    if (seen.has(key)) {
      errors.push(`字段名重复: ${field.name}`);
    }
    seen.set(key, true);
    if (isUserUploadType(kbType) && reserved.has(key)) {
      errors.push(`字段名与系统字段冲突: ${field.name}`);
    }
  });

  if (schemaPayload.length && !seen.has(textField.toLowerCase())) {
    warnings.push(`主文本字段 ${textField} 不在 Schema 中`);
  }
  if (!schemaPayload.length) {
    warnings.push("尚未配置 Schema 字段");
  }
  if (!getVectorFieldsFromSchema().length) {
    warnings.push("未勾选向量化字段，将默认使用主文本字段向量化");
  }

  const message = [...errors, ...warnings].join("；");
  kbSchemaHint.textContent = message || "Schema 配置完整。";
  kbSchemaHint.classList.toggle("text-danger", errors.length > 0);
}

function renderKbSchemaEditor() {
  if (!kbSchemaTable) return;
  if (!isSuperAdmin()) {
    kbSchemaTable.innerHTML = "";
    updateSchemaStatus();
    return;
  }

  const header = `
    <div class="table-row header">
      <div>字段名</div>
      <div>类型</div>
      <div>向量化</div>
      <div>备注</div>
      <div>操作</div>
    </div>
  `;

  if (!kbSchemaDraft.length) {
    kbSchemaTable.innerHTML = header + `
      <div class="table-row">
        <div class="cell-muted">暂无字段</div>
        <div>-</div>
        <div>-</div>
        <div class="cell-muted">点击“新增字段”开始配置</div>
        <div>-</div>
      </div>
    `;
    updateSchemaStatus();
    return;
  }

  const rows = kbSchemaDraft
    .map((field, index) => {
      const safeName = escapeHtml(field.name || "");
      const safeDesc = escapeHtml(field.description || "");
      return `
        <div class="table-row" data-schema-row="${index}">
          <div><input type="text" value="${safeName}" data-schema-field="name" data-index="${index}" /></div>
          <div>
            <select data-schema-field="data_type" data-index="${index}">
              <option value="text" ${field.data_type === "text" ? "selected" : ""}>text</option>
              <option value="int" ${field.data_type === "int" ? "selected" : ""}>int</option>
              <option value="number" ${field.data_type === "number" ? "selected" : ""}>number</option>
              <option value="boolean" ${field.data_type === "boolean" ? "selected" : ""}>boolean</option>
              <option value="date" ${field.data_type === "date" ? "selected" : ""}>date</option>
            </select>
          </div>
          <div>
            <label class="filter-chip">
              <input type="checkbox" data-schema-field="vectorize" data-index="${index}" ${field.vectorize ? "checked" : ""} />
              启用
            </label>
          </div>
          <div><input type="text" value="${safeDesc}" data-schema-field="description" data-index="${index}" /></div>
          <div><button type="button" class="ghost" data-schema-remove="${index}">删除</button></div>
        </div>
      `;
    })
    .join("");

  kbSchemaTable.innerHTML = header + rows;

  kbSchemaTable.querySelectorAll("[data-schema-field]").forEach((input) => {
    input.addEventListener("change", (event) => {
      const index = Number(event.target.dataset.index);
      const field = event.target.dataset.schemaField;
      if (Number.isNaN(index) || !kbSchemaDraft[index]) return;
      if (field === "vectorize") {
        kbSchemaDraft[index].vectorize = Boolean(event.target.checked);
      } else {
        kbSchemaDraft[index][field] = String(event.target.value || "").trim();
      }
      updateSchemaStatus();
    });
  });

  kbSchemaTable.querySelectorAll("[data-schema-remove]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const index = Number(btn.dataset.schemaRemove);
      if (Number.isNaN(index)) return;
      kbSchemaDraft.splice(index, 1);
      renderKbSchemaEditor();
    });
  });

  updateSchemaStatus();
}

function loadKbSchemaDraft(kb) {
  const schema = Array.isArray(kb?.schema) ? kb.schema.map(normalizeSchemaEntry) : [];
  const vectorSet = new Set((kb?.vector_fields || []).map((field) => String(field || "").toLowerCase()));
  schema.forEach((field) => {
    if (vectorSet.has(String(field.name || "").toLowerCase())) {
      field.vectorize = true;
    }
  });
  kbSchemaDraft = schema;
  renderKbSchemaEditor();
  updateSchemaStatus();
}

function getSchemaPayload() {
  return kbSchemaDraft
    .map((field) => normalizeSchemaEntry(field))
    .filter((field) => field.name)
    .map((field) => {
      const payload = {
        name: field.name,
        data_type: field.data_type || "text",
        vectorize: Boolean(field.vectorize),
      };
      if (field.description) {
        payload.description = field.description;
      }
      return payload;
    });
}

function validateSchemaDraft() {
  const kbType = (kbConfigType?.value || "").trim();
  const schemaPayload = getSchemaPayload();
  const seen = new Set();
  const duplicates = new Set();
  const reserved = new Set(RESERVED_USER_UPLOAD_FIELDS.map((field) => field.toLowerCase()));
  const reservedUsed = new Set();

  schemaPayload.forEach((field) => {
    const key = field.name.toLowerCase();
    if (seen.has(key)) duplicates.add(field.name);
    seen.add(key);
    if (isUserUploadType(kbType) && reserved.has(key)) reservedUsed.add(field.name);
  });

  if (duplicates.size) {
    throw new Error(`Schema 字段名重复: ${Array.from(duplicates).join(", ")}`);
  }
  if (reservedUsed.size) {
    throw new Error(`Schema 字段名与系统字段冲突: ${Array.from(reservedUsed).join(", ")}`);
  }
}

function normalizeIntentEntry(item) {
  const entry = item || {};
  const params = Array.isArray(entry.params) ? entry.params : [];
  return {
    name: String(entry.name || "").trim(),
    description: String(entry.description || "").trim(),
    params: params.map((p) => String(p || "").trim()).filter(Boolean),
    exposed: entry.exposed !== false,
  };
}

function normalizeWorkflowEntry(item) {
  const entry = item || {};
  const intents = Array.isArray(entry.intents) ? entry.intents : [];
  return {
    name: String(entry.name || "").trim(),
    description: String(entry.description || "").trim(),
    intents: intents.map((p) => String(p || "").trim()).filter(Boolean),
    enabled: entry.enabled !== false,
  };
}

function parseCsvList(value) {
  return String(value || "")
    .split(/[,，]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function cloneList(value) {
  try {
    return JSON.parse(JSON.stringify(value || []));
  } catch {
    return [];
  }
}

function renderIntentTable() {
  if (!intentTable) return;
  const header = `
    <div class="table-row header">
      <div>名称</div>
      <div>公开</div>
      <div>参数</div>
      <div>描述</div>
      <div>操作</div>
    </div>
  `;
  if (!intentDraft.length) {
    intentTable.innerHTML = header + `
      <div class="table-row">
        <div class="cell-muted">暂无 Intent</div>
        <div>-</div>
        <div>-</div>
        <div class="cell-muted">点击“新增 Intent”开始配置</div>
        <div>-</div>
      </div>
    `;
    return;
  }
  const rows = intentDraft
    .map((intent, index) => {
      const safeName = escapeHtml(intent.name || "");
      const safeDesc = escapeHtml(intent.description || "");
      const params = escapeHtml((intent.params || []).join(", "));
      return `
        <div class="table-row" data-intent-row="${index}">
          <div><input type="text" value="${safeName}" data-intent-field="name" data-index="${index}" /></div>
          <div>
            <label class="filter-chip">
              <input type="checkbox" data-intent-field="exposed" data-index="${index}" ${intent.exposed ? "checked" : ""} />
              对外
            </label>
          </div>
          <div><input type="text" value="${params}" data-intent-field="params" data-index="${index}" placeholder="param_a, param_b" /></div>
          <div><input type="text" value="${safeDesc}" data-intent-field="description" data-index="${index}" /></div>
          <div><button type="button" class="ghost" data-intent-remove="${index}">删除</button></div>
        </div>
      `;
    })
    .join("");
  intentTable.innerHTML = header + rows;
  intentTable.querySelectorAll("[data-intent-field]").forEach((input) => {
    input.addEventListener("change", (event) => {
      const index = Number(event.target.dataset.index);
      const field = event.target.dataset.intentField;
      if (Number.isNaN(index) || !intentDraft[index]) return;
      if (field === "exposed") {
        intentDraft[index].exposed = Boolean(event.target.checked);
      } else if (field === "params") {
        intentDraft[index].params = parseCsvList(event.target.value);
      } else {
        intentDraft[index][field] = String(event.target.value || "").trim();
      }
    });
  });
  intentTable.querySelectorAll("[data-intent-remove]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const index = Number(btn.dataset.intentRemove);
      if (Number.isNaN(index)) return;
      intentDraft.splice(index, 1);
      renderIntentTable();
    });
  });
}

function renderWorkflowTable() {
  if (!workflowTable) return;
  const header = `
    <div class="table-row header">
      <div>名称</div>
      <div>启用</div>
      <div>关联意图</div>
      <div>描述</div>
      <div>操作</div>
    </div>
  `;
  if (!workflowDraft.length) {
    workflowTable.innerHTML = header + `
      <div class="table-row">
        <div class="cell-muted">暂无流程</div>
        <div>-</div>
        <div>-</div>
        <div class="cell-muted">点击“新增流程”开始配置</div>
        <div>-</div>
      </div>
    `;
    return;
  }
  const rows = workflowDraft
    .map((flow, index) => {
      const safeName = escapeHtml(flow.name || "");
      const safeDesc = escapeHtml(flow.description || "");
      const intents = escapeHtml((flow.intents || []).join(", "));
      return `
        <div class="table-row" data-workflow-row="${index}">
          <div><input type="text" value="${safeName}" data-workflow-field="name" data-index="${index}" /></div>
          <div>
            <label class="filter-chip">
              <input type="checkbox" data-workflow-field="enabled" data-index="${index}" ${flow.enabled ? "checked" : ""} />
              启用
            </label>
          </div>
          <div><input type="text" value="${intents}" data-workflow-field="intents" data-index="${index}" placeholder="intent_a, intent_b" /></div>
          <div><input type="text" value="${safeDesc}" data-workflow-field="description" data-index="${index}" /></div>
          <div><button type="button" class="ghost" data-workflow-remove="${index}">删除</button></div>
        </div>
      `;
    })
    .join("");
  workflowTable.innerHTML = header + rows;
  workflowTable.querySelectorAll("[data-workflow-field]").forEach((input) => {
    input.addEventListener("change", (event) => {
      const index = Number(event.target.dataset.index);
      const field = event.target.dataset.workflowField;
      if (Number.isNaN(index) || !workflowDraft[index]) return;
      if (field === "enabled") {
        workflowDraft[index].enabled = Boolean(event.target.checked);
      } else if (field === "intents") {
        workflowDraft[index].intents = parseCsvList(event.target.value);
      } else {
        workflowDraft[index][field] = String(event.target.value || "").trim();
      }
    });
  });
  workflowTable.querySelectorAll("[data-workflow-remove]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const index = Number(btn.dataset.workflowRemove);
      if (Number.isNaN(index)) return;
      workflowDraft.splice(index, 1);
      renderWorkflowTable();
    });
  });
}

function loadIntentDraft(intents) {
  intentDraft = (intents || []).map(normalizeIntentEntry);
  intentSnapshot = cloneList(intentDraft);
  renderIntentTable();
}

function loadWorkflowDraft(workflows) {
  workflowDraft = (workflows || []).map(normalizeWorkflowEntry);
  workflowSnapshot = cloneList(workflowDraft);
  renderWorkflowTable();
}

function validateIntentDraft() {
  const names = new Set();
  const duplicates = new Set();
  intentDraft.forEach((intent) => {
    const key = String(intent.name || "").trim();
    if (!key) return;
    const lower = key.toLowerCase();
    if (names.has(lower)) duplicates.add(key);
    names.add(lower);
  });
  if (duplicates.size) {
    throw new Error(`Intent 名称重复: ${Array.from(duplicates).join(", ")}`);
  }
}

function validateWorkflowDraft() {
  const names = new Set();
  const duplicates = new Set();
  workflowDraft.forEach((flow) => {
    const key = String(flow.name || "").trim();
    if (!key) return;
    const lower = key.toLowerCase();
    if (names.has(lower)) duplicates.add(key);
    names.add(lower);
  });
  if (duplicates.size) {
    throw new Error(`流程名称重复: ${Array.from(duplicates).join(", ")}`);
  }
}

async function loadIntentConfigs() {
  if (!intentTable || !currentAppId) return;
  try {
    const res = await fetchAppIntentDetails(currentAppId, state.walletId);
    loadIntentDraft(res.intents || []);
    setHint(intentHint, "");
  } catch (err) {
    intentDraft = [];
    intentSnapshot = [];
    renderIntentTable();
    setHint(intentHint, `加载失败: ${err.message}`, "error");
  }
}

async function loadWorkflowConfigs() {
  if (!workflowTable || !currentAppId) return;
  try {
    const res = await fetchAppWorkflows(currentAppId, state.walletId);
    loadWorkflowDraft(res.workflows || []);
    setHint(workflowHint, "");
  } catch (err) {
    workflowDraft = [];
    workflowSnapshot = [];
    renderWorkflowTable();
    setHint(workflowHint, `加载失败: ${err.message}`, "error");
  }
}

async function saveIntentConfigs() {
  if (!currentAppId) return;
  try {
    validateIntentDraft();
    const payload = {
      intents: intentDraft.map(normalizeIntentEntry).filter((item) => item.name),
    };
    if (!payload.intents.length) {
      throw new Error("请至少保留一个 Intent");
    }
    setHint(intentHint, "正在保存 Intent...");
    const res = await updateAppIntents(currentAppId, payload, state.walletId);
    loadIntentDraft(res.intents || payload.intents);
    setHint(intentHint, "Intent 已更新。");
  } catch (err) {
    setHint(intentHint, `保存失败: ${err.message}`, "error");
  }
}

async function saveWorkflowConfigs() {
  if (!currentAppId) return;
  try {
    validateWorkflowDraft();
    const payload = {
      workflows: workflowDraft.map(normalizeWorkflowEntry).filter((item) => item.name),
    };
    setHint(workflowHint, "正在保存工作流...");
    const res = await updateAppWorkflows(currentAppId, payload, state.walletId);
    loadWorkflowDraft(res.workflows || payload.workflows);
    setHint(workflowHint, "工作流已更新。");
  } catch (err) {
    setHint(workflowHint, `保存失败: ${err.message}`, "error");
  }
}

function resetIntentConfigs() {
  intentDraft = cloneList(intentSnapshot);
  renderIntentTable();
  setHint(intentHint, "已恢复草稿。");
}

function resetWorkflowConfigs() {
  workflowDraft = cloneList(workflowSnapshot);
  renderWorkflowTable();
  setHint(workflowHint, "已恢复草稿。");
}

function formatBytes(size) {
  const value = Number(size) || 0;
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  if (value < 1024 * 1024 * 1024) return `${(value / (1024 * 1024)).toFixed(1)} MB`;
  return `${(value / (1024 * 1024 * 1024)).toFixed(1)} GB`;
}

function formatPluginKind(kind) {
  const mapping = {
    config: "配置",
    intents: "Intent",
    workflows: "工作流",
    pipeline: "Pipeline",
    prompt: "Prompt",
  };
  return mapping[kind] || kind || "-";
}

function hasPluginChanges() {
  if (!pluginEditor) return false;
  return pluginEditor.value !== (state.pluginContentSnapshot || "");
}

function updatePluginEditorInfo(fileInfo) {
  if (pluginFilePath) pluginFilePath.textContent = fileInfo?.path || "-";
  if (pluginFileKind) pluginFileKind.textContent = formatPluginKind(fileInfo?.kind);
  if (pluginFileSize) {
    pluginFileSize.textContent = fileInfo?.exists ? formatBytes(fileInfo?.size_bytes) : "未创建";
  }
  if (pluginFileUpdated) {
    pluginFileUpdated.textContent = fileInfo?.updated_at || "-";
  }
  if (pluginEditorTitle) pluginEditorTitle.textContent = fileInfo?.path ? "文件编辑器" : "文件编辑器";
  if (pluginEditorSubtitle) {
    pluginEditorSubtitle.textContent = fileInfo?.path
      ? `${formatPluginKind(fileInfo?.kind)} · ${fileInfo.path}`
      : "请选择文件开始编辑。";
  }
  if (pluginEditor) pluginEditor.disabled = !fileInfo;
  if (pluginSave) pluginSave.disabled = !fileInfo;
  if (pluginReset) pluginReset.disabled = !fileInfo;
}

function renderPluginFileTable() {
  if (!pluginFileTable) return;
  if (!currentAppId) {
    pluginFileTable.innerHTML = "<div class=\"detail-label\">请先选择应用。</div>";
    updatePluginEditorInfo(null);
    return;
  }
  const rows = state.pluginFiles || [];
  if (!rows.length) {
    pluginFileTable.innerHTML = renderEmptyState("暂无插件文件", "当前应用未加载到插件文件。");
    updatePluginEditorInfo(null);
    return;
  }
  const header = `
    <div class="table-row header">
      <div>文件</div>
      <div>类型</div>
      <div>大小</div>
      <div>更新时间</div>
    </div>
  `;
  const body = rows
    .map((file) => {
      const active = state.selectedPluginPath === file.path ? "active" : "";
      const muted = file.exists ? "" : "cell-muted";
      const size = file.exists ? formatBytes(file.size_bytes) : "未创建";
      return `
        <div class="table-row ${active}" data-plugin-path="${file.path}">
          <div class="${muted} text-mono">${escapeHtml(file.path)}</div>
          <div>${escapeHtml(formatPluginKind(file.kind))}</div>
          <div class="${muted}">${size}</div>
          <div class="${muted}">${escapeHtml(file.updated_at || "-")}</div>
        </div>
      `;
    })
    .join("");
  pluginFileTable.innerHTML = header + body;
  pluginFileTable.querySelectorAll(".table-row[data-plugin-path]").forEach((row) => {
    row.addEventListener("click", () => {
      const path = row.dataset.pluginPath;
      if (!path) return;
      const fileInfo = (state.pluginFiles || []).find((item) => item.path === path) || null;
      openPluginFile(fileInfo);
    });
  });
}

async function loadPluginFiles() {
  if (!pluginFileTable || !currentAppId) return;
  try {
    const res = await fetchPluginFiles(currentAppId, state.walletId);
    state.pluginFiles = res.files || [];
    const selected = state.selectedPluginPath;
    if (selected) {
      const exists = state.pluginFiles.some((item) => item.path === selected);
      if (!exists) {
        state.selectedPluginPath = null;
        state.pluginFileMeta = null;
        state.pluginContentSnapshot = "";
      }
    }
    renderPluginFileTable();
    if (state.selectedPluginPath) {
      const fileInfo = state.pluginFiles.find((item) => item.path === state.selectedPluginPath) || null;
      updatePluginEditorInfo(fileInfo);
    } else {
      updatePluginEditorInfo(null);
    }
    setHint(pluginHint, "");
  } catch (err) {
    state.pluginFiles = [];
    renderPluginFileTable();
    setHint(pluginHint, `插件文件加载失败: ${err.message}`, "error");
  }
}

async function openPluginFile(fileInfo) {
  if (!pluginEditor || !fileInfo) return;
  if (hasPluginChanges()) {
    const proceed = window.confirm("当前文件尚未保存，确认切换？");
    if (!proceed) return;
  }
  state.selectedPluginPath = fileInfo.path;
  state.pluginFileMeta = fileInfo;
  pluginEditor.value = "";
  state.pluginContentSnapshot = "";
  updatePluginEditorInfo(fileInfo);
  if (!fileInfo.exists) {
    setHint(pluginHint, "新文件尚未创建，编辑后点击保存即可。");
    return;
  }
  try {
    const res = await fetchPluginFile(currentAppId, fileInfo.path, state.walletId);
    pluginEditor.value = res.content || "";
    state.pluginContentSnapshot = res.content || "";
    updatePluginEditorInfo({ ...fileInfo, kind: res.kind || fileInfo.kind, exists: true });
    setHint(pluginHint, "");
  } catch (err) {
    setHint(pluginHint, `加载失败: ${err.message}`, "error");
  }
}

async function savePluginFile() {
  if (!currentAppId || !state.selectedPluginPath) {
    setHint(pluginHint, "请先选择需要保存的文件。", "error");
    return;
  }
  try {
    setHint(pluginHint, "正在保存文件...");
    const content = pluginEditor?.value || "";
    await updatePluginFile(
      currentAppId,
      { path: state.selectedPluginPath, content },
      state.walletId
    );
    state.pluginContentSnapshot = content;
    setHint(pluginHint, "保存成功。");
    await loadPluginFiles();
  } catch (err) {
    setHint(pluginHint, `保存失败: ${err.message}`, "error");
  }
}

function resetPluginEditor() {
  if (!pluginEditor) return;
  pluginEditor.value = state.pluginContentSnapshot || "";
  setHint(pluginHint, "已恢复到上次保存内容。");
}

function createNewPrompt() {
  if (!currentAppId) return;
  const name = window.prompt("请输入 Prompt 名称（仅字母/数字/下划线）");
  if (!name) return;
  const safe = name.trim();
  if (!/^[a-zA-Z0-9_-]+$/.test(safe)) {
    setHint(pluginHint, "Prompt 名称格式不正确。", "error");
    return;
  }
  const path = `prompts/${safe}.md`;
  const exists = (state.pluginFiles || []).some((item) => item.path === path);
  const fileInfo = {
    path,
    kind: "prompt",
    exists,
    size_bytes: 0,
    updated_at: null,
  };
  if (!exists) {
    state.pluginFiles = [fileInfo, ...(state.pluginFiles || [])];
    renderPluginFileTable();
  }
  openPluginFile(fileInfo);
}

function openPipelineFile() {
  const fileInfo = (state.pluginFiles || []).find((item) => item.path === "pipeline.py") || {
    path: "pipeline.py",
    kind: "pipeline",
    exists: false,
    size_bytes: 0,
    updated_at: null,
  };
  openPluginFile(fileInfo);
}

function resetKbConfigForm() {
  if (!kbConfigForm) return;
  kbConfigKey.value = "";
  kbConfigKey.disabled = false;
  kbConfigType.value = "public_kb";
  kbConfigCollection.value = "";
  kbConfigTextField.value = "text";
  kbConfigTopk.value = "";
  kbConfigWeight.value = "";
  kbConfigAllowed.value = "false";
  if (kbConfigDelete) {
    kbConfigDelete.disabled = true;
  }
  if (kbConfigSubtitle) {
    kbConfigSubtitle.textContent = "新建或调整当前应用的知识库配置。";
  }
  setHint(kbConfigHint, "");
  kbSchemaDraft = [];
  renderKbSchemaEditor();
  updateSchemaStatus();
}

function setKbConfigForm(kb) {
  if (!kbConfigForm) return;
  if (!kb) {
    resetKbConfigForm();
    return;
  }
  kbConfigKey.value = kb.kb_key || "";
  kbConfigKey.disabled = true;
  kbConfigType.value = normalizeKbType(kb.type || "public_kb");
  kbConfigCollection.value = kb.collection || "";
  kbConfigTextField.value = kb.text_field || "text";
  kbConfigTopk.value = kb.top_k !== undefined && kb.top_k !== null ? String(kb.top_k) : "";
  kbConfigWeight.value = kb.weight !== undefined && kb.weight !== null ? String(kb.weight) : "";
  kbConfigAllowed.value = kb.use_allowed_apps_filter ? "true" : "false";
  if (kbConfigDelete) {
    kbConfigDelete.disabled = false;
  }
  if (kbConfigSubtitle) {
    kbConfigSubtitle.textContent = `编辑 ${kb.kb_key}`;
  }
  setHint(kbConfigHint, "");
  loadKbSchemaDraft(kb);
}

function buildKbConfigPayload(isCreate) {
  const kbKey = (kbConfigKey.value || "").trim();
  const kbType = normalizeKbType((kbConfigType.value || "").trim());
  const collection = (kbConfigCollection.value || "").trim();
  const textField = (kbConfigTextField.value || "").trim() || "text";
  const topKRaw = (kbConfigTopk.value || "").trim();
  const weightRaw = (kbConfigWeight.value || "").trim();
  const allowFilter = kbConfigAllowed.value === "true";

  if (isCreate && !kbKey) {
    throw new Error("请填写 KB Key");
  }
  if (!kbType) {
    throw new Error("请选择 KB 类型");
  }
  if (!collection) {
    throw new Error("请填写 collection");
  }

  const payload = {
    kb_key: kbKey,
    kb_type: kbType,
    collection,
    text_field: textField,
    use_allowed_apps_filter: allowFilter,
  };

  if (isSuperAdmin()) {
    validateSchemaDraft();
    payload.schema = getSchemaPayload();
    payload.vector_fields = getVectorFieldsFromSchema();
  }

  if (topKRaw) {
    const topK = Number(topKRaw);
    if (Number.isNaN(topK) || topK <= 0) {
      throw new Error("Top K 必须为正整数");
    }
    payload.top_k = topK;
  } else if (isCreate) {
    payload.top_k = 3;
  }
  if (weightRaw) {
    const weight = Number(weightRaw);
    if (Number.isNaN(weight) || weight < 0) {
      throw new Error("Weight 必须为非负数");
    }
    payload.weight = weight;
  } else if (isCreate) {
    payload.weight = 1.0;
  }
  return payload;
}

async function handleKbConfigSubmit(event) {
  event.preventDefault();
  if (!currentAppId) {
    setHint(kbConfigHint, "未选择应用。", "error");
    return;
  }
  const editing = kbConfigKey.disabled;
  const kbKey = (kbConfigKey.value || "").trim();
  const exists = state.knowledgeBases.some((kb) => kb.app_id === currentAppId && kb.kb_key === kbKey);

  if (!editing && exists) {
    setHint(kbConfigHint, "KB Key 已存在，请修改或选择该 KB 进行编辑。", "error");
    return;
  }

  try {
    const payload = buildKbConfigPayload(!editing);
    if (editing) {
      delete payload.kb_key;
    }
    setHint(kbConfigHint, editing ? "正在更新配置..." : "正在创建知识库...");
    if (editing) {
      await updateKBConfig(currentAppId, kbKey, payload, state.walletId);
    } else {
      await createKBConfig(currentAppId, payload, state.walletId);
    }
    await loadData();
    if (editing) {
      const selected = state.knowledgeBases.find((kb) => kb.app_id === currentAppId && kb.kb_key === kbKey);
      setKbConfigForm(selected || null);
      setHint(kbConfigHint, "配置已更新。");
    } else {
      const newId = `${currentAppId}:${kbKey}`;
      await selectKb(newId);
      setHint(kbConfigHint, "知识库已创建。");
    }
  } catch (err) {
    setHint(kbConfigHint, `保存失败: ${err.message}`, "error");
  }
}

async function handleKbConfigDelete() {
  const kbKey = (kbConfigKey.value || "").trim();
  if (!kbKey || !kbConfigKey.disabled) {
    setHint(kbConfigHint, "请选择已有 KB 后再删除。", "error");
    return;
  }
  const confirmed = window.confirm(`确认删除 KB ${kbKey}？此操作会移除配置但不删除已有向量。`);
  if (!confirmed) return;
  try {
    setHint(kbConfigHint, "正在删除...");
    await deleteKBConfig(currentAppId, kbKey, state.walletId);
    await loadData();
    if (!state.knowledgeBases.length) {
      resetKbConfigForm();
    }
    setHint(kbConfigHint, "KB 已删除。");
  } catch (err) {
    setHint(kbConfigHint, `删除失败: ${err.message}`, "error");
  }
}

function normalizeSessionIds(raw) {
  return (raw || "")
    .split(/[\s,]+/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function updatePrivateDbDetail(db) {
  if (!privateDbDetailTitle) return;
  if (!db) {
    privateDbDetailTitle.textContent = "私有库详情";
    privateDbDetailSubtitle.textContent = "选择私有库查看会话。";
    privateDbDetailId.textContent = "-";
    privateDbDetailOwner.textContent = "-";
    privateDbDetailStatus.textContent = "-";
    privateDbDetailCreated.textContent = "-";
    if (privateDbSessionsList) {
      privateDbSessionsList.innerHTML = "<div class=\"detail-label\">暂无会话。</div>";
    }
    return;
  }
  privateDbDetailTitle.textContent = `私有库 ${db.private_db_id}`;
  privateDbDetailSubtitle.textContent = `业务钱包 ${db.owner_wallet_id} · 状态 ${db.status || "-"}`;
  privateDbDetailId.textContent = db.private_db_id || "-";
  privateDbDetailOwner.textContent = db.owner_wallet_id || "-";
  privateDbDetailStatus.textContent = db.status || "-";
  privateDbDetailCreated.textContent = db.created_at || "-";
}

function renderPrivateDbSessions() {
  if (!privateDbSessionsList) return;
  const sessions = state.privateDbSessions || [];
  if (!sessions.length) {
    privateDbSessionsList.innerHTML = "<div class=\"detail-label\">暂无会话绑定。</div>";
    return;
  }
  privateDbSessionsList.innerHTML = sessions
    .map(
      (session) => `
      <div class="session-item">
        <div>
          <div class="session-id">${escapeHtml(session.session_id)}</div>
          <div class="session-meta">${escapeHtml(session.created_at || "-")}</div>
        </div>
        <button class="ghost" data-unbind="${escapeHtml(session.session_id)}">解绑</button>
      </div>
    `
    )
    .join("");

  privateDbSessionsList.querySelectorAll("button[data-unbind]").forEach((btn) => {
    btn.addEventListener("click", async (event) => {
      event.preventDefault();
      const sessionId = btn.dataset.unbind;
      if (!sessionId || !state.selectedPrivateDbId) return;
      const confirmed = window.confirm(`确认解绑会话 ${sessionId}？`);
      if (!confirmed) return;
      try {
        await unbindPrivateDBSession(
          state.selectedPrivateDbId,
          sessionId,
          currentAppId,
          state.walletId
        );
        await loadPrivateDbSessions();
      } catch (err) {
        setHint(privateDbHint, `解绑失败: ${err.message}`, "error");
      }
    });
  });
}

function renderPrivateDbTable() {
  if (!privateDbTable) return;
  const rows = state.privateDbs || [];
  if (!rows.length) {
    privateDbTable.innerHTML = "<div class=\"detail-label\">暂无私有库。</div>";
    return;
  }
  const header = `
    <div class="table-row header">
      <div>私有库</div>
      <div>状态</div>
      <div>操作</div>
    </div>
  `;
  const body = rows
    .map((db) => {
      const active = state.selectedPrivateDbId === db.private_db_id ? "active" : "";
      const fullId = escapeHtml(db.private_db_id || "-");
      const shortId = escapeHtml(compactId(db.private_db_id || "-"));
      const ownerFull = escapeHtml(db.owner_wallet_id || "-");
      const ownerShort = escapeHtml(compactId(db.owner_wallet_id || "-"));
      const createdAt = escapeHtml(db.created_at || "-");
      const statusLabel = escapeHtml(db.status || "-");
      const statusClass = resolveStatusClass(db.status || "");
      return `
        <div class="table-row ${active}" data-private-db="${escapeHtml(db.private_db_id)}">
          <div class="private-db-main">
            <div class="private-db-id" title="${fullId}">${shortId}</div>
            <div class="cell-muted" title="${ownerFull}">业务钱包 ${ownerShort}</div>
            <div class="cell-muted">创建 ${createdAt}</div>
          </div>
          <div class="private-db-meta">
            <span class="status-pill ${statusClass}">${statusLabel}</span>
          </div>
          <div class="private-db-actions">
            <button class="ghost" data-select="${escapeHtml(db.private_db_id)}">查看</button>
          </div>
        </div>
      `;
    })
    .join("");
  privateDbTable.innerHTML = header + body;
  privateDbTable.querySelectorAll("[data-private-db]").forEach((row) => {
    row.addEventListener("click", () => selectPrivateDb(row.dataset.privateDb));
  });
  privateDbTable.querySelectorAll("button[data-select]").forEach((btn) => {
    btn.addEventListener("click", (event) => {
      event.stopPropagation();
      selectPrivateDb(btn.dataset.select);
    });
  });
}

async function loadPrivateDbs() {
  if (!privateDbTable) return;
  if (!currentAppId) {
    privateDbTable.innerHTML = "<div class=\"detail-label\">请先选择应用。</div>";
    return;
  }
  const ownerFilter = (privateDbOwnerFilter?.value || "").trim();
  try {
    const res = await fetchPrivateDBs({
      walletId: state.walletId,
      appId: currentAppId,
      ownerWalletId: ownerFilter || undefined,
    });
    state.privateDbs = res.items || [];
    renderPrivateDbTable();
    if (!state.privateDbs.length) {
      state.selectedPrivateDbId = null;
      updatePrivateDbDetail(null);
      renderPrivateDbSessions();
      return;
    }
    if (!state.selectedPrivateDbId && state.privateDbs.length) {
      selectPrivateDb(state.privateDbs[0].private_db_id);
    } else if (state.selectedPrivateDbId) {
      const exists = state.privateDbs.some((db) => db.private_db_id === state.selectedPrivateDbId);
      if (!exists) {
        state.selectedPrivateDbId = null;
        updatePrivateDbDetail(null);
        renderPrivateDbSessions();
      }
    }
  } catch (err) {
    privateDbTable.innerHTML = `<div class="detail-label">加载失败: ${escapeHtml(err.message)}</div>`;
  }
}

async function loadPrivateDbSessions() {
  if (!state.selectedPrivateDbId || !currentAppId) {
    state.privateDbSessions = [];
    renderPrivateDbSessions();
    return;
  }
  try {
    const res = await fetchPrivateDBSessions(state.selectedPrivateDbId, currentAppId, state.walletId);
    state.privateDbSessions = res.sessions || [];
    renderPrivateDbSessions();
  } catch (err) {
    setHint(privateDbHint, `加载会话失败: ${err.message}`, "error");
  }
}

function selectPrivateDb(privateDbId) {
  if (!privateDbId) return;
  const db = state.privateDbs.find((item) => item.private_db_id === privateDbId);
  if (!db) return;
  state.selectedPrivateDbId = privateDbId;
  if (privateDbOwner) {
    privateDbOwner.value = db.owner_wallet_id || "";
  }
  if (privateDbIdInput) {
    privateDbIdInput.value = db.private_db_id || "";
  }
  if (privateDbSessionsInput) {
    privateDbSessionsInput.value = "";
  }
  updatePrivateDbDetail(db);
  renderPrivateDbTable();
  loadPrivateDbSessions();
}

async function handlePrivateDbCreate() {
  if (!currentAppId) {
    setHint(privateDbHint, "未选择应用。", "error");
    return;
  }
  const dataWallet = (privateDbOwner?.value || "").trim();
  if (!dataWallet) {
    setHint(privateDbHint, "请填写业务用户 wallet_id。", "error");
    return;
  }
  const privateDbId = (privateDbIdInput?.value || "").trim();
  try {
    setHint(privateDbHint, "正在创建私有库...");
    const res = await createPrivateDB(
      {
        app_id: currentAppId,
        data_wallet_id: dataWallet,
        private_db_id: privateDbId || undefined,
      },
      state.walletId
    );
    setHint(privateDbHint, `已创建/获取私有库 ${res.private_db_id}`);
    await loadPrivateDbs();
    selectPrivateDb(res.private_db_id);
  } catch (err) {
    setHint(privateDbHint, `创建失败: ${err.message}`, "error");
  }
}

async function handlePrivateDbBind() {
  if (!currentAppId) {
    setHint(privateDbHint, "未选择应用。", "error");
    return;
  }
  const privateDbId = state.selectedPrivateDbId || (privateDbIdInput?.value || "").trim();
  if (!privateDbId) {
    setHint(privateDbHint, "请先选择或填写 private_db_id。", "error");
    return;
  }
  const dataWallet = (privateDbOwner?.value || "").trim();
  const sessionIds = normalizeSessionIds(privateDbSessionsInput?.value || "");
  if (!sessionIds.length) {
    setHint(privateDbHint, "请填写至少一个 session_id。", "error");
    return;
  }
  try {
    setHint(privateDbHint, "正在绑定会话...");
    await bindPrivateDBSessions(
      privateDbId,
      {
        app_id: currentAppId,
        data_wallet_id: dataWallet || undefined,
        session_ids: sessionIds,
      },
      state.walletId
    );
    setHint(privateDbHint, `已绑定 ${sessionIds.length} 条会话。`);
    if (privateDbSessionsInput) {
      privateDbSessionsInput.value = "";
    }
    await loadPrivateDbSessions();
  } catch (err) {
    setHint(privateDbHint, `绑定失败: ${err.message}`, "error");
  }
}

function formatAuditAction(action) {
  const mapping = {
    "kb_config.create": "KB 新建",
    "kb_config.update": "KB 更新",
    "kb_config.delete": "KB 删除",
    "private_db.create": "私有库创建",
    "private_db.bind_session": "私有库绑定",
    "private_db.unbind_session": "私有库解绑",
    "intent.update": "Intent 更新",
    "workflow.update": "工作流更新",
    "plugin.update": "插件文件更新",
  };
  return mapping[action] || action || "-";
}

function formatAuditTarget(log) {
  const type = log.entity_type || "-";
  const id = log.entity_id || "-";
  if (type === "kb_config") return `KB ${id}`;
  if (type === "private_db") return `私有库 ${id}`;
  if (type === "intent") return `Intent ${id}`;
  if (type === "workflow") return `工作流 ${id}`;
  if (type === "plugin_file") return `插件文件 ${id}`;
  return `${type} ${id}`;
}

function diffConfigKeys(before, after) {
  const left = before && typeof before === "object" ? before : {};
  const right = after && typeof after === "object" ? after : {};
  const keys = new Set([...Object.keys(left), ...Object.keys(right)]);
  const changed = [];
  keys.forEach((key) => {
    const l = JSON.stringify(left[key]);
    const r = JSON.stringify(right[key]);
    if (l !== r) changed.push(key);
  });
  return changed;
}

function summarizeAudit(log) {
  const meta = log.meta || {};
  if (log.action === "kb_config.create") return "新建 KB 配置";
  if (log.action === "kb_config.delete") return "删除 KB 配置";
  if (log.action === "kb_config.update") {
    const changed = diffConfigKeys(meta.before || {}, meta.after || {});
    return changed.length ? `变更字段: ${changed.join(", ")}` : "更新 KB 配置";
  }
  if (log.action === "private_db.create") {
    return meta.data_wallet_id ? `业务钱包 ${meta.data_wallet_id}` : "创建私有库";
  }
  if (log.action === "private_db.bind_session") {
    const count = Array.isArray(meta.session_ids) ? meta.session_ids.length : 0;
    return count ? `绑定会话 ${count} 条` : "绑定会话";
  }
  if (log.action === "private_db.unbind_session") {
    return meta.session_id ? `解绑会话 ${meta.session_id}` : "解绑会话";
  }
  if (log.action === "intent.update") {
    const before = meta.before || {};
    const after = meta.after || {};
    const count = Object.keys(after || {}).length;
    const changed = diffConfigKeys(before, after);
    return changed.length ? `变更 Intent ${changed.join(", ")}` : `Intent ${count} 个`;
  }
  if (log.action === "workflow.update") {
    const before = Array.isArray(meta.before) ? meta.before.length : 0;
    const after = Array.isArray(meta.after) ? meta.after.length : 0;
    return `流程 ${before} → ${after}`;
  }
  if (log.action === "plugin.update") {
    if (meta.path) return meta.path;
    if (meta.size_before !== undefined || meta.size_after !== undefined) {
      return `大小 ${meta.size_before ?? "-"} → ${meta.size_after ?? "-"}`;
    }
    return "插件文件更新";
  }
  return "";
}

function updateAuditDetail(log) {
  if (!auditDetail) return;
  if (!log) {
    auditDetail.textContent = "选择日志查看详情。";
    return;
  }
  auditDetail.textContent = JSON.stringify(log.meta || {}, null, 2);
}

function renderAuditTable() {
  if (!auditTable) return;
  const rows = state.auditLogs || [];
  if (!rows.length) {
    auditTable.innerHTML = renderEmptyState("暂无审计日志", "当前应用暂无配置变更记录。");
    updateAuditDetail(null);
    return;
  }

  const header = `
    <div class="table-row header">
      <div>时间</div>
      <div>操作</div>
      <div>目标</div>
      <div>操作人</div>
      <div>备注</div>
    </div>
  `;

  const body = rows
    .map((log) => {
      const active = state.selectedAuditId === log.id ? "active" : "";
      const summary = summarizeAudit(log);
      return `
        <div class="table-row ${active}" data-audit-id="${log.id}">
          <div class="cell-muted">${log.created_at || "-"}</div>
          <div>${escapeHtml(formatAuditAction(log.action))}</div>
          <div>${escapeHtml(formatAuditTarget(log))}</div>
          <div class="cell-muted">${escapeHtml(log.operator_wallet_id || "-")}</div>
          <div>${escapeHtml(summary || "-")}</div>
        </div>
      `;
    })
    .join("");

  auditTable.innerHTML = header + body;
  auditTable.querySelectorAll(".table-row[data-audit-id]").forEach((row) => {
    row.addEventListener("click", () => selectAuditLog(Number(row.dataset.auditId)));
  });
}

function selectAuditLog(id) {
  if (!id) return;
  state.selectedAuditId = id;
  const log = (state.auditLogs || []).find((item) => item.id === id);
  renderAuditTable();
  updateAuditDetail(log || null);
}

async function loadAuditLogs() {
  if (!auditTable) return;
  if (!currentAppId) {
    auditTable.innerHTML = "<div class=\"detail-label\">请先选择应用。</div>";
    updateAuditDetail(null);
    return;
  }
  try {
    const res = await fetchAuditLogs({
      walletId: state.walletId,
      appId: currentAppId,
      entityType: auditEntityType?.value || undefined,
      entityId: (auditEntityId?.value || "").trim() || undefined,
      action: auditAction?.value || undefined,
      operatorWalletId: (auditOperator?.value || "").trim() || undefined,
      limit: 50,
      offset: 0,
    });
    state.auditLogs = res.items || [];
    if (state.selectedAuditId) {
      const exists = state.auditLogs.some((log) => log.id === state.selectedAuditId);
      if (!exists) state.selectedAuditId = null;
    }
    if (!state.selectedAuditId && state.auditLogs.length) {
      state.selectedAuditId = state.auditLogs[0].id;
    }
    renderAuditTable();
    updateAuditDetail((state.auditLogs || []).find((log) => log.id === state.selectedAuditId) || null);
    setHint(auditHint, "");
  } catch (err) {
    state.auditLogs = [];
    state.selectedAuditId = null;
    renderAuditTable();
    updateAuditDetail(null);
    setHint(auditHint, `加载失败: ${err.message}`, "error");
  }
}

function exportAuditLogs() {
  const rows = state.auditLogs || [];
  if (!rows.length) {
    setHint(auditHint, "没有可导出的审计日志。");
    return;
  }
  setHint(auditHint, "");
  const blob = new Blob([JSON.stringify(rows, null, 2)], {
    type: "application/json",
  });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `audit-${Date.now()}.json`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function openNewDocDrawer() {
  resetDocForm();
  updateDocDrawerMeta(null);
  setDrawerOpen(true);
  docTextInput.focus();
}

function selectDoc(docId) {
  const doc = state.documents.find((item) => item.id === docId);
  if (!doc) return;
  state.selectedDocId = docId;
  setDocFormFields(doc);
  renderDocTable();
  updateDocDrawerMeta(doc);
  setDrawerOpen(true);
}

function getSelectedKb() {
  return state.knowledgeBases.find((kb) => kb.id === state.selectedKb);
}

function buildDocColumns(docs, textField) {
  const counts = new Map();
  docs.forEach((doc) => {
    const props = doc.properties || {};
    Object.keys(props).forEach((key) => {
      if (key === textField) return;
      counts.set(key, (counts.get(key) || 0) + 1);
    });
  });
  const extraKeys = Array.from(counts.entries())
    .sort((a, b) => b[1] - a[1])
    .slice(0, 4)
    .map(([key]) => key);
  return ["id", textField || "text", ...extraKeys];
}

function buildDocGridTemplate(count, includeSelect = false) {
  const columns = [];
  if (includeSelect) {
    columns.push("44px");
  }
  if (count <= 2) {
    columns.push("1.2fr", "2.6fr");
    return columns.join(" ");
  }
  columns.push("1.2fr", "2.6fr");
  for (let i = 2; i < count; i += 1) {
    columns.push("1fr");
  }
  return columns.join(" ");
}

function renderCell(value) {
  if (value === null || value === undefined || value === "") {
    return "<span class=\"cell-muted\">-</span>";
  }
  let text = value;
  if (typeof value !== "string") {
    try {
      text = JSON.stringify(value);
    } catch (err) {
      text = String(value);
    }
  }
  const output = text.length > 160 ? `${text.slice(0, 160)}...` : text;
  return `<span title="${escapeHtml(text)}">${escapeHtml(output)}</span>`;
}

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function compactId(value, head = 8, tail = 4) {
  const text = String(value || "");
  if (!text) return "-";
  if (text.length <= head + tail + 3) return text;
  return `${text.slice(0, head)}...${text.slice(-tail)}`;
}

function resolveStatusClass(status) {
  const value = String(status || "").toLowerCase();
  if (value.includes("ok") || value.includes("active") || value.includes("ready")) return "status-ok";
  if (value.includes("pending") || value.includes("init")) return "status-pending";
  if (value.includes("fail") || value.includes("error")) return "status-failed";
  return "status-configured";
}

function getDocFilters() {
  return {
    dataWalletId: (docDataWalletFilter?.value || "").trim(),
    privateDbId: (docPrivateDbFilter?.value || "").trim(),
    sessionId: (docSessionFilter?.value || "").trim(),
  };
}


async function toggleSchema() {
  const kb = getSelectedKb();
  if (!kb) {
    schemaPanel.textContent = "请先选择知识库。";
    schemaPanel.classList.remove("hidden");
    schemaToggle.textContent = "收起字段";
    return;
  }
  const isHidden = schemaPanel.classList.contains("hidden");
  if (!isHidden) {
    schemaPanel.classList.add("hidden");
    schemaToggle.textContent = "字段结构";
    return;
  }
  schemaToggle.textContent = "收起字段";
  schemaPanel.classList.remove("hidden");
  schemaPanel.textContent = "字段结构加载中...";

  let docs = state.documents;
  if (!docs.length) {
    try {
      const { dataWalletId, privateDbId, sessionId } = getDocFilters();
      if (sessionId && !dataWalletId) {
        schemaPanel.textContent = "使用 session_id 过滤时需先填写业务用户 wallet_id。";
        return;
      }
      const res = await fetchKBDocuments(kb.app_id, kb.kb_key, 25, 0, state.walletId, {
        dataWalletId,
        privateDbId,
        sessionId,
      });
      docs = res.items || [];
    } catch (err) {
      schemaPanel.textContent = `加载失败: ${err.message}`;
      return;
    }
  }

  const schema = inferSchema(docs);
  schemaPanel.innerHTML = renderSchema(schema);
}

function inferSchema(docs) {
  const map = new Map();
  docs.forEach((doc) => {
    const props = doc.properties || {};
    Object.entries(props).forEach(([key, value]) => {
      const entry = map.get(key) || { types: new Set(), example: null };
      const type = normalizeSchemaType(value);
      entry.types.add(type);
      if (entry.example === null && value !== null && value !== undefined) {
        entry.example = value;
      }
      map.set(key, entry);
    });
  });

  return Array.from(map.entries())
    .map(([name, entry]) => ({
      name,
      types: Array.from(entry.types.values()).sort(),
      example: entry.example,
    }))
    .sort((a, b) => a.name.localeCompare(b.name));
}

function normalizeSchemaType(value) {
  if (value === null) return "空值";
  if (Array.isArray(value)) return "数组";
  const type = typeof value;
  if (type === "object") return "对象";
  if (type === "string") return "字符串";
  if (type === "number") return "数值";
  if (type === "boolean") return "布尔";
  return "其他";
}

function renderSchema(schema) {
  if (!schema.length) {
    return "<div>暂无文档用于推断字段结构。</div>";
  }
  return schema
    .map((field) => {
      const types = escapeHtml(field.types.join(" | "));
      const example = escapeHtml(formatSchemaValue(field.example));
      return `<div><strong>${escapeHtml(field.name)}</strong> (${types})<br /><span>${example}</span></div>`;
    })
    .join("<br />");
}

function formatSchemaValue(value) {
  if (value === null || value === undefined) return "-";
  try {
    const raw = typeof value === "string" ? value : JSON.stringify(value);
    return raw.length > 140 ? `${raw.slice(0, 140)}...` : raw;
  } catch (err) {
    return String(value);
  }
}

function renderTimeline() {
  ingestionHint.textContent = "";
  if (!state.ingestion.length) {
    timeline.innerHTML = "<div class=\"timeline-item\">暂无摄取事件。</div>";
    return;
  }
  timeline.innerHTML = state.ingestion
    .map(
      (item) => `
      <div class="timeline-item">
        <strong>${item.title}</strong>
        <span>${item.time}</span>
        <span>${item.meta}</span>
      </div>
    `
    )
    .join("");
}

function mapIngestion(payload) {
  if (!payload || !Array.isArray(payload.items)) return null;
  return payload.items.slice(0, 6).map((item) => ({
    title: `${item.status.toUpperCase()} ${item.kb_key || ""}`.trim(),
    time: item.created_at || "-",
    meta: item.message || item.collection || "",
  }));
}

function resetDocForm(options = {}) {
  const { render = true } = options;
  state.selectedDocId = null;
  setDocFormFields(null);
  if (render) {
    renderDocTable();
  }
}

async function handleDocSubmit(event) {
  event.preventDefault();
  const kb = getSelectedKb();
  if (!kb) {
    docHint.textContent = "请先选择知识库。";
    return;
  }

  let props = {};
  if (docPropsInput.value.trim()) {
    try {
      props = JSON.parse(docPropsInput.value);
    } catch (err) {
      docHint.textContent = "属性 JSON 格式无效。";
      return;
    }
  }

  const payload = {
    text: docTextInput.value.trim() || null,
    properties: props,
  };

  const docId = docIdInput.value.trim();
  try {
    if (state.selectedDocId) {
      await updateKBDocument(kb.app_id, kb.kb_key, docId || state.selectedDocId, payload, state.walletId);
      docHint.textContent = "文档已更新。";
    } else {
      await createKBDocument(kb.app_id, kb.kb_key, { ...payload, id: docId || null }, state.walletId);
      docHint.textContent = "文档已创建。";
    }
    await loadDocuments();
  } catch (err) {
    docHint.textContent = `保存失败: ${err.message}`;
  }
}

async function handleDocDelete() {
  const kb = getSelectedKb();
  if (!kb || !state.selectedDocId) {
    docHint.textContent = "请先选择文档。";
    return;
  }
  try {
    await deleteKBDocument(kb.app_id, kb.kb_key, state.selectedDocId, state.walletId);
    docHint.textContent = "文档已删除。";
    ensureSelectedDocIds();
    state.selectedDocIds.delete(state.selectedDocId);
    resetDocForm();
    updateDocDrawerMeta(null);
    await loadDocuments();
  } catch (err) {
    docHint.textContent = `删除失败: ${err.message}`;
  }
}

function renderMemorySessionTable() {
  if (!memorySessionTable) return;
  const rows = state.memorySessions || [];
  if (!rows.length) {
    memorySessionTable.innerHTML = renderEmptyState("暂无记忆会话", "请先产生会话或检查筛选条件。");
    if (memoryDetailPanel) {
      memoryDetailPanel.classList.remove("open");
    }
    return;
  }
  const header = `
    <div class="table-row header">
      <div>钱包</div>
      <div>会话</div>
      <div>消息数</div>
      <div>最近更新</div>
    </div>
  `;
  const body = rows
    .map((row) => {
      const active = state.selectedMemoryKey === row.memory_key ? "active" : "";
      const walletFull = escapeHtml(row.wallet_id || "-");
      const walletShort = escapeHtml(compactId(row.wallet_id || "-"));
      const sessionFull = escapeHtml(row.session_id || "-");
      const sessionShort = escapeHtml(compactId(row.session_id || "-"));
      return `
        <div class="table-row memory-session-row ${active}" data-memory-key="${row.memory_key}">
          <div title="${walletFull}">${walletShort}</div>
          <div title="${sessionFull}">${sessionShort}</div>
          <div>${row.message_count ?? 0}</div>
          <div>${row.last_message_at || row.updated_at || "-"}</div>
        </div>
      `;
    })
    .join("");
  memorySessionTable.innerHTML = header + body;
  memorySessionTable.querySelectorAll(".table-row[data-memory-key]").forEach((row) => {
    row.addEventListener("click", () => {
      const key = row.dataset.memoryKey;
      if (key && state.selectedMemoryKey === key && memoryDetailPanel?.classList.contains("open")) {
        state.selectedMemoryKey = null;
        state.selectedMemoryContextId = null;
        state.memoryContextSnapshot = null;
        updateMemoryDetail(null);
        state.memoryContexts = [];
        renderMemoryContextTable();
        renderMemorySessionTable();
        return;
      }
      selectMemorySession(key);
    });
  });
  if (memoryDetailPanel) {
    const activeRow = memorySessionTable.querySelector(
      `.memory-session-row[data-memory-key="${state.selectedMemoryKey}"]`
    );
    if (activeRow) {
      activeRow.insertAdjacentElement("afterend", memoryDetailPanel);
    } else {
      memoryDetailPanel.classList.remove("open");
    }
  }
}

function renderMemoryContextTable() {
  if (!memoryContextTable) return;
  const rows = state.memoryContexts || [];
  if (!rows.length) {
    memoryContextTable.innerHTML = renderEmptyState("暂无记忆条目", "当前会话没有可展示的记忆上下文。");
    return;
  }
  const header = `
    <div class="table-row header">
      <div>角色</div>
      <div>描述</div>
      <div>状态</div>
      <div>创建时间</div>
    </div>
  `;
  const body = rows
    .map((row) => {
      const active = state.selectedMemoryContextId === row.uid ? "active" : "";
      const status = row.is_summarized ? "已总结" : "未总结";
      return `
        <div class="table-row ${active}" data-memory-uid="${row.uid}">
          <div>${escapeHtml(row.role || "-")}</div>
          <div>${escapeHtml(row.description || "-")}</div>
          <div>${status}</div>
          <div>${row.created_at || "-"}</div>
        </div>
      `;
    })
    .join("");
  memoryContextTable.innerHTML = header + body;
  memoryContextTable.querySelectorAll(".table-row[data-memory-uid]").forEach((row) => {
    row.addEventListener("click", () => selectMemoryContext(row.dataset.memoryUid));
  });
}

function updateMemoryDetail(session) {
  if (!memoryDetailTitle || !memoryDetailSubtitle) return;
  if (!session) {
    memoryDetailTitle.textContent = "记忆详情";
    memoryDetailSubtitle.textContent = "选择会话查看记忆内容。";
    if (memoryDetailKey) memoryDetailKey.textContent = "-";
    if (memoryDetailCount) memoryDetailCount.textContent = "-";
    if (memoryDetailWallet) memoryDetailWallet.textContent = "-";
    if (memoryDetailSession) memoryDetailSession.textContent = "-";
    if (memoryDetailPanel) memoryDetailPanel.classList.remove("open");
    return;
  }
  memoryDetailTitle.textContent = "记忆详情";
  memoryDetailSubtitle.textContent = `钱包 ${session.wallet_id || "-"} · 会话 ${session.session_id || "-"}`;
  if (memoryDetailKey) memoryDetailKey.textContent = session.memory_key || "-";
  if (memoryDetailCount) memoryDetailCount.textContent = session.message_count ?? 0;
  if (memoryDetailWallet) memoryDetailWallet.textContent = session.wallet_id || "-";
  if (memoryDetailSession) memoryDetailSession.textContent = session.session_id || "-";
  if (memoryDetailPanel) memoryDetailPanel.classList.add("open");
}

function resetMemoryContextForm(context) {
  if (!memoryContextRole || !memoryContextDesc || !memoryContextHint) return;
  if (!context) {
    memoryContextRole.value = "user";
    memoryContextDesc.value = "";
    memoryContextHint.textContent = "请先选择记忆条目。";
    if (memoryContextRole) memoryContextRole.disabled = true;
    if (memoryContextDesc) memoryContextDesc.disabled = true;
    if (memoryContextSave) memoryContextSave.disabled = true;
    if (memoryContextReset) memoryContextReset.disabled = true;
    if (memoryContextText) {
      memoryContextText.textContent = "选择记忆条目查看内容。";
    }
    return;
  }
  memoryContextHint.textContent = "";
  if (memoryContextRole) memoryContextRole.disabled = false;
  if (memoryContextDesc) memoryContextDesc.disabled = false;
  if (memoryContextSave) memoryContextSave.disabled = false;
  if (memoryContextReset) memoryContextReset.disabled = false;
  ensureRoleOption(context.role);
  memoryContextRole.value = context.role || "user";
  memoryContextDesc.value = context.description || "";
  if (memoryContextText) {
    memoryContextText.textContent = context.content || "未加载内容。";
  }
}

function ensureRoleOption(role) {
  if (!memoryContextRole || !role) return;
  const hasOption = Array.from(memoryContextRole.options).some((opt) => opt.value === role);
  if (!hasOption) {
    const option = document.createElement("option");
    option.value = role;
    option.textContent = role;
    memoryContextRole.appendChild(option);
  }
}

function getSelectedMemorySession() {
  return (state.memorySessions || []).find((row) => row.memory_key === state.selectedMemoryKey) || null;
}

function getSelectedMemoryContext() {
  return (state.memoryContexts || []).find((row) => row.uid === state.selectedMemoryContextId) || null;
}

function selectMemorySession(memoryKey) {
  if (!memoryKey) return;
  state.selectedMemoryKey = memoryKey;
  state.selectedMemoryContextId = null;
  state.memoryContextSnapshot = null;
  updateMemoryDetail(getSelectedMemorySession());
  renderMemorySessionTable();
  loadMemoryContexts();
}

function selectMemoryContext(uid) {
  state.selectedMemoryContextId = uid;
  const ctx = getSelectedMemoryContext();
  state.memoryContextSnapshot = ctx ? { role: ctx.role, description: ctx.description || "" } : null;
  renderMemoryContextTable();
  resetMemoryContextForm(ctx);
}

async function loadMemorySessions() {
  if (!memorySessionTable) return;
  const dataWalletId = memoryWalletFilter?.value.trim();
  const sessionId = memorySessionFilter?.value.trim();
  try {
    const res = await fetchMemorySessions({
      appId: currentAppId || undefined,
      walletId: state.walletId,
      dataWalletId: dataWalletId || undefined,
      sessionId: sessionId || undefined,
      limit: 50,
      offset: 0,
    });
    state.memorySessions = res.items || [];
    state.memorySessionTotal = res.total ?? (res.items || []).length;
    if (!state.memorySessions.length) {
      state.selectedMemoryKey = null;
      state.selectedMemoryContextId = null;
    }
    if (state.selectedMemoryKey) {
      const exists = state.memorySessions.some((row) => row.memory_key === state.selectedMemoryKey);
      if (!exists) {
        state.selectedMemoryKey = null;
        state.selectedMemoryContextId = null;
      }
    }
  } catch (err) {
    state.memorySessions = [];
    state.memorySessionTotal = 0;
  }
  renderMemorySessionTable();
  updateMemoryDetail(getSelectedMemorySession());
  await loadMemoryContexts();
}

async function loadMemoryContexts() {
  if (!memoryContextTable) return;
  const memoryKey = state.selectedMemoryKey;
  if (!memoryKey) {
    state.memoryContexts = [];
    state.memoryContextTotal = 0;
    renderMemoryContextTable();
    resetMemoryContextForm(null);
    return;
  }
  try {
    const session = getSelectedMemorySession();
    const dataWalletId = session?.wallet_id || memoryWalletFilter?.value.trim() || undefined;
    const res = await fetchMemoryContexts(memoryKey, {
      limit: 50,
      offset: 0,
      includeContent: true,
      walletId: state.walletId,
      dataWalletId,
    });
    state.memoryContexts = res.items || [];
    state.memoryContextTotal = res.total ?? (res.items || []).length;
    if (state.selectedMemoryContextId) {
      const exists = state.memoryContexts.some((row) => row.uid === state.selectedMemoryContextId);
      if (!exists) {
        state.selectedMemoryContextId = state.memoryContexts[0]?.uid || null;
      }
    } else if (state.memoryContexts.length) {
      state.selectedMemoryContextId = state.memoryContexts[0].uid;
    }
    const ctx = getSelectedMemoryContext();
    state.memoryContextSnapshot = ctx ? { role: ctx.role, description: ctx.description || "" } : null;
  } catch (err) {
    state.memoryContexts = [];
    state.memoryContextTotal = 0;
  }
  renderMemoryContextTable();
  resetMemoryContextForm(getSelectedMemoryContext());
}

async function handleMemoryContextSubmit(event) {
  event.preventDefault();
  const ctx = getSelectedMemoryContext();
  if (!ctx) {
    if (memoryContextHint) {
      memoryContextHint.textContent = "请先选择记忆条目。";
    }
    return;
  }
  const nextRole = memoryContextRole?.value.trim() || ctx.role;
  const nextDesc = memoryContextDesc?.value.trim() || "";
  const snapshot = state.memoryContextSnapshot || {};
  if (snapshot.role === nextRole && (snapshot.description || "") === nextDesc) {
    if (memoryContextHint) {
      memoryContextHint.textContent = "没有可保存的修改。";
    }
    return;
  }
  try {
    const session = getSelectedMemorySession();
    const dataWalletId = session?.wallet_id || memoryWalletFilter?.value.trim() || undefined;
    const updated = await updateMemoryContext(
      ctx.uid,
      {
        role: nextRole,
        description: nextDesc || null,
      },
      state.walletId,
      dataWalletId
    );
    state.memoryContexts = state.memoryContexts.map((row) => (row.uid === ctx.uid ? updated : row));
    state.memoryContextSnapshot = { role: updated.role, description: updated.description || "" };
    if (memoryContextHint) {
      memoryContextHint.textContent = "记忆已更新。";
    }
    renderMemoryContextTable();
    resetMemoryContextForm(updated);
  } catch (err) {
    if (memoryContextHint) {
      memoryContextHint.textContent = `更新失败: ${err.message}`;
    }
  }
}

function resetMemoryContextChanges() {
  const ctx = getSelectedMemoryContext();
  if (!ctx) return;
  const snapshot = state.memoryContextSnapshot || { role: ctx.role, description: ctx.description || "" };
  ensureRoleOption(snapshot.role);
  if (memoryContextRole) {
    memoryContextRole.value = snapshot.role || "user";
  }
  if (memoryContextDesc) {
    memoryContextDesc.value = snapshot.description || "";
  }
  if (memoryContextHint) {
    memoryContextHint.textContent = "已恢复修改。";
  }
}

function exportIngestionLogs() {
  const payload = state.ingestionRaw.length ? state.ingestionRaw : state.ingestion;
  if (!payload.length) {
    ingestionHint.textContent = "没有可导出的摄取日志。";
    return;
  }
  ingestionHint.textContent = "";
  const blob = new Blob([JSON.stringify(payload, null, 2)], {
    type: "application/json",
  });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `ingestion-${Date.now()}.json`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function scrollToSection(section) {
  const target = document.querySelector(`[data-section="${section}"]`);
  if (!target) return;
  target.scrollIntoView({ behavior: "smooth", block: "start" });
}

function setKbTab(tab) {
  if (!tab) return;
  kbTabButtons.forEach((button) => {
    const isActive = button.dataset.tab === tab;
    button.classList.toggle("active", isActive);
    button.setAttribute("aria-selected", isActive ? "true" : "false");
  });
  const panels = kbTabPanels.length
    ? kbTabPanels
    : Array.from(document.querySelectorAll(".tab-panel[data-tab-panel]"));
  panels.forEach((panel) => {
    const isActive = panel.dataset.tabPanel === tab;
    panel.classList.toggle("active", isActive);
    panel.setAttribute("aria-hidden", isActive ? "false" : "true");
  });
}

function setSidebarCollapsed(collapsed) {
  if (!layoutRoot) return;
  layoutRoot.classList.toggle("sidebar-collapsed", collapsed);
  if (sidebarToggle) {
    sidebarToggle.textContent = collapsed ? "展开侧栏" : "收起侧栏";
    sidebarToggle.setAttribute("aria-pressed", collapsed ? "true" : "false");
  }
  try {
    localStorage.setItem(SIDEBAR_COLLAPSED_KEY, collapsed ? "1" : "0");
  } catch {
  }
}

function loadSidebarState() {
  const stored = localStorage.getItem(SIDEBAR_COLLAPSED_KEY);
  setSidebarCollapsed(stored === "1");
}

function setActiveNav(section) {
  if (!section || !navItems.length) return;
  navItems.forEach((item) => {
    item.classList.toggle("active", item.dataset.nav === section);
  });
}

function setupNavObserver() {
  const sections = Array.from(document.querySelectorAll("[data-section]"));
  if (!sections.length || typeof IntersectionObserver === "undefined") return;
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          setActiveNav(entry.target.dataset.section);
        }
      });
    },
    { rootMargin: "-35% 0px -55% 0px", threshold: 0.1 }
  );
  sections.forEach((section) => observer.observe(section));
}

apiBaseInput.addEventListener("change", (event) => {
  setApiBase(event.target.value.trim());
  loadData();
});
refreshBtn.addEventListener("click", () => loadData());
backBtn.addEventListener("click", () => {
  window.location.href = "./index.html";
});
if (loginBtn) {
  loginBtn.addEventListener("click", () => {
    const next = encodeURIComponent(`${window.location.pathname}${window.location.search}`);
    window.location.href = `./login.html?next=${next}`;
  });
}
appSwitch.addEventListener("change", (event) => {
  const nextApp = event.target.value;
  if (!nextApp) return;
  window.location.href = `./app.html?app_id=${encodeURIComponent(nextApp)}`;
});
appNewDoc.addEventListener("click", () => {
  setKbTab("data");
  scrollToSection("knowledge");
  openNewDocDrawer();
});
appIngestion.addEventListener("click", () => {
  scrollToSection("ingestion");
});
if (appApiTest) {
  appApiTest.addEventListener("click", () => {
    const appId = currentAppId || "";
    const target = appId ? `./api_test.html?app_id=${encodeURIComponent(appId)}` : "./api_test.html";
    window.location.href = target;
  });
}
if (kbViewTabs) {
  kbTabButtons.forEach((button) => {
    button.addEventListener("click", (event) => {
      event.preventDefault();
      setKbTab(button.dataset.tab);
    });
  });
  kbViewTabs.addEventListener("click", (event) => {
    if (!(event.target instanceof Element)) return;
    const button = event.target.closest(".tab-button");
    if (!button || !kbViewTabs.contains(button)) return;
    setKbTab(button.dataset.tab);
  });
  const defaultTab = kbTabButtons.find((button) => button.classList.contains("active"))?.dataset.tab || "structure";
  setKbTab(defaultTab);
}
kbFilterToggle.addEventListener("click", () => {
  kbFilterPanel.classList.toggle("hidden");
});
schemaToggle.addEventListener("click", () => toggleSchema());
kbSearch.addEventListener("input", () => renderKbTable());
if (kbConfigForm) {
  kbConfigForm.addEventListener("submit", handleKbConfigSubmit);
}
if (kbConfigNew) {
  kbConfigNew.addEventListener("click", () => resetKbConfigForm());
}
if (kbConfigDelete) {
  kbConfigDelete.addEventListener("click", () => handleKbConfigDelete());
}
if (kbConfigType && kbConfigAllowed) {
  kbConfigType.addEventListener("change", () => {
    if (isUserUploadType(kbConfigType.value)) {
      if (kbConfigAllowed.value === "false") {
        kbConfigAllowed.value = "true";
      }
    } else {
      kbConfigAllowed.value = "false";
    }
    updateSchemaStatus();
  });
}
if (kbConfigTextField) {
  kbConfigTextField.addEventListener("input", () => updateSchemaStatus());
}
if (kbSchemaAdd) {
  kbSchemaAdd.addEventListener("click", () => {
    kbSchemaDraft.push({ name: "", data_type: "text", vectorize: false, description: "" });
    renderKbSchemaEditor();
  });
}
docSearch.addEventListener("input", () => {
  renderDocTable();
  if (docExportHint) {
    docExportHint.textContent = "";
  }
});
docRefresh.addEventListener("click", () => loadDocuments());
if (docDataWalletFilter) {
  docDataWalletFilter.addEventListener("change", () => {
    state.docPageOffset = 0;
    loadDocuments();
  });
  docDataWalletFilter.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      state.docPageOffset = 0;
      loadDocuments();
    }
  });
}
if (docPrivateDbFilter) {
  docPrivateDbFilter.addEventListener("change", () => {
    state.docPageOffset = 0;
    loadDocuments();
  });
  docPrivateDbFilter.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      state.docPageOffset = 0;
      loadDocuments();
    }
  });
}
if (docSessionFilter) {
  docSessionFilter.addEventListener("change", () => {
    state.docPageOffset = 0;
    loadDocuments();
  });
  docSessionFilter.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      state.docPageOffset = 0;
      loadDocuments();
    }
  });
}
if (docToggle) {
  docToggle.addEventListener("click", () => toggleDocPanel());
}
if (docColumnsToggle) {
  docColumnsToggle.addEventListener("click", () => toggleDocColumnsPanel());
}
if (docExport) {
  docExport.addEventListener("click", () => exportDocuments());
}
if (docBulkExport) {
  docBulkExport.addEventListener("click", () => exportSelectedDocuments());
}
if (docBulkDelete) {
  docBulkDelete.addEventListener("click", () => deleteSelectedDocuments());
}
if (docPageSize) {
  docPageSize.addEventListener("change", (event) => {
    const next = Number.parseInt(event.target.value, 10);
    if (Number.isNaN(next)) return;
    updateDocPageSize(next);
  });
}
if (docPrev) {
  docPrev.addEventListener("click", () => {
    updateDocPageOffset(state.docPageOffset - state.docPageSize);
  });
}
if (docNext) {
  docNext.addEventListener("click", () => {
    updateDocPageOffset(state.docPageOffset + state.docPageSize);
  });
}
docReset.addEventListener("click", () => openNewDocDrawer());
docDelete.addEventListener("click", () => handleDocDelete());
docForm.addEventListener("submit", handleDocSubmit);
if (memoryRefresh) {
  memoryRefresh.addEventListener("click", () => loadMemorySessions());
}
if (memoryWalletFilter) {
  memoryWalletFilter.addEventListener("input", () => loadMemorySessions());
}
if (memorySessionFilter) {
  memorySessionFilter.addEventListener("input", () => loadMemorySessions());
}
if (memoryContextRefresh) {
  memoryContextRefresh.addEventListener("click", () => loadMemoryContexts());
}
if (memoryContextForm) {
  memoryContextForm.addEventListener("submit", handleMemoryContextSubmit);
}
if (memoryContextReset) {
  memoryContextReset.addEventListener("click", () => resetMemoryContextChanges());
}
if (privateDbRefresh) {
  privateDbRefresh.addEventListener("click", () => loadPrivateDbs());
}
if (privateDbOwnerFilter) {
  privateDbOwnerFilter.addEventListener("input", () => loadPrivateDbs());
}
if (privateDbSessionsRefresh) {
  privateDbSessionsRefresh.addEventListener("click", () => loadPrivateDbSessions());
}
if (privateDbCreate) {
  privateDbCreate.addEventListener("click", () => handlePrivateDbCreate());
}
if (privateDbBind) {
  privateDbBind.addEventListener("click", () => handlePrivateDbBind());
}
if (intentRefresh) {
  intentRefresh.addEventListener("click", () => loadIntentConfigs());
}
if (intentAdd) {
  intentAdd.addEventListener("click", () => {
    intentDraft.push({ name: "", description: "", params: [], exposed: true });
    renderIntentTable();
  });
}
if (intentSave) {
  intentSave.addEventListener("click", () => saveIntentConfigs());
}
if (intentReset) {
  intentReset.addEventListener("click", () => resetIntentConfigs());
}
if (workflowRefresh) {
  workflowRefresh.addEventListener("click", () => loadWorkflowConfigs());
}
if (workflowAdd) {
  workflowAdd.addEventListener("click", () => {
    workflowDraft.push({ name: "", description: "", intents: [], enabled: true });
    renderWorkflowTable();
  });
}
if (workflowSave) {
  workflowSave.addEventListener("click", () => saveWorkflowConfigs());
}
if (workflowReset) {
  workflowReset.addEventListener("click", () => resetWorkflowConfigs());
}

if (pluginRefresh) {
  pluginRefresh.addEventListener("click", () => loadPluginFiles());
}
if (pluginSave) {
  pluginSave.addEventListener("click", () => savePluginFile());
}
if (pluginReset) {
  pluginReset.addEventListener("click", () => resetPluginEditor());
}
if (pluginNewPrompt) {
  pluginNewPrompt.addEventListener("click", () => createNewPrompt());
}
if (pluginOpenPipeline) {
  pluginOpenPipeline.addEventListener("click", () => openPipelineFile());
}
if (pluginEditor) {
  pluginEditor.addEventListener("input", () => {
    if (!state.selectedPluginPath) return;
    const changed = hasPluginChanges();
    setHint(pluginHint, changed ? "已修改，记得保存。" : "");
  });
}
if (auditRefresh) {
  auditRefresh.addEventListener("click", () => loadAuditLogs());
}
if (auditExport) {
  auditExport.addEventListener("click", () => exportAuditLogs());
}
if (auditEntityType) {
  auditEntityType.addEventListener("change", () => loadAuditLogs());
}
if (auditAction) {
  auditAction.addEventListener("change", () => loadAuditLogs());
}
if (auditEntityId) {
  auditEntityId.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      loadAuditLogs();
    }
  });
}
if (auditOperator) {
  auditOperator.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      loadAuditLogs();
    }
  });
}
ingestionExport.addEventListener("click", () => exportIngestionLogs());
if (docDrawerBackdrop) {
  docDrawerBackdrop.addEventListener("click", () => closeDocDrawer());
}
if (docDrawerClose) {
  docDrawerClose.addEventListener("click", () => closeDocDrawer());
}
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && docDrawer?.classList.contains("open")) {
    closeDocDrawer();
  }
});

if (navItems.length) {
  navItems.forEach((item) => {
    item.addEventListener("click", () => {
      const target = item.dataset.nav;
      if (!target) return;
      scrollToSection(target);
      setActiveNav(target);
    });
  });
  setupNavObserver();
}

if (navActions.length) {
  navActions.forEach((btn) => {
    btn.addEventListener("click", () => {
      const action = btn.dataset.action;
      if (!action) return;
      if (action === "kb-new") {
        setKbTab("structure");
        scrollToSection("knowledge");
        resetKbConfigForm();
        kbConfigKey?.focus();
        return;
      }
      if (action === "kb-schema") {
        setKbTab("structure");
        scrollToSection("knowledge");
        kbSchemaAdd?.focus();
        return;
      }
      if (action === "doc-new") {
        setKbTab("data");
        scrollToSection("knowledge");
        openNewDocDrawer();
        return;
      }
      if (action === "audit") {
        scrollToSection("audit");
        return;
      }
      if (action === "orchestration") {
        scrollToSection("orchestration");
        return;
      }
      if (action === "plugin") {
        scrollToSection("plugin");
        return;
      }
    });
  });
}

if (sidebarToggle) {
  sidebarToggle.addEventListener("click", () => {
    const next = !layoutRoot?.classList.contains("sidebar-collapsed");
    setSidebarCollapsed(next);
  });
  loadSidebarState();
}

apiBaseInput.value = loadApiBase();
loadWalletId();
const loggedIn = ensureLoggedIn();
if (loggedIn) {
  renderIdentity();
  if (docPageSize) {
    docPageSize.value = String(state.docPageSize);
  }
  loadData();
}
