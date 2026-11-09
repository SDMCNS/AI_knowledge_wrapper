"""Command Line Interface for AI Knowledge Wrapper (akw)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
import uvicorn

from akw.core.config import AKWConfig
from akw.kb import KnowledgeBase


def main():
    parser = argparse.ArgumentParser(
        prog="akw",
        description="AI Knowledge Wrapper: Local Grounded Knowledge Base & LLM Session Orchestrator",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # 1. 'serve' command
    serve_parser = subparsers.add_parser("serve", help="Launch the FastAPI server and Dual-View Web UI")
    serve_parser.add_argument("--host", default="127.0.0.1", help="Host address (default: 127.0.0.1)")
    serve_parser.add_argument("--port", type=int, default=8000, help="Port (default: 8000)")
    serve_parser.add_argument("--db", default="./knowledge_base.sqlite", help="SQLite DB path")
    serve_parser.add_argument("--reload", action="store_true", help="Enable auto-reload for dev")

    # 2. 'ingest' command
    ingest_parser = subparsers.add_parser("ingest", help="Ingest a document or directory into SQLite")
    ingest_parser.add_argument("path", help="Path to file or folder")
    ingest_parser.add_argument("--db", default="./knowledge_base.sqlite", help="SQLite DB path")

    # 3. 'search' command
    search_parser = subparsers.add_parser("search", help="Execute hybrid search with +/- 2 chunk window expansion")
    search_parser.add_argument("query", help="Search query string")
    search_parser.add_argument("--top-k", type=int, default=3, help="Number of seed hits (default: 3)")
    search_parser.add_argument("--window", type=int, default=2, help="Neighbor window (+/- chunks, default: 2)")
    search_parser.add_argument("--db", default="./knowledge_base.sqlite", help="SQLite DB path")

    # 4. 'examples' command
    examples_parser = subparsers.add_parser("examples", help="Manage discoverable example knowledge bases")
    examples_sub = examples_parser.add_subparsers(dest="examples_action", required=True)
    examples_sub.add_parser("list", help="List available example datasets")
    load_p = examples_sub.add_parser("load", help="Load example datasets into workspaces")
    load_p.add_argument("--example", default=None, help="Specific example ID to load")
    load_p.add_argument("--reset", action="store_true", help="Wipe and reload fresh example datasets")

    # 5. 'reset' command
    reset_parser = subparsers.add_parser("reset", help="Wipe all workspaces, databases, and local assets")
    reset_parser.add_argument("--force", action="store_true", help="Force reset without confirmation")

    args = parser.parse_args()

    if args.command == "serve":
        import os
        os.environ["AKW_DB_PATH"] = args.db
        print(f"\n=======================================================")
        print(f"  AI Knowledge Wrapper (akw) - Local RAG Server")
        print(f"  Database : {Path(args.db).resolve()}")
        print(f"  Web UI   : http://{args.host}:{args.port}/")
        print(f"  API Docs : http://{args.host}:{args.port}/docs")
        print(f"=======================================================\n")
        uvicorn.run("server.app:app", host=args.host, port=args.port, reload=args.reload)

    elif args.command == "ingest":
        config = AKWConfig(db_path=args.db)
        kb = KnowledgeBase(config=config)
        target = Path(args.path)
        if target.is_dir():
            print(f"Indexing directory: {target}...")
            docs = kb.add_directory(target)
            print(f"Successfully ingested {len(docs)} documents.")
        elif target.is_file():
            print(f"Indexing file: {target}...")
            doc = kb.add_document(target)
            print(f"Ingested '{doc.filename}' ({doc.total_chunks} chunks).")
        else:
            print(f"Path does not exist: {target}", file=sys.stderr)
            sys.exit(1)

    elif args.command == "search":
        config = AKWConfig(db_path=args.db)
        kb = KnowledgeBase(config=config)
        print(f"Searching: '{args.query}' (top_k={args.top_k}, window=±{args.window})...\n")
        blocks, citations = kb.search(args.query, top_k=args.top_k, expand_window=args.window)

        if not blocks:
            print("No matching knowledge found.")
            return

        for block in blocks:
            print(f"[{block.citation_id}] {block.document_name} | Score: {block.relevance_score:.3f}")
            print(f"  Breadcrumb: {block.breadcrumb}")
            print(f"  Contiguous Chunks Window ({len(block.chunks)} chunks):")
            print("  " + "-" * 60)
            preview = block.merged_text[:400] + ("..." if len(block.merged_text) > 400 else "")
            for line in preview.splitlines():
                print(f"  {line}")
            print("  " + "-" * 60 + "\n")

    elif args.command == "examples":
        from akw.examples.manager import ExampleManager
        mgr = ExampleManager()

        if args.examples_action == "list":
            examples = mgr.list_available_examples()
            print(f"\nAvailable Example Knowledge Bases ({len(examples)}):")
            print("=" * 65)
            for ex in examples:
                print(f"ID:          {ex.id}")
                print(f"Name:        {ex.name}")
                print(f"Description: {ex.description}")
                print(f"Tags:        {', '.join(ex.tags)}")
                print(f"Documents:   {', '.join(ex.documents)}")
                print(f"Diagrams:    {'Yes' if ex.has_diagrams else 'No'}")
                print("Sample Queries:")
                for q in ex.sample_queries:
                    print(f"  • {q}")
                print("-" * 65)

        elif args.examples_action == "load":
            if args.example:
                print(f"Loading example workspace '{args.example}' (reset={args.reset})...")
                ws = mgr.load_example(args.example, reset=args.reset)
                print(f"✓ Loaded workspace: {ws.name} ({ws.document_count} documents, {ws.total_chunks} chunks).")
            else:
                print(f"Loading all example knowledge bases (reset={args.reset})...")
                workspaces = mgr.load_all_examples(reset=args.reset)
                print(f"✓ Loaded {len(workspaces)} example workspaces:")
                for ws in workspaces:
                    marker = " [ACTIVE]" if ws.is_active else ""
                    print(f"  - {ws.name} ({ws.document_count} docs, {ws.total_chunks} chunks){marker}")

    elif args.command == "reset":
        from akw.examples.manager import ExampleManager
        mgr = ExampleManager()
        if not args.force:
            confirm = input("Are you sure you want to wipe all workspaces, databases, and assets? (y/N): ")
            if confirm.lower() != "y":
                print("Aborted.")
                return

        print("Resetting all workspaces and hydrating fresh example knowledge bases...")
        workspaces = mgr.reset_all()
        print(f"✓ Reset complete. {len(workspaces)} example workspaces initialized.")


if __name__ == "__main__":
    main()
