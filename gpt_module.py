import asyncio
from gpt import send_to_chatGpt, load_conversations, save_conversations, initialize_conversation

async def handle_gpt_request(ctx, query):
    if not query:
        await ctx.send("질문을 해주세요.")
        return

    user_id = str(ctx.author.id)
    try:
        response = await asyncio.to_thread(send_to_chatGpt, user_id, query)
        await ctx.send(response)
    except Exception as e:
        await ctx.send("GPT 요청 중 오류가 발생했습니다.")
        print(f"GPT 요청 중 오류 발생: {e}")

async def clear_conversations(ctx):
    user_id = str(ctx.author.id)
    conversations = load_conversations()

    if user_id in conversations:
        conversations[user_id] = initialize_conversation()
        save_conversations(conversations)
        await ctx.send("대화 기록이 초기화되었습니다.")
    else:
        await ctx.send("대화 기록이 존재하지 않습니다.")

async def get_conversation_history(ctx, limit: int):
    user_id = str(ctx.author.id)
    conversations = load_conversations()

    if user_id not in conversations:
        await ctx.send("대화 기록이 존재하지 않습니다.")
        return

    messages = conversations[user_id]
    recent_messages = messages[-(limit * 2):]

    history = ""
    for message in recent_messages:
        if message['role'] == 'user':
            history += f"**User:** {message['content']}\n"
        elif message['role'] == 'assistant':
            history += f"**GPT:** {message['content']}\n"

    await ctx.send(f"**최근 {limit}개의 대화 기록:**\n{history}")
