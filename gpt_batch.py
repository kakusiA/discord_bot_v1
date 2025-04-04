import os
import json
from dotenv import load_dotenv
from openai import OpenAI, OpenAIError
from celery import Celery

# 환경 변수 로드
load_dotenv()

# OpenAI API 키 가져오기
openai_api_key = os.getenv("OPENAI_API_KEY")

# OpenAI 클라이언트 초기화
client = OpenAI(api_key=openai_api_key)

# Celery 앱 설정 (예: Redis 브로커 사용)
celery_app = Celery('gpt_batch', broker='redis://localhost:6379/0')

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
        "content": "당신은 회의 내용을 요약하는 전문가입니다. 회의 대화의 주요 논의사항, 결정사항, 그리고 후속 작업을 불릿 포인트로 정리해 주세요."
    }
    return [system_message]

def send_to_chatGpt(user_id, query):
    """
    GPT에게 메시지를 전송하고 응답을 반환합니다.
    사용자별로 대화 기록을 관리합니다.
    """
    conversations = load_conversations()

    if user_id not in conversations:
        conversations[user_id] = initialize_conversation()

    messages = conversations[user_id]
    user_message = {"role": "user", "content": query}
    messages.append(user_message)

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # 실제 사용 모델에 맞게 조정
            messages=messages,
            max_tokens=1000,
            temperature=0.5,
        )
        message_content = response.choices[0].message.content.strip()
        gpt_message = {"role": "assistant", "content": message_content}
        messages.append(gpt_message)
        conversations[user_id] = messages
        save_conversations(conversations)
        return message_content
    except OpenAIError as e:
        print(f"OpenAI API 호출 중 오류 발생: {e}")
        return "죄송합니다. 현재 서버에 문제가 발생했습니다."

@celery_app.task
def batch_summarize_meeting(user_id, meeting_file="회의_대화내용.json"):
    """
    NDJSON 형식의 회의 대화 내용을 읽어 하나의 텍스트로 결합한 후,
    ChatGPT에게 요약 요청을 보내고 그 결과를 반환하는 배치 작업입니다.
    """
    if not os.path.exists(meeting_file):
        return "회의 내용 파일이 존재하지 않습니다."

    meeting_logs = []
    try:
        with open(meeting_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    meeting_logs.append(json.loads(line))
    except Exception as e:
        print(f"파일 로드 에러: {e}")
        return "회의 내용을 불러오는 데 실패했습니다."

    conversation_text = "\n".join(
        [f"{msg['timestamp']} - {msg['author']}: {msg['content']}" for msg in meeting_logs]
    )

    summarization_prompt = (
        "당신은 회의 내용을 요약하는 전문가입니다.\n"
        "다음 회의 대화 내용을 분석하여, 주요 논의 사항, 결정된 사항, 그리고 추후 진행해야 할 작업이나 질문을 "
        "불릿 포인트 형식으로 명확하게 정리해 주세요.\n"
        "각 항목에 대해 간단한 설명도 덧붙여 주세요.\n\n"
        f"{conversation_text}"
    )

    summary = send_to_chatGpt(user_id, summarization_prompt)
    return summary
