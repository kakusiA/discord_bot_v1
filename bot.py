import os
import platform
import discord
from discord.ext import commands
from dotenv import load_dotenv

# 모듈 임포트
from gpt import summarize_meeting_content, send_independent_query
from save import save_conversation_data_json
from youtube_module import search_youtube
from gpt_module import handle_gpt_request, clear_conversations, get_conversation_history
from tts_module import handle_tts, set_tts_language

# Opus 라이브러리 로드 (OS별 경로 설정)
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

# 음성 채널 연결 상태 저장 (전역 변수, on_message보다 앞에 선언)
voice_connected_guilds = set()

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # 명령어를 먼저 처리합니다.
    await bot.process_commands(message)

    # TTS 처리: tts 채널에서, 명령어가 아닌 메시지, 그리고 음성 연결 상태인 경우
    if (message.channel.name == 'tts' and
        not message.content.startswith('/') and
        message.guild.id in voice_connected_guilds):
        await handle_tts(message)

    # 회의 채널에서 대화 내용 저장 (명령어 제외)
    if message.channel.name == "회의" and not message.content.startswith('/'):
        await save_conversation_data_json(message)

    # chatgpt 채널에서 메시지 처리 (명령어 제외)
    if message.channel.name == "chatgpt" and not message.content.startswith('/'):
        ctx = await bot.get_context(message)
        await handle_gpt_request(ctx, message.content)

# 유튜브 검색 명령어: 사용자가 입력한 쿼리를 기반으로 유튜브 영상을 검색합니다.
@bot.command()
async def y(ctx, *, query=None):
    await search_youtube(ctx, query)

# 회의 요약 명령어: 회의 채널에 저장된 대화 내용을 요약하여 출력합니다.
@bot.command()
async def mtcl(ctx):
    user_id = str(ctx.author.id)
    summary = summarize_meeting_content(user_id)
    await ctx.send(summary)

# GPT 대화 명령어: 기존 대화 기록을 활용하여 GPT에게 질문을 전달합니다.
@bot.command()
async def gpt(ctx, *, query=None):
    await handle_gpt_request(ctx, query)

# 독립적 GPT 질문 명령어: 대화 기록 없이 개별적으로 GPT에 질문하여 응답을 받습니다.
@bot.command()
async def gptCl(ctx, *, query=None):
    if query is None:
        await ctx.send("질문을 입력해 주세요.")
        return
    answer = send_independent_query(query)
    await ctx.send(answer)

# 전체 채팅방 초기화 명령어: 채널을 클론하고 기존 채팅방을 삭제하여 초기화합니다.
@bot.command()
async def clearChatAll(ctx):
    new_channel = await ctx.channel.clone()
    await ctx.channel.delete()
    await new_channel.send("채팅방이 초기화되었습니다!")

# 회의 채팅방 및 회의 내용 초기화 명령어: '회의' 채널에서 채팅 내용과 회의 로그 파일을 초기화합니다.
@bot.command()
async def clearChat(ctx):
    if ctx.channel.name != "회의":
        await ctx.send("이 채널은 '회의' 채널이 아니어서 초기화할 수 없습니다.", delete_after=5)
        return

    # 채널 클론
    new_channel = await ctx.channel.clone()

    # 회의 대화내용 파일 초기화 (파일 내용을 비웁니다)
    with open("json_data/meeting_data.json", "w", encoding="utf-8") as f:
        f.write("")

    # 기존 채널 삭제 후 새 채널에 메시지 전송
    await ctx.channel.delete()
    await new_channel.send("채팅방과 회의 대화 내용이 초기화되었습니다!")

# 대화 기록 초기화 명령어: GPT 모듈에 저장된 대화 기록을 초기화합니다.
@bot.command()
async def clear(ctx):
    await clear_conversations(ctx)

# 대화 기록 확인 명령어: 지정한 갯수만큼의 대화 기록을 출력합니다.
@bot.command()
async def history(ctx, limit: int = 5):
    await get_conversation_history(ctx, limit)

# TTS 언어 설정 명령어: TTS의 언어를 설정합니다.
@bot.command(name='lang')
async def set_language(ctx, lang_code: str):
    await set_tts_language(ctx, lang_code)

# 음성 채널 접속 명령어: 사용자가 있는 음성 채널로 봇이 접속합니다.
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

# 음성 채널 종료 명령어: 봇이 연결된 음성 채널에서 나옵니다.
@bot.command(name='vc_del')
async def leave_voice_channel(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        voice_connected_guilds.discard(ctx.guild.id)
        await ctx.send("음성 채널에서 나왔습니다.")
    else:
        await ctx.send("봇이 현재 음성 채널에 연결되어 있지 않습니다.")

# TTS 재생 중지 명령어: 현재 재생 중인 TTS를 중지합니다.
@bot.command()
async def stop(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("TTS 재생을 중지했습니다.")
    else:
        await ctx.send("현재 재생 중인 TTS가 없습니다.")

# 음성 상태 업데이트 이벤트: 봇이 음성 채널에 혼자 남을 경우 자동으로 연결을 종료합니다.
@bot.event
async def on_voice_state_update(member, before, after):
    # 봇 자신인 경우나 봇이 음성 채널에서 나간 경우 무시
    if member.bot and after.channel is None:
        return

    # 음성 채널에서 멤버가 떠나서 봇만 남은 경우, 봇이 채널에서 나갑니다.
    if before.channel and before.channel != after.channel:
        voice_channel = before.channel
        connected_bot = voice_channel.guild.voice_client
        if connected_bot and len(voice_channel.members) == 1:
            await connected_bot.disconnect()
            voice_connected_guilds.discard(voice_channel.guild.id)
            print(f"Disconnected from {voice_channel.name} in {voice_channel.guild.name} due to being alone.")

bot.run(DISCORD_TOKEN)
