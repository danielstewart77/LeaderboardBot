# === bot.py ===
import discord
from discord import app_commands # Import app_commands
from discord.ext import commands # Import commands
import aiohttp
import os
from dotenv import load_dotenv
import io
from typing import Optional
import logging
import asyncio # For FastAPI lifespan integration
from contextlib import asynccontextmanager # For FastAPI lifespan integration

logger = logging.getLogger("discord") # Standard discord logger
logger.setLevel(logging.INFO)
logging.basicConfig(level=logging.INFO)

# Validate env vars
token_env = os.getenv("LEADERBOARDBOT_TOKEN")
api_url_env = os.getenv("API_BASE_URL")

if not token_env:
    raise RuntimeError("Environment variable LEADERBOARDBOT_TOKEN is not set.")
if not api_url_env:
    raise RuntimeError("Environment variable API_BASE_URL is not set.")

LEADERBOARDBOT_TOKEN: str = token_env
API_BASE_URL: str = api_url_env

FACET_MAP = {
    "quiet_time": "daily_quiet_time",
    "team_call": "team_call_attendance",
    "journal": "daily_journaling",
    "homework": "weekly_curriculum",
    "bonus": "bonus",
    "check_in": "brotherhood_check_in"
}

DEFAULT_FACET_POINTS = {
    "daily_quiet_time": 5,
    "team_call_attendance": 15,
    "daily_journaling": 2,
    "weekly_curriculum": 15,
    "bonus": 15,
    "brotherhood_check_in": 15
}

intents = discord.Intents.default()
intents.message_content = True # Keep if you might add prefix commands later

bot = commands.Bot(command_prefix="!", intents=intents) # Changed: client -> bot, and class to commands.Bot

# tree = app_commands.CommandTree(client) # This was the old way, now it's client.tree

# Guild ID for testing - commands update instantly. Remove for global commands.
TEST_GUILD_ID = False #discord.Object(id=1233578210009026580) # Replace with your server ID

@bot.event # Changed: client -> bot
async def on_ready():
    logger.info(f"Logged in as {bot.user}") # Changed: client -> bot
    try:
        # If using a specific guild for testing:
        if TEST_GUILD_ID:
            logger.info("Clearing existing commands...")
            bot.tree.clear_commands(guild=TEST_GUILD_ID)

            await bot.tree.sync(guild=TEST_GUILD_ID) # Changed: client -> bot
            logger.info(f"Synced commands to guild {TEST_GUILD_ID.id}")
        else:
        # Sync globally
            await bot.tree.sync() # Changed: client -> bot
            logger.info("Synced commands globally.")
    except Exception as e:
        logger.error(f"Failed to sync commands: {e}")

async def update_score_for_facet(
    interaction: discord.Interaction, 
    member: discord.Member, 
    facet_key: str, 
    custom_amount: Optional[int] = None
):
    api_facet_name = FACET_MAP.get(facet_key)
    if not api_facet_name:
        await interaction.response.send_message(f"Internal error: Unknown facet key '{facet_key}'.", ephemeral=True)
        return

    amount_to_add = custom_amount if custom_amount is not None else DEFAULT_FACET_POINTS[api_facet_name]

    payload = {
        "user_id": str(member), 
        "facet": api_facet_name,
        "amount": amount_to_add
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(f"{API_BASE_URL}/score", json=payload) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    await interaction.response.send_message(
                        f"{member.display_name}'s {api_facet_name.replace('_', ' ')} score is now {data['score']}. Points added: {amount_to_add}.",
                        ephemeral=False
                    )
                else:
                    error_data = await resp.text()
                    logger.error(f"API Error for {api_facet_name} ({member}): {resp.status} - {error_data}")
                    await interaction.response.send_message(
                        f"Failed to update {api_facet_name.replace('_', ' ')} score for {member.display_name}. API Error: {resp.status}", 
                        ephemeral=True
                    )
        except aiohttp.ClientConnectorError as e:
            logger.error(f"Connection Error updating score for {api_facet_name} ({member}): {e}")
            await interaction.response.send_message(
                f"Could not connect to the Leaderboard API to update score for {member.display_name}.",
                ephemeral=True
            )

@bot.tree.command(name="leaderboard", description="Displays the current leaderboard.") # Changed: client -> bot
async def leaderboard_slash(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=False) 
    async with aiohttp.ClientSession() as session:
        discord_leaderboard_url = f"{API_BASE_URL}/leaderboard/discord"
        try:
            async with session.get(discord_leaderboard_url) as resp:
                if resp.status == 200:
                    image_bytes = await resp.read()
                    await interaction.followup.send(file=discord.File(io.BytesIO(image_bytes), filename="leaderboard.png"))
                else:
                    error_message = await resp.text()
                    logger.error(f"API Error for /leaderboard/discord: {resp.status} - {error_message}")
                    await interaction.followup.send(f"Failed to fetch leaderboard image. API Error: {resp.status}", ephemeral=True)
        except aiohttp.ClientConnectorError as e:
            logger.error(f"Connection Error fetching leaderboard: {e}")
            await interaction.followup.send("Could not connect to the Leaderboard API to fetch the leaderboard.", ephemeral=True)

@bot.tree.command(name="quiet_time", description="Log daily quiet time.") # Changed: client -> bot
@app_commands.describe(member="The member to credit.", points="Custom points to award (optional).")
async def quiet_time_slash(interaction: discord.Interaction, member: discord.Member, points: Optional[int] = None):
    await update_score_for_facet(interaction, member, "quiet_time", points)

@bot.tree.command(name="team_call", description="Log team call attendance.") # Changed: client -> bot
@app_commands.describe(member="The member to credit.", points="Custom points to award (optional).")
async def team_call_slash(interaction: discord.Interaction, member: discord.Member, points: Optional[int] = None):
    await update_score_for_facet(interaction, member, "team_call", points)

@bot.tree.command(name="journal", description="Log daily journaling.") # Changed: client -> bot
@app_commands.describe(member="The member to credit.", points="Custom points to award (optional).")
async def journal_slash(interaction: discord.Interaction, member: discord.Member, points: Optional[int] = None):
    await update_score_for_facet(interaction, member, "journal", points)

@bot.tree.command(name="homework", description="Log weekly curriculum/homework completion.") # Changed: client -> bot
@app_commands.describe(member="The member to credit.", points="Custom points to award (optional).")
async def homework_slash(interaction: discord.Interaction, member: discord.Member, points: Optional[int] = None):
    await update_score_for_facet(interaction, member, "homework", points)

@bot.tree.command(name="bonus", description="Award bonus points to a member.")
@app_commands.describe(member="The member to credit.", points="Custom points to award (optional).")
async def bonus_slash(interaction: discord.Interaction, member: discord.Member, points: Optional[int] = None):
    await update_score_for_facet(interaction, member, "bonus", points)

@bot.tree.command(name="check_in", description="Log daily check-in.")
@app_commands.describe(member="The member to credit.", points="Custom points to award (optional).")
async def check_in_slash(interaction: discord.Interaction, member: discord.Member, points: Optional[int] = None):
    await update_score_for_facet(interaction, member, "check_in", points)

@bot.tree.command(name="my_score", description="Show a user's individual scores for all facets.")
@app_commands.describe(user="The user to check scores for.")
async def my_score_slash(interaction: discord.Interaction, user: discord.Member):
    await interaction.response.defer(ephemeral=False)
    
    async with aiohttp.ClientSession() as session:
        try:
            # Get user's individual facet scores
            scores_url = f"{API_BASE_URL}/get_user_scores/{str(user)}"
            async with session.get(scores_url) as resp:
                if resp.status == 200:
                    user_scores = await resp.json()
                    
                    # Build formatted message
                    embed = discord.Embed(
                        title=f"📊 {user.display_name}'s Scores",
                        color=0x3498db
                    )
                    
                    total_score = 0
                    for facet_data in user_scores:
                        facet_name = facet_data['facet'].replace('_', ' ').title()
                        score = facet_data['score']
                        total_score += score
                        embed.add_field(name=facet_name, value=f"{score} points", inline=True)
                    
                    embed.add_field(name="🏆 Total Score", value=f"{total_score} points", inline=False)
                    embed.set_thumbnail(url=user.display_avatar.url)
                    
                    await interaction.followup.send(embed=embed)
                else:
                    error_message = await resp.text()
                    logger.error(f"API Error for /get_user_scores: {resp.status} - {error_message}")
                    await interaction.followup.send(f"Failed to fetch scores for {user.display_name}. User may not have any scores yet.", ephemeral=True)
        except aiohttp.ClientConnectorError as e:
            logger.error(f"Connection Error fetching user scores: {e}")
            await interaction.followup.send("Could not connect to the Leaderboard API to fetch user scores.", ephemeral=True)

async def team_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> list[app_commands.Choice[str]]:
    """Autocomplete function to fetch available teams."""
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{API_BASE_URL}/get_teams") as resp:
                if resp.status == 200:
                    teams = await resp.json()
                    # Filter teams based on current input and return up to 25 choices
                    filtered_teams = [team for team in teams if current.lower() in team.lower()]
                    return [
                        app_commands.Choice(name=team, value=team)
                        for team in filtered_teams[:25]  # Discord limits to 25 choices
                    ]
                else:
                    return []
        except Exception:
            return []

@bot.tree.command(name="my_team", description="Show team's total scores for all facets.")
@app_commands.describe(team_name="The team to check scores for.")
@app_commands.autocomplete(team_name=team_autocomplete)
async def my_team_slash(interaction: discord.Interaction, team_name: str):
    await interaction.response.defer(ephemeral=False)
    
    async with aiohttp.ClientSession() as session:
        try:
            # Get team's aggregated scores
            team_url = f"{API_BASE_URL}/get_team_scores/{team_name}"
            async with session.get(team_url) as resp:
                if resp.status == 200:
                    team_data = await resp.json()
                    
                    # Build formatted message
                    embed = discord.Embed(
                        title=f"🏆 Team {team_name} Scores",
                        color=0xe74c3c
                    )
                    
                    total_score = team_data.get('total_score', 0)
                    facet_scores = team_data.get('facet_scores', {})
                    members = team_data.get('members', [])
                    
                    # Add facet scores
                    for facet, score in facet_scores.items():
                        facet_name = facet.replace('_', ' ').title()
                        embed.add_field(name=facet_name, value=f"{score} points", inline=True)
                    
                    embed.add_field(name="🏆 Total Team Score", value=f"{total_score} points", inline=False)
                    
                    if members:
                        member_list = ", ".join(members)
                        embed.add_field(name="👥 Team Members", value=member_list, inline=False)
                    
                    await interaction.followup.send(embed=embed)
                else:
                    error_message = await resp.text()
                    logger.error(f"API Error for /get_team_scores: {resp.status} - {error_message}")
                    await interaction.followup.send(f"Failed to fetch scores for team '{team_name}'. Team may not exist or have no scores.", ephemeral=True)
        except aiohttp.ClientConnectorError as e:
            logger.error(f"Connection Error fetching team scores: {e}")
            await interaction.followup.send("Could not connect to the Leaderboard API to fetch team scores.", ephemeral=True)

# --- FastAPI Lifespan Integration (Optional) ---
# This part is for running the bot alongside a FastAPI server in the same process.
# If you run bot.py standalone, the if __name__ == "__main__": block will be used.

async def run_bot_in_background():
    try:
        logger.info("[BOT] Attempting to start bot...")
        await bot.start(LEADERBOARDBOT_TOKEN) # Changed: client -> bot
    except Exception as e:
        logger.error(f"[BOT] Bot crashed: {e}", exc_info=True)

@asynccontextmanager
async def lifespan(app):
    logger.info("[FastAPI] Starting up, launching Discord bot in background...")
    asyncio.create_task(run_bot_in_background())
    yield
    logger.info("[FastAPI] Shutting down, closing Discord bot...")
    await bot.close() # Changed: client -> bot
    logger.info("[FastAPI] Discord bot closed.")

# --- Standalone Bot Running --- 
if __name__ == "__main__":
    print("✅ Bot container started and reached __main__ block.")
    logger.info("[BOT] Starting bot as standalone script...")
    try:
        bot.run(LEADERBOARDBOT_TOKEN) # Changed: client -> bot
    except Exception as e:
        logger.error(f"[BOT] Error running bot: {e}", exc_info=True)
