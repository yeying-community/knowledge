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
  fetchKBList,
  fetchKBStats,
  fetchKBDocuments,
  createKBDocument,
  updateKBDocument,
  deleteKBDocument,
  fetchIngestionLogs,
  fetchPrivateDBs,
  fetchPrivateDBSessions,
  unbindPrivateDBSession,
  fetchMemorySessions,
  fetchMemoryContexts,
  updateMemoryContext,
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
const docSessionFilter = document.getElementById("doc-session-filter");
const docPrivateDbFilter = document.getElementById("doc-private-db-filter");
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

const privateOwnerFilter = document.getElementById("private-owner-filter");
const privateSessionFilter = document.getElementById("private-session-filter");
const privateDbFilter = document.getElementById("private-db-filter");
const privateDbRefresh = document.getElementById("private-refresh");
const privateDbTable = document.getElementById("private-db-table");
const privateDbHint = document.getElementById("private-db-hint");


const timeline = document.getElementById("ingestion-timeline");
const ingestionExport = document.getElementById("ingestion-export");
const ingestionHint = document.getElementById("ingestion-hint");

let currentAppId = new URLSearchParams(window.location.search).get("app_id");
let privateDbCache = [];
let expandedPrivateDbId = null;
const privateDbSessionsCache = new Map();

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

  if (!state.selectedKb && state.knowledgeBases.length) {
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
    privateDbCache = [];
    renderPrivateDbTable();
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
      return {
        id,
        app_id: kb.app_id,
        kb_key: kb.kb_key,
        text_field: kb.text_field || "text",
        name: kb.kb_key,
        type: kb.kb_type || "kb",
        collection: kb.collection || "-",
        docs: stat.count,
        chunks: stat.chunks,
        owner: kb.app_id,
        access: kb.kb_type === "user_upload" ? "restricted" : "public",
        updated_at: kb.status ? `应用 ${kb.status}` : "未知",
        log: [
          `Top_k ${kb.top_k ?? "-"}`,
          `Weight ${kb.weight ?? "-"}`,
          kb.use_allowed_apps_filter ? "启用应用过滤" : "未启用应用过滤",
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
    await loadMemorySessions();
    await loadPrivateDbs();
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
    privateDbCache = [];
    renderPrivateDbTable();
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
      const badge = kb.access === "restricted" ? "受限" : "公开";
      return `
        <div class="table-row ${active}" data-kb="${kb.id}">
          <div>
            <strong>${kb.name}</strong>
            <div class="badge">${kb.owner}</div>
          </div>
          <div>${kb.type}</div>
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
        return `<label class="filter-chip"><input type="checkbox" data-filter="${key}" value="${item}" ${checked} />${item}</label>`;
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
  const scopeLabel = kb.type === "user_upload" ? "用户隔离" : "共享";
  detailSubtitle.textContent = `更新 ${kb.updated_at} · 应用 ${kb.owner} · ${scopeLabel}`;
  detailCollection.textContent = kb.collection;
  detailDocs.textContent = kb.docs;
  detailChunks.textContent = kb.chunks;
  detailAccess.textContent = kb.access === "restricted" ? "受限（用户隔离）" : "公开（共享）";
  detailLog.innerHTML = kb.log.map((line) => `> ${line}`).join("<br>");

  kb.histogram.forEach((value, index) => {
    const height = Math.min(100, Math.max(12, value));
    chartBars[index].style.height = `${height}%`;
  });

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
    const { sessionId, privateDbId } = getDocFilters();
    const res = await fetchKBDocuments(
      kb.app_id,
      kb.kb_key,
      state.docPageSize,
      state.docPageOffset,
      state.walletId,
      { sessionId, privateDbId }
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
    if (sessionId) filterNotes.push(`session ${sessionId}`);
    if (privateDbId) filterNotes.push(`private_db ${privateDbId}`);
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

function getDocFilters() {
  return {
    sessionId: (docSessionFilter?.value || "").trim(),
    privateDbId: (docPrivateDbFilter?.value || "").trim(),
  };
}

function getPrivateDbFilters() {
  return {
    ownerWalletId: (privateOwnerFilter?.value || "").trim(),
    sessionId: (privateSessionFilter?.value || "").trim(),
    privateDbId: (privateDbFilter?.value || "").trim(),
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
      const { sessionId, privateDbId } = getDocFilters();
      const res = await fetchKBDocuments(kb.app_id, kb.kb_key, 25, 0, state.walletId, {
        sessionId,
        privateDbId,
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
      return `
        <div class="table-row memory-session-row ${active}" data-memory-key="${row.memory_key}">
          <div>${escapeHtml(row.wallet_id || "-")}</div>
          <div>${escapeHtml(row.session_id || "-")}</div>
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

function renderPrivateDbTable() {
  if (!privateDbTable) return;
  const filters = getPrivateDbFilters();
  let rows = privateDbCache || [];
  if (filters.privateDbId) {
    rows = rows.filter((row) => String(row.private_db_id || "").includes(filters.privateDbId));
  }
  if (!rows.length) {
    privateDbTable.innerHTML = renderEmptyState("暂无私有库", "请检查应用与筛选条件。");
    return;
  }

  const header = `
    <div class="table-row header">
      <div>私有库</div>
      <div>Owner</div>
      <div>状态</div>
      <div>创建时间</div>
      <div>操作</div>
    </div>
  `;

  const body = rows
    .map((row) => {
      const active = expandedPrivateDbId === row.private_db_id ? "active" : "";
      const owner = escapeHtml(row.owner_wallet_id || "-");
      const status = escapeHtml(row.status || "-");
      const createdAt = row.created_at || "-";
      const badge = `<div class="badge">${escapeHtml(row.app_id || "-")}</div>`;
      return `
        <div class="table-row ${active}" data-private-db="${row.private_db_id}">
          <div>
            <strong>${escapeHtml(row.private_db_id || "-")}</strong>
            ${badge}
          </div>
          <div>${owner}</div>
          <div>${status}</div>
          <div>${createdAt}</div>
          <div class="panel-tools">
            <button class="ghost" data-private-sessions="${row.private_db_id}">会话</button>
          </div>
        </div>
      `;
    })
    .join("");

  const expandedRow = rows.find((row) => row.private_db_id === expandedPrivateDbId);
  let expandedBlock = "";
  if (expandedRow) {
    const sessionState = privateDbSessionsCache.get(expandedRow.private_db_id);
    if (!sessionState) {
      expandedBlock = `
        <div class="table-row expanded">
          <div class="detail-label">会话加载中...</div>
        </div>
      `;
    } else if (sessionState.error) {
      expandedBlock = `
        <div class="table-row expanded">
          <div class="detail-label text-danger">加载失败：${escapeHtml(sessionState.error)}</div>
        </div>
      `;
    } else if (!sessionState.sessions.length) {
      expandedBlock = `
        <div class="table-row expanded">
          <div class="detail-label">暂无绑定会话。</div>
        </div>
      `;
    } else {
      const sessionRows = sessionState.sessions
        .map(
          (item) => `
            <div class="session-item">
              <div>
                <div class="session-id">${escapeHtml(item.session_id)}</div>
                <div class="session-meta">${escapeHtml(item.created_at || "-")}</div>
              </div>
              <button class="ghost" data-private-unbind="${expandedRow.private_db_id}" data-session-id="${escapeHtml(
            item.session_id
          )}">解绑</button>
            </div>
          `
        )
        .join("");
      expandedBlock = `
        <div class="table-row expanded">
          <div class="session-list">${sessionRows}</div>
        </div>
      `;
    }
  }

  privateDbTable.innerHTML = header + body + expandedBlock;

  privateDbTable.querySelectorAll("button[data-private-sessions]").forEach((button) => {
    button.addEventListener("click", (event) => {
      event.stopPropagation();
      togglePrivateDbSessions(button.dataset.privateSessions);
    });
  });

  privateDbTable.querySelectorAll("button[data-private-unbind]").forEach((button) => {
    button.addEventListener("click", (event) => {
      event.stopPropagation();
      const privateDbId = button.dataset.privateUnbind;
      const sessionId = button.dataset.sessionId;
      if (privateDbId && sessionId) {
        handlePrivateDbUnbind(privateDbId, sessionId);
      }
    });
  });
}

async function togglePrivateDbSessions(privateDbId) {
  if (!privateDbId) return;
  if (expandedPrivateDbId === privateDbId) {
    expandedPrivateDbId = null;
    renderPrivateDbTable();
    return;
  }
  expandedPrivateDbId = privateDbId;
  if (!privateDbSessionsCache.has(privateDbId)) {
    privateDbSessionsCache.set(privateDbId, { sessions: [], error: null });
  }
  renderPrivateDbTable();
  try {
    const res = await fetchPrivateDBSessions(privateDbId, currentAppId, state.walletId);
    privateDbSessionsCache.set(privateDbId, { sessions: res.sessions || [], error: null });
  } catch (err) {
    privateDbSessionsCache.set(privateDbId, { sessions: [], error: err.message });
  }
  renderPrivateDbTable();
}

async function handlePrivateDbUnbind(privateDbId, sessionId) {
  if (!privateDbId || !sessionId) return;
  const ok = window.confirm(`确认解绑 session_id=${sessionId} 吗？`);
  if (!ok) return;
  try {
    await unbindPrivateDBSession(privateDbId, sessionId, currentAppId, state.walletId);
    const res = await fetchPrivateDBSessions(privateDbId, currentAppId, state.walletId);
    privateDbSessionsCache.set(privateDbId, { sessions: res.sessions || [], error: null });
    renderPrivateDbTable();
  } catch (err) {
    if (privateDbHint) {
      privateDbHint.textContent = `解绑失败: ${err.message}`;
    }
  }
}

async function loadPrivateDbs() {
  if (!privateDbTable) return;
  if (!currentAppId) {
    privateDbCache = [];
    renderPrivateDbTable();
    return;
  }
  const filters = getPrivateDbFilters();
  const ownerWalletId = isSuperAdmin() ? filters.ownerWalletId : "";
  const sessionId = filters.sessionId;
  if (!isSuperAdmin() && privateOwnerFilter) {
    privateOwnerFilter.value = "";
    privateOwnerFilter.disabled = true;
  } else if (privateOwnerFilter) {
    privateOwnerFilter.disabled = false;
  }
  try {
    const res = await fetchPrivateDBs({
      walletId: state.walletId,
      appId: currentAppId,
      ownerWalletId: ownerWalletId || undefined,
      sessionId: sessionId || undefined,
    });
    privateDbCache = res.items || [];
    if (expandedPrivateDbId && !privateDbCache.some((row) => row.private_db_id === expandedPrivateDbId)) {
      expandedPrivateDbId = null;
    }
    if (privateDbHint) {
      privateDbHint.textContent = "";
    }
  } catch (err) {
    privateDbCache = [];
    if (privateDbHint) {
      privateDbHint.textContent = `加载失败: ${err.message}`;
    }
  }
  renderPrivateDbTable();
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
docSearch.addEventListener("input", () => {
  renderDocTable();
  if (docExportHint) {
    docExportHint.textContent = "";
  }
});
docRefresh.addEventListener("click", () => loadDocuments());
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
if (privateDbRefresh) {
  privateDbRefresh.addEventListener("click", () => loadPrivateDbs());
}
if (privateOwnerFilter) {
  privateOwnerFilter.addEventListener("change", () => loadPrivateDbs());
}
if (privateSessionFilter) {
  privateSessionFilter.addEventListener("change", () => loadPrivateDbs());
}
if (privateDbFilter) {
  privateDbFilter.addEventListener("input", () => renderPrivateDbTable());
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
