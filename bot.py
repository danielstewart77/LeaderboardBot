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
    "homework": "weekly_curriculum"
}

DEFAULT_FACET_POINTS = {
    "daily_quiet_time": 5,
    "team_call_attendance": 15,
    "daily_journaling": 2,
    "weekly_curriculum": 15
}

intents = discord.Intents.default()
intents.message_content = True # Keep if you might add prefix commands later

bot = commands.Bot(command_prefix="!", intents=intents) # Changed: client -> bot, and class to commands.Bot

# tree = app_commands.CommandTree(client) # This was the old way, now it's client.tree

# Guild ID for testing - commands update instantly. Remove for global commands.
TEST_GUILD_ID = discord.Object(id=1233578210009026580) # Replace with your server ID

@bot.event # Changed: client -> bot
async def on_ready():
    logger.info(f"Logged in as {bot.user}") # Changed: client -> bot
    try:
        # If using a specific guild for testing:
        if TEST_GUILD_ID:
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
    logger.info("[BOT] Starting bot as standalone script...")
    try:
        bot.run(LEADERBOARDBOT_TOKEN) # Changed: client -> bot
    except Exception as e:
        logger.error(f"[BOT] Error running bot: {e}", exc_info=True)
