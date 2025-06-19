# === models.py ===
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, DateTime, func, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import os

from dotenv import load_dotenv
# Load environment variables from .env file
load_dotenv()


POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_HOST = os.getenv("POSTGRES_HOST")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB")

if not all([POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_HOST, POSTGRES_DB]):
    raise ValueError("Missing one or more PostgreSQL environment variables: POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_HOST, POSTGRES_DB")

DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# SQLAlchemy model for the leaderboard
class Leaderboard(Base):
    __tablename__ = "leaderboard"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False) # Discord username#discriminator
    facet = Column(String, index=True, nullable=False)
    score = Column(Integer, default=0, nullable=False)
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # You might want a unique constraint on user_id and facet combined
    # from sqlalchemy.schema import UniqueConstraint
    # __table_args__ = (UniqueConstraint('user_id', 'facet', name='_user_facet_uc'),)

# New SQLAlchemy models for Teams and Users
class Team(Base):
    __tablename__ = "leaderboard_teams"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    
    # Relationship to the User model
    users = relationship("User", back_populates="team")

class User(Base):
    __tablename__ = "leaderboard_users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False) # Discord username#discriminator
    group_id = Column(Integer, ForeignKey("leaderboard_teams.id"))

    # Relationship to the Team model
    team = relationship("Team", back_populates="users")


# Pydantic model for request body
class ScoreUpdate(BaseModel):
    user_id: str
    facet: str
    amount: int

# Pydantic models for new routes
class TeamCreate(BaseModel):
    name: str

class UserTeamAssign(BaseModel):
    user_name: str
    team_name: str

# Function to create tables (call this once at startup if tables don't exist)
def create_tables():
    Base.metadata.create_all(bind=engine)
