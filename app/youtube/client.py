"""YouTube Data API 호출 래퍼."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, Optional

import httpx

from app import config


@dataclass
class YouTubeClient:
    """YouTube API 호출을 담당하는 간단한 클라이언트."""

    api_key: str
    base_url: str = "https://www.googleapis.com/youtube/v3"
    session: Optional[httpx.Client] = None

    def _get_client(self) -> httpx.Client:
        """지연 생성되는 HTTP 클라이언트를 반환한다."""

        if self.session is None:
            # TODO: 추후 커넥션 풀 설정, 재시도 로직, 쿼터 관리 등을 추가한다.
            self.session = httpx.Client(timeout=30.0)
        return self.session

    def list_videos(self, *, channel_id: str, parts: Iterable[str] | None = None, page_token: str | None = None) -> Dict[str, Any]:
        """비디오 목록을 조회한다."""

        params = {
            "part": ",".join(parts or ["snippet", "contentDetails", "statistics"]),
            "channelId": channel_id,
            "maxResults": 50,
            "key": self.api_key,
        }
        if page_token:
            params["pageToken"] = page_token

        response = self._get_client().get(f"{self.base_url}/videos", params=params)
        response.raise_for_status()
        return response.json()

    def list_comment_threads(self, *, video_id: str, page_token: str | None = None) -> Dict[str, Any]:
        """특정 비디오의 댓글 스레드를 조회한다."""

        params = {
            "part": "snippet,replies",
            "videoId": video_id,
            "maxResults": 100,
            "textFormat": "plainText",
            "key": self.api_key,
        }
        if page_token:
            params["pageToken"] = page_token

        response = self._get_client().get(f"{self.base_url}/commentThreads", params=params)
        response.raise_for_status()
        return response.json()


def create_client() -> YouTubeClient:
    """환경 설정으로부터 API 키를 로드하여 클라이언트를 생성한다."""

    settings = config.get_settings()
    return YouTubeClient(api_key=settings.youtube_api_key)
