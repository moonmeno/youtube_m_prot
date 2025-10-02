"""수집 오케스트레이션 테스트."""

from __future__ import annotations

from typing import Dict, List

import pytest

from app.orchestration import jobs


class StubStorage:
    """put_json 호출 기록을 보관하는 스텁."""

    def __init__(self) -> None:
        self.payloads: Dict[str, object] = {}

    def put_json(self, key: str, data: object) -> None:  # pragma: no cover - 단순 기록
        self.payloads[key] = data


class StubYouTubeClient:
    """영상/댓글 응답을 순차적으로 반환하는 스텁."""

    def __init__(
        self,
        *,
        video_pages: List[Dict[str, object]],
        comment_pages: Dict[str, List[Dict[str, object]]],
    ) -> None:
        self._video_pages = video_pages
        self._comment_pages = comment_pages
        self.video_calls = 0
        self.comment_calls: Dict[str, int] = {vid: 0 for vid in comment_pages}

    def list_videos(
        self,
        *,
        channel_id: str,
        page_token: str | None = None,
    ) -> Dict[str, object]:
        assert channel_id == "UC123"
        expected_token = None if self.video_calls == 0 else "PAGE2"
        if page_token != expected_token:
            raise AssertionError(f"예상과 다른 page_token: {page_token}")

        page = self._video_pages[self.video_calls]
        self.video_calls += 1
        return page

    def list_comment_threads(
        self,
        *,
        video_id: str,
        page_token: str | None = None,
    ) -> Dict[str, object]:
        pages = self._comment_pages[video_id]
        idx = self.comment_calls[video_id]

        expected_token = None if idx == 0 else pages[idx - 1].get("nextPageToken")
        if idx > 0 and page_token != expected_token:
            raise AssertionError(
                f"예상과 다른 댓글 page_token: video_id={video_id}, token={page_token}"
            )

        self.comment_calls[video_id] += 1
        return pages[idx]


@pytest.fixture
def stub_environment(monkeypatch: pytest.MonkeyPatch) -> Dict[str, object]:
    """공통 스텁을 세팅하고 테스트 후 정리한다."""

    storage = StubStorage()
    video_pages = [
        {
            "items": [
                {"id": "vid1", "snippet": {"title": "Video 1"}},
            ],
            "playlistItems": [
                {"contentDetails": {"videoId": "vid1"}},
            ],
            "nextPageToken": "PAGE2",
        },
        {
            "items": [
                {"id": "vid2", "snippet": {"title": "Video 2"}},
            ],
            "playlistItems": [
                {"contentDetails": {"videoId": "vid2"}},
            ],
        },
    ]
    comment_pages = {
        "vid1": [
            {"items": [{"id": "c1"}], "nextPageToken": "N2"},
            {"items": [{"id": "c2"}]},
        ],
        "vid2": [
            {"items": []},
        ],
    }
    client = StubYouTubeClient(video_pages=video_pages, comment_pages=comment_pages)

    monkeypatch.setattr(jobs.youtube_client, "create_client", lambda: client)
    monkeypatch.setattr(jobs.s3_storage, "create_storage", lambda: storage)
    monkeypatch.setattr(jobs, "_generate_run_id", lambda: "20240101T000000Z")

    return {"storage": storage, "client": client}


def test_enqueue_fetch_job_persists_videos_and_comments(
    stub_environment: Dict[str, object],
) -> None:
    jobs.enqueue_fetch_job(channel_id="UC123")

    storage: StubStorage = stub_environment["storage"]  # type: ignore[assignment]
    client: StubYouTubeClient = stub_environment["client"]  # type: ignore[assignment]

    base = "raw/channels/UC123/20240101T000000Z"

    assert storage.payloads[f"{base}/videos/vid1.json"]["id"] == "vid1"
    assert storage.payloads[f"{base}/videos/vid2.json"]["id"] == "vid2"

    assert storage.payloads[f"{base}/comments/vid1_page_00000.json"]["items"][0]["id"] == "c1"
    assert storage.payloads[f"{base}/comments/vid1_page_00001.json"]["items"][0]["id"] == "c2"
    assert "items" in storage.payloads[f"{base}/comments/vid2_page_00000.json"]

    index = storage.payloads[f"{base}/videos_index.json"]
    assert index == {"videoIds": ["vid1", "vid2"]}

    assert client.video_calls == 2
    assert client.comment_calls == {"vid1": 2, "vid2": 1}
