import type {
  ChatResponse,
  MessageResponse,
  SessionSummary,
  TokenResponse,
  User,
} from "./types";

const API_BASE_URL =
  import.meta.env.VITE_API_URL || "/api/v1";

/* -------------------------------- */
/* Generic Request Helper           */
/* -------------------------------- */

async function request<T>(
  path: string,
  init: RequestInit = {}
): Promise<T> {
  try {
    const headers = new Headers(init.headers);

    if (!headers.has("Content-Type")) {
      headers.set("Content-Type", "application/json");
    }

    console.log("=================================");
    console.log("API URL:", `${API_BASE_URL}${path}`);
    console.log("METHOD:", init.method);
    console.log("HEADERS:", Object.fromEntries(headers.entries()));
    console.log("BODY:", init.body);
    console.log("=================================");

    const response = await fetch(
      `${API_BASE_URL}${path}`,
      {
        ...init,
        headers,
      }
    );

    if (!response.ok) {
      let errorMessage = `Request failed (${response.status})`;

      try {
        const errorData = await response.json();

        if (Array.isArray(errorData.detail)) {
          errorMessage = JSON.stringify(
            errorData.detail,
            null,
            2
          );
        } else {
          errorMessage =
            errorData.detail ||
            errorData.message ||
            errorMessage;
        }
      } catch {
        try {
          errorMessage = await response.text();
        } catch {
          //
        }
      }

      throw new Error(errorMessage);
    }

    const contentType =
      response.headers.get("content-type");

    if (
      contentType &&
      contentType.includes("application/json")
    ) {
      return response.json();
    }

    return {} as T;
  } catch (error) {
    if (error instanceof TypeError) {
      throw new Error(
        "Cannot connect to backend server."
      );
    }

    throw error;
  }
}

/* -------------------------------- */
/* Auth Helpers                     */
/* -------------------------------- */

const authHeaders = (
  token: string
): HeadersInit => ({
  Authorization: `Bearer ${token}`,
});

/* -------------------------------- */
/* Authentication APIs              */
/* -------------------------------- */

export const apiLogin = (
  email: string,
  password: string
) =>
  request<TokenResponse>(
    "/auth/login",
    {
      method: "POST",
      body: JSON.stringify({
        email,
        password,
      }),
    }
  );

export const apiRegister = (
  email: string,
  password: string,
  full_name: string
) =>
  request<User>(
    "/auth/register",
    {
      method: "POST",
      body: JSON.stringify({
        email,
        password,
        full_name,
      }),
    }
  );

export const apiGetMe = (
  token: string
) =>
  request<User>(
    "/auth/me",
    {
      method: "GET",
      headers: authHeaders(
        token
      ),
    }
  );

/* -------------------------------- */
/* Sessions APIs                    */
/* -------------------------------- */

export const apiFetchSessions = (
  token: string
) =>
  request<SessionSummary[]>(
    "/chat/sessions",
    {
      method: "GET",
      headers: authHeaders(
        token
      ),
    }
  );

export const apiFetchSessionMessages =
  (
    token: string,
    sessionId: number
  ) =>
    request<MessageResponse[]>(
      `/chat/sessions/${sessionId}/messages`,
      {
        method: "GET",
        headers: authHeaders(
          token
        ),
      }
    );

/* -------------------------------- */
/* Chat API                         */
/* -------------------------------- */

export async function apiSendMessage(
  token: string,
  query: string,
  sessionId?: number,
  top_k = 10,
  final_top_k = 3
): Promise<ChatResponse> {
  const cleanedQuery = query.trim();

  if (!cleanedQuery) {
    throw new Error("Message cannot be empty.");
  }

  if (top_k < 1 || top_k > 50) {
    throw new Error("top_k must be between 1 and 50");
  }

  if (final_top_k < 1 || final_top_k > 20) {
    throw new Error("final_top_k must be between 1 and 20");
  }

  const payload: Record<string, unknown> = {
    query: cleanedQuery,
    top_k,
    final_top_k,
    filters: null,
  };

  if (sessionId !== undefined && sessionId !== null) {
    payload.session_id = sessionId;
  }

  return request<ChatResponse>("/chat/message", {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify(payload),
  });
}