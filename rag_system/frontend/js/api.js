/**
 * Centralized API Client for RAG System
 */

const API_BASE = "https://scalable-document-qa-rag-backend.onrender.com/api/v1";

class ApiClient {
  constructor() {
    this.tokenKey = "rag_access_token";
    this.userKey = "rag_user_data";
  }

  getToken() {
    return localStorage.getItem(this.tokenKey);
  }

  setSession(token, user) {
    localStorage.setItem(this.tokenKey, token);
    localStorage.setItem(this.userKey, JSON.stringify(user));
  }

  clearSession() {
    localStorage.removeItem(this.tokenKey);
    localStorage.removeItem(this.userKey);
  }

  getUser() {
    const data = localStorage.getItem(this.userKey);
    return data ? JSON.parse(data) : null;
  }

  isAuthenticated() {
    return !!this.getToken();
  }

  async request(endpoint, options = {}) {
    const url = `${API_BASE}${endpoint}`;
    const headers = options.headers || {};

    const token = this.getToken();
    if (token && !headers["Authorization"]) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    if (!(options.body instanceof FormData) && !headers["Content-Type"]) {
      headers["Content-Type"] = "application/json";
    }

    try {
      const response = await fetch(url, {
        ...options,
        headers,
      });

      if (response.status === 401 && !endpoint.includes("/auth/login") && !endpoint.includes("/auth/register")) {
        this.clearSession();
        window.location.href = "/login.html";
        return null;
      }

      let json;
      const text = await response.text();
      try {
        json = JSON.parse(text);
      } catch (err) {
        throw new Error(text.slice(0, 200) || `Server error (${response.status})`);
      }

      if (!response.ok) {
        const errorMsg = json && json.error ? json.error.message : (json && json.message ? json.message : `Request failed with status ${response.status}`);
        throw new Error(errorMsg);
      }
      return json;
    } catch (err) {
      throw err;
    }
  }

  // Auth Endpoints
  async register(email, password, full_name) {
    const res = await this.request("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password, full_name }),
    });
    if (res && res.data) {
      this.setSession(res.data.access_token, res.data.user);
    }
    return res;
  }

  async login(email, password) {
    const res = await this.request("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    if (res && res.data) {
      this.setSession(res.data.access_token, res.data.user);
    }
    return res;
  }

  async logout() {
    try {
      await this.request("/auth/logout", { method: "POST" });
    } finally {
      this.clearSession();
      window.location.href = "/login.html";
    }
  }

  async getMe() {
    return this.request("/auth/me");
  }

  // Documents Endpoints
  async getDocuments(collectionId = null, page = 1) {
    let q = `?page=${page}`;
    if (collectionId) q += `&collection_id=${collectionId}`;
    return this.request(`/documents${q}`);
  }

  async uploadDocument(file, collectionId = null) {
    const formData = new FormData();
    formData.append("file", file);
    if (collectionId) formData.append("collection_id", collectionId);

    return this.request("/documents", {
      method: "POST",
      body: formData,
    });
  }

  async deleteDocument(documentId) {
    return this.request(`/documents/${documentId}`, {
      method: "DELETE",
    });
  }

  async reprocessDocument(documentId) {
    return this.request(`/documents/${documentId}/reprocess`, {
      method: "POST",
    });
  }

  // Collections Endpoints
  async getCollections() {
    return this.request("/collections");
  }

  async createCollection(name, description = "") {
    return this.request("/collections", {
      method: "POST",
      body: JSON.stringify({ name, description }),
    });
  }

  async deleteCollection(collectionId) {
    return this.request(`/collections/${collectionId}`, {
      method: "DELETE",
    });
  }

  // Conversations & RAG Chat Endpoints
  async getConversations() {
    return this.request("/conversations");
  }

  async createConversation(title = "New Conversation") {
    return this.request("/conversations", {
      method: "POST",
      body: JSON.stringify({ title }),
    });
  }

  async getConversation(id) {
    return this.request(`/conversations/${id}`);
  }

  async deleteConversation(id) {
    return this.request(`/conversations/${id}`, {
      method: "DELETE",
    });
  }

  async sendMessage(conversationId, message, collectionId = null, documentIds = null, topK = null) {
    return this.request(`/conversations/${conversationId}/messages`, {
      method: "POST",
      body: JSON.stringify({
        message,
        collection_id: collectionId,
        document_ids: documentIds,
        top_k: topK ? parseInt(topK, 10) : null,
      }),
    });
  }
}

window.api = new ApiClient();
