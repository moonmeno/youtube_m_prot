"""YouTube 클라이언트 동작 테스트."""

from __future__ import annotations

from typing import Any, Dict, List

import httpx
import pytest

from app.youtube.client import YouTubeClient


def _build_client(responses: Dict[str, List[Dict[str, Any]]]) -> YouTubeClient:
    """요청 경로별로 순차 응답을 반환하는 클라이언트를 생성한다."""

    counters: Dict[str, int] = {key: 0 for key in responses}

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path.split("/")[-1]
        if path not in responses:
            raise AssertionError(f"예상하지 못한 경로 요청: {path}")

        idx = counters[path]
        counters[path] += 1
        payload = responses[path][idx]
        status = payload.pop("status", 200)
        return httpx.Response(status, json=payload)

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)
    return YouTubeClient(api_key="dummy", session=client, max_retries=2, backoff_factor=0.0)


def test_list_videos_fetches_through_playlist(monkeypatch: pytest.MonkeyPatch) -> None:
    responses = {
        "channels": [
            {
                "items": [
                    {
                        "contentDetails": {
                            "relatedPlaylists": {"uploads": "UPLOADS123"},
                        }
                    }
                ]
            }
        ],
        "playlistItems": [
            {
                "items": [
                    {"contentDetails": {"videoId": "vid1"}},
                    {"contentDetails": {"videoId": "vid2"}},
                ],
                "nextPageToken": "TOKEN",
            }
        ],
        "videos": [
            {
                "items": [
                    {"id": "vid1", "snippet": {"title": "Video 1"}},
                    {"id": "vid2", "snippet": {"title": "Video 2"}},
                ]
            }
        ],
    }

    client = _build_client(responses)

    try:
        result = client.list_videos(channel_id="UC123")
    finally:
        client.session.close()  # type: ignore[union-attr]

    assert [item["id"] for item in result["items"]] == ["vid1", "vid2"]
    assert result["nextPageToken"] == "TOKEN"
    assert "playlistItems" in result


def test_list_comment_threads_retries_on_server_error(monkeypatch: pytest.MonkeyPatch) -> None:
    responses = {
        "commentThreads": [
            {"status": 500, "error": "server"},
            {"items": [{"id": "c1"}]},
        ]
    }

    client = _build_client(responses)

    # 재시도 대기 시간을 제거하기 위해 sleep을 패치한다.
    monkeypatch.setattr("app.youtube.client.sleep", lambda *_: None)

    try:
        result = client.list_comment_threads(video_id="vid1")
    finally:
        client.session.close()  # type: ignore[union-attr]
    assert result["items"][0]["id"] == "c1"


def test_list_comment_threads_raises_on_client_error(monkeypatch: pytest.MonkeyPatch) -> None:
    responses = {"commentThreads": [{"status": 403, "error": "forbidden"}]}
    client = _build_client(responses)

    try:
        with pytest.raises(httpx.HTTPStatusError):
            client.list_comment_threads(video_id="vid1")
    finally:
        client.session.close()  # type: ignore[union-attr]

