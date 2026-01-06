import boto3
from django.conf import settings


def get_s3_client():
    return boto3.client(
        "s3",
        region_name=settings.AWS_REGION,
    )


def generate_presigned_put_url(s3_key, content_type="image/webp"):
    s3 = get_s3_client()

    return s3.generate_presigned_url(
        ClientMethod="put_object",
        Params={
            "Bucket": settings.AWS_S3_BUCKET_NAME,
            "Key": s3_key,
            "ContentType": content_type,
            "ACL": "private",
        },
        ExpiresIn=settings.AWS_S3_UPLOAD_EXPIRE_SECONDS,
    )
