"""FastAPI 기반 웹 API 스켈레톤."""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, FastAPI, Query
from pydantic import BaseModel

from app.orchestration import jobs


class FetchRequest(BaseModel):
    """채널 수집 요청 본문."""

    channel_id: str
    force: bool = False


class ProcessRequest(BaseModel):
    """영상 분석 요청 본문."""

    video_id: str
    segment: str | None = None


router = APIRouter(prefix="/api", tags=["pipeline"])


@router.get("/health", summary="서비스 헬스 체크")
def health_check() -> Dict[str, str]:
    """배포 상태를 빠르게 확인하기 위한 엔드포인트."""

    return {"status": "ok"}


@router.post("/fetch", summary="YouTube 데이터 수집 작업 등록")
def enqueue_fetch(request: FetchRequest) -> Dict[str, Any]:
    """채널 수집 작업을 큐에 넣고 즉시 응답한다."""

    jobs.enqueue_fetch_job(channel_id=request.channel_id, force=request.force)
    return {"queued": True, "channel_id": request.channel_id, "force": request.force}


@router.post("/process", summary="OpenAI 분석 작업 등록")
def enqueue_process(request: ProcessRequest) -> Dict[str, Any]:
    """영상 분석 작업을 등록한다."""

    jobs.enqueue_process_job(video_id=request.video_id, segment=request.segment)
    return {"queued": True, "video_id": request.video_id, "segment": request.segment}


@router.get("/report", summary="요약 결과 조회")
def get_report(
    limit: int = Query(10, ge=1, le=100, description="표시할 결과 수"),
    channel_id: str | None = Query(None, description="특정 채널만 필터링"),
) -> Dict[str, Any]:
    """단순 보고서 출력을 웹에 맞춰 래핑한 엔드포인트."""

    videos = jobs.render_report(limit=limit, channel_id=channel_id)
    return {"items": videos, "limit": limit, "channelId": channel_id}


def create_app() -> FastAPI:
    """FastAPI 애플리케이션을 생성해 라우터를 등록한다."""

    app = FastAPI(title="YouTube 데이터 파이프라인", version="0.1.0")
    app.include_router(router)
    return app


app = create_app()
