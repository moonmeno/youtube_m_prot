"""OpenAI 기반 분석을 담당하는 프로세서."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

# TODO: OpenAI Python SDK를 설치한 뒤 실제 클라이언트로 교체한다.

from app import config


@dataclass
class OpenAIProcessor:
    """콘텐츠 요약 및 태깅을 담당하는 클래스."""

    api_key: str
    model: str = "gpt-4o-mini"

    def summarize_video(self, *, transcript: str, language: str = "ko") -> Dict[str, Any]:
        """비디오 스크립트를 요약한다."""

        # TODO: OpenAI API 호출 로직을 구현한다.
        # 지금은 구조만 정의하여 후속 개발 시 빠르게 연결할 수 있도록 한다.
        raise NotImplementedError("OpenAI API 연동이 아직 구현되지 않았습니다.")

    def analyze_comments(self, *, comments: list[dict[str, Any]], language: str = "ko") -> Dict[str, Any]:
        """댓글 감성 및 토픽 분석을 수행한다."""

        raise NotImplementedError("OpenAI API 연동이 아직 구현되지 않았습니다.")


def create_processor(model: Optional[str] = None) -> OpenAIProcessor:
    """설정값에 기반해 프로세서를 생성한다."""

    settings = config.get_settings()
    return OpenAIProcessor(api_key=settings.openai_api_key, model=model or "gpt-4o-mini")
