import os
import audioop  # Fake audioop for Python 3.14 compatibility
import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import asyncio
import time
from datetime import datetime

# ============================================================
# CONFIG — Read from environment variables
# ============================================================

TOKEN = os.getenv("TOKEN")
OWNER_ID = 1528719270127865982      # YOUR DISCORD USER ID
DB_FILE = "leaderboard.db"

# ============================================================
# DATABASE FUNCTIONS
# ============================================================

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            discord_id TEXT UNIQUE,
            username TEXT,
            hits INTEGER DEFAULT 0,
            today_hits INTEGER DEFAULT 0,
            total_hits INTEGER DEFAULT 0,
            role TEXT DEFAULT 'user',
            created_at TEXT
        )
    ''')
    conn.commit()
    conn.close()

def get_user(username):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username = ?", (username,))
    result = c.fetchone()
    conn.close()
    return result

def get_user_by_discord(discord_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE discord_id = ?", (str(discord_id),))
    result = c.fetchone()
    conn.close()
    return result

def get_all_users():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM users ORDER BY hits DESC")
    result = c.fetchall()
    conn.close()
    return result

def add_user(username, discord_id=None, role='user'):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username = ?", (username,))
    if c.fetchone():
        conn.close()
        return False
    c.execute(
        "INSERT INTO users (username, discord_id, role, created_at) VALUES (?, ?, ?, ?)",
        (username, str(discord_id) if discord_id else None, role, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()
    return True

def delete_user(username):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE username = ?", (username,))
    affected = c.rowcount
    conn.commit()
    conn.close()
    return affected > 0

def add_hits(username, amount):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE users SET hits = hits + ?, today_hits = today_hits + ?, total_hits = total_hits + ? WHERE username = ?",
              (amount, amount, amount, username))
    affected = c.rowcount
    conn.commit()
    conn.close()
    return affected > 0

def remove_hits(username, amount):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE users SET hits = hits - ?, today_hits = today_hits - ? WHERE username = ? AND hits >= ?",
              (amount, amount, username, amount))
    affected = c.rowcount
    conn.commit()
    conn.close()
    return affected > 0

def reset_hits(username):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE users SET hits = 0, today_hits = 0 WHERE username = ?", (username,))
    affected = c.rowcount
    conn.commit()
    conn.close()
    return affected > 0

def set_role(username, role):
    if role not in ['owner', 'staff', 'user']:
        return False
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE users SET role = ? WHERE username = ?", (role, username))
    affected = c.rowcount
    conn.commit()
    conn.close()
    return affected > 0

def reset_today_hits():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE users SET today_hits = 0")
    conn.commit()
    conn.close()

def get_total_hits():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT SUM(hits) FROM users")
    result = c.fetchone()[0] or 0
    conn.close()
    return result

# ============================================================
# BOT SETUP
# ============================================================

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    init_db()
    print(f"✅ Bot online as {bot.user}")
    print(f"📊 Database: {DB_FILE}")
    print(f"👑 Owner ID: {OWNER_ID}")
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} commands globally")
    except Exception as e:
        print(f"❌ Sync error: {e}")
    reset_today_hits()
    print("🔄 Today hits reset")
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="/leaderboard"))

def is_owner(interaction: discord.Interaction):
    return interaction.user.id == OWNER_ID

# ============================================================
# COMMANDS
# ============================================================

# ---- Leaderboard & Hits ----

@bot.tree.command(name="leaderboard", description="View the hit leaderboard")
async def leaderboard(interaction: discord.Interaction):
    await interaction.response.defer()
    users = get_all_users()
    if not users:
        await interaction.followup.send("📊 No users on the leaderboard yet!")
        return
    embed = discord.Embed(title="🏆 LEADERBOARD", description="Top hit earners", color=0x6c7aff)
    embed.set_footer(text="Updated in real-time")
    medal_emojis = ["🥇", "🥈", "🥉"]
    for idx, user in enumerate(users[:10]):
        rank = idx + 1
        medal = medal_emojis[idx] if idx < 3 else f"#{rank}"
        role_emoji = "👑" if user[6] == 'owner' else "⭐" if user[6] == 'staff' else ""
        embed.add_field(name=f"{medal} {user[2]}", value=f"**{user[3]}** hits {role_emoji}", inline=False)
    current_user = get_user_by_discord(interaction.user.id)
    if current_user:
        embed.set_footer(text=f"Your hits: {current_user[3]} | Today: {current_user[4]} | Total: {current_user[5]}")
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="hits", description="Check your hits")
async def hits(interaction: discord.Interaction):
    user_data = get_user_by_discord(interaction.user.id)
    if not user_data:
        add_user(interaction.user.name, interaction.user.id, 'user')
        user_data = get_user_by_discord(interaction.user.id)
    embed = discord.Embed(title=f"📊 {user_data[2]}'s Stats", color=0x5df2a1)
    embed.add_field(name="Total Hits", value=str(user_data[3]), inline=True)
    embed.add_field(name="Today", value=str(user_data[4]), inline=True)
    embed.add_field(name="All-Time", value=str(user_data[5]), inline=True)
    embed.add_field(name="Role", value=user_data[6].upper(), inline=True)
    embed.set_footer(text=f"ID: {user_data[1]}")
    await interaction.response.send_message(embed=embed)

# ---- Hit Notification ----

@bot.tree.command(name="hit_notify", description="[USER] Notify owner that you got a hit")
async def hit_notify(interaction: discord.Interaction):
    user_data = get_user_by_discord(interaction.user.id)
    if not user_data:
        await interaction.response.send_message("❌ You're not in the system yet. Use `/hits` to register.", ephemeral=True)
        return
    owner = await bot.fetch_user(OWNER_ID)
    if owner:
        embed = discord.Embed(
            title="🔔 Hit Notification",
            description=f"{interaction.user.mention} got a hit!",
            color=0xfbbf24
        )
        embed.add_field(name="Username", value=user_data[2], inline=True)
        embed.add_field(name="Total Hits", value=user_data[3], inline=True)
        embed.add_field(name="Today", value=user_data[4], inline=True)
        embed.set_footer(text=f"User ID: {interaction.user.id}")
        await owner.send(embed=embed)
        await interaction.response.send_message("✅ Owner has been notified of your hit!", ephemeral=True)
    else:
        await interaction.response.send_message("❌ Could not notify owner.", ephemeral=True)

# ---- Owner Commands ----

@bot.tree.command(name="give", description="[OWNER] Give hits to a user")
@app_commands.describe(username="The username to give hits to", amount="Number of hits to give")
async def give(interaction: discord.Interaction, username: str, amount: int = 1):
    if not is_owner(interaction):
        await interaction.response.send_message("❌ You must be the owner to use this command.", ephemeral=True)
        return
    if amount <= 0:
        await interaction.response.send_message("❌ Amount must be positive.", ephemeral=True)
        return
    user = get_user(username)
    if not user:
        await interaction.response.send_message(f"❌ User `{username}` not found. Use `/add` first.", ephemeral=True)
        return
    add_hits(username, amount)
    user = get_user(username)
    await interaction.response.send_message(f"✅ **+{amount}** hits given to **{username}**!\nTotal: **{user[3]}** hits")

@bot.tree.command(name="remove", description="[OWNER] Remove hits from a user")
@app_commands.describe(username="The username to remove hits from", amount="Number of hits to remove")
async def remove(interaction: discord.Interaction, username: str, amount: int = 1):
    if not is_owner(interaction):
        await interaction.response.send_message("❌ You must be the owner to use this command.", ephemeral=True)
        return
    if amount <= 0:
        await interaction.response.send_message("❌ Amount must be positive.", ephemeral=True)
        return
    user = get_user(username)
    if not user:
        await interaction.response.send_message(f"❌ User `{username}` not found.", ephemeral=True)
        return
    if user[3] < amount:
        await interaction.response.send_message(f"❌ User only has {user[3]} hits.", ephemeral=True)
        return
    remove_hits(username, amount)
    user = get_user(username)
    await interaction.response.send_message(f"✅ **-{amount}** hits removed from **{username}**!\nTotal: **{user[3]}** hits")

@bot.tree.command(name="add", description="[OWNER] Add a user to the leaderboard")
@app_commands.describe(username="The username to add", role="Role: owner, staff, or user")
async def add(interaction: discord.Interaction, username: str, role: str = "user"):
    if not is_owner(interaction):
        await interaction.response.send_message("❌ You must be the owner to use this command.", ephemeral=True)
        return
    if role not in ['owner', 'staff', 'user']:
        await interaction.response.send_message("❌ Role must be `owner`, `staff`, or `user`.", ephemeral=True)
        return
    if get_user(username):
        await interaction.response.send_message(f"❌ User `{username}` already exists.", ephemeral=True)
        return
    add_user(username, None, role)
    await interaction.response.send_message(f"✅ Added **{username}** as **{role.upper()}**!\nUse `/give {username}` to add hits.")

@bot.tree.command(name="delete", description="[OWNER] Delete a user from the leaderboard")
@app_commands.describe(username="The username to delete")
async def delete(interaction: discord.Interaction, username: str):
    if not is_owner(interaction):
        await interaction.response.send_message("❌ You must be the owner to use this command.", ephemeral=True)
        return
    if delete_user(username):
        await interaction.response.send_message(f"✅ Deleted **{username}** from the leaderboard.")
    else:
        await interaction.response.send_message(f"❌ User `{username}` not found.", ephemeral=True)

@bot.tree.command(name="setrole", description="[OWNER] Change a user's role")
@app_commands.describe(username="The username", role="Role: owner, staff, or user")
async def setrole(interaction: discord.Interaction, username: str, role: str):
    if not is_owner(interaction):
        await interaction.response.send_message("❌ You must be the owner to use this command.", ephemeral=True)
        return
    if role not in ['owner', 'staff', 'user']:
        await interaction.response.send_message("❌ Role must be `owner`, `staff`, or `user`.", ephemeral=True)
        return
    if not get_user(username):
        await interaction.response.send_message(f"❌ User `{username}` not found.", ephemeral=True)
        return
    set_role(username, role)
    await interaction.response.send_message(f"✅ **{username}** is now **{role.upper()}**!")

@bot.tree.command(name="reset", description="[OWNER] Reset a user's hits to 0")
@app_commands.describe(username="The username to reset")
async def reset(interaction: discord.Interaction, username: str):
    if not is_owner(interaction):
        await interaction.response.send_message("❌ You must be the owner to use this command.", ephemeral=True)
        return
    if not get_user(username):
        await interaction.response.send_message(f"❌ User `{username}` not found.", ephemeral=True)
        return
    reset_hits(username)
    await interaction.response.send_message(f"✅ Reset **{username}**'s hits to 0!")

@bot.tree.command(name="resetall", description="[OWNER] Reset ALL users' hits to 0")
async def resetall(interaction: discord.Interaction):
    if not is_owner(interaction):
        await interaction.response.send_message("❌ You must be the owner to use this command.", ephemeral=True)
        return
    users = get_all_users()
    for user in users:
        reset_hits(user[2])
    await interaction.response.send_message("✅ Reset ALL users' hits to 0!")

@bot.tree.command(name="dashboard", description="[OWNER] View full dashboard with all users")
async def dashboard(interaction: discord.Interaction):
    if not is_owner(interaction):
        await interaction.response.send_message("❌ You must be the owner to use this command.", ephemeral=True)
        return
    await interaction.response.defer()
    users = get_all_users()
    if not users:
        await interaction.followup.send("📊 No users on the dashboard.")
        return
    embed = discord.Embed(title="📊 OWNER DASHBOARD", description="Full user management view", color=0xfbbf24)
    total = get_total_hits()
    embed.add_field(name="Total Hits (All Users)", value=str(total), inline=False)
    for user in users[:15]:
        role_emoji = "👑" if user[6] == 'owner' else "⭐" if user[6] == 'staff' else ""
        embed.add_field(name=f"{user[2]} {role_emoji}", value=f"**{user[3]}** hits | Today: {user[4]} | Total: {user[5]} | Role: **{user[6].upper()}**", inline=False)
    embed.set_footer(text="Use /give, /remove, /add, /delete, /setrole, /reset to manage")
    await interaction.followup.send(embed=embed)

# ============================================================
# FLOOD COMMANDS (OWNER ONLY)
# ============================================================

@bot.tree.command(name="flood", description="[OWNER] Flood the current channel with messages")
@app_commands.describe(count="Number of messages to send", message="Message to spam (optional)")
async def flood(interaction: discord.Interaction, count: int = 10, message: str = None):
    if not is_owner(interaction):
        await interaction.response.send_message("❌ You must be the owner to use this command.", ephemeral=True)
        return
    if count < 1 or count > 200:
        await interaction.response.send_message("❌ Count must be between 1 and 200.", ephemeral=True)
        return
    await interaction.response.send_message(f"⏳ Flooding {count} messages...", ephemeral=True)
    msg = message or "🌊 Flooding the chat! #flood"
    channel = interaction.channel
    for i in range(count):
        await channel.send(f"{msg} [{i+1}/{count}]")
        await asyncio.sleep(0.1)  # Slight delay to avoid rate limits

@bot.tree.command(name="flood_customize", description="[OWNER] Flood with custom message and count")
@app_commands.describe(message="The message to spam", count="Number of messages (1-200)")
async def flood_customize(interaction: discord.Interaction, message: str, count: int = 10):
    if not is_owner(interaction):
        await interaction.response.send_message("❌ You must be the owner to use this command.", ephemeral=True)
        return
    if count < 1 or count > 200:
        await interaction.response.send_message("❌ Count must be between 1 and 200.", ephemeral=True)
        return
    await interaction.response.send_message(f"⏳ Flooding {count} messages with custom message...", ephemeral=True)
    channel = interaction.channel
    for i in range(count):
        await channel.send(f"{message} [{i+1}/{count}]")
        await asyncio.sleep(0.1)

@bot.tree.command(name="flood_links", description="[OWNER] Flood the channel with random links")
@app_commands.describe(count="Number of links to send")
async def flood_links(interaction: discord.Interaction, count: int = 10):
    if not is_owner(interaction):
        await interaction.response.send_message("❌ You must be the owner to use this command.", ephemeral=True)
        return
    if count < 1 or count > 200:
        await interaction.response.send_message("❌ Count must be between 1 and 200.", ephemeral=True)
        return
    await interaction.response.send_message(f"⏳ Flooding {count} links...", ephemeral=True)
    links = [
        "https://youtu.be/dQw4w9WgXcQ",
        "https://www.youtube.com/watch?v=6n3pFFPSlW4",
        "https://www.youtube.com/watch?v=8v_4O44bP9Y",
        "https://discord.gg/example",
        "https://www.google.com/search?q=random",
        "https://www.reddit.com/r/all",
        "https://www.xkcd.com/",
        "https://www.wikipedia.org/",
        "https://www.github.com/",
        "https://www.stackoverflow.com/"
    ]
    channel = interaction.channel
    import random
    for i in range(count):
        link = random.choice(links)
        await channel.send(f"🔗 {link} [{i+1}/{count}]")
        await asyncio.sleep(0.1)

# ============================================================
# ERROR HANDLING
# ============================================================

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CommandOnCooldown):
        await interaction.response.send_message(f"⏳ Cooldown: {error.retry_after:.1f}s", ephemeral=True)
    else:
        await interaction.response.send_message(f"❌ Error: {error}", ephemeral=True)
        print(f"Error: {error}")

# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    if not TOKEN:
        print("❌ ERROR: TOKEN environment variable is not set!")
        print("   Please add TOKEN to Railway Variables.")
    else:
        bot.run(TOKEN)
