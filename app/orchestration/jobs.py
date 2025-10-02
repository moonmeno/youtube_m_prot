"""CLI에서 호출하는 작업 구현."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

from app.storage import dynamodb as index_storage
from app.storage import s3 as s3_storage
from app.youtube import client as youtube_client

LOGGER = logging.getLogger(__name__)


def enqueue_fetch_job(*, channel_id: str, force: bool = False) -> None:
    """YouTube 데이터 수집 작업을 실행한다."""

    del force  # 추후 캐시 무시 옵션을 구현할 때 사용한다.

    youtube = youtube_client.create_client()
    storage = s3_storage.create_storage()
    metadata_index = index_storage.create_metadata_index()

    run_id = _generate_run_id()
    base_prefix = f"raw/channels/{channel_id}/{run_id}"
    LOGGER.info("YouTube 수집 시작: channel_id=%s, run_id=%s", channel_id, run_id)

    all_video_ids: list[str] = []
    page_token: Optional[str] = None
    page_index = 0

    while True:
        response = youtube.list_videos(channel_id=channel_id, page_token=page_token)

        playlist_key = f"{base_prefix}/playlist/page_{page_index:05d}.json"
        storage.put_json(playlist_key, response.get("playlistItems", []))

        videos = response.get("items", [])
        LOGGER.info(
            "영상 상세 %d건 수신 (page=%d, channel_id=%s)",
            len(videos),
            page_index,
            channel_id,
        )

        for video in videos:
            video_id = video.get("id")
            if not video_id:
                LOGGER.debug("비디오 ID를 찾을 수 없어 건너뜀: %s", video)
                continue

            video_key = f"{base_prefix}/videos/{video_id}.json"
            storage.put_json(video_key, video)
            all_video_ids.append(video_id)
            metadata_index.upsert_video(
                channel_id=channel_id,
                video_payload=video,
                run_id=run_id,
                stored_at=datetime.now(timezone.utc),
            )

            _fetch_comments(
                storage=storage,
                youtube=youtube,
                base_prefix=base_prefix,
                video_id=video_id,
            )

        page_token = response.get("nextPageToken")
        page_index += 1
        if not page_token:
            break

    index_key = f"{base_prefix}/videos_index.json"
    storage.put_json(index_key, {"videoIds": all_video_ids})
    LOGGER.info(
        "YouTube 수집 완료: channel_id=%s, run_id=%s, videos=%d",
        channel_id,
        run_id,
        len(all_video_ids),
    )


def enqueue_process_job(*, video_id: str, segment: Optional[str] = None) -> None:
    """OpenAI 분석 작업을 등록한다."""

    LOGGER.info("[stub] process job -> video_id=%s, segment=%s", video_id, segment)


def render_report(*, limit: int = 10, channel_id: Optional[str] = None) -> List[Dict[str, object]]:
    """간단한 결과 리포트를 출력한다."""

    metadata_index = index_storage.create_metadata_index()
    videos = metadata_index.list_recent_videos(channel_id=channel_id, limit=limit)

    for video in videos:
        LOGGER.info(
            "영상 요약: channel=%s video=%s title=%s published=%s",
            video.get("channelId"),
            video.get("videoId"),
            video.get("title"),
            video.get("publishedAt"),
        )

    return videos


def _generate_run_id() -> str:
    """S3 경로에 사용할 수집 실행 ID를 생성한다."""

    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _fetch_comments(
    *,
    storage: s3_storage.S3Storage,
    youtube: youtube_client.YouTubeClient,
    base_prefix: str,
    video_id: str,
) -> None:
    """특정 비디오의 댓글을 모두 조회해 저장한다."""

    page_token: Optional[str] = None
    page_index = 0

    while True:
        response: Dict[str, object] = youtube.list_comment_threads(
            video_id=video_id,
            page_token=page_token,
        )

        comments_key = f"{base_prefix}/comments/{video_id}_page_{page_index:05d}.json"
        storage.put_json(comments_key, response)

        page_token = response.get("nextPageToken")  # type: ignore[assignment]
        page_index += 1
        if not page_token:
            break

