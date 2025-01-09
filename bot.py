import discord
from discord.ext import commands

# Directly add your bot token here (replace YOUR_BOT_TOKEN with your actual token)
TOKEN = "BOT_TOKEN"

# Intents setup
intents = discord.Intents.default()
intents.guilds = True
intents.messages = True

# Bot setup
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    """
    Event triggered when the bot is ready.
    Syncs slash commands with Discord.
    """
    print(f"Logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()  # Sync slash commands
        print(f"Synced {len(synced)} commands with Discord.")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

@bot.tree.command(name="support", description="Send a support ticket embed.")
async def support(interaction: discord.Interaction):
    """
    Sends an embed with a button to create a support ticket.
    """
    embed = discord.Embed(
        title="🎟 Support Tickets",
        description="Click the button below to create a support ticket and get help from our team.",
        color=discord.Color.blue()
    )
    embed.set_footer(text="Our team is here to assist you!")

    # Create a button to open a support ticket
    view = discord.ui.View()
    view.add_item(
        discord.ui.Button(
            label="Open Ticket",
            style=discord.ButtonStyle.primary,
            custom_id="open_ticket"
        )
    )

    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


@bot.event
async def on_interaction(interaction: discord.Interaction):
    """
    Handles interactions for opening and closing tickets.
    """
    if "custom_id" in interaction.data:  # Ensure the interaction has a custom_id
        custom_id = interaction.data["custom_id"]

        if custom_id == "open_ticket":
            guild = interaction.guild
            category = discord.utils.get(guild.categories, name="Support Tickets")
            if not category:
                category = await guild.create_category("Support Tickets")

            # Ensure bot has permission to manage channels in the category
            if interaction.guild.me.guild_permissions.manage_channels:
                # Create a ticket channel
                ticket_channel = await category.create_text_channel(f"ticket-{interaction.user.name}")

                # Set permissions for the channel
                await ticket_channel.set_permissions(interaction.guild.default_role, read_messages=False)
                await ticket_channel.set_permissions(interaction.user, read_messages=True, send_messages=True)
                await ticket_channel.set_permissions(interaction.guild.me, read_messages=True, send_messages=True)

                try:
                    # Send an embed in the ticket channel
                    embed = discord.Embed(
                        title="🎫 Support Ticket",
                        description=f"Hello {interaction.user.mention}, our support team will assist you soon.\n\n"
                                    "Click the button below to close this ticket when you're done.",
                        color=discord.Color.green()
                    )
                    embed.set_footer(text="Thank you for contacting support!")
                    close_view = discord.ui.View()
                    close_view.add_item(
                        discord.ui.Button(
                            label="Close Ticket",
                            style=discord.ButtonStyle.danger,
                            custom_id="close_ticket"
                        )
                    )
                    await ticket_channel.send(embed=embed, view=close_view)
                    await interaction.response.send_message("Your ticket has been created!", ephemeral=True)
                except discord.errors.NotFound:
                    await interaction.response.send_message("The ticket channel could not be found or was deleted.", ephemeral=True)

            else:
                await interaction.response.send_message("I don't have permission to manage channels.", ephemeral=True)

        elif custom_id == "close_ticket":
            try:
                # Ensure the channel exists and the bot has permission to delete it
                if interaction.guild.me.guild_permissions.manage_channels:
                    if interaction.channel:  # Make sure the channel isn't None
                        await interaction.channel.delete()
                        await interaction.response.send_message("Ticket closed!", ephemeral=True)
                    else:
                        await interaction.response.send_message("The ticket channel no longer exists.", ephemeral=True)
                else:
                    await interaction.response.send_message("I don't have permission to delete the ticket channel.", ephemeral=True)
            except discord.errors.NotFound:
                await interaction.response.send_message("The ticket channel has already been deleted or is unavailable.", ephemeral=True)
            except discord.errors.Forbidden:
                await interaction.response.send_message("I don't have permission to delete the ticket channel.", ephemeral=True)


# Run the bot with the token
if TOKEN:
    bot.run(TOKEN)
else:
    print("Error: Bot token not provided.")