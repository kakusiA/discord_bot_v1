import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import asyncio
import platform
from youtube_module import search_youtube
from gpt_module import handle_gpt_request, clear_conversations, get_conversation_history
from tts_module import handle_tts, set_tts_language, guild_languages

# Opus 라이브러리 로드
OPUS_LIBRARY_PATH = {
    "Darwin": "/opt/homebrew/lib/libopus.0.dylib",
    "Windows": "C:\\discord_bot\\libopus-0\\libopus-0.dll"
}

system_platform = platform.system()

if system_platform in OPUS_LIBRARY_PATH:
    try:
        discord.opus.load_opus(OPUS_LIBRARY_PATH[system_platform])
    except Exception as e:
        print(f"Error loading Opus library for {system_platform}: {e}")
else:
    print("Opus library path not specified for this OS.")

# 환경 변수 로드
load_dotenv()
DISCORD_TOKEN = os.getenv('discord_token')

# Discord 봇 인텐트 설정
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.message_content = True
intents.voice_states = True
intents.members = True

bot = commands.Bot(command_prefix='/', intents=intents)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')

@bot.command()
async def y(ctx, *, query=None):
    await search_youtube(ctx, query)

@bot.command()
async def gpt(ctx, *, query=None):
    await handle_gpt_request(ctx, query)

@bot.command()
async def clear(ctx):
    await clear_conversations(ctx)

@bot.command()
async def history(ctx, limit: int = 5):
    await get_conversation_history(ctx, limit)

@bot.command(name='언어')
async def set_language(ctx, lang_code: str):
    await set_tts_language(ctx, lang_code)

@bot.command()
async def vc(ctx):
    if ctx.author.voice is None:
        await ctx.send("음성 채널에 먼저 입장해주세요.")
        return

    voice_channel = ctx.author.voice.channel
    if ctx.voice_client is not None:
        await ctx.voice_client.move_to(voice_channel)
    else:
        await voice_channel.connect()

    await ctx.send(f"{voice_channel.name} 채널에 입장했습니다.")

@bot.command()
async def stop(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("TTS 재생을 중지했습니다.")
    else:
        await ctx.send("현재 재생 중인 TTS가 없습니다.")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    await bot.process_commands(message)

    if message.channel.name == 'tts':
        await handle_tts(message)

bot.run(DISCORD_TOKEN)
