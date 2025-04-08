import json


async def save_conversation_data_json(message):
    """회의 채널의 메시지를 JSON 형식으로 저장하는 함수 (NDJSON 형식)"""
    message_data = {
        "timestamp": message.created_at.isoformat(),
        "author": str(message.author),
        "content": message.content
    }
    with open("json_data/meeting_data.json", "a", encoding="utf-8") as f:
        json.dump(message_data, f, ensure_ascii=False)
        f.write("\n")  # 각 메시지를 새로운 줄에 기록