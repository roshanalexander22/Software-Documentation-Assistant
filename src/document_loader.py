"""
Document Loader module for Software Documentation Assistant.
Reads Markdown technical documentation files and parses frontmatter metadata.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import re
import yaml


@dataclass
class Document:
    """Represents an ingested documentation file with its structured metadata."""
    doc_id: str
    title: str
    version: str
    framework: str
    category: str
    tags: list[str]
    source_url: str
    content: str
    file_path: str = ""
    char_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        self.char_count = len(self.content)
        if not self.metadata:
            self.metadata = {
                "doc_id": self.doc_id,
                "title": self.title,
                "version": self.version,
                "framework": self.framework,
                "category": self.category,
                "tags": self.tags,
                "source_url": self.source_url,
                "file_path": self.file_path,
            }


class DocumentLoader:
    """Loads and parses Markdown documentation files with YAML frontmatter."""

    FRONTMATTER_REGEX = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)

    def __init__(self, docs_dir: Path | str):
        self.docs_dir = Path(docs_dir)

    def load_document(self, file_path: Path | str) -> Document:
        """Parses a single Markdown document and extracts frontmatter metadata."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Document file not found: {path}")

        text = path.read_text(encoding="utf-8")
        match = self.FRONTMATTER_REGEX.match(text)

        if match:
            frontmatter_raw, body = match.groups()
            try:
                meta = yaml.safe_load(frontmatter_raw) or {}
            except Exception as e:
                meta = {}
        else:
            meta = {}
            body = text

        doc_id = str(meta.get("doc_id", path.stem))
        title = str(meta.get("title", path.stem.replace("_", " ").title()))
        version = str(meta.get("version", "latest"))
        framework = str(meta.get("framework", "General"))
        category = str(meta.get("category", "General"))
        tags = meta.get("tags", [])
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",")]
        source_url = str(meta.get("source_url", ""))

        return Document(
            doc_id=doc_id,
            title=title,
            version=version,
            framework=framework,
            category=category,
            tags=tags,
            source_url=source_url,
            content=body.strip(),
            file_path=str(path),
        )

    def load_all(self) -> list[Document]:
        """Loads all Markdown (.md) documents from the target directory."""
        if not self.docs_dir.exists():
            return []

        doc_files = sorted(list(self.docs_dir.glob("*.md")))
        documents = []
        for file_path in doc_files:
            try:
                doc = self.load_document(file_path)
                documents.append(doc)
            except Exception as e:
                print(f"[WARN] Failed to load {file_path}: {e}")

        return documents
