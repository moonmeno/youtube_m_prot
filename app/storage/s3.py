"""S3 버킷과 상호작용하는 헬퍼."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

import boto3
from botocore.client import BaseClient
from botocore.exceptions import BotoCoreError, ClientError

from app import config

LOGGER = logging.getLogger(__name__)


@dataclass
class S3Storage:
    """S3 파일 업로드/다운로드를 추상화한다."""

    bucket: str
    client: BaseClient

    def put_json(self, key: str, data: Any) -> None:
        """JSON 데이터를 업로드한다."""

        try:
            payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        except (TypeError, ValueError) as exc:  # pragma: no cover - json error path
            raise ValueError("JSON 직렬화에 실패했습니다.") from exc

        try:
            self.client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=payload,
                ContentType="application/json",
            )
            LOGGER.debug("S3 업로드 성공: bucket=%s, key=%s", self.bucket, key)
        except ClientError as exc:
            raise RuntimeError(
                f"S3 업로드에 실패했습니다: bucket={self.bucket}, key={key}"
            ) from exc
        except BotoCoreError as exc:  # pragma: no cover - 일반적인 예외 경로 아님
            raise RuntimeError("S3 클라이언트 오류가 발생했습니다.") from exc

    def get_object(self, key: str) -> bytes:
        """객체를 다운로드한다."""

        try:
            response = self.client.get_object(Bucket=self.bucket, Key=key)
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code")
            if error_code in {"NoSuchKey", "404"}:
                raise FileNotFoundError(
                    f"S3 객체를 찾을 수 없습니다: bucket={self.bucket}, key={key}"
                ) from exc
            raise RuntimeError(
                f"S3 다운로드에 실패했습니다: bucket={self.bucket}, key={key}"
            ) from exc
        except BotoCoreError as exc:  # pragma: no cover
            raise RuntimeError("S3 클라이언트 오류가 발생했습니다.") from exc

        body = response.get("Body")
        if body is None:
            raise RuntimeError("S3 응답에 Body가 없습니다.")

        data = body.read()
        LOGGER.debug("S3 다운로드 성공: bucket=%s, key=%s", self.bucket, key)
        return data


def create_storage() -> S3Storage:
    """환경 설정을 활용해 스토리지 인스턴스를 생성한다."""

    settings = config.get_settings()
    session = boto3.session.Session(region_name=settings.aws_region)
    client = session.client("s3")
    return S3Storage(bucket=settings.default_bucket, client=client)
