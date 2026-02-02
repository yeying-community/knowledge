import { state, setWalletId, setIsSuperAdmin } from "./state.js";
import { authFetch } from "../assets/vendor/web3-bs.esm.js";

const AUTH_TOKEN_KEY = "rag_auth_token";

function normalizeBaseUrl(value) {
  return (value || "").replace(/\/+$/, "");
}

function resolveAuthBaseUrl() {
  const base = normalizeBaseUrl(state.apiBase);
  return base ? `${base}/api/v1/public/auth` : "/api/v1/public/auth";
}

async function request(path, options = {}) {
  const url = state.apiBase ? `${state.apiBase}${path}` : path;
  const res = await authFetch(
    url,
    {
      headers: { "Content-Type": "application/json" },
      ...options,
    },
    {
      baseUrl: resolveAuthBaseUrl(),
      tokenStorageKey: AUTH_TOKEN_KEY,
      storeToken: true,
    }
  );
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`Request failed (${res.status}): ${detail}`);
  }
  return res.json();
}

function requireWalletId(walletId) {
  const id = (walletId || state.walletId || "").trim();
  if (!id) {
    throw new Error("wallet_id missing");
  }
  return id;
}

export function ping() {
  return request("/health");
}

export async function fetchProfile() {
  const res = await request("/api/v1/public/profile");
  const address = (res?.data?.address || "").toLowerCase();
  if (address) {
    setWalletId(address);
  }
  setIsSuperAdmin(Boolean(res?.data?.is_super_admin));
  return res;
}

export function fetchApps(walletId) {
  const id = requireWalletId(walletId);
  return request(`/app/list?wallet_id=${encodeURIComponent(id)}`);
}

export function fetchAppStatus(appId, walletId) {
  const id = requireWalletId(walletId);
  return request(`/app/${appId}/status?wallet_id=${encodeURIComponent(id)}`);
}

export function fetchAppIntents(appId, walletId) {
  const id = requireWalletId(walletId);
  return request(`/app/${appId}/intents?wallet_id=${encodeURIComponent(id)}`);
}

export function fetchAppIntentDetails(appId, walletId) {
  const id = requireWalletId(walletId);
  return request(`/app/${appId}/intents/detail?wallet_id=${encodeURIComponent(id)}`);
}

export function updateAppIntents(appId, payload, walletId) {
  const id = requireWalletId(walletId);
  return request(`/app/${appId}/intents?wallet_id=${encodeURIComponent(id)}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function fetchAppWorkflows(appId, walletId) {
  const id = requireWalletId(walletId);
  return request(`/app/${appId}/workflows?wallet_id=${encodeURIComponent(id)}`);
}

export function updateAppWorkflows(appId, payload, walletId) {
  const id = requireWalletId(walletId);
  return request(`/app/${appId}/workflows?wallet_id=${encodeURIComponent(id)}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function fetchPluginFiles(appId, walletId) {
  const id = requireWalletId(walletId);
  return request(`/app/${appId}/plugin/files?wallet_id=${encodeURIComponent(id)}`);
}

export function fetchPluginFile(appId, path, walletId) {
  const id = requireWalletId(walletId);
  const params = new URLSearchParams({ wallet_id: id, path: path || "" });
  return request(`/app/${appId}/plugin/file?${params.toString()}`);
}

export function updatePluginFile(appId, payload, walletId) {
  const id = requireWalletId(walletId);
  return request(`/app/${appId}/plugin/file?wallet_id=${encodeURIComponent(id)}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function registerApp(appId, walletId) {
  const id = requireWalletId(walletId);
  return request("/app/register", {
    method: "POST",
    body: JSON.stringify({ app_id: appId, wallet_id: id }),
  });
}

export function fetchKBList(walletId) {
  const id = requireWalletId(walletId);
  return request(`/kb/list?wallet_id=${encodeURIComponent(id)}`);
}

export function fetchKBStats(appId, kbKey, walletId, options = {}) {
  const id = requireWalletId(walletId);
  const params = new URLSearchParams({ wallet_id: id });
  if (options.dataWalletId) params.set("data_wallet_id", options.dataWalletId);
  if (options.privateDbId) params.set("private_db_id", options.privateDbId);
  if (options.sessionId) params.set("session_id", options.sessionId);
  return request(`/kb/${appId}/${kbKey}/stats?${params.toString()}`);
}

export function fetchKBDocuments(appId, kbKey, limit = 20, offset = 0, walletId, options = {}) {
  const id = requireWalletId(walletId);
  const params = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
    wallet_id: id,
  });
  if (options.dataWalletId) params.set("data_wallet_id", options.dataWalletId);
  if (options.privateDbId) params.set("private_db_id", options.privateDbId);
  if (options.sessionId) params.set("session_id", options.sessionId);
  return request(`/kb/${appId}/${kbKey}/documents?${params.toString()}`);
}

export function fetchStoresHealth() {
  return request("/stores/health");
}

export function fetchIngestionLogs(options = {}) {
  const {
    limit = 20,
    offset = 0,
    walletId,
    appId,
    kbKey,
    status,
  } = options;
  const id = requireWalletId(walletId);
  if (!appId) {
    throw new Error("app_id missing");
  }
  const params = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
    wallet_id: id,
    app_id: appId,
  });
  if (kbKey) params.set("kb_key", kbKey);
  if (status) params.set("status", status);
  return request(`/ingestion/logs?${params.toString()}`);
}

export function fetchAuditLogs(options = {}) {
  const {
    limit = 50,
    offset = 0,
    walletId,
    appId,
    entityType,
    entityId,
    action,
    operatorWalletId,
  } = options;
  const id = requireWalletId(walletId);
  const params = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
    wallet_id: id,
  });
  if (appId) params.set("app_id", appId);
  if (entityType) params.set("entity_type", entityType);
  if (entityId) params.set("entity_id", entityId);
  if (action) params.set("action", action);
  if (operatorWalletId) params.set("operator_wallet_id", operatorWalletId);
  return request(`/audit/logs?${params.toString()}`);
}

export function createIngestionJob(payload, runNow = false, walletId) {
  const id = requireWalletId(walletId || payload?.wallet_id);
  const params = runNow ? "?run=true" : "";
  const body = { ...payload, wallet_id: id };
  return request(`/ingestion/jobs${params}`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function fetchIngestionJobs(options = {}) {
  const {
    limit = 20,
    offset = 0,
    walletId,
    appId,
    status,
    dataWalletId,
    privateDbId,
    sessionId,
  } = options;
  const id = requireWalletId(walletId);
  const params = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
    wallet_id: id,
  });
  if (appId) params.set("app_id", appId);
  if (dataWalletId) params.set("data_wallet_id", dataWalletId);
  if (privateDbId) params.set("private_db_id", privateDbId);
  if (sessionId) params.set("session_id", sessionId);
  if (status) params.set("status", status);
  return request(`/ingestion/jobs?${params.toString()}`);
}

export function fetchIngestionJob(jobId, walletId) {
  const id = requireWalletId(walletId);
  return request(`/ingestion/jobs/${jobId}?wallet_id=${encodeURIComponent(id)}`);
}

export function runIngestionJob(jobId, walletId) {
  const id = requireWalletId(walletId);
  return request(`/ingestion/jobs/${jobId}/run?wallet_id=${encodeURIComponent(id)}`, {
    method: "POST",
  });
}

export function fetchIngestionJobRuns(jobId, walletId, limit = 50, offset = 0) {
  const id = requireWalletId(walletId);
  const params = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
    wallet_id: id,
  });
  return request(`/ingestion/jobs/${jobId}/runs?${params.toString()}`);
}

export function fetchIngestionJobPresets(
  appId,
  kbKey,
  walletId,
  limit = 20,
  dataWalletId = ""
) {
  const id = requireWalletId(walletId);
  const params = new URLSearchParams({
    wallet_id: id,
    app_id: appId,
    kb_key: kbKey,
    limit: String(limit),
  });
  if (dataWalletId) {
    params.set("data_wallet_id", dataWalletId);
  }
  return request(`/ingestion/jobs/presets?${params.toString()}`);
}

export function fetchPrivateDBs(options = {}) {
  const { walletId, appId, ownerWalletId, sessionId, limit = 50, offset = 0 } = options;
  const id = requireWalletId(walletId);
  const params = new URLSearchParams({
    wallet_id: id,
    limit: String(limit),
    offset: String(offset),
  });
  if (appId) params.set("app_id", appId);
  if (ownerWalletId) params.set("owner_wallet_id", ownerWalletId);
  if (sessionId) params.set("session_id", sessionId);
  return request(`/private_dbs?${params.toString()}`);
}

export function fetchPrivateDBSessions(privateDbId, appId, walletId) {
  const id = requireWalletId(walletId);
  const params = new URLSearchParams({ wallet_id: id, app_id: appId });
  return request(`/private_dbs/${privateDbId}/sessions?${params.toString()}`);
}

export function createPrivateDB(payload, walletId) {
  const id = requireWalletId(walletId || payload?.wallet_id);
  const body = { ...payload, wallet_id: id };
  return request("/private_dbs", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function bindPrivateDBSessions(privateDbId, payload, walletId) {
  const id = requireWalletId(walletId || payload?.wallet_id);
  const body = { ...payload, wallet_id: id };
  return request(`/private_dbs/${privateDbId}/bind`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function unbindPrivateDBSession(privateDbId, sessionId, appId, walletId) {
  const id = requireWalletId(walletId);
  const params = new URLSearchParams({ wallet_id: id, app_id: appId });
  return request(`/private_dbs/${privateDbId}/sessions/${sessionId}?${params.toString()}`, {
    method: "DELETE",
  });
}

export function createKBDocument(appId, kbKey, payload, walletId) {
  const id = requireWalletId(walletId);
  return request(`/kb/${appId}/${kbKey}/documents?wallet_id=${encodeURIComponent(id)}`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function replaceKBDocument(appId, kbKey, docId, payload, walletId) {
  const id = requireWalletId(walletId);
  return request(`/kb/${appId}/${kbKey}/documents/${docId}?wallet_id=${encodeURIComponent(id)}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function updateKBDocument(appId, kbKey, docId, payload, walletId) {
  const id = requireWalletId(walletId);
  return request(`/kb/${appId}/${kbKey}/documents/${docId}?wallet_id=${encodeURIComponent(id)}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function deleteKBDocument(appId, kbKey, docId, walletId) {
  const id = requireWalletId(walletId);
  return request(`/kb/${appId}/${kbKey}/documents/${docId}?wallet_id=${encodeURIComponent(id)}`, {
    method: "DELETE",
  });
}

export function createKBConfig(appId, payload, walletId) {
  const id = requireWalletId(walletId);
  return request(`/kb/${appId}/configs?wallet_id=${encodeURIComponent(id)}`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateKBConfig(appId, kbKey, payload, walletId) {
  const id = requireWalletId(walletId);
  return request(`/kb/${appId}/${kbKey}/config?wallet_id=${encodeURIComponent(id)}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function deleteKBConfig(appId, kbKey, walletId) {
  const id = requireWalletId(walletId);
  return request(`/kb/${appId}/${kbKey}/config?wallet_id=${encodeURIComponent(id)}`, {
    method: "DELETE",
  });
}

export function pushMemory(payload) {
  return request("/memory/push", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function fetchMemorySessions(options = {}) {
  const { limit = 20, offset = 0, appId, walletId, dataWalletId, sessionId } = options;
  const id = requireWalletId(walletId);
  const params = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
    wallet_id: id,
  });
  if (appId) params.set("app_id", appId);
  if (dataWalletId) params.set("data_wallet_id", dataWalletId);
  if (sessionId) params.set("session_id", sessionId);
  return request(`/memory/sessions?${params.toString()}`);
}

export function fetchMemoryContexts(memoryKey, options = {}) {
  const { limit = 20, offset = 0, includeContent = false, walletId, dataWalletId } = options;
  const id = requireWalletId(walletId);
  const params = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
    wallet_id: id,
  });
  if (dataWalletId) params.set("data_wallet_id", dataWalletId);
  if (includeContent) params.set("include_content", "1");
  return request(`/memory/${memoryKey}/contexts?${params.toString()}`);
}

export function updateMemoryContext(uid, payload, walletId, dataWalletId) {
  const id = requireWalletId(walletId);
  const params = new URLSearchParams({ wallet_id: id });
  if (dataWalletId) params.set("data_wallet_id", dataWalletId);
  return request(`/memory/contexts/${uid}?${params.toString()}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}
