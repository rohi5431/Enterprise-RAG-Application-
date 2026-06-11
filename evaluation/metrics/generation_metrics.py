"""
Generation Metrics — LLM-based evaluation of RAG responses using Ollama
"""
from __future__ import annotations

import logging
import re
from typing import Optional

from rag.llm.ollama_client import OllamaClient

logger = logging.getLogger(__name__)


class GenerationEvaluator:
    """Uses Ollama to evaluate RAG generation quality metrics."""

    def __init__(self, llm: Optional[OllamaClient] = None) -> None:
        self.llm = llm or OllamaClient()

    def faithfulness(self, answer: str, context: str) -> float:
        """
        Evaluate if the answer is grounded in the context (no hallucination).
        Returns a score between 0.0 and 1.0.
        """
        prompt = f"""
You are an expert evaluator. Evaluate if the generated answer is faithful to the provided context.
Answer only based on facts directly supported by the context. Hallucinations or extra facts not in context are unfaithful.

Context:
{context}

Generated Answer:
{answer}

Output a single JSON object in the following format:
{{
  "score": <score_from_0_to_100>,
  "reasoning": "<brief_reasoning>"
}}
"""
        try:
            response = self.llm.generate(prompt)
            score = self._parse_json_score(response)
            return score / 100.0
        except Exception as exc:
            logger.error("Failed to compute faithfulness score: %s", exc)
            return 0.5

    def context_relevance(self, query: str, context: str) -> float:
        """
        Evaluate if the retrieved context is relevant to the user query.
        Returns a score between 0.0 and 1.0.
        """
        prompt = f"""
You are an expert evaluator. Evaluate if the retrieved context is relevant and useful for answering the query.

Query:
{query}

Retrieved Context:
{context}

Output a single JSON object in the following format:
{{
  "score": <score_from_0_to_100>,
  "reasoning": "<brief_reasoning>"
}}
"""
        try:
            response = self.llm.generate(prompt)
            score = self._parse_json_score(response)
            return score / 100.0
        except Exception as exc:
            logger.error("Failed to compute context relevance score: %s", exc)
            return 0.5

    def answer_relevance(self, query: str, answer: str) -> float:
        """
        Evaluate if the generated answer directly addresses the query.
        Returns a score between 0.0 and 1.0.
        """
        prompt = f"""
You are an expert evaluator. Evaluate if the generated answer is relevant and directly addresses the query.
Score lower if the answer is vague, incomplete, or misses the point.

Query:
{query}

Generated Answer:
{answer}

Output a single JSON object in the following format:
{{
  "score": <score_from_0_to_100>,
  "reasoning": "<brief_reasoning>"
}}
"""
        try:
            response = self.llm.generate(prompt)
            score = self._parse_json_score(response)
            return score / 100.0
        except Exception as exc:
            logger.error("Failed to compute answer relevance score: %s", exc)
            return 0.5

    def _parse_json_score(self, text: str) -> int:
        """Helper to extract score from raw LLM output, falling back to regex search."""
        try:
            # Try parsing whole text as JSON
            data = json.loads(text.strip())
            return int(data.get("score", 50))
        except Exception:
            # Fallback to regex search
            match = re.search(r'"score"\s*:\s*(\d+)', text)
            if match:
                return int(match.group(1))
            # Second fallback: find first number in string
            num_match = re.search(r'\b([0-9]{1,3})\b', text)
            if num_match:
                val = int(num_match.group(1))
                return min(val, 100)
            return 50
