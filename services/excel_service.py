"""Excel file operations for the KOL booking demo."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import BinaryIO, Dict

import pandas as pd

from utils.validators import (
    KOL_SHEET_NAME,
    PRICE_SHEET_NAME,
    WorkbookValidationError,
    validate_workbook_frames,
)


def read_excel_data(file_source: str | Path | BinaryIO) -> Dict[str, pd.DataFrame]:
    """Read and validate workbook data from file path or uploaded file."""

    try:
        workbook = pd.read_excel(file_source, sheet_name=None, engine="openpyxl")
    except ValueError as exc:
        raise WorkbookValidationError(f"Không thể đọc file Excel: {exc}") from exc
    except FileNotFoundError as exc:
        raise WorkbookValidationError(f"Không tìm thấy file mẫu: {exc}") from exc
    except Exception as exc:
        raise WorkbookValidationError(f"Lỗi khi mở file Excel: {exc}") from exc

    return validate_workbook_frames(workbook)


def export_workbook_bytes(kol_df: pd.DataFrame, price_df: pd.DataFrame) -> bytes:
    """Export edited dataframes to an Excel workbook in memory."""

    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        kol_df.to_excel(writer, sheet_name=KOL_SHEET_NAME, index=False)
        price_df.to_excel(writer, sheet_name=PRICE_SHEET_NAME, index=False)
    output.seek(0)
    return output.read()


def export_filtered_joined_bytes(filtered_df: pd.DataFrame) -> bytes:
    """Export filtered joined data to an Excel workbook in memory."""

    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        filtered_df.to_excel(writer, sheet_name="Filtered_KOL_Booking", index=False)
    output.seek(0)
    return output.read()
