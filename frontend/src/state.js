export const state = {
  apiBase: "",
  walletId: "",
  superAdminId: "super_admin",
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
  kbFilters: {
    owners: [],
    types: [],
    access: [],
  },
};

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
  const stored = localStorage.getItem("rag_wallet_id");
  state.walletId = stored || "";
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

export function isSuperAdmin() {
  return state.walletId && state.walletId === state.superAdminId;
}

export function roleLabel() {
  if (!state.walletId) return "未登录";
  return isSuperAdmin() ? "超级管理员" : "开发者";
}

export function ensureLoggedIn(nextPath = "") {
  if (state.walletId) return true;
  if (typeof window === "undefined") return false;
  const target = nextPath || `${window.location.pathname}${window.location.search}`;
  const next = encodeURIComponent(target);
  window.location.href = `./login.html?next=${next}`;
  return false;
}
