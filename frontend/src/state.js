export const state = {
  apiBase: "",
  walletId: "",
  isSuperAdmin: false,
  apps: [],
  knowledgeBases: [],
  documents: [],
  docColumns: [],
  docTotal: 0,
  docPageSize: 20,
  docPageOffset: 0,
  docVisibleColumns: [],
  docSort: null,
  selectedDocIds: new Set(),
  stores: [],
  ingestion: [],
  ingestionRaw: [],
  vectors: 0,
  selectedKb: null,
  selectedDocId: null,
  selectedAppId: null,
  memorySessions: [],
  memorySessionTotal: 0,
  memoryContexts: [],
  memoryContextTotal: 0,
  selectedMemoryKey: null,
  selectedMemoryContextId: null,
  memoryContextSnapshot: null,
  privateDbs: [],
  privateDbSessions: [],
  selectedPrivateDbId: null,
  pluginFiles: [],
  selectedPluginPath: null,
  pluginFileMeta: null,
  pluginContentSnapshot: "",
  auditLogs: [],
  selectedAuditId: null,
  kbFilters: {
    owners: [],
    types: [],
    access: [],
  },
};

const AUTH_TOKEN_KEY = "rag_auth_token";
const SUPER_ADMIN_FLAG_KEY = "rag_is_super_admin";

export function loadApiBase() {
  const stored = localStorage.getItem("rag_api_base") || "";
  state.apiBase = stored;
  return stored;
}

export function setApiBase(value) {
  state.apiBase = value;
  localStorage.setItem("rag_api_base", value);
}

export function loadWalletId() {
  const token = localStorage.getItem(AUTH_TOKEN_KEY) || "";
  const addr = token ? decodeJwtAddress(token) : "";
  const stored = localStorage.getItem("rag_wallet_id") || "";
  const isSuperAdmin = localStorage.getItem(SUPER_ADMIN_FLAG_KEY);
  state.isSuperAdmin = isSuperAdmin === "1";
  state.walletId = addr || stored || "";
  return state.walletId;
}

export function setWalletId(value) {
  const next = value || "";
  state.walletId = next;
  if (next) {
    localStorage.setItem("rag_wallet_id", next);
  } else {
    localStorage.removeItem("rag_wallet_id");
  }
}

export function setIsSuperAdmin(value) {
  const flag = Boolean(value);
  state.isSuperAdmin = flag;
  localStorage.setItem(SUPER_ADMIN_FLAG_KEY, flag ? "1" : "0");
}

export function getAuthToken() {
  return localStorage.getItem(AUTH_TOKEN_KEY) || "";
}

export function isLoggedIn() {
  return Boolean(getAuthToken());
}

function decodeJwtAddress(token) {
  try {
    const parts = (token || "").split(".");
    if (parts.length !== 3) return "";
    const payloadB64 = parts[1].replace(/-/g, "+").replace(/_/g, "/");
    const padded = payloadB64 + "=".repeat((4 - (payloadB64.length % 4)) % 4);
    const json = atob(padded);
    const payload = JSON.parse(json);
    const address = (payload?.address || "").toLowerCase();
    return address;
  } catch {
    return "";
  }
}

export function isSuperAdmin() {
  return Boolean(state.isSuperAdmin);
}

export function roleLabel() {
  if (!state.walletId) return "未登录";
  return isSuperAdmin() ? "知识库管理员" : "租户用户";
}

export function ensureLoggedIn(nextPath = "") {
  if (isLoggedIn()) return true;
  if (typeof window === "undefined") return false;
  const target = nextPath || `${window.location.pathname}${window.location.search}`;
  const next = encodeURIComponent(target);
  window.location.href = `./login.html?next=${next}`;
  return false;
}
