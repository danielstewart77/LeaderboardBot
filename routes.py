# === routes.py ===
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse, Response
from models import ScoreUpdate
from database import get_db
import sqlite3
import os
import asyncio
from playwright.async_api import async_playwright

router = APIRouter()

FACETS = [
    "daily_quiet_time",
    "team_call_attendance",
    "daily_journaling",
    "weekly_curriculum"
]

@router.post("/score")
def update_score(payload: ScoreUpdate, db: sqlite3.Connection = Depends(get_db)):
    if payload.facet not in FACETS:
        raise HTTPException(status_code=400, detail="Invalid facet")

    cursor = db.cursor()
    cursor.execute("SELECT score FROM scores WHERE user_id = ? AND facet = ?", (payload.user_id, payload.facet))
    row = cursor.fetchone()
    if row:
        new_score = row[0] + payload.amount
        cursor.execute("UPDATE scores SET score = ? WHERE user_id = ? AND facet = ?", (new_score, payload.user_id, payload.facet))
    else:
        new_score = payload.amount
        cursor.execute("INSERT INTO scores (user_id, facet, score) VALUES (?, ?, ?)", (payload.user_id, payload.facet, new_score))
    db.commit()
    return {"user_id": payload.user_id, "facet": payload.facet, "score": new_score}

@router.get("/leaderboard", response_class=HTMLResponse)
def leaderboard_page():
    with open("templates/leaderboard.html") as f:
        return f.read()

@router.get("/leaderboard/image", response_class=Response)
def leaderboard_image():
    html_path = os.path.abspath("templates/leaderboard.html")

    async def render_html_to_png():
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
            page = await browser.new_page()
            await page.goto(f"file://{html_path}", wait_until="networkidle")
            image_bytes = await page.screenshot(full_page=True)
            await browser.close()
            return image_bytes

    image_bytes = asyncio.get_event_loop().run_until_complete(render_html_to_png())
    return Response(content=image_bytes, media_type="image/png")
