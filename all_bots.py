import threading
import os
from dotenv import load_dotenv
import yt_dlp
load_dotenv()

# ================== Application Bot ==================
import discord as discord_app
from discord.ext import commands as commands_app
from discord.ui import Button as Button_app, View as View_app
import asyncio as asyncio_app

import sqlite3
# --- SQLite setup for Application Bot ---
app_db_lock = threading.Lock()
app_db = sqlite3.connect('applicationbot.db', check_same_thread=False)
app_db.row_factory = sqlite3.Row
app_cursor = app_db.cursor()
app_cursor.execute('''
CREATE TABLE IF NOT EXISTS app_counter (
    app_type TEXT PRIMARY KEY,
    counter INTEGER NOT NULL
)
''')
app_cursor.execute('''
CREATE TABLE IF NOT EXISTS applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    app_type TEXT NOT NULL,
    channel_id INTEGER NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)
''')
# Initialize counters if not present
for t in ("astdx", "als", "all"):
    if not app_cursor.execute('SELECT 1 FROM app_counter WHERE app_type = ?', (t,)).fetchone():
        app_cursor.execute('INSERT INTO app_counter (app_type, counter) VALUES (?, ?)', (t, 1))
app_db.commit()

def get_app_counter(app_type):
    with app_db_lock:
        row = app_cursor.execute('SELECT counter FROM app_counter WHERE app_type = ?', (app_type,)).fetchone()
        return row['counter'] if row else 1

def increment_app_counter(app_type):
    with app_db_lock:
        c = get_app_counter(app_type)
        app_cursor.execute('UPDATE app_counter SET counter = ? WHERE app_type = ?', (c+1, app_type))
        app_db.commit()
        return c

def log_application(user_id, app_type, channel_id):
    with app_db_lock:
        app_cursor.execute('INSERT INTO applications (user_id, app_type, channel_id) VALUES (?, ?, ?)', (user_id, app_type, channel_id))
        app_db.commit()

intents_app = discord_app.Intents.all()
bot_app = commands_app.Bot(command_prefix="app!", intents=intents_app)

bot_app.remove_command('help')

ASTDX_ROLE_ID = 1382679356975087647
ALS_ROLE_ID = 1397023739631108188
CATEGORY_ID = 1397234544368685269
STAFF_ROLE_ID = 1397186487044411522

application_counter = {
    "astdx": 1,
    "als": 1,
    "all": 1
}

form_message = (
    "Welcome! We are glad that you want to become our important part - Helpers, but we need to clarify that you could do it or not.\n\n"
    "**1. Respect**\n"
    "- You must respect people, but if they don't respect or are not grateful for your help, please make a report with proofs.\n\n"
    "**2. Choices**\n"
    "- You can choose what requests you want to do. If you see a request you can't handle, pass it to someone else.\n\n"
    "**3. Ratings**\n"
    "- After finishing the request, ask them to click 'Delete Ticket' and a rating board will appear. With enough 5-star ratings, you can join special giveaways!"
)

class ApplicationView(View_app):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ApplicationButton("Apply on ASTDX", "astdx"))
        self.add_item(ApplicationButton("Apply on ALS", "als"))
        self.add_item(ApplicationButton("Apply All", "all"))

# Refactor ApplicationButton to use SQLite for counter and log applications
class ApplicationButton(Button_app):
    def __init__(self, label, app_type):
        super().__init__(label=label, style=discord_app.ButtonStyle.primary)
        self.app_type = app_type

    async def callback(self, interaction: discord_app.Interaction):
        user = interaction.user
        guild = interaction.guild
        category = guild.get_channel(CATEGORY_ID)
        number = increment_app_counter(self.app_type)
        channel_name = f"{self.app_type}-application-#{number:04}"
        overwrites = {
            guild.default_role: discord_app.PermissionOverwrite(read_messages=False),
            user: discord_app.PermissionOverwrite(read_messages=True, send_messages=True),
        }
        channel = await guild.create_text_channel(
            name=channel_name,
            category=category,
            overwrites=overwrites
        )
        log_application(user.id, self.app_type, channel.id)
        await interaction.response.send_message(f"\u2705 Application created: {channel.mention}", ephemeral=True)
        await channel.send(f"{user.mention}\n{form_message}")
        view = View_app()
        view.add_item(AcceptButton(self.app_type, user))
        view.add_item(RejectButton(user))
        view.add_item(DeleteTicketButton(channel, user))
        await channel.send("Staff controls:", view=view)

class AcceptButton(Button_app):
    def __init__(self, app_type, user):
        super().__init__(label="\u2705 Accept", style=discord_app.ButtonStyle.success)
        self.app_type = app_type
        self.user = user
    async def callback(self, interaction: discord_app.Interaction):
        roles = []
        if self.app_type == "astdx":
            roles.append(ASTDX_ROLE_ID)
        elif self.app_type == "als":
            roles.append(ALS_ROLE_ID)
        elif self.app_type == "all":
            roles.extend([ALS_ROLE_ID, ASTDX_ROLE_ID])
        for role_id in roles:
            role = interaction.guild.get_role(role_id)
            if role:
                await self.user.add_roles(role)
        await interaction.response.send_message(f"\u2705 {self.user.mention} has been accepted and given roles.", ephemeral=True)

class RejectButton(Button_app):
    def __init__(self, user):
        super().__init__(label="\u274c Reject", style=discord_app.ButtonStyle.danger)
        self.user = user
    async def callback(self, interaction: discord_app.Interaction):
        await interaction.response.send_message(f"\u274c {self.user.mention}'s application was rejected.", ephemeral=True)

class DeleteTicketButton(Button_app):
    def __init__(self, channel, user):
        super().__init__(label="\ud83d\uddd1\ufe0f Delete Ticket", style=discord_app.ButtonStyle.danger)
        self.channel = channel
        self.user = user
    async def callback(self, interaction: discord_app.Interaction):
        await interaction.response.send_message("This ticket will be deleted in 5 seconds...", ephemeral=True)
        await asyncio_app.sleep(5)
        ticket_data = get_ticket(interaction.channel.id)
        if not ticket_data:
            await interaction.response.send_message("\u274c This ticket does not exist or is already closed.", ephemeral=True)
            return
        if interaction.user.id != ticket_data['creator_id']:
            await interaction.response.send_message("\u274c Only the ticket creator can delete this ticket.", ephemeral=True)
            return
        delete_ticket(interaction.channel.id)
        await interaction.response.send_message("\ud83d\uddd1\ufe0f Ticket deleted.", ephemeral=True)
        await interaction.channel.delete()
        staff_id = ticket_data['staff_id']
        if staff_id:
            staff_member = interaction.guild.get_member(staff_id)
            if staff_member:
                view = VouchView([staff_member], interaction.user.id)
                try:
                    await interaction.user.send("Would you like to vouch for the staff who helped you?", view=view)
                except Exception:
                    pass  # User may have DMs closed

class RulesView(View_app):
    def __init__(self, author: discord_app.Member):
        super().__init__(timeout=None)
        self.author = author
        self.current_page = 1
    async def interaction_check(self, interaction: discord_app.Interaction) -> bool:
        return interaction.user.id == self.author.id
    @discord_app.ui.button(label="Next \u25b6\ufe0f", style=discord_app.ButtonStyle.primary)
    async def next_page(self, interaction: discord_app.Interaction, button: Button_app):
        if self.current_page == 1:
            staff_role = interaction.guild.get_role(STAFF_ROLE_ID)
            if staff_role in interaction.user.roles:
                embed2 = discord_app.Embed(
                    title="\ud83d\udc6e Staff Guide",
                    description=(
                        "\u2022 **Take Requests:** When a ticket appears, check what the member needs. If you're confident you can help, press **TAKE REQUEST**.\n\n"
                        "\u2022 **Deletion & Ratings:** After completing the request, ask the member to press **DELETE TICKET** to leave a rating.\n\n"
                        "\u2022 **Choices:** You don\u2019t have to take every ticket. Only take the ones you can handle.\n\n"
                        "\u2022 **Respect:** Always respect members. If someone disrespects you, stop helping and report it.\n\n"
                        "\u2022 **Benefits:** Staff can join exclusive giveaways and perks."
                    ),
                    color=discord_app.Color.red()
                )
                self.current_page = 2
                await interaction.response.edit_message(embed=embed2, view=self)
            else:
                await interaction.response.send_message("\ud83d\udeab You don't have permission to view this page.", ephemeral=True)
    @discord_app.ui.button(label="\u25c0\ufe0f Back", style=discord_app.ButtonStyle.secondary)
    async def back_page(self, interaction: discord_app.Interaction, button: Button_app):
        if self.current_page == 2:
            embed1 = discord_app.Embed(
                title="\ud83d\udcdc AVS Server Rules & Guidelines",
                description=(
                    "**Welcome to AVS \u2014 a fun community for ALS, ASTDX, and chill chats!**\n\n"
                    "**\ud83c\udf1f 1. Respect & Kindness**\n"
                    "\u2022 Be respectful to everyone.\n"
                    "\u2022 No harassment, hate, threats, or toxic behavior \u2014 jokes are fine, but not harmful ones.\n"
                    "\u2022 If someone bothers you, don\u2019t retaliate \u2014 report them.\n\n"
                    "**\ud83d\udce2 2. Language & Behavior**\n"
                    "\u2022 Keep chats appropriate for all ages.\n"
                    "\u2022 Swearing is okay in moderation \u2014 no slurs or hate speech.\n"
                    "\u2022 No spam, flooding, mass pings.\n\n"
                    "**\ud83d\udccc 3. Use the Right Channels**\n"
                    "\u2022 Chat in general, memes in #memes, help in #support, etc.\n\n"
                    "**\ud83e\udde0 4. Content Rules**\n"
                    "\u2022 No NSFW/NSFL, illegal, pirated, or disturbing content.\n\n"
                    "**\ud83d\udeab 5. Alts & Raids**\n"
                    "\u2022 No alts unless approved. Trolls = instant ban.\n\n"
                    "**\u2705 Final:**\n"
                    "\u2022 No disrespect to helpers. Major = ban. Minor = mute.\n"
                ),
                color=discord_app.Color.blue()
            )
            self.current_page = 1
            await interaction.response.edit_message(embed=embed1, view=self)

@bot_app.command()
async def rules(ctx):
    embed1 = discord_app.Embed(
        title="\ud83d\udcdc AVS Server Rules & Guidelines",
        description=(
            "**Welcome to AVS \u2014 a fun community for ALS, ASTDX, and chill chats!**\n\n"
            "**\ud83c\udf1f 1. Respect & Kindness**\n"
            "\u2022 Be respectful to everyone.\n"
            "\u2022 No harassment, hate, threats, or toxic behavior \u2014 jokes are fine, but not harmful ones.\n"
            "\u2022 If someone bothers you, don\u2019t retaliate \u2014 report them.\n\n"
            "**\ud83d\udce2 2. Language & Behavior**\n"
            "\u2022 Keep chats appropriate for all ages.\n"
            "\u2022 Swearing is okay in moderation \u2014 no slurs or hate speech.\n"
            "\u2022 No spam, flooding, mass pings.\n\n"
            "**\ud83d\udccc 3. Use the Right Channels**\n"
            "\u2022 Chat in general, memes in #memes, help in #support, etc.\n\n"
            "**\ud83e\udde0 4. Content Rules**\n"
            "\u2022 No NSFW/NSFL, illegal, pirated, or disturbing content.\n\n"
            "**\ud83d\udeab 5. Alts & Raids**\n"
            "\u2022 No alts unless approved. Trolls = instant ban.\n\n"
            "**\u2705 Final:**\n"
            "\u2022 No disrespect to helpers. Major = ban. Minor = mute.\n"
        ),
        color=discord_app.Color.blue()
    )
    await ctx.send(embed=embed1, view=RulesView(ctx.author))

@bot_app.command()
async def application(ctx):
    await ctx.send("Click a button below to apply:", view=ApplicationView())

# --- Application Bot Help Command ---
@bot_app.command()
async def help(ctx):
    embed = discord_app.Embed(title="Application Bot Commands", color=discord_app.Color.green())
    embed.add_field(name="!rules", value="Show the server rules.", inline=False)
    embed.add_field(name="!application", value="Start an application process.", inline=False)
    await ctx.send(embed=embed)

def run_application_bot():
    bot_app.run(os.environ["APP_BOT_TOKEN"])

# ================== Giveaway Levels Bot ==================
import discord as discord_give
from discord.ext import commands as commands_give, tasks as tasks_give
import asyncio as asyncio_give
import random as random_give
from datetime import datetime as datetime_give, timedelta as timedelta_give

import sqlite3
# --- SQLite setup for Level Bot ---
level_db_lock = threading.Lock()

# Update SQLite connection for thread safety
level_db = sqlite3.connect('levelbot.db', check_same_thread=False)
level_db.row_factory = sqlite3.Row
level_cursor = level_db.cursor()
level_cursor.execute('''
CREATE TABLE IF NOT EXISTS user_exp (
    user_id INTEGER PRIMARY KEY,
    exp INTEGER NOT NULL,
    level INTEGER NOT NULL
)
''')
level_db.commit()

intents_give = discord_give.Intents.default()
intents_give.message_content = True
intents_give.members = True
bot_give = commands_give.Bot(command_prefix='mul!', intents=intents_give)

bot_give.remove_command('help')

# --- SQLite helper functions for user EXP/level ---
def get_user_exp(user_id):
    with level_db_lock:
        row = level_cursor.execute('SELECT exp, level FROM user_exp WHERE user_id = ?', (user_id,)).fetchone()
        if row:
            return {'exp': row['exp'], 'level': row['level']}
        else:
            return {'exp': 0, 'level': 1}

def set_user_exp(user_id, exp, level):
    with level_db_lock:
        if level_cursor.execute('SELECT 1 FROM user_exp WHERE user_id = ?', (user_id,)).fetchone():
            level_cursor.execute('UPDATE user_exp SET exp = ?, level = ? WHERE user_id = ?', (exp, level, user_id))
        else:
            level_cursor.execute('INSERT INTO user_exp (user_id, exp, level) VALUES (?, ?, ?)', (user_id, exp, level))
        level_db.commit()

def get_required_exp(level):
    return 3 * (2 ** (level - 1))

@bot_give.event
async def on_message(message):
    if message.author.bot:
        return
    user_id = message.author.id
    user_data = get_user_exp(user_id)
    user_data['exp'] += 1
    leveled_up = False
    while user_data['exp'] >= get_required_exp(user_data['level']):
        user_data['exp'] -= get_required_exp(user_data['level'])
        user_data['level'] += 1
        leveled_up = True
    set_user_exp(user_id, user_data['exp'], user_data['level'])
    if leveled_up:
        await message.channel.send(f"\ud83c\udf89 {message.author.mention} leveled up to level {user_data['level']}!")
    await bot_give.process_commands(message)
@bot_give.command(name='check')
async def check_level(ctx):
    user = get_user_exp(ctx.author.id)
    await ctx.send(f"{ctx.author.mention}, Level: {user['level']}, EXP: {user['exp']} / {get_required_exp(user['level'])}")
@bot_give.command(name='lb')
async def leaderboard(ctx):
    with level_db_lock:
        sorted_users = level_cursor.execute('SELECT user_id, exp, level FROM user_exp ORDER BY level DESC, exp DESC LIMIT 10').fetchall()
    desc = ""
    for i, row in enumerate(sorted_users):
        user = await bot_give.fetch_user(row['user_id'])
        desc += f"**{i+1}. {user.name}** - Level {row['level']} ({row['exp']} EXP)\n"
    embed = discord_give.Embed(title="\ud83d\udcca Leaderboard", description=desc, color=0x00ff00)
    await ctx.send(embed=embed)
giveaway_data = {}
@bot_give.command(name="giveaways")
async def start_giveaway(ctx, headline: str, winners: int, duration: str):
    duration_sec = int(duration[:-1]) * (3600 if duration.endswith("h") else 60)
    end_time = datetime_give.utcnow() + timedelta_give(seconds=duration_sec)
    embed = discord_give.Embed(title="\ud83c\udf89 Giveaway", description=headline, color=0x3498db)
    embed.add_field(name="\ud83c\udf81 Casual", value="Anyone can join!", inline=False)
    embed.add_field(name="\ud83d\udc8e Premium", value="Requires staff approval", inline=False)
    embed.set_footer(text=f"Ends <t:{int(end_time.timestamp())}:R>")
    view = GiveawayView(ctx.author.id, end_time, winners, headline)
    msg = await ctx.send(embed=embed, view=view)
    giveaway_data[msg.id] = {
        'casual_entries': [],
        'premium_entries': [],
        'end_time': end_time,
        'winners': winners,
        'message': msg,
        'type': 'main',
        'headline': headline
    }
    view.msg = msg
    countdown_timer.start()
class GiveawayView(discord_give.ui.View):
    def __init__(self, host_id, end_time, winners, headline):
        super().__init__(timeout=None)
        self.host_id = host_id
        self.end_time = end_time
        self.winners = winners
        self.headline = headline
        self.msg = None
    @discord_give.ui.button(label="Join Casual", style=discord_give.ButtonStyle.success)
    async def join_casual(self, interaction: discord_give.Interaction, button: discord_give.ui.Button):
        gid = self.msg.id
        if interaction.user.id in giveaway_data[gid]['casual_entries']:
            await interaction.response.send_message("\u274c You already joined the casual giveaway.", ephemeral=True)
            return
        giveaway_data[gid]['casual_entries'].append(interaction.user.id)
        await interaction.response.send_message("\u2705 Joined casual giveaway!", ephemeral=True)
    @discord_give.ui.button(label="Join Premium", style=discord_give.ButtonStyle.primary)
    async def join_premium(self, interaction: discord_give.Interaction, button: discord_give.ui.Button):
        gid = self.msg.id
        ticket_channel = await interaction.guild.create_text_channel(
            name=f"giveaway-entry-{random_give.randint(1000, 9999)}",
            overwrites={
                interaction.guild.default_role: discord_give.PermissionOverwrite(view_channel=False),
                interaction.user: discord_give.PermissionOverwrite(view_channel=True, send_messages=True),
                interaction.guild.me: discord_give.PermissionOverwrite(view_channel=True)
            },
            reason="Premium giveaway entry"
        )
        await interaction.response.send_message(f"\ud83d\udce9 A ticket was created: {ticket_channel.mention}", ephemeral=True)
        view = ApprovalView(gid, interaction.user.id, ticket_channel)
        await ticket_channel.send(f"Staff, please review the premium entry by {interaction.user.mention}.", view=view)
class ApprovalView(discord_give.ui.View):
    def __init__(self, giveaway_id, user_id, channel):
        super().__init__(timeout=None)
        self.giveaway_id = giveaway_id
        self.user_id = user_id
        self.channel = channel
    @discord_give.ui.button(label="Approve", style=discord_give.ButtonStyle.success)
    async def approve(self, interaction: discord_give.Interaction, button: discord_give.ui.Button):
        giveaway_data[self.giveaway_id]['premium_entries'].append(self.user_id)
        await interaction.response.send_message(f"\u2705 Approved <@{self.user_id}>")
        await self.channel.delete()
    @discord_give.ui.button(label="Decline", style=discord_give.ButtonStyle.danger)
    async def decline(self, interaction: discord_give.Interaction, button: discord_give.ui.Button):
        await interaction.response.send_message(f"\u274c Declined <@{self.user_id}>")
        await self.channel.delete()
@tasks_give.loop(seconds=30)
async def countdown_timer():
    now = datetime_give.utcnow()
    expired = []
    for gid, data in list(giveaway_data.items()):
        if data['end_time'] <= now:
            expired.append(gid)
            all_entries = data['casual_entries'] + data['premium_entries']
            if not all_entries:
                await data['message'].channel.send("\ud83c\udf81 Giveaway ended. No valid entries.")
                continue
            winners = random_give.sample(all_entries, min(len(all_entries), data['winners']))
            winner_mentions = ", ".join(f"<@{u}>" for u in winners)
            await data['message'].channel.send(f"\ud83c\udf89 Giveaway Over!\n**{data['headline']}**\nWinners: {winner_mentions}")
        else:
            embed = data['message'].embeds[0]
            embed.set_footer(text=f"Ends <t:{int(data['end_time'].timestamp())}:R>")
            await data['message'].edit(embed=embed)
    for gid in expired:
        del giveaway_data[gid]
def run_giveaway_bot():
    bot_give.run(os.environ["GIVEAWAY_BOT_TOKEN"])

# --- Giveaway Levels Bot Help Command ---
@bot_give.command(name="help")
async def help_give(ctx):
    embed = discord_give.Embed(title="Giveaway Levels Bot Commands", color=discord_give.Color.green())
    embed.add_field(name="mul!check", value="Check your level and EXP.", inline=False)
    embed.add_field(name="mul!lb", value="Show the leaderboard.", inline=False)
    embed.add_field(name="mul!giveaways <headline> <winners> <duration>", value="Start a giveaway (admin only).", inline=False)
    await ctx.send(embed=embed)

# ================== Invites Tracker Bot ==================
import discord as discord_inv
from discord.ext import commands as commands_inv
import json as json_inv
import os as os_inv
# --- SQLite setup for Invites Bot ---
invites_db_lock = threading.Lock()
invites_db = sqlite3.connect('invites.db', check_same_thread=False)
invites_db.row_factory = sqlite3.Row
invites_cursor = invites_db.cursor()
invites_cursor.execute('''
CREATE TABLE IF NOT EXISTS invites (
    user_id INTEGER PRIMARY KEY,
    points INTEGER NOT NULL
)
''')
invites_db.commit()

def get_invite_points(user_id):
    with invites_db_lock:
        row = invites_cursor.execute('SELECT points FROM invites WHERE user_id = ?', (user_id,)).fetchone()
        return row['points'] if row else 0

def set_invite_points(user_id, points):
    with invites_db_lock:
        if invites_cursor.execute('SELECT 1 FROM invites WHERE user_id = ?', (user_id,)).fetchone():
            invites_cursor.execute('UPDATE invites SET points = ? WHERE user_id = ?', (points, user_id))
        else:
            invites_cursor.execute('INSERT INTO invites (user_id, points) VALUES (?, ?)', (user_id, points))
        invites_db.commit()

def add_invite_points(user_id, points):
    current = get_invite_points(user_id)
    set_invite_points(user_id, current + points)

def remove_invite_points(user_id, points):
    current = get_invite_points(user_id)
    set_invite_points(user_id, max(0, current - points))

intents_inv = discord_inv.Intents.all()
bot_inv = commands_inv.Bot(command_prefix='inv!', intents=intents_inv)
data_file = 'invites.json'
if not os_inv.path.exists(data_file):
    with open(data_file, 'w') as f:
        json_inv.dump({}, f)
bot_inv.remove_command('help')

@bot_inv.command()
async def add(ctx, member: discord_inv.Member, points: int):
    add_invite_points(member.id, points)
    await ctx.send(f"✅ Added {points} points to {member.display_name}.")

@bot_inv.command()
async def remove(ctx, member: discord_inv.Member, points: int):
    remove_invite_points(member.id, points)
    await ctx.send(f"❌ Removed {points} points from {member.display_name}.")

@bot_inv.command()
async def lb(ctx):
    with invites_db_lock:
        rows = invites_cursor.execute('SELECT user_id, points FROM invites ORDER BY points DESC LIMIT 10').fetchall()
    if not rows:
        await ctx.send(embed=discord_inv.Embed(title="🏆 Invite Leaderboard", description="No invites yet!", color=0x00ff00))
        return
    desc = ""
    medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 7
    for i, row in enumerate(rows, start=1):
        user = await bot_inv.fetch_user(row['user_id'])
        medal = medals[i-1] if i <= len(medals) else "🏅"
        desc += f"{medal} **{user.display_name}** — `{row['points']} invites`\n"
    embed = discord_inv.Embed(title="🏆 Invite Leaderboard", description=desc, color=discord_inv.Color.gold())
    embed.set_footer(text="Top inviters this week!")
    await ctx.send(embed=embed)

def run_invites_bot():
    bot_inv.run(os.environ["INVITES_BOT_TOKEN"])

# ================== Ticket Bot ==================
import discord as discord_ticket
from discord.ext import commands as commands_ticket
from discord.ui import View as View_ticket, Button as Button_ticket, Select as Select_ticket
from collections import defaultdict as defaultdict_ticket
import sqlite3
# --- SQLite setup for Ticket Bot ---
ticket_db_lock = threading.Lock()
ticket_db = sqlite3.connect('tickets.db', check_same_thread=False)
ticket_db.row_factory = sqlite3.Row
ticket_cursor = ticket_db.cursor()
ticket_cursor.execute('''
CREATE TABLE IF NOT EXISTS tickets (
    ticket_id INTEGER PRIMARY KEY,
    creator_id INTEGER NOT NULL,
    staff_id INTEGER,
    status TEXT NOT NULL
)
''')
ticket_db.commit()

# --- SQLite setup for staff ratings ---
staff_ratings_db_lock = threading.Lock()
staff_ratings_cursor = ticket_db.cursor()
staff_ratings_cursor.execute('''
CREATE TABLE IF NOT EXISTS staff_ratings (
    staff_id INTEGER NOT NULL,
    rating INTEGER NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)
''')
ticket_db.commit()

# --- SQLite setup for vouches ---
vouch_db_lock = threading.Lock()
vouch_cursor = ticket_db.cursor()
vouch_cursor.execute('''
CREATE TABLE IF NOT EXISTS vouches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    staff_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    rating INTEGER NOT NULL,
    description TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)
''')
ticket_db.commit()

def add_staff_rating(staff_id, rating):
    with staff_ratings_db_lock:
        staff_ratings_cursor.execute('INSERT INTO staff_ratings (staff_id, rating) VALUES (?, ?)', (staff_id, rating))
        ticket_db.commit()

def get_staff_ratings(staff_id):
    with staff_ratings_db_lock:
        rows = staff_ratings_cursor.execute('SELECT rating FROM staff_ratings WHERE staff_id = ?', (staff_id,)).fetchall()
        return [row['rating'] for row in rows]

def count_five_star_ratings(staff_id):
    with staff_ratings_db_lock:
        row = staff_ratings_cursor.execute('SELECT COUNT(*) as count FROM staff_ratings WHERE staff_id = ? AND rating = 5', (staff_id,)).fetchone()
        return row['count'] if row else 0

intents_ticket = discord_ticket.Intents.all()
bot_ticket = commands_ticket.Bot(command_prefix="dio!", intents=intents_ticket)

bot_ticket.remove_command('help')

ticket_counter = 0
# --- SQLite helper functions for tickets ---
def get_ticket(ticket_id):
    with ticket_db_lock:
        row = ticket_cursor.execute('SELECT creator_id, staff_id, status FROM tickets WHERE ticket_id = ?', (ticket_id,)).fetchone()
        if row:
            return {'creator_id': row['creator_id'], 'staff_id': row['staff_id'], 'status': row['status']}
        else:
            return None

def create_ticket(ticket_id, creator_id):
    with ticket_db_lock:
        ticket_cursor.execute('INSERT OR REPLACE INTO tickets (ticket_id, creator_id, staff_id, status) VALUES (?, ?, ?, ?)', (ticket_id, creator_id, None, 'open'))
        ticket_db.commit()

def update_ticket_staff(ticket_id, staff_id):
    with ticket_db_lock:
        ticket_cursor.execute('UPDATE tickets SET staff_id = ? WHERE ticket_id = ?', (staff_id, ticket_id))
        ticket_db.commit()

def delete_ticket(ticket_id):
    with ticket_db_lock:
        ticket_cursor.execute('DELETE FROM tickets WHERE ticket_id = ?', (ticket_id,))
        ticket_db.commit()

staff_ratings = defaultdict_ticket(list)
CATEGORY_ID = 1397234544368685269
ALS_ROLE_ID = 1397023739631108188
ASTDX_ROLE_ID = 1382679356975087647
PROMOTION_ROLE_ID = 1397185106975920138
LOG_CHANNEL_ID = 1397579436274090035
STAFF_ROLE_ID = 1397186487044411522
class RatingButton(Button_ticket):
    def __init__(self, rating, staff_id, ticket_channel, rater_id):
        super().__init__(label=f"{rating} \u2b50", style=discord_ticket.ButtonStyle.secondary)
        self.rating = rating
        self.staff_id = staff_id
        self.ticket_channel = ticket_channel
        self.rater_id = rater_id
    async def callback(self, interaction: discord_ticket.Interaction):
        if self.staff_id:
            add_staff_rating(self.staff_id, self.rating)
            await interaction.response.send_message(f"\u2705 You rated {self.rating} stars!", ephemeral=True)
            log_channel = bot_ticket.get_channel(LOG_CHANNEL_ID)
            if log_channel:
                rater = interaction.guild.get_member(self.rater_id)
                staff = interaction.guild.get_member(self.staff_id)
                await log_channel.send(
                    f"\u2b50 **Rating**: `{self.rating} stars`\n\ud83d\udc64 From: {rater.mention}\n\ud83c\udfaf To: {staff.mention}")
            guild = interaction.guild
            staff_member = guild.get_member(self.staff_id)
            if staff_member and self.rating == 5:
                if count_five_star_ratings(self.staff_id) == 15:
                    role = guild.get_role(PROMOTION_ROLE_ID)
                    if role and role not in staff_member.roles:
                        await staff_member.add_roles(role)
                        await log_channel.send(f"\ud83c\udf89 {staff_member.mention} has been promoted with 15 five-star ratings!")
            await self.ticket_channel.delete()
class RatingView(View_ticket):
    def __init__(self, staff_id, ticket_channel, rater_id):
        super().__init__(timeout=60)
        for i in range(1, 6):
            self.add_item(RatingButton(i, staff_id, ticket_channel, rater_id))
class DeleteTicketButton(Button_ticket):
    def __init__(self, creator_id):
        super().__init__(label="\ud83d\uddd1\ufe0f Delete Ticket", style=discord_ticket.ButtonStyle.danger)
        self.creator_id = creator_id
    async def callback(self, interaction: discord_ticket.Interaction):
        ticket_data = get_ticket(interaction.channel.id)
        if not ticket_data:
            await interaction.response.send_message("\u274c This ticket does not exist or is already closed.", ephemeral=True)
            return
        if interaction.user.id != ticket_data['creator_id']:
            await interaction.response.send_message("\u274c Only the ticket creator can delete this ticket.", ephemeral=True)
            return
        delete_ticket(interaction.channel.id)
        await interaction.response.send_message("\ud83d\uddd1\ufe0f Ticket deleted.", ephemeral=True)
        await interaction.channel.delete()
        staff_id = ticket_data['staff_id']
        if staff_id:
            staff_member = interaction.guild.get_member(staff_id)
            if staff_member:
                view = VouchView([staff_member], interaction.user.id)
                try:
                    await interaction.user.send("Would you like to vouch for the staff who helped you?", view=view)
                except Exception:
                    pass  # User may have DMs closed

class TakeRequestButton(Button_ticket):
    def __init__(self, creator_id):
        super().__init__(label="\ud83c\udfaf Take Request", style=discord_ticket.ButtonStyle.primary)
        self.creator_id = creator_id
    async def callback(self, interaction: discord_ticket.Interaction):
        ticket_data = get_ticket(interaction.channel.id)
        if not ticket_data:
            await interaction.response.send_message("\u26a0\ufe0f Internal error.", ephemeral=True)
            return
        if ticket_data["staff_id"] is not None:
            await interaction.response.send_message("\u274c This request has already been taken.", ephemeral=True)
            return
        if interaction.user.id == ticket_data["creator_id"]:
            await interaction.response.send_message("\u274c You cannot take your own request.", ephemeral=True)
            return
        update_ticket_staff(interaction.channel.id, interaction.user.id)
        await interaction.channel.send(f"\u2705 This request has been taken by {interaction.user.mention}.")
        self.disabled = True
        await interaction.message.edit(view=self.view)
        await interaction.response.send_message("\ud83c\udfaf You claimed this request!", ephemeral=True)
class TicketTypeSelect(Select_ticket):
    def __init__(self):
        options = [
            discord_ticket.SelectOption(label="ALS", description="Open a ticket for ALS Staff"),
            discord_ticket.SelectOption(label="ASTDX", description="Open a ticket for ASTDX Staffs")
        ]
        super().__init__(placeholder="Ticket Selector", options=options)
    async def callback(self, interaction: discord_ticket.Interaction):
        global ticket_counter
        ticket_counter += 1
        ticket_type = self.values[0].lower()
        ticket_name = f"{ticket_type}-ticket-{ticket_counter:04}"
        guild = interaction.guild
        category = guild.get_channel(CATEGORY_ID)
        helpers_role = guild.get_role(STAFF_ROLE_ID)
        overwrites = {
            guild.default_role: discord_ticket.PermissionOverwrite(read_messages=False),
            interaction.user: discord_ticket.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True, embed_links=True),
            helpers_role: discord_ticket.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        ticket_channel = await guild.create_text_channel(ticket_name, overwrites=overwrites, category=category)
        create_ticket(ticket_channel.id, interaction.user.id)
        view = View_ticket()
        view.add_item(TakeRequestButton(interaction.user.id))
        view.add_item(DeleteTicketButton(interaction.user.id))
        role_id = ALS_ROLE_ID if ticket_type == "als" else ASTDX_ROLE_ID
        staff_role = guild.get_role(role_id)
        await ticket_channel.send(f"{interaction.user.mention} has opened a **{ticket_type.upper()}** support ticket!\n{staff_role.mention if staff_role else ''}", view=view)
        await interaction.response.send_message(f"\u2705 Your ticket has been created: {ticket_channel.mention}", ephemeral=True)
        self.view.clear_items()
        self.view.add_item(TicketTypeSelect())
        await interaction.message.edit(view=self.view)
class TicketBoardView(View_ticket):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketTypeSelect())
@bot_ticket.command()
async def ticketboard(ctx):
    view = TicketBoardView()
    await ctx.send("\ud83c\udfab Select a ticket type below:", view=view)
@bot_ticket.command()
async def staffratings(ctx):
    if not get_staff_ratings(ctx.author.id):
        await ctx.send("No ratings yet.")
        return
    embed = discord_ticket.Embed(title="\u2b50 Staff Ratings", color=discord_ticket.Color.green())
    for staff_id, ratings in get_staff_ratings(ctx.author.id):
        user = await bot_ticket.fetch_user(staff_id)
        avg = sum(ratings) / len(ratings)
        embed.add_field(name=f"{user}", value=f"{len(ratings)} ratings | Avg: {avg:.2f}\u2b50", inline=False)
    await ctx.send(embed=embed)

# --- Discord UI for Vouching ---
class VouchModal(discord_ticket.ui.Modal, title="Vouch Description"):
    def __init__(self, staff_id, user_id, rating, on_submit_callback):
        super().__init__()
        self.staff_id = staff_id
        self.user_id = user_id
        self.rating = rating
        self.on_submit_callback = on_submit_callback
        self.description = discord_ticket.ui.TextInput(label="Describe your experience", style=discord_ticket.TextStyle.paragraph, required=False, max_length=500)
        self.add_item(self.description)

    async def on_submit(self, interaction: discord_ticket.Interaction):
        await self.on_submit_callback(interaction, self.staff_id, self.user_id, self.rating, self.description.value)

class VouchView(discord_ticket.ui.View):
    def __init__(self, staff_members, user_id):
        super().__init__(timeout=120)
        self.staff_members = staff_members
        self.user_id = user_id
        self.selected_staff_id = None
        self.selected_rating = None
        self.add_item(self.StaffSelect(staff_members, self))
        self.add_item(self.StarSelect(self))
        self.add_item(self.VouchButton(self))

    class StaffSelect(discord_ticket.ui.Select):
        def __init__(self, staff_members, parent_view):
            options = [discord_ticket.SelectOption(label=member.display_name, value=str(member.id)) for member in staff_members]
            super().__init__(placeholder="Select staff to vouch for", options=options, min_values=1, max_values=1)
            self.parent_view = parent_view
        async def callback(self, interaction: discord_ticket.Interaction):
            self.parent_view.selected_staff_id = int(self.values[0])
            await interaction.response.send_message(f"Selected staff: <@{self.values[0]}>", ephemeral=True)

    class StarSelect(discord_ticket.ui.Select):
        def __init__(self, parent_view):
            options = [discord_ticket.SelectOption(label=f"{i} ⭐", value=str(i)) for i in range(1, 6)]
            super().__init__(placeholder="Select rating (1-5 stars)", options=options, min_values=1, max_values=1)
            self.parent_view = parent_view
        async def callback(self, interaction: discord_ticket.Interaction):
            self.parent_view.selected_rating = int(self.values[0])
            await interaction.response.send_message(f"Selected rating: {self.values[0]} ⭐", ephemeral=True)

    class VouchButton(discord_ticket.ui.Button):
        def __init__(self, parent_view):
            super().__init__(label="Submit Vouch", style=discord_ticket.ButtonStyle.success)
            self.parent_view = parent_view
        async def callback(self, interaction: discord_ticket.Interaction):
            if not self.parent_view.selected_staff_id or not self.parent_view.selected_rating:
                await interaction.response.send_message("Please select a staff member and a rating before submitting.", ephemeral=True)
                return
            modal = VouchModal(self.parent_view.selected_staff_id, self.parent_view.user_id, self.parent_view.selected_rating, on_submit_callback=handle_vouch_submit)
            await interaction.response.send_modal(modal)

async def handle_vouch_submit(interaction, staff_id, user_id, rating, description):
    with vouch_db_lock:
        vouch_cursor.execute('INSERT INTO vouches (staff_id, user_id, rating, description) VALUES (?, ?, ?, ?)', (staff_id, user_id, rating, description))
        ticket_db.commit()
    msg = f"Thank you for vouching for <@{staff_id}>!"
    if description and description.strip():
        msg += f"\nYour feedback: {description.strip()}"
    await interaction.response.send_message(msg, ephemeral=True)
    # Send to ratings log channel
    log_channel = interaction.client.get_channel(LOG_CHANNEL_ID)
    if log_channel:
        staff_mention = f"<@{staff_id}>"
        user_mention = f"<@{user_id}>"
        embed = discord_ticket.Embed(title="New Vouch Received", color=discord_ticket.Color.gold())
        embed.add_field(name="Staff", value=staff_mention, inline=True)
        embed.add_field(name="User", value=user_mention, inline=True)
        embed.add_field(name="Rating", value=f"{rating} ⭐", inline=True)
        if description and description.strip():
            embed.add_field(name="Feedback", value=description.strip(), inline=False)
        await log_channel.send(embed=embed)

# --- Trigger VouchView after ticket deletion if staff handled ---
# In DeleteTicketButton.callback, after deleting the ticket, if a staff_id exists, show the VouchView to the user.
# Example:
# staff_id = ticket_data['staff_id']
# if staff_id:
#     staff_member = interaction.guild.get_member(staff_id)
#     if staff_member:
#         view = VouchView([staff_member], interaction.user.id)
#         await interaction.channel.send("Would you like to vouch for the staff who helped you?", view=view)

# --- Ticket Bot Help Command ---
@bot_ticket.command()
async def help(ctx):
    embed = discord_ticket.Embed(title="Ticket Bot Commands", color=discord_ticket.Color.green())
    embed.add_field(name="dio!ticketboard", value="Open the ticket board to create a ticket.", inline=False)
    embed.add_field(name="dio!staffratings", value="Show staff ratings.", inline=False)
    await ctx.send(embed=embed)

class VouchPaginationView(discord_ticket.ui.View):
    def __init__(self, ctx, user=None, total=0, page=1, per_page=10, all_vouches=False):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.user = user
        self.page = page
        self.per_page = per_page
        self.total = total
        self.all_vouches = all_vouches  # <-- Ensure this is always set
        self.total_pages = (total + per_page - 1) // per_page
        self.update_buttons()

    def update_buttons(self):
        self.clear_items()
        if self.page > 1:
            self.add_item(self.PrevButton(self))
        if self.page < self.total_pages:
            self.add_item(self.NextButton(self))

    class PrevButton(discord_ticket.ui.Button):
        def __init__(self, parent):
            super().__init__(label="Previous", style=discord_ticket.ButtonStyle.primary)
            self.parent = parent
        async def callback(self, interaction):
            self.parent.page -= 1
            await self.parent.update(interaction)

    class NextButton(discord_ticket.ui.Button):
        def __init__(self, parent):
            super().__init__(label="Next", style=discord_ticket.ButtonStyle.primary)
            self.parent = parent
        async def callback(self, interaction):
            self.parent.page += 1
            await self.parent.update(interaction)

    async def update(self, interaction):
        self.update_buttons()
        if self.all_vouches:
            embed = await get_allvouches_embed(self.ctx, self.page, self.per_page)
        else:
            embed = await get_vouches_embed(self.ctx, self.user, self.page, self.per_page)
        await interaction.response.edit_message(embed=embed, view=self)

async def get_vouches_embed(ctx, user, page, per_page):
    offset = (page - 1) * per_page
    with vouch_db_lock:
        total = vouch_cursor.execute('SELECT COUNT(*) FROM vouches WHERE user_id = ?', (user.id,)).fetchone()[0]
        rows = vouch_cursor.execute('SELECT staff_id, rating, description, timestamp FROM vouches WHERE user_id = ? ORDER BY timestamp DESC LIMIT ? OFFSET ?', (user.id, per_page, offset)).fetchall()
    embed = discord_ticket.Embed(title=f"🌟 Vouches by {user.display_name}", color=discord_ticket.Color.blurple())
    for row in rows:
        staff_member = ctx.guild.get_member(row['staff_id'])
        staff_name = staff_member.display_name if staff_member else f"ID:{row['staff_id']}"
        desc = row['description'] if row['description'] else 'No feedback.'
        embed.add_field(
            name=f"**🕒 {row['timestamp']}**\n👤 **Staff:** `{staff_name}`\n⭐ **Rating:** `{row['rating']} / 5`",
            value=f"💬 **Feedback:** {desc}\n\u200b",
            inline=False
        )
    total_pages = (total + per_page - 1) // per_page
    embed.set_footer(text=f"Page {page}/{total_pages} | Total vouches: {total}")
    return embed

async def get_allvouches_embed(ctx, page, per_page):
    offset = (page - 1) * per_page
    with vouch_db_lock:
        total = vouch_cursor.execute('SELECT COUNT(*) FROM vouches').fetchone()[0]
        rows = vouch_cursor.execute('SELECT staff_id, user_id, rating, description, timestamp FROM vouches ORDER BY timestamp DESC LIMIT ? OFFSET ?', (per_page, offset)).fetchall()
    embed = discord_ticket.Embed(title="🌟 All Vouches", color=discord_ticket.Color.green())
    for row in rows:
        staff_member = ctx.guild.get_member(row['staff_id'])
        user_member = ctx.guild.get_member(row['user_id'])
        staff_name = staff_member.display_name if staff_member else f"ID:{row['staff_id']}"
        user_name = user_member.display_name if user_member else f"ID:{row['user_id']}"
        desc = row['description'] if row['description'] else 'No feedback.'
        embed.add_field(
            name=f"**🕒 {row['timestamp']}**\n👤 **Staff:** `{staff_name}`\n🙍 **User:** `{user_name}`\n⭐ **Rating:** `{row['rating']} / 5`",
            value=f"💬 **Feedback:** {desc}\n\u200b",
            inline=False
        )
    total_pages = (total + per_page - 1) // per_page
    embed.set_footer(text=f"Page {page}/{total_pages} | Total vouches: {total}")
    return embed

@bot_ticket.command()
async def vouches(ctx, user: discord_ticket.Member = None, page: int = 1):
    user = user or ctx.author
    per_page = 10
    offset = (page - 1) * per_page
    with vouch_db_lock:
        total = vouch_cursor.execute('SELECT COUNT(*) FROM vouches WHERE user_id = ?', (user.id,)).fetchone()[0]
        rows = vouch_cursor.execute('SELECT staff_id, rating, description, timestamp FROM vouches WHERE user_id = ? ORDER BY timestamp DESC LIMIT ? OFFSET ?', (user.id, per_page, offset)).fetchall()
    if not rows:
        await ctx.send(f"No vouches found for {user.mention} on page {page}.")
        return
    embed = await get_vouches_embed(ctx, user, page, per_page)
    view = VouchPaginationView(ctx, user=user, total=total, page=page, per_page=per_page, all_vouches=False)
    await ctx.send(embed=embed, view=view)

@bot_ticket.command()
async def allvouches(ctx, page: int = 1):
    per_page = 5
    offset = (page - 1) * per_page
    with vouch_db_lock:
        total = vouch_cursor.execute('SELECT COUNT(*) FROM vouches').fetchone()[0]
        rows = vouch_cursor.execute('SELECT staff_id, user_id, rating, description, timestamp FROM vouches ORDER BY timestamp DESC LIMIT ? OFFSET ?', (per_page, offset)).fetchall()
    if not rows:
        await ctx.send(f"No vouches found in the database on page {page}.")
        return
    embed = await get_allvouches_embed(ctx, page, per_page)
    view = VouchPaginationView(ctx, total=total, page=page, per_page=per_page, all_vouches=True)
    await ctx.send(embed=embed, view=view)

def run_ticket_bot():
    bot_ticket.run(os.environ["TICKET_BOT_TOKEN"])

# ================== Music Bot ==================
import discord as discord_music
from discord.ext import commands as commands_music

intents_music = discord_music.Intents.default()
intents_music.message_content = True
intents_music.voice_states = True

bot_music = commands_music.Bot(command_prefix='?', intents=intents_music)

guild_id = None  # Set your server's guild ID here for faster slash command registration

# Add a global variable to track the current song info
current_song = {}

@bot_music.event
async def on_ready():
    print(f'Music Bot logged in as {bot_music.user}')
    try:
        synced = await bot_music.tree.sync(guild=discord_music.Object(id=guild_id)) if guild_id else await bot_music.tree.sync()
        print(f'Music Bot synced {len(synced)} command(s)')
    except Exception as e:
        print(f'Error syncing music bot commands: {e}')

@bot_music.command(name='music-play', help='Play music by title or YouTube link')
async def music_play(ctx, *, query: str):
    global current_song
    user = ctx.author
    voice_state = user.voice
    if not voice_state or not voice_state.channel:
        await ctx.send('❌ Please join a voice channel first!')
        return

    channel = voice_state.channel
    # Connect to voice channel if not already connected
    if ctx.voice_client is None:
        try:
            vc = await channel.connect()
        except Exception as e:
            await ctx.send(f'❌ Could not join voice channel: {e}')
            return
    else:
        vc = ctx.voice_client
        if vc.channel != channel:
            await vc.move_to(channel)

    await ctx.send(f'🔍 Searching for: {query}')

    # Always search YouTube with the user query
    search_opts = {
        'format': 'bestaudio/best',
        'noplaylist': True,
        'default_search': 'ytsearch',
        'quiet': True,
        'extract_flat': 'True',
    }
    print(f"yt_query passed to yt-dlp: {query}")
    with yt_dlp.YoutubeDL(search_opts) as ydl:
        try:
            info = ydl.extract_info(query, download=False)
            if 'entries' in info:
                info = info['entries'][0]
            video_url = info['url'] if 'url' in info else info['webpage_url']
            title = info.get('title', 'Unknown Title')
            webpage_url = info.get('webpage_url', video_url)
            thumbnail = info.get('thumbnail', None)
        except Exception as e:
            await ctx.send(f'❌ Could not find or play "{query}": {e}')
            return

    audio_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
    }
    with yt_dlp.YoutubeDL(audio_opts) as ydl:
        try:
            audio_info = ydl.extract_info(video_url, download=False)
            audio_url = audio_info['url']
        except Exception as e:
            await ctx.send(f'❌ Could not extract audio: {e}')
            return

    ffmpeg_options = {
        'options': '-vn',
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'
    }
    try:
        audio_source = await discord_music.FFmpegOpusAudio.from_probe(audio_url, **ffmpeg_options)
    except Exception as e:
        await ctx.send(f'❌ Error preparing audio: {e}')
        return

    try:
        if vc.is_playing():
            vc.stop()
        vc.play(audio_source)
    except Exception as e:
        await ctx.send(f'❌ Error playing audio: {e}')
        return

    # Track current song info
    current_song[ctx.guild.id] = {
        'title': title,
        'webpage_url': webpage_url,
        'thumbnail': thumbnail,
        'requester': user.display_name,
        'requester_avatar': user.display_avatar.url
    }

    embed = discord_music.Embed(title='Now Playing', description=f'[{title}]({webpage_url})', color=0x1DB954)
    if thumbnail:
        embed.set_thumbnail(url=thumbnail)
    embed.set_footer(text=f'Requested by {user.display_name}', icon_url=user.display_avatar.url)
    await ctx.send(embed=embed)

@bot_music.command(name='music-help', help='Show help for music commands')
async def music_help(ctx):
    embed = discord_music.Embed(title='Music Bot Help', color=0x1DB954)
    embed.add_field(name='?music-play [title or link]', value='Play a song by title or link.', inline=False)
    embed.add_field(name='?music-skip', value='Skip the current song.', inline=False)
    embed.add_field(name='?music-pause', value='Pause the current song.', inline=False)
    embed.add_field(name='?music-resume', value='Resume playback.', inline=False)
    embed.add_field(name='?music-stop', value='Stop playback and clear the queue.', inline=False)
    embed.add_field(name='?music-nowplaying', value='Show info about the currently playing song.', inline=False)
    embed.set_footer(text='Use ?music-play to get started!')
    await ctx.send(embed=embed)

@bot_music.command(name='music-skip', help='Skip the current song.')
async def music_skip(ctx):
    vc = ctx.voice_client
    if vc and vc.is_playing():
        vc.stop()
        await ctx.send('⏭️ Skipped the current song.')
    else:
        await ctx.send('❌ No song is currently playing.')

@bot_music.command(name='music-pause', help='Pause the current song.')
async def music_pause(ctx):
    vc = ctx.voice_client
    if vc and vc.is_playing():
        vc.pause()
        await ctx.send('⏸️ Paused the current song.')
    else:
        await ctx.send('❌ No song is currently playing.')

@bot_music.command(name='music-resume', help='Resume playback.')
async def music_resume(ctx):
    vc = ctx.voice_client
    if vc and vc.is_paused():
        vc.resume()
        await ctx.send('▶️ Resumed playback.')
    else:
        await ctx.send('❌ No song is currently paused.')

@bot_music.command(name='music-stop', help='Stop playback and clear the queue.')
async def music_stop(ctx):
    vc = ctx.voice_client
    if vc:
        await vc.disconnect()
        current_song.pop(ctx.guild.id, None)
        await ctx.send('⏹️ Stopped playback and disconnected.')
    else:
        await ctx.send('❌ I am not connected to a voice channel.')

@bot_music.command(name='music-nowplaying', help='Show info about the currently playing song.')
async def music_nowplaying(ctx):
    song = current_song.get(ctx.guild.id)
    if song:
        embed = discord_music.Embed(title='Now Playing', description=f'[{song["title"]}]({song["webpage_url"]})', color=0x1DB954)
        if song['thumbnail']:
            embed.set_thumbnail(url=song['thumbnail'])
        embed.set_footer(text=f'Requested by {song["requester"]}', icon_url=song['requester_avatar'])
        await ctx.send(embed=embed)
    else:
        await ctx.send('❌ No song is currently playing.')

def run_music_bot():
    bot_music.run(os.environ["MUSIC_BOT_TOKEN"])

# ================== Start All Bots ==================
if __name__ == "__main__":
    threads = [
        threading.Thread(target=run_application_bot),
        threading.Thread(target=run_giveaway_bot),
        threading.Thread(target=run_invites_bot),
        threading.Thread(target=run_ticket_bot),
        threading.Thread(target=run_music_bot),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()


# ================== Start All Bots ==================