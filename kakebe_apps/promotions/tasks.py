from celery import shared_task

from .models import BannerImageImport
from .services import discover_banner_image_imports, process_banner_image_import


@shared_task
def discover_banner_image_imports_task():
    """Scan the banner import folder and enqueue new image files."""
    return {'created': discover_banner_image_imports()}


@shared_task
def process_pending_banner_image_imports(limit=10):
    """Upload pending banner image imports to S3 and attach them to banners."""
    discover_banner_image_imports()
    import_ids = list(
        BannerImageImport.objects
        .filter(status='PENDING')
        .order_by('created_at')
        .values_list('id', flat=True)[:limit]
    )

    results = []
    for import_id in import_ids:
        results.append(process_banner_image_import(import_id))
    return {'processed': len(results), 'results': results}
