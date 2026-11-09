"""Prompt Builder for Grounded RAG with strict citation contracts."""

from __future__ import annotations

import re
from typing import List, Tuple

from akw.core.models import Citation, ExpandedContextBlock


class PromptBuilder:
    """Constructs grounded prompts containing retrieved context and extracts cited references."""

    SYSTEM_INSTRUCTION_TEMPLATE = (
        "You are an authoritative and precise knowledge assistant. Your goal is to answer the user's "
        "question strictly using the facts present in the provided Document Context.\n\n"
        "### STRICT CITATION RULES:\n"
        "1. Every factual statement, policy rule, metric, or procedure MUST be followed by its citation tag, e.g. [REF-1].\n"
        "2. If multiple sources support a statement, combine citations, e.g. [REF-1][REF-2].\n"
        "3. Do NOT make up facts or extrapolate beyond the provided text.\n"
        "4. If the provided context does not contain enough information to answer the question, state clearly: "
        "'Based on the local knowledge base, I cannot find sufficient information to answer this question.'\n"
        "5. Conclude your answer with a 'References' section listing each citation tag used, its document name, and section."
    )

    CITATION_REGEX = re.compile(r"\[(REF-\d+)\]")

    @classmethod
    def build_user_prompt(cls, query: str, context_blocks: List[ExpandedContextBlock]) -> str:
        """Assemble retrieved context blocks into structured prompt context."""
        if not context_blocks:
            return (
                f"### CONTEXT:\nNo relevant documents were found in the local knowledge base.\n\n"
                f"### USER QUERY:\n{query}"
            )

        context_sections = []
        for block in context_blocks:
            page_info = ""
            if block.page_start:
                page_info = f" | Page {block.page_start}"
                if block.page_end and block.page_end != block.page_start:
                    page_info += f"-{block.page_end}"

            section_header = (
                f"--- BEGIN {block.citation_id} ---\n"
                f"Document: {block.document_name}{page_info}\n"
                f"Breadcrumb: {block.breadcrumb}\n"
                f"Relevance: {block.relevance_score:.3f}\n\n"
                f"{block.merged_text}\n"
                f"--- END {block.citation_id} ---"
            )
            context_sections.append(section_header)

        assembled_context = "\n\n".join(context_sections)

        prompt = (
            f"### DOCUMENT CONTEXT:\n\n"
            f"{assembled_context}\n\n"
            f"### USER QUERY:\n"
            f"{query}\n\n"
            f"### GROUNDED ANSWER (with [REF-X] citations):"
        )
        return prompt

    @classmethod
    def extract_cited_references(
        cls, response_text: str, available_citations: List[Citation]
    ) -> List[Citation]:
        """Extract which citation IDs from available_citations were cited in response_text."""
        found_tags = set(cls.CITATION_REGEX.findall(response_text))
        citation_map = {c.id: c for c in available_citations}
        return [citation_map[tag] for tag in sorted(found_tags) if tag in citation_map]

