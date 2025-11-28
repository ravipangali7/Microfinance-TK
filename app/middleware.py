from django.utils.deprecation import MiddlewareMixin
import json


class AddUserRolesMiddleware(MiddlewareMixin):
    """
    Middleware to add user roles and phone to all API responses.
    This ensures every response includes user_roles and user_phone.
    """
    
    def process_response(self, request, response):
        # Only process JSON responses from DRF API views
        if hasattr(response, 'data') and isinstance(response.data, dict):
            # Check if user is authenticated
            if hasattr(request, 'user') and request.user.is_authenticated:
                # Add user roles and phone to response
                if 'user_roles' not in response.data:
                    response.data['user_roles'] = [group.name for group in request.user.groups.all()]
                if 'user_phone' not in response.data:
                    response.data['user_phone'] = request.user.phone
        # Also handle regular HttpResponse with JSON content
        elif response.get('Content-Type', '').startswith('application/json'):
            try:
                if hasattr(request, 'user') and request.user.is_authenticated:
                    content = response.content.decode('utf-8')
                    if content:
                        data = json.loads(content)
                        if isinstance(data, dict):
                            if 'user_roles' not in data:
                                data['user_roles'] = [group.name for group in request.user.groups.all()]
                            if 'user_phone' not in data:
                                data['user_phone'] = request.user.phone
                            response.content = json.dumps(data).encode('utf-8')
            except (json.JSONDecodeError, UnicodeDecodeError, AttributeError):
                # If response is not JSON or can't be decoded, skip
                pass
        
        return response

