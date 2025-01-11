import discord
from discord.ext import commands
import asyncio
import requests
import os
from datetime import datetime, timedelta

# Get the bot token from environment variables
TOKEN = os.getenv("BOT_TOKEN")  # Store the token securely

# Initialize the bot with necessary intents
intents = discord.Intents.default()
intents.message_content = True  # Enable message content intent

bot = commands.Bot(command_prefix="!", intents=intents)

# Variable to hold the channel IDs where memes will be sent
active_channels = {}
stopped_channels = set()  # To track channels where memes are stopped
memes_posted = 0  # Counter for memes posted
recent_memes = []  # List to store recent memes
command_history_list = []  # List to store history of bot commands

# Variable to track tasks
channel_tasks = {}

# Function to fetch a meme from the internet
def get_meme():
    url = "https://meme-api.com/gimme"  # Public meme API
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        meme_url = data["url"]  # Meme image URL
        meme_title = data["title"]  # Meme title or description
        return meme_url, meme_title  # Return both the URL and the title
    return None, None  # Return None if there's an issue

# Helper function to fetch weekly memes
def get_weekly_memes():
    # For now, we'll just return the recent memes from the list as an example
    return recent_memes[-7:]  # Show the last 7 memes

# Helper function to track commands (implementing a basic command logging system)
def log_command(command: str):
    command_history_list.append(command)

# Function to rate dankness (implement your rating logic here)
def rate_dankness(meme_url):
    # Simple example: Based on meme title length or some other metric
    return len(meme_url) % 10  # Just an example, replace with a more advanced rating system

# Slash command to set the meme channel with interval
@bot.tree.command(name="setchannel", description="Set the channel for memes to be posted and set the interval.")
async def setchannel(interaction: discord.Interaction, channel: discord.TextChannel, time: str):
    if channel.id in active_channels:
        if channel.id in stopped_channels:
            await interaction.response.send_message(f"{channel.mention} is already set up for memes but has been stopped. To resume posting, use /startmemes.")
        else:
            await interaction.response.send_message(f"{channel.mention} is already set up for memes.")
    else:
        try:
            interval = parse_time(time)
            active_channels[channel.id] = {"channel": channel, "interval": interval}
            await interaction.response.send_message(f"Meme channel has been set to {channel.mention} with an interval of {interval} seconds.")
            # Start posting memes immediately
            asyncio.create_task(post_memes())
        except ValueError:
            await interaction.response.send_message("Invalid time format. Please use 'min' for minutes or 'sec' for seconds.")

# Helper function to parse time input
def parse_time(time_str):
    time_str = time_str.lower().strip()
    if 'min' in time_str:
        minutes = int(time_str.replace("min", "").strip())
        return minutes * 60  # Convert minutes to seconds
    elif 'sec' in time_str:
        seconds = int(time_str.replace("sec", "").strip())
        return seconds  # Already in seconds
    else:
        raise ValueError("Invalid time format")

# Slash command to stop posting memes to a specific channel
@bot.tree.command(name="stopmemes", description="Stop posting memes to a specific channel.")
async def stopmemes(interaction: discord.Interaction, channel: discord.TextChannel):
    if channel.id in active_channels:
        stopped_channels.add(channel.id)
        # Cancel the task that is posting memes for this channel
        if channel.id in channel_tasks:
            channel_tasks[channel.id].cancel()  # Cancel the task
            del channel_tasks[channel.id]  # Remove the task from the tracking dictionary
        await interaction.response.send_message(f"Stopped posting memes in {channel.mention}. To resume posting, use /startmemes.")
    else:
        await interaction.response.send_message(f"{channel.mention} is not set up to post memes.")

# Slash command to start posting memes to a specific channel
@bot.tree.command(name="startmemes", description="Start posting memes to a specific channel.")
async def startmemes(interaction: discord.Interaction, channel: discord.TextChannel):
    if channel.id in active_channels:
        if channel.id in stopped_channels:
            stopped_channels.remove(channel.id)
            # Restart the meme task for the channel
            interval = active_channels[channel.id]["interval"]
            task = asyncio.create_task(post_meme_to_channel(channel, interval))
            channel_tasks[channel.id] = task  # Store the task for future cancellation
            await interaction.response.send_message(f"Started posting memes in {channel.mention}.")
        else:
            await interaction.response.send_message(f"Memes are already being posted in {channel.mention}.")
    else:
        await interaction.response.send_message(f"{channel.mention} is not set up to post memes.")

# Slash command to send a meme instantly
@bot.tree.command(name="meme", description="Fetch and post a meme instantly.")
async def meme(interaction: discord.Interaction):
    meme_url, meme_title = get_meme()
    if meme_url:
        await interaction.response.send_message(f"**{meme_title}**\n{meme_url}")
    else:
        await interaction.response.send_message("Sorry, couldn't fetch a meme right now.")

@bot.tree.command(name="daily", description="Send daily memes at midnight in a specific channel.")
async def daily(interaction: discord.Interaction, channel: discord.TextChannel):
    if channel.id in active_channels:
        await interaction.response.send_message(f"Daily memes are already being sent in {channel.mention}.")
    else:
        active_channels[channel.id] = {"channel": channel, "interval": 24 * 60 * 60}  # Store info
        await interaction.response.send_message(f"Daily memes will now be sent in {channel.mention} at midnight.")
        # Schedule the first meme for midnight
        asyncio.create_task(schedule_midnight_posting(channel))

# New command to view the history of sent memes
@bot.tree.command(name="memehistory", description="View a history of sent memes.")
async def memehistory(interaction: discord.Interaction):
    if recent_memes:
        message = "Meme history:\n"
        for meme in recent_memes:
            message += f"{meme['title']} - {meme['url']}\n"
        await interaction.response.send_message(message)
    else:
        await interaction.response.send_message("No memes sent yet.")

# New command to view a history of bot commands used
@bot.tree.command(name="command_history", description="View a history of bot commands used.")
async def command_history(interaction: discord.Interaction):
    if command_history_list:
        message = "Command history:\n"
        for command in command_history_list:
            message += f"{command}\n"
        await interaction.response.send_message(message)
    else:
        await interaction.response.send_message("No commands used yet.")

# New command to show trending memes
@bot.tree.command(name="memetrend", description="Show trending memes.")
async def memetrend(interaction: discord.Interaction):
    trending_memes = get_weekly_memes()  # For now, using weekly memes as trending
    if trending_memes:
        message = "Trending memes:\n"
        for meme in trending_memes:
            message += f"{meme['title']} - {meme['url']}\n"
        await interaction.response.send_message(message)
    else:
        await interaction.response.send_message("No trending memes available.")

# New command to rate the dankness of a meme
@bot.tree.command(name="dankmeter", description="Rate the dankness of a meme.")
async def dankmeter(interaction: discord.Interaction, meme_url: str):
    dankness_rating = rate_dankness(meme_url)
    await interaction.response.send_message(f"The dankness of the meme is: {dankness_rating}/10")

# Slash command to check if the bot is online (ping)
@bot.tree.command(name="ping", description="Check if the bot is online.")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("Pong! The bot is online and responsive.")

@bot.tree.command(name="help", description="Show available bot commands.")
async def help(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Bot Commands",
        description="Here are the available commands you can use:",
        color=discord.Color.blue()
    )
    
    embed.add_field(
        name="🔧 /setchannel",
        value="Set the channel for memes to be posted and set the interval.",
        inline=False
    )
    embed.add_field(
        name="🎯 /meme",
        value="Fetch and send a single meme immediately.",
        inline=False
    )
    embed.add_field(
        name="⏸️ /stopmemes",
        value="Stop automatic meme posting.",
        inline=False
    )
    embed.add_field(
        name="▶️ /startmemes",
        value="Start automatic meme posting.",
        inline=False
    )
    embed.add_field(
        name="📊 /stats",
        value="Display bot usage statistics.",
        inline=False
    )
    embed.add_field(
        name="🔝 /topmemes",
        value="Show the most popular memes.",
        inline=False
    )
    embed.add_field(
        name="🏓 /ping",
        value="Test the bot's responsiveness.",
        inline=False
    )
    embed.add_field(
        name="📅 /weekly",
        value="Fetch weekly meme highlights.",
        inline=False
    )
    embed.add_field(
        name="⏳ /memehistory",
        value="View a history of sent memes.",
        inline=False
    )
    embed.add_field(
        name="⏳ /command_history",
        value="View a history of bot commands used.",
        inline=False
    )
    embed.add_field(
        name="👀 /memetrend",
        value="Show trending memes.",
        inline=False
    )
    embed.add_field(
        name="💀 /dankmeter",
        value="Rate the dankness of a meme.",
        inline=False
    )
    
    await interaction.response.send_message(embed=embed)

# Event triggered when the bot logs in successfully
@bot.event
async def on_ready():
    await bot.tree.sync()  # Force syncing the slash commands with Discord
    print(f'Logged in as {bot.user}')

# Function to post memes at the set intervals
async def post_memes():
    global active_channels, stopped_channels, memes_posted, recent_memes
    tasks = []
    for channel_id, data in active_channels.items():
        if channel_id not in stopped_channels:
            interval = data["interval"]
            channel = data["channel"]
            # Create and track the task for posting memes
            task = asyncio.create_task(post_meme_to_channel(channel, interval))
            channel_tasks[channel_id] = task  # Store the task for future cancellation
            tasks.append(task)
    await asyncio.gather(*tasks)

# Function to post a meme to the channel
async def post_meme_to_channel(channel, interval):
    global memes_posted, recent_memes
    while True:
        # Check if the channel is in stopped_channels before continuing
        if channel.id in stopped_channels:
            break  # Stop posting memes to this channel
        
        meme_url, meme_title = get_meme()
        if meme_url:
            recent_memes.append({"url": meme_url, "title": meme_title})
            await channel.send(f"**{meme_title}**\n{meme_url}")
            memes_posted += 1
        
        await asyncio.sleep(interval)
        
async def schedule_midnight_posting(channel):
    while True:
        # Calculate the time until the next midnight
        now = datetime.now()
        next_midnight = datetime.combine(now.date() + timedelta(days=1), datetime.min.time())
        seconds_until_midnight = (next_midnight - now).total_seconds()

        # Wait until midnight
        await asyncio.sleep(seconds_until_midnight)

        # Post a meme
        meme_url, meme_title = get_meme()
        if meme_url:
            await channel.send(f"**{meme_title}**\n{meme_url}")
        else:
            await channel.send("Couldn't fetch a meme at this time. Please try again later.")

# Run the bot
bot.run(TOKEN)
