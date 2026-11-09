"""SQLite Storage Engine supporting Relational, FTS5 BM25, and Vector Search."""

from __future__ import annotations

import json
import sqlite3
import struct
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

try:
    import sqlite_vec
    _SQLITE_VEC_AVAILABLE = True
except Exception:
    _SQLITE_VEC_AVAILABLE = False

from akw.core.exceptions import StorageError
from akw.core.models import (
    ChatMessage,
    ChatRole,
    ChatSession,
    Chunk,
    Document,
)


class SQLiteStorage:
    """Unified SQLite storage manager for documents, chunks, FTS5 BM25, and vectors."""

    def __init__(self, db_path: str = "./knowledge_base.sqlite"):
        self.db_path = str(Path(db_path).resolve())
        # Ensure parent directory exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

    def get_connection(self) -> sqlite3.Connection:
        """Create a configured SQLite connection."""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")

        if _SQLITE_VEC_AVAILABLE:
            try:
                conn.enable_load_extension(True)
                sqlite_vec.load(conn)
                conn.enable_load_extension(False)
            except Exception:
                pass

        return conn

    def _init_database(self) -> None:
        """Create tables, FTS5 virtual tables, and triggers if they do not exist."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # 1. Documents Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                file_path TEXT,
                sha256_hash TEXT NOT NULL UNIQUE,
                mime_type TEXT NOT NULL,
                file_size_bytes INTEGER NOT NULL,
                total_chunks INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL,
                metadata_json TEXT DEFAULT '{}'
            );
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_docs_hash ON documents(sha256_hash);")

            # 2. Chunks Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS chunks (
                id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                chunk_index INTEGER NOT NULL,
                content TEXT NOT NULL,
                breadcrumb_display TEXT NOT NULL,
                breadcrumb_json TEXT NOT NULL,
                page_start INTEGER,
                page_end INTEGER,
                token_count INTEGER NOT NULL,
                metadata_json TEXT DEFAULT '{}',
                FOREIGN KEY(document_id) REFERENCES documents(id) ON DELETE CASCADE
            );
            """)
            cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_chunks_doc_idx ON chunks(document_id, chunk_index);")

            # 3. FTS5 Virtual Table for BM25
            cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
                content,
                breadcrumb_display,
                content='chunks',
                content_rowid='rowid',
                tokenize='porter unicode61'
            );
            """)

            # Triggers to keep FTS5 synchronized with Chunks table
            cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS chunks_ai AFTER INSERT ON chunks BEGIN
                INSERT INTO chunks_fts(rowid, content, breadcrumb_display)
                VALUES (new.rowid, new.content, new.breadcrumb_display);
            END;
            """)
            cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS chunks_ad AFTER DELETE ON chunks BEGIN
                INSERT INTO chunks_fts(chunks_fts, rowid, content, breadcrumb_display)
                VALUES('delete', old.rowid, old.content, old.breadcrumb_display);
            END;
            """)
            cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS chunks_au AFTER UPDATE ON chunks BEGIN
                INSERT INTO chunks_fts(chunks_fts, rowid, content, breadcrumb_display)
                VALUES('delete', old.rowid, old.content, old.breadcrumb_display);
                INSERT INTO chunks_fts(rowid, content, breadcrumb_display)
                VALUES (new.rowid, new.content, new.breadcrumb_display);
            END;
            """)

            # 4. Chunk Embeddings Table (Portable float32 BLOBs)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS chunk_embeddings (
                chunk_id TEXT PRIMARY KEY,
                model_name TEXT NOT NULL,
                dimensions INTEGER NOT NULL,
                embedding BLOB NOT NULL,
                FOREIGN KEY(chunk_id) REFERENCES chunks(id) ON DELETE CASCADE
            );
            """)

            # 5. Chat Sessions & Messages
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_sessions (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                model_provider TEXT NOT NULL,
                model_name TEXT NOT NULL,
                system_instruction TEXT,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL
            );
            """)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                context_blocks_json TEXT,
                citations_json TEXT,
                created_at TIMESTAMP NOT NULL,
                FOREIGN KEY(session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
            );
            """)

            conn.commit()

    # --------------------------------------------------------------------------
    # Document Operations
    # --------------------------------------------------------------------------

    def insert_document(self, doc: Document) -> None:
        """Insert or replace a document record."""
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO documents 
                (id, filename, file_path, sha256_hash, mime_type, file_size_bytes, total_chunks, created_at, updated_at, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    doc.id,
                    doc.filename,
                    doc.file_path,
                    doc.sha256_hash,
                    doc.mime_type,
                    doc.file_size_bytes,
                    doc.total_chunks,
                    doc.created_at,
                    doc.updated_at,
                    json.dumps(doc.metadata),
                ),
            )
            conn.commit()

    def get_document(self, document_id: str) -> Optional[Document]:
        """Fetch document by ID."""
        with self.get_connection() as conn:
            row = conn.execute("SELECT * FROM documents WHERE id = ?", (document_id,)).fetchone()
            if not row:
                return None
            return self._row_to_document(row)

    def get_document_by_hash(self, sha256_hash: str) -> Optional[Document]:
        """Fetch document by SHA256 content hash."""
        with self.get_connection() as conn:
            row = conn.execute("SELECT * FROM documents WHERE sha256_hash = ?", (sha256_hash,)).fetchone()
            if not row:
                return None
            return self._row_to_document(row)

    def list_documents(self) -> List[Document]:
        """List all ingested documents."""
        with self.get_connection() as conn:
            rows = conn.execute("SELECT * FROM documents ORDER BY created_at DESC").fetchall()
            return [self._row_to_document(r) for r in rows]

    def delete_document(self, document_id: str) -> bool:
        """Delete document and cascade to chunks, FTS, and embeddings."""
        with self.get_connection() as conn:
            cursor = conn.execute("DELETE FROM documents WHERE id = ?", (document_id,))
            conn.commit()
            return cursor.rowcount > 0

    @staticmethod
    def _row_to_document(row: sqlite3.Row) -> Document:
        return Document(
            id=row["id"],
            filename=row["filename"],
            file_path=row["file_path"],
            sha256_hash=row["sha256_hash"],
            mime_type=row["mime_type"],
            file_size_bytes=row["file_size_bytes"],
            total_chunks=row["total_chunks"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            metadata=json.loads(row["metadata_json"] or "{}"),
        )

    # --------------------------------------------------------------------------
    # Chunk Operations
    # --------------------------------------------------------------------------

    def insert_chunks(self, chunks: List[Chunk]) -> None:
        """Batch insert chunks with automatic FTS synchronization."""
        if not chunks:
            return

        with self.get_connection() as conn:
            data = [
                (
                    c.id,
                    c.document_id,
                    c.chunk_index,
                    c.content,
                    c.breadcrumb_display,
                    json.dumps(c.breadcrumb_path),
                    c.page_start,
                    c.page_end,
                    c.token_count,
                    json.dumps(c.metadata),
                )
                for c in chunks
            ]
            conn.executemany(
                """
                INSERT OR REPLACE INTO chunks 
                (id, document_id, chunk_index, content, breadcrumb_display, breadcrumb_json, page_start, page_end, token_count, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                data,
            )
            # Update total_chunks in documents table
            doc_id = chunks[0].document_id
            conn.execute("UPDATE documents SET total_chunks = ? WHERE id = ?", (len(chunks), doc_id))
            conn.commit()

    def get_chunk(self, chunk_id: str) -> Optional[Chunk]:
        """Fetch chunk by ID."""
        with self.get_connection() as conn:
            row = conn.execute("SELECT * FROM chunks WHERE id = ?", (chunk_id,)).fetchone()
            if not row:
                return None
            return self._row_to_chunk(row)

    def update_chunk(
        self, chunk_id: str, new_content: str, new_breadcrumb: Optional[str] = None, token_count: Optional[int] = None
    ) -> Optional[Chunk]:
        """Update an existing chunk's content and breadcrumb, auto-syncing FTS."""
        with self.get_connection() as conn:
            existing = self.get_chunk(chunk_id)
            if not existing:
                return None

            bc_display = new_breadcrumb if new_breadcrumb is not None else existing.breadcrumb_display
            t_count = token_count if token_count is not None else max(1, len(new_content) // 4)

            conn.execute(
                """
                UPDATE chunks 
                SET content = ?, breadcrumb_display = ?, token_count = ?
                WHERE id = ?
                """,
                (new_content, bc_display, t_count, chunk_id),
            )
            conn.commit()
            return self.get_chunk(chunk_id)

    def delete_chunk(self, chunk_id: str) -> bool:
        """Delete an individual chunk and update document count."""
        return self.delete_chunks([chunk_id]) > 0

    def delete_chunks(self, chunk_ids: List[str]) -> int:
        """Batch delete multiple chunks and update document counts in a single transaction."""
        if not chunk_ids:
            return 0

        with self.get_connection() as conn:
            # Find affected document IDs first
            placeholders = ",".join("?" for _ in chunk_ids)
            doc_rows = conn.execute(
                f"SELECT DISTINCT document_id FROM chunks WHERE id IN ({placeholders})", chunk_ids
            ).fetchall()
            affected_doc_ids = [r["document_id"] for r in doc_rows]

            # Delete chunks
            cursor = conn.execute(f"DELETE FROM chunks WHERE id IN ({placeholders})", chunk_ids)
            deleted_count = cursor.rowcount

            # Delete associated embeddings
            conn.execute(f"DELETE FROM chunk_embeddings WHERE chunk_id IN ({placeholders})", chunk_ids)

            # Update total_chunks count for affected documents
            for doc_id in affected_doc_ids:
                conn.execute(
                    "UPDATE documents SET total_chunks = (SELECT COUNT(*) FROM chunks WHERE document_id = ?) WHERE id = ?",
                    (doc_id, doc_id),
                )
            conn.commit()
            return deleted_count

    def get_chunks_for_document(self, document_id: str) -> List[Chunk]:
        """Fetch all chunks for a document ordered by chunk_index."""
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM chunks WHERE document_id = ? ORDER BY chunk_index ASC", (document_id,)
            ).fetchall()
            return [self._row_to_chunk(r) for r in rows]

    def get_neighbor_chunks(self, document_id: str, start_index: int, end_index: int) -> List[Chunk]:
        """Fetch contiguous range of chunks within a document [start_index, end_index]."""
        with self.get_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM chunks 
                WHERE document_id = ? AND chunk_index BETWEEN ? AND ?
                ORDER BY chunk_index ASC
                """,
                (document_id, start_index, end_index),
            ).fetchall()
            return [self._row_to_chunk(r) for r in rows]

    @staticmethod
    def _row_to_chunk(row: sqlite3.Row) -> Chunk:
        return Chunk(
            id=row["id"],
            document_id=row["document_id"],
            chunk_index=row["chunk_index"],
            content=row["content"],
            breadcrumb_display=row["breadcrumb_display"],
            breadcrumb_path=json.loads(row["breadcrumb_json"] or "[]"),
            page_start=row["page_start"],
            page_end=row["page_end"],
            token_count=row["token_count"],
            metadata=json.loads(row["metadata_json"] or "{}"),
        )

    # --------------------------------------------------------------------------
    # Sparse BM25 Search (FTS5)
    # --------------------------------------------------------------------------

    def search_bm25(self, query: str, limit: int = 50) -> List[Tuple[Chunk, float, int]]:
        """Search chunks using SQLite FTS5 Okapi BM25.
        
        Returns:
            List of (Chunk, bm25_score, rank_1_based)
        """
        # Sanitize query for FTS5 (escape quotes and special tokens)
        sanitized = "".join(ch if ch.isalnum() or ch in " _-" else " " for ch in query).strip()
        if not sanitized:
            return []

        # Tokenize into terms for FTS MATCH
        terms = [t for t in sanitized.split() if t]
        if not terms:
            return []
        fts_match_query = " OR ".join(f'"{t}"*' for t in terms)

        results: List[Tuple[Chunk, float, int]] = []
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                rows = cursor.execute(
                    """
                    SELECT c.*, bm25(chunks_fts, 2.0, 1.0) AS score
                    FROM chunks_fts
                    JOIN chunks c ON chunks_fts.rowid = c.rowid
                    WHERE chunks_fts MATCH ?
                    ORDER BY score ASC
                    LIMIT ?
                    """,
                    (fts_match_query, limit),
                ).fetchall()

                for rank, row in enumerate(rows, start=1):
                    chunk = self._row_to_chunk(row)
                    score = float(row["score"])
                    results.append((chunk, score, rank))
            except sqlite3.OperationalError:
                # Fallback if syntax query fails
                pass

        return results

    # --------------------------------------------------------------------------
    # Dense Vector Operations
    # --------------------------------------------------------------------------

    def store_embeddings(self, chunk_embeddings: Dict[str, np.ndarray], model_name: str) -> None:
        """Store float32 vector embeddings as BLOBs."""
        if not chunk_embeddings:
            return

        with self.get_connection() as conn:
            data = []
            for chunk_id, vec in chunk_embeddings.items():
                vec_arr = np.asarray(vec, dtype=np.float32)
                blob = vec_arr.tobytes()
                dims = len(vec_arr)
                data.append((chunk_id, model_name, dims, blob))

            conn.executemany(
                """
                INSERT OR REPLACE INTO chunk_embeddings 
                (chunk_id, model_name, dimensions, embedding)
                VALUES (?, ?, ?, ?)
                """,
                data,
            )
            conn.commit()

    def search_vectors(self, query_vector: np.ndarray, model_name: Optional[str] = None, limit: int = 50) -> List[Tuple[Chunk, float, int]]:
        """Vector similarity search using cosine distance over stored BLOBs.
        
        Returns:
            List of (Chunk, cosine_similarity_score, rank_1_based)
        """
        query_vec = np.asarray(query_vector, dtype=np.float32)
        q_norm = np.linalg.norm(query_vec)
        if q_norm == 0:
            return []
        query_vec = query_vec / q_norm

        with self.get_connection() as conn:
            sql = "SELECT chunk_id, embedding FROM chunk_embeddings"
            params = ()
            if model_name:
                sql += " WHERE model_name = ?"
                params = (model_name,)

            rows = conn.execute(sql, params).fetchall()
            if not rows:
                return []

            chunk_ids = []
            matrix_rows = []
            for r in rows:
                chunk_ids.append(r["chunk_id"])
                vec = np.frombuffer(r["embedding"], dtype=np.float32)
                matrix_rows.append(vec)

            matrix = np.array(matrix_rows, dtype=np.float32)
            # Normalize rows
            row_norms = np.linalg.norm(matrix, axis=1, keepdims=True)
            row_norms[row_norms == 0] = 1.0
            norm_matrix = matrix / row_norms

            # Compute cosine similarities
            scores = np.dot(norm_matrix, query_vec)

            # Sort descending
            top_indices = np.argsort(scores)[::-1][:limit]

            # Fetch corresponding chunks
            top_chunk_ids = [chunk_ids[i] for i in top_indices]
            chunk_map = {c.id: c for c in [self.get_chunk(cid) for cid in top_chunk_ids] if c is not None}

            results: List[Tuple[Chunk, float, int]] = []
            for rank, idx in enumerate(top_indices, start=1):
                cid = chunk_ids[idx]
                chunk = chunk_map.get(cid)
                if chunk:
                    score = float(scores[idx])
                    results.append((chunk, score, rank))

            return results

    # --------------------------------------------------------------------------
    # Chat Sessions & Messages
    # --------------------------------------------------------------------------

    def create_chat_session(self, session: ChatSession) -> None:
        """Create a new chat session."""
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO chat_sessions 
                (id, title, model_provider, model_name, system_instruction, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session.id,
                    session.title,
                    session.model_provider,
                    session.model_name,
                    session.system_instruction,
                    session.created_at,
                    session.updated_at,
                ),
            )
            conn.commit()

    def get_chat_session(self, session_id: str) -> Optional[ChatSession]:
        """Fetch chat session by ID."""
        with self.get_connection() as conn:
            row = conn.execute("SELECT * FROM chat_sessions WHERE id = ?", (session_id,)).fetchone()
            if not row:
                return None
            return ChatSession(
                id=row["id"],
                title=row["title"],
                model_provider=row["model_provider"],
                model_name=row["model_name"],
                system_instruction=row["system_instruction"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )

    def list_chat_sessions(self) -> List[ChatSession]:
        """List all chat sessions ordered by updated_at descending."""
        with self.get_connection() as conn:
            rows = conn.execute("SELECT * FROM chat_sessions ORDER BY updated_at DESC").fetchall()
            return [
                ChatSession(
                    id=r["id"],
                    title=r["title"],
                    model_provider=r["model_provider"],
                    model_name=r["model_name"],
                    system_instruction=r["system_instruction"],
                    created_at=r["created_at"],
                    updated_at=r["updated_at"],
                )
                for r in rows
            ]

    def delete_chat_session(self, session_id: str) -> bool:
        """Delete chat session and all messages."""
        with self.get_connection() as conn:
            cursor = conn.execute("DELETE FROM chat_sessions WHERE id = ?", (session_id,))
            conn.commit()
            return cursor.rowcount > 0

    def insert_chat_message(self, message: ChatMessage) -> None:
        """Insert a chat message."""
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO chat_messages 
                (id, session_id, role, content, context_blocks_json, citations_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    message.id,
                    message.session_id,
                    message.role.value if hasattr(message.role, "value") else str(message.role),
                    message.content,
                    json.dumps([b.model_dump() for b in message.context_blocks]) if message.context_blocks else None,
                    json.dumps([c.model_dump() for c in message.citations]) if message.citations else None,
                    message.created_at,
                ),
            )
            # Update session timestamp
            conn.execute("UPDATE chat_sessions SET updated_at = ? WHERE id = ?", (message.created_at, message.session_id))
            conn.commit()

    def get_session_messages(self, session_id: str) -> List[ChatMessage]:
        """Get all messages for a session ordered by created_at."""
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM chat_messages WHERE session_id = ? ORDER BY created_at ASC", (session_id,)
            ).fetchall()
            messages = []
            for r in rows:
                ctx_blocks = None
                if r["context_blocks_json"]:
                    from akw.core.models import ExpandedContextBlock
                    ctx_blocks = [ExpandedContextBlock(**item) for item in json.loads(r["context_blocks_json"])]

                cits = None
                if r["citations_json"]:
                    from akw.core.models import Citation
                    cits = [Citation(**item) for item in json.loads(r["citations_json"])]

                messages.append(
                    ChatMessage(
                        id=r["id"],
                        session_id=r["session_id"],
                        role=ChatRole(r["role"]),
                        content=r["content"],
                        context_blocks=ctx_blocks,
                        citations=cits,
                        created_at=r["created_at"],
                    )
                )
            return messages

