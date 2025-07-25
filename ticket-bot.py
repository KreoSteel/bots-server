import discord
from discord.ext import commands
from discord.ui import View, Button, Select
from collections import defaultdict


intents = discord.Intents.all()
bot = commands.Bot(command_prefix="dio!", intents=intents)


ticket_counter = 0
active_tickets = {}
staff_ratings = defaultdict(list)


CATEGORY_ID = 1397234544368685269
ALS_ROLE_ID = 1397023739631108188
ASTDX_ROLE_ID = 1382679356975087647
PROMOTION_ROLE_ID = 1397185106975920138
LOG_CHANNEL_ID = 1397579436274090035
STAFF_ROLE_ID = 1397186487044411522




class RatingButton(Button):
    def __init__(self, rating, staff_id, ticket_channel, rater_id):
        super().__init__(label=f"{rating} ⭐", style=discord.ButtonStyle.secondary)
        self.rating = rating
        self.staff_id = staff_id
        self.ticket_channel = ticket_channel
        self.rater_id = rater_id


    async def callback(self, interaction: discord.Interaction):
        if self.staff_id:
            staff_ratings[self.staff_id].append(self.rating)
            await interaction.response.send_message(f"✅ You rated {self.rating} stars!", ephemeral=True)


            log_channel = bot.get_channel(LOG_CHANNEL_ID)
            if log_channel:
                rater = interaction.guild.get_member(self.rater_id)
                staff = interaction.guild.get_member(self.staff_id)
                await log_channel.send(
                    f"⭐ **Rating**: `{self.rating} stars`\n👤 From: {rater.mention}\n🎯 To: {staff.mention}"
                )


            # Promotion check
            guild = interaction.guild
            staff_member = guild.get_member(self.staff_id)
            if staff_member and self.rating == 5:
                if staff_ratings[self.staff_id].count(5) == 15:
                    role = guild.get_role(PROMOTION_ROLE_ID)
                    if role and role not in staff_member.roles:
                        await staff_member.add_roles(role)
                        await log_channel.send(f"🎉 {staff_member.mention} has been promoted with 15 five-star ratings!")


            await self.ticket_channel.delete()




class RatingView(View):
    def __init__(self, staff_id, ticket_channel, rater_id):
        super().__init__(timeout=60)
        for i in range(1, 6):
            self.add_item(RatingButton(i, staff_id, ticket_channel, rater_id))




class DeleteTicketButton(Button):
    def __init__(self, creator_id):
        super().__init__(label="🗑️ Delete Ticket", style=discord.ButtonStyle.danger)
        self.creator_id = creator_id


    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.creator_id:
            await interaction.response.send_message("❌ Only the ticket creator can delete this ticket.", ephemeral=True)
            return


        staff_id = active_tickets.get(interaction.channel.id, {}).get("staff_id")
        if not staff_id:
            await interaction.channel.delete()
            return


        view = RatingView(staff_id, interaction.channel, interaction.user.id)
        await interaction.response.send_message("Please rate the support you received:", view=view, ephemeral=True)




class TakeRequestButton(Button):
    def __init__(self, creator_id):
        super().__init__(label="🎯 Take Request", style=discord.ButtonStyle.primary)
        self.creator_id = creator_id


    async def callback(self, interaction: discord.Interaction):
        data = active_tickets.get(interaction.channel.id)
        if not data:
            await interaction.response.send_message("⚠️ Internal error.", ephemeral=True)
            return


        if data["staff_id"] is not None:
            await interaction.response.send_message("❌ This request has already been taken.", ephemeral=True)
            return


        if interaction.user.id == self.creator_id:
            await interaction.response.send_message("❌ You cannot take your own request.", ephemeral=True)
            return


        data["staff_id"] = interaction.user.id
        await interaction.channel.send(f"✅ This request has been taken by {interaction.user.mention}.")
        self.disabled = True
        await interaction.message.edit(view=self.view)
        await interaction.response.send_message("🎯 You claimed this request!", ephemeral=True)




class TicketTypeSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="ALS", description="Open a ticket for ALS Staff"),
            discord.SelectOption(label="ASTDX", description="Open a ticket for ASTDX Staffs")
        ]
        super().__init__(placeholder="Ticket Selector", options=options)


    async def callback(self, interaction: discord.Interaction):
        global ticket_counter
        ticket_counter += 1


        ticket_type = self.values[0].lower()
        ticket_name = f"{ticket_type}-ticket-{ticket_counter:04}"
        guild = interaction.guild
        category = guild.get_channel(CATEGORY_ID)
        helpers_role = guild.get_role(STAFF_ROLE_ID)


        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True, embed_links=True),
            helpers_role: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }


        ticket_channel = await guild.create_text_channel(ticket_name, overwrites=overwrites, category=category)
        active_tickets[ticket_channel.id] = {
            "creator_id": interaction.user.id,
            "staff_id": None
        }


        view = View()
        view.add_item(TakeRequestButton(interaction.user.id))
        view.add_item(DeleteTicketButton(interaction.user.id))


        role_id = ALS_ROLE_ID if ticket_type == "als" else ASTDX_ROLE_ID
        staff_role = guild.get_role(role_id)


        await ticket_channel.send(f"{interaction.user.mention} has opened a **{ticket_type.upper()}** support ticket!\n{staff_role.mention if staff_role else ''}", view=view)
        await interaction.response.send_message(f"✅ Your ticket has been created: {ticket_channel.mention}", ephemeral=True)


        # Reset selection
        self.view.clear_items()
        self.view.add_item(TicketTypeSelect())
        await interaction.message.edit(view=self.view)




class TicketBoardView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketTypeSelect())




@bot.command()
async def ticketboard(ctx):
    view = TicketBoardView()
    await ctx.send("🎫 Select a ticket type below:", view=view)




@bot.command()
async def staffratings(ctx):
    if not staff_ratings:
        await ctx.send("No ratings yet.")
        return


    embed = discord.Embed(title="⭐ Staff Ratings", color=discord.Color.green())
    for staff_id, ratings in staff_ratings.items():
        user = await bot.fetch_user(staff_id)
        avg = sum(ratings) / len(ratings)
        embed.add_field(name=f"{user}", value=f"{len(ratings)} ratings | Avg: {avg:.2f}⭐", inline=False)
    await ctx.send(embed=embed)




