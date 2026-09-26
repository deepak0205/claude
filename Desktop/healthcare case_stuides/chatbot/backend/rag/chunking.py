"""Chunk markdown docs into retrievable passages, split on headings then a word-count sliding window."""
from dataclasses import dataclass
from pathlib import Path

from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter


@dataclass
class Chunk:
    doc_id: str
    heading: str
    text: str


def load_docs(docs_dir: Path) -> dict[str, str]:
    return {p.name: p.read_text(encoding="utf-8") for p in sorted(docs_dir.glob("*.md"))}


def chunk_markdown(doc_id: str, text: str, chunk_size_words: int = 200, chunk_overlap_words: int = 40) -> list[Chunk]:
    header_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=[("#", "h1"), ("##", "h2"), ("###", "h3")],
        strip_headers=False,
    )
    sections = header_splitter.split_text(text)

    char_size = chunk_size_words * 6
    char_overlap = chunk_overlap_words * 6
    sub_splitter = RecursiveCharacterTextSplitter(chunk_size=char_size, chunk_overlap=char_overlap)

    chunks: list[Chunk] = []
    for section in sections:
        heading = section.metadata.get("h3") or section.metadata.get("h2") or section.metadata.get("h1") or doc_id
        for piece in sub_splitter.split_text(section.page_content):
            if piece.strip():
                chunks.append(Chunk(doc_id=doc_id, heading=heading, text=piece))
    return chunks


def build_corpus(docs_dir: Path, chunk_size_words: int = 200, chunk_overlap_words: int = 40) -> list[Chunk]:
    all_chunks: list[Chunk] = []
    for doc_id, text in load_docs(docs_dir).items():
        all_chunks.extend(chunk_markdown(doc_id, text, chunk_size_words, chunk_overlap_words))
    return all_chunks
