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
  fetchKBList,
  createIngestionJob,
  fetchIngestionJobs,
  fetchIngestionJobRuns,
  fetchIngestionJobPresets,
  runIngestionJob,
} from "./api.js";

const apiBaseInput = document.getElementById("api-base");
const refreshBtn = document.getElementById("refresh-btn");
const statusDot = document.getElementById("api-status-dot");
const statusText = document.getElementById("api-status-text");
const rolePill = document.getElementById("role-pill");
const walletIdDisplay = document.getElementById("wallet-id-display");
const loginBtn = document.getElementById("login-btn");
const backBtn = document.getElementById("back-btn");

const metricTotal = document.getElementById("metric-total");
const metricRunning = document.getElementById("metric-running");
const metricFailed = document.getElementById("metric-failed");

const jobRefresh = document.getElementById("job-refresh");
const jobClear = document.getElementById("job-clear");

const jobForm = document.getElementById("job-form");
const jobAppSelect = document.getElementById("job-app-select");
const jobKbSelect = document.getElementById("job-kb-select");
const jobDataWallet = document.getElementById("job-data-wallet");
const jobSessionId = document.getElementById("job-session-id");
const jobPrivateDbId = document.getElementById("job-private-db-id");
const jobSourceUrl = document.getElementById("job-source-url");
const jobContent = document.getElementById("job-content");
const jobFilename = document.getElementById("job-filename");
const jobFileType = document.getElementById("job-file-type");
const jobPrefix = document.getElementById("job-prefix");
const jobPrefixRefresh = document.getElementById("job-prefix-refresh");
const jobRecentKeys = document.getElementById("job-recent-keys");
const jobRunNow = document.getElementById("job-run-now");
const jobMetadata = document.getElementById("job-metadata");
const jobOptions = document.getElementById("job-options");
const jobReset = document.getElementById("job-reset");
const jobHint = document.getElementById("job-hint");

const jobsTable = document.getElementById("jobs-table");
const jobsHint = document.getElementById("jobs-hint");
const jobsAppSelect = document.getElementById("jobs-app-select");
const jobsDataWallet = document.getElementById("jobs-data-wallet");
const jobsSessionId = document.getElementById("jobs-session-id");
const jobsPrivateDbId = document.getElementById("jobs-private-db-id");
const jobsStatusSelect = document.getElementById("jobs-status-select");
const jobsRefresh = document.getElementById("jobs-refresh");

const jobOutput = document.getElementById("job-output");
const jobOutputTitle = document.getElementById("job-output-title");
const jobOutputCopy = document.getElementById("job-output-copy");
const jobOutputClear = document.getElementById("job-output-clear");
const jobOutputHint = document.getElementById("job-output-hint");

let kbCache = [];
let jobCache = [];
let selectedJobId = null;

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
}

function escapeHtml(value) {
  return String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function setHint(el, text, tone = "") {
  if (!el) return;
  el.textContent = text || "";
  el.classList.toggle("text-danger", tone === "error");
}

function normalizeJson(value, fallback = {}) {
  const raw = (value || "").trim();
  if (!raw) return fallback;
  try {
    return JSON.parse(raw);
  } catch (err) {
    throw new Error("JSON 解析失败");
  }
}

function statusBadge(status) {
  const normalized = String(status || "").toLowerCase();
  if (normalized === "success") return { label: "成功", className: "status-ok" };
  if (normalized === "running") return { label: "运行中", className: "status-running" };
  if (normalized === "failed") return { label: "失败", className: "status-failed" };
  if (normalized === "pending") return { label: "等待中", className: "status-pending" };
  return { label: normalized || "未知", className: "status-unknown" };
}

function updateMetrics() {
  const total = jobCache.length;
  const running = jobCache.filter((job) => job.status === "running").length;
  const failed = jobCache.filter((job) => job.status === "failed").length;
  metricTotal.textContent = String(total);
  metricRunning.textContent = String(running);
  metricFailed.textContent = String(failed);
}

function renderJobs() {
  if (!jobsTable) return;
  if (!jobCache.length) {
    jobsTable.innerHTML = "<div class=\"detail-label\">暂无作业记录。</div>";
    updateMetrics();
    return;
  }

  const header = `
    <div class="table-row header">
      <div>ID</div>
      <div>操作钱包</div>
      <div>业务用户钱包</div>
      <div>应用</div>
      <div>KB</div>
      <div>状态</div>
      <div>来源</div>
      <div>操作</div>
    </div>
  `;

  const rows = jobCache
    .map((job) => {
      const badge = statusBadge(job.status);
      const source = job.source_url ? escapeHtml(job.source_url) : "-";
      const operatorId = escapeHtml(job.wallet_id || "-");
      const dataWallet = job.data_wallet_id ? escapeHtml(job.data_wallet_id) : "共享";
      const appId = escapeHtml(job.app_id);
      const kbKey = escapeHtml(job.kb_key);
      return `
        <div class="table-row">
          <div class="cell-muted">#${job.id}</div>
          <div class="cell-muted">${operatorId}</div>
          <div>${dataWallet}</div>
          <div>${appId}</div>
          <div>${kbKey}</div>
          <div><span class="status-pill ${badge.className}">${badge.label}</span></div>
          <div class="cell-muted">${source}</div>
          <div class="panel-tools">
            <button class="ghost" data-run="${job.id}">运行</button>
            <button class="ghost" data-detail="${job.id}">详情</button>
          </div>
        </div>
      `;
    })
    .join("");

  jobsTable.innerHTML = header + rows;
  jobsTable.querySelectorAll("button[data-run]").forEach((btn) => {
    btn.addEventListener("click", () => runJob(btn.dataset.run));
  });
  jobsTable.querySelectorAll("button[data-detail]").forEach((btn) => {
    btn.addEventListener("click", () => showJobDetail(btn.dataset.detail));
  });
  updateMetrics();
}

function renderJobOutput(payload) {
  if (!payload) {
    jobOutput.textContent = "尚未选择作业。";
    jobOutputTitle.textContent = "作业详情";
    return;
  }
  jobOutputTitle.textContent = `作业 #${payload.job?.id || "-"}`;
  jobOutput.textContent = JSON.stringify(payload, null, 2);
}

async function showJobDetail(jobId) {
  selectedJobId = Number(jobId);
  const job = jobCache.find((item) => String(item.id) === String(jobId));
  if (!job) {
    renderJobOutput(null);
    return;
  }
  try {
    const runs = await fetchIngestionJobRuns(job.id, state.walletId);
    renderJobOutput({ job, runs: runs.items || [] });
  } catch (err) {
    renderJobOutput({ job, runs: [], error: err.message });
  }
}

async function runJob(jobId) {
  try {
    await runIngestionJob(jobId, state.walletId);
    await loadJobs();
    await showJobDetail(jobId);
  } catch (err) {
    setHint(jobsHint, `运行失败：${err.message}`, "error");
  }
}

function fillAppOptions(apps) {
  jobAppSelect.innerHTML = (apps || [])
    .map((app) => `<option value="${escapeHtml(app.app_id)}">${escapeHtml(app.app_id)}</option>`)
    .join("");
  const options = [
    `<option value="">全部应用</option>`,
    ...(apps || []).map(
      (app) => `<option value="${escapeHtml(app.app_id)}">${escapeHtml(app.app_id)}</option>`
    ),
  ];
  jobsAppSelect.innerHTML = options.join("");
}

function fillKbOptions(appId) {
  const kbs = kbCache.filter((kb) => kb.app_id === appId);
  if (!kbs.length) {
    jobKbSelect.innerHTML = "<option value=\"\">暂无 KB</option>";
    jobKbSelect.disabled = true;
    renderRecentKeys(null);
    return;
  }
  jobKbSelect.disabled = false;
  jobKbSelect.innerHTML = kbs
    .map((kb) => `<option value="${escapeHtml(kb.kb_key)}">${escapeHtml(kb.kb_key)}</option>`)
    .join("");
}

function getSelectedKbType() {
  const appId = jobAppSelect.value;
  const kbKey = jobKbSelect.value;
  const kbItem = kbCache.find((kb) => kb.app_id === appId && kb.kb_key === kbKey);
  return kbItem?.kb_type || kbItem?.type || "";
}

function updateDataWalletField() {
  if (!jobDataWallet) return;
  const kbType = getSelectedKbType();
  const isUserUpload = kbType === "user_upload";
  jobDataWallet.disabled = !isUserUpload;
  jobDataWallet.placeholder = isUserUpload ? "业务用户 wallet_id（可选）" : "共享 KB 无需填写";
  if (!isUserUpload) {
    jobDataWallet.value = "";
  }
}

function renderRecentKeys(preset) {
  if (!jobRecentKeys) return;
  const kbType = getSelectedKbType();
  const keys = preset?.recent_keys || [];
  if (jobPrefix) {
    const ownerWallet = (jobDataWallet?.value || "").trim() || state.walletId || "";
    const scopeLabel = kbType === "user_upload" ? `业务用户钱包 ${ownerWallet || "-"}` : "共享 KB";
    jobPrefix.textContent = preset?.prefix ? `${scopeLabel} · 默认路径：${preset.prefix}` : "";
  }
  if (!keys.length) {
    jobRecentKeys.innerHTML = "<span class=\"detail-label\">暂无文件记录。</span>";
    return;
  }
  jobRecentKeys.innerHTML = keys
    .slice(0, 12)
    .map((key) => `<button type="button" class="pill" data-key="${escapeHtml(key)}">${escapeHtml(key)}</button>`)
    .join("");

  jobRecentKeys.querySelectorAll("button[data-key]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const key = btn.dataset.key || "";
      if (!preset?.bucket) return;
      jobSourceUrl.value = `minio://${preset.bucket}/${key}`;
      if (!jobFileType.value) {
        const suffix = key.split(".").pop();
        if (suffix && suffix !== key) {
          jobFileType.value = suffix;
        }
      }
    });
  });
}

async function loadPresets() {
  const appId = jobAppSelect.value;
  const kbKey = jobKbSelect.value;
  if (!appId || !kbKey) {
    renderRecentKeys(null);
    return;
  }
  try {
    const dataWalletId = (jobDataWallet?.value || "").trim();
    const preset = await fetchIngestionJobPresets(appId, kbKey, state.walletId, 30, dataWalletId);
    renderRecentKeys(preset);
  } catch (err) {
    renderRecentKeys(null);
  }
}

async function loadAppsAndKbs() {
  const walletId = state.walletId;
  const [apps, kbList] = await Promise.all([
    fetchApps(walletId),
    fetchKBList(walletId),
  ]);
  state.apps = apps || [];
  kbCache = kbList || [];
  fillAppOptions(state.apps);
  if (jobAppSelect.value) {
    fillKbOptions(jobAppSelect.value);
  } else if (state.apps[0]) {
    jobAppSelect.value = state.apps[0].app_id;
    fillKbOptions(jobAppSelect.value);
  }
  updateDataWalletField();
  await loadPresets();
}

async function loadJobs() {
  const walletId = state.walletId;
  const appId = jobsAppSelect.value || undefined;
  const status = jobsStatusSelect.value || undefined;
  const dataWalletId = (jobsDataWallet?.value || "").trim() || undefined;
  const sessionId = (jobsSessionId?.value || "").trim() || undefined;
  const privateDbId = (jobsPrivateDbId?.value || "").trim() || undefined;
  if ((sessionId || privateDbId) && !appId) {
    setHint(jobsHint, "使用 session/private_db 过滤时需先选择应用。", "error");
    return;
  }
  try {
    const result = await fetchIngestionJobs({
      walletId,
      appId,
      dataWalletId,
      sessionId,
      privateDbId,
      status,
      limit: 50,
      offset: 0,
    });
    jobCache = result.items || [];
    renderJobs();
    setHint(jobsHint, jobCache.length ? "" : "当前没有作业。");
  } catch (err) {
    setHint(jobsHint, `加载失败：${err.message}`, "error");
  }
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
  await loadAppsAndKbs();
  await loadJobs();
}

jobForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  setHint(jobHint, "");
  try {
    const appId = (jobAppSelect.value || "").trim();
    const kbKey = (jobKbSelect.value || "").trim();
    if (!appId) throw new Error("请选择应用");
    if (!kbKey) throw new Error("请选择 KB");

    const sourceUrl = (jobSourceUrl.value || "").trim();
    const content = (jobContent.value || "").trim();
    if (!sourceUrl && !content) {
      throw new Error("请提供 MinIO URL 或内联内容");
    }

    const metadata = normalizeJson(jobMetadata.value, {});
    const options = normalizeJson(jobOptions.value, {});
    const runNow = jobRunNow.value === "yes";
    const dataWalletId = (jobDataWallet?.value || "").trim();
    const sessionId = (jobSessionId?.value || "").trim();
    const privateDbId = (jobPrivateDbId?.value || "").trim();
    const payload = {
      wallet_id: state.walletId,
      data_wallet_id: dataWalletId || undefined,
      session_id: sessionId || undefined,
      private_db_id: privateDbId || undefined,
      app_id: appId,
      kb_key: kbKey,
      source_url: sourceUrl || undefined,
      content: content || undefined,
      filename: (jobFilename.value || "").trim() || undefined,
      file_type: (jobFileType.value || "").trim() || undefined,
      metadata,
      options,
    };

    const created = await createIngestionJob(payload, runNow, state.walletId);
    setHint(jobHint, `作业 #${created.id} 已创建${runNow ? "并执行" : ""}。`);
    await loadJobs();
    await showJobDetail(created.id);
  } catch (err) {
    setHint(jobHint, `创建失败：${err.message}`, "error");
  }
});

jobReset?.addEventListener("click", () => {
  jobSourceUrl.value = "";
  jobContent.value = "";
  jobFilename.value = "";
  jobFileType.value = "";
  if (jobDataWallet) {
    jobDataWallet.value = "";
  }
  if (jobSessionId) {
    jobSessionId.value = "";
  }
  if (jobPrivateDbId) {
    jobPrivateDbId.value = "";
  }
  jobMetadata.value = "";
  jobOptions.value = "";
  jobRunNow.value = "yes";
  setHint(jobHint, "");
  loadPresets();
});

jobAppSelect?.addEventListener("change", () => {
  fillKbOptions(jobAppSelect.value);
  updateDataWalletField();
  loadPresets();
});

jobKbSelect?.addEventListener("change", () => {
  updateDataWalletField();
  loadPresets();
});

jobDataWallet?.addEventListener("change", () => {
  loadPresets();
});

jobPrefixRefresh?.addEventListener("click", () => {
  loadPresets();
});

jobsRefresh?.addEventListener("click", loadJobs);
jobsAppSelect?.addEventListener("change", loadJobs);
jobsDataWallet?.addEventListener("change", loadJobs);
jobsStatusSelect?.addEventListener("change", loadJobs);
jobsSessionId?.addEventListener("change", loadJobs);
jobsPrivateDbId?.addEventListener("change", loadJobs);
jobRefresh?.addEventListener("click", loadJobs);

jobClear?.addEventListener("click", () => {
  renderJobOutput(null);
});

jobOutputClear?.addEventListener("click", () => {
  renderJobOutput(null);
});

jobOutputCopy?.addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(jobOutput.textContent || "");
    setHint(jobOutputHint, "已复制到剪贴板。");
  } catch (err) {
    setHint(jobOutputHint, "复制失败。", "error");
  }
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

apiBaseInput.value = loadApiBase();
state.walletId = loadWalletId();
const loggedIn = ensureLoggedIn();
if (loggedIn) {
  refreshAll();
}

loginBtn?.addEventListener("click", () => {
  const next = encodeURIComponent(window.location.pathname + window.location.search);
  window.location.href = `./login.html?next=${next}`;
});

backBtn?.addEventListener("click", () => {
  window.location.href = "./index.html";
});
