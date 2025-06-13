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
    import bot

if os.getenv("RUN_DISCORD_BOT") == "1":
    threading.Thread(target=run_bot, daemon=True).start()
