from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages


def role_required(*roles):
    """角色校验装饰器: 仅允许指定角色访问。"""
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
            if request.user.role not in roles:
                messages.error(request, '无权访问该页面')
                return redirect('/')
            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator
