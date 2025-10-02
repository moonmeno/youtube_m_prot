"""app.config 테스트."""

from __future__ import annotations

import os

import pytest

from app.config import get_settings


def clear_cache() -> None:
    """get_settings LRU 캐시를 초기화한다."""

    get_settings.cache_clear()  # type: ignore[attr-defined]


@pytest.fixture(autouse=True)
def _reset_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """각 테스트 시작 전/후 환경 변수를 초기화한다."""

    # 기존 환경 변수 값을 백업
    backup = {
        "YOUTUBE_API_KEY": os.getenv("YOUTUBE_API_KEY"),
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
        "DATA_BUCKET": os.getenv("DATA_BUCKET"),
        "AWS_REGION": os.getenv("AWS_REGION"),
        "VIDEO_INDEX_TABLE": os.getenv("VIDEO_INDEX_TABLE"),
    }

    clear_cache()

    yield

    for key, value in backup.items():
        if value is None:
            monkeypatch.delenv(key, raising=False)
        else:
            monkeypatch.setenv(key, value)
    clear_cache()


def test_get_settings_returns_values(monkeypatch: pytest.MonkeyPatch) -> None:
    """필수 환경 변수가 모두 있을 때 Settings를 반환한다."""

    monkeypatch.setenv("YOUTUBE_API_KEY", "youtube-key")
    monkeypatch.setenv("OPENAI_API_KEY", "openai-key")
    monkeypatch.setenv("DATA_BUCKET", "my-bucket")
    monkeypatch.setenv("AWS_REGION", "us-west-2")
    monkeypatch.setenv("VIDEO_INDEX_TABLE", "video-table")
    clear_cache()

    settings = get_settings()

    assert settings.youtube_api_key == "youtube-key"
    assert settings.openai_api_key == "openai-key"
    assert settings.default_bucket == "my-bucket"
    assert settings.aws_region == "us-west-2"
    assert settings.video_index_table == "video-table"


def test_get_settings_missing_required_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """필수 값이 비어 있으면 예외를 발생시킨다."""

    monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "openai-key")
    monkeypatch.setenv("DATA_BUCKET", "my-bucket")
    monkeypatch.setenv("VIDEO_INDEX_TABLE", "video-table")
    clear_cache()

    with pytest.raises(ValueError) as exc:
        get_settings()

    assert "YOUTUBE_API_KEY" in str(exc.value)
