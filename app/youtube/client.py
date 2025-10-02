"""YouTube Data API 호출 래퍼."""

from __future__ import annotations

from dataclasses import dataclass
from time import sleep
from typing import Any, Dict, Iterable, List, Optional

import httpx

from app import config


@dataclass
class YouTubeClient:
    """YouTube API 호출을 담당하는 간단한 클라이언트."""

    api_key: str
    base_url: str = "https://www.googleapis.com/youtube/v3"
    session: Optional[httpx.Client] = None
    max_retries: int = 3
    backoff_factor: float = 1.0

    def _get_client(self) -> httpx.Client:
        """지연 생성되는 HTTP 클라이언트를 반환한다."""

        if self.session is None:
            # TODO: 추후 커넥션 풀 설정, 재시도 로직, 쿼터 관리 등을 추가한다.
            self.session = httpx.Client(timeout=30.0)
        return self.session

    def list_videos(self, *, channel_id: str, parts: Iterable[str] | None = None, page_token: str | None = None) -> Dict[str, Any]:
        """채널 업로드 플레이리스트를 기반으로 비디오 상세 정보를 조회한다."""

        parts_to_fetch: List[str] = list(parts or ["snippet", "contentDetails", "statistics"])
        uploads_playlist_id = self._get_uploads_playlist_id(channel_id=channel_id)

        playlist_params: Dict[str, Any] = {
            "part": "contentDetails",
            "playlistId": uploads_playlist_id,
            "maxResults": 50,
            "key": self.api_key,
        }
        if page_token:
            playlist_params["pageToken"] = page_token

        playlist_response = self._request("playlistItems", playlist_params)

        video_ids = [
            item.get("contentDetails", {}).get("videoId")
            for item in playlist_response.get("items", [])
            if item.get("contentDetails", {}).get("videoId")
        ]

        videos_response: Dict[str, Any] = {"items": []}
        if video_ids:
            video_params = {
                "part": ",".join(parts_to_fetch),
                "id": ",".join(video_ids),
                "maxResults": 50,
                "key": self.api_key,
            }
            videos_response = self._request("videos", video_params)

        return {
            "items": videos_response.get("items", []),
            "nextPageToken": playlist_response.get("nextPageToken"),
            "prevPageToken": playlist_response.get("prevPageToken"),
            "pageInfo": videos_response.get("pageInfo", playlist_response.get("pageInfo")),
            "playlistItems": playlist_response.get("items", []),
        }

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

        return self._request("commentThreads", params)

    def _get_uploads_playlist_id(self, *, channel_id: str) -> str:
        """채널의 업로드 플레이리스트 ID를 조회한다."""

        params = {
            "part": "contentDetails",
            "id": channel_id,
            "key": self.api_key,
        }
        response = self._request("channels", params)
        items = response.get("items", [])
        if not items:
            raise ValueError("채널 정보를 찾을 수 없습니다.")

        uploads_id = (
            items[0]
            .get("contentDetails", {})
            .get("relatedPlaylists", {})
            .get("uploads")
        )
        if not uploads_id:
            raise ValueError("업로드 플레이리스트 ID를 확인할 수 없습니다.")
        return uploads_id

    def _request(self, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """재시도 로직이 포함된 GET 요청 헬퍼."""

        client = self._get_client()
        last_error: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            try:
                response = client.get(f"{self.base_url}/{path}", params=params)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                # 4xx 에러는 재시도하지 않는다.
                if status < 500 or attempt == self.max_retries:
                    raise
                last_error = exc
            except httpx.RequestError as exc:
                if attempt == self.max_retries:
                    raise
                last_error = exc

            sleep(self.backoff_factor * attempt)

        assert last_error is not None  # 논리적으로 여기에 도달하지 않는다.
        raise last_error


def create_client() -> YouTubeClient:
    """환경 설정으로부터 API 키를 로드하여 클라이언트를 생성한다."""

    settings = config.get_settings()
    return YouTubeClient(api_key=settings.youtube_api_key)
