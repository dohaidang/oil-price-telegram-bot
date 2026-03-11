from flask import Flask
from threading import Thread
import os

app = Flask(__name__)

@app.route('/')
def home():
    return "Oil Price Telegram Bot is running on Render!"

def run():
    # Render requires binding to 0.0.0.0 and dynamically assigning the PORT
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    """Starts a web server on a separate thread to keep the bot alive."""
    t = Thread(target=run)
    t.daemon = True # Allows the program to exit even if this thread is running
    t.start()
