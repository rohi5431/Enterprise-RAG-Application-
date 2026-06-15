"""
Prompt Builder
==============
Constructs prompts for RAG generation.

Supports:
- Retrieved context
- Conversation memory
- Source-aware prompting
"""

from __future__ import annotations

from typing import List, Optional

from rag.retrieval.schemas import RetrievedChunk


class PromptBuilder:
    """
    Builds prompts for LLM generation.
    """

    def build(
        self,
        query: str,
        chunks: List[RetrievedChunk],
        conversation_history: Optional[str] = None,
    ) -> str:

        context = self._build_context(chunks)

        history_section = ""

        if conversation_history:
            history_section = (
                "Conversation History:\n"
                f"{conversation_history}\n\n"
            )

        prompt = f"""
You are a helpful AI assistant.

Answer ONLY using the provided context.

If the answer is not present in the context,
say:
"I could not find that information in the provided documents."

{history_section}
Context:
{context}

Question:
{query}

Answer:
""".strip()

        return prompt

    def _build_context(
        self,
        chunks: List[RetrievedChunk],
    ) -> str:

        context_parts = []

        for idx, chunk in enumerate(chunks, start=1):

            source = (
                chunk.doc_filename
                or chunk.doc_title
                or f"Doc {chunk.doc_id}"
            )

            page = (
                f"Page {chunk.page_number}"
                if chunk.page_number is not None
                else "Page Unknown"
            )

            context_parts.append(
                f"[{idx}] ({source}) {page}\n"
                f"{chunk.text}"
            )

        return "\n\n---\n\n".join(context_parts)