"""Business logic for KOL and booking price management."""

from __future__ import annotations

from typing import Any

import pandas as pd


PLATFORM_VIEW_COLUMNS = {
    "Facebook": "avg_facebook_views",
    "YouTube": "avg_youtube_views",
    "TikTok": "avg_tiktok_views",
}


def join_kol_and_prices(kol_df: pd.DataFrame, price_df: pd.DataFrame) -> pd.DataFrame:
    """Join KOL profile and price data on kol_id."""

    renamed_kol = kol_df.rename(columns={"description": "description_kol"})
    renamed_price = price_df.rename(columns={"description": "description_price"})
    joined = renamed_kol.merge(renamed_price, on="kol_id", how="left")
    joined["price"] = pd.to_numeric(joined["price"], errors="coerce")
    joined["avg_views"] = joined.apply(_resolve_avg_views, axis=1)
    return joined


def _resolve_avg_views(row: pd.Series) -> float:
    column = PLATFORM_VIEW_COLUMNS.get(row.get("main_platform", ""), "")
    if column:
        return float(row.get(column, 0) or 0)
    return 0.0


def _truncate_text(value: str, limit: int = 40) -> str:
    text = str(value or "").strip()
    if len(text) <= limit:
        return text
    return f"{text[:limit - 3]}..."


def summarize_kol_catalog(joined: pd.DataFrame) -> pd.DataFrame:
    """Return one summary row per booking item from the current joined dataset."""

    if joined.empty:
        return pd.DataFrame(
            columns=[
                "price_id",
                "kol_id",
                "uid",
                "name",
                "main_platform",
                "booking_platform",
                "avg_views",
                "service_type",
                "price",
                "total_cost",
                "content_topics",
                "description",
            ]
        )

    working_df = joined.copy()
    working_df["price"] = pd.to_numeric(working_df["price"], errors="coerce").fillna(0)
    total_cost_by_kol = working_df.groupby("kol_id", dropna=False)["price"].sum().to_dict()

    records = []
    for _, row in working_df.iterrows():
        if pd.isna(row.get("price_id")) or str(row.get("price_id", "")).strip() == "":
            continue
        price_value = float(row.get("price", 0) or 0)
        kol_total_cost = float(total_cost_by_kol.get(row["kol_id"], 0) or 0)
        records.append(
            {
                "price_id": str(row["price_id"]),
                "kol_id": row["kol_id"],
                "uid": row.get("uid", ""),
                "name": row["name"],
                "main_platform": row["main_platform"],
                "booking_platform": row.get("platform", ""),
                "avg_views": float(row.get("avg_views", 0) or 0),
                "service_type": row.get("service_type", ""),
                "price": price_value,
                "total_cost": kol_total_cost,
                "content_topics": _truncate_text(row.get("content_topics", ""), 28),
                "description": _truncate_text(row.get("description_kol", ""), 36),
            }
        )

    return pd.DataFrame(records).sort_values(by=["name", "kol_id", "price_id"]).reset_index(drop=True)


def get_kol_options(kol_df: pd.DataFrame) -> list[tuple[str, str]]:
    """Return KOL selector tuples as (kol_id, label)."""

    return [
        (row["kol_id"], f"{row['name']} ({row['kol_id']})")
        for _, row in kol_df.sort_values("name").iterrows()
    ]


def get_kol_detail(kol_id: str, kol_df: pd.DataFrame, price_df: pd.DataFrame) -> dict[str, Any] | None:
    """Return a KOL record and its price list."""

    matched = kol_df[kol_df["kol_id"] == kol_id]
    if matched.empty:
        return None

    kol_record = matched.iloc[0].to_dict()
    prices = price_df[price_df["kol_id"] == kol_id].sort_values(by=["platform", "service_type", "price_id"])
    total_cost = float(pd.to_numeric(prices["price"], errors="coerce").fillna(0).sum())
    avg_views = float(_resolve_avg_views(matched.iloc[0]))
    return {"kol": kol_record, "prices": prices, "total_cost": total_cost, "avg_views": avg_views}


def upsert_kol(kol_df: pd.DataFrame, kol_payload: dict[str, Any]) -> pd.DataFrame:
    """Insert or update a KOL profile record."""

    updated = kol_df.copy()
    kol_id = str(kol_payload["kol_id"]).strip()
    payload = {key: kol_payload.get(key, "") for key in updated.columns}
    payload["kol_id"] = kol_id

    if (updated["kol_id"] == kol_id).any():
        updated.loc[updated["kol_id"] == kol_id, updated.columns] = [[payload[column] for column in updated.columns]]
        return updated.reset_index(drop=True)

    return pd.concat([updated, pd.DataFrame([payload])], ignore_index=True)


def delete_kol(kol_df: pd.DataFrame, price_df: pd.DataFrame, kol_id: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Delete a KOL and all its related price records."""

    remaining_kol = kol_df[kol_df["kol_id"] != kol_id].reset_index(drop=True)
    remaining_prices = price_df[price_df["kol_id"] != kol_id].reset_index(drop=True)
    return remaining_kol, remaining_prices


def upsert_price(price_df: pd.DataFrame, price_payload: dict[str, Any]) -> pd.DataFrame:
    """Insert or update a booking price row."""

    updated = price_df.copy()
    price_id = str(price_payload["price_id"]).strip()
    payload = {key: price_payload.get(key, "") for key in updated.columns}
    payload["price_id"] = price_id
    payload["price"] = float(payload["price"])

    if (updated["price_id"] == price_id).any():
        updated.loc[updated["price_id"] == price_id, updated.columns] = [[payload[column] for column in updated.columns]]
        return updated.reset_index(drop=True)

    return pd.concat([updated, pd.DataFrame([payload])], ignore_index=True)


def delete_price(price_df: pd.DataFrame, price_id: str) -> pd.DataFrame:
    """Delete a booking price row."""

    return price_df[price_df["price_id"] != price_id].reset_index(drop=True)
