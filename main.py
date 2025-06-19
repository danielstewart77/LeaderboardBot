# === main.py ===
from fastapi import FastAPI, Depends
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from routes import router # Assuming your routes will be updated to use Depends(get_db)
from models import create_tables # Import create_tables from models.py
from database import get_db # Import get_db for dependency injection if needed directly here
from sqlalchemy.orm import Session # Import Session for type hinting if needed
import os
import asyncio

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[API] Application startup...")
    # Create database tables on startup
    print("[DB] Initializing database and creating tables if they don't exist...")
    create_tables() # Call the function to create tables
    print("[DB] Database initialization complete.")

    # Bot launching logic - keep if bot is still meant to run in the same process
    # Ensure your bot.py is adapted if it needs DB access through SQLAlchemy sessions
    if os.getenv("RUN_DISCORD_BOT") == "1":
        print("[BOT] RUN_DISCORD_BOT is set. Launching bot with asyncio...")
        try:
            print("[BOT] Bot launch sequence initiated (ensure bot.py is updated for new DB if it interacts directly).")
        except Exception as e:
            print(f"[BOT] Failed to launch bot: {e}")
    yield
    print("[API] Application shutdown.")

app = FastAPI(title="Discord Leaderboard API", lifespan=lifespan)
app.include_router(router) # Ensure routes in routes.py use Depends(get_db)

# Static files mounting - ensure 'static' directory exists or is created if needed
os.makedirs("static", exist_ok=True) # If you have static files served by FastAPI
app.mount("/static", StaticFiles(directory="static"), name="static")

# The 'data' directory for SQLite is no longer needed for PostgreSQL
# os.makedirs("data", exist_ok=True)
