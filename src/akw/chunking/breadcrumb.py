"""Hierarchical Breadcrumb Tracker for document structural context."""

from __future__ import annotations

from typing import List, Optional


class BreadcrumbTracker:
    """Maintains a stack of headings representing current document context."""

    def __init__(self, document_title: str):
        self.document_title = document_title.strip()
        # Stack entries are tuples of (level: int, title: str)
        # Level 0 is document title
        self._stack: List[tuple[int, str]] = [(0, self.document_title)]

    def update_heading(self, level: int, title: str) -> None:
        """Update the hierarchy when a new heading is encountered."""
        clean_title = title.strip()
        if not clean_title:
            return

        # Ensure level is at least 1
        level = max(1, level)

        # Pop any headings with level >= current heading level
        while len(self._stack) > 1 and self._stack[-1][0] >= level:
            self._stack.pop()

        self._stack.append((level, clean_title))

    def set_sheet(self, sheet_name: str) -> None:
        """Convenience helper for spreadsheet sheets."""
        # Keep document title, replace anything else with sheet name
        self._stack = [(0, self.document_title), (1, f"Sheet: {sheet_name.strip()}")]

    def get_path(self) -> List[str]:
        """Return the current hierarchical path as a list of strings."""
        return [entry[1] for entry in self._stack]

    def get_display(self, separator: str = " > ") -> str:
        """Return the formatted breadcrumb display string."""
        return separator.join(self.get_path())

    def snapshot(self) -> str:
        """Get the current display string."""
        return self.get_display()

