# === main.py ===
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from routes import router
import os
import threading

app = FastAPI(title="Discord Leaderboard API")
app.include_router(router)

# Ensure DB folder exists
os.makedirs("data", exist_ok=True)

# Mount static files (for JS/CSS)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Start the Discord bot if the flag is enabled
def run_bot():
    print("[BOT] Starting bot thread...")
    try:
        import bot
        print("[BOT] bot.py imported successfully.")
    except Exception as e:
        print(f"[BOT] Failed to start bot: {e}")

if os.getenv("RUN_DISCORD_BOT") == "1":
    print("[BOT] RUN_DISCORD_BOT is set to 1. Launching bot...")
    threading.Thread(target=run_bot, daemon=True).start()
else:
    print("[BOT] RUN_DISCORD_BOT is not set or not '1'. Bot will not start.")
