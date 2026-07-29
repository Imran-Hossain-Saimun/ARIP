import io
import uuid
from functools import lru_cache

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from app.core.config import get_settings


@lru_cache
def get_s3_client():
    settings = get_settings()
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )


def ensure_bucket() -> None:
    settings = get_settings()
    client = get_s3_client()
    try:
        client.head_bucket(Bucket=settings.s3_bucket)
    except ClientError:
        client.create_bucket(Bucket=settings.s3_bucket)


def upload_document(filename: str, content: bytes, content_type: str) -> str:
    """Returns the storage key the object was written under."""
    ensure_bucket()
    settings = get_settings()
    key = f"knowledge/{uuid.uuid4()}/{filename}"
    get_s3_client().put_object(Bucket=settings.s3_bucket, Key=key, Body=io.BytesIO(content), ContentType=content_type)
    return key
