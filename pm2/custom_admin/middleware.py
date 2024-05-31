import re

class ReferrerPolicyMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Check if the request path matches the pattern for the specific route
        if re.match(r'^/pm2/custom_admin/download_files/\d+$', request.path):
            response['Referrer-Policy'] = 'no-referrer-when-downgrade'  # Change this to your desired policy
        
        return response
