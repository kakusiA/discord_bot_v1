import json

# 두 JSON 파일을 읽습니다.
with open("filtered_messages.json", "r", encoding="utf-8") as f1:
    data1 = json.load(f1)

with open("filtered_messages1.json", "r", encoding="utf-8") as f2:
    data2 = json.load(f2)

# 두 파일의 데이터가 리스트라고 가정하고 병합합니다.
merged_data = data1 + data2

# 병합된 데이터를 새로운 JSON 파일로 저장합니다.
with open("../merged_messages.json", "w", encoding="utf-8") as outfile:
    json.dump(merged_data, outfile, ensure_ascii=False, indent=4)

print("두 JSON 파일이 병합되었습니다. 결과는 'merged_messages.json' 파일을 확인하세요.")
