import discord
import asyncio
import os
from dotenv import load_dotenv
from discord.ext import commands

# --- CONFIGURATION ---
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
WELCOME_AUDIO_PATH = 'voice.mp3'
TARGET_CHANNEL_ID = YOUR_CHANNEL_ID_HERE # <--- ENSURE THIS IS CORRECT

intents = discord.Intents.default()
intents.voice_states = True
intents.members = True
intents.message_content = True # Fixes the "Privileged intent" warning

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    print('------')

@bot.event
async def on_voice_state_update(member, before, after):
    if member.bot:
        return

    # Check if the user joined the target support channel
    if after.channel and after.channel.id == TARGET_CHANNEL_ID:
        # Only trigger if they weren't in this specific channel already
        if before.channel is None or before.channel.id != TARGET_CHANNEL_ID:
            
            if not os.path.exists(WELCOME_AUDIO_PATH):
                print(f"Error: {WELCOME_AUDIO_PATH} not found.")
                return

            try:
                vc = member.guild.voice_client

                # Join or Move
                if not vc:
                    vc = await after.channel.connect()
                elif vc.channel.id != TARGET_CHANNEL_ID:
                    await vc.move_to(after.channel)

                # Small delay to let the handshake finish
                await asyncio.sleep(1)

                if not vc.is_playing():
                    # CLEANED FFMPEG CALL: No extra options to avoid host errors
                    source = discord.FFmpegPCMAudio(
                        executable="ffmpeg", 
                        source=WELCOME_AUDIO_PATH
                    )
                    
                    vc.play(source)
                    print(f"Successfully started audio for {member.name}")

            except Exception as e:
                print(f"Voice Error: {e}")

@bot.command()
async def leave(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("Leaving.")

bot.run(TOKEN)