import { state } from "./state.js";

async function request(path, options = {}) {
  const url = state.apiBase ? `${state.apiBase}${path}` : path;
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
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
