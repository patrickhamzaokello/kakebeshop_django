import uuid


def build_s3_key(image_type, object_id, variant):
    image_id = uuid.uuid4().hex

    return (
        f"{image_type}s/"
        f"{object_id}/"
        f"{image_id}/"
        f"{variant}.webp"
    )
