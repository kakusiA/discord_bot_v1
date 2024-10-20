import os
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv
load_dotenv()
YOUTUBE_API_KEY = os.getenv('youtube_key')

if not YOUTUBE_API_KEY:
    raise ValueError("YouTube API key가 설정되지 않았습니다. .env 파일을 확인하세요.")

youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)

async def search_youtube(ctx, query):
    if not query:
        await ctx.send("검색할 유튜브 제목을 입력해주세요.")
        return
    try:
        search_response = youtube.search().list(
            q=query,
            part='id,snippet',
            maxResults=1,
            type='video'
        ).execute()

        items = search_response.get('items', [])
        if not items:
            await ctx.send("검색 결과가 없습니다.")
            return

        video = items[0]
        video_id = video['id']['videoId']
        video_title = video['snippet']['title']
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        await ctx.send(f"**{video_title}**\n{video_url}")
    except HttpError as e:
        await ctx.send(f"유튜브 검색 중 오류가 발생했습니다.")
        print(f"An HTTP error {e.resp.status} occurred:\n{e.content}")
