type MessageBubbleProps = {
  role: "user" | "assistant" | "system";
  content: string;
};

export function MessageBubble({ role, content }: MessageBubbleProps) {
  return (
    <div className={`message-bubble ${role}`}>
      <div className="message-role">{role === "assistant" ? "AI" : role === "user" ? "You" : "System"}</div>
      <div className="message-content">{content}</div>
    </div>
  );
}
