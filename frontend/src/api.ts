import type { ChatResponse, MessageResponse, SessionSummary, TokenResponse, User } from "./types";

const baseUrl = import.meta.env.VITE_API_URL || "/api/v1";

const request = async <T>(path: string, init: RequestInit = {}) => {
  const response = await fetch(`${baseUrl}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...init.headers,
    },
    ...init,
  });

  if (!response.ok) {
    const errorBody = await response.text();
    if (errorBody) {
      try {
        const json = JSON.parse(errorBody) as {
          detail?: unknown;
          message?: string;
        };
        let detail: string | undefined;

        if (Array.isArray(json.detail)) {
          detail = json.detail
            .map((item) => {
              const parsed = item as { msg?: string };
              return parsed.msg ?? JSON.stringify(item);
            })
            .join("; ");
        } else if (typeof json.detail === "string") {
          detail = json.detail;
        } else if (typeof json.message === "string") {
          detail = json.message;
        }

        throw new Error(detail || JSON.stringify(json));
      } catch {
        throw new Error(errorBody);
      }
    }
    throw new Error(response.statusText);
  }

  return response.json() as Promise<T>;
};

export const apiLogin = (email: string, password: string) =>
  request<TokenResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });

export const apiRegister = (email: string, password: string, full_name: string) =>
  request<User>("/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, password, full_name }),
  });

export const apiGetMe = (token: string) =>
  request<User>("/auth/me", {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

export const apiFetchSessions = (token: string) =>
  request<SessionSummary[]>("/chat/sessions", {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

export const apiFetchSessionMessages = (token: string, sessionId: number) =>
  request<MessageResponse[]>(`/chat/sessions/${sessionId}/messages`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

export const apiSendMessage = async (
  token: string,
  query: string,
  sessionId?: number,
  top_k = 20,
  final_top_k = 5
) => {
  // ✅ Validate query before sending
  if (!query || query.trim().length === 0) {
    throw new Error("Query cannot be empty");
  }

  // ✅ Validate ranges for top_k and final_top_k
  if (top_k < 1 || top_k > 50) {
    throw new Error("top_k must be between 1 and 50");
  }
  if (final_top_k < 1 || final_top_k > 20) {
    throw new Error("final_top_k must be between 1 and 20");
  }

  try {
    return await request<ChatResponse>("/chat/message", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        query: query.trim(),          // ✅ required field
        session_id: sessionId ?? null,
        top_k,
        final_top_k,
        filters: null,                // optional, can be extended later
      }),
    });
  } catch (err: unknown) {
    // ✅ More descriptive error handling
    if (err instanceof Error) {
      throw new Error(`Failed to send message: ${err.message}`);
    }
    throw new Error("Failed to send message due to unknown error");
  }
};

