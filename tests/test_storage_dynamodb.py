"""DynamoDB 메타데이터 인덱스 테스트."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

import pytest

from app.storage.dynamodb import MetadataIndex


class FakeTable:
    """DynamoDB Table 동작을 단순화한 테스트 스텁."""

    def __init__(self) -> None:
        self.items: List[Dict[str, Any]] = []

    def put_item(self, *, Item: Dict[str, Any]) -> None:  # noqa: N803 - boto3 스타일 유지
        self.items.append(Item)

    def query(self, *, KeyConditionExpression, ScanIndexForward: bool, Limit: int):  # noqa: N803
        # 테스트에서는 KeyConditionExpression이 Key('PK').eq(value) 형태로 넘어오므로
        # __call__ 로직에서 값을 저장했다고 가정한다.
        key_value = KeyConditionExpression.value  # type: ignore[attr-defined]
        filtered = [item for item in self.items if item["PK"] == key_value]
        filtered.sort(key=lambda item: item["SK"], reverse=not ScanIndexForward)
        return {"Items": filtered[:Limit]}

    def scan(self, **kwargs):  # noqa: D401 - boto3 유사 시그니처 유지
        return {"Items": list(self.items)}


class KeyConditionStub:
    """boto3 KeyConditionExpression 흉내를 내는 단순 스텁."""

    def __init__(self, value: str) -> None:
        self.value = value


@pytest.fixture(autouse=True)
def patch_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """boto3 Key.eq 호출을 가로채 테스트 스텁을 반환한다."""

    from boto3.dynamodb.conditions import Key

    original_eq = Key.eq

    def fake_eq(self, value):  # type: ignore[override]
        stub = KeyConditionStub(value)
        return stub

    monkeypatch.setattr(Key, "eq", fake_eq)
    yield
    monkeypatch.setattr(Key, "eq", original_eq)


def test_upsert_video_saves_expected_item() -> None:
    table = FakeTable()
    index = MetadataIndex(table=table)

    index.upsert_video(
        channel_id="UC123",
        video_payload={
            "id": "vid1",
            "snippet": {"title": "Video", "description": "Desc", "publishedAt": "2024-01-01T00:00:00Z"},
            "statistics": {"viewCount": "100"},
        },
        run_id="run-1",
        stored_at=datetime(2024, 1, 2, 3, 4, 5, tzinfo=timezone.utc),
    )

    assert table.items[0]["PK"] == "CHANNEL#UC123"
    assert table.items[0]["videoId"] == "vid1"
    assert table.items[0]["statistics"] == {"viewCount": "100"}


def test_upsert_video_requires_id() -> None:
    table = FakeTable()
    index = MetadataIndex(table=table)

    with pytest.raises(ValueError):
        index.upsert_video(
            channel_id="UC123",
            video_payload={"snippet": {}},
            run_id="run-1",
            stored_at=datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        )


def test_list_recent_videos_filters_by_channel() -> None:
    table = FakeTable()
    index = MetadataIndex(table=table)

    index.upsert_video(
        channel_id="UC123",
        video_payload={"id": "vid1", "snippet": {"title": "Video1"}},
        run_id="run-1",
        stored_at=datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
    )
    index.upsert_video(
        channel_id="UC123",
        video_payload={"id": "vid2", "snippet": {"title": "Video2"}},
        run_id="run-1",
        stored_at=datetime(2024, 1, 2, 0, 0, 0, tzinfo=timezone.utc),
    )
    index.upsert_video(
        channel_id="UC456",
        video_payload={"id": "vid3", "snippet": {"title": "Video3"}},
        run_id="run-2",
        stored_at=datetime(2024, 1, 3, 0, 0, 0, tzinfo=timezone.utc),
    )

    results = index.list_recent_videos(channel_id="UC123", limit=5)
    assert [item["videoId"] for item in results] == ["vid2", "vid1"]

    results_all = index.list_recent_videos(limit=2)
    assert len(results_all) == 2
