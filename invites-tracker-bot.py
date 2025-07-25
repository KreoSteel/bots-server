import discord
from discord.ext import commands
import json
import os


intents = discord.Intents.all()
bot = commands.Bot(command_prefix='inv!', intents=intents)


data_file = 'invites.json'
if not os.path.exists(data_file):
    with open(data_file, 'w') as f:
        json.dump({}, f)


@bot.event
async def on_ready():
    print(f'✅ Logged in as {bot.user}')
    for guild in bot.guilds:
        invites = await guild.invites()
        bot.invites[guild.id] = {invite.code: invite.uses for invite in invites}


@bot.event
async def on_guild_join(guild):
    invites = await guild.invites()
    bot.invites[guild.id] = {invite.code: invite.uses for invite in invites}


@bot.event
async def on_member_join(member):
    with open(data_file, 'r') as f:
        data = json.load(f)


    invites_before = bot.invites.get(member.guild.id, {})
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
            json.dump(data, f)


        print(f"{member.name} was invited by {inviter.name}")


    bot.invites[member.guild.id] = {invite.code: invite.uses for invite in invites_after}


@bot.event
async def on_member_remove(member):
    with open(data_file, 'r') as f:
        data = json.load(f)


    invites_before = bot.invites.get(member.guild.id, {})
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
                json.dump(data, f)


    bot.invites[member.guild.id] = {invite.code: invite.uses for invite in invites_after}


@bot.command()
async def add(ctx, member: discord.Member, points: int):
    with open(data_file, 'r') as f:
        data = json.load(f)


    user_id = str(member.id)
    if user_id not in data:
        data[user_id] = 0
    data[user_id] += points


    with open(data_file, 'w') as f:
        json.dump(data, f)


    await ctx.send(f"✅ Added {points} points to {member.display_name}.")


@bot.command()
async def remove(ctx, member: discord.Member, points: int):
    with open(data_file, 'r') as f:
        data = json.load(f)


    user_id = str(member.id)
    if user_id not in data:
        data[user_id] = 0
    data[user_id] = max(0, data[user_id] - points)


    with open(data_file, 'w') as f:
        json.dump(data, f)


    await ctx.send(f"❌ Removed {points} points from {member.display_name}.")


@bot.command()
async def lb(ctx):
    with open(data_file, 'r') as f:
        data = json.load(f)


    sorted_data = sorted(data.items(), key=lambda x: x[1], reverse=True)
    leaderboard = ""
    for i, (user_id, points) in enumerate(sorted_data[:10], start=1):
        user = await bot.fetch_user(int(user_id))
        leaderboard += f"**{i}.** {user.name} - **{points} invites**\n"


    await ctx.send(embed=discord.Embed(title="🏆 Invite Leaderboard", description=leaderboard, color=0x00ff00))


bot.invites = {}
bot.run("MTM5NjE1MzY3ODYwMzM1ODI4OA.GGv8Mt.fJAEV4Sdp2XRmp0nA_PBT2rIJVJh1wiwtEd2oo")