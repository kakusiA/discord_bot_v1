import json
import os
import asyncio
from gtts import gTTS, lang as gtts_lang
import platform
import discord

LANGUAGES_FILE = 'guild_languages.json'

# 서버별 TTS 언어 설정을 저장/불러오기
if os.path.exists(LANGUAGES_FILE):
    with open(LANGUAGES_FILE, 'r', encoding='utf-8') as f:
        guild_languages = json.load(f)
else:
    guild_languages = {}

# 각 길드별 TTS 메시지 큐를 저장하는 전역 변수
tts_queues = {}
# 각 길드별로 큐 처리가 진행 중인지 여부를 나타내는 플래그
tts_processing = {}

async def set_tts_language(ctx, lang_code):
    """
    TTS 언어 설정 함수.
    - ctx: 명령어가 실행된 컨텍스트
    - lang_code: 사용자가 설정할 언어 코드
    """
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

async def generate_tts_audio(message):
    """
    주어진 메시지에 대해 TTS 오디오 파일을 생성하고, 파일 경로를 반환합니다.
    파일 이름은 고유하게 message.id를 사용합니다.
    """
    guild_id = str(message.guild.id)
    language = guild_languages.get(guild_id, 'ko')
    # 고유 파일명 생성 (메시지 ID 사용)
    filename = f"tts_audio_{guild_id}_{message.id}.mp3"
    try:
        tts = gTTS(text=message.content, lang=language)
        # gTTS 저장 작업을 별도의 스레드에서 실행하여 블로킹을 피함
        await asyncio.to_thread(tts.save, filename)
        return filename
    except Exception as e:
        print(f"TTS 파일 생성 오류: {e}")
        return None

async def process_tts_queue(guild, voice_client):
    """
    해당 길드의 TTS 큐에 쌓인 메시지들을 순차적으로 재생합니다.
    동시에 하나의 프로세싱만 진행되도록 보장합니다.
    """
    guild_id = str(guild.id)
    if tts_processing.get(guild_id, False):
        return
    tts_processing[guild_id] = True
    queue = tts_queues.get(guild_id)
    while not queue.empty():
        message, audio_future = await queue.get()
        # 기다려서 오디오 파일 생성 완료
        filename = await audio_future
        if not filename:
            await message.channel.send("TTS 오디오 파일 생성에 실패했습니다.")
            queue.task_done()
            continue

        ffmpeg_executable = {
            "Darwin": "/opt/homebrew/bin/ffmpeg",
            "Windows": r"C:\ffmpeg\bin\ffmpeg.exe"
        }.get(platform.system())

        if not ffmpeg_executable or not os.path.exists(ffmpeg_executable):
            await message.channel.send("FFmpeg 실행 파일을 찾을 수 없습니다. 시스템에 FFmpeg가 설치되어 있는지 확인해주세요.")
            queue.task_done()
            continue

        play_complete = asyncio.Event()

        def after_playing(error):
            if error:
                print(f"오디오 재생 중 오류 발생: {error}")
            play_complete.set()

        try:
            # 재생 전에 음성 클라이언트의 현재 재생 상태를 확인하지 않고,
            # 순차 재생을 위해 queue에서 하나씩 처리합니다.
            source = discord.FFmpegPCMAudio(filename, executable=ffmpeg_executable)
            voice_client.play(source, after=after_playing)
            await play_complete.wait()
        except Exception as e:
            await message.channel.send("오디오 재생 중 오류가 발생했습니다.")
            print(f"오디오 재생 오류: {e}")

        # 재생 후 파일 삭제
        if os.path.exists(filename):
            try:
                os.remove(filename)
                print(f"오디오 파일 삭제 완료: {filename}")
            except Exception as e:
                print(f"오디오 파일 삭제 중 오류 발생: {e}")
        queue.task_done()
    tts_processing[guild_id] = False

async def handle_tts(message):
    """
    TTS 요청 처리 함수.
    사용자가 TTS 채널에 입력한 메시지를 해당 길드의 큐에 추가하고,
    큐에 쌓인 메시지를 순차적으로 재생합니다.
    """
    voice_client = message.guild.voice_client
    if voice_client is None:
        if message.author.voice:
            voice_channel = message.author.voice.channel
            try:
                await voice_channel.connect()
                voice_client = message.guild.voice_client
            except Exception as e:
                print(f"음성 채널 연결 오류: {e}")
                await message.channel.send("음성 채널에 연결하는 중 오류가 발생했습니다.")
                return
        else:
            await message.channel.send("먼저 음성 채널에 접속해주세요.")
            return

    guild_id = str(message.guild.id)
    if guild_id not in tts_queues:
        tts_queues[guild_id] = asyncio.Queue()

    # TTS 파일 생성 작업을 즉시 시작 (병렬 실행)
    audio_future = asyncio.create_task(generate_tts_audio(message))
    await tts_queues[guild_id].put((message, audio_future))

    # 처리 중이 아니라면 큐 처리를 시작
    if not tts_processing.get(guild_id, False):
        await process_tts_queue(message.guild, voice_client)
