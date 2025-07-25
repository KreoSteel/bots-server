import discord
from discord.ext import commands
from discord.ui import Button, View
import asyncio


intents = discord.Intents.all()
bot = commands.Bot(command_prefix="app!", intents=intents)


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


class ApplicationView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ApplicationButton("Apply on ASTDX", "astdx"))
        self.add_item(ApplicationButton("Apply on ALS", "als"))
        self.add_item(ApplicationButton("Apply All", "all"))


class ApplicationButton(Button):
    def __init__(self, label, app_type):
        super().__init__(label=label, style=discord.ButtonStyle.primary)
        self.app_type = app_type


    async def callback(self, interaction: discord.Interaction):
        user = interaction.user
        guild = interaction.guild
        category = guild.get_channel(CATEGORY_ID)


        number = application_counter[self.app_type]
        application_counter[self.app_type] += 1


        channel_name = f"{self.app_type}-application-#{number:04}"
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }


        channel = await guild.create_text_channel(
            name=channel_name,
            category=category,
            overwrites=overwrites
        )


        await interaction.response.send_message(f"✅ Application created: {channel.mention}", ephemeral=True)


        await channel.send(f"{user.mention}\n{form_message}")


        view = View()
        view.add_item(AcceptButton(self.app_type, user))
        view.add_item(RejectButton(user))
        view.add_item(DeleteTicketButton(channel, user))
        await channel.send("Staff controls:", view=view)


class AcceptButton(Button):
    def __init__(self, app_type, user):
        super().__init__(label="✅ Accept", style=discord.ButtonStyle.success)
        self.app_type = app_type
        self.user = user


    async def callback(self, interaction: discord.Interaction):
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


        await interaction.response.send_message(f"✅ {self.user.mention} has been accepted and given roles.", ephemeral=True)


class RejectButton(Button):
    def __init__(self, user):
        super().__init__(label="❌ Reject", style=discord.ButtonStyle.danger)
        self.user = user


    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"❌ {self.user.mention}'s application was rejected.", ephemeral=True)


class DeleteTicketButton(Button):
    def __init__(self, channel, user):
        super().__init__(label="🗑️ Delete Ticket", style=discord.ButtonStyle.danger)
        self.channel = channel
        self.user = user


    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message("This ticket will be deleted in 5 seconds...", ephemeral=True)
        await asyncio.sleep(5)
        await self.channel.delete()


# ======================= RULES COMMAND ========================


class RulesView(View):
    def __init__(self, author: discord.Member):
        super().__init__(timeout=None)
        self.author = author
        self.current_page = 1


    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.author.id


    @discord.ui.button(label="Next ▶️", style=discord.ButtonStyle.primary)
    async def next_page(self, interaction: discord.Interaction, button: Button):
        if self.current_page == 1:
            staff_role = interaction.guild.get_role(STAFF_ROLE_ID)
            if staff_role in interaction.user.roles:
                embed2 = discord.Embed(
                    title="👮 Staff Guide",
                    description=(
                        "• **Take Requests:** When a ticket appears, check what the member needs. If you're confident you can help, press **TAKE REQUEST**.\n\n"
                        "• **Deletion & Ratings:** After completing the request, ask the member to press **DELETE TICKET** to leave a rating.\n\n"
                        "• **Choices:** You don’t have to take every ticket. Only take the ones you can handle.\n\n"
                        "• **Respect:** Always respect members. If someone disrespects you, stop helping and report it.\n\n"
                        "• **Benefits:** Staff can join exclusive giveaways and perks."
                    ),
                    color=discord.Color.red()
                )
                self.current_page = 2
                await interaction.response.edit_message(embed=embed2, view=self)
            else:
                await interaction.response.send_message("🚫 You don't have permission to view this page.", ephemeral=True)


    @discord.ui.button(label="◀️ Back", style=discord.ButtonStyle.secondary)
    async def back_page(self, interaction: discord.Interaction, button: Button):
        if self.current_page == 2:
            embed1 = discord.Embed(
                title="📜 AVS Server Rules & Guidelines",
                description=(
                    "**Welcome to AVS — a fun community for ALS, ASTDX, and chill chats!**\n\n"
                    "**🌟 1. Respect & Kindness**\n"
                    "• Be respectful to everyone.\n"
                    "• No harassment, hate, threats, or toxic behavior — jokes are fine, but not harmful ones.\n"
                    "• If someone bothers you, don’t retaliate — report them.\n\n"
                    "**📢 2. Language & Behavior**\n"
                    "• Keep chats appropriate for all ages.\n"
                    "• Swearing is okay in moderation — no slurs or hate speech.\n"
                    "• No spam, flooding, mass pings.\n\n"
                    "**📌 3. Use the Right Channels**\n"
                    "• Chat in general, memes in #memes, help in #support, etc.\n\n"
                    "**🧠 4. Content Rules**\n"
                    "• No NSFW/NSFL, illegal, pirated, or disturbing content.\n\n"
                    "**🚫 5. Alts & Raids**\n"
                    "• No alts unless approved. Trolls = instant ban.\n\n"
                    "**✅ Final:**\n"
                    "• No disrespect to helpers. Major = ban. Minor = mute.\n"
                ),
                color=discord.Color.blue()
            )
            self.current_page = 1
            await interaction.response.edit_message(embed=embed1, view=self)


@bot.command()
async def rules(ctx):
    embed1 = discord.Embed(
        title="📜 AVS Server Rules & Guidelines",
        description=(
            "**Welcome to AVS — a fun community for ALS, ASTDX, and chill chats!**\n\n"
            "**🌟 1. Respect & Kindness**\n"
            "• Be respectful to everyone.\n"
            "• No harassment, hate, threats, or toxic behavior — jokes are fine, but not harmful ones.\n"
            "• If someone bothers you, don’t retaliate — report them.\n\n"
            "**📢 2. Language & Behavior**\n"
            "• Keep chats appropriate for all ages.\n"
            "• Swearing is okay in moderation — no slurs or hate speech.\n"
            "• No spam, flooding, mass pings.\n\n"
            "**📌 3. Use the Right Channels**\n"
            "• Chat in general, memes in #memes, help in #support, etc.\n\n"
            "**🧠 4. Content Rules**\n"
            "• No NSFW/NSFL, illegal, pirated, or disturbing content.\n\n"
            "**🚫 5. Alts & Raids**\n"
            "• No alts unless approved. Trolls = instant ban.\n\n"
            "**✅ Final:**\n"
            "• No disrespect to helpers. Major = ban. Minor = mute.\n"
        ),
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed1, view=RulesView(ctx.author))


# ====================== APPLICATION BUTTON TRIGGER =======================


@bot.command()
async def application(ctx):
    await ctx.send("Click a button below to apply:", 
view=ApplicationView())
bot.run("MTM5NjQ5ODk2Mjg2OTEyOTM5Nw.GZpaeH.lEGyvWHhO1jpnF-mlErm07iZvBKVsFOpPyV2NY")