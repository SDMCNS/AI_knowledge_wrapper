#!/usr/bin/env python3
"""Standalone utility script to list, load, and reset example knowledge bases."""

import argparse
import sys
from pathlib import Path

# Ensure src is on python path
root = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(root / "src"))

from akw.examples.manager import ExampleManager


def main():
    parser = argparse.ArgumentParser(
        description="Load or reset example knowledge bases (Project Apollo & BioNexus Diagnostics)"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all available example knowledge base datasets",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Wipe existing workspaces and reload fresh example datasets",
    )
    parser.add_argument(
        "--example",
        type=str,
        default=None,
        help="Specific example to load (e.g. project_apollo or bionexus_diagnostics)",
    )

    args = parser.parse_args()
    mgr = ExampleManager()

    if args.list:
        examples = mgr.list_available_examples()
        print("\nAvailable Example Knowledge Bases:")
        print("=" * 60)
        for ex in examples:
            print(f"ID:          {ex.id}")
            print(f"Name:        {ex.name}")
            print(f"Description: {ex.description}")
            print(f"Tags:        {', '.join(ex.tags)}")
            print(f"Documents:   {', '.join(ex.documents)}")
            print(f"Diagrams:    {'Yes' if ex.has_diagrams else 'No'}")
            print(f"Sample Queries:")
            for q in ex.sample_queries:
                print(f"  - {q}")
            print("-" * 60)
        return

    if args.reset:
        print("Resetting all workspaces and hydrating fresh example knowledge bases...")
        workspaces = mgr.reset_all()
        print(f"\nSuccessfully reset and loaded {len(workspaces)} example workspaces:")
        for ws in workspaces:
            active_marker = " (ACTIVE)" if ws.is_active else ""
            print(f"- {ws.name} [{ws.id}]{active_marker}: {ws.document_count} docs, {ws.total_chunks} chunks")
        return

    if args.example:
        print(f"Loading example workspace: {args.example}...")
        ws = mgr.load_example(args.example, reset=args.reset)
        print(f"Loaded workspace: {ws.name} ({ws.document_count} docs, {ws.total_chunks} chunks)")
        return

    # Default: load all examples
    print("Loading all example knowledge bases into workspaces...")
    workspaces = mgr.load_all_examples(reset=args.reset)
    print(f"\nSuccessfully loaded {len(workspaces)} example workspaces:")
    for ws in workspaces:
        active_marker = " (ACTIVE)" if ws.is_active else ""
        print(f"- {ws.name} [{ws.id}]{active_marker}: {ws.document_count} docs, {ws.total_chunks} chunks")


if __name__ == "__main__":
    main()

