# === bot.py ===
import discord
from discord.ext import commands
import aiohttp
import os
from dotenv import load_dotenv
load_dotenv()

LEADERBOARDBOT_TOKEN = os.getenv("LEADERBOARDBOT_TOKEN")
API_BASE_URL = os.getenv("API_BASE_URL")  # e.g., "https://your-api.azurewebsites.net"
FACETS = ["teamwork", "creativity", "wins"]

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

@bot.command()
async def score(ctx, member: discord.Member, facet: str, amount: int):
    if facet not in FACETS:
        await ctx.send(f"Invalid facet. Choose from: {', '.join(FACETS)}")
        return

    payload = {
        "user_id": str(member.id),
        "facet": facet,
        "amount": amount
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(f"{API_BASE_URL}/score", json=payload) as resp:
            if resp.status != 200:
                await ctx.send("Failed to update score.")
                return
            data = await resp.json()
            await ctx.send(f"{member.display_name}'s {facet} score is now {data['score']}")

@bot.command()
async def leaderboard(ctx):
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{API_BASE_URL}/leaderboard") as resp:
            if resp.status != 200:
                await ctx.send("Failed to fetch leaderboard.")
                return
            data = await resp.json()

    lines = [f"{'Name':<20} " + " ".join(f"{facet[:10]:>10}" for facet in FACETS)]
    for user_id, facets in data.items():
        user = ctx.guild.get_member(int(user_id))
        name = user.display_name if user else user_id
        line = f"{name:<20} " + " ".join(f"{facets.get(f, 0):>10}" for f in FACETS)
        lines.append(line)

    await ctx.send("```" + "\n".join(lines) + "```")

if LEADERBOARDBOT_TOKEN is None:
    raise ValueError("LEADERBOARDBOT_TOKEN environment variable is not set.")
bot.run(LEADERBOARDBOT_TOKEN)
