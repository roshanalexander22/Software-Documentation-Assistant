"""
Markdown and Code-Aware Document Chunker.
Splits technical documentation preserving code blocks intact and retaining header hierarchy.
"""

from dataclasses import dataclass, field
from typing import Any
import re
from src.document_loader import Document


@dataclass
class DocumentChunk:
    """Represents an atomic, searchable text passage with rich metadata."""
    chunk_id: str
    doc_id: str
    title: str
    section: str
    version: str
    framework: str
    category: str
    content: str
    char_count: int
    has_code: bool
    code_language: str = ""
    citation: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.citation:
            self.citation = f"[Doc: {self.doc_id} | Section: '{self.section}' | Ver: {self.version}]"
        if not self.metadata:
            self.metadata = {
                "chunk_id": self.chunk_id,
                "doc_id": self.doc_id,
                "title": self.title,
                "section": self.section,
                "version": self.version,
                "framework": self.framework,
                "category": self.category,
                "has_code": self.has_code,
                "code_language": self.code_language,
                "citation": self.citation,
            }


class MarkdownCodeAwareChunker:
    """
    Hierarchical chunker that:
    1. Splits Markdown along section headers (#, ##, ###).
    2. Identifies fenced code blocks (```...```) and treats them as indivisible atomic units.
    3. Bundles code with its immediate explanatory context.
    4. Slices remaining prose into overlapping chunks respecting sentence boundaries.
    """

    CODE_BLOCK_REGEX = re.compile(r"(```[a-zA-Z0-9_-]*\n[\s\S]*?```)")
    HEADER_REGEX = re.compile(r"^(#{1,3})\s+(.+)$", re.MULTILINE)

    def __init__(self, target_chunk_size: int = 650, chunk_overlap: int = 100, min_chunk_size: int = 80):
        self.target_chunk_size = target_chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size

    def chunk_document(self, document: Document) -> list[DocumentChunk]:
        """Processes a single document into an ordered list of DocumentChunks."""
        sections = self._split_by_headers(document.content)
        chunks: list[DocumentChunk] = []
        chunk_idx = 1

        for header_title, section_text in sections:
            section_chunks = self._chunk_section_preserving_code(
                section_text=section_text,
                document=document,
                header_title=header_title,
                start_index=chunk_idx
            )
            chunks.extend(section_chunks)
            chunk_idx += len(section_chunks)

        return chunks

    def chunk_all(self, documents: list[Document]) -> list[DocumentChunk]:
        """Processes a list of documents into a single flat list of chunks."""
        all_chunks = []
        for doc in documents:
            doc_chunks = self.chunk_document(doc)
            all_chunks.extend(doc_chunks)
        return all_chunks

    def _split_by_headers(self, text: str) -> list[tuple[str, str]]:
        """Splits text into (header_title, section_content) pairs."""
        matches = list(self.HEADER_REGEX.finditer(text))
        if not matches:
            return [("Overview", text.strip())]

        sections = []
        # Any text before the first header
        if matches[0].start() > 0:
            pre_text = text[:matches[0].start()].strip()
            if pre_text:
                sections.append(("Introduction", pre_text))

        for i, match in enumerate(matches):
            header_level = match.group(1)
            header_title = match.group(2).strip()
            start_pos = match.end()
            end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            content = text[start_pos:end_pos].strip()
            if content:
                sections.append((header_title, content))

        return sections

    def _chunk_section_preserving_code(
        self,
        section_text: str,
        document: Document,
        header_title: str,
        start_index: int
    ) -> list[DocumentChunk]:
        """Divides section content while keeping code blocks intact."""
        # Split text into alternating prose and code parts
        parts = self.CODE_BLOCK_REGEX.split(section_text)
        sub_chunks: list[DocumentChunk] = []
        current_buffer = ""
        current_has_code = False
        current_lang = ""
        idx = start_index

        for part in parts:
            if not part.strip():
                continue

            is_code = part.startswith("```") and part.endswith("```")

            if is_code:
                # Extract language tag if available
                first_line = part.split("\n", 1)[0]
                lang = first_line.replace("```", "").strip() or "python"

                # If current buffer + code exceeds target, flush buffer first
                if current_buffer and (len(current_buffer) + len(part) > self.target_chunk_size):
                    chunk = self._create_chunk(
                        document=document,
                        section=header_title,
                        content=current_buffer.strip(),
                        has_code=current_has_code,
                        lang=current_lang,
                        index=idx
                    )
                    sub_chunks.append(chunk)
                    idx += 1
                    current_buffer = ""
                    current_has_code = False
                    current_lang = ""

                # If code itself is large or fits with current buffer
                if len(part) >= self.target_chunk_size:
                    # Flush buffer if any
                    if current_buffer:
                        chunk = self._create_chunk(
                            document=document,
                            section=header_title,
                            content=current_buffer.strip(),
                            has_code=current_has_code,
                            lang=current_lang,
                            index=idx
                        )
                        sub_chunks.append(chunk)
                        idx += 1
                        current_buffer = ""

                    # Code block stands alone as an atomic chunk
                    chunk = self._create_chunk(
                        document=document,
                        section=header_title,
                        content=part.strip(),
                        has_code=True,
                        lang=lang,
                        index=idx
                    )
                    sub_chunks.append(chunk)
                    idx += 1
                else:
                    current_buffer = (current_buffer + "\n\n" + part).strip() if current_buffer else part
                    current_has_code = True
                    current_lang = lang
            else:
                # Prose part: split into paragraphs or sentences
                paragraphs = [p.strip() for p in part.split("\n\n") if p.strip()]
                for para in paragraphs:
                    if len(current_buffer) + len(para) + 2 <= self.target_chunk_size:
                        current_buffer = (current_buffer + "\n\n" + para).strip() if current_buffer else para
                    else:
                        if current_buffer:
                            chunk = self._create_chunk(
                                document=document,
                                section=header_title,
                                content=current_buffer.strip(),
                                has_code=current_has_code,
                                lang=current_lang,
                                index=idx
                            )
                            sub_chunks.append(chunk)
                            idx += 1
                            current_buffer = ""
                            current_has_code = False
                            current_lang = ""

                        # If single paragraph exceeds target, split by sentence
                        if len(para) > self.target_chunk_size:
                            sentence_chunks = self._split_prose_by_sentences(
                                para, document, header_title, idx
                            )
                            sub_chunks.extend(sentence_chunks)
                            idx += len(sentence_chunks)
                        else:
                            current_buffer = para

        # Flush remaining buffer
        if current_buffer and (len(current_buffer.strip()) >= self.min_chunk_size or len(sub_chunks) == 0):
            chunk = self._create_chunk(
                document=document,
                section=header_title,
                content=current_buffer.strip(),
                has_code=current_has_code,
                lang=current_lang,
                index=idx
            )
            sub_chunks.append(chunk)
        elif current_buffer and sub_chunks:
            # Append trailing tiny text to the last chunk
            last_chunk = sub_chunks[-1]
            updated_content = last_chunk.content + "\n\n" + current_buffer.strip()
            sub_chunks[-1] = self._create_chunk(
                document=document,
                section=last_chunk.section,
                content=updated_content,
                has_code=last_chunk.has_code or current_has_code,
                lang=last_chunk.code_language or current_lang,
                index=int(last_chunk.chunk_id.split("_chk")[-1])
            )

        return sub_chunks

    def _split_prose_by_sentences(
        self,
        text: str,
        document: Document,
        section: str,
        start_idx: int
    ) -> list[DocumentChunk]:
        """Splits long prose on sentence boundaries."""
        sentences = re.split(r"(?<=[.!?])\s+", text)
        chunks = []
        buf = ""
        idx = start_idx

        for s in sentences:
            if len(buf) + len(s) + 1 <= self.target_chunk_size:
                buf = (buf + " " + s).strip() if buf else s
            else:
                if buf:
                    chunks.append(self._create_chunk(document, section, buf, False, "", idx))
                    idx += 1
                buf = s

        if buf:
            chunks.append(self._create_chunk(document, section, buf, False, "", idx))

        return chunks

    def _create_chunk(
        self,
        document: Document,
        section: str,
        content: str,
        has_code: bool,
        lang: str,
        index: int
    ) -> DocumentChunk:
        """Helper to build a DocumentChunk with formatted citation and IDs."""
        chunk_id = f"{document.doc_id}_chk{index:02d}"
        citation = f"[Doc: {document.doc_id} | Section: '{section}' | Ver: {document.version}]"
        return DocumentChunk(
            chunk_id=chunk_id,
            doc_id=document.doc_id,
            title=document.title,
            section=section,
            version=document.version,
            framework=document.framework,
            category=document.category,
            content=content,
            char_count=len(content),
            has_code=has_code,
            code_language=lang,
            citation=citation,
        )
