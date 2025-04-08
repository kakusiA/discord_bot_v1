import json
import re

def filter_content(content):
    # 정규표현식을 사용하여 문장 단위로 분리 (문장 구분자: . ! ?)
    sentences = re.split(r'(?<=[.!?])\s+', content)
    filtered_sentences = []
    for sentence in sentences:
        stripped = sentence.strip()
        # "@"가 포함된 문장, "/" 또는 "http"로 시작하는 문장은 건너뜁니다.
        if "@" in stripped or stripped.startswith("/") or stripped.startswith("http"):
            continue
        filtered_sentences.append(sentence)
    # 필터링된 문장들을 다시 하나의 문자열로 합칩니다.
    return " ".join(filtered_sentences)

# 기존 JSON 파일 읽기
with open("../messages1.json", "r", encoding="utf-8") as infile:
    messages = json.load(infile)

# 각 메시지의 content 필드를 필터링 처리
for message in messages:
    original_content = message.get("content", "")
    message["content"] = filter_content(original_content)

# 결과를 새로운 JSON 파일로 저장
with open("filtered_messages1.json", "w", encoding="utf-8") as outfile:
    json.dump(messages, outfile, ensure_ascii=False, indent=4)

print("필터링이 완료되었습니다. 'filtered_messages.json' 파일을 확인하세요.")
