"""S3 버킷과 상호작용하는 헬퍼."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import boto3
from botocore.client import BaseClient

from app import config


@dataclass
class S3Storage:
    """S3 파일 업로드/다운로드를 추상화한다."""

    bucket: str
    client: BaseClient

    def put_json(self, key: str, data: Any) -> None:
        """JSON 데이터를 업로드한다."""

        # TODO: json.dumps, ContentType 지정, 에러 처리 등을 추가한다.
        raise NotImplementedError("S3 업로드 로직이 아직 구현되지 않았습니다.")

    def get_object(self, key: str) -> bytes:
        """객체를 다운로드한다."""

        raise NotImplementedError("S3 다운로드 로직이 아직 구현되지 않았습니다.")


def create_storage() -> S3Storage:
    """환경 설정을 활용해 스토리지 인스턴스를 생성한다."""

    settings = config.get_settings()
    session = boto3.session.Session(region_name=settings.aws_region)
    client = session.client("s3")
    return S3Storage(bucket=settings.default_bucket, client=client)
