# 🛢️ Oil Price Tracker Telegram Bot

Telegram Bot theo dõi giá dầu thô toàn cầu theo thời gian thực.

## Tính năng

- 📊 Xem giá dầu thời gian thực (WTI, Brent, Natural Gas, v.v.)
- 🇻🇳 Xem giá xăng dầu Việt Nam (Petrolimex) cập nhật tự động
- 📈 Biểu đồ lịch sử giá với nhiều khung thời gian
- 🔔 Cảnh báo tự động khi giá vượt ngưỡng hoặc khi VN đổi giá xăng
- 📰 Phân tích tin tức thị trường & so sánh chênh lệch giá thế giới vs VN

## Cài đặt

```bash
# Clone repository
git clone <repo-url>
cd oil_bot

# Tạo môi trường ảo
python -m venv venv
venv\Scripts\activate  # Windows

# Cài đặt dependencies
pip install -r requirements.txt

# Cấu hình
cp .env.example .env
# Điền Bot Token và API Keys vào .env

# Chạy bot
python bot.py
```

## Lệnh Bot

| Lệnh | Mô tả |
|-------|--------|
| `/start` | Khởi động bot |
| `/price` | Xem giá dầu hiện tại |
| `/vn` | Xem giá xăng dầu Việt Nam (Petrolimex) |
| `/vn compare` | So sánh giá xăng VN với giá thế giới quy đổi |
| `/chart [type] [period]` | Biểu đồ giá dầu |
| `/alert [type] [above/below] [price]` | Đặt cảnh báo giá |
| `/news` | Phân tích thị trường |
| `/help` | Trợ giúp |

## Nguồn dữ liệu

- **Thế giới**: Yahoo Finance (yfinance)
- **Việt Nam**: VNExpress (primary), webtygia.com (fallback)
- **Tỷ giá**: Vietcombank

## Tech Stack

- Python 3.10+
- `python-telegram-bot`
- `matplotlib` / `pandas`
- `BeautifulSoup4` (Scraping)
- `Flask` (Webserver Ảo)
- `SQLite`

## Triển khai (Deployment)

Dự án này được cấu hình sẵn để deploy miễn phí 24/7 trên **Render.com**:
1. Tạo Web Service trên Render.com, trỏ về repo GitHub của bạn.
2. Cài đặt **Start Command**: `python bot.py`
3. Cài đặt **Environment Variable**: `BOT_TOKEN`
4. Dùng [cron-job.org](https://cron-job.org/) gọi vào đường dẫn Render cấp mỗi 10 phút để giữ bot chạy liên tục (nhờ `keep_alive.py`).
