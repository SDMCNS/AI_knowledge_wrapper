"""Spreadsheet Parser for Excel (.xlsx, .xls) and CSV files using openpyxl & pandas."""

from __future__ import annotations

import io
from pathlib import Path
from typing import BinaryIO, List, Union

import openpyxl
import pandas as pd

from akw.chunking.breadcrumb import BreadcrumbTracker
from akw.core.exceptions import DocumentParseError
from akw.core.models import BlockType, ParsedBlock
from akw.parsers.base import BaseParser


class ExcelParser(BaseParser):
    """Parses Excel and CSV workbooks, serializing rows with column header persistence."""

    def __init__(self, rows_per_block: int = 40):
        self.rows_per_block = rows_per_block

    def parse(self, file_source: Union[str, Path, BinaryIO, bytes], filename: str) -> List[ParsedBlock]:
        blocks: List[ParsedBlock] = []
        tracker = BreadcrumbTracker(document_title=filename)

        is_csv = filename.lower().endswith(".csv")

        try:
            if is_csv:
                if isinstance(file_source, bytes):
                    df = pd.read_csv(io.BytesIO(file_source))
                elif isinstance(file_source, (str, Path)):
                    df = pd.read_csv(file_source)
                else:
                    df = pd.read_csv(file_source)
                sheets = {"Data": df}
            else:
                if isinstance(file_source, bytes):
                    excel_file = pd.ExcelFile(io.BytesIO(file_source))
                elif isinstance(file_source, (str, Path)):
                    excel_file = pd.ExcelFile(str(file_source))
                else:
                    data = file_source.read()
                    excel_file = pd.ExcelFile(io.BytesIO(data))
                sheets = {name: excel_file.parse(name) for name in excel_file.sheet_names}
        except Exception as e:
            raise DocumentParseError(f"Failed to load spreadsheet '{filename}': {e}") from e

        try:
            for sheet_name, df in sheets.items():
                if df.empty:
                    continue

                tracker.set_sheet(sheet_name)
                # Clean dataframe: fill NaNs, format columns
                df = df.fillna("")
                columns = [str(col).strip() for col in df.columns]

                total_rows = len(df)
                for start_idx in range(0, total_rows, self.rows_per_block):
                    end_idx = min(start_idx + self.rows_per_block, total_rows)
                    chunk_df = df.iloc[start_idx:end_idx]

                    # Build Markdown table
                    header_line = "| " + " | ".join(columns) + " |"
                    separator = "| " + " | ".join(["---"] * len(columns)) + " |"
                    row_lines = [header_line, separator]

                    for _, row in chunk_df.iterrows():
                        row_vals = [str(val).replace("\n", " ").strip() for val in row]
                        row_lines.append("| " + " | ".join(row_vals) + " |")

                    table_text = f"### Sheet: {sheet_name} (Rows {start_idx + 1} to {end_idx} of {total_rows})\n" + "\n".join(row_lines)

                    blocks.append(
                        ParsedBlock(
                            content=table_text,
                            breadcrumb=tracker.get_path(),
                            sheet_name=sheet_name,
                            block_type=BlockType.TABLE,
                            metadata={"start_row": start_idx + 1, "end_row": end_idx, "total_rows": total_rows}
                        )
                    )
        except Exception as e:
            raise DocumentParseError(f"Error parsing spreadsheet '{filename}': {e}") from e

        return blocks
