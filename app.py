"""Streamlit demo app for KOL booking management."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from services.excel_service import (
    export_filtered_joined_bytes,
    export_workbook_bytes,
    read_excel_data,
)
from services.filter_service import apply_filters
from services.kol_service import (
    delete_kol,
    delete_price,
    get_kol_detail,
    get_kol_options,
    join_kol_and_prices,
    summarize_kol_catalog,
    upsert_kol,
    upsert_price,
)
from utils.validators import WorkbookValidationError


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_FILE = BASE_DIR / "data" / "kol_booking_template.xlsx"
SERVICE_TYPES = [
    "Đi quay",
    "Làm clip",
    "Livestream",
    "Làm giải đấu",
    "Post bài",
    "Short video",
    "Combo",
]
PLATFORMS = ["Facebook", "YouTube", "TikTok"]


TABLE_COLUMNS = [
    ("Chọn", 0.5),
    ("Tên KOL", 1.4),
    ("Nền tảng booking", 1.2),
    ("AVG View", 0.8),
    ("Dịch vụ", 1.1),
    ("Giá", 0.8),
    ("Tổng chi phí", 1.0),
    ("Chủ đề", 1.3),
    ("Mô tả", 1.4),
    ("Chi tiết", 0.7),
]


def initialize_state() -> None:
    if "kol_df" not in st.session_state or "price_df" not in st.session_state:
        workbook = read_excel_data(DEFAULT_FILE)
        st.session_state.kol_df = workbook["KOL_Profile"]
        st.session_state.price_df = workbook["Booking_Prices"]
        st.session_state.source_name = DEFAULT_FILE.name

    st.session_state.setdefault("selection_result", pd.DataFrame())


def load_uploaded_file(uploaded_file) -> None:
    workbook = read_excel_data(uploaded_file)
    st.session_state.kol_df = workbook["KOL_Profile"]
    st.session_state.price_df = workbook["Booking_Prices"]
    st.session_state.source_name = uploaded_file.name
    st.session_state.selection_result = pd.DataFrame()


def normalize_number(value: float | int) -> int:
    return int(float(value or 0))


def safe_index(options: list[str], current_value: str, default: int = 0) -> int:
    return options.index(current_value) if current_value in options else default


def render_platform_link(label: str, url: str) -> str:
    if not url:
        return f"**{label}:** -"
    return f"**{label}:** [{url}]({url})"


def render_sidebar() -> pd.DataFrame:
    st.sidebar.header("Nguồn dữ liệu")
    uploaded_file = st.sidebar.file_uploader(
        "Upload file Excel",
        type=["xlsx"],
        help="Nếu không upload, app dùng file mẫu trong thư mục data.",
    )

    if uploaded_file is not None:
        try:
            load_uploaded_file(uploaded_file)
            st.sidebar.success(f"Đã nạp file: {uploaded_file.name}")
        except WorkbookValidationError as exc:
            st.sidebar.error(str(exc))

    joined_df = join_kol_and_prices(st.session_state.kol_df, st.session_state.price_df)
    st.sidebar.caption(f"File hiện tại: {st.session_state.get('source_name', DEFAULT_FILE.name)}")

    st.sidebar.header("Bộ lọc")
    name_query = st.sidebar.text_input("Tên KOL")
    keyword_query = st.sidebar.text_input("Mô tả hoặc chủ đề")
    selected_platforms = st.sidebar.multiselect("Nền tảng", PLATFORMS)
    selected_services = st.sidebar.multiselect("Service type", SERVICE_TYPES)

    numeric_prices = pd.to_numeric(joined_df["price"], errors="coerce").dropna()
    min_default = float(numeric_prices.min()) if not numeric_prices.empty else 0.0
    max_default = float(numeric_prices.max()) if not numeric_prices.empty else 0.0

    min_price, max_price = st.sidebar.slider(
        "Khoảng giá",
        min_value=min_default,
        max_value=max_default if max_default >= min_default else min_default,
        value=(min_default, max_default if max_default >= min_default else min_default),
        step=50000.0 if max_default > 0 else 1.0,
    )

    filtered_df = apply_filters(
        joined_df=joined_df,
        name_query=name_query,
        keyword_query=keyword_query,
        platforms=selected_platforms,
        service_types=selected_services,
        min_price=min_price,
        max_price=max_price,
    )

    st.sidebar.download_button(
        "Export dữ liệu đã lọc",
        data=export_filtered_joined_bytes(filtered_df),
        file_name="filtered_kol_booking.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    st.sidebar.download_button(
        "Download Excel đã chỉnh sửa",
        data=export_workbook_bytes(st.session_state.kol_df, st.session_state.price_df),
        file_name="kol_booking_edited.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    return filtered_df


def render_detail_popover(kol_id: str) -> None:
    detail = get_kol_detail(kol_id, st.session_state.kol_df, st.session_state.price_df)
    if detail is None:
        st.write("Không tìm thấy thông tin KOL.")
        return

    kol = detail["kol"]
    prices = detail["prices"]

    st.markdown(f"**{kol['name']} ({kol['kol_id']})**")
    st.caption(f"UID: {kol.get('uid', '') or '-'}")
    st.metric("Tổng chi phí", f"{detail['total_cost']:,.0f}")
    st.metric("AVG View trung bình", f"{normalize_number(detail['avg_views']):,}")
    st.markdown(render_platform_link("Facebook", kol["facebook_link"]))
    st.markdown(render_platform_link("YouTube", kol["youtube_link"]))
    st.markdown(render_platform_link("TikTok", kol["tiktok_link"]))
    st.markdown(f"**Size áo:** {kol.get('shirt_size', '') or '-'}")
    st.markdown(f"**Size quần:** {kol.get('pants_size', '') or '-'}")
    st.markdown(f"**Size giày:** {kol.get('shoe_size', '') or '-'}")
    st.markdown(f"**Địa chỉ KOL:** {kol.get('address', '') or '-'}")
    st.markdown(f"**Mô tả:** {kol['description'] or '-'}")
    st.markdown(f"**Chủ đề nội dung:** {kol['content_topics'] or '-'}")
    st.markdown(f"**Ghi chú:** {kol['note'] or '-'}")
    st.markdown("**Bảng giá dịch vụ**")
    st.dataframe(prices, use_container_width=True, hide_index=True)


def render_table_header() -> None:
    header_cols = st.columns([width for _, width in TABLE_COLUMNS])
    for column, (label, _) in zip(header_cols, TABLE_COLUMNS):
        column.markdown(f"**{label}**")


def render_kol_selector(filtered_df: pd.DataFrame) -> None:
    st.subheader("Danh sách KOL")
    catalog_df = summarize_kol_catalog(filtered_df).reset_index(drop=True)

    if catalog_df.empty:
        st.info("Không có KOL phù hợp với bộ lọc hiện tại.")
        st.session_state.selection_result = pd.DataFrame()
        return

    render_table_header()
    previous_kol_id = None
    for _, row in catalog_df.iterrows():
        cols = st.columns([width for _, width in TABLE_COLUMNS])
        row_key = row["price_id"]
        show_total_cost = row["kol_id"] != previous_kol_id
        with cols[0]:
            st.checkbox(
                "Chọn",
                key=f"select_{row_key}",
                label_visibility="collapsed",
            )
        cols[1].write(row["name"])
        cols[2].write(row["booking_platform"])
        cols[3].write(f"{normalize_number(row['avg_views']):,}")
        cols[4].write(row["service_type"])
        cols[5].write(f"{float(row['price']):,.0f}")
        cols[6].write(f"{float(row['total_cost']):,.0f}" if show_total_cost else "")
        cols[7].write(row["content_topics"])
        cols[8].write(row["description"])
        with cols[9]:
            with st.popover("Chi tiết"):
                render_detail_popover(row["kol_id"])
        previous_kol_id = row["kol_id"]

    if st.button("Submit danh sách KOL đã chọn"):
        selected_ids = [
            row["price_id"]
            for _, row in catalog_df.iterrows()
            if st.session_state.get(f"select_{row['price_id']}", False)
        ]
        selected_df = catalog_df[catalog_df["price_id"].isin(selected_ids)].copy()
        if not selected_df.empty:
            selected_total_by_kol = (
                selected_df.groupby("kol_id", dropna=False)["price"]
                .sum()
                .to_dict()
            )
            selected_df["total_cost"] = selected_df["kol_id"].map(selected_total_by_kol).fillna(0)
        selected_df = selected_df.rename(
            columns={
                "price_id": "Price ID",
                "kol_id": "KOL ID",
                "uid": "UID",
                "name": "Tên KOL",
                "booking_platform": "Nền tảng booking",
                "avg_views": "AVG View",
                "service_type": "Dịch vụ",
                "price": "Giá",
                "total_cost": "Tổng chi phí",
                "content_topics": "Chủ đề",
                "description": "Mô tả",
            }
        )
        st.session_state.selection_result = selected_df.reset_index(drop=True)
        if selected_df.empty:
            st.warning("Bạn chưa chọn KOL nào.")
        else:
            st.success(f"Đã chọn {len(selected_df)} dòng booking.")


def render_selection_summary() -> None:
    st.subheader("Danh sách cuối cùng được chọn")
    selected_df = st.session_state.get("selection_result", pd.DataFrame())
    if selected_df is None or selected_df.empty:
        st.info("Chưa có dòng booking nào được submit.")
        return

    total_all = float(pd.to_numeric(selected_df["Giá"], errors="coerce").fillna(0).sum())
    metric_col1, metric_col2 = st.columns(2)
    with metric_col1:
        st.metric("Số dòng booking đã chọn", len(selected_df))
    with metric_col2:
        st.metric("Tổng tiền tất cả dòng đã chọn", f"{total_all:,.0f}")

    display_df = selected_df.copy()
    previous_kol_id = None
    total_cost_display = []
    for _, row in display_df.iterrows():
        if row["KOL ID"] != previous_kol_id:
            total_cost_display.append(row["Tổng chi phí"])
        else:
            total_cost_display.append("")
        previous_kol_id = row["KOL ID"]

    display_df["Tổng chi phí hiển thị"] = total_cost_display
    display_df = display_df[
        [
            "KOL ID",
            "UID",
            "Tên KOL",
            "Nền tảng booking",
            "AVG View",
            "Dịch vụ",
            "Giá",
            "Tổng chi phí hiển thị",
            "Chủ đề",
            "Mô tả",
        ]
    ].rename(columns={"Tổng chi phí hiển thị": "Tổng chi phí"})
    st.dataframe(display_df, use_container_width=True, hide_index=True)


def render_kol_form() -> None:
    st.subheader("Quản lý KOL")
    mode = st.radio("Thao tác KOL", ["Thêm mới", "Sửa", "Xóa"], horizontal=True)

    existing_labels = {label: kol_id for kol_id, label in get_kol_options(st.session_state.kol_df)}
    selected_kol = None
    selected_record = None

    if mode in {"Sửa", "Xóa"}:
        if not existing_labels:
            st.info("Chưa có KOL để thao tác.")
            return
        selected_label = st.selectbox("Chọn KOL cần thao tác", list(existing_labels.keys()))
        selected_kol = existing_labels[selected_label]
        detail = get_kol_detail(selected_kol, st.session_state.kol_df, st.session_state.price_df)
        selected_record = detail["kol"] if detail else None

    with st.form("kol_form", clear_on_submit=(mode == "Thêm mới")):
        col1, col2 = st.columns(2)
        with col1:
            kol_id = st.text_input(
                "KOL ID",
                value="" if mode == "Thêm mới" else selected_record["kol_id"],
                disabled=mode == "Sửa",
            )
            uid = st.text_input("UID ingame", value="" if not selected_record else selected_record.get("uid", ""))
            name = st.text_input("Tên KOL", value="" if not selected_record else selected_record["name"])
            main_platform = st.selectbox(
                "Nền tảng chính",
                options=PLATFORMS,
                index=0 if not selected_record else safe_index(PLATFORMS, selected_record["main_platform"]),
            )
            shirt_size = st.text_input(
                "Size áo",
                value="" if not selected_record else selected_record.get("shirt_size", ""),
            )
            pants_size = st.text_input(
                "Size quần",
                value="" if not selected_record else selected_record.get("pants_size", ""),
            )
            shoe_size = st.text_input(
                "Size giày",
                value="" if not selected_record else selected_record.get("shoe_size", ""),
            )
            address = st.text_input(
                "Địa chỉ KOL",
                value="" if not selected_record else selected_record.get("address", ""),
            )
        with col2:
            facebook_link = st.text_input("Facebook link", value="" if not selected_record else selected_record["facebook_link"])
            youtube_link = st.text_input("YouTube link", value="" if not selected_record else selected_record["youtube_link"])
            tiktok_link = st.text_input("TikTok link", value="" if not selected_record else selected_record["tiktok_link"])
            description = st.text_area("Mô tả", value="" if not selected_record else selected_record["description"])
            content_topics = st.text_area(
                "Chủ đề nội dung",
                value="" if not selected_record else selected_record["content_topics"],
            )
            note = st.text_area("Ghi chú", value="" if not selected_record else selected_record["note"])

        view_col1, view_col2, view_col3 = st.columns(3)
        with view_col1:
            avg_facebook_views = st.number_input(
                "Avg Facebook views",
                min_value=0,
                value=0 if not selected_record else normalize_number(selected_record["avg_facebook_views"]),
                step=1000,
            )
        with view_col2:
            avg_youtube_views = st.number_input(
                "Avg YouTube views",
                min_value=0,
                value=0 if not selected_record else normalize_number(selected_record["avg_youtube_views"]),
                step=1000,
            )
        with view_col3:
            avg_tiktok_views = st.number_input(
                "Avg TikTok views",
                min_value=0,
                value=0 if not selected_record else normalize_number(selected_record["avg_tiktok_views"]),
                step=1000,
            )
        submit = st.form_submit_button(mode)

    if not submit:
        return

    if mode == "Xóa":
        st.session_state.kol_df, st.session_state.price_df = delete_kol(
            st.session_state.kol_df,
            st.session_state.price_df,
            selected_kol,
        )
        st.session_state.selection_result = pd.DataFrame()
        st.success("Đã xóa KOL và toàn bộ giá booking liên quan.")
        st.rerun()

    if not kol_id.strip() or not name.strip():
        st.error("KOL ID và tên KOL là bắt buộc.")
        return

    if mode == "Thêm mới" and st.session_state.kol_df["kol_id"].eq(kol_id.strip()).any():
        st.error("KOL ID đã tồn tại.")
        return

    payload = {
        "kol_id": kol_id.strip(),
        "uid": uid.strip(),
        "name": name.strip(),
        "facebook_link": facebook_link.strip(),
        "youtube_link": youtube_link.strip(),
        "tiktok_link": tiktok_link.strip(),
        "avg_facebook_views": avg_facebook_views,
        "avg_youtube_views": avg_youtube_views,
        "avg_tiktok_views": avg_tiktok_views,
        "description": description.strip(),
        "content_topics": content_topics.strip(),
        "main_platform": main_platform,
        "shirt_size": shirt_size.strip(),
        "pants_size": pants_size.strip(),
        "shoe_size": shoe_size.strip(),
        "address": address.strip(),
        "note": note.strip(),
    }
    st.session_state.kol_df = upsert_kol(st.session_state.kol_df, payload)
    st.success(f"Đã {mode.lower()} thông tin KOL.")
    st.rerun()


def render_price_form() -> None:
    st.subheader("Quản lý giá booking")
    mode = st.radio("Thao tác giá booking", ["Thêm mới", "Sửa", "Xóa"], horizontal=True)

    kol_labels = {label: kol_id for kol_id, label in get_kol_options(st.session_state.kol_df)}
    if not kol_labels:
        st.info("Cần có KOL trước khi thêm giá booking.")
        return

    price_df = st.session_state.price_df
    price_options = {
        f"{row['price_id']} | {row['kol_id']} | {row['platform']} | {row['service_type']}": row["price_id"]
        for _, row in price_df.sort_values(["kol_id", "platform", "service_type"]).iterrows()
    }
    selected_price = None
    selected_record = None

    if mode in {"Sửa", "Xóa"}:
        if not price_options:
            st.info("Chưa có giá booking để thao tác.")
            return
        selected_label = st.selectbox("Chọn giá booking", list(price_options.keys()))
        selected_price = price_options[selected_label]
        selected_record = price_df[price_df["price_id"] == selected_price].iloc[0].to_dict()

    kol_labels_list = list(kol_labels.keys())
    kol_id_values = list(kol_labels.values())

    with st.form("price_form", clear_on_submit=(mode == "Thêm mới")):
        price_id = st.text_input(
            "Price ID",
            value="" if mode == "Thêm mới" else selected_record["price_id"],
            disabled=mode == "Sửa",
        )
        kol_label = st.selectbox(
            "KOL",
            kol_labels_list,
            index=0 if not selected_record else kol_id_values.index(selected_record["kol_id"]),
        )
        service_type = st.selectbox(
            "Dịch vụ",
            SERVICE_TYPES,
            index=0 if not selected_record else safe_index(SERVICE_TYPES, selected_record["service_type"]),
        )
        platform = st.selectbox(
            "Nền tảng booking",
            PLATFORMS,
            index=0 if not selected_record else safe_index(PLATFORMS, selected_record["platform"]),
        )
        price = st.number_input(
            "Giá",
            min_value=0.0,
            value=0.0 if not selected_record else float(selected_record["price"]),
            step=50000.0,
        )
        description = st.text_area(
            "Mô tả dịch vụ",
            value="" if not selected_record else selected_record["description"],
        )
        note = st.text_area("Ghi chú", value="" if not selected_record else selected_record["note"])
        submit = st.form_submit_button(mode)

    if not submit:
        return

    if mode == "Xóa":
        st.session_state.price_df = delete_price(st.session_state.price_df, selected_price)
        st.session_state.selection_result = pd.DataFrame()
        st.success("Đã xóa giá booking.")
        st.rerun()

    if not price_id.strip():
        st.error("Price ID là bắt buộc.")
        return

    if mode == "Thêm mới" and st.session_state.price_df["price_id"].eq(price_id.strip()).any():
        st.error("Price ID đã tồn tại.")
        return

    payload = {
        "price_id": price_id.strip(),
        "kol_id": kol_labels[kol_label],
        "service_type": service_type,
        "platform": platform,
        "price": price,
        "description": description.strip(),
        "note": note.strip(),
    }
    st.session_state.price_df = upsert_price(st.session_state.price_df, payload)
    st.success(f"Đã {mode.lower()} giá booking.")
    st.rerun()


def main() -> None:
    st.set_page_config(page_title="KOL Booking Manager", layout="wide")
    st.title("KOL Booking Manager Demo")
    st.caption("Web demo quản lý booking KOL cho team booking, chạy local với Streamlit.")

    try:
        initialize_state()
    except WorkbookValidationError as exc:
        st.error(str(exc))
        st.stop()

    filtered_df = render_sidebar()

    metric_col1, metric_col2 = st.columns(2)
    with metric_col1:
        st.metric("Số KOL", int(st.session_state.kol_df["kol_id"].nunique()))
    with metric_col2:
        st.metric("Dòng giá booking", int(len(st.session_state.price_df)))

    render_kol_selector(filtered_df)

    st.divider()
    render_selection_summary()

    st.divider()
    crud_col1, crud_col2 = st.columns(2)
    with crud_col1:
        render_kol_form()
    with crud_col2:
        render_price_form()


if __name__ == "__main__":
    main()
