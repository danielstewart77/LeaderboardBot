# === models.py ===
from pydantic import BaseModel

class ScoreUpdate(BaseModel):
    user_id: str
    facet: str
    amount: int
