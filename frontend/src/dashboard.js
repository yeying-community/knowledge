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
  fetchIngestionLogs,
} from "./api.js";

const apiBaseInput = document.getElementById("api-base");
const refreshBtn = document.getElementById("refresh-btn");
const statusDot = document.getElementById("api-status-dot");
const statusText = document.getElementById("api-status-text");
const rolePill = document.getElementById("role-pill");
const walletIdDisplay = document.getElementById("wallet-id-display");
const appsRefresh = document.getElementById("apps-refresh");
const heroIngestion = document.getElementById("hero-ingestion");
const heroStores = document.getElementById("hero-stores");
const heroValidation = document.getElementById("hero-validation");
const heroApiTest = document.getElementById("hero-api-test");
const heroJobs = document.getElementById("hero-jobs");
const heroSettings = document.getElementById("hero-settings");
const loginBtn = document.getElementById("login-btn");

const metricApps = document.getElementById("metric-apps");
const metricKbs = document.getElementById("metric-kbs");
const metricVectors = document.getElementById("metric-vectors");
const metricIngestion = document.getElementById("metric-ingestion");
const metricIngestionTrend = document.getElementById("metric-ingestion-trend");

const heroApiStatus = document.getElementById("hero-api-status");
const heroIngestionTime = document.getElementById("hero-ingestion-time");
const heroVectors = document.getElementById("hero-vectors");

const appSearch = document.getElementById("app-search");
const appGrid = document.getElementById("app-grid");

const timeline = document.getElementById("ingestion-timeline");
const ingestionExport = document.getElementById("ingestion-export");
const ingestionHint = document.getElementById("ingestion-hint");

function setStatus(online) {
  statusDot.style.background = online ? "#39d98a" : "#ff6a88";
  statusDot.style.boxShadow = online
    ? "0 0 12px rgba(57, 217, 138, 0.7)"
    : "0 0 12px rgba(255, 106, 136, 0.7)";
  statusText.textContent = online ? "在线" : "离线";
  if (heroApiStatus) {
    heroApiStatus.textContent = online ? "在线" : "离线";
  }
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
  state.knowledgeBases = data.knowledgeBases || [];
  state.ingestion = data.ingestion || [];
  state.ingestionRaw = data.ingestionRaw || [];
  state.vectors = data.vectors || 0;

  metricApps.textContent = state.apps.filter((app) => app.status === "active").length;
  metricKbs.textContent = state.knowledgeBases.length;
  metricVectors.textContent = new Intl.NumberFormat().format(state.vectors);
  if (metricIngestion) {
    metricIngestion.textContent = state.ingestionRaw.length;
  }
  if (metricIngestionTrend) {
    metricIngestionTrend.textContent = state.ingestionRaw[0]?.created_at || "暂无";
  }
  if (heroIngestionTime) {
    heroIngestionTime.textContent = state.ingestionRaw[0]?.created_at || "暂无";
  }
  if (heroVectors) {
    heroVectors.textContent = new Intl.NumberFormat().format(state.vectors);
  }

  renderAppGrid();
  renderTimeline();
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
    applyData(mockData);
    return;
  }

  try {
    const walletId = state.walletId;
    const [apps, kbList] = await Promise.all([
      fetchApps(walletId),
      fetchKBList(walletId),
    ]);

    const ingestionRaw = [];
    if (apps && apps.length) {
      const ingestionResults = await Promise.all(
        apps.map((app) =>
          fetchIngestionLogs({ appId: app.app_id, walletId, limit: 5, offset: 0 }).catch(() => ({ items: [] }))
        )
      );
      ingestionResults.forEach((res) => {
        (res.items || []).forEach((item) => ingestionRaw.push(item));
      });
      ingestionRaw.sort((a, b) => String(b.created_at || "").localeCompare(String(a.created_at || "")));
    }

    const kbStats = await Promise.all(
      (kbList || []).map(async (kb) => {
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
    const mappedKbs = (kbList || []).map((kb) => {
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
      };
    });

    const totalVectors = mappedKbs
      .map((kb) => (typeof kb.chunks === "number" ? kb.chunks : 0))
      .reduce((a, b) => a + b, 0);

    applyData({
      ...mockData,
      apps: apps || mockData.apps,
      knowledgeBases: mappedKbs.length ? mappedKbs : mockData.knowledgeBases,
      vectors: totalVectors,
      ingestion: mapIngestion({ items: ingestionRaw }) || mockData.ingestion,
      ingestionRaw,
    });
  } catch (err) {
    applyData(mockData);
  }
}

function renderAppGrid() {
  const query = (appSearch.value || "").toLowerCase();
  const apps = state.apps.filter((app) => {
    if (!query) return true;
    return app.app_id.toLowerCase().includes(query);
  });

  if (!apps.length) {
    appGrid.innerHTML = "<div class=\"detail-label\">未找到应用。</div>";
    return;
  }

  const appKbs = state.knowledgeBases.reduce((acc, kb) => {
    acc[kb.app_id] = acc[kb.app_id] || [];
    acc[kb.app_id].push(kb);
    return acc;
  }, {});

  appGrid.innerHTML = apps
    .map((app) => {
      const kbs = appKbs[app.app_id] || [];
      const vectors = kbs
        .map((kb) => (typeof kb.chunks === "number" ? kb.chunks : 0))
        .reduce((a, b) => a + b, 0);
      const link = `./app.html?app_id=${encodeURIComponent(app.app_id)}`;
      return `
        <div class="app-card">
          <div>
            <h3>${app.app_id}</h3>
            <div class="meta-row">
              <span>状态: ${app.status || "未知"}</span>
              <span>知识库: ${kbs.length}</span>
              <span>向量: ${new Intl.NumberFormat().format(vectors)}</span>
              <span>插件: ${app.has_plugin ? "启用" : "缺失"}</span>
            </div>
          </div>
          <div class="app-card-actions">
            <button class="primary" data-open="${link}">进入控制台</button>
            <button class="ghost" data-copy="${link}">复制链接</button>
          </div>
        </div>
      `;
    })
    .join("");

  appGrid.querySelectorAll("button[data-open]").forEach((button) => {
    button.addEventListener("click", () => {
      window.location.href = button.dataset.open;
    });
  });

  appGrid.querySelectorAll("button[data-copy]").forEach((button) => {
    button.addEventListener("click", () => copyLink(button.dataset.copy));
  });
}

function copyLink(path) {
  const url = new URL(path, window.location.href).toString();
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(url).then(() => {
      ingestionHint.textContent = "应用链接已复制。";
    });
    return;
  }
  ingestionHint.textContent = `请复制链接: ${url}`;
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

apiBaseInput.addEventListener("change", (event) => {
  setApiBase(event.target.value.trim());
  loadData();
});
refreshBtn.addEventListener("click", () => loadData());
appsRefresh.addEventListener("click", () => loadData());
heroIngestion.addEventListener("click", () => scrollToSection("activity"));
heroStores.addEventListener("click", () => {
  window.location.href = "./stores.html";
});
if (heroValidation) {
  heroValidation.addEventListener("click", () => {
    window.location.href = "./validation.html";
  });
}
if (heroApiTest) {
  heroApiTest.addEventListener("click", () => {
    window.location.href = "./api_test.html";
  });
}
if (heroJobs) {
  heroJobs.addEventListener("click", () => {
    window.location.href = "./ingestion_jobs.html";
  });
}
heroSettings.addEventListener("click", () => {
  window.location.href = "./settings.html";
});
if (loginBtn) {
  loginBtn.addEventListener("click", () => {
    const next = encodeURIComponent(`${window.location.pathname}${window.location.search}`);
    window.location.href = `./login.html?next=${next}`;
  });
}
appSearch.addEventListener("input", () => renderAppGrid());
ingestionExport.addEventListener("click", () => exportIngestionLogs());

apiBaseInput.value = loadApiBase();
loadWalletId();
const loggedIn = ensureLoggedIn();
if (loggedIn) {
  renderIdentity();
  loadData();
}
