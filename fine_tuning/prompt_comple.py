import json

input_file = "fine_tuning_data.json"  # JSONL 파일 경로
output_file = "../fine_tuning_data.jsonl"

data = []
with open(input_file, "r", encoding="utf-8") as infile:
    for line in infile:
        line = line.strip()
        if line:  # 빈 줄 무시
            data.append(json.loads(line))

with open(output_file, "w", encoding="utf-8") as outfile:
    for entry in data:
        new_entry = {
            "messages": [
                {"role": "user", "content": entry.get("prompt", "")},
                {"role": "assistant", "content": entry.get("completion", "")}
            ]
        }
        outfile.write(json.dumps(new_entry, ensure_ascii=False) + "\n")

print(f"변환이 완료되었습니다. 결과는 '{output_file}' 파일에서 확인하세요.")
