import os
import asyncio
from dotenv import load_dotenv
import discord
from discord.ext import commands
from discord import app_commands

# Load environment
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
WELCOME_AUDIO_PATH = os.getenv("WELCOME_AUDIO_PATH", "voice.mp3")

# Intents
intents = discord.Intents.default()
intents.voice_states = True
intents.members = True
intents.message_content = True

# Bot
bot = commands.Bot(command_prefix="!", intents=intents)

# Persistence files
TARGET_CHANNEL_FILE = "target_channel.txt"
LOG_CHANNEL_FILE = "log_channel.txt"

# Helpers for file-backed IDs
def _read_id(path: str):
    if not os.path.exists(path):
        return None
    try:
        return int(open(path, "r").read().strip())
    except Exception:
        return None

def _write_id(path: str, val: int):
    with open(path, "w") as f:
        f.write(str(val))

def get_target_channel_id():
    return _read_id(TARGET_CHANNEL_FILE)

def set_target_channel_id(channel_id: int):
    _write_id(TARGET_CHANNEL_FILE, channel_id)

def get_log_channel_id():
    return _read_id(LOG_CHANNEL_FILE)

def set_log_channel_id(channel_id: int):
    _write_id(LOG_CHANNEL_FILE, channel_id)

async def send_log(guild: discord.Guild, message: str):
    channel_id = get_log_channel_id()
    if not channel_id:
        return
    channel = guild.get_channel(channel_id)
    if channel:
        try:
            await channel.send(message)
        except Exception:
            pass

# Runtime state
bot_enabled = True

# Events
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} ({bot.user.id})")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash commands.")
    except Exception as e:
        print("Slash command sync failed:", e)
    for g in bot.guilds:
        await send_log(g, f"Bot started as {bot.user}")

@bot.event
async def on_voice_state_update(member: discord.Member, before, after):
    if member.bot:
        return
    if not bot_enabled:
        return

    target_id = get_target_channel_id()
    if not target_id:
        return

    if after.channel and after.channel.id == target_id:
        if before.channel is None or before.channel.id != target_id:
            if not os.path.exists(WELCOME_AUDIO_PATH):
                print(f"Missing welcome audio: {WELCOME_AUDIO_PATH}")
                await send_log(member.guild, f"Missing welcome audio: {WELCOME_AUDIO_PATH}")
                return
            try:
                vc = member.guild.voice_client
                if not vc:
                    vc = await after.channel.connect()
                elif vc.channel.id != target_id:
                    await vc.move_to(after.channel)
                await asyncio.sleep(1)
                if not vc.is_playing():
                    source = discord.FFmpegPCMAudio(executable="ffmpeg", source=WELCOME_AUDIO_PATH)
                    vc.play(source)
                    print(f"Playing welcome audio for {member}")
                    await send_log(member.guild, f"Played welcome audio for {member.display_name} in {after.channel.name}")
            except Exception as e:
                print("Voice error:", e)
                await send_log(member.guild, f"Voice error for {member.display_name}: {e}")

# Slash commands (admin only)
@bot.tree.command(name="setchannel", description="Set the target voice channel for welcome audio")
@app_commands.describe(channel="Voice channel to monitor")
@app_commands.checks.has_permissions(administrator=True)
async def setchannel(interaction: discord.Interaction, channel: discord.VoiceChannel):
    set_target_channel_id(channel.id)
    await interaction.response.send_message(f"Target voice channel set to: {channel.name}", ephemeral=True)
    await send_log(interaction.guild, f"Target voice channel set to {channel.name} by {interaction.user.display_name}")

@bot.tree.command(name="setlogchannel", description="Set the text channel where bot logs are sent")
@app_commands.describe(channel="Text channel for logs")
@app_commands.checks.has_permissions(administrator=True)
async def setlogchannel(interaction: discord.Interaction, channel: discord.TextChannel):
    set_log_channel_id(channel.id)
    await interaction.response.send_message(f"Log channel set to: {channel.name}", ephemeral=True)
    await send_log(interaction.guild, f"Log channel set to {channel.name} by {interaction.user.display_name}")

@bot.tree.command(name="reloadaudio", description="Check/Reload the welcome audio file")
@app_commands.checks.has_permissions(administrator=True)
async def reloadaudio(interaction: discord.Interaction):
    if os.path.exists(WELCOME_AUDIO_PATH):
        await interaction.response.send_message("Welcome audio is present.", ephemeral=True)
        await send_log(interaction.guild, f"Audio validated by {interaction.user.display_name}")
    else:
        await interaction.response.send_message("Welcome audio not found.", ephemeral=True)
        await send_log(interaction.guild, f"Audio missing (checked by {interaction.user.display_name})")

@bot.tree.command(name="togglebot", description="Enable or disable playing welcome audio")
@app_commands.checks.has_permissions(administrator=True)
async def togglebot(interaction: discord.Interaction):
    global bot_enabled
    bot_enabled = not bot_enabled
    state = "enabled" if bot_enabled else "disabled"
    await interaction.response.send_message(f"Bot is now {state}.", ephemeral=True)
    await send_log(interaction.guild, f"Bot {state} by {interaction.user.display_name}")

@bot.tree.command(name="leave", description="Disconnect the bot from voice channel")
@app_commands.checks.has_permissions(administrator=True)
async def leave(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if vc:
        await vc.disconnect()
        await interaction.response.send_message("Disconnected.", ephemeral=True)
        await send_log(interaction.guild, f"Disconnected by {interaction.user.display_name}")
    else:
        await interaction.response.send_message("I'm not connected to a voice channel.", ephemeral=True)

# App command error handler
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CheckFailure):
        await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
    else:
        try:
            await interaction.response.send_message("An error occurred while running the command.", ephemeral=True)
        except Exception:
            pass
        if interaction.guild:
            await send_log(interaction.guild, f"Command error by {interaction.user.display_name}: {error}")

if __name__ == '__main__':
    if not TOKEN:
        print("DISCORD_TOKEN not set in .env")
    else:
        bot.run(TOKEN)