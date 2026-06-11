import type { SessionSummary } from "../types";

type SessionSidebarProps = {
  sessions: SessionSummary[];
  activeSessionId?: number;
  onSelect: (session: SessionSummary) => Promise<void>;
};

export function SessionSidebar({ sessions, activeSessionId, onSelect }: SessionSidebarProps) {
  return (
    <div className="session-list">
      <div className="session-list-heading">Chat history</div>
      {sessions.length === 0 ? (
        <div className="session-empty">No sessions yet — ask a question to start one.</div>
      ) : (
        sessions.map((session) => (
          <button
            key={session.id}
            className={`session-item ${session.id === activeSessionId ? "active" : ""}`}
            onClick={() => onSelect(session)}
            type="button"
          >
            <div className="session-name">{session.title || `Session ${session.id}`}</div>
            <div className="session-meta">{session.message_count} messages</div>
          </button>
        ))
      )}
    </div>
  );
}
