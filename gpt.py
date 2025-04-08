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
        "content": ()
    }
    return [system_message]
# 요약을 위한 gpt
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


def send_independent_query(query, ctx=None):
    """
    대화 기록 없이 독립적으로 GPT 응답을 받아옵니다.
    (ctx는 호출 환경 정보를 위해 optional로 받지만 사용되지는 않습니다.)
    """
    system_message = {
        "role": "system",
        "content": "너의 이름은 도형이야"
        # "content": "정확한 정보를 나에게줘 틀린정보를 주면안되 모르면 모른다고해"
    }
    messages = [
        system_message,
        {"role": "user", "content": query}
    ]
    try:
        response = client.chat.completions.create(
            model="ft:gpt-4o-mini-2024-07-18:personal::BJbo7ZWN",  # 실제 사용 모델명으로 조정
            messages=messages,
            max_tokens=1000,
            temperature=0.5,
        )
        answer = response.choices[0].message.content.strip()
        return answer
    except OpenAIError as e:
        print(f"OpenAI API 호출 중 오류 발생: {e}")
        return "죄송합니다. 현재 서버에 문제가 발생했습니다."


def summarize_meeting_content(user_id, meeting_file="회의_대화내용.json"):
    """
    NDJSON 형식으로 저장된 회의 대화 내용을 읽어 하나의 텍스트로 결합하고,
    ChatGPT에게 요약 요청을 보낸 후 요약 결과를 반환합니다.
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

    # 각 메시지를 "타임스탬프 - 작성자: 내용" 형태로 결합
    conversation_text = "\n".join(
        [f"{msg['timestamp']} - {msg['author']}: {msg['content']}" for msg in meeting_logs]
    )

    # 요약 요청 프롬프트 구성
    # summarization_prompt = f"당신은 회의 내용을 요약하는 전문가야 다음 회의 내용을 요약해줘:\n\n{conversation_text}"
    # 보다 구체적인 프롬프트 구성
    summarization_prompt = (
        "당신은 회의 내용을 요약하는 전문가입니다.\n"
        "다음 회의 대화 내용을 분석하여, 주요 논의 사항, 결정된 사항, 그리고 추후 진행해야 할 작업이나 질문을 "
        "불릿 포인트 형식으로 명확하게 정리해 주세요.\n"
        "가능하면 각 항목에 대해 간단한 설명도 덧붙여 주세요.\n\n"
        f"{conversation_text}"
    )
    # 요약 요청
    summary = send_to_chatGpt(user_id, summarization_prompt)
    return summary
