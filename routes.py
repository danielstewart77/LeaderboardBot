# === routes.py ===
from fastapi import APIRouter, Depends, HTTPException
from models import ScoreUpdate
from database import get_db
import sqlite3
from fastapi.responses import HTMLResponse


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

@router.get("/leaderboard/html", response_class=HTMLResponse)
def leaderboard_page():
    with open("templates/leaderboard.html") as f:
        return f.read()


@router.get("/leaderboard")
def get_leaderboard(db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT user_id, facet, score FROM scores")
    data = cursor.fetchall()

    leaderboard = {}
    for user_id, facet, score in data:
        if user_id not in leaderboard:
            leaderboard[user_id] = {f: 0 for f in FACETS}
        leaderboard[user_id][facet] = score
    return leaderboard