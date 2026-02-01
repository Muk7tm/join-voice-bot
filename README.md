# Join Voice Bot (Discord)

A Discord bot that automatically joins a specific voice channel and plays a welcome audio message when a user joins. Perfect for support channels or community servers!

## Features
- Automatically joins a designated voice channel when a user joins
- Plays a custom welcome audio file (MP3)
- Simple `!leave` command to disconnect the bot
- Easy configuration with environment variables

## Setup

### 1. Clone the repository
```bash
git clone https://github.com/yourusername/join-voice-bot-discord.git
cd join-voice-bot-discord
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Prepare your `.env` file
Create a `.env` file in the project root:
```
DISCORD_TOKEN=your-bot-token-here
```

### 4. Add your welcome audio
Place your `voice.mp3` file in the project root. This is the audio that will play when a user joins the target channel.

### 5. Set your target channel
Edit `app.py` and set the `TARGET_CHANNEL_ID` to your desired voice channel's ID.

## Usage
Run the bot with:
```bash
python app.py
```

Invite the bot to your server and join the specified voice channel. The bot will join and play the welcome audio!

Use `!leave` in any text channel to make the bot disconnect from the voice channel.

## Requirements
- Python 3.8+
- FFmpeg installed and available in your system PATH

## Environment Variables
- `DISCORD_TOKEN`: Your Discord bot token (keep this secret!)

## Security
- The `.env` file is included in `.gitignore` and will not be published to GitHub.
- **Never share your bot token publicly.**

## License
MIT

---

Made with ❤️ for Discord communities!
