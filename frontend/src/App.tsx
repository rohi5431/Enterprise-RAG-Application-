import { useEffect, useState } from "react";
import { AuthPanel } from "./components/AuthPanel";
import { ChatPanel } from "./components/ChatPanel";
import { SessionSidebar } from "./components/SessionSidebar";
// import { UploadPanel } from "./components/UploadPanel";
import {
  apiFetchSessionMessages,
  apiFetchSessions,
  apiGetMe,
  apiLogin,
  apiRegister,
  apiSendMessage,
} from "./api";
import type {
  ChatMessage,
  SessionSummary,
  TokenResponse,
  User,
} from "./types";

function App() {
  const [token, setToken] = useState<string | null>(() =>
    localStorage.getItem("rag_access_token")
  );
  const [user, setUser] = useState<User | null>(null);
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [activeSession, setActiveSession] =
    useState<SessionSummary | null>(null);
  const [messages, setMessages] = useState<
    ChatMessage[]
  >([]);
  const [error, setError] = useState<string | null>(
    null
  );
  const [loading, setLoading] = useState(false);
  const [metadata, setMetadata] = useState<{
    confidence?: number;
    total?: number;
    llm?: number;
    retrieval?: number;
  } | null>(null);

  const isAuthenticated = Boolean(token);

  useEffect(() => {
    if (!token) {
      setUser(null);
      return;
    }

    apiGetMe(token)
      .then((profile) => {
        setUser(profile);
        setError(null);
      })
      .catch(() => {
        setError(
          "Authentication expired, please log in again."
        );
        handleSignOut();
      });
  }, [token]);

  useEffect(() => {
    if (!token || !user) return;
    void refreshSessionList();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, user]);

  const handleSignOut = () => {
    localStorage.removeItem("rag_access_token");
    localStorage.removeItem("rag_refresh_token");
    setToken(null);
    setUser(null);
    setSessions([]);
    setActiveSession(null);
    setMessages([]);
    setMetadata(null);
    setError(null);
  };

  const parseApiError = (
    err: unknown,
    fallback: string
  ) => {
    const message =
      err instanceof Error ? err.message : "";
    if (message.includes("Failed to fetch")) {
      return "Unable to connect to the backend. Make sure the API server is running and reachable.";
    }
    return message || fallback;
  };

  const scheduleToken = (
    response: TokenResponse
  ) => {
    localStorage.setItem(
      "rag_access_token",
      response.access_token
    );
    localStorage.setItem(
      "rag_refresh_token",
      response.refresh_token
    );
    setToken(response.access_token);
  };

  const refreshSessionList = async () => {
    if (!token) return;
    setLoading(true);
    setError(null);

    try {
        const sessionList = await apiFetchSessions(token);
      
        setSessions(sessionList);
      
        if (!activeSession && sessionList.length > 0) {
          await selectSession(sessionList[0]);
        }
      } catch (err) {
        console.error(err);
      
        if (err instanceof Error) {
          setError(err.message);
        } else {
          setError("Unknown error");
        }
      } finally {
        setLoading(false);
      }
    };

  const handleLogin = async (
    email: string,
    password: string
  ) => {
    setLoading(true);
    setError(null);

    try {
      const response = await apiLogin(
        email,
        password
      );
      scheduleToken(response);
      await refreshSessionList();
    } catch (err) {
      setError(
        parseApiError(
          err,
          "Login failed. Check your credentials and try again."
        )
      );
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (
    email: string,
    password: string,
    fullName: string
  ) => {
    setLoading(true);
    setError(null);

    try {
      await apiRegister(
        email,
        password,
        fullName
      );
      await handleLogin(email, password);
    } catch (err) {
      setError(
        parseApiError(
          err,
          "Registration failed. Please use a valid email and strong password."
        )
      );
    } finally {
      setLoading(false);
    }
  };

  const selectSession = async (
    session: SessionSummary
  ) => {
    if (!token) return;

    setActiveSession(session);
    setMessages([]);
    setMetadata(null);
    setLoading(true);
    setError(null);

    try {
      const sessionMessages =
        await apiFetchSessionMessages(
          token,
          session.id
        );

      setMessages(
        sessionMessages.map((message) => ({
          id: message.id,
          role: message.role,
          content: message.content,
          created_at:
            message.created_at,
        }))
      );
    } catch {
      setError(
        "Could not load messages for this session."
      );
    } finally {
      setLoading(false);
    }
  };

  const handleNewChat = async () => {
    setActiveSession(null);
    setMessages([]);
    setMetadata(null);
  };

  const handleSendMessage = async (
    text: string
  ) => {
    if (!token) {
      setError(
        "Please sign in before sending a message."
      );
      return;
    }

    setMessages((current) => [
      ...current,
      { role: "user", content: text },
    ]);
    setError(null);
    setLoading(true);

    try {
      const result = await apiSendMessage(
        token,
        text,
        activeSession?.id
      );

      setMetadata({
        confidence: result.confidence,
        total: result.total_latency_ms,
        llm: result.llm_latency_ms,
        retrieval:
          result.retrieval_latency_ms,
      });

      setActiveSession((prev) =>
        ({
          ...prev,
          id: result.session_id,
          title:
            prev?.title ||
            `Chat ${new Date().toLocaleDateString(
              undefined,
              {
                month: "short",
                day: "numeric",
              }
            )}`,
        } as SessionSummary)
      );

      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          content: result.answer,
        },
      ]);

      await refreshSessionList();
    } catch {
      setError(
        "Unable to send message. The API may be unreachable."
      );
    } finally {
      setLoading(false);
    }
  };

  if (!isAuthenticated) {
    return (
      <div className="auth-shell">
        <div className="screen-center">
          <AuthPanel
            onLogin={handleLogin}
            onRegister={handleRegister}
            loading={loading}
            error={error}
          />
        </div>
      </div>
    );
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-card">
          <div className="brand-symbol">R</div>
          <div>
            <p className="brand-title">
              RAG Studio
            </p>
            <p className="brand-subtitle">
              AI chat with document recall
            </p>
          </div>
        </div>

        <div className="sidebar-actions">
          <button
            className="primary-button"
            onClick={handleNewChat}
            disabled={loading}
            type="button"
          >
            + Start a new chat
          </button>
        </div>

        <SessionSidebar
          sessions={sessions}
          activeSessionId={activeSession?.id}
          onSelect={selectSession}
        />

        <button
          className="ghost-button signout-button"
          onClick={handleSignOut}
          type="button"
        >
          Sign out
        </button>
      </aside>

      <main className="content-panel">
        <header className="page-header">
          <div>
            <h1>
              {activeSession?.title ||
                "Ask anything"}
            </h1>
            <p className="muted-text">
              {user?.full_name || user?.email}
            </p>
          </div>

          <div className="summary-pill">
            {sessions.length} sessions •{" "}
            {messages.length} messages
          </div>
        </header>

        {/* <UploadPanel token={token} /> */}

        <ChatPanel
          messages={messages}
          onSend={handleSendMessage}
          loading={loading}
          error={error}
          metadata={metadata}
        />

        {/* <footer className="metadata-bar">
          <div className="metadata-item">
            <span className="metadata-label">
              Latency
            </span>
            <strong>
              {metadata?.total
                ? `${metadata.total} ms`
                : "—"}
            </strong>
          </div>

          <div className="metadata-item">
            <span className="metadata-label">
              Retrieval
            </span>
            <strong>
              {metadata?.retrieval
                ? `${metadata.retrieval} ms`
                : "—"}
            </strong>
          </div>

          <div className="metadata-item">
            <span className="metadata-label">
              Confidence
            </span>
            <strong>
              {metadata?.confidence
                ? `${(
                    metadata.confidence * 100
                  ).toFixed(1)}%`
                : "—"}
            </strong>
          </div>
        </footer> */}
      </main>
    </div>
  );
}

export default App;