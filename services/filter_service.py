"""Filtering logic for the KOL booking demo."""

from __future__ import annotations

import pandas as pd


def apply_filters(
    joined_df: pd.DataFrame,
    name_query: str = "",
    keyword_query: str = "",
    platforms: list[str] | None = None,
    service_types: list[str] | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
) -> pd.DataFrame:
    """Filter joined KOL-booking data based on user inputs."""

    filtered = joined_df.copy()
    platforms = platforms or []
    service_types = service_types or []

    if name_query:
        filtered = filtered[
            filtered["name"].fillna("").str.contains(name_query, case=False, na=False)
        ]

    if keyword_query:
        combined = filtered["description_kol"].fillna("") + " " + filtered["content_topics"].fillna("")
        filtered = filtered[combined.str.contains(keyword_query, case=False, na=False)]

    if platforms:
        filtered = filtered[filtered["platform"].isin(platforms)]

    if service_types:
        filtered = filtered[filtered["service_type"].isin(service_types)]

    if min_price is not None:
        filtered = filtered[filtered["price"] >= min_price]

    if max_price is not None:
        filtered = filtered[filtered["price"] <= max_price]

    return filtered.reset_index(drop=True)
