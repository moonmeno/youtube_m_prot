"""환경별 설정 로딩 유틸리티."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import os


@dataclass
class Settings:
    """프로젝트 전역 설정."""

    youtube_api_key: str
    openai_api_key: str
    aws_region: str = "ap-northeast-2"
    default_bucket: str = ""


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """환경 변수에서 설정을 읽어 Settings 객체로 반환한다."""

    # TODO: 추후 AWS Secrets Manager 연동을 추가할 수 있도록 확장 포인트를 남긴다.
    return Settings(
        youtube_api_key=os.getenv("YOUTUBE_API_KEY", ""),
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        aws_region=os.getenv("AWS_REGION", "ap-northeast-2"),
        default_bucket=os.getenv("DATA_BUCKET", ""),
    )
