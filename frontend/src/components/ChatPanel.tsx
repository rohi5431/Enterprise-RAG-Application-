import {
  useEffect,
  useRef,
  useState,
  type FormEvent,
  type KeyboardEvent,
} from "react";

import { MessageBubble } from "./MessageBubble";
import type { ChatMessage } from "../types";

type ChatPanelProps = {
  messages: ChatMessage[];
  onSend: (text: string) => Promise<void>;
  loading: boolean;
  error: string | null;
  metadata: {
    confidence?: number;
    total?: number;
    llm?: number;
    retrieval?: number;
  } | null;
};

export function ChatPanel({
  messages,
  onSend,
  loading,
  error,
  metadata,
}: ChatPanelProps) {
  const [draft, setDraft] = useState("");

  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({
      behavior: "smooth",
    });
  }, [messages, loading]);

  const handleSubmit = async (
    event: FormEvent<HTMLFormElement>
  ) => {
    event.preventDefault();

    const text = draft.trim();

    if (!text || loading) return;

    await onSend(text);

    setDraft("");
  };

  const handleKeyDown = (
    event: KeyboardEvent<HTMLTextAreaElement>
  ) => {
    if (
      event.key === "Enter" &&
      !event.shiftKey
    ) {
      event.preventDefault();

      if (draft.trim()) {
        void handleSubmit(
          event as unknown as FormEvent<HTMLFormElement>
        );
      }
    }
  };

  return (
    <section className="chat-panel">
      <div className="chat-window">
        {messages.length === 0 ? (
          <div className="empty-state">
            <h2>Welcome to RAG Studio</h2>

            <p>
              Upload documents and ask questions
              about your data.
            </p>

            <div className="chat-flair">
              <span>📄 PDF</span>
              <span>📝 DOCX</span>
              <span>📚 Knowledge Base</span>
              <span>⚡ AI Search</span>
            </div>
          </div>
        ) : (
          <>
            {messages.map((message, index) => (
              <MessageBubble
                key={`${message.role}-${index}`}
                role={message.role}
                content={message.content}
              />
            ))}

            {loading && (
              <div className="message-bubble assistant">
                <div className="message-role">
                  Assistant
                </div>

                <div className="typing-indicator">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      <form
          className="composer"
          onSubmit={handleSubmit}
        >
          <div className="chat-input-row">
        
            <label className="upload-btn">
              📎
              <input
                type="file"
                hidden
              />
            </label>
        
            <textarea
              value={draft}
              rows={2}
              placeholder="Message RAG Studio..."
              onChange={(event) =>
                setDraft(event.target.value)
              }
              onKeyDown={handleKeyDown}
            />
        
            <button
              className="send-btn"
              type="submit"
              disabled={!draft.trim() || loading}
            >
              {loading ? "..." : "➤"}
            </button>
        
          </div>
        </form>

      {error && (
        <div className="chat-error">
          {error}
        </div>
      )}

      {metadata && (
        <div className="chat-flair">
          <span>
            Confidence:{" "}
            {metadata.confidence
              ? `${(metadata.confidence * 100).toFixed(1)}%`
              : "—"}
          </span>

          <span>
            LLM:{" "}
            {metadata.llm
              ? `${metadata.llm} ms`
              : "—"}
          </span>

          <span>
            Retrieval:{" "}
            {metadata.retrieval
              ? `${metadata.retrieval} ms`
              : "—"}
          </span>

          <span>
            Total:{" "}
            {metadata.total
              ? `${metadata.total} ms`
              : "—"}
          </span>
        </div>
      )}
    </section>
  );
}
