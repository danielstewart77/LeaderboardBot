# === bot.py ===
import discord
from discord.ext import commands
import aiohttp
import os
from typing import Optional

# Get env vars
token_env = os.getenv("LEADERBOARDBOT_TOKEN")
api_url_env = os.getenv("API_BASE_URL")

if not token_env:
    raise RuntimeError("Environment variable LEADERBOARDBOT_TOKEN is not set.")
if not api_url_env:
    raise RuntimeError("Environment variable API_BASE_URL is not set.")

# These are now guaranteed to be strings
LEADERBOARDBOT_TOKEN: str = token_env
API_BASE_URL: str = api_url_env

FACETS = [
    "daily_quiet_time",
    "team_call_attendance",
    "daily_journaling",
    "weekly_curriculum"
]

DEFAULT_FACET_POINTS = {
    "daily_quiet_time": 5,
    "team_call_attendance": 15,
    "daily_journaling": 2,
    "weekly_curriculum": 15
}

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

@bot.command()
async def score(ctx, member: discord.Member, facet: str, amount: Optional[int] = None):
    if facet not in FACETS:
        await ctx.send(
            "Invalid facet. Choose from: daily_quiet_time, team_call_attendance, daily_journaling, weekly_curriculum"
        )
        return

    if amount is None:
        amount = DEFAULT_FACET_POINTS[facet]

    payload = {
        "user_id": str(member.id),
        "facet": facet,
        "amount": amount
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(f"{API_BASE_URL}/score", json=payload) as resp:
            if resp.status != 200:
                data = await resp.text()
                print(f"API Response: {resp.status} - {data}")
                await ctx.send("Failed to update score.")
                return
            data = await resp.json()
            await ctx.send(f"{member.display_name}'s {facet.replace('_', ' ')} score is now {data['score']}")

@bot.command()
async def leaderboard(ctx):
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{API_BASE_URL}/leaderboard/html") as resp:
            if resp.status != 200:
                await ctx.send("Failed to fetch leaderboard.")
                return
            data = await resp.json()

    lines = [f"{'Name':<20} " + " ".join(f"{facet.replace('_', ' ')[:16]:>16}" for facet in FACETS)]
    for user_id, facets in data.items():
        try:
            user = ctx.guild.get_member(int(user_id))
            name = user.display_name if user else f"User {user_id}"
        except ValueError:
            name = f"User {user_id}"  # fallback for test data

        line = f"{name:<20} " + " ".join(f"{facets.get(f, 0):>16}" for f in FACETS)
        lines.append(line)

    await ctx.send("```" + "\n".join(lines) + "```")

# Used by FastAPI lifespan
async def run_bot_async():
    print("[BOT] Running bot.run() from lifespan context")
    await bot.start(LEADERBOARDBOT_TOKEN)

# Used when running bot.py directly
if __name__ == "__main__":
    bot.run(LEADERBOARDBOT_TOKEN)
