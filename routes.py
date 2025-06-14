# === routes.py ===
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates
from models import ScoreUpdate
from database import get_db, add_score as db_add_score, get_leaderboard_data as db_get_leaderboard_data, get_all_scores_by_user
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
        facet_scores_list = get_all_scores_by_user(db, user_id)
        # Convert list of facet scores to a dict for easier template access
        facets_for_user = {item["facet"]: item["score"] for item in facet_scores_list}
        detailed_leaderboard.append({
            "user_id": user_id,
            "total_score": total_score,
            "facets": facets_for_user
        })

    return templates.TemplateResponse(
        "leaderboard.html", 
        {
            "request": request, 
            "leaderboard": detailed_leaderboard, # Pass the detailed structure
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
