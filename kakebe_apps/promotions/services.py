import json
import mimetypes
import shutil
import re
import uuid
from pathlib import Path
from urllib import request as urllib_request

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.images import get_image_dimensions
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from kakebe_apps.imagehandler.models import ImageAsset
from kakebe_apps.imagehandler.s3 import generate_presigned_put_url
from kakebe_apps.imagehandler.utils import build_s3_key
from kakebe_apps.listings.models import Listing

from .models import BannerImageImport, BannerListing, PromotionalBanner


BANNER_IMPORT_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}


def get_banner_import_dir():
    return Path(getattr(settings, 'BANNER_IMPORT_INCOMING_DIR', settings.BASE_DIR / 'banner_imports' / 'incoming'))


def get_banner_processed_dir():
    return Path(getattr(settings, 'BANNER_IMPORT_PROCESSED_DIR', settings.BASE_DIR / 'banner_imports' / 'processed'))


def get_banner_failed_dir():
    return Path(getattr(settings, 'BANNER_IMPORT_FAILED_DIR', settings.BASE_DIR / 'banner_imports' / 'failed'))


def _safe_child_path(directory, filename):
    directory = Path(directory).resolve()
    path = (directory / filename).resolve()
    if directory not in path.parents and path != directory:
        raise ValueError('Invalid import path.')
    return path


def _safe_filename(filename):
    stem = Path(filename).stem
    suffix = Path(filename).suffix.lower()
    stem = re.sub(r'[^A-Za-z0-9._-]+', '-', stem).strip('-') or 'banner'
    if suffix not in BANNER_IMPORT_EXTENSIONS:
        raise ValueError('Unsupported banner image file type.')
    return f"{uuid.uuid4()}__{stem}{suffix}"


def save_remote_banner_upload(uploaded_file, metadata, agent_credential):
    """
    Store a remote AI agent upload in the same incoming folder used by the worker.
    """
    incoming_dir = get_banner_import_dir()
    incoming_dir.mkdir(parents=True, exist_ok=True)

    filename = _safe_filename(uploaded_file.name)
    image_path = _safe_child_path(incoming_dir, filename)
    sidecar_path = image_path.with_suffix('.json')

    with image_path.open('wb') as handle:
        for chunk in uploaded_file.chunks():
            handle.write(chunk)

    metadata = metadata or {}
    metadata['is_verified'] = False
    with sidecar_path.open('w', encoding='utf-8') as handle:
        json.dump(metadata, handle, indent=2)

    target_field = metadata.get('target_field') or metadata.get('target') or _guess_target_from_filename(image_path)
    if target_field not in ['image', 'mobile_image']:
        target_field = 'image'

    banner = None
    banner_id = metadata.get('banner_id')
    if banner_id:
        banner = PromotionalBanner.objects.filter(pk=banner_id).first()

    return BannerImageImport.objects.create(
        banner=banner,
        uploaded_by_agent=agent_credential,
        source_path=str(image_path),
        sidecar_path=str(sidecar_path),
        target_field=target_field,
        metadata=metadata,
    )


def _load_sidecar(image_path):
    sidecar_path = image_path.with_suffix('.json')
    if not sidecar_path.exists():
        return {}, ''
    with sidecar_path.open('r', encoding='utf-8') as handle:
        return json.load(handle), str(sidecar_path)


def _guess_banner_id_from_filename(image_path):
    first_token = image_path.stem.split('__')[0]
    try:
        return uuid.UUID(first_token)
    except ValueError:
        return None


def _guess_target_from_filename(image_path):
    name = image_path.stem.lower()
    return 'mobile_image' if 'mobile' in name else 'image'


def discover_banner_image_imports():
    """
    Create queue records for files dropped into the banner import folder.
    """
    incoming_dir = get_banner_import_dir()
    incoming_dir.mkdir(parents=True, exist_ok=True)

    created = 0
    for image_path in incoming_dir.iterdir():
        if not image_path.is_file() or image_path.suffix.lower() not in BANNER_IMPORT_EXTENSIONS:
            continue

        metadata, sidecar_path = _load_sidecar(image_path)
        target_field = metadata.get('target_field') or metadata.get('target') or _guess_target_from_filename(image_path)
        if target_field not in ['image', 'mobile_image']:
            target_field = 'image'

        banner = None
        banner_id = metadata.get('banner_id') or _guess_banner_id_from_filename(image_path)
        if banner_id:
            banner = PromotionalBanner.objects.filter(pk=banner_id).first()

        _, was_created = BannerImageImport.objects.get_or_create(
            source_path=str(image_path),
            defaults={
                'banner': banner,
                'sidecar_path': sidecar_path,
                'target_field': target_field,
                'metadata': metadata,
            },
        )
        if was_created:
            created += 1
    return created


def _get_asset_owner():
    User = get_user_model()
    owner_email = getattr(settings, 'BANNER_IMPORT_OWNER_EMAIL', '')
    if owner_email:
        owner = User.objects.filter(email=owner_email).first()
        if owner:
            return owner
    owner = User.objects.filter(is_staff=True).order_by('id').first()
    if owner:
        return owner
    owner = User.objects.order_by('id').first()
    if owner:
        return owner
    raise ValueError('No user exists to own imported banner image assets.')


def _parse_dt(value, default):
    if not value:
        return default
    parsed = parse_datetime(value)
    return parsed or default


def _upsert_banner(import_job):
    metadata = import_job.metadata or {}
    banner = import_job.banner
    if banner is None and metadata.get('banner_id'):
        banner = PromotionalBanner.objects.filter(pk=metadata['banner_id']).first()

    if banner is None:
        now = timezone.now()
        banner = PromotionalBanner.objects.create(
            title=metadata.get('title') or Path(import_job.source_path).stem.replace('_', ' ').title(),
            description=metadata.get('description', ''),
            display_type=metadata.get('display_type', 'BANNER'),
            placement=metadata.get('placement', 'HOME_TOP'),
            platform=metadata.get('platform', 'ALL'),
            image='',
            mobile_image='',
            link_type=metadata.get('link_type', 'NONE'),
            link_url=metadata.get('link_url', ''),
            link_category_id=metadata.get('category_id') or None,
            link_merchant_id=metadata.get('merchant_id') or None,
            cta_text=metadata.get('cta_text', ''),
            start_date=_parse_dt(metadata.get('start_date'), now),
            end_date=_parse_dt(metadata.get('end_date'), now + timezone.timedelta(days=30)),
            is_verified=metadata.get('is_verified', False),
            is_active=metadata.get('is_active', True),
            sort_order=metadata.get('sort_order', 0),
        )
    else:
        update_fields = []
        editable_fields = [
            'title', 'description', 'display_type', 'placement', 'platform',
            'link_type', 'link_url', 'cta_text', 'is_verified', 'is_active',
            'sort_order',
        ]
        for field in editable_fields:
            if field in metadata:
                setattr(banner, field, metadata[field])
                update_fields.append(field)
        if 'category_id' in metadata:
            banner.link_category_id = metadata.get('category_id') or None
            update_fields.append('link_category')
        if 'merchant_id' in metadata:
            banner.link_merchant_id = metadata.get('merchant_id') or None
            update_fields.append('link_merchant')
        if 'start_date' in metadata:
            banner.start_date = _parse_dt(metadata.get('start_date'), banner.start_date)
            update_fields.append('start_date')
        if 'end_date' in metadata:
            banner.end_date = _parse_dt(metadata.get('end_date'), banner.end_date)
            update_fields.append('end_date')
        if update_fields:
            update_fields.append('updated_at')
            banner.save(update_fields=list(set(update_fields)))

    listing_ids = metadata.get('listing_ids') or []
    if metadata.get('listing_id'):
        listing_ids = [metadata['listing_id'], *listing_ids]

    if listing_ids:
        existing_listing_ids = set(
            Listing.objects.filter(id__in=listing_ids).values_list('id', flat=True)
        )
        for index, listing_id in enumerate(listing_ids):
            try:
                listing_uuid = uuid.UUID(str(listing_id))
            except ValueError:
                continue
            if listing_uuid not in existing_listing_ids:
                continue
            BannerListing.objects.get_or_create(
                banner=banner,
                listing_id=listing_uuid,
                defaults={'sort_order': index},
            )

    import_job.banner = banner
    import_job.save(update_fields=['banner', 'updated_at'])
    return banner


def _upload_file_with_presigned_url(file_path, s3_key, content_type):
    upload_url = generate_presigned_put_url(s3_key, content_type=content_type)
    with Path(file_path).open('rb') as handle:
        payload = handle.read()
    req = urllib_request.Request(
        upload_url,
        data=payload,
        method='PUT',
        headers={'Content-Type': content_type, 'x-amz-acl': 'private'},
    )
    with urllib_request.urlopen(req, timeout=60) as response:
        if response.status >= 300:
            raise ValueError(f'S3 upload failed with status {response.status}')


def _move_import_files(import_job, destination_dir):
    destination_dir.mkdir(parents=True, exist_ok=True)
    source_path = Path(import_job.source_path)
    if source_path.exists():
        shutil.move(str(source_path), str(_safe_child_path(destination_dir, source_path.name)))
    if import_job.sidecar_path:
        sidecar_path = Path(import_job.sidecar_path)
        if sidecar_path.exists():
            shutil.move(str(sidecar_path), str(_safe_child_path(destination_dir, sidecar_path.name)))


def process_banner_image_import(import_id):
    with transaction.atomic():
        import_job = BannerImageImport.objects.select_for_update().get(pk=import_id)
        if import_job.status not in ['PENDING', 'FAILED']:
            return {'status': import_job.status, 'banner_id': str(import_job.banner_id) if import_job.banner_id else None}

        import_job.status = 'PROCESSING'
        import_job.error_message = ''
        import_job.save(update_fields=['status', 'error_message', 'updated_at'])

    try:
        source_path = Path(import_job.source_path)
        if not source_path.exists():
            raise FileNotFoundError(f'Import file not found: {source_path}')

        banner = _upsert_banner(import_job)
        target_field = import_job.target_field
        variant = 'mobile' if target_field == 'mobile_image' else 'large'
        image_group_id = uuid.uuid4()
        s3_key = build_s3_key('banner', str(image_group_id), variant)
        content_type = mimetypes.guess_type(source_path.name)[0] or 'image/webp'

        with source_path.open('rb') as image_file:
            width, height = get_image_dimensions(image_file)
        if not width or not height:
            raise ValueError('Could not determine banner image dimensions.')

        _upload_file_with_presigned_url(source_path, s3_key, content_type)

        asset = ImageAsset.objects.create(
            owner=_get_asset_owner(),
            image_group_id=image_group_id,
            object_id=banner.id,
            image_type='banner',
            variant=variant,
            s3_key=s3_key,
            width=width,
            height=height,
            size_bytes=source_path.stat().st_size,
            is_confirmed=True,
        )

        cdn_url = asset.cdn_url()
        if target_field == 'mobile_image':
            banner.mobile_image = cdn_url
            banner.mobile_image_asset = asset
            banner.save(update_fields=['mobile_image', 'mobile_image_asset', 'updated_at'])
        else:
            banner.image = cdn_url
            banner.image_asset = asset
            banner.save(update_fields=['image', 'image_asset', 'updated_at'])

        import_job.status = 'UPLOADED'
        import_job.image_asset = asset
        import_job.processed_at = timezone.now()
        import_job.save(update_fields=['status', 'image_asset', 'processed_at', 'updated_at'])
        _move_import_files(import_job, get_banner_processed_dir())
        return {'status': 'UPLOADED', 'banner_id': str(banner.id), 'cdn_url': cdn_url}
    except Exception as exc:
        import_job.status = 'FAILED'
        import_job.error_message = str(exc)
        import_job.save(update_fields=['status', 'error_message', 'updated_at'])
        return {'status': 'FAILED', 'error': str(exc)}
