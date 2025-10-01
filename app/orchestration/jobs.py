"""CLI에서 호출하는 작업 스텁."""

from __future__ import annotations

from typing import Optional


def enqueue_fetch_job(*, channel_id: str, force: bool = False) -> None:
    """YouTube 데이터 수집 작업을 등록한다."""

    # TODO: SQS, Step Functions 등 실제 큐잉 로직을 구현한다.
    # 현재는 아키텍처 설계를 위한 자리표시자 역할만 수행한다.
    print(f"[stub] fetch job -> channel_id={channel_id}, force={force}")


def enqueue_process_job(*, video_id: str, segment: Optional[str] = None) -> None:
    """OpenAI 분석 작업을 등록한다."""

    print(f"[stub] process job -> video_id={video_id}, segment={segment}")


def render_report(*, limit: int = 10) -> None:
    """간단한 결과 리포트를 출력한다."""

    print(f"[stub] report -> limit={limit}")
