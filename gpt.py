import os
import json
from dotenv import load_dotenv
from openai import OpenAI, OpenAIError

# 환경 변수 로드
load_dotenv()

# OpenAI API 키 가져오기
openai_api_key = os.getenv("OPENAI_API_KEY")

# OpenAI 클라이언트 초기화
client = OpenAI(api_key=openai_api_key)

# 대화 기록을 저장할 파일 경로
CONVERSATIONS_FILE = "conversations.json"

def load_conversations():
    """대화 기록을 파일에서 불러옵니다."""
    if os.path.exists(CONVERSATIONS_FILE):
        with open(CONVERSATIONS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_conversations(conversations):
    """대화 기록을 파일에 저장합니다."""
    with open(CONVERSATIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(conversations, f, ensure_ascii=False, indent=4)

def initialize_conversation():
    """
    대화를 초기화하고 시스템 메시지를 포함합니다.
    시스템 메시지를 통해 GPT의 동작 방식을 정의합니다.
    """
    system_message = {
        "role": "system",
        "content": (
            "당신은 이름은 도형이야. 사용자의 질문에 정확하고 간결하게 답변하며, "
            "필요한 경우 예시를 들어 설명합니다."
        )
    }
    return [system_message]

def send_to_chatGpt(user_id, query):
    """
    GPT에게 메시지를 전송하고 응답을 반환합니다.
    사용자별로 대화 기록을 관리합니다.

    Parameters:
    - user_id (str): Discord 사용자 ID
    - query (str): 사용자의 질문

    Returns:
    - str: GPT의 응답 내용
    """
    # 대화 기록 불러오기
    conversations = load_conversations()

    # 사용자별 대화 기록 초기화
    if user_id not in conversations:
        conversations[user_id] = initialize_conversation()

    messages = conversations[user_id]

    # 사용자 메시지 추가
    user_message = {"role": "user", "content": query}
    messages.append(user_message)

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=1000,
            temperature=0.5,
        )
        message_content = response.choices[0].message.content.strip()

        # GPT의 응답을 메시지 목록에 추가
        gpt_message = {"role": "assistant", "content": message_content}
        messages.append(gpt_message)

        # 대화 기록 저장
        conversations[user_id] = messages
        save_conversations(conversations)

        return message_content
    except OpenAIError as e:
        print(f"OpenAI API 호출 중 오류 발생: {e}")
        return "죄송합니다. 현재 서버에 문제가 발생했습니다."


