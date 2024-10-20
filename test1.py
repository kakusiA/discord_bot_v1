import os
import discord
from discord.ext import commands
from discord import opus
import ctypes
from dotenv import load_dotenv
from gpt import send_to_chatGpt, load_conversations, save_conversations, initialize_conversation
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from gtts import gTTS, lang as gtts_lang
import asyncio
import json
import platform

# Opus 라이브러리 로드
OPUS_LIBRARY_PATH = {
    "Darwin": "/opt/homebrew/lib/libopus.0.dylib",  # macOS
    "Windows": "C:\discord_bot\libopus-0\libopus-0.dll"  # Windows용 라이브러리 경로
}

system_platform = platform.system()

if system_platform in OPUS_LIBRARY_PATH:
    try:
        opus.load_opus(OPUS_LIBRARY_PATH[system_platform])
    except Exception as e:
        print(f"Error loading Opus library for {system_platform}: {e}")
else:
    print("Opus library path not specified for this OS.")

# 환경 변수를 .env 파일에서 로드
load_dotenv()

DISCORD_TOKEN = os.getenv('discord_token')
YOUTUBE_API_KEY = os.getenv('youtube_api_key')

# YouTube API 클라이언트 초기화
youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)

# 길드별 언어 설정을 저장할 딕셔너리
LANGUAGES_FILE = 'guild_languages.json'

if os.path.exists(LANGUAGES_FILE):
    with open(LANGUAGES_FILE, 'r', encoding='utf-8') as f:
        guild_languages = json.load(f)
else:
    guild_languages = {}

# Discord 봇 인텐트 설정
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.message_content = True
intents.voice_states = True
intents.members = True

# Discord 봇 초기화
bot = commands.Bot(command_prefix='/', intents=intents)

@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user.name}')

@bot.command()
async def y(ctx, *, query=None):
    if not query:
        await ctx.send("검색할 유튜브 제목을 입력해주세요.")
        return
    try:
        # YouTube 검색 수행
        search_response = youtube.search().list(
            q=query,
            part='id,snippet',
            maxResults=1,
            type='video'
        ).execute()

        items = search_response.get('items', [])
        if not items:
            await ctx.send("검색 결과가 없습니다.")
            return

        video = items[0]
        video_id = video['id']['videoId']
        video_title = video['snippet']['title']
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        await ctx.send(f"**{video_title}**\n{video_url}")
    except HttpError as e:
        print(f"An HTTP error {e.resp.status} occurred:\n{e.content}")
        await ctx.send("유튜브 검색 중 오류가 발생했습니다.")

@bot.command()
async def gpt(ctx, *, query=None):
    if not query:
        await ctx.send("질문을 해주세요.")
        return

    user_id = str(ctx.author.id)

    try:
        # OpenAI API에 메시지 전송 (비동기로 실행)
        response = await asyncio.to_thread(send_to_chatGpt, user_id, query)
    except Exception as e:
        print(f"GPT 요청 중 오류 발생: {e}")
        await ctx.send("GPT 요청 중 오류가 발생했습니다.")
        return

    await ctx.send(response)

    if ctx.voice_client is not None:
        try:
            language = guild_languages.get(str(ctx.guild.id), 'ko')

            tts = await asyncio.to_thread(gTTS, text=response, lang=language)
            tts_file = f"chat_response_{ctx.guild.id}.mp3"
            await asyncio.to_thread(tts.save, tts_file)

            if ctx.voice_client.is_playing():
                ctx.voice_client.stop()

            def after_playing(error):
                if error:
                    print(f"Error occurred during playback: {error}")
                if os.path.exists(tts_file):
                    os.remove(tts_file)

            ffmpeg_executable = {
                "Darwin": "/opt/homebrew/bin/ffmpeg",
                "Windows": "ffmpeg"  # Windows 환경에서 ffmpeg가 PATH에 있어야 함
            }.get(platform.system())

            ctx.voice_client.play(
                discord.FFmpegPCMAudio(tts_file, executable=ffmpeg_executable),
                after=after_playing
            )
        except Exception as e:
            print(f"TTS 재생 중 오류 발생: {e}")
            await ctx.send("음성 재생 중 오류가 발생했습니다.")

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
    if ctx.voice_client is not None and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("TTS 재생을 중지했습니다.")
    else:
        await ctx.send("현재 재생 중인 TTS가 없습니다.")

@bot.command()
async def clear(ctx):
    user_id = str(ctx.author.id)
    conversations = load_conversations()

    if user_id in conversations:
        conversations[user_id] = initialize_conversation()
        save_conversations(conversations)
        await ctx.send("대화 기록이 초기화되었습니다.")
    else:
        await ctx.send("대화 기록이 존재하지 않습니다.")

@bot.command()
async def history(ctx, limit: int = 5):
    user_id = str(ctx.author.id)
    conversations = load_conversations()

    if user_id not in conversations:
        await ctx.send("대화 기록이 존재하지 않습니다.")
        return

    messages = conversations[user_id]
    recent_messages = messages[-(limit * 2):]

    history = ""
    for message in recent_messages:
        if message['role'] == 'user':
            history += f"**User:** {message['content']}\n"
        elif message['role'] == 'assistant':
            history += f"**GPT:** {message['content']}\n"

    await ctx.send(f"**최근 {limit}개의 대화 기록:**\n{history}")

@bot.command(name='언어')
async def set_language(ctx, lang_code: str):
    supported_langs = gtts_lang.tts_langs()

    if lang_code not in supported_langs:
        available_langs = ', '.join([f"{code} ({name})" for code, name in supported_langs.items()])
        await ctx.send(f"지원되지 않는 언어 코드입니다. 사용 가능한 언어 코드는 다음과 같습니다:\n{available_langs}")
        return

    guild_languages[str(ctx.guild.id)] = lang_code
    with open(LANGUAGES_FILE, 'w', encoding='utf-8') as f:
        json.dump(guild_languages, f, ensure_ascii=False, indent=4)

    language_name = supported_langs[lang_code]
    await ctx.send(f"TTS 언어가 {language_name}({lang_code})으로 설정되었습니다.")

queue = asyncio.Queue()

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    await bot.process_commands(message)

    if message.channel.name == 'tts':
        await queue.put((message.content, message))
        if not hasattr(bot, 'tts_processing') or not bot.tts_processing:
            bot.tts_processing = True
            bot.loop.create_task(process_queue())

async def process_queue():
    while not queue.empty():
        text, message = await queue.get()
        await handle_tts(text, message)
    bot.tts_processing = False

async def handle_tts(text, message):
    voice_client = message.guild.voice_client
    if voice_client is None:
        if message.author.voice:
            voice_channel = message.author.voice.channel
            try:
                await voice_channel.connect()
                voice_client = message.guild.voice_client
            except Exception as e:
                print(f"음성 채널 연결 중 오류 발생: {e}")
                await message.channel.send("음성 채널에 연결하는 중 오류가 발생했습니다.")
                return
        else:
            await message.channel.send("음성 채널에 먼저 접속해주세요.")
            return

    language = guild_languages.get(str(message.guild.id), 'ko')
    tts_file = f"tts_audio_{message.guild.id}.mp3"

    try:
        tts = gTTS(text=text, lang=language)
        await asyncio.to_thread(tts.save, tts_file)

        if voice_client.is_playing() or voice_client.is_paused():
            voice_client.stop()

        def after_playing(error):
            if error:
                print(f"Error occurred during playback: {error}")
            if os.path.exists(tts_file):
                os.remove(tts_file)

        ffmpeg_executable = {
            "Darwin": "/opt/homebrew/bin/ffmpeg",
            "Windows": r"C:\ffmpeg\bin\ffmpeg.exe"
        }.get(platform.system())

        voice_client.play(
            discord.FFmpegPCMAudio(tts_file, executable=ffmpeg_executable),
            after=after_playing
        )
    except Exception as e:
        print(f"TTS 재생 중 오류 발생: {e}")
        await message.channel.send("TTS 변환 또는 재생 중 오류가 발생했습니다.")

bot.run(DISCORD_TOKEN)
