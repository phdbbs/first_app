from django.utils.deprecation import MiddlewareMixin


class DistrictScopeMiddleware(MiddlewareMixin):
    """
    区县数据隔离中间件。
    - 市级政府管理员 (gov_city): user_district_scope = None, 表示可见全部区县。
    - 其他已登录用户: user_district_scope = user.district_id, 仅可见所属区县数据。
    - 未登录用户: 不设置该属性。
    """

    def process_request(self, request):
        user = getattr(request, 'user', None)
        if user is None or not user.is_authenticated:
            return None
        if user.role == 'gov_city':
            request.user_district_scope = None
        else:
            request.user_district_scope = user.district_id
        return None
