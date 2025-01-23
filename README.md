# Discord Meme Bot

![Discord Meme Bot](https://img.shields.io/badge/Discord-Bot-blue?style=flat&logo=discord)

A fun and interactive Discord bot that fetches and posts memes from Reddit, provides random jokes, and offers various commands for user engagement. This bot is designed to enhance your Discord server with entertaining content.

## Features

- **Meme Posting**: Automatically posts memes from specified subreddits at set intervals.
- **Random Jokes**: Fetches and posts random jokes on command.
- **Command History**: Keeps track of the last 30 commands used.
- **Server and User Info**: Provides detailed information about the server and users.
- **Interactive Buttons**: Utilizes Discord's UI components for a better user experience.
- **Error Reporting**: Allows users to report issues directly to the support team.

## Requirements

- Python 3.8 or higher
- `discord.py` library
- `asyncpraw` for Reddit API interaction
- `watchdog` for file change detection
- `requests` for fetching jokes

## Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/discord-meme-bot.git
   cd discord-meme-bot
   ```

2. **Install the required packages**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up your environment variables**:
   - Create a `.env` file in the root directory and add your Discord bot token and Reddit API credentials:
     ```
     DISCORD_TOKEN=your_discord_token
     REDDIT_CLIENT_ID=your_reddit_client_id
     REDDIT_CLIENT_SECRET=your_reddit_client_secret
     ```

4. **Run the bot**:
   ```bash
   python Bot.py
   ```

## Commands

Here are some of the commands you can use with the bot:

### Meme Commands
- `/meme [subreddit]`: Fetch and post a meme from a specific subreddit (default: r/memes).
- `/meme_search <keyword>`: Search for memes with specific keywords.
- `/top_memes [timeframe] [count]`: Get top memes from a specified timeframe (day, week, month, year).
- `/setchannel [channel] [search_query] [interval]`: Set a channel for auto-posting memes.
- `/stopmemes [channel]`: Stop posting memes in a specified channel.
- `/startmemes [channel] [subreddit_name]`: Resume posting memes in a specified channel.

### Fun Commands
- `/random_joke [channel]`: Fetch and post a random joke in a specified channel.
- `/ping`: Check the bot's latency.

### Information Commands
- `/serverinfo`: Display information about the server.
- `/userinfo [user]`: Show information about a specified user.
- `/stats`: Show bot statistics.
- `/command_history`: View the history of commands used.

### Utility Commands
- `/invite`: Get the invite link to add the bot to your server.
- `/report <issue>`: Report an issue with the bot.
- `/sync`: Sync bot commands (Admin only).

## Contributing

Contributions are welcome! If you have suggestions for improvements or new features, feel free to open an issue or submit a pull request.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [discord.py](https://discordpy.readthedocs.io/en/stable/) - The library used to interact with the Discord API.
- [asyncpraw](https://asyncpraw.readthedocs.io/en/latest/) - The library used to interact with the Reddit API.
- [Watchdog](https://pypi.org/project/watchdog/) - A library to monitor file system events.

## Contact

For any inquiries or support, please reach out to [your_email@example.com](mailto:your_email@example.com).
