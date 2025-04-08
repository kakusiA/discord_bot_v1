import json

import discord
import asyncio
from dotenv import load_dotenv
import os
# 환경 변수 로드
load_dotenv()
DISCORD_TOKEN = os.getenv('discord_token')
json1 = "messages1244"
intents = discord.Intents.default()
intents.message_content = True  # 메시지 내용을 읽기 위한 권한 활성화
client = discord.Client(intents=intents)

# 대상 채널 ID와 유저 ID를 설정합니다.
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))  # '일반' 채널의 ID
TARGET_USER_ID = int(os.getenv("TARGET_USER_ID"))  # 대상 유저의 ID

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')
    channel = client.get_channel(CHANNEL_ID)
    if channel is None:
        print("채널을 찾을 수 없습니다.")
        await client.close()
        return

    messages_data = []
    # 채널의 메시지를 역순(최신 메시지부터)으로 가져옵니다. limit 값을 조정해 주세요.
    async for message in channel.history(limit=1000):
        # if message.author.id == TARGET_USER_ID:
        messages_data.append({
            "message_id": message.id,
            "author_id": message.author.id,
            "author_name": str(message.author),
            "content": message.content,
            "created_at": message.created_at.isoformat()  # ISO 포맷으로 날짜 저장
        })

    # JSON 파일로 저장합니다.
    with open(f"json_data/{json1}.json", "w", encoding="utf-8") as f:
        json.dump(messages_data, f, ensure_ascii=False, indent=4)

    print(f"총 {len(messages_data)}개의 메시지를 {json1}.json 파일에 저장했습니다.")
    await client.close()

client.run(DISCORD_TOKEN)
