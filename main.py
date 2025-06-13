# === main.py ===
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from routes import router
import os
import asyncio

@asynccontextmanager
async def lifespan(app: FastAPI):
    if os.getenv("RUN_DISCORD_BOT") == "1":
        print("[BOT] RUN_DISCORD_BOT is set. Launching bot with asyncio...")
        try:
            import bot
            asyncio.create_task(bot.run_bot_async())
            print("[BOT] Bot launched successfully.")
        except Exception as e:
            print(f"[BOT] Failed to launch bot: {e}")
    yield
    print("[BOT] Lifespan shutdown")

app = FastAPI(title="Discord Leaderboard API", lifespan=lifespan)
app.include_router(router)

os.makedirs("data", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")
