import threading
import os
from dotenv import load_dotenv
load_dotenv()

# ================== Application Bot ==================
import discord as discord_app
from discord.ext import commands as commands_app
from discord.ui import Button as Button_app, View as View_app
import asyncio as asyncio_app

intents_app = discord_app.Intents.all()
bot_app = commands_app.Bot(command_prefix="app!", intents=intents_app)

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

class ApplicationButton(Button_app):
    def __init__(self, label, app_type):
        super().__init__(label=label, style=discord_app.ButtonStyle.primary)
        self.app_type = app_type

    async def callback(self, interaction: discord_app.Interaction):
        user = interaction.user
        guild = interaction.guild
        category = guild.get_channel(CATEGORY_ID)
        number = application_counter[self.app_type]
        application_counter[self.app_type] += 1
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
        await self.channel.delete()

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

def run_application_bot():
    bot_app.run(os.environ["APP_BOT_TOKEN"])

# ================== Giveaway Levels Bot ==================
import discord as discord_give
from discord.ext import commands as commands_give, tasks as tasks_give
import asyncio as asyncio_give
import random as random_give
from datetime import datetime as datetime_give, timedelta as timedelta_give

intents_give = discord_give.Intents.default()
intents_give.message_content = True
intents_give.members = True
bot_give = commands_give.Bot(command_prefix='mul!', intents=intents_give)
user_exp = {}
def get_required_exp(level):
    return 3 * (2 ** (level - 1))
@bot_give.event
async def on_message(message):
    if message.author.bot:
        return
    user_id = message.author.id
    if user_id not in user_exp:
        user_exp[user_id] = {'exp': 0, 'level': 1}
    user_data = user_exp[user_id]
    user_data['exp'] += 1
    while user_data['exp'] >= get_required_exp(user_data['level']):
        user_data['exp'] -= get_required_exp(user_data['level'])
        user_data['level'] += 1
        await message.channel.send(f"\ud83c\udf89 {message.author.mention} leveled up to level {user_data['level']}!")
    await bot_give.process_commands(message)
@bot_give.command(name='check')
async def check_level(ctx):
    user = user_exp.get(ctx.author.id, {'exp': 0, 'level': 1})
    await ctx.send(f"{ctx.author.mention}, Level: {user['level']}, EXP: {user['exp']} / {get_required_exp(user['level'])}")
@bot_give.command(name='lb')
async def leaderboard(ctx):
    sorted_users = sorted(user_exp.items(), key=lambda x: (x[1]['level'], x[1]['exp']), reverse=True)
    desc = ""
    for i, (uid, data) in enumerate(sorted_users[:10]):
        user = await bot_give.fetch_user(uid)
        desc += f"**{i+1}. {user.name}** - Level {data['level']} ({data['exp']} EXP)\n"
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

# ================== Invites Tracker Bot ==================
import discord as discord_inv
from discord.ext import commands as commands_inv
import json as json_inv
import os as os_inv
intents_inv = discord_inv.Intents.all()
bot_inv = commands_inv.Bot(command_prefix='inv!', intents=intents_inv)
data_file = 'invites.json'
if not os_inv.path.exists(data_file):
    with open(data_file, 'w') as f:
        json_inv.dump({}, f)
@bot_inv.event
async def on_ready():
    print(f'\u2705 Logged in as {bot_inv.user}')
    for guild in bot_inv.guilds:
        invites = await guild.invites()
        bot_inv.invites[guild.id] = {invite.code: invite.uses for invite in invites}
@bot_inv.event
async def on_guild_join(guild):
    invites = await guild.invites()
    bot_inv.invites[guild.id] = {invite.code: invite.uses for invite in invites}
@bot_inv.event
async def on_member_join(member):
    with open(data_file, 'r') as f:
        data = json_inv.load(f)
    invites_before = bot_inv.invites.get(member.guild.id, {})
    invites_after = await member.guild.invites()
    used_invite = None
    for invite in invites_after:
        if invite.code in invites_before and invite.uses > invites_before[invite.code]:
            used_invite = invite
            break
    if used_invite:
        inviter = used_invite.inviter
        inviter_id = str(inviter.id)
        if inviter_id not in data:
            data[inviter_id] = 0
        data[inviter_id] += 1
        with open(data_file, 'w') as f:
            json_inv.dump(data, f)
        print(f"{member.name} was invited by {inviter.name}")
    bot_inv.invites[member.guild.id] = {invite.code: invite.uses for invite in invites_after}
@bot_inv.event
async def on_member_remove(member):
    with open(data_file, 'r') as f:
        data = json_inv.load(f)
    invites_before = bot_inv.invites.get(member.guild.id, {})
    invites_after = await member.guild.invites()
    used_invite = None
    for invite in invites_after:
        if invite.code in invites_before and invite.uses < invites_before[invite.code]:
            used_invite = invite
            break
    if used_invite:
        inviter = used_invite.inviter
        inviter_id = str(inviter.id)
        if inviter_id in data:
            data[inviter_id] = max(0, data[inviter_id] - 1)
            with open(data_file, 'w') as f:
                json_inv.dump(data, f)
    bot_inv.invites[member.guild.id] = {invite.code: invite.uses for invite in invites_after}
@bot_inv.command()
async def add(ctx, member: discord_inv.Member, points: int):
    with open(data_file, 'r') as f:
        data = json_inv.load(f)
    user_id = str(member.id)
    if user_id not in data:
        data[user_id] = 0
    data[user_id] += points
    with open(data_file, 'w') as f:
        json_inv.dump(data, f)
    await ctx.send(f"\u2705 Added {points} points to {member.display_name}.")
@bot_inv.command()
async def remove(ctx, member: discord_inv.Member, points: int):
    with open(data_file, 'r') as f:
        data = json_inv.load(f)
    user_id = str(member.id)
    if user_id not in data:
        data[user_id] = 0
    data[user_id] = max(0, data[user_id] - points)
    with open(data_file, 'w') as f:
        json_inv.dump(data, f)
    await ctx.send(f"\u274c Removed {points} points from {member.display_name}.")
@bot_inv.command()
async def lb(ctx):
    with open(data_file, 'r') as f:
        data = json_inv.load(f)
    sorted_data = sorted(data.items(), key=lambda x: x[1], reverse=True)
    leaderboard = ""
    for i, (user_id, points) in enumerate(sorted_data[:10], start=1):
        user = await bot_inv.fetch_user(int(user_id))
        leaderboard += f"**{i}.** {user.name} - **{points} invites**\n"
    await ctx.send(embed=discord_inv.Embed(title="\ud83c\udfc6 Invite Leaderboard", description=leaderboard, color=0x00ff00))
bot_inv.invites = {}
def run_invites_bot():
    bot_inv.run(os.environ["INVITES_BOT_TOKEN"])

# ================== Ticket Bot ==================
import discord as discord_ticket
from discord.ext import commands as commands_ticket
from discord.ui import View as View_ticket, Button as Button_ticket, Select as Select_ticket
from collections import defaultdict as defaultdict_ticket
intents_ticket = discord_ticket.Intents.all()
bot_ticket = commands_ticket.Bot(command_prefix="dio!", intents=intents_ticket)
ticket_counter = 0
active_tickets = {}
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
            staff_ratings[self.staff_id].append(self.rating)
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
                if staff_ratings[self.staff_id].count(5) == 15:
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
        if interaction.user.id != self.creator_id:
            await interaction.response.send_message("\u274c Only the ticket creator can delete this ticket.", ephemeral=True)
            return
        staff_id = active_tickets.get(interaction.channel.id, {}).get("staff_id")
        if not staff_id:
            await interaction.channel.delete()
            return
        view = RatingView(staff_id, interaction.channel, interaction.user.id)
        await interaction.response.send_message("Please rate the support you received:", view=view, ephemeral=True)
class TakeRequestButton(Button_ticket):
    def __init__(self, creator_id):
        super().__init__(label="\ud83c\udfaf Take Request", style=discord_ticket.ButtonStyle.primary)
        self.creator_id = creator_id
    async def callback(self, interaction: discord_ticket.Interaction):
        data = active_tickets.get(interaction.channel.id)
        if not data:
            await interaction.response.send_message("\u26a0\ufe0f Internal error.", ephemeral=True)
            return
        if data["staff_id"] is not None:
            await interaction.response.send_message("\u274c This request has already been taken.", ephemeral=True)
            return
        if interaction.user.id == self.creator_id:
            await interaction.response.send_message("\u274c You cannot take your own request.", ephemeral=True)
            return
        data["staff_id"] = interaction.user.id
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
        active_tickets[ticket_channel.id] = {
            "creator_id": interaction.user.id,
            "staff_id": None
        }
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
    if not staff_ratings:
        await ctx.send("No ratings yet.")
        return
    embed = discord_ticket.Embed(title="\u2b50 Staff Ratings", color=discord_ticket.Color.green())
    for staff_id, ratings in staff_ratings.items():
        user = await bot_ticket.fetch_user(staff_id)
        avg = sum(ratings) / len(ratings)
        embed.add_field(name=f"{user}", value=f"{len(ratings)} ratings | Avg: {avg:.2f}\u2b50", inline=False)
    await ctx.send(embed=embed)
def run_ticket_bot():
    bot_ticket.run(os.environ["TICKET_BOT_TOKEN"])

# ================== Start All Bots ==================
if __name__ == "__main__":
    threads = [
        threading.Thread(target=run_application_bot),
        threading.Thread(target=run_giveaway_bot),
        threading.Thread(target=run_invites_bot),
        threading.Thread(target=run_ticket_bot),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join() 