"""
Task 7: 物料供应链与双台账
- 物料列表/采购/下发/签收/异动
- 收容所台账 / 医院台账
- 芯片号段管理
"""
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt

from accounts.decorators import role_required
from business.models import Material, MaterialTransaction, Chip
from business.services import (
    json_ok, json_fail, parse_json_body, serialize_instance,
    generate_ledger_no, get_district_filtered_queryset,
    adjust_stock, get_hospital_stock,
)
from core.models import Institution


@csrf_exempt
@login_required
@role_required('shelter', 'hospital', 'gov_city', 'gov_district')
def material_list(request):
    """物料列表（含医院库存计算）"""
    user = request.user
    qs = get_district_filtered_queryset(Material, user)

    category = request.GET.get('category')
    if category:
        qs = qs.filter(category=category)

    data = []
    for m in qs:
        item = serialize_instance(m)
        # 如果用户是医院，附加该医院的库存
        if user.role == 'hospital' and user.institution_id:
            item['hospital_stock'] = get_hospital_stock(m, user.institution)
        else:
            # 列出所有关联医院的库存
            hospitals = Institution.objects.filter(
                type='hospital', district_id=m.district_id
            )
            item['hospital_stocks'] = {
                str(h.id): {
                    'name': h.name,
                    'stock': get_hospital_stock(m, h),
                }
                for h in hospitals
            }
        data.append(item)
    return json_ok(data)


@csrf_exempt
@login_required
@role_required('shelter', 'gov_city', 'gov_district')
def purchase_create(request):
    """采购入库

    请求体示例:
    {
        "material_id": 1,
        "quantity": 100,
        "supplier": "国药集团",
        "batch_no": "B20250101",
        "expiry_date": "2025-12-31",
        "chip_range_start": "1000010001",  // 芯片才需要
        "chip_range_end": "1000010100"
    }
    """
    data = parse_json_body(request)
    user = request.user

    material_id = data.get('material_id')
    if not material_id:
        return json_fail('缺少物料ID')

    try:
        material = Material.objects.get(id=material_id)
    except Material.DoesNotExist:
        return json_fail('物料不存在')

    quantity = int(data.get('quantity', 0))
    if quantity <= 0:
        return json_fail('采购数量必须大于0')

    district_id = material.district_id

    # 创建采购流水（收容所侧，hospital=None）
    txn = adjust_stock(
        material=material,
        hospital=None,
        quantity=quantity,
        txn_type='purchase',
        operator=user,
        operator_name=user.get_full_name() or user.username,
        supplier=data.get('supplier', ''),
        batch_no=data.get('batch_no', ''),
        from_to=data.get('supplier', ''),
        note=data.get('note', '采购入库'),
        ledger_no=generate_ledger_no('PUR'),
        district_id=district_id,
    )

    # 更新物料扩展信息
    update_fields = []
    if data.get('supplier'):
        material.supplier = data['supplier']
        update_fields.append('supplier')
    if data.get('batch_no'):
        material.batch_no = data['batch_no']
        update_fields.append('batch_no')
    if data.get('expiry_date'):
        try:
            material.expiry_date = datetime.strptime(str(data['expiry_date'])[:10], '%Y-%m-%d').date()
            update_fields.append('expiry_date')
        except (ValueError, TypeError):
            pass
    if update_fields:
        material.save(update_fields=update_fields)

    # 芯片采购：创建芯片号段
    if material.category == 'chip':
        range_start = data.get('chip_range_start', '')
        range_end = data.get('chip_range_end', '')
        if range_start and range_end:
            _create_chip_range(range_start, range_end, material)
            material.chip_range_start = range_start
            material.chip_range_end = range_end
            material.save(update_fields=['chip_range_start', 'chip_range_end'])

    return json_ok(serialize_instance(txn), message=f'采购入库成功，增加库存 {quantity}')


@csrf_exempt
@login_required
@role_required('shelter', 'gov_city', 'gov_district')
def dispatch_create(request):
    """下发至医院

    请求体示例:
    {
        "material_id": 1,
        "hospital_id": 3,
        "quantity": 50,
        "chip_numbers": ["1000010001", "1000010002"]  // 芯片可选指定号
    }
    """
    data = parse_json_body(request)
    user = request.user

    material_id = data.get('material_id')
    hospital_id = data.get('hospital_id')
    if not material_id or not hospital_id:
        return json_fail('缺少物料或医院信息')

    try:
        material = Material.objects.get(id=material_id)
    except Material.DoesNotExist:
        return json_fail('物料不存在')

    try:
        hospital = Institution.objects.get(id=hospital_id, type='hospital')
    except Institution.DoesNotExist:
        return json_fail('医院不存在')

    quantity = int(data.get('quantity', 0))
    if quantity <= 0:
        return json_fail('下发数量必须大于0')

    if material.shelter_stock < quantity:
        return json_fail(f'收容所库存不足（当前库存 {material.shelter_stock}）')

    # 检查芯片号是否可用
    chip_numbers = data.get('chip_numbers', [])
    if material.category == 'chip' and chip_numbers:
        unavailable = Chip.objects.filter(
            number__in=chip_numbers, status='used'
        ).count()
        if unavailable > 0:
            return json_fail(f'{unavailable} 个芯片号已被使用')

    # 创建下发流水（收容所侧扣减库存，同时关联目标医院）
    txn = adjust_stock(
        material=material,
        hospital=None,
        quantity=quantity,
        txn_type='dispatch',
        operator=user,
        operator_name=user.get_full_name() or user.username,
        from_to=hospital.name,
        note=f'下发至 {hospital.name}',
        ledger_no=generate_ledger_no('DIS'),
        district_id=material.district_id,
    )
    # 关联目标医院（用于医院台账统计）
    txn.hospital = hospital
    txn.save(update_fields=['hospital'])

    return json_ok(serialize_instance(txn), message=f'下发成功，数量 {quantity}')


@csrf_exempt
@login_required
@role_required('hospital')
def material_receive(request, pk):
    """医院确认签收下发物料"""
    try:
        txn = MaterialTransaction.objects.get(id=pk, type='dispatch')
    except MaterialTransaction.DoesNotExist:
        return json_fail('下发记录不存在', status=404)

    user = request.user
    if user.institution_id != txn.hospital_id:
        return json_fail('无权签收此物料')

    # 签收：在备注中标记，已有 dispatch 流水即代表在途库存
    txn.note = (txn.note + ' [已签收]' if txn.note else '[已签收]').strip()
    txn.save(update_fields=['note'])

    return json_ok(serialize_instance(txn), message='签收成功')


@csrf_exempt
@login_required
@role_required('hospital', 'gov_city', 'gov_district')
def stock_adjustment(request):
    """库存异动（过期/损坏/丢失）

    请求体示例:
    {
        "material_id": 1,
        "quantity": 5,
        "reason": "过期报废"
    }
    """
    data = parse_json_body(request)
    user = request.user

    material_id = data.get('material_id')
    if not material_id:
        return json_fail('缺少物料ID')

    try:
        material = Material.objects.get(id=material_id)
    except Material.DoesNotExist:
        return json_fail('物料不存在')

    quantity = int(data.get('quantity', 0))
    if quantity <= 0:
        return json_fail('异动数量必须大于0')

    hospital = None
    if user.role == 'hospital':
        hospital = user.institution
        if not hospital:
            return json_fail('缺少医院机构信息')

    txn = adjust_stock(
        material=material,
        hospital=hospital,
        quantity=quantity,
        txn_type='adjustment',
        operator=user,
        operator_name=user.get_full_name() or user.username,
        from_to=hospital.name if hospital else '收容所',
        note=data.get('reason', '库存异动'),
        ledger_no=generate_ledger_no('ADJ'),
        district_id=material.district_id,
    )

    return json_ok(serialize_instance(txn), message=f'异动登记成功，扣减 {quantity}')


@csrf_exempt
@login_required
@role_required('shelter', 'hospital', 'gov_city', 'gov_district')
def material_transactions(request):
    """物资流水列表（台账）"""
    user = request.user
    qs = get_district_filtered_queryset(MaterialTransaction, user)

    txn_type = request.GET.get('type')
    if txn_type:
        qs = qs.filter(type=txn_type)

    material_id = request.GET.get('material_id')
    if material_id:
        qs = qs.filter(material_id=material_id)

    if user.role == 'hospital':
        if user.institution_id:
            qs = qs.filter(hospital_id=user.institution_id)
        else:
            qs = qs.none()

    data = [serialize_instance(t) for t in qs]
    return json_ok(data)


@csrf_exempt
@login_required
@role_required('shelter', 'gov_city', 'gov_district')
def shelter_stock_ledger(request):
    """收容所台账（采购+下发+异动）"""
    user = request.user
    qs = get_district_filtered_queryset(MaterialTransaction, user)

    # 收容所台账：所有 hospital=None 的流水 + dispatch 流水
    qs = qs.filter(hospital__isnull=True) | qs.filter(type='dispatch')

    material_id = request.GET.get('material_id')
    if material_id:
        qs = qs.filter(material_id=material_id)

    data = []
    for txn in qs:
        item = serialize_instance(txn)
        data.append(item)
    return json_ok(data)


@csrf_exempt
@login_required
@role_required('hospital', 'gov_city', 'gov_district')
def hospital_stock_ledger(request):
    """医院台账（下发+消耗+异动）"""
    user = request.user
    qs = get_district_filtered_queryset(MaterialTransaction, user)

    if user.role == 'hospital':
        if user.institution_id:
            qs = qs.filter(hospital_id=user.institution_id)
        else:
            qs = qs.none()
    else:
        # 政府/收容所查看时只看有医院关联的流水
        qs = qs.filter(hospital__isnull=False)

    data = [serialize_instance(t) for t in qs]
    return json_ok(data)


# ============================================
# 辅助函数
# ============================================
def _create_chip_range(range_start, range_end, material):
    """根据芯片号段创建 Chip 记录

    支持纯数字号段（如 1000010001 ~ 1000010100）
    """
    try:
        start_num = int(range_start)
        end_num = int(range_end)
    except (ValueError, TypeError):
        return

    if end_num < start_num:
        return

    # 批量创建（跳过已存在的）
    existing = set(Chip.objects.filter(
        number__gte=range_start,
        number__lte=range_end
    ).values_list('number', flat=True))

    chips_to_create = []
    for n in range(start_num, end_num + 1):
        num_str = str(n)
        if num_str not in existing:
            chips_to_create.append(Chip(number=num_str))

    if chips_to_create:
        Chip.objects.bulk_create(chips_to_create, batch_size=200)
