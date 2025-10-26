class ForcePrefixMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if response.status_code in (301, 302) and response.get('Location', '').startswith('/'):
            # Evita doppio /fornitori
            if not response['Location'].startswith('/fornitori'):
                response['Location'] = '/fornitori' + response['Location']
        return response
