"""
门户端视图 - 各角色门户页面渲染 + 门户专用辅助 API。
"""
import json

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

from accounts.decorators import role_required
from business.models import Pet, AdoptionHallListing, Adoption, Message
from business.services import (
    json_ok, json_fail, parse_json_body, serialize_instance,
    get_district_filtered_queryset,
)


# ============================================
# 收容所门户页面
# ============================================
@login_required
@role_required('shelter', 'gov_city', 'gov_district')
def shelter_portal(request):
    """收容所端门户页面。"""
    user = request.user
    user_data = {
        'id': user.id,
        'username': user.username,
        'name': user.get_full_name() or user.username,
        'role': user.role,
        'role_display': user.get_role_display(),
        'district_id': user.district_id,
        'district_name': user.district.name if user.district else '',
        'institution_id': user.institution_id,
        'institution_name': user.institution.name if user.institution else '',
        'phone': user.phone,
    }
    return render(request, 'portal/shelter/portal.html', {
        'user_data': json.dumps(user_data, ensure_ascii=False),
    })


# ============================================
# 医院门户页面
# ============================================
@login_required
@role_required('hospital', 'gov_city', 'gov_district')
def hospital_portal(request):
    """宠物医院端门户页面。"""
    user = request.user
    user_data = {
        'id': user.id,
        'username': user.username,
        'name': user.get_full_name() or user.username,
        'role': user.role,
        'role_display': user.get_role_display(),
        'district_id': user.district_id,
        'district_name': user.district.name if user.district else '',
        'institution_id': user.institution_id,
        'institution_name': user.institution.name if user.institution else '',
        'phone': user.phone,
    }
    return render(request, 'portal/hospital/portal.html', {
        'user_data': json.dumps(user_data, ensure_ascii=False),
    })


# ============================================
# 政府监管门户页面
# ============================================
@login_required
@role_required('gov_city', 'gov_district')
def gov_portal(request):
    """政府监管端门户页面。"""
    user = request.user
    user_data = {
        'id': user.id,
        'username': user.username,
        'name': user.get_full_name() or user.username,
        'role': user.role,
        'role_display': user.get_role_display(),
        'district_id': user.district_id,
        'district_name': user.district.name if user.district else '',
        'institution_id': user.institution_id,
        'institution_name': user.institution.name if user.institution else '',
        'phone': user.phone,
    }
    return render(request, 'portal/gov/portal.html', {
        'user_data': json.dumps(user_data, ensure_ascii=False),
    })


# ============================================
# 门户专用辅助 API - 医院
# ============================================
@csrf_exempt
@login_required
@role_required('hospital', 'gov_city', 'gov_district')
def hospital_pets(request):
    """医院在院宠物列表（可按 status 过滤）。

    GET /api/business/pets/?status=in_treatment
    """
    user = request.user
    qs = get_district_filtered_queryset(Pet, user)

    if user.role == 'hospital':
        if user.institution_id:
            qs = qs.filter(hospital_id=user.institution_id)
        else:
            qs = qs.none()

    status = request.GET.get('status')
    if status:
        qs = qs.filter(status=status)

    data = [serialize_instance(p) for p in qs]
    return json_ok(data)


@csrf_exempt
@login_required
@role_required('hospital', 'gov_city', 'gov_district')
def hospital_hall_listings(request):
    """医院领养大厅上架信息列表（含已下架）。

    GET /api/business/hall-listings/
    """
    user = request.user
    qs = AdoptionHallListing.objects.all()

    if user.role == 'hospital':
        if user.institution_id:
            qs = qs.filter(hospital_id=user.institution_id)
        else:
            qs = qs.none()
    else:
        qs = get_district_filtered_queryset(AdoptionHallListing, user)

    data = []
    for listing in qs:
        item = serialize_instance(listing)
        item['pet'] = serialize_instance(listing.pet) if listing.pet_id else None
        data.append(item)
    return json_ok(data)


# ============================================
# 领养人门户页面
# ============================================
@login_required
@role_required('adopter', 'gov_city', 'gov_district')
def adopter_portal(request):
    """领养人端门户页面（登录后全功能）。"""
    user = request.user
    user_data = {
        'id': user.id,
        'username': user.username,
        'name': user.get_full_name() or user.username,
        'role': user.role,
        'role_display': user.get_role_display(),
        'district_id': user.district_id,
        'district_name': user.district.name if user.district else '',
        'institution_id': user.institution_id,
        'institution_name': user.institution.name if user.institution else '',
        'phone': user.phone,
    }
    return render(request, 'portal/adopter/portal.html', {
        'user_data': json.dumps(user_data, ensure_ascii=False),
        'public_mode': False,
    })


def adoption_hall_public(request):
    """领养大厅公开页面（无需登录）。

    未登录或非领养人角色时仅展示领养大厅；
    已登录的领养人/政府角色直接进入完整门户。
    """
    if request.user.is_authenticated and request.user.role in ('adopter', 'gov_city', 'gov_district'):
        return adopter_portal(request)

    user_data = None
    if request.user.is_authenticated:
        user_data = json.dumps({
            'id': request.user.id,
            'username': request.user.username,
            'name': request.user.get_full_name() or request.user.username,
            'role': request.user.role,
            'role_display': request.user.get_role_display(),
            'phone': request.user.phone,
        }, ensure_ascii=False)

    return render(request, 'portal/adopter/portal.html', {
        'user_data': user_data or 'null',
        'public_mode': True,
    })


# ============================================
# 门户专用辅助 API - 领养人
# ============================================
@csrf_exempt
@login_required
@role_required('adopter', 'gov_city', 'gov_district')
def my_adoptions(request):
    """领养人 - 我的领养记录列表。"""
    qs = Adoption.objects.filter(adopter=request.user).order_by('-id')
    data = []
    for a in qs:
        item = serialize_instance(a)
        if a.pet_id:
            item['pet'] = serialize_instance(a.pet)
        data.append(item)
    return json_ok(data)


@csrf_exempt
@login_required
@role_required('adopter', 'gov_city', 'gov_district')
def my_messages(request):
    """领养人 - 我的消息列表。"""
    qs = Message.objects.filter(user=request.user).order_by('-id')
    data = [serialize_instance(m) for m in qs]
    return json_ok(data)


@csrf_exempt
@login_required
@role_required('adopter', 'gov_city', 'gov_district')
def mark_message_read(request, pk):
    """领养人 - 标记消息已读。"""
    if request.method != 'POST':
        return json_fail('仅支持 POST 请求', status=405)
    try:
        msg = Message.objects.get(id=pk, user=request.user)
    except Message.DoesNotExist:
        return json_fail('消息不存在', status=404)

    msg.is_read = True
    msg.save(update_fields=['is_read'])
    return json_ok(serialize_instance(msg), message='已标记为已读')
