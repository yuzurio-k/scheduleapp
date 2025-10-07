from django.utils.cache import add_never_cache_headers
from django.utils.deprecation import MiddlewareMixin

class NoCacheMiddleware(MiddlewareMixin):
    """認証が必要なページでキャッシュを無効にするミドルウェア"""
    
    def process_response(self, request, response):
        # ログインが必要なページの場合、キャッシュを無効にする
        if hasattr(request, 'user') and request.user.is_authenticated:
            # 認証済みユーザーのページはキャッシュしない
            add_never_cache_headers(response)
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate, private'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
            
        # ログイン・ログアウトページもキャッシュしない
        if request.path.startswith('/accounts/'):
            add_never_cache_headers(response)
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate, private'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
            
        return response