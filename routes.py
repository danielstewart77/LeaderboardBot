# === routes.py ===
from discord import HTTPException
from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from models import ScoreUpdate
from database import get_db
import sqlite3
from fastapi import HTTPException


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

@router.get("/leaderboard", response_class=PlainTextResponse)
def leaderboard_markdown(db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT user_id, facet, score FROM scores")
    rows = cursor.fetchall()

    # Build nested dict: {user_id: {facet: score}}
    leaderboard = {}
    for user_id, facet, score in rows:
        leaderboard.setdefault(user_id, {}).update({facet: score})

    # Create markdown table
    lines = []
    header = "| User ID | " + " | ".join(facet.replace("_", " ").title() for facet in FACETS) + " |"
    separator = "|" + "|".join(["---"] * (len(FACETS) + 1)) + "|"
    lines.extend([header, separator])

    for user_id, scores in leaderboard.items():
        row = [f"`{user_id[:6]}`"]  # show partial user ID
        row.extend(str(scores.get(facet, 0)) for facet in FACETS)
        lines.append("| " + " | ".join(row) + " |")

    return "\n".join(lines)
