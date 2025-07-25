import discord
from discord.ext import commands, tasks
import asyncio
import random
from datetime import datetime, timedelta


intents = discord.Intents.default()
intents.message_content = True
intents.members = True


bot = commands.Bot(command_prefix='mul!', intents=intents)


# ===== LEVELING SYSTEM =====
user_exp = {}


def get_required_exp(level):
    return 3 * (2 ** (level - 1))


@bot.event
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
        await message.channel.send(f"🎉 {message.author.mention} leveled up to level {user_data['level']}!")


    await bot.process_commands(message)


@bot.command(name='check')
async def check_level(ctx):
    user = user_exp.get(ctx.author.id, {'exp': 0, 'level': 1})
    await ctx.send(f"{ctx.author.mention}, Level: {user['level']}, EXP: {user['exp']} / {get_required_exp(user['level'])}")


@bot.command(name='lb')
async def leaderboard(ctx):
    sorted_users = sorted(user_exp.items(), key=lambda x: (x[1]['level'], x[1]['exp']), reverse=True)
    desc = ""
    for i, (uid, data) in enumerate(sorted_users[:10]):
        user = await bot.fetch_user(uid)
        desc += f"**{i+1}. {user.name}** - Level {data['level']} ({data['exp']} EXP)\n"
    embed = discord.Embed(title="📊 Leaderboard", description=desc, color=0x00ff00)
    await ctx.send(embed=embed)


# ===== GIVEAWAY SYSTEM =====
giveaway_data = {}


@bot.command(name="giveaways")
async def start_giveaway(ctx, headline: str, winners: int, duration: str):
    duration_sec = int(duration[:-1]) * (3600 if duration.endswith("h") else 60)
    end_time = datetime.utcnow() + timedelta(seconds=duration_sec)


    embed = discord.Embed(title="🎉 Giveaway", description=headline, color=0x3498db)
    embed.add_field(name="🎁 Casual", value="Anyone can join!", inline=False)
    embed.add_field(name="💎 Premium", value="Requires staff approval", inline=False)
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


class GiveawayView(discord.ui.View):
    def __init__(self, host_id, end_time, winners, headline):
        super().__init__(timeout=None)
        self.host_id = host_id
        self.end_time = end_time
        self.winners = winners
        self.headline = headline
        self.msg = None


    @discord.ui.button(label="Join Casual", style=discord.ButtonStyle.success)
    async def join_casual(self, interaction: discord.Interaction, button: discord.ui.Button):
        gid = self.msg.id
        if interaction.user.id in giveaway_data[gid]['casual_entries']:
            await interaction.response.send_message("❌ You already joined the casual giveaway.", ephemeral=True)
            return
        giveaway_data[gid]['casual_entries'].append(interaction.user.id)
        await interaction.response.send_message("✅ Joined casual giveaway!", ephemeral=True)


    @discord.ui.button(label="Join Premium", style=discord.ButtonStyle.primary)
    async def join_premium(self, interaction: discord.Interaction, button: discord.ui.Button):
        gid = self.msg.id
        ticket_channel = await interaction.guild.create_text_channel(
            name=f"giveaway-entry-{random.randint(1000, 9999)}",
            overwrites={
                interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
                interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
                interaction.guild.me: discord.PermissionOverwrite(view_channel=True)
            },
            reason="Premium giveaway entry"
        )
        await interaction.response.send_message(f"📩 A ticket was created: {ticket_channel.mention}", ephemeral=True)


        view = ApprovalView(gid, interaction.user.id, ticket_channel)
        await ticket_channel.send(f"Staff, please review the premium entry by {interaction.user.mention}.", view=view)


class ApprovalView(discord.ui.View):
    def __init__(self, giveaway_id, user_id, channel):
        super().__init__(timeout=None)
        self.giveaway_id = giveaway_id
        self.user_id = user_id
        self.channel = channel


    @discord.ui.button(label="Approve", style=discord.ButtonStyle.success)
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        giveaway_data[self.giveaway_id]['premium_entries'].append(self.user_id)
        await interaction.response.send_message(f"✅ Approved <@{self.user_id}>")
        await self.channel.delete()


    @discord.ui.button(label="Decline", style=discord.ButtonStyle.danger)
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(f"❌ Declined <@{self.user_id}>")
        await self.channel.delete()


@tasks.loop(seconds=30)
async def countdown_timer():
    now = datetime.utcnow()
    expired = []
    for gid, data in list(giveaway_data.items()):
        if data['end_time'] <= now:
            expired.append(gid)
            all_entries = data['casual_entries'] + data['premium_entries']
            if not all_entries:
                await data['message'].channel.send("🎁 Giveaway ended. No valid entries.")
                continue
            winners = random.sample(all_entries, min(len(all_entries), data['winners']))
            winner_mentions = ", ".join(f"<@{u}>" for u in winners)
            await data['message'].channel.send(f"🎉 Giveaway Over!\n**{data['headline']}**\nWinners: {winner_mentions}")
        else:
            # Update countdown with relative time
            embed = data['message'].embeds[0]
            embed.set_footer(text=f"Ends <t:{int(data['end_time'].timestamp())}:R>")
            await data['message'].edit(embed=embed)


    for gid in expired:
        del giveaway_data[gid]


# ===== BOT START =====
bot.run("MTM5NTg3Mzg3NTUyNjQyMjcxOQ.G2jPo4.iGeuiQAPyCCK-kHQyGDwVFu1vceowmoSOp6Tvc")