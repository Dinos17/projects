# ===== IMPORTS =====
import discord
from discord.ext import commands
from discord.ui import Button, View
from discord import Embed
from discord import app_commands
import asyncio
import requests
from collections import deque
import os
import sys
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import time
import random
import praw
import asyncpraw
import subprocess
from discord.app_commands import checks
from datetime import datetime, timedelta
import aiohttp

# ===== CONFIGURATION AND SETUP =====
TOKEN = os.getenv("BOT_TOKEN")  # Use environment variable for the bot token
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")  # Use environment variable for Reddit client ID
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")  # Use environment variable for Reddit client secret

reddit = praw.Reddit(
    client_id=REDDIT_CLIENT_ID,
    client_secret=REDDIT_CLIENT_SECRET,
    user_agent="Auto Memer",
)

# Bot Setup
intents = discord.Intents.default()
intents.messages = True  # Enables access to message events
intents.message_content = True  # Allows access to message content
intents.members = True  # Allows access to member events
bot = commands.Bot(command_prefix="/", intents=intents)

# ===== GLOBAL VARIABLES =====
active_channels = {}  # Stores active channels and their intervals
stopped_channels = set()  # Channels where meme posting is paused
memes_posted = 0  # Counter for memes posted
meme_command_count = 0  # Counter for /meme command usage
command_history_list = deque(maxlen=30)  # Stores last 30 commands
last_sync_time = None
SYNC_COOLDOWN = 60  # Cooldown in seconds

# Define your support server channel ID
SUPPORT_CHANNEL_ID = 1331983087898460160  # Replace with your actual channel ID

# ===== UTILITY FUNCTIONS =====
def parse_time(time_str):
    time_str = time_str.lower().strip()
    if "min" in time_str:
        return int(time_str.replace("min", "").strip()) * 60
    elif "sec" in time_str:
        return int(time_str.replace("sec", "").strip())
    raise ValueError("Invalid time format. Use 'min' for minutes or 'sec' for seconds.")

def format_time(seconds):
    if seconds < 60:
        return f"{seconds} sec"
    elif seconds < 3600:
        return f"{seconds // 60} min"
    else:
        return f"{seconds // 3600} hours {(seconds % 3600) // 60} min"

def get_meme(subreddit_name="memes"):
    try:
        # Fetch subreddit posts
        subreddit = reddit.subreddit(subreddit_name)
        posts = [
            post
            for post in subreddit.hot(limit=50)
            if post.url.endswith(("jpg", "jpeg", "png", "gif"))
        ]

        if not posts:
            return None, "No suitable memes found."

        # Select a random post from the list of fetched posts
        post = random.choice(posts)
        return post.url, post.title

    except Exception as e:
        print(f"Error fetching meme: {e}")
        return None, None

def get_joke():
    try:
        response = requests.get("https://v2.jokeapi.dev/joke/Programming,Miscellaneous?type=twopart")
        if response.status_code == 200:
            joke_data = response.json()
            if joke_data["type"] == "twopart":
                return joke_data["setup"], joke_data["delivery"]
            else:
                return joke_data["joke"], None  # For single-part jokes
        else:
            print("Failed to fetch joke.")
            return None, None
    except Exception as e:
        print(f"Error fetching joke: {e}")
        return None, None

# ===== AUTO-RESTART FUNCTIONALITY =====
class BotFileChangeHandler(FileSystemEventHandler):
    def __init__(self, script_path):
        self.script_path = script_path
        self.restart_pending = False
        
    def on_modified(self, event):
        if event.src_path.endswith(".py") and not self.restart_pending:
            self.restart_pending = True
            print(f"\nFile {event.src_path} has been modified.")
            print("Restarting bot...")
            try:
                # Start a new process for the bot
                subprocess.Popen([sys.executable, self.script_path])
                sys.exit()  # Exit the current process
            except Exception as e:
                print(f"Error restarting bot: {e}")
                self.restart_pending = False

def setup_watchdog(path_to_watch=".", script_path=__file__):
    event_handler = BotFileChangeHandler(script_path)
    observer = Observer()
    observer.schedule(event_handler, path=path_to_watch, recursive=False)
    observer.start()
    return observer

# ===== CORE FUNCTIONALITY =====
async def post_meme_to_channel(channel, interval, subreddit_name):
    global memes_posted
    while True:
        if channel.id in stopped_channels:
            break
        meme_url, meme_title = get_meme(subreddit_name)  # Remove await here
        if meme_url:
            await channel.send(f"**{meme_title}**\n{meme_url}")
            memes_posted += 1
        
        # Wait for the next interval before posting another meme
        await asyncio.sleep(interval)

async def fetch_data(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()

# ===== EVENT HANDLERS =====
@bot.event
async def on_ready():
    print(f"Bot is ready as {bot.user}")
    try:
        # Only sync commands if they haven't been synced recently
        global last_sync_time
        current_time = datetime.now()
        
        if not last_sync_time or (current_time - last_sync_time).total_seconds() > SYNC_COOLDOWN:
            start_time = time.time()
            synced = await bot.tree.sync()  # Sync commands when the bot is ready
            last_sync_time = current_time
            print(f"Synced {len(synced)} command(s)")
            print(f"Sync time: {time.time() - start_time} seconds")
        else:
            print("Skipping command sync due to cooldown")
    except Exception as e:
        print(f"Error syncing commands: {e}")
    await bot.change_presence(status=discord.Status.online)  # Set the bot's status

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Keyword-based trigger
    keywords = ["post a meme", "send meme"]
    if any(keyword in message.content.lower() for keyword in keywords):
        meme_url, meme_title = get_meme("funny")  # Remove await here
        if meme_url:
            await message.channel.send(f"**{meme_title}**\n{meme_url}")
        else:
            await message.channel.send("Sorry, couldn't fetch a meme right now.")

@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.type == discord.InteractionType.application_command:
        command_history_list.append(
            f"/{interaction.data['name']}"
        )  # Add command to history

# ===== SLASH COMMANDS =====
@bot.tree.command(name="help", description="Show a list of all available commands.")
async def help_command(interaction: discord.Interaction):
    def generate_help_embed():
        embed = Embed(title="Help - Available Commands", color=discord.Color.blue())
        
        # Meme Commands
        embed.add_field(
            name="🎭 Meme Commands",
            value=(
                "`/meme [subreddit]` - Fetch and post a meme with refresh option\n"
                "`/meme_search <keyword>` - Search for memes with specific keywords\n"
                "`/top_memes [timeframe] [count]` - Get top memes from a time period\n"
                "`/setchannel` - Set a channel for auto-posting memes\n"
                "`/stopmemes` - Stop posting memes in a channel\n"
                "`/startmemes` - Resume posting memes in a channel\n"
                "`/memes_by_number <count>` - Fetch multiple memes at once"
            ),
            inline=False
        )
        
        # Fun Commands
        embed.add_field(
            name="🎮 Fun Commands",
            value=(
                "`/random_joke [channel]` - Fetch and post a random joke\n"
                "`/ping` - Check bot's latency"
            ),
            inline=False
        )
        
        # Info Commands
        embed.add_field(
            name="ℹ️ Information Commands",
            value=(
                "`/serverinfo` - Display server information\n"
                "`/userinfo [user]` - Show information about a user\n"
                "`/stats` - Show bot statistics\n"
                "`/command_history` - View command usage history"
            ),
            inline=False
        )
        
        # Utility Commands
        embed.add_field(
            name="🛠️ Utility Commands",
            value=(
                "`/invite` - Get bot invite link\n"
                "`/report <issue>` - Report an issue with the bot\n"
                "`/sync` - Sync bot commands (Admin only)"
            ),
            inline=False
        )

        embed.set_footer(text="[Optional] parameters, <Required> parameters")
        return embed

    help_embed = generate_help_embed()
    
    # Create buttons
    close_button = Button(label="Close", style=discord.ButtonStyle.danger)
    invite_button = Button(
        label="Join Support Server",
        style=discord.ButtonStyle.link,
        url="https://discord.gg/QegFaGhmmq"
    )

    async def close_callback(interaction: discord.Interaction):
        await interaction.message.delete()

    close_button.callback = close_callback

    view = View()
    view.add_item(invite_button)
    view.add_item(close_button)

    await interaction.response.send_message(embed=help_embed, view=view)

@bot.tree.command(name="sync", description="Manually sync bot commands.")
async def sync(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("You need administrator permissions to use this command.", ephemeral=True)
        return

    global last_sync_time
    current_time = datetime.now()

    # Check cooldown
    if last_sync_time and (current_time - last_sync_time).total_seconds() < SYNC_COOLDOWN:
        remaining = int(SYNC_COOLDOWN - (current_time - last_sync_time).total_seconds())
        await interaction.response.send_message(
            f"Command sync is on cooldown. Please wait {remaining} seconds.",
            ephemeral=True
        )
        return

    # Attempt to defer the response
    try:
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=True)
    except discord.errors.HTTPException as e:
        print(f"Failed to defer interaction: {e}")
        return  # Exit if the interaction is no longer valid

    try:
        # Sync commands
        start_time = time.time()
        synced = await bot.tree.sync(guild=interaction.guild)  # Sync only for the current guild
        last_sync_time = current_time
        
        # Check if the interaction response is still valid before sending a message
        if not interaction.response.is_done():
            embed = discord.Embed(
                title="✅ Command Sync Complete",
                description="All commands have been synchronized successfully!",
                color=discord.Color.green()
            )
            
            command_list = "\n".join([f"• /{cmd.name}" for cmd in synced]) if synced else "No commands synced"
            embed.add_field(
                name="Available Commands",
                value=f"Synced {len(synced)} commands:\n{command_list}",
                inline=False
            )
            embed.set_footer(text=f"Requested by {interaction.user}")

            await interaction.followup.send(embed=embed, ephemeral=True)

    except Exception as e:
        error_embed = discord.Embed(
            title="❌ Sync Failed",
            description=f"An error occurred while syncing commands:\n```{str(e)}```",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=error_embed, ephemeral=True)

@bot.tree.command(name="vote", description="Vote for the bot on top.gg.")
async def vote(interaction: discord.Interaction):
    embed = Embed(
        title="Vote for Me on top.gg!",
        description="If you enjoy using this bot, please take a moment to vote for it on top.gg. Your support helps improve the bot and keep it active!\n\nClick the button below to vote.",
        color=discord.Color.green(),
    )
    vote_button = Button(
        label="Vote for Me",
        style=discord.ButtonStyle.link,
        url="https://top.gg/bot/1325110227225546854/vote",
    )
    view = View()
    view.add_item(vote_button)

    await interaction.response.send_message(embed=embed, view=view)

@bot.tree.command(name="meme", description="Fetch and post a meme from a specific subreddit.")
async def meme(
    interaction: discord.Interaction,
    subreddit: str = "memes"  # Default to r/memes but allow custom subreddits
):
    global meme_command_count  # Access the global counter
    meme_command_count += 1  # Increment the counter only here
    await interaction.response.defer()  # Defer response if meme takes time to fetch
    
    try:
        meme_url, meme_title = get_meme(subreddit)  # Remove await here
        if meme_url:
            embed = discord.Embed(
                title=meme_title,
                color=discord.Color.random()
            )
            embed.set_image(url=meme_url)
            embed.set_footer(text=f"From r/{subreddit} | Requested by {interaction.user}")
            
            # Create buttons
            refresh_button = Button(label="New Meme", style=discord.ButtonStyle.primary, emoji="🔄")
            like_button = Button(label="Like", style=discord.ButtonStyle.success, emoji="👍")
            
            async def refresh_callback(button_interaction: discord.Interaction):
                global meme_command_count  # Access the global counter
                meme_command_count += 1  # Increment the counter for the new meme
                new_meme_url, new_meme_title = get_meme(subreddit)  # Remove await here
                if new_meme_url:
                    new_embed = discord.Embed(
                        title=new_meme_title,
                        color=discord.Color.random()
                    )
                    new_embed.set_image(url=new_meme_url)
                    new_embed.set_footer(text=f"From r/{subreddit} | Requested by {interaction.user}")
                    await button_interaction.response.edit_message(embed=new_embed, view=view)
                else:
                    await button_interaction.response.send_message("Couldn't fetch a new meme!", ephemeral=True)
            
            async def like_callback(button_interaction: discord.Interaction):
                await button_interaction.response.send_message("Thanks for liking the meme! 😊", ephemeral=True)
            
            refresh_button.callback = refresh_callback
            like_button.callback = like_callback
            
            view = View()
            view.add_item(refresh_button)
            view.add_item(like_button)
            
            await interaction.followup.send(embed=embed, view=view)
        else:
            await interaction.followup.send(f"Couldn't fetch a meme from r/{subreddit}. Try another subreddit!", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"An error occurred: {str(e)}", ephemeral=True)

@bot.tree.command(name="meme_search", description="Search for memes with specific keywords.")
async def meme_search(interaction: discord.Interaction, keyword: str):
    try:
        # First, acknowledge the interaction
        await interaction.response.defer()
        
        # Search in multiple meme subreddits
        subreddits = ["memes", "dankmemes", "funny"]
        found_memes = []
        
        for subreddit_name in subreddits:
            subreddit = reddit.subreddit(subreddit_name)
            search_results = subreddit.search(keyword, limit=5)  # Use the keyword for searching
            
            for post in search_results:
                if post.url.endswith(("jpg", "jpeg", "png", "gif")):
                    found_memes.append({
                        "title": post.title,
                        "url": post.url,
                        "subreddit": subreddit_name,
                        "score": post.score
                    })
        
        if found_memes:
            # Sort by score
            found_memes.sort(key=lambda x: x["score"], reverse=True)
            current_index = 0
            
            # Create embed for first meme
            embed = discord.Embed(
                title=found_memes[current_index]["title"],
                color=discord.Color.random()
            )
            embed.set_image(url=found_memes[current_index]["url"])
            embed.set_footer(
                text=f"Meme {current_index + 1}/{len(found_memes)} | "
                f"From r/{found_memes[current_index]['subreddit']} | "
                f"Score: {found_memes[current_index]['score']}"
            )
            
            # Create navigation buttons
            previous_button = Button(
                label="Previous",
                style=discord.ButtonStyle.primary,
                emoji="⬅️",
                disabled=True
            )
            next_button = Button(
                label="Next",
                style=discord.ButtonStyle.primary,
                emoji="➡️",
                disabled=len(found_memes) <= 1
            )
            
            async def previous_callback(button_interaction: discord.Interaction):
                nonlocal current_index
                current_index -= 1
                await update_meme(button_interaction)
                
            async def next_callback(button_interaction: discord.Interaction):
                nonlocal current_index
                current_index += 1
                await update_meme(button_interaction)
                
            async def update_meme(button_interaction: discord.Interaction):
                # Update embed with new meme
                new_embed = discord.Embed(
                    title=found_memes[current_index]["title"],
                    color=discord.Color.random()
                )
                new_embed.set_image(url=found_memes[current_index]["url"])
                new_embed.set_footer(
                    text=f"Meme {current_index + 1}/{len(found_memes)} | "
                    f"From r/{found_memes[current_index]['subreddit']} | "
                    f"Score: {found_memes[current_index]['score']}"
                )
                
                # Update button states
                previous_button.disabled = current_index == 0
                next_button.disabled = current_index == len(found_memes) - 1
                
                await button_interaction.response.edit_message(
                    embed=new_embed,
                    view=view
                )
            
            previous_button.callback = previous_callback
            next_button.callback = next_callback
            
            view = View()
            view.add_item(previous_button)
            view.add_item(next_button)
            
            await interaction.followup.send(
                f"Found {len(found_memes)} memes matching '{keyword}':",
                embed=embed,
                view=view
            )
        else:
            await interaction.followup.send(f"No memes found matching '{keyword}'.")
            
    except Exception as e:
        # If the interaction hasn't been acknowledged yet, acknowledge it with an error message
        if not interaction.response.is_done():
            await interaction.response.send_message(
                f"An error occurred: {str(e)}",
                ephemeral=True
            )
        # If it has been acknowledged, use followup
        else:
            await interaction.followup.send(
                f"An error occurred: {str(e)}",
                ephemeral=True
            )

@bot.tree.command(name="top_memes", description="Get top memes from the last day/week/month/year.")
async def top_memes(
    interaction: discord.Interaction,
    timeframe: str = "day",  # day, week, month, year
    count: int = 5  # How many memes to fetch
):
    valid_timeframes = ["day", "week", "month", "year"]
    if timeframe not in valid_timeframes:
        await interaction.response.send_message(
            "Invalid timeframe! Please use: day, week, month, or year.",
            ephemeral=True
        )
        return
        
    if count < 1 or count > 10:
        await interaction.response.send_message(
            "Please request between 1 and 10 memes.",
            ephemeral=True
        )
        return
        
    await interaction.response.defer()
    
    try:
        subreddit = reddit.subreddit("memes")
        top_posts = subreddit.top(time_filter=timeframe, limit=count)
        
        embeds = []
        for post in top_posts:
            if post.url.endswith(("jpg", "jpeg", "png", "gif")):
                embed = discord.Embed(
                    title=post.title,
                    color=discord.Color.random()
                )
                embed.set_image(url=post.url)
                embed.add_field(name="Score", value=f"👍 {post.score:,}", inline=True)
                embed.add_field(name="Comments", value=f"💬 {post.num_comments:,}", inline=True)
                embed.set_footer(text=f"Top meme from the last {timeframe}")
                embeds.append(embed)
        
        if embeds:
            await interaction.followup.send(
                f"Top {len(embeds)} memes from the last {timeframe}:",
                embeds=embeds
            )
        else:
            await interaction.followup.send("Couldn't find any suitable memes.", ephemeral=True)
            
    except Exception as e:
        await interaction.followup.send(f"An error occurred: {str(e)}", ephemeral=True)

@bot.tree.command(name="memes_by_number", description="Fetch a specific number of memes (max 20).")
async def memes_by_number(interaction: discord.Interaction, count: int):
    if count < 1 or count > 20:
        await interaction.response.send_message(
            "Please provide a number between 1 and 20."
        )
        return

    try:
        # Access the 'memes' subreddit
        subreddit = reddit.subreddit("memes")

        # Fetch 'count' number of posts from the subreddit
        posts = subreddit.new(limit=count)

        # Prepare a list of memes with necessary information
        memes = []
        for post in posts:
            memes.append(
                {
                    "title": post.title,
                    "url": post.url,
                    "ups": post.ups,
                    "author": post.author.name if post.author else "Unknown",
                    "postLink": f"https://www.reddit.com{post.permalink}",
                    "subreddit": post.subreddit.display_name,
                }
            )

        if not memes:
            await interaction.response.send_message(
                "Couldn't fetch memes at the moment. Please try again later."
            )
            return

        # Create embeds for each meme to display them nicely
        embeds = []
        for meme in memes:
            embed = discord.Embed(
                title=meme["title"],
                url=meme["postLink"],
                description=f"Subreddit: {meme['subreddit']}",
                color=discord.Color.green(),
            )
            embed.set_image(url=meme["url"])
            embed.set_footer(text=f"👍 {meme['ups']} | Author: {meme['author']}")
            embeds.append(embed)

        # Send the embed messages with memes to Discord, limiting to 10 embeds per message
        for i in range(0, len(embeds), 10):
            await interaction.response.send_message(
                f"Here are your memes {i + 1}-{min(i + 10, len(embeds))}:",
                embeds=embeds[i:i + 10]
            )
    except asyncpraw.exceptions.PRAWException as e:
        print(f"Error fetching memes: {e}")
        await interaction.response.send_message(
            "There was an error fetching memes. Please try again later."
        )

@bot.tree.command(name="invite", description="Get the invite link to add the bot to your server.")
async def invite(interaction: discord.Interaction):
    bot_invite_link = f"https://discord.com/oauth2/authorize?client_id={bot.user.id}&permissions=8&scope=bot%20applications.commands"
    
    # Create embed
    embed = discord.Embed(
        title="🤖 Invite Me to Your Server!",
        description="Click the button below to add me to your server and start enjoying memes and jokes!",
        color=discord.Color.blue()
    )
    embed.add_field(
        name="Features",
        value="• Auto-posting memes\n• Random jokes\n• Easy to use commands\n• And much more!",
        inline=False
    )
    embed.set_footer(text=f"Requested by {interaction.user}")

    # Create buttons
    invite_button = Button(
        label="Add to Server", 
        style=discord.ButtonStyle.link,
        url=bot_invite_link,
        emoji="➕"
    )
    support_button = Button(
        label="Support Server",
        style=discord.ButtonStyle.link,
        url="https://discord.gg/QegFaGhmmq",
        emoji="❓"
    )

    # Create view and add buttons
    view = View()
    view.add_item(invite_button)
    view.add_item(support_button)

    # Send the message (not ephemeral)
    await interaction.response.send_message(embed=embed, view=view)

@bot.tree.command(name="setchannel", description="Set the channel for memes to be posted.")
async def setchannel(interaction: discord.Interaction, channel: discord.TextChannel, search_query: str, interval: str):
    try:
        search_query = search_query.strip().lower()
        time_in_seconds = parse_time(interval)

        active_channels[channel.id] = {
            "channel": channel,
            "search_query": search_query,
            "interval": time_in_seconds
        }
        asyncio.create_task(post_meme_to_channel(channel, time_in_seconds, search_query))
        await interaction.response.send_message(f"Set {channel.mention} as a meme channel with search query '{search_query}' and an interval of {interval}.")
    except ValueError:
        await interaction.response.send_message("Invalid time format. Use 'min' for minutes or 'sec' for seconds.")

@bot.tree.command(name="stopmemes", description="Stop posting memes in a channel.")
async def stopmemes(interaction: discord.Interaction, channel: discord.TextChannel):
    if channel.id in active_channels:
        stopped_channels.add(channel.id)
        await interaction.response.send_message(
            f"Stopped posting memes in {channel.mention}."
        )
    else:
        await interaction.response.send_message(
            f"{channel.mention} is not set up for meme posting."
        )

@bot.tree.command(name="startmemes", description="Resume posting memes in a channel.")
async def startmemes(
    interaction: discord.Interaction, channel: discord.TextChannel, subreddit_name: str
):
    if channel.id in active_channels and channel.id in stopped_channels:
        stopped_channels.remove(channel.id)
        interval = active_channels[channel.id]["interval"]
        # Pass subreddit_name to the post_meme_to_channel function
        asyncio.create_task(post_meme_to_channel(channel, interval, subreddit_name))
        await interaction.response.send_message(
            f"Resumed posting memes from {subreddit_name} in {channel.mention}."
        )
    else:
        await interaction.response.send_message(
            f"{channel.mention} is not set up or already active."
        )

@bot.tree.command(name="stats", description="Show bot statistics.")
async def stats(interaction: discord.Interaction):
    def generate_stats_embed():
        embed = Embed(title="Bot Statistics", color=discord.Color.green())
        embed.add_field(name="Memes Posted", value=str(memes_posted), inline=True)
        embed.add_field(name="Meme Commands Used", value=str(meme_command_count), inline=True)
        embed.add_field(
            name="Active Channels", value=str(len(active_channels)), inline=True
        )
        embed.add_field(
            name="Stopped Channels", value=str(len(stopped_channels)), inline=True
        )

        if active_channels:
            sample_channel = list(active_channels.values())[0]
            interval = sample_channel["interval"]
            formatted_interval = format_time(interval)
            embed.add_field(
                name="Sample Interval", value=formatted_interval, inline=False
            )

        avatar_url = (
            bot.user.avatar.url if bot.user.avatar else bot.user.default_avatar.url
        )
        embed.set_thumbnail(url=avatar_url)
        return embed

    initial_embed = generate_stats_embed()

    refresh_button = Button(label="Refresh Stats", style=discord.ButtonStyle.primary)

    async def refresh_callback(interaction: discord.Interaction):
        updated_embed = generate_stats_embed()
        await interaction.response.edit_message(embed=updated_embed, view=view)

    refresh_button.callback = refresh_callback

    view = View()
    view.add_item(refresh_button)

    await interaction.response.send_message(embed=initial_embed, view=view)

@bot.tree.command(name="command_history", description="View the history of commands used.")
async def command_history(interaction: discord.Interaction):
    if not command_history_list:
        await interaction.response.send_message("No commands have been used yet.")
        return
        
    embed = discord.Embed(
        title="Command History",
        description="Last 30 commands used:",
        color=discord.Color.blue()
    )
    
    # Group commands and count their occurrences
    command_counts = {}
    for cmd in command_history_list:
        command_counts[cmd] = command_counts.get(cmd, 0) + 1
    
    # Format the command history
    history_text = "\n".join(f"{cmd}: {count} times" for cmd, count in command_counts.items())
    embed.add_field(name="Commands", value=history_text if history_text else "No commands used yet")
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="random_joke", description="Fetch and post a random joke. Optionally specify a channel.")
async def random_joke(
    interaction: discord.Interaction, 
    channel: discord.TextChannel = None
):
    # Check if user has permission to send messages in the specified channel
    target_channel = channel or interaction.channel
    
    if not target_channel.permissions_for(interaction.user).send_messages:
        await interaction.response.send_message(
            f"You don't have permission to send messages in {target_channel.mention}",
            ephemeral=True
        )
        return

    setup, punchline = get_joke()
    
    if setup and punchline:
        # Create embed
        embed = discord.Embed(
            title="😄 Random Joke",
            color=discord.Color.blue()
        )
        embed.add_field(name="Setup", value=setup, inline=False)
        embed.add_field(name="Punchline", value="||" + punchline + "||", inline=False)
        embed.set_footer(text=f"Requested by {interaction.user}")

        # Create buttons
        new_joke_button = Button(label="New Joke", style=discord.ButtonStyle.primary, emoji="🎲")
        
        async def new_joke_callback(button_interaction: discord.Interaction):
            new_setup, new_punchline = get_joke()
            if new_setup and new_punchline:
                new_embed = discord.Embed(
                    title="😄 Random Joke",
                    color=discord.Color.blue()
                )
                new_embed.add_field(name="Setup", value=new_setup, inline=False)
                new_embed.add_field(name="Punchline", value="||" + new_punchline + "||", inline=False)
                new_embed.set_footer(text=f"Requested by {interaction.user}")
                await button_interaction.response.edit_message(embed=new_embed, view=view)
            else:
                await button_interaction.response.send_message("Sorry, couldn't fetch a new joke right now.", ephemeral=True)

        new_joke_button.callback = new_joke_callback

        view = View()
        view.add_item(new_joke_button)

        # Send to specified channel
        if channel:
            await interaction.response.send_message(
                f"Joke sent to {channel.mention}!", 
                ephemeral=True
            )
            await channel.send(embed=embed, view=view)
        else:
            await interaction.response.send_message(embed=embed, view=view)
    else:
        await interaction.response.send_message("Sorry, couldn't fetch a joke right now.", ephemeral=True)

@bot.tree.command(name="ping", description="Check the bot's latency.")
async def ping(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)  # Convert to milliseconds
    embed = discord.Embed(
        title="🏓 Pong!",
        description=f"Bot Latency: `{latency}ms`",
        color=discord.Color.green() if latency < 200 else discord.Color.red()
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="serverinfo", description="Display information about the server.")
async def serverinfo(interaction: discord.Interaction):
    guild = interaction.guild
    
    embed = discord.Embed(
        title=f"📊 {guild.name} Server Information",
        color=discord.Color.blue()
    )
    
    # Server info
    embed.add_field(name="Owner", value=guild.owner.mention, inline=True)
    embed.add_field(name="Created On", value=guild.created_at.strftime("%B %d, %Y"), inline=True)
    embed.add_field(name="Server ID", value=guild.id, inline=True)
    
    # Member stats
    total_members = len(guild.members)
    humans = len([m for m in guild.members if not m.bot])
    bots = total_members - humans
    embed.add_field(name="Total Members", value=total_members, inline=True)
    embed.add_field(name="Humans", value=humans, inline=True)
    embed.add_field(name="Bots", value=bots, inline=True)
    
    # Channel stats
    text_channels = len(guild.text_channels)
    voice_channels = len(guild.voice_channels)
    categories = len(guild.categories)
    embed.add_field(name="Text Channels", value=text_channels, inline=True)
    embed.add_field(name="Voice Channels", value=voice_channels, inline=True)
    embed.add_field(name="Categories", value=categories, inline=True)
    
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="userinfo", description="Display information about a user.")
async def userinfo(interaction: discord.Interaction, user: discord.Member = None):
    user = user or interaction.user
    
    embed = discord.Embed(
        title=f"👤 User Information for {user.name}",
        color=user.color if user.color != discord.Color.default() else discord.Color.blue()
    )
    
    embed.add_field(name="User ID", value=user.id, inline=True)
    embed.add_field(name="Nickname", value=user.nick or "None", inline=True)
    embed.add_field(name="Bot", value="Yes" if user.bot else "No", inline=True)
    
    embed.add_field(name="Account Created", value=user.created_at.strftime("%B %d, %Y"), inline=True)
    embed.add_field(name="Joined Server", value=user.joined_at.strftime("%B %d, %Y"), inline=True)
    
    roles = [role.mention for role in user.roles if role.name != "@everyone"]
    embed.add_field(name=f"Roles [{len(roles)}]", value=" ".join(roles) if roles else "None", inline=False)
    
    embed.set_thumbnail(url=user.display_avatar.url)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="report", description="Report an issue with the bot.")
async def report(interaction: discord.Interaction, issue: str):
    # Create embed for the report
    embed = discord.Embed(
        title="🐛 Bug Report",
        description=issue,
        color=discord.Color.red(),
        timestamp=datetime.now()
    )
    embed.add_field(name="Reported by", value=f"{interaction.user.mention} ({interaction.user.id})")
    embed.add_field(name="Server", value=f"{interaction.guild.name} ({interaction.guild.id})")

    # Get the support channel
    support_channel = bot.get_channel(SUPPORT_CHANNEL_ID)
    
    if support_channel:
        # Send the report to the support channel
        report_message = await support_channel.send(embed=embed)

        # Create buttons for staff to interact with
        acknowledge_button = Button(label="Acknowledge", style=discord.ButtonStyle.success)
        resolve_button = Button(label="Resolve", style=discord.ButtonStyle.primary)

        async def acknowledge_callback(button_interaction: discord.Interaction):
            await button_interaction.response.send_message("Report acknowledged.", ephemeral=True)
            await report_message.add_reaction("✅")  # Add a checkmark reaction to the report message

        async def resolve_callback(button_interaction: discord.Interaction):
            await button_interaction.response.send_message("Report resolved.", ephemeral=True)
            await report_message.add_reaction("🔒")  # Add a lock reaction to indicate resolution

        acknowledge_button.callback = acknowledge_callback
        resolve_button.callback = resolve_callback

        view = View()
        view.add_item(acknowledge_button)
        view.add_item(resolve_button)

        # Edit the report message to include the buttons
        await report_message.edit(view=view)

        # Send confirmation to the user
        await interaction.response.send_message(
            "Thank you for your report! Our team will look into it.",
            ephemeral=True
        )
    else:
        await interaction.response.send_message(
            "There was an error sending your report. Please try again later.",
            ephemeral=True
        )

@bot.tree.command(name="clearall", description="Clear all messages in the channel.")
async def clear_all(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("You need administrator permissions to use this command.", ephemeral=True)
        return

    await interaction.response.send_message("Clearing all messages...", ephemeral=True)
    
    # Purge messages in the channel
    await interaction.channel.purge()
    await interaction.channel.send("All messages have been cleared.")

# ===== MAIN EXECUTION =====
def run_bot():
    try:
        observer = setup_watchdog()
        try:
            bot.run(TOKEN)
        finally:
            observer.stop()
            observer.join()
    except Exception as e:
        print(f"Error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_bot()
