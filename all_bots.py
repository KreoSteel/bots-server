import threading
import os
import sys
from dotenv import load_dotenv
import yt_dlp
import asyncio

last_ticketboard_message = None
load_dotenv()

# Validate required environment variables
required_tokens = [
    "APP_BOT_TOKEN",
    "GIVEAWAY_BOT_TOKEN",
    "INVITES_BOT_TOKEN",
    "TICKET_BOT_TOKEN",
    "MUSIC_BOT_TOKEN"
]

missing_tokens = [token for token in required_tokens if not os.getenv(token)]
if missing_tokens:
    print(f"❌ Missing required environment variables: {', '.join(missing_tokens)}")
    print("Please create a .env file with all required bot tokens.")
    sys.exit(1)

# Validate voice dependencies
try:
    import nacl
    print("✅ PyNaCl is installed")
except ImportError:
    print("❌ PyNaCl is not installed. Please run: pip install PyNaCl")
    print("Voice functionality will not work without PyNaCl.")
    sys.exit(1)

# Check for FFmpeg
try:
    import subprocess
    result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True)
    if result.returncode == 0:
        print("✅ FFmpeg is available")
    else:
        print("⚠️  FFmpeg not found. Voice functionality may not work properly.")
        print("Please install FFmpeg: https://ffmpeg.org/download.html")
except FileNotFoundError:
    print("⚠️  FFmpeg not found. Voice functionality may not work properly.")
    print("Please install FFmpeg: https://ffmpeg.org/download.html")

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
        # view.add_item(DeleteTicketButton(channel, user))  # Removed as requested
        staff_controls_msg = await channel.send("Staff controls:", view=view)

        # Remove ticket buttons after 1 minute (delete the message)
        async def remove_ticket_buttons_later(message, delay=60):
            await asyncio.sleep(delay)
            try:
                await message.delete()
            except Exception:
                pass  # Message might be deleted already
        # Schedule the task in the background (non-blocking, safe inside async function)
        asyncio.create_task(remove_ticket_buttons_later(staff_controls_msg))

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

@bot_app.event
async def on_ready():
    print(f"bot_app is online! Username: {bot_app.user} (ID: {bot_app.user.id})")

def run_application_bot():
    try:
        print("🚀 Starting Application Bot...")
        bot_app.run(os.environ["APP_BOT_TOKEN"])
    except Exception as e:
        print(f"❌ Application Bot failed to start: {e}")

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
    try:
        print("🎁 Starting Giveaway Bot...")
        bot_give.run(os.environ["GIVEAWAY_BOT_TOKEN"])
    except Exception as e:
        print(f"❌ Giveaway Bot failed to start: {e}")

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
import collections
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

# --- Invite Cache for Tracking ---
invite_cache = {}

intents_inv = discord_inv.Intents.all()
bot_inv = commands_inv.Bot(command_prefix='inv!', intents=intents_inv)
data_file = 'invites.json'
if not os_inv.path.exists(data_file):
    with open(data_file, 'w') as f:
        json_inv.dump({}, f)
bot_inv.remove_command('help')

@bot_inv.event
async def on_ready():
    print(f"Logged in as {bot_inv.user} (Invite Tracker)")
    for guild in bot_inv.guilds:
        invites = await guild.invites()
        invite_cache[guild.id] = {invite.code: invite.uses for invite in invites}

@bot_inv.event
async def on_guild_join(guild):
    invites = await guild.invites()
    invite_cache[guild.id] = {invite.code: invite.uses for invite in invites}

@bot_inv.event
async def on_member_join(member):
    guild = member.guild
    before = invite_cache.get(guild.id, {})
    invites = await guild.invites()
    invite_cache[guild.id] = {invite.code: invite.uses for invite in invites}
    used_code = None
    inviter_id = None
    for invite in invites:
        if invite.code in before and invite.uses > before[invite.code]:
            used_code = invite.code
            inviter_id = invite.inviter.id if invite.inviter else None
            break
        elif invite.code not in before and invite.uses > 0:
            used_code = invite.code
            inviter_id = invite.inviter.id if invite.inviter else None
            break
    # Handle vanity URL
    if not used_code and guild.vanity_url_code:
        vanity = await guild.vanity_invite()
        if vanity and vanity.uses > before.get('vanity', 0):
            used_code = 'vanity'
            inviter_id = None  # Can't track inviter for vanity
    if inviter_id:
        add_invite_points(inviter_id, 1)

@bot_inv.event
async def on_member_remove(member):
    # Try to detect who invited this member (optional: store joiner->inviter mapping for accuracy)
    # For now, just check invites again and update cache
    guild = member.guild
    invites = await guild.invites()
    invite_cache[guild.id] = {invite.code: invite.uses for invite in invites}
    # If you want to subtract from inviter, you need to store joiner->inviter mapping on join
    # (not implemented here, but can be added if needed)
    # For now, this will not subtract points unless you want to implement joiner->inviter mapping.
    pass

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
    try:
        print("📨 Starting Invites Bot...")
        bot_inv.run(os.environ["INVITES_BOT_TOKEN"])
    except Exception as e:
        print(f"❌ Invites Bot failed to start: {e}")

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

# --- SQLite setup for vouches (using ticket_db) ---
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

# Persistent view for ticket controls
class PersistentTicketView(View_ticket):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(CloseTicketButton("persistent"))
        self.add_item(DeleteTicketButton("persistent"))

# Update CloseTicketButton and DeleteTicketButton to use static custom_id for persistence
class CloseTicketButton(Button_ticket):
    def __init__(self, creator_id):
        super().__init__(label="🔒 Close Ticket", style=discord_ticket.ButtonStyle.secondary, custom_id=f"close_ticket:{creator_id}")
        self.creator_id = creator_id
    async def callback(self, interaction: discord_ticket.Interaction):
        ticket_data = get_ticket(interaction.channel.id)
        if not ticket_data:
            await interaction.response.send_message("⚠️ Internal error.", ephemeral=True)
            return
        if interaction.user.id != ticket_data["creator_id"]:
            await interaction.response.send_message("❌ Only the ticket creator can close this ticket.", ephemeral=True)
            return
        # Edit the message to show only the persistent DeleteTicketButton
        view = PersistentTicketView()
        view.clear_items()
        view.add_item(DeleteTicketButton("persistent"))
        await interaction.message.edit(view=view)
        await interaction.response.send_message("🔒 Ticket closed! You can now delete it.", ephemeral=True)

# --- Persistent DeleteTicketButton for Ticket Bot ---
class DeleteTicketButton(Button_ticket):
    def __init__(self, creator_id):
        super().__init__(label="\U0001f5d1\ufe0f Delete Ticket", style=discord_ticket.ButtonStyle.danger, custom_id=f"delete_ticket:{creator_id}")
        self.creator_id = creator_id

# --- Persistent TakeRequestButton for Ticket Bot ---
class TakeRequestButton(Button_ticket):
    def __init__(self, creator_id):
        super().__init__(label="\U0001f3af Take Request", style=discord_ticket.ButtonStyle.primary, custom_id=f"take_request:{creator_id}")
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
        # Disable the button in the view
        view = await interaction.message.view.from_message(interaction.message)
        for item in view.children:
            if isinstance(item, TakeRequestButton):
                item.disabled = True
        await interaction.message.edit(view=view)
        await interaction.response.send_message("\U0001f3af You claimed this request!", ephemeral=True)

# --- Persistent View Registration ---
@bot_ticket.event
async def on_ready():
    print(f"bot_ticket is online! Username: {bot_ticket.user} (ID: {bot_ticket.user.id})")
    # Register persistent views for TakeRequestButton and DeleteTicketButton
    class PersistentTicketView(View_ticket):
        def __init__(self):
            super().__init__(timeout=None)
            self.add_item(TakeRequestButton("persistent"))
            self.add_item(DeleteTicketButton("persistent"))
    bot_ticket.add_view(PersistentTicketView())

# --- Global handler for persistent DeleteTicketButton ---
@bot_ticket.event
async def on_interaction(interaction: discord_ticket.Interaction):
    # Only handle component interactions
    if not interaction.type.name == "component":
        return
    # Handle persistent DeleteTicketButton
    if interaction.data.get("custom_id", "").startswith("delete_ticket:"):
        ticket_data = get_ticket(interaction.channel.id)
        if not ticket_data:
            await interaction.response.send_message("\u274c This ticket does not exist or is already closed.", ephemeral=True)
            return
        if interaction.user.id != ticket_data['creator_id']:
            await interaction.response.send_message("\u274c Only the ticket creator can delete this ticket.", ephemeral=True)
            return
        delete_ticket(interaction.channel.id)
        await interaction.response.send_message("\U0001f5d1\ufe0f Ticket deleted.", ephemeral=True)
        await interaction.channel.delete()
        staff_id = ticket_data['staff_id']
        if staff_id:
            staff_member = None
            for g in bot_ticket.guilds:
                staff_member = g.get_member(staff_id)
                if staff_member:
                    break
            if staff_member:
                view = VouchView([staff_member], interaction.user.id)
                try:
                    await interaction.user.send("Would you like to vouch for the staff who helped you?", view=view)
                except Exception:
                    pass  # User may have DMs closed

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
        super().__init__(timeout=None)
        for i in range(1, 6):
            self.add_item(RatingButton(i, staff_id, ticket_channel, rater_id))

# --- Vouch Submit Handler ---
async def handle_vouch_submit(interaction, staff_id, user_id, rating, description):
    await interaction.response.send_message(
        f"Thank you for your vouch!\nStaff: <@{staff_id}>\nRating: {rating} stars\nDescription: {description}",
        ephemeral=True
    )
    # Save the vouch to the database (thread-safe)
    with vouch_db_lock:
        vouch_cursor.execute(
            'INSERT INTO vouches (staff_id, user_id, rating, description) VALUES (?, ?, ?, ?)',
            (staff_id, user_id, rating, description)
        )
        ticket_db.commit()
    # Try to get the guild from the bot's cache (since interaction.guild may be None in DMs)
    guild = None
    for g in bot_ticket.guilds:
        if g.get_member(staff_id):
            guild = g
            break
    log_channel = bot_ticket.get_channel(LOG_CHANNEL_ID)
    if log_channel and guild:
        user = guild.get_member(user_id)
        staff = guild.get_member(staff_id)
        await log_channel.send(
            f"📝 **Vouch Submitted**\nStaff: {staff.mention if staff else staff_id}\nFrom: {user.mention if user else user_id}\nRating: {rating} stars\nDescription: {description if description else 'No description.'}"
        )

# --- Vouch Pagination View ---
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
        super().__init__(timeout=None)
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
            super().__init__(placeholder="Select staff to vouch for", options=options, min_values=1, max_values=1, custom_id="vouch_staff_select")
            self.parent_view = parent_view
        async def callback(self, interaction: discord_ticket.Interaction):
            self.parent_view.selected_staff_id = int(self.values[0])
            await interaction.response.send_message(f"Selected staff: <@{self.values[0]}>", ephemeral=True)

    class StarSelect(discord_ticket.ui.Select):
        def __init__(self, parent_view):
            options = [discord_ticket.SelectOption(label=f"{i} ⭐", value=str(i)) for i in range(1, 6)]
            super().__init__(placeholder="Select rating (1-5 stars)", options=options, min_values=1, max_values=1, custom_id="vouch_star_select")
            self.parent_view = parent_view
        async def callback(self, interaction: discord_ticket.Interaction):
            self.parent_view.selected_rating = int(self.values[0])
            await interaction.response.send_message(f"Selected rating: {self.values[0]} ⭐", ephemeral=True)

    class VouchButton(discord_ticket.ui.Button):
        def __init__(self, parent_view):
            super().__init__(label="Submit Vouch", style=discord_ticket.ButtonStyle.success, custom_id="vouch_submit")
            self.parent_view = parent_view

        async def callback(self, interaction: discord_ticket.Interaction):
            if not self.parent_view.selected_staff_id or not self.parent_view.selected_rating:
                await interaction.response.send_message("Please select a staff member and a rating before submitting.", ephemeral=True)
                return
            modal = VouchModal(
                self.parent_view.selected_staff_id,
                self.parent_view.user_id,
                self.parent_view.selected_rating,
                on_submit_callback=handle_vouch_submit
            )
            await interaction.response.send_modal(modal)

# Add the dio!vouch command ---
@bot_ticket.command(name="vouch")
async def vouch(ctx):
    print("vouch command triggered")
    # Try to get all staff members from the guild
    staff_role = ctx.guild.get_role(STAFF_ROLE_ID)
    if staff_role:
        staff_members = staff_role.members
    else:
        staff_members = []
    if not staff_members:
        await ctx.send("No staff members found to vouch for.", ephemeral=True)
        return
    view = VouchView(staff_members, ctx.author.id)
    try:
        await ctx.author.send("Would you like to vouch for the staff who helped you?", view=view)
        await ctx.send("Check your DMs to submit a vouch!", ephemeral=True)
    except Exception:
        await ctx.send("Could not send you a DM. Please check your privacy settings.", ephemeral=True)

# Debug command to list all loaded commands
@bot_ticket.command(name="commandsdebug")
async def commandsdebug(ctx):
    cmds = [c.name for c in bot_ticket.commands]
    await ctx.send(f"Loaded commands: {cmds}")

# --- Command to View Vouches ---
# @bot_ticket.command(name="vouches") # This command is now handled by the new dio!vouches command
# async def vouches(ctx, member: discord_ticket.Member = None):
#     if member:
#         rows = vouch_cursor.execute(
#             'SELECT * FROM vouches WHERE staff_id = ? ORDER BY timestamp DESC LIMIT 10',
#             (member.id,)
#         ).fetchall()
#         title = f"Vouches for {member.display_name}"
#     else:
#         rows = vouch_cursor.execute(
#             'SELECT * FROM vouches ORDER BY timestamp DESC LIMIT 10'
#         ).fetchall()
#         title = "Recent Vouches"
#     if not rows:
#         await ctx.send("No vouches found.")
#         return
#     embed = discord_ticket.Embed(title=title, color=0x00ff00)
#     for row in rows:
#         user = ctx.guild.get_member(row['user_id'])
#         embed.add_field(
#             name=f"{row['rating']}⭐ from {user.display_name if user else row['user_id']}",
#             value=row['description'] or "No description.",
#             inline=False
#         )
#     await ctx.send(embed=embed)

# --- Make all interactive ticket bot UI persistent ---
# 1. All Views (VouchView, VouchPaginationView, RatingView, TicketBoardView, etc.) should have timeout=None.
# 2. All Buttons and Selects must have a custom_id.
# 3. Register all persistent views in on_ready.
# 4. Add global on_interaction handlers for all persistent custom_ids.

# --- Persistent VouchPaginationView ---
class VouchPaginationView(discord_ticket.ui.View):
    def __init__(self, ctx, user=None, total=0, page=1, per_page=10, all_vouches=False):
        super().__init__(timeout=None)
        self.ctx = ctx
        self.user = user
        self.page = page
        self.per_page = per_page
        self.total = total
        self.all_vouches = all_vouches
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
            super().__init__(label="Previous", style=discord_ticket.ButtonStyle.primary, custom_id="vouch_prev")
            self.parent = parent
        async def callback(self, interaction):
            self.parent.page -= 1
            await self.parent.update(interaction)

    class NextButton(discord_ticket.ui.Button):
        def __init__(self, parent):
            super().__init__(label="Next", style=discord_ticket.ButtonStyle.primary, custom_id="vouch_next")
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

# --- Persistent VouchView ---
class VouchView(discord_ticket.ui.View):
    def __init__(self, staff_members, user_id):
        super().__init__(timeout=None)
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
            super().__init__(placeholder="Select staff to vouch for", options=options, min_values=1, max_values=1, custom_id="vouch_staff_select")
            self.parent_view = parent_view
        async def callback(self, interaction: discord_ticket.Interaction):
            self.parent_view.selected_staff_id = int(self.values[0])
            await interaction.response.send_message(f"Selected staff: <@{self.values[0]}>", ephemeral=True)

    class StarSelect(discord_ticket.ui.Select):
        def __init__(self, parent_view):
            options = [discord_ticket.SelectOption(label=f"{i} ⭐", value=str(i)) for i in range(1, 6)]
            super().__init__(placeholder="Select rating (1-5 stars)", options=options, min_values=1, max_values=1, custom_id="vouch_star_select")
            self.parent_view = parent_view
        async def callback(self, interaction: discord_ticket.Interaction):
            self.parent_view.selected_rating = int(self.values[0])
            await interaction.response.send_message(f"Selected rating: {self.values[0]} ⭐", ephemeral=True)

    class VouchButton(discord_ticket.ui.Button):
        def __init__(self, parent_view):
            super().__init__(label="Submit Vouch", style=discord_ticket.ButtonStyle.success, custom_id="vouch_submit")
            self.parent_view = parent_view

        async def callback(self, interaction: discord_ticket.Interaction):
            if not self.parent_view.selected_staff_id or not self.parent_view.selected_rating:
                await interaction.response.send_message("Please select a staff member and a rating before submitting.", ephemeral=True)
                return
            modal = VouchModal(
                self.parent_view.selected_staff_id,
                self.parent_view.user_id,
                self.parent_view.selected_rating,
                on_submit_callback=handle_vouch_submit
            )
            await interaction.response.send_modal(modal)

# --- Persistent RatingView ---
class RatingView(View_ticket):
    def __init__(self, staff_id, ticket_channel, rater_id):
        super().__init__(timeout=None)
        for i in range(1, 6):
            self.add_item(RatingButton(i, staff_id, ticket_channel, rater_id))

# --- Persistent TicketBoardView ---
class TicketBoardView(View_ticket):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketTypeSelect())

# --- Persistent TicketTypeSelect ---
class TicketTypeSelect(Select_ticket):
    def __init__(self):
        options = [
            discord_ticket.SelectOption(label="ALS", description="Open a ticket for ALS Staff"),
            discord_ticket.SelectOption(label="ASTDX", description="Open a ticket for ASTDX Staffs")
        ]
        super().__init__(placeholder="Ticket Selector", options=options, custom_id="ticket_type_select")
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
        # Help/instructions message for ticket creators (as an embed)
        help_embed = discord_ticket.Embed(
            title="Ticket Help & Tips",
            description=(
                "• **Done? Drop a rating!** Once your issue's sorted, hit **DELETE TICKET** — that'll close it and let you rate the staff. A 5-star makes their day.\n\n"
                "• **Be specific:** It's best for you to tell a specific number of runs (example: I want to do 5 dungeons) or something like that.\n\n"
                "• **Hang tight:** If no one replies right away, don't worry. Our team's probably helping someone else. You're not being ignored.\n\n"
                "• **Ignorances:** No one takes your request? Maybe because it's too hard or time-wasting, try to change!\n\n"
                "• **Be cool:** Treat staff with respect, and they'll do their best to help. If someone's being rude, let us know.\n\n"
                "• **After you're done:** Use the **dio!vouch** command to vouch for the staff!"
            ),
            color=discord_ticket.Color.blurple()
        )
        await ticket_channel.send(embed=help_embed)
        await ticket_channel.send(f"{interaction.user.mention} has opened a **{ticket_type.upper()}** support ticket!\n{staff_role.mention if staff_role else ''}", view=view)
        await interaction.response.send_message(f"\u2705 Your ticket has been created: {ticket_channel.mention}", ephemeral=True)
        self.view.clear_items()
        self.view.add_item(TicketTypeSelect())
        await interaction.message.edit(view=self.view)

# --- Register all persistent views in on_ready ---
@bot_ticket.event
async def on_ready():
    print(f"bot_ticket is online! Username: {bot_ticket.user} (ID: {bot_ticket.user.id})")
    bot_ticket.add_view(PersistentTicketView())
    bot_ticket.add_view(TicketBoardView())
    bot_ticket.add_view(VouchView([], 0))
    bot_ticket.add_view(VouchPaginationView(None))
    # Add more as needed

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

def run_ticket_bot():
    try:
        print("🎫 Starting Ticket Bot...")
        bot_ticket.run(os.environ["TICKET_BOT_TOKEN"])
    except Exception as e:
        print(f"❌ Ticket Bot failed to start: {e}")

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

# Add rate limiting for YouTube requests
import time
last_youtube_request = 0
YOUTUBE_RATE_LIMIT = 2  # Minimum seconds between requests

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
    
    # Check if we have voice permissions
    if not channel.permissions_for(ctx.guild.me).connect:
        await ctx.send('❌ I don\'t have permission to connect to this voice channel!')
        return
    
    if not channel.permissions_for(ctx.guild.me).speak:
        await ctx.send('❌ I don\'t have permission to speak in this voice channel!')
        return

    # Connect to voice channel if not already connected
    if ctx.voice_client is None:
        try:
            vc = await channel.connect(timeout=20.0)
        except Exception as e:
            await ctx.send(f'❌ Could not join voice channel: {e}')
            return
    else:
        vc = ctx.voice_client
        if vc.channel != channel:
            try:
                await vc.move_to(channel)
            except Exception as e:
                await ctx.send(f'❌ Could not move to voice channel: {e}')
                return

    # Rate limiting
    global last_youtube_request
    current_time = time.time()
    if current_time - last_youtube_request < YOUTUBE_RATE_LIMIT:
        await asyncio.sleep(YOUTUBE_RATE_LIMIT - (current_time - last_youtube_request))
    last_youtube_request = time.time()
    
    await ctx.send(f'🔍 Searching for: {query}')

    # Try multiple search strategies
    search_strategies = [
        query,  # Original query
        f'"{query}"',  # Quoted query
        query + ' official',  # Add "official" to search
        query + ' music'  # Add "music" to search
    ]
    
    search_opts = {
        'format': 'bestaudio/best',
        'noplaylist': True,
        'default_search': 'ytsearch',
        'quiet': True,
        'extract_flat': 'True',
        'no_warnings': True,
        'ignoreerrors': True,
        'no_check_certificate': True,
        'prefer_insecure': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
    }
    
    info = None
    last_error = None
    
    for search_query in search_strategies:
        print(f"Trying search: {search_query}")
        with yt_dlp.YoutubeDL(search_opts) as ydl:
            try:
                info = ydl.extract_info(search_query, download=False)
                if 'entries' in info:
                    info = info['entries'][0]
                video_url = info['url'] if 'url' in info else info['webpage_url']
                title = info.get('title', 'Unknown Title')
                webpage_url = info.get('webpage_url', video_url)
                thumbnail = info.get('thumbnail', None)
                break  # Success, exit the loop
            except Exception as e:
                last_error = e
                await asyncio.sleep(0.5)  # Small delay between attempts
                continue  # Try next strategy
    
    if info is None:
        error_msg = str(last_error)
        if "Sign in to confirm you're not a bot" in error_msg:
            await ctx.send(f'❌ YouTube is temporarily blocking automated access.\n\n**Solutions:**\n• Wait a few minutes and try again\n• Try a different search term\n• Use a YouTube link instead of search terms\n• Contact server staff if the issue persists')
        else:
            await ctx.send(f'❌ Could not find or play "{query}": {last_error}')
        return

    audio_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'no_warnings': True,
        'ignoreerrors': True,
        'no_check_certificate': True,
        'prefer_insecure': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
    }
    with yt_dlp.YoutubeDL(audio_opts) as ydl:
        try:
            audio_info = ydl.extract_info(video_url, download=False)
            audio_url = audio_info['url']
        except Exception as e:
            error_msg = str(e)
            if "Sign in to confirm you're not a bot" in error_msg:
                await ctx.send(f'❌ YouTube is temporarily blocking audio extraction.\n\n**Solutions:**\n• Wait a few minutes and try again\n• Try a different song\n• Use a YouTube link instead of search terms')
            else:
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
    try:
        print("🎵 Starting Music Bot...")
        bot_music.run(os.environ["MUSIC_BOT_TOKEN"])
    except Exception as e:
        print(f"❌ Music Bot failed to start: {e}")

# ================== Start All Bots ==================
if __name__ == "__main__":
    print("🤖 Starting Discord Bot Orchestrator...")
    print("=" * 50)
    
    # Start bots with error handling
    threads = []
    bot_functions = [
        ("Application Bot", run_application_bot),
        ("Giveaway Bot", run_giveaway_bot),
        ("Invites Bot", run_invites_bot),
        ("Ticket Bot", run_ticket_bot),
        ("Music Bot", run_music_bot),
    ]
    
    for name, func in bot_functions:
        thread = threading.Thread(target=func, name=name)
        thread.daemon = True  # Allow main thread to exit if bots fail
        threads.append(thread)
        thread.start()
        print(f"✅ {name} thread started")
    
    print("=" * 50)
    print("🎉 All bots are starting up...")
    print("Press Ctrl+C to stop all bots")
    
    try:
        # Wait for all threads to complete (they won't unless there's an error)
        for thread in threads:
            thread.join()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down bots...")
        print("Bots will disconnect automatically")
        sys.exit(0)

@bot_ticket.event
async def on_message(message):
    await bot_ticket.process_commands(message)