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
#TTS봇 나가기
@bot.event
async def on_voice_state_update(member, before, after):
    """
    음성 상태 변경 이벤트 처리
    """
    # 봇 자신인지 확인
    if member.bot and after.channel is None:
        return  # 봇이 음성 채널에서 나간 경우는 무시

    # 음성 채널에 남은 멤버 확인
    if before.channel and before.channel != after.channel:
        voice_channel = before.channel
        connected_bot = voice_channel.guild.voice_client

        # 봇이 음성 채널에 있고, 혼자 남아 있다면 나가기
        if connected_bot and len(voice_channel.members) == 1:
            await connected_bot.disconnect()
            voice_connected_guilds.discard(voice_channel.guild.id)
            print(f"Disconnected from {voice_channel.name} in {voice_channel.guild.name} due to being alone.")

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

@bot.command(name='lang')
async def set_language(ctx, lang_code: str):
    await set_tts_language(ctx, lang_code)
# 음성 채널 연결 상태 저장
voice_connected_guilds = set()

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
        # 음성 채널에 연결된 길드 ID 저장
    voice_connected_guilds.add(ctx.guild.id)
    await ctx.send(f"{voice_channel.name} 채널에 입장했습니다.")

@bot.command(name='vc_del')
async def leave_voice_channel(ctx):
    if ctx.voice_client:  # 봇이 음성 채널에 연결되어 있는 경우
        await ctx.voice_client.disconnect()
        # 음성 채널 연결 상태 제거
        voice_connected_guilds.discard(ctx.guild.id)
        await ctx.send("음성 채널에서 나왔습니다.")
    else:  # 봇이 음성 채널에 연결되어 있지 않은 경우
        await ctx.send("봇이 현재 음성 채널에 연결되어 있지 않습니다.")

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

    # 명령어를 처리
    await bot.process_commands(message)

    # 음성 채널 연결 상태 확인 및 TTS 처리
    if (
        message.channel.name == 'tts'  # TTS 채널 확인
        and not message.content.startswith('/')  # 명령어 제외
        and message.guild.id in voice_connected_guilds  # 음성 채널에 연결된 상태인지 확인
    ):
        await handle_tts(message)

bot.run(DISCORD_TOKEN)
