"""환경별 설정 로딩 유틸리티."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import os
from typing import List


@dataclass
class Settings:
    """프로젝트 전역 설정."""

    youtube_api_key: str
    openai_api_key: str
    aws_region: str = "ap-northeast-2"
    default_bucket: str = ""
    video_index_table: str = ""


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """환경 변수에서 설정을 읽어 Settings 객체로 반환한다."""

    # TODO: 추후 AWS Secrets Manager 연동을 추가할 수 있도록 확장 포인트를 남긴다.
    youtube_api_key = (os.getenv("YOUTUBE_API_KEY") or "").strip()
    openai_api_key = (os.getenv("OPENAI_API_KEY") or "").strip()
    default_bucket = (os.getenv("DATA_BUCKET") or "").strip()
    video_index_table = (os.getenv("VIDEO_INDEX_TABLE") or "").strip()
    aws_region = (os.getenv("AWS_REGION") or "ap-northeast-2").strip()

    missing: List[str] = []
    if not youtube_api_key:
        missing.append("YOUTUBE_API_KEY")
    if not openai_api_key:
        missing.append("OPENAI_API_KEY")
    if not default_bucket:
        missing.append("DATA_BUCKET")

    if not video_index_table:
        missing.append("VIDEO_INDEX_TABLE")

    if missing:
        missing_csv = ", ".join(missing)
        raise ValueError(
            "필수 환경 변수가 누락되었습니다: "
            f"{missing_csv}. README의 환경 변수 설정 절차를 확인하세요."
        )

    return Settings(
        youtube_api_key=youtube_api_key,
        openai_api_key=openai_api_key,
        aws_region=aws_region,
        default_bucket=default_bucket,
        video_index_table=video_index_table,
    )
