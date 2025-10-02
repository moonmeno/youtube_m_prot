"""저장소 접근 레이어."""

from .dynamodb import MetadataIndex, create_metadata_index
from .s3 import S3Storage, create_storage

__all__ = [
    "MetadataIndex",
    "S3Storage",
    "create_metadata_index",
    "create_storage",
]
