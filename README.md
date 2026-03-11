# 🛢️ Oil Price Tracker Telegram Bot

Telegram Bot theo dõi giá dầu thô toàn cầu theo thời gian thực.

## Tính năng

- 📊 Xem giá dầu thời gian thực (WTI, Brent, Dubai, OPEC Basket, Natural Gas)
- 📈 Biểu đồ xu hướng giá với nhiều khung thời gian
- 🔔 Cảnh báo giá tự động
- 📰 Phân tích thị trường

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
| `/chart [type] [period]` | Biểu đồ giá dầu |
| `/alert [type] [above/below] [price]` | Đặt cảnh báo giá |
| `/news` | Phân tích thị trường |
| `/help` | Trợ giúp |

## Nguồn dữ liệu

- Yahoo Finance (yfinance)
- CrudePrice API
- EIA API (backup)

## Tech Stack

- Python 3.10+
- python-telegram-bot
- matplotlib / pandas
- SQLite
