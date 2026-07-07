"""Validation utilities for KOL booking workbooks."""

from __future__ import annotations

from typing import Dict

import pandas as pd


KOL_SHEET_NAME = "KOL_Profile"
PRICE_SHEET_NAME = "Booking_Prices"

KOL_REQUIRED_COLUMNS = [
    "kol_id",
    "name",
    "facebook_link",
    "youtube_link",
    "tiktok_link",
    "avg_facebook_views",
    "avg_youtube_views",
    "avg_tiktok_views",
    "description",
    "content_topics",
    "main_platform",
    "note",
]

KOL_OPTIONAL_COLUMNS = [
    "uid",
    "shirt_size",
    "pants_size",
    "shoe_size",
    "address",
]

KOL_EXPORT_COLUMNS = [
    "kol_id",
    "uid",
    "name",
    "facebook_link",
    "youtube_link",
    "tiktok_link",
    "avg_facebook_views",
    "avg_youtube_views",
    "avg_tiktok_views",
    "description",
    "content_topics",
    "main_platform",
    "shirt_size",
    "pants_size",
    "shoe_size",
    "address",
    "note",
]

PRICE_REQUIRED_COLUMNS = [
    "price_id",
    "kol_id",
    "service_type",
    "platform",
    "price",
    "description",
    "note",
]

NUMERIC_COLUMNS = [
    "avg_facebook_views",
    "avg_youtube_views",
    "avg_tiktok_views",
]


class WorkbookValidationError(ValueError):
    """Raised when workbook structure or data is invalid."""


def _normalize_text_columns(frame: pd.DataFrame) -> pd.DataFrame:
    normalized = frame.copy()
    for column in normalized.columns:
        if normalized[column].dtype == "object":
            normalized[column] = normalized[column].fillna("").astype(str).str.strip()
    return normalized


def _ensure_columns(frame: pd.DataFrame, required_columns: list[str], sheet_name: str) -> None:
    missing = [column for column in required_columns if column not in frame.columns]
    if missing:
        missing_display = ", ".join(missing)
        raise WorkbookValidationError(
            f"Sheet '{sheet_name}' thiếu cột bắt buộc: {missing_display}."
        )


def _add_optional_columns(frame: pd.DataFrame, optional_columns: list[str]) -> pd.DataFrame:
    result = frame.copy()
    if "clothing_size" in result.columns:
        if "shirt_size" not in result.columns:
            result["shirt_size"] = result["clothing_size"]
        if "pants_size" not in result.columns:
            result["pants_size"] = ""
        if "shoe_size" not in result.columns:
            result["shoe_size"] = ""
    for column in optional_columns:
        if column not in result.columns:
            result[column] = ""
    return result


def _coerce_numeric_columns(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    result = frame.copy()
    for column in columns:
        result[column] = pd.to_numeric(result[column], errors="coerce").fillna(0)
    return result


def _coerce_price_column(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    result["price"] = pd.to_numeric(result["price"], errors="coerce")
    invalid_rows = result[result["price"].isna()]
    if not invalid_rows.empty:
        sample_ids = ", ".join(invalid_rows["price_id"].astype(str).head(3).tolist())
        raise WorkbookValidationError(
            "Cột 'price' phải là số hợp lệ trong sheet "
            f"'{PRICE_SHEET_NAME}'. Bản ghi lỗi: {sample_ids}."
        )
    return result


def validate_workbook_frames(sheets: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
    """Validate workbook sheets and return normalized dataframes."""

    for required_sheet in (KOL_SHEET_NAME, PRICE_SHEET_NAME):
        if required_sheet not in sheets:
            raise WorkbookValidationError(
                f"Thiếu sheet bắt buộc '{required_sheet}' trong file Excel."
            )

    kol_df = _normalize_text_columns(sheets[KOL_SHEET_NAME])
    price_df = _normalize_text_columns(sheets[PRICE_SHEET_NAME])

    _ensure_columns(kol_df, KOL_REQUIRED_COLUMNS, KOL_SHEET_NAME)
    _ensure_columns(price_df, PRICE_REQUIRED_COLUMNS, PRICE_SHEET_NAME)

    kol_df = _add_optional_columns(kol_df, KOL_OPTIONAL_COLUMNS)
    kol_df = kol_df[KOL_EXPORT_COLUMNS].copy()
    price_df = price_df[PRICE_REQUIRED_COLUMNS].copy()

    kol_df = _coerce_numeric_columns(kol_df, NUMERIC_COLUMNS)
    price_df = _coerce_price_column(price_df)

    if kol_df["kol_id"].eq("").any():
        raise WorkbookValidationError("Sheet 'KOL_Profile' có dòng thiếu 'kol_id'.")

    if price_df["price_id"].eq("").any() or price_df["kol_id"].eq("").any():
        raise WorkbookValidationError(
            "Sheet 'Booking_Prices' có dòng thiếu 'price_id' hoặc 'kol_id'."
        )

    return {
        KOL_SHEET_NAME: kol_df,
        PRICE_SHEET_NAME: price_df,
    }
