from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import PermissionDenied
from functools import wraps

def manager_required(view_func):
    """マネージャー権限が必要なビュー用のデコレーター"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            from django.contrib.auth.views import redirect_to_login
            return redirect_to_login(request.get_full_path())
        
        if not (request.user.is_manager or request.user.is_superuser):
            raise PermissionDenied("マネージャー権限が必要です。")
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def is_manager(user):
    """ユーザーがマネージャーかどうかを判定"""
    return user.is_authenticated and (user.is_manager or user.is_superuser)