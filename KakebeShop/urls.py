from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from django.http import JsonResponse
from django.db import connection

from KakebeShop import settings

schema_view = get_schema_view(
    openapi.Info(
        title="Kakebe Shop Backend",
        default_version='v1',
        description="Test description",
        terms_of_service="https://backend.kakebeshop.com/terms/",
        contact=openapi.Contact(email="contact@kakebeshop.com"),
        license=openapi.License(name="Kakebeshop License"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny,],
    authentication_classes=[]
)

def health_check(request):
    try:
        # Check database connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        return JsonResponse({"status": "healthy"}, status=200)
    except Exception as e:
        return JsonResponse({"status": "unhealthy", "error": str(e)}, status=500)
urlpatterns = [
    path('admin/', admin.site.urls),
    #local apps
    path('auth/', include('kakebe_apps.authentication.urls')),
    path('social_auth/', include(('kakebe_apps.social_auth.urls', 'social_auth'), namespace="social_auth")),
    path('health/', health_check, name='health_check'),


    #================ Apps api====================
    path('api/v1/', include([
        path('', include('kakebe_apps.categories.urls')),
        path('', include('kakebe_apps.listings.urls')),
        path('', include('kakebe_apps.location.urls')),
        path('', include('kakebe_apps.merchants.urls')),

        path('', include('kakebe_apps.cart.urls')),
        path('', include('kakebe_apps.orders.urls')),
        path('', include('kakebe_apps.transactions.urls')),
        path('', include('kakebe_apps.engagement.urls')),
        path('', include('kakebe_apps.promotions.urls')),

        path('', include('kakebe_apps.notifications.urls')),

        path('image/', include('kakebe_apps.imagehandler.urls')),

    ])),


    #=============== END OF APPS APIs ==============================



    # Swagger endpoints
    path('', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('api/api.json/', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),


]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)