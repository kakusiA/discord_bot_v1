import json
import os
import asyncio
from gtts import gTTS, lang as gtts_lang
import platform
import discord

LANGUAGES_FILE = 'guild_languages.json'

# 서버 별 언어 저장
if os.path.exists(LANGUAGES_FILE):
    with open(LANGUAGES_FILE, 'r', encoding='utf-8') as f:
        guild_languages = json.load(f)
else:
    guild_languages = {}


async def set_tts_language(ctx, lang_code):
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


async def handle_tts(message):
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

    language = guild_languages.get(str(message.guild.id), 'ko')  # 기본값을 영어로 설정
    tts_file = f"tts_audio_{message.guild.id}.mp3"

    print(f"파일 저장 경로: {os.path.abspath(tts_file)}")

    try:
        tts = gTTS(text=message.content, lang=language)
        await asyncio.to_thread(tts.save, tts_file)

        # if not os.path.exists(tts_file):
        #     await message.channel.send(f"TTS 파일 저장에 실패했습니다. 경로: {os.path.abspath(tts_file)}")
        #     return

        if voice_client.is_playing() or voice_client.is_paused():
            voice_client.stop()

        ffmpeg_executable = {
            "Darwin": "/opt/homebrew/bin/ffmpeg",
            "Windows": r"C:\ffmpeg\bin\ffmpeg.exe"
        }.get(platform.system())

        if not ffmpeg_executable or not os.path.exists(ffmpeg_executable):
            await message.channel.send("FFmpeg 실행 파일을 찾을 수 없습니다. 시스템에 FFmpeg가 설치되어 있는지 확인해주세요.")
            return

        play_complete = asyncio.Event()

        def after_playing(error):
            if error:
                print(f"Error occurred during playback: {error}")
            play_complete.set()  # 재생 완료
            print("재생 완료 후 FFmpeg 종료 대기 중...")

        voice_client.play(
            discord.FFmpegPCMAudio(tts_file, executable=ffmpeg_executable),
            after=after_playing
        )

        # TTS 재생 완료 대기
        await play_complete.wait()

        # 파일 삭제 (종료 후 확인)
        if os.path.exists(tts_file):
            try:
                os.remove(tts_file)
                print(f"TTS 파일 삭제 완료: {tts_file}")
            except Exception as e:
                print(f"TTS 파일 삭제 중 오류 발생: {e}")

    except Exception as e:
        await message.channel.send("TTS 변환 또는 재생 중 오류가 발생했습니다.")
        print(f"TTS 재생 중 오류 발생: {e}")
