"""DynamoDB 기반 메타데이터 인덱스."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from app.config import get_settings


@dataclass
class MetadataIndex:
    """영상/댓글 메타데이터를 조회하기 위한 DynamoDB 인덱스."""

    table: Any

    def upsert_video(
        self,
        *,
        channel_id: str,
        video_payload: Dict[str, Any],
        run_id: str,
        stored_at: datetime,
    ) -> None:
        """영상 메타데이터를 테이블에 저장한다."""

        video_id: str = video_payload.get("id", "")
        if not video_id:
            raise ValueError("video_payload에 'id'가 필요합니다.")

        snippet: Dict[str, Any] = video_payload.get("snippet", {})
        published_at: str = snippet.get("publishedAt") or stored_at.isoformat()
        title: str = snippet.get("title", "")
        description: str = snippet.get("description", "")

        item = {
            "PK": f"CHANNEL#{channel_id}",
            "SK": f"PUBLISHED#{published_at}#VIDEO#{video_id}",
            "videoId": video_id,
            "channelId": channel_id,
            "title": title,
            "description": description,
            "publishedAt": published_at,
            "runId": run_id,
            "storedAt": stored_at.isoformat(),
        }

        statistics = video_payload.get("statistics")
        if isinstance(statistics, dict):
            item["statistics"] = statistics

        try:
            self.table.put_item(Item=item)
        except ClientError as exc:  # pragma: no cover - 예외 메시지 전달
            raise RuntimeError("영상 메타데이터 저장 중 오류가 발생했습니다.") from exc

    def list_recent_videos(
        self,
        *,
        channel_id: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """최근 저장된 영상 메타데이터를 조회한다."""

        if channel_id:
            response = self.table.query(
                KeyConditionExpression=Key("PK").eq(f"CHANNEL#{channel_id}"),
                ScanIndexForward=False,
                Limit=limit,
            )
            return list(response.get("Items", []))

        # 채널이 지정되지 않았다면 전체 스캔 후 정렬한다.
        response = self.table.scan()
        items: List[Dict[str, Any]] = list(response.get("Items", []))
        items.sort(key=lambda item: item.get("storedAt", ""), reverse=True)
        return items[:limit]


def create_metadata_index(*, table_name: Optional[str] = None) -> MetadataIndex:
    """환경 설정에 기반해 MetadataIndex 인스턴스를 생성한다."""

    settings = get_settings()
    dynamodb = boto3.resource("dynamodb", region_name=settings.aws_region)
    table = dynamodb.Table(table_name or settings.video_index_table)
    return MetadataIndex(table=table)

