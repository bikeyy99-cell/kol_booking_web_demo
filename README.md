# KOL Booking Web Demo

Web demo quản lý booking KOL bằng Python Streamlit.

## Chạy trên Windows

1. Mở terminal trong VS Code.
2. Chạy lần lượt:

```powershell
cd "D:\Code dex\kol_booking_web_demo"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

Nếu PowerShell chặn activate script:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

## Tính năng

- Upload file Excel
- Dùng file mẫu nếu chưa upload
- Join `KOL_Profile` và `Booking_Prices` theo `kol_id`
- Lọc theo tên, mô tả/chủ đề, nền tảng, service type, khoảng giá
- Xem chi tiết KOL
- Thêm, sửa, xóa KOL
- Thêm, sửa, xóa giá booking
- Export dữ liệu đã lọc
- Download Excel sau khi chỉnh sửa
- Kiểm tra lỗi thiếu sheet, thiếu cột, sai kiểu giá
