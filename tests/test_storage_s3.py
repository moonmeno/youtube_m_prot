"""S3 스토리지 헬퍼 단위 테스트."""

from __future__ import annotations

import io

import boto3
import pytest
from botocore.response import StreamingBody
from botocore.stub import Stubber

from app.storage.s3 import S3Storage


def create_stubbed_storage():
    client = boto3.client("s3", region_name="ap-northeast-2")
    stubber = Stubber(client)
    storage = S3Storage(bucket="test-bucket", client=client)
    return storage, stubber


def test_put_json_uploads_bytes():
    storage, stubber = create_stubbed_storage()
    expected_body = b'{"hello": "world"}'
    stubber.add_response(
        "put_object",
        service_response={},
        expected_params={
            "Bucket": "test-bucket",
            "Key": "path/data.json",
            "Body": expected_body,
            "ContentType": "application/json",
        },
    )

    with stubber:
        storage.put_json("path/data.json", {"hello": "world"})


def test_put_json_raises_runtime_error_on_client_error():
    storage, stubber = create_stubbed_storage()
    stubber.add_client_error(
        "put_object",
        service_error_code="AccessDenied",
        service_message="denied",
    )

    with stubber, pytest.raises(RuntimeError):
        storage.put_json("path/data.json", {"hello": "world"})


def test_get_object_reads_body_bytes():
    storage, stubber = create_stubbed_storage()
    body = StreamingBody(raw_stream=io.BytesIO(b"payload"), content_length=7)
    stubber.add_response(
        "get_object",
        service_response={"Body": body},
        expected_params={"Bucket": "test-bucket", "Key": "path/data.json"},
    )

    with stubber:
        data = storage.get_object("path/data.json")

    assert data == b"payload"


def test_get_object_raises_file_not_found_for_missing_key():
    storage, stubber = create_stubbed_storage()
    stubber.add_client_error(
        "get_object",
        service_error_code="NoSuchKey",
        service_message="missing",
        http_status_code=404,
    )

    with stubber, pytest.raises(FileNotFoundError):
        storage.get_object("path/missing.json")


def test_get_object_wraps_other_errors():
    storage, stubber = create_stubbed_storage()
    stubber.add_client_error(
        "get_object",
        service_error_code="InternalError",
        service_message="boom",
    )

    with stubber, pytest.raises(RuntimeError):
        storage.get_object("path/error.json")
