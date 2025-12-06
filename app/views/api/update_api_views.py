from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from app.models import MySetting

@csrf_exempt
@require_http_methods(["GET"])
def check_update_api(request):
    """
    Check if app update is available
    Expected query params: current_version (e.g., "1.0.0"), version_code (e.g., "1")
    """
    try:
        current_version = request.GET.get('current_version', '0.0.0')
        current_version_code = int(request.GET.get('version_code', '0'))
        
        # Get settings from database
        settings = MySetting.get_settings()
        
        # Get latest version info from settings
        latest_version = settings.latest_app_version or '1.0.0'
        latest_version_code = settings.latest_version_code or 1
        
        # Build APK URL if file exists
        apk_url = None
        if settings.apk_file and hasattr(settings.apk_file, 'url'):
            apk_url = request.build_absolute_uri(settings.apk_file.url)
        
        # Compare versions
        needs_update = current_version_code < latest_version_code
        
        response_data = {
            "needs_update": needs_update,
            "current_version": current_version,
            "current_version_code": current_version_code,
            "latest_version": latest_version,
            "latest_version_code": latest_version_code,
            "apk_url": apk_url if needs_update and apk_url else None,
            "mandatory": settings.mandatory_update if needs_update else False,
            "message": settings.update_message if needs_update and settings.update_message else None,
            "release_notes": settings.release_notes if needs_update and settings.release_notes else None
        }
        
        return JsonResponse(response_data, status=200)
        
    except Exception as e:
        return JsonResponse({
            "error": str(e),
            "needs_update": False
        }, status=500)

