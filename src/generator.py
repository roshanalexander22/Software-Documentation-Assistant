"""
Grounded Generation Engine with Strict Citation Formatting and Abstention Handling.
Supports Google Gemini via google-genai SDK with a deterministic grounded fallback.
"""

from dataclasses import dataclass
from typing import Optional
import os
import re
from src.retriever import RetrievalResult
from src.config import settings


@dataclass
class GenerationOutput:
    """Encapsulates generated answer, citation list, confidence score, and abstention status."""
    query: str
    answer: str
    citations: list[str]
    is_abstained: bool
    confidence_score: float
    model_name: str
    latency_ms: float = 0.0


class GroundedGenerator:
    """
    RAG Generation Engine.
    Enforces factual grounding, mandatory citations in [Doc: <id> | Section: <sec> | Ver: <ver>] format,
    and automatic abstention when evidence is insufficient.
    """

    SYSTEM_PROMPT = """You are an expert Software Documentation Assistant.
Your mission is to provide accurate, version-relevant technical explanations and code examples strictly grounded in the provided technical documentation passages.

CRITICAL RULES:
1. STRICT GROUNDING: Answer ONLY using information explicitly stated in the EVIDENCE PASSAGES below.
2. NO HALLUCINATION: Never invent API endpoints, classes, decorator names, or version compatibility rules not present in the evidence.
3. CITATIONS: Whenever stating a technical fact or presenting a code snippet, append its source citation in this exact format: [Doc: <doc_id> | Section: '<section>' | Ver: <version>].
4. CODE EXAMPLES: When code snippets are present in the evidence, preserve them with appropriate Markdown ```python blocks.
5. ABSTENTION: If the evidence passages do not contain sufficient information to answer the question accurately, or if the question asks about a nonexistent/unrelated feature, you MUST state:
"[ABSTENTION] Based on the indexed technical documentation, there is insufficient evidence to answer this question."
Do not attempt to fabricate an answer.
"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        temperature: float = 0.0,
        abstention_threshold: float = 0.38
    ):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or settings.GEMINI_API_KEY
        self.model_name = model_name or settings.GEMINI_MODEL
        self.temperature = temperature
        self.abstention_threshold = abstention_threshold
        self._genai_client = None

        if self.api_key:
            try:
                from google import genai
                self._genai_client = genai.Client(api_key=self.api_key)
                print(f"[INFO] Initialized Google GenAI Client with model: {self.model_name}")
            except Exception as e:
                print(f"[WARN] Could not initialize google.genai Client ({e}). Using deterministic grounded generator.")

    def generate(self, retrieval_result: RetrievalResult) -> GenerationOutput:
        """
        Generates a grounded response with citations or abstains if evidence is insufficient.
        """
        import time
        start_time = time.perf_counter()

        # Rule 1: Pre-generation Abstention Check
        if not retrieval_result.has_sufficient_evidence or len(retrieval_result.chunks) == 0:
            latency = (time.perf_counter() - start_time) * 1000.0
            abstain_msg = (
                f"[ABSTENTION] Based on the indexed technical documentation, there is insufficient evidence "
                f"to answer the question: '{retrieval_result.query}'. The knowledge base does not contain "
                f"matching API explanations or code examples for this query (Top similarity score: {retrieval_result.top_score:.3f} "
                f"below threshold {self.abstention_threshold:.2f})."
            )
            return GenerationOutput(
                query=retrieval_result.query,
                answer=abstain_msg,
                citations=[],
                is_abstained=True,
                confidence_score=retrieval_result.top_score,
                model_name=self.model_name,
                latency_ms=latency
            )

        # Rule 2: LLM Generation via Google GenAI SDK if client available
        if self._genai_client is not None:
            try:
                output = self._generate_with_gemini(retrieval_result, start_time)
                return output
            except Exception as e:
                print(f"[WARN] Gemini generation failed ({e}). Falling back to deterministic grounded engine.")

        # Rule 3: Deterministic Grounded Generation Mode (Offline / Fallback)
        output = self._generate_deterministic_grounded(retrieval_result, start_time)
        return output

    def _generate_with_gemini(self, res: RetrievalResult, start_time: float) -> GenerationOutput:
        """Calls Google GenAI SDK with structured prompt."""
        from google.genai import types
        import time

        user_content = (
            f"USER QUESTION: {res.query}\n\n"
            f"DETECTED VERSION CONTEXT: {res.detected_version or 'General'}\n\n"
            f"EVIDENCE PASSAGES:\n{res.formatted_context}\n\n"
            f"INSTRUCTIONS:\nProvide a clear, version-relevant technical explanation with code examples "
            f"and inline citations matching the format [Doc: <id> | Section: '<sec>' | Ver: <ver>]. "
            f"If the passages do not answer the question, output [ABSTENTION] as instructed."
        )

        response = self._genai_client.models.generate_content(
            model=self.model_name,
            contents=[
                types.Content(
                    role="system",
                    parts=[types.Part.from_text(text=self.SYSTEM_PROMPT)]
                ),
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=user_content)]
                )
            ],
            config=types.GenerateContentConfig(
                temperature=self.temperature,
                max_output_tokens=1024
            )
        )

        answer_text = response.text or ""
        latency = (time.perf_counter() - start_time) * 1000.0

        is_abstained = "[ABSTENTION]" in answer_text or "insufficient evidence" in answer_text.lower()
        citations = self._extract_citations(answer_text)
        if not citations and not is_abstained:
            # Fallback attach citations of top retrieved chunks
            citations = [c.citation for c in res.chunks[:2]]

        return GenerationOutput(
            query=res.query,
            answer=answer_text,
            citations=citations,
            is_abstained=is_abstained,
            confidence_score=res.top_score,
            model_name=self.model_name,
            latency_ms=latency
        )

    def _generate_deterministic_grounded(self, res: RetrievalResult, start_time: float) -> GenerationOutput:
        """
        Synthesizes a grounded, formatted technical response from top retrieved passages.
        Preserves code blocks and attaches exact citations.
        """
        import time

        top_chunk = res.chunks[0]
        citations = [top_chunk.citation]

        # Check for secondary supporting chunk
        secondary_chunk = res.chunks[1] if len(res.chunks) > 1 and res.combined_scores[1] > 0.45 else None
        if secondary_chunk and secondary_chunk.doc_id != top_chunk.doc_id:
            citations.append(secondary_chunk.citation)

        # Build grounded synthesis
        sections = []
        sections.append(f"### Technical Overview ({top_chunk.framework} {top_chunk.version})\n")
        sections.append(
            f"According to the official {top_chunk.framework} documentation ({top_chunk.title}), "
            f"in section **'{top_chunk.section}'** (Target Version: `{top_chunk.version}`):\n"
        )

        # Extract prose summary
        lines = [line.strip() for line in top_chunk.content.split("\n") if line.strip() and not line.startswith("```")]
        prose_summary = " ".join(lines[:3]) if lines else top_chunk.content[:200]
        sections.append(f"{prose_summary} {top_chunk.citation}\n")

        # Extract and format code block if present
        code_match = re.search(r"```([a-zA-Z0-9_-]*\n[\s\S]*?```)", top_chunk.content)
        if code_match:
            code_block = code_match.group(0)
            sections.append("\n**Implementation Code Example:**\n")
            sections.append(f"{code_block}\n")
            sections.append(f"*Source: {top_chunk.citation}*\n")
        elif secondary_chunk:
            sec_code_match = re.search(r"```([a-zA-Z0-9_-]*\n[\s\S]*?```)", secondary_chunk.content)
            if sec_code_match:
                sections.append("\n**Implementation Code Example:**\n")
                sections.append(f"{sec_code_match.group(0)}\n")
                sections.append(f"*Source: {secondary_chunk.citation}*\n")

        # If comparing versions (e.g. migration or legacy)
        if secondary_chunk and ("v1" in secondary_chunk.version or "v2" in secondary_chunk.version or "legacy" in secondary_chunk.version):
            sections.append(f"\n### Version Comparison & Deprecation Notice\n")
            sec_lines = [l.strip() for l in secondary_chunk.content.split("\n") if l.strip() and not l.startswith("```")]
            sec_prose = " ".join(sec_lines[:2])
            sections.append(f"Regarding version `{secondary_chunk.version}`: {sec_prose} {secondary_chunk.citation}\n")

        answer_text = "\n".join(sections)
        latency = (time.perf_counter() - start_time) * 1000.0

        return GenerationOutput(
            query=res.query,
            answer=answer_text,
            citations=citations,
            is_abstained=False,
            confidence_score=res.top_score,
            model_name="deterministic-grounded-engine",
            latency_ms=latency
        )

    def _extract_citations(self, text: str) -> list[str]:
        """Extracts [Doc: ... | Section: ... | Ver: ...] citation patterns."""
        matches = re.findall(r"\[Doc:\s*[^\]]+\]", text)
        return list(dict.fromkeys(matches))  # remove duplicates while preserving order
