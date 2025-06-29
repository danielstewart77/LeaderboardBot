# === routes.py ===
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from models import ScoreUpdate, TeamCreate, UserTeamAssign
from database import get_db, add_score as db_add_score, get_leaderboard_data as db_get_leaderboard_data, get_all_scores_by_user, add_team, add_user_to_team, get_all_teams, get_all_users, get_team_leaderboard_data
from sqlalchemy.orm import Session
from starlette.background import BackgroundTask
import tempfile
from playwright.async_api import async_playwright
import os

router = APIRouter()

FACETS = [
    "daily_quiet_time",
    "team_call_attendance",
    "daily_journaling",
    "weekly_curriculum"
]

# Ensure templates directory exists
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
if not os.path.exists(TEMPLATES_DIR):
    os.makedirs(TEMPLATES_DIR)

templates = Jinja2Templates(directory=TEMPLATES_DIR)

@router.post("/score")
async def update_score(payload: ScoreUpdate, db: Session = Depends(get_db)):
    if payload.facet not in FACETS:
        raise HTTPException(status_code=400, detail="Invalid facet")
    # Ensure the user exists in leaderboard_users
    from models import User
    if not db.query(User).filter(User.name == payload.user_id).first():
        new_user = User(name=payload.user_id)
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

    # Use the new database function
    updated_entry = db_add_score(db, payload)
    
    # The db_add_score function now returns the Leaderboard SQLAlchemy object.
    # We can return its details or a specific message.
    return {
        "user_id": updated_entry.user_id,
        "facet": updated_entry.facet,
        "score": updated_entry.score,
        "last_updated": updated_entry.last_updated
    }

@router.get("/leaderboard", response_class=HTMLResponse)
async def get_leaderboard_html(request: Request, db: Session = Depends(get_db)):
    # Fetches aggregated scores: [{'user_id': 'user1', 'total_score': 100}, ...]
    leaderboard_summary = db_get_leaderboard_data(db)
    
    # To display individual facets as well, we need to fetch them for each user
    # This can be N+1 queries if not careful. For a small number of users, it might be acceptable.
    # For larger leaderboards, consider optimizing or changing the display format.
    detailed_leaderboard = []
    for summary_item in leaderboard_summary:
        user_id = summary_item["user_id"]
        total_score = summary_item["total_score"]
        team_name = summary_item["team_name"]  # Include team_name from the database query
        facet_scores_list = get_all_scores_by_user(db, user_id)
        # Convert list of facet scores to a dict for easier template access
        facets_for_user = {item["facet"]: item["score"] for item in facet_scores_list}
        detailed_leaderboard.append({
            "user_id": user_id,
            "total_score": total_score,
            "team_name": team_name,  # Include team_name in the detailed leaderboard
            "facets": facets_for_user
        })

    # Fetch team leaderboard data
    team_leaderboard = get_team_leaderboard_data(db)

    return templates.TemplateResponse(
        "leaderboard.html", 
        {
            "request": request, 
            "leaderboard": detailed_leaderboard, # Pass the detailed structure
            "team_leaderboard": team_leaderboard, # Pass the team leaderboard data
            "all_possible_facets": FACETS # Pass all possible facets for consistent column rendering
        }
    )

@router.get("/leaderboard/discord")
async def get_leaderboard_discord(request: Request, db: Session = Depends(get_db)): # Added db session
    # Construct absolute URL for Playwright to access
    # If API ingress is restricted to internal, Playwright (running in the same container)
    # should access via localhost.
    # The port is the one Uvicorn listens on inside the container.
    leaderboard_html_url = "http://localhost:8000/leaderboard" 
    # print(f"Playwright attempting to screenshot internal URL: {leaderboard_html_url}")

    async with async_playwright() as p:
        # browser = await p.chromium.launch() # Default, might need args in Docker
        browser = await p.chromium.launch(args=["--no-sandbox", "--disable-setuid-sandbox"]) # Common for Docker
        page = await browser.new_page()
        try:
            await page.goto(leaderboard_html_url, wait_until="networkidle") # wait_until can be helpful
            # Wait for a specific element that indicates the leaderboard is loaded.
            # Adjust selector if your table or a key element has a specific ID or class.
            await page.wait_for_selector('table.leaderboard-table', timeout=15000) # Example selector, increased timeout
            screenshot_bytes = await page.screenshot(type="png", full_page=True) # full_page might be useful
        except Exception as e:
            print(f"Playwright error: {e}")
            await browser.close()
            raise HTTPException(status_code=500, detail=f"Failed to generate leaderboard image: {e}")
        await browser.close()

    # MODIFIED SECTION FOR TEMP FILE HANDLING AND CLEANUP
    # import tempfile # Already imported at the top
    # import os # Already imported at the top
    from starlette.background import BackgroundTask

    # Create a temporary file
    # delete=False is important because FileResponse will open it by path.
    # We will delete it manually with a background task.
    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    tmp_file.write(screenshot_bytes)
    tmp_file_path = tmp_file.name
    tmp_file.close() # Close the file handle, FileResponse will reopen by path

    # Define a cleanup function
    def cleanup_temp_file(path: str):
        try:
            os.remove(path)
            print(f"Successfully removed temp file: {path}")
        except Exception as e:
            print(f"Error removing temp file {path}: {e}")

    return FileResponse(
        tmp_file_path,
        media_type="image/png",
        filename="leaderboard.png",
        background=BackgroundTask(cleanup_temp_file, path=tmp_file_path)
    )

@router.post("/create_team")
def create_team(team_data: TeamCreate, db: Session = Depends(get_db)):
    """
    Creates a new team.
    """
    # This import is needed here to avoid circular dependency issues with models
    from models import Team
    
    existing_team = db.query(Team).filter(Team.name == team_data.name).first()
    if existing_team:
        raise HTTPException(status_code=400, detail=f"Team '{team_data.name}' already exists.")
        
    new_team = add_team(db, team_name=team_data.name)
    return {"id": new_team.id, "name": new_team.name}

@router.post("/assign_user_to_team")
def assign_user_to_team(assignment: UserTeamAssign, db: Session = Depends(get_db)):
    """
    Assigns a user to a team. Creates the user if they don't exist.
    """
    updated_user = add_user_to_team(db, user_name=assignment.user_name, team_name=assignment.team_name)
    
    if not updated_user:
        raise HTTPException(status_code=404, detail=f"Team '{assignment.team_name}' not found.")
        
    return {
        "user_name": updated_user.name,
        "team_name": updated_user.team.name
    }

@router.get("/get_users", response_class=JSONResponse)
def get_users_route(db: Session = Depends(get_db)):
    users = get_all_users(db)
    return [user.name for user in users]

@router.get("/get_teams", response_class=JSONResponse)
def get_teams_route(db: Session = Depends(get_db)):
    teams = get_all_teams(db)
    return [team.name for team in teams]

@router.get("/users", response_class=HTMLResponse)
async def get_users_page(request: Request, db: Session = Depends(get_db)):
    users = get_all_users(db)
    teams = get_all_teams(db)
    return templates.TemplateResponse("users.html", {"request": request, "users": users, "teams": teams})

@router.get("/teams", response_class=HTMLResponse)
async def get_teams_page(request: Request):
    return templates.TemplateResponse("teams.html", {"request": request})

@router.get("/get_user_scores/{user_id}", response_class=JSONResponse)
def get_user_scores_route(user_id: str, db: Session = Depends(get_db)):
    """Get all facet scores for a specific user."""
    user_scores = get_all_scores_by_user(db, user_id)
    if not user_scores:
        raise HTTPException(status_code=404, detail=f"No scores found for user '{user_id}'")
    return user_scores

@router.get("/get_team_scores/{team_name}", response_class=JSONResponse)
def get_team_scores_route(team_name: str, db: Session = Depends(get_db)):
    """Get aggregated scores for a specific team."""
    from models import Team, User
    
    # Find the team
    team = db.query(Team).filter(Team.name == team_name).first()
    if not team:
        raise HTTPException(status_code=404, detail=f"Team '{team_name}' not found")
    
    # Get all team members
    team_members = db.query(User).filter(User.group_id == team.id).all()
    member_names = [member.name for member in team_members]
    
    if not team_members:
        raise HTTPException(status_code=404, detail=f"Team '{team_name}' has no members")
    
    # Aggregate scores by facet for all team members
    facet_totals = {}
    total_score = 0
    
    for member in team_members:
        member_scores = get_all_scores_by_user(db, str(member.name))
        for score_data in member_scores:
            facet = score_data['facet']
            score = score_data['score']
            facet_totals[facet] = facet_totals.get(facet, 0) + score
            total_score += score
    
    return {
        "team_name": team_name,
        "total_score": total_score,
        "facet_scores": facet_totals,
        "members": member_names
    }
