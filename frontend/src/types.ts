export type User = {
  id: number;
  email: string;
  full_name: string | null;
};

export type TokenResponse = {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
};

export type ChatMessage = {
  id?: number;
  role: "user" | "assistant" | "system";
  content: string;
  created_at?: string;
};

export type ChatResponse = {
  answer: string;
  query: string;
  session_id: number;
  message_id: number;
  feedback_id: string;
  confidence: number;
  citations: Array<{
    citation_number: number;
    chunk_id: string;
    doc_id: number;
    doc_title: string | null;
    doc_filename: string | null;
    filename: string | null;
    page_number: number | null;
    text_snippet: string;
    score: number;
    rerank_score: number | null;
  }>;
  num_sources: number;
  retrieval_latency_ms: number;
  llm_latency_ms: number;
  total_latency_ms: number;
  cache_hit: boolean;
};

export type SessionSummary = {
  id: number;
  title: string | null;
  summary: string | null;
  message_count: number;
  is_active: boolean;
  created_at: string;
  last_message_at: string | null;
};

export type MessageResponse = {
  id: number;
  session_id: number;
  role: "user" | "assistant" | "system";
  content: string;
  sources: Array<unknown>;
  created_at: string;
};
