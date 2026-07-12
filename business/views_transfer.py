"""
Task 5: 转运拆分下发
- 转运列表/创建/签收/驳回
- 支持拆分至多家医院
"""
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from accounts.decorators import role_required
from business.models import Transfer, Pet, Capture
from business.services import (
    json_ok, json_fail, parse_json_body, serialize_instance,
    generate_ledger_no, get_district_filtered_queryset,
)
from core.models import Institution


@csrf_exempt
@login_required
@role_required('shelter', 'gov_city', 'gov_district', 'hospital')
def transfer_list(request):
    """转运列表（收容所看发出，医院看接收）"""
    user = request.user
    qs = get_district_filtered_queryset(Transfer, user)

    if user.role == 'hospital':
        # 医院只看发给自己的
        if user.institution_id:
            qs = qs.filter(to_hospital_id=user.institution_id)
        else:
            qs = qs.none()
    elif user.role == 'shelter':
        # 收容所只看自己发出的
        if user.institution_id:
            qs = qs.filter(from_shelter_id=user.institution_id)

    status = request.GET.get('status')
    if status:
        qs = qs.filter(status=status)

    data = [serialize_instance(t) for t in qs]
    return json_ok(data)


@csrf_exempt
@login_required
@role_required('shelter', 'gov_city', 'gov_district')
def transfer_create(request):
    """创建转运记录（支持拆分至多家医院）

    请求体示例:
    {
        "capture_id": 1,
        "items": [
            {"hospital_id": 3, "pet_ids": [1, 2]},
            {"hospital_id": 4, "pet_ids": [3]}
        ]
    }
    """
    data = parse_json_body(request)
    user = request.user

    capture_id = data.get('capture_id')
    items = data.get('items', [])
    if not items:
        return json_fail('缺少转运明细')

    # 获取来源收容所
    shelter_id = data.get('from_shelter_id') or getattr(user, 'institution_id', None)
    if not shelter_id:
        return json_fail('缺少收容所信息')

    try:
        shelter = Institution.objects.get(id=shelter_id, type='shelter')
    except Institution.DoesNotExist:
        return json_fail('收容所不存在')

    district_id = data.get('district_id') or getattr(user, 'district_id', None)
    if not district_id:
        return json_fail('缺少区县信息')

    capture = None
    if capture_id:
        capture = Capture.objects.filter(id=capture_id).first()

    created = []
    for item in items:
        hospital_id = item.get('hospital_id')
        pet_ids = item.get('pet_ids', [])
        if not hospital_id or not pet_ids:
            continue

        try:
            hospital = Institution.objects.get(id=hospital_id, type='hospital')
        except Institution.DoesNotExist:
            continue

        pets = Pet.objects.filter(id__in=pet_ids, status='in_transit')
        if not pets.exists():
            continue

        pet_codes = [p.code for p in pets]
        transfer = Transfer.objects.create(
            capture=capture,
            from_shelter=shelter,
            from_shelter_name=shelter.name,
            to_hospital=hospital,
            to_hospital_name=hospital.name,
            pet_codes=','.join(pet_codes),
            pet_count=len(pet_codes),
            status='pending',
            operator=user,
            operator_name=user.get_full_name() or user.username,
            ledger_no=generate_ledger_no('TRF'),
            district_id=district_id,
        )

        # 更新宠物归属医院（状态保持 in_transit 直到签收）
        for pet in pets:
            pet.hospital = hospital
            pet.save(update_fields=['hospital'])

        created.append(serialize_instance(transfer))

    return json_ok(created, message=f'创建 {len(created)} 条转运记录')


@csrf_exempt
@login_required
@role_required('hospital')
def transfer_receive(request, pk):
    """医院签收转运"""
    try:
        transfer = Transfer.objects.get(id=pk)
    except Transfer.DoesNotExist:
        return json_fail('转运记录不存在', status=404)

    if transfer.status != 'pending':
        return json_fail(f'当前状态({transfer.status})不可签收')

    user = request.user
    if user.institution_id != transfer.to_hospital_id:
        return json_fail('无权签收此转运记录')

    transfer.status = 'received'
    transfer.received_at = timezone.now().date()
    transfer.save(update_fields=['status', 'received_at'])

    # 更新宠物状态为待诊疗
    pet_codes = [c.strip() for c in transfer.pet_codes.split(',') if c.strip()]
    Pet.objects.filter(code__in=pet_codes).update(status='in_treatment')

    return json_ok(serialize_instance(transfer), message='签收成功')


@csrf_exempt
@login_required
@role_required('hospital')
def transfer_reject(request, pk):
    """医院驳回转运"""
    data = parse_json_body(request)

    try:
        transfer = Transfer.objects.get(id=pk)
    except Transfer.DoesNotExist:
        return json_fail('转运记录不存在', status=404)

    if transfer.status != 'pending':
        return json_fail(f'当前状态({transfer.status})不可驳回')

    user = request.user
    if user.institution_id != transfer.to_hospital_id:
        return json_fail('无权驳回此转运记录')

    transfer.status = 'rejected'
    transfer.reject_reason = data.get('reason', '')
    transfer.save(update_fields=['status', 'reject_reason'])

    # 宠物状态回退为 in_transit
    pet_codes = [c.strip() for c in transfer.pet_codes.split(',') if c.strip()]
    Pet.objects.filter(code__in=pet_codes).update(status='in_transit')

    return json_ok(serialize_instance(transfer), message='已驳回')
