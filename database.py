# === database.py ===
from sqlalchemy.orm import Session
from sqlalchemy import func # for SUM and other SQL functions
from models import SessionLocal, Leaderboard, ScoreUpdate, Team, User # Changed from .models
from typing import List, Dict, Tuple, Optional, Any # Import Any


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
        db_score.score = db_score.score + score_update.amount  # type: ignore[reportAttributeAccessIssue]
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
    return db_score[0] if db_score else 0

def get_leaderboard_data(db: Session) -> List[Dict[str, Any]]:
    """
    Fetches aggregated leaderboard data, joining with user and team info.
    Each item contains user_id, total_score, and team_name.
    """
    # This query joins Leaderboard with User and Team to get the team name for each user.
    # It groups by user and team to calculate the total score.
    query_result = db.query(
        Leaderboard.user_id,
        func.sum(Leaderboard.score).label('total_score'),
        Team.name.label('team_name')
    ).outerjoin(User, User.name == Leaderboard.user_id)\
     .outerjoin(Team, Team.id == User.group_id)\
     .group_by(Leaderboard.user_id, Team.name)\
     .order_by(func.sum(Leaderboard.score).desc())\
     .all()

    # Convert the list of Row objects to a list of dictionaries
    leaderboard_list = [
        {"user_id": row.user_id, "total_score": row.total_score, "team_name": row.team_name}
        for row in query_result
    ]
    return leaderboard_list

def get_all_scores_by_user(db: Session, user_id: str) -> List[Dict[str, Any]]:
    """Fetches all facet scores for a specific user."""
    results = db.query(Leaderboard.facet, Leaderboard.score).filter(Leaderboard.user_id == user_id).all()
    user_scores = []
    for row in results:
        user_scores.append({"facet": row[0], "score": row[1]})  # Fix to access tuple elements
    return user_scores

def add_team(db: Session, team_name: str) -> Team:
    """Creates a new team in the database."""
    db_team = Team(name=team_name)
    db.add(db_team)
    db.commit()
    db.refresh(db_team)
    return db_team

def add_user_to_team(db: Session, user_name: str, team_name: str) -> Optional[User]:
    """Assigns an existing user to an existing team."""
    # Find the team
    db_team = db.query(Team).filter(Team.name == team_name).first()
    if not db_team:
        return None # Or raise an exception

    # Find or create the user
    db_user = db.query(User).filter(User.name == user_name).first()
    if not db_user:
        db_user = User(name=user_name, team=db_team)
        db.add(db_user)
    else:
        db_user.team = db_team

    db.commit()
    db.refresh(db_user)
    return db_user

def get_all_teams(db: Session) -> List[Team]:
    """Returns all teams from the database."""
    return db.query(Team).order_by(Team.name).all()

def get_all_users(db: Session) -> List[User]:
    """Returns all users from the database."""
    return db.query(User).order_by(User.name).all()

def get_team_leaderboard_data(db: Session) -> List[Dict[str, Any]]:
    """
    Fetches aggregated team leaderboard data.
    Each item contains team_name and total_score.
    """
    # This query joins Leaderboard with User and Team to get team totals.
    # It groups by team to calculate the total score for each team.
    query_result = db.query(
        Team.name.label('team_name'),
        func.sum(Leaderboard.score).label('total_score')
    ).join(User, User.group_id == Team.id)\
     .join(Leaderboard, Leaderboard.user_id == User.name)\
     .group_by(Team.name)\
     .order_by(func.sum(Leaderboard.score).desc())\
     .all()

    # Convert the list of Row objects to a list of dictionaries
    team_leaderboard_list = [
        {"team_name": row.team_name, "total_score": row.total_score}
        for row in query_result
    ]
    return team_leaderboard_list

def get_all_users_with_scores(db: Session) -> List[Dict[str, Any]]:
    """
    Fetches all users with their total scores, ordered by total score descending.
    Each item contains user_id, total_score, and team_name.
    """
    query_result = db.query(
        Leaderboard.user_id,
        func.sum(Leaderboard.score).label('total_score'),
        Team.name.label('team_name')
    ).outerjoin(User, User.name == Leaderboard.user_id)\
     .outerjoin(Team, Team.id == User.group_id)\
     .group_by(Leaderboard.user_id, Team.name)\
     .order_by(func.sum(Leaderboard.score).desc())\
     .all()

    # Convert the list of Row objects to a list of dictionaries
    users_list = [
        {
            "user_id": row.user_id, 
            "total_score": row.total_score, 
            "team_name": row.team_name if row.team_name else "No Team"
        }
        for row in query_result
    ]
    return users_list