import { useState, type FormEvent } from "react";
import { MessageBubble } from "./MessageBubble";
import type { ChatMessage } from "../types";

type ChatPanelProps = {
  messages: ChatMessage[];
  onSend: (text: string) => Promise<void>;
  loading: boolean;
  error: string | null;
  metadata: { confidence?: number; total?: number; llm?: number; retrieval?: number } | null;
};

export function ChatPanel({ messages, onSend, loading, error, metadata }: ChatPanelProps) {
  const [draft, setDraft] = useState("");

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!draft.trim()) return;
    await onSend(draft.trim());
    setDraft("");
  };

  return (
    <section className="chat-panel">
      <div className="chat-window">
        {messages.length === 0 ? (
          <div className="empty-state">
            <h2>Begin your conversation</h2>
            <p>Ask a question about your documents, knowledge base, or internal policies.</p>
          </div>
        ) : (
          messages.map((message, index) => (
            <MessageBubble key={`${message.role}-${index}-${message.content.slice(0, 16)}`} role={message.role} content={message.content} />
          ))
        )}
      </div>

      <form className="composer" onSubmit={handleSubmit}>
        <textarea
          rows={2}
          placeholder="Type a question or request..."
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
        />
        <div className="composer-actions">
          <button className="secondary-button" type="submit" disabled={loading || !draft.trim()}>
            {loading ? "Sending…" : "Send"}
          </button>
        </div>
      </form>

      {error && <div className="chat-error">{error}</div>}
      {metadata && (
        <div className="chat-flair">
          <span>Confidence: {metadata.confidence ? `${metadata.confidence * 100}%` : "—"}</span>
          <span>LLM: {metadata.llm ? `${metadata.llm} ms` : "—"}</span>
          <span>Retrieval: {metadata.retrieval ? `${metadata.retrieval} ms` : "—"}</span>
        </div>
      )}
    </section>
  );
}
