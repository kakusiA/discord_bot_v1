client_id = ""
permissions = ""  # 예시: Manage Messages 권한 등이 포함된 권한 정수
invite_url = f"https://discord.com/api/oauth2/authorize?client_id={client_id}&permissions={permissions}&scope=bot"
print(invite_url)