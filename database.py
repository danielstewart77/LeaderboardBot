# === database.py ===
from sqlalchemy.orm import Session
from sqlalchemy import func # for SUM and other SQL functions
from models import SessionLocal, Leaderboard, ScoreUpdate # Changed from .models
from typing import List, Dict, Tuple

# Dependency to get a DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def add_score(db: Session, score_update: ScoreUpdate) -> Leaderboard:
    # Check if a record already exists for this user_id and facet
    db_score = db.query(Leaderboard).filter(
        Leaderboard.user_id == score_update.user_id, 
        Leaderboard.facet == score_update.facet
    ).first()

    if db_score:
        # If exists, add the new amount to the existing score
        db_score.score += score_update.amount
    else:
        # If not exists, create a new record
        db_score = Leaderboard(
            user_id=score_update.user_id, 
            facet=score_update.facet, 
            score=score_update.amount
        )
        db.add(db_score)
    
    db.commit()
    db.refresh(db_score)
    return db_score

def get_user_score_for_facet(db: Session, user_id: str, facet: str) -> int:
    db_score = db.query(Leaderboard.score).filter(
        Leaderboard.user_id == user_id, 
        Leaderboard.facet == facet
    ).first()
    return db_score.score if db_score else 0

def get_leaderboard_data(db: Session) -> List[Dict[str, any]]:
    """Fetches aggregated scores for each user across all facets."""
    # Query to sum scores for each user_id, ordered by total score descending
    results = db.query(
        Leaderboard.user_id,
        func.sum(Leaderboard.score).label("total_score")
    ).group_by(Leaderboard.user_id).order_by(func.sum(Leaderboard.score).desc()).all()
    
    leaderboard_list = []
    for row in results:
        leaderboard_list.append({"user_id": row.user_id, "total_score": row.total_score})
    return leaderboard_list

def get_all_scores_by_user(db: Session, user_id: str) -> List[Dict[str, any]]:
    """Fetches all facet scores for a specific user."""
    results = db.query(Leaderboard.facet, Leaderboard.score).filter(Leaderboard.user_id == user_id).all()
    user_scores = []
    for row in results:
        user_scores.append({"facet": row.facet, "score": row.score})
    return user_scores