# === main.py ===
from fastapi import FastAPI
from routes import router
import os

app = FastAPI(title="Discord Leaderboard API")
app.include_router(router)

# Ensure DB folder exists
os.makedirs("data", exist_ok=True)