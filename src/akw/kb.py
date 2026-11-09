"""Knowledge Base orchestrator managing ingestion, indexing, and retrieval."""

from __future__ import annotations

import hashlib
import io
import os
from pathlib import Path
from typing import BinaryIO, Dict, List, Optional, Tuple, Union

from akw.chunking.chunker import WindowedSemanticChunker
from akw.core.config import AKWConfig
from akw.core.exceptions import StorageError
from akw.core.models import (
    Chunk,
    Citation,
    CommitChunksRequest,
    Document,
    ExpandedContextBlock,
    StagedChunk,
    StagedDocument,
)
from akw.embeddings.engine import EmbeddingEngine
from akw.parsers.factory import ParserFactory
from akw.parsers.vision import VisionEngine
from akw.retrieval.engine import HybridRetrievalEngine
from akw.storage.assets import AssetManager
from akw.storage.sqlite_db import SQLiteStorage


class KnowledgeBase:
    """High-level Knowledge Base interface for local document management and hybrid search."""

    def __init__(self, config: Optional[AKWConfig] = None):
        self.config = config or AKWConfig()
        self.storage = SQLiteStorage(db_path=self.config.db_path)
        self.asset_manager = AssetManager(assets_dir=self.config.assets_dir)
        self.embedder = EmbeddingEngine(config=self.config)
        self.vision_engine = VisionEngine(config=self.config)
        self.chunker = WindowedSemanticChunker(
            target_chunk_size=self.config.target_chunk_size,
            chunk_overlap=self.config.chunk_overlap,
        )
        self.retrieval_engine = HybridRetrievalEngine(
            storage=self.storage,
            embedder=self.embedder,
            config=self.config,
        )

    def add_document(
        self,
        file_source: Union[str, Path, BinaryIO, bytes],
        filename: Optional[str] = None,
        metadata: Optional[Dict[str, any]] = None,
    ) -> Document:
        """Ingest, parse, chunk, embed, and index a single document."""
        # 1. Resolve source and read raw bytes for SHA-256 computation
        file_path_str: Optional[str] = None
        if isinstance(file_source, (str, Path)):
            path = Path(file_source)
            if not path.exists():
                raise FileNotFoundError(f"File not found: {path}")
            fname = filename or path.name
            file_path_str = str(path.resolve())
            with open(path, "rb") as f:
                raw_bytes = f.read()
        elif isinstance(file_source, bytes):
            raw_bytes = file_source
            fname = filename or "unnamed_document"
        else:
            raw_bytes = file_source.read()
            fname = filename or "unnamed_document"

        sha256_hash = hashlib.sha256(raw_bytes).hexdigest()

        # 2. Check for duplicate content
        existing = self.storage.get_document_by_hash(sha256_hash)
        if existing:
            return existing

        # 3. Parse content
        parser = ParserFactory.get_parser(
            fname, vision_engine=self.vision_engine, asset_manager=self.asset_manager
        )
        blocks = parser.parse(raw_bytes, filename=fname)

        doc_id = f"doc_{sha256_hash[:12]}"

        # Ensure retained local copy of original file is saved for user downloads
        files_dir = Path(self.config.files_dir).resolve()
        files_dir.mkdir(parents=True, exist_ok=True)
        permanent_file = files_dir / f"{doc_id}_{fname}"
        if not permanent_file.exists():
            permanent_file.write_bytes(raw_bytes)
        file_path_str = str(permanent_file)

        # 4. Chunk content with breadcrumbs
        chunks = self.chunker.chunk_blocks(blocks, document_id=doc_id)

        # 5. Create Document record
        doc = Document(
            id=doc_id,
            filename=fname,
            file_path=file_path_str,
            sha256_hash=sha256_hash,
            mime_type=Path(fname).suffix.lower(),
            file_size_bytes=len(raw_bytes),
            total_chunks=len(chunks),
            metadata=metadata or {},
        )

        # 6. Store document and chunks in SQLite
        self.storage.insert_document(doc)
        if chunks:
            self.storage.insert_chunks(chunks)

            # 7. Generate and store embeddings (including breadcrumb in text representation)
            texts_to_embed = [
                f"{c.breadcrumb_display}\n{c.content}" if c.breadcrumb_display else c.content
                for c in chunks
            ]
            embeddings = self.embedder.embed_texts(texts_to_embed)
            embedding_map = {c.id: embeddings[idx] for idx, c in enumerate(chunks)}
            self.storage.store_embeddings(embedding_map, model_name=self.config.embedding_model)

        return doc

    def stage_document(
        self,
        file_source: Union[str, Path, BinaryIO, bytes],
        filename: Optional[str] = None,
        metadata: Optional[Dict[str, any]] = None,
    ) -> StagedDocument:
        """Parse and chunk a document into a draft stage for user inspection, editing, and curation."""
        if isinstance(file_source, (str, Path)):
            path = Path(file_source)
            if not path.exists():
                raise FileNotFoundError(f"File not found: {path}")
            fname = filename or path.name
            with open(path, "rb") as f:
                raw_bytes = f.read()
        elif isinstance(file_source, bytes):
            raw_bytes = file_source
            fname = filename or "unnamed_document"
        else:
            raw_bytes = file_source.read()
            fname = filename or "unnamed_document"

        sha256_hash = hashlib.sha256(raw_bytes).hexdigest()
        staging_id = f"stg_{sha256_hash[:12]}"

        # Save staged original file copy on disk for persistence and download
        files_dir = Path(self.config.files_dir).resolve()
        files_dir.mkdir(parents=True, exist_ok=True)
        staged_file = files_dir / f"{staging_id}_{fname}"
        if not staged_file.exists():
            staged_file.write_bytes(raw_bytes)

        # Parse content into blocks
        parser = ParserFactory.get_parser(
            fname, vision_engine=self.vision_engine, asset_manager=self.asset_manager
        )
        blocks = parser.parse(raw_bytes, filename=fname)

        # Chunk blocks
        temp_chunks = self.chunker.chunk_blocks(blocks, document_id=staging_id)

        staged_chunks = [
            StagedChunk(
                staging_id=f"chk_{idx}_{staging_id}",
                chunk_index=idx,
                content=c.content,
                breadcrumb_display=c.breadcrumb_display,
                breadcrumb_path=c.breadcrumb_path,
                page_start=c.page_start,
                page_end=c.page_end,
                token_count=c.token_count,
                is_retained=True,
                is_modified=False,
                metadata=dict(c.metadata) if c.metadata else {},
            )
            for idx, c in enumerate(temp_chunks)
        ]

        return StagedDocument(
            staging_id=staging_id,
            filename=fname,
            sha256_hash=sha256_hash,
            mime_type=Path(fname).suffix.lower(),
            file_size_bytes=len(raw_bytes),
            chunks=staged_chunks,
            file_path=str(staged_file),
        )

    def commit_staged_chunks(self, request: CommitChunksRequest) -> Document:
        """Commit reviewed and curated draft chunks to the SQLite knowledge base."""
        # 1. Filter only retained chunks
        retained = [c for c in request.chunks if c.is_retained and c.content.strip()]
        if not retained:
            raise ValueError("Cannot commit document with 0 retained chunks.")

        doc_id = f"doc_{request.sha256_hash[:12]}"

        # Ensure permanent copy exists in files_dir for downloading
        files_dir = Path(self.config.files_dir).resolve()
        files_dir.mkdir(parents=True, exist_ok=True)
        final_file_path = files_dir / f"{doc_id}_{request.filename}"

        if request.file_path and Path(request.file_path).exists() and not final_file_path.exists():
            try:
                import shutil
                shutil.copy2(request.file_path, final_file_path)
            except Exception:
                pass
        elif not final_file_path.exists():
            staged_candidate = files_dir / f"{request.staging_id}_{request.filename}"
            if staged_candidate.exists():
                try:
                    import shutil
                    shutil.copy2(staged_candidate, final_file_path)
                except Exception:
                    pass

        actual_file_path = str(final_file_path) if final_file_path.exists() else request.file_path

        # 2. Re-index sequentially and create final Chunk records
        final_chunks: List[Chunk] = []
        texts_to_embed: List[str] = []

        for idx, sc in enumerate(retained):
            token_count = self.chunker.count_tokens(sc.content)
            chunk_obj = Chunk(
                id=f"chk_{request.sha256_hash[:8]}_{idx:04d}",
                document_id=doc_id,
                chunk_index=idx,
                content=sc.content.strip(),
                breadcrumb_display=sc.breadcrumb_display.strip(),
                breadcrumb_path=sc.breadcrumb_path or ([sc.breadcrumb_display] if sc.breadcrumb_display else []),
                page_start=sc.page_start,
                page_end=sc.page_end,
                token_count=token_count,
                metadata=dict(sc.metadata) if sc.metadata else {},
            )
            final_chunks.append(chunk_obj)
            texts_to_embed.append(
                f"{chunk_obj.breadcrumb_display}\n{chunk_obj.content}"
                if chunk_obj.breadcrumb_display
                else chunk_obj.content
            )

        # 3. Create Document record
        doc = Document(
            id=doc_id,
            filename=request.filename,
            file_path=actual_file_path,
            sha256_hash=request.sha256_hash,
            mime_type=request.mime_type or Path(request.filename).suffix.lower(),
            file_size_bytes=request.file_size_bytes,
            total_chunks=len(final_chunks),
            metadata=request.metadata or {},
        )

        # 4. Save to SQLite
        self.storage.insert_document(doc)
        self.storage.insert_chunks(final_chunks)

        # 5. Embed and store vectors
        embeddings = self.embedder.embed_texts(texts_to_embed)
        embedding_map = {c.id: embeddings[idx] for idx, c in enumerate(final_chunks)}
        self.storage.store_embeddings(embedding_map, model_name=self.config.embedding_model)

        return doc

    def update_chunk(
        self, chunk_id: str, new_content: str, new_breadcrumb: Optional[str] = None
    ) -> Optional[Chunk]:
        """Modify an already committed chunk and refresh its dense embedding."""
        token_count = self.chunker.count_tokens(new_content)
        updated = self.storage.update_chunk(
            chunk_id=chunk_id,
            new_content=new_content,
            new_breadcrumb=new_breadcrumb,
            token_count=token_count,
        )
        if updated:
            embed_text = (
                f"{updated.breadcrumb_display}\n{updated.content}"
                if updated.breadcrumb_display
                else updated.content
            )
            new_vec = self.embedder.embed_query(embed_text)
            self.storage.store_embeddings({updated.id: new_vec}, model_name=self.config.embedding_model)
        return updated

    def delete_chunk(self, chunk_id: str) -> bool:
        """Delete an individual chunk from SQLite and its vector embedding."""
        return self.storage.delete_chunk(chunk_id)

    def delete_chunks(self, chunk_ids: List[str]) -> int:
        """Batch delete multiple chunks from SQLite and their vector embeddings."""
        return self.storage.delete_chunks(chunk_ids)

    def add_directory(
        self,
        directory_path: Union[str, Path],
        recursive: bool = True,
        extensions: Optional[List[str]] = None,
    ) -> List[Document]:
        """Ingest all supported documents in a directory."""
        path = Path(directory_path)
        if not path.is_dir():
            raise NotADirectoryError(f"Directory not found: {path}")

        valid_exts = set(ext.lower() for ext in extensions) if extensions else set(ParserFactory._EXTENSION_MAP.keys())

        ingested: List[Document] = []
        pattern = "**/*" if recursive else "*"
        for item in path.glob(pattern):
            if item.is_file() and item.suffix.lower() in valid_exts:
                try:
                    doc = self.add_document(item)
                    ingested.append(doc)
                except Exception as e:
                    # Continue indexing other files on error
                    continue

        return ingested

    def search(
        self, query: str, top_k: Optional[int] = None, expand_window: Optional[int] = None
    ) -> Tuple[List[ExpandedContextBlock], List[Citation]]:
        """Execute hybrid search with HyDE, RRF, reranking, and window expansion (+/- 2 chunks)."""
        return self.retrieval_engine.retrieve(query=query, top_k=top_k, expand_window=expand_window)

    def list_documents(self) -> List[Document]:
        """List all documents currently in the knowledge base."""
        return self.storage.list_documents()

    def get_document(self, document_id: str) -> Optional[Document]:
        """Fetch a document by ID."""
        return self.storage.get_document(document_id)

    def get_document_file_path(self, document_id: str) -> Optional[Path]:
        """Resolve the local file path of the original uploaded document for downloads."""
        doc = self.storage.get_document(document_id)
        if not doc:
            return None
        if doc.file_path and Path(doc.file_path).exists():
            return Path(doc.file_path)

        files_dir = Path(self.config.files_dir).resolve()
        matches = list(files_dir.glob(f"{document_id}_*"))
        if matches and matches[0].exists():
            return matches[0]
        return None

    def get_chunks(self, document_id: str) -> List[Chunk]:
        """Get all chunks for a document ordered by index."""
        return self.storage.get_chunks_for_document(document_id)

    def delete_document(self, document_id: str) -> bool:
        """Delete a document and all associated chunks, vectors, and FTS records."""
        return self.storage.delete_document(document_id)

