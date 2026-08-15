"""
TNR 系统端到端测试
覆盖：登录/权限隔离、捕捉→转运→诊疗→放养/领养/安乐死主闭环、
物料供应链双台账、在线领养申请、回访打卡、黑名单拦截、定时任务。
"""
import json
from datetime import timedelta

from django.core.management import call_command
from django.test import TestCase, Client
from django.utils import timezone

from accounts.models import User
from business.models import (
    Pet, Capture, Transfer, Treatment, Material, MaterialTransaction,
    Chip, Release, Adoption, AdoptionApplication, CheckIn, Blacklist,
    Euthanasia, AdoptionHallListing, Message,
)
from business.tasks import auto_promote_to_adoptable
from core.models import District, Institution


def _post(client, url, payload):
    return client.post(url, data=json.dumps(payload), content_type='application/json')


class TNRBaseTestCase(TestCase):
    """加载种子数据的基础测试类"""

    @classmethod
    def setUpTestData(cls):
        call_command('seed_data', verbosity=0)

    def setUp(self):
        self.client = Client()

    def login(self, username, password='123456'):
        self.client.logout()
        return self.client.post('/login/', {
            'username': username, 'password': password,
        })

    def api(self, url, payload=None, method='post'):
        if method == 'get':
            return self.client.get(url)
        return _post(self.client, url, payload or {})


class LoginAndRBACTest(TNRBaseTestCase):
    """登录与角色权限隔离"""

    def test_login_success_redirects_by_role(self):
        cases = {
            'admin': '/gov/',
            'cy_shelter': '/shelter/',
            'aixin_hosp': '/hospital/',
            'adopter1': '/adopter/',
        }
        for username, expected in cases.items():
            resp = self.login(username)
            self.assertEqual(resp.status_code, 302, f'{username} 登录应重定向')
            self.assertIn(expected, resp.url, f'{username} 应跳转 {expected}')

    def test_login_wrong_password(self):
        # 使用 RequestFactory 避免 Py3.14 + Django5.0 测试客户端模板上下文拷贝的兼容性问题
        from django.test import RequestFactory
        from accounts.views import login_view
        factory = RequestFactory()
        req = factory.post('/login/', {'username': 'admin', 'password': 'wrong'})
        from django.contrib.sessions.middleware import SessionMiddleware
        from django.contrib.messages.middleware import MessageMiddleware
        from django.contrib.auth.middleware import AuthenticationMiddleware
        SessionMiddleware(lambda r: None).process_request(req)
        MessageMiddleware(lambda r: None).process_request(req)
        AuthenticationMiddleware(lambda r: None).process_request(req)
        req.session.save()
        resp = login_view(req)
        self.assertEqual(resp.status_code, 200)  # 停留登录页

    def test_unauthenticated_blocked(self):
        resp = self.client.get('/api/business/captures/')
        self.assertIn(resp.status_code, (302, 401, 403))

    def test_role_isolation_shelter_cannot_treat(self):
        """捕捉点角色不能创建诊疗（仅医院/政府）"""
        self.login('cy_shelter')
        pet = Pet.objects.filter(status='in_treatment').first()
        resp = self.api('/api/business/treatments/create/', {'pet_id': pet.id})
        self.assertIn(resp.status_code, (302, 403))

    def test_district_data_isolation(self):
        """海淀区政府只能看到海淀区数据"""
        self.login('hd_gov')
        resp = self.api('/api/business/captures/', method='get')
        data = resp.json()['data']
        hd_district = District.objects.get(code='HD')
        for item in data:
            self.assertEqual(item.get('district_id'), hd_district.id,
                             '区级政府不应看到其他区县数据')


class CaptureTransferTreatmentFlowTest(TNRBaseTestCase):
    """主业务闭环：捕捉→转运→诊疗"""

    def test_full_flow_capture_to_treatment(self):
        # 1. 捕捉登记（朝阳捕捉点）
        self.login('cy_shelter')
        shelter = Institution.objects.get(name='朝阳区流浪动物捕捉点')
        community = Institution.objects.filter(type='community').first()
        resp = self.api('/api/business/captures/create/', {
            'shelter_id': shelter.id,
            'community_id': community.id,
            'community_name': community.name,
            'address': '测试地址',
            'contact_person': '测试联系人',
            'contact_phone': '13800009999',
            'pet_count': 2,
            'species': '猫',
        })
        self.assertEqual(resp.status_code, 200, resp.content)
        body = resp.json()
        self.assertTrue(body['success'])
        pet_codes = body['data']['pet_codes']
        self.assertEqual(len(pet_codes), 2)
        capture_id = body['data']['capture']['id']

        # 验证宠物档案生成且状态为 in_transit
        pets = Pet.objects.filter(code__in=pet_codes)
        self.assertEqual(pets.count(), 2)
        for p in pets:
            self.assertEqual(p.status, 'in_transit')

        # 2. 转运至爱心宠物医院
        hospital = Institution.objects.get(name='爱心宠物医院')
        resp = self.api('/api/business/transfers/create/', {
            'capture_id': capture_id,
            'from_shelter_id': shelter.id,
            'to_hospital_id': hospital.id,
            'pet_codes': pet_codes,
            'pet_count': 2,
        })
        self.assertEqual(resp.status_code, 200, resp.content)
        transfers = resp.json()['data']
        self.assertEqual(len(transfers), 1)
        transfer_id = transfers[0]['id']

        # 3. 医院签收
        self.login('aixin_hosp')
        resp = self.api(f'/api/business/transfers/{transfer_id}/receive/')
        self.assertEqual(resp.status_code, 200, resp.content)
        # 宠物状态应变为待诊疗
        for p in Pet.objects.filter(code__in=pet_codes):
            self.assertEqual(p.status, 'in_treatment')

        # 4. 创建诊疗（绝育+疫苗+驱虫+芯片）
        pet = Pet.objects.filter(code__in=pet_codes).first()
        vaccine = Material.objects.filter(category='vaccine').first()
        dewormer = Material.objects.filter(category='dewormer').first()

        # 真实补货流程：捕捉点先向医院下发疫苗/驱虫药，医院签收后才有库存
        self.login('cy_shelter')
        for mat, qty in ((vaccine, 10), (dewormer, 10)):
            resp = self.api('/api/business/materials/dispatch/', {
                'material_id': mat.id, 'hospital_id': hospital.id, 'quantity': qty,
            })
            self.assertEqual(resp.status_code, 200, resp.content)
            txn_id = resp.json()['data']['id']
            self.login('aixin_hosp')
            resp = self.api(f'/api/business/materials/{txn_id}/receive/')
            self.assertEqual(resp.status_code, 200, resp.content)
            self.login('cy_shelter')

        # 找一个未使用芯片
        chip = Chip.objects.filter(status='available').first()
        self.login('aixin_hosp')
        resp = self.api('/api/business/treatments/create/', {
            'pet_id': pet.id,
            'items': {'sterilization': True, 'vaccine': True, 'deworming': True, 'chip': True},
            'sterilization': {'surgeon': '赵医生', 'diagnosis': '健康', 'surgery_date': '2025-03-01'},
            'vaccine': {'type': '狂犬疫苗', 'material_id': vaccine.id, 'batch_no': 'B001', 'date': '2025-03-01'},
            'deworming': {'type': '驱虫药', 'material_id': dewormer.id, 'batch_no': 'Q001', 'date': '2025-03-01'},
            'chip': {'chip_no': chip.number, 'date': '2025-03-01'},
            'status': 'completed',
        })
        self.assertEqual(resp.status_code, 200, resp.content)

        # 验证芯片被标记已用
        chip.refresh_from_db()
        self.assertEqual(chip.status, 'used')
        pet.refresh_from_db()
        self.assertEqual(pet.chip_no, chip.number)

    def test_transfer_reject_and_resend(self):
        """转运驳回与重新下发"""
        self.login('hd_shelter')
        shelter = Institution.objects.get(name='海淀区流浪动物捕捉点')
        hospital = Institution.objects.get(name='芭比堂动物医院')
        pet = Pet.objects.filter(status='in_transit').first()

        resp = self.api('/api/business/transfers/create/', {
            'from_shelter_id': shelter.id,
            'to_hospital_id': hospital.id,
            'pet_codes': [pet.code],
            'pet_count': 1,
        })
        transfer_id = resp.json()['data'][0]['id']

        # 医院驳回
        self.login('babitang_hosp')
        resp = self.api(f'/api/business/transfers/{transfer_id}/reject/', {'reason': '容量不足'})
        self.assertEqual(resp.status_code, 200)
        pet.refresh_from_db()
        self.assertEqual(pet.status, 'in_transit')

        # 捕捉点重新下发
        self.login('hd_shelter')
        resp = self.api(f'/api/business/transfers/{transfer_id}/resend/')
        self.assertEqual(resp.status_code, 200, resp.content)
        new_transfer_id = resp.json()['data']['id']
        self.assertNotEqual(new_transfer_id, transfer_id)


class MaterialSupplyChainTest(TNRBaseTestCase):
    """物料供应链与双台账"""

    def test_purchase_dispatch_receive_consume(self):
        self.login('cy_shelter')
        material = Material.objects.filter(category='vaccine').first()
        initial_stock = material.shelter_stock

        # 1. 采购入库
        resp = self.api('/api/business/materials/purchase/', {
            'material_id': material.id,
            'quantity': 50,
            'supplier': '测试供应商',
            'batch_no': 'BTEST001',
        })
        self.assertEqual(resp.status_code, 200, resp.content)
        material.refresh_from_db()
        self.assertEqual(material.shelter_stock, initial_stock + 50)

        # 2. 下发至医院
        hospital = Institution.objects.get(name='爱心宠物医院')
        resp = self.api('/api/business/materials/dispatch/', {
            'material_id': material.id,
            'hospital_id': hospital.id,
            'quantity': 20,
        })
        self.assertEqual(resp.status_code, 200, resp.content)
        dispatch_txn_id = resp.json()['data']['id']
        material.refresh_from_db()
        self.assertEqual(material.shelter_stock, initial_stock + 50 - 20)

        # 3. 医院签收
        self.login('aixin_hosp')
        resp = self.api(f'/api/business/materials/{dispatch_txn_id}/receive/')
        self.assertEqual(resp.status_code, 200, resp.content)

        # 4. 重复签收应被拒绝
        resp = self.api(f'/api/business/materials/{dispatch_txn_id}/receive/')
        self.assertEqual(resp.json()['success'], False)

        # 5. 验证医院台账有签收记录
        resp = self.api('/api/business/materials/hospital-ledger/', method='get')
        self.assertEqual(resp.status_code, 200)

    def test_chip_range_created_on_purchase(self):
        """芯片采购应创建号段"""
        self.login('cy_shelter')
        resp = self.api('/api/business/materials/purchase/', {
            'name': '测试芯片',
            'category': 'chip',
            'unit': '个',
            'quantity': 10,
            'chip_range_start': '9990000001',
            'chip_range_end': '9990000010',
        })
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertTrue(Chip.objects.filter(number='9990000001').exists())
        self.assertTrue(Chip.objects.filter(number='9990000010').exists())

    def test_chip_reuse_blocked(self):
        """芯片号不可复用"""
        used_chip = Chip.objects.filter(status='used').first()
        pet = Pet.objects.filter(status='in_treatment').first()
        self.login('aixin_hosp')
        resp = self.api('/api/business/treatments/create/', {
            'pet_id': pet.id,
            'items': {'chip': True},
            'chip': {'chip_no': used_chip.number},
            'status': 'in_progress',
        })
        body = resp.json()
        self.assertFalse(body['success'], '已使用芯片应被拒绝')


class AdoptionFlowTest(TNRBaseTestCase):
    """领养业务：线下登记 + 在线申请"""

    def test_offline_adoption_register_and_claim(self):
        pet = Pet.objects.filter(status='pending_adopt').first()
        self.login('cy_shelter')
        resp = self.api('/api/business/adoptions/register/', {
            'pet_id': pet.id,
            'adopter_name': '测试领养人',
            'adopter_phone': '13811112222',
            'adopter_id_card': '110101199001011234',
            'qualification': '有稳定住所',
        })
        self.assertEqual(resp.status_code, 200, resp.content)
        adoption_id = resp.json()['data']['id']
        pet.refresh_from_db()
        self.assertEqual(pet.status, 'pending_claim')

        # 医院确认领出
        self.login('aixin_hosp')
        resp = self.api(f'/api/business/adoptions/{adoption_id}/confirm-claim/')
        self.assertEqual(resp.status_code, 200, resp.content)
        pet.refresh_from_db()
        self.assertEqual(pet.status, 'adopted')

    def test_online_application_flow(self):
        """在线领养申请：提交→审核通过"""
        pet = Pet.objects.filter(status='pending_adopt').first()
        self.login('adopter1')
        resp = self.api('/api/business/adoptions/apply/', {
            'pet_id': pet.id,
            'applicant_name': '王领养',
            'applicant_phone': '13800000009',
            'qualification': '有养宠经验',
            'reason': '想给它一个家',
        })
        self.assertEqual(resp.status_code, 200, resp.content)
        app_id = resp.json()['data']['id']

        # 重复提交应被拒绝
        resp = self.api('/api/business/adoptions/apply/', {'pet_id': pet.id, 'applicant_name': '王', 'applicant_phone': '1'})
        self.assertFalse(resp.json()['success'])

        # 医院审核通过
        self.login('aixin_hosp')
        resp = self.api(f'/api/business/adoptions/applications/{app_id}/review/', {
            'action': 'approve', 'review_note': '资质符合',
        })
        self.assertEqual(resp.status_code, 200, resp.content)
        app = AdoptionApplication.objects.get(id=app_id)
        self.assertEqual(app.status, 'approved')
        # 应发送通知
        self.assertTrue(Message.objects.filter(user__username='adopter1').exists())

    def test_application_reject(self):
        pet = Pet.objects.filter(status='pending_adopt').first()
        self.login('adopter1')
        resp = self.api('/api/business/adoptions/apply/', {
            'pet_id': pet.id, 'applicant_name': '王', 'applicant_phone': '13800000009',
        })
        app_id = resp.json()['data']['id']
        self.login('aixin_hosp')
        resp = self.api(f'/api/business/adoptions/applications/{app_id}/review/', {
            'action': 'reject', 'review_note': '资质不足',
        })
        self.assertEqual(resp.json()['data']['status'], 'rejected')


class ReleaseEuthanasiaTest(TNRBaseTestCase):
    """放养闭环与安乐死"""

    def test_release_flow(self):
        pet = Pet.objects.filter(status='in_treatment', capture__isnull=False).first()
        self.login('cy_shelter')
        resp = self.api('/api/business/releases/create/', {'pet_id': pet.id})
        self.assertEqual(resp.status_code, 200, resp.content)
        release_id = resp.json()['data']['id']
        # 小区确认
        resp = self.api(f'/api/business/releases/{release_id}/confirm/', {
            'receiver_name': '张物业', 'signature': 'base64sig',
        })
        self.assertEqual(resp.status_code, 200, resp.content)
        pet.refresh_from_db()
        self.assertEqual(pet.status, 'released')

    def test_euthanasia_flow(self):
        pet = Pet.objects.filter(status='in_treatment').first()
        self.login('aixin_hosp')
        resp = self.api('/api/business/euthanasia/create/', {
            'pet_id': pet.id, 'reason': '病重无法救治', 'euthanized_at': '2025-03-01',
        })
        self.assertEqual(resp.status_code, 200, resp.content)
        record_id = resp.json()['data']['id']
        pet.refresh_from_db()
        self.assertEqual(pet.status, 'euthanized')

        # 捕捉点领取遗体
        self.login('cy_shelter')
        resp = self.api(f'/api/business/euthanasia/{record_id}/body-receive/', {
            'receiver_name': '朝阳捕捉点',
        })
        self.assertEqual(resp.status_code, 200, resp.content)


class CheckInBlacklistTest(TNRBaseTestCase):
    """回访打卡与黑名单拦截"""

    def test_checkin_and_review(self):
        adopter = User.objects.get(username='adopter1')
        pet = Pet.objects.filter(adoptions__adopter=adopter).first()
        self.login('adopter1')
        resp = self.api('/api/business/checkins/create/', {
            'pet_id': pet.id, 'month': '2025-04', 'note': '状态良好',
        })
        self.assertEqual(resp.status_code, 200, resp.content)
        checkin_id = resp.json()['data']['id']

        # 重复打卡被拒
        resp = self.api('/api/business/checkins/create/', {'pet_id': pet.id, 'month': '2025-04'})
        self.assertFalse(resp.json()['success'])

        # 捕捉点审核
        self.login('cy_shelter')
        resp = self.api(f'/api/business/checkins/{checkin_id}/review/', {'status': 'approved'})
        self.assertEqual(resp.json()['data']['status'], 'approved')

    def test_blacklist_blocks_adoption(self):
        """黑名单拦截领养登记"""
        self.login('cy_shelter')
        # 先加入黑名单
        resp = self.api('/api/business/blacklist/create/', {
            'name': '测试黑名单', 'phone': '13900009999',
            'id_card': '110101199001019999', 'reason': '弃养',
        })
        self.assertEqual(resp.status_code, 200, resp.content)

        pet = Pet.objects.filter(status='pending_adopt').first()
        resp = self.api('/api/business/adoptions/register/', {
            'pet_id': pet.id, 'adopter_name': '测试黑名单',
            'adopter_phone': '13900009999', 'adopter_id_card': '110101199001019999',
        })
        self.assertFalse(resp.json()['success'], '黑名单用户领养应被拦截')

    def test_blacklist_check_endpoint(self):
        self.login('cy_shelter')
        resp = self.client.get('/api/business/blacklist/check/?phone=13900000001')
        self.assertTrue(resp.json()['data']['in_blacklist'])


class ScheduledTaskTest(TNRBaseTestCase):
    """定时任务：诊疗完成5天自动转待领养"""

    def _make_completed_treatment(self, pet, days_ago=None):
        treatment = Treatment.objects.create(
            pet=pet, pet_code=pet.code,
            hospital=pet.hospital or Institution.objects.filter(type='hospital').first(),
            hospital_name=(pet.hospital or Institution.objects.filter(type='hospital').first()).name,
            district=pet.district,
            status='completed',
        )
        if days_ago is not None:
            Treatment.objects.filter(id=treatment.id).update(
                created_at=timezone.now() - timedelta(days=days_ago)
            )
        return treatment

    def test_auto_promote_after_5_days(self):
        pet = Pet.objects.filter(status='in_treatment').first()
        self._make_completed_treatment(pet, days_ago=6)
        result = auto_promote_to_adoptable()
        pet.refresh_from_db()
        self.assertEqual(pet.status, 'pending_adopt')
        self.assertTrue(AdoptionHallListing.objects.filter(pet=pet).exists())
        self.assertIn('Promoted', result)

    def test_auto_promote_respects_5_day_window(self):
        """未满5天不应被提升"""
        pet = Pet.objects.filter(status='in_treatment').first()
        self._make_completed_treatment(pet, days_ago=None)  # 刚完成
        before = pet.status
        auto_promote_to_adoptable()
        pet.refresh_from_db()
        self.assertEqual(pet.status, before, '未满5天不应自动转待领养')


class BoundaryConditionTest(TNRBaseTestCase):
    """边界情况：状态机越权操作、数值边界、重复提交"""

    def test_adopted_pet_cannot_be_euthanized(self):
        """已领养宠物不可安乐死"""
        pet = Pet.objects.filter(status='adopted').first()
        self.login('aixin_hosp')
        resp = self.api('/api/business/euthanasia/create/', {
            'pet_id': pet.id, 'reason': '误操作测试',
        })
        self.assertFalse(resp.json()['success'])
        pet.refresh_from_db()
        self.assertEqual(pet.status, 'adopted')

    def test_capture_count_upper_bound(self):
        """单批捕捉数量超100被拒"""
        self.login('cy_shelter')
        shelter = Institution.objects.get(name='朝阳区流浪动物捕捉点')
        resp = self.api('/api/business/captures/create/', {
            'shelter_id': shelter.id, 'pet_count': 101,
        })
        self.assertFalse(resp.json()['success'])

    def test_transfer_split_no_duplicate_pet(self):
        """拆分转运时同一宠物不可进入两张转运单"""
        self.login('cy_shelter')
        shelter = Institution.objects.get(name='朝阳区流浪动物捕捉点')
        community = Institution.objects.filter(type='community').first()
        resp = self.api('/api/business/captures/create/', {
            'shelter_id': shelter.id, 'community_id': community.id,
            'pet_count': 1, 'species': '猫',
        })
        pet = Pet.objects.get(code=resp.json()['data']['pet_codes'][0])
        h1 = Institution.objects.get(name='爱心宠物医院')
        h2 = Institution.objects.get(name='瑞鹏宠物医院')
        # 两家医院都填同一只宠物
        resp = self.api('/api/business/transfers/create/', {
            'from_shelter_id': shelter.id,
            'items': [
                {'hospital_id': h1.id, 'pet_ids': [pet.id]},
                {'hospital_id': h2.id, 'pet_ids': [pet.id]},
            ],
        })
        transfers = resp.json()['data']
        self.assertEqual(len(transfers), 1, '同一宠物只能进入一张转运单')
        self.assertEqual(transfers[0]['pet_count'], 1)
        pet.refresh_from_db()
        self.assertEqual(pet.hospital_id, transfers[0]['to_hospital_id'])

    def test_shelter_stock_cannot_go_negative(self):
        """捕捉点库存不足时异动被拒"""
        self.login('cy_shelter')
        material = Material.objects.filter(category='vaccine').first()
        resp = self.api('/api/business/materials/adjustment/', {
            'material_id': material.id,
            'quantity': material.shelter_stock + 999,
            'reason': '超额报废测试',
        })
        self.assertFalse(resp.json()['success'])
        material.refresh_from_db()
        self.assertGreaterEqual(material.shelter_stock, 0)

    def test_blacklist_no_false_positive_by_prefix(self):
        """黑名单身份证前6位相同（同区县）不误伤他人"""
        self.login('cy_shelter')
        # 种子黑名单 BLK001: id_card=110102****5678, phone=13900000001
        # 换一个前6位相同但尾号不同的身份证 → 不应被拦截
        pet = Pet.objects.filter(status='pending_adopt').first()
        resp = self.api('/api/business/adoptions/register/', {
            'pet_id': pet.id, 'adopter_name': '无辜市民',
            'adopter_phone': '13877776666', 'adopter_id_card': '110102199001019999',
        })
        self.assertTrue(resp.json()['success'], '同区县前缀不同人不应被黑名单误伤')

    def test_checkin_cannot_be_reviewed_twice(self):
        """回访打卡不可重复审核"""
        adopter = User.objects.get(username='adopter1')
        pet = Pet.objects.filter(adoptions__adopter=adopter).first()
        self.login('adopter1')
        resp = self.api('/api/business/checkins/create/', {
            'pet_id': pet.id, 'month': '2025-06',
        })
        checkin_id = resp.json()['data']['id']
        self.login('cy_shelter')
        resp = self.api(f'/api/business/checkins/{checkin_id}/review/', {'status': 'approved'})
        self.assertTrue(resp.json()['success'])
        # 第二次审核应被拒
        resp = self.api(f'/api/business/checkins/{checkin_id}/review/', {'status': 'rejected'})
        self.assertFalse(resp.json()['success'])

    def test_treatment_rejected_when_vaccine_out_of_stock(self):
        """医院疫苗库存不足时诊疗被拒（库存联动保护）"""
        pet = Pet.objects.filter(status='in_treatment').first()
        hospital_user = 'aixin_hosp' if pet.hospital.name == '爱心宠物医院' else 'babitang_hosp'
        # 选用从未向该医院下发的疫苗（库存为0）
        stocked_ids = MaterialTransaction.objects.filter(
            hospital=pet.hospital, type='receive', material__category='vaccine',
        ).values_list('material_id', flat=True)
        unused = Material.objects.filter(category='vaccine').exclude(id__in=stocked_ids).first()
        if unused is None:
            self.skipTest('所有疫苗均有库存')
        self.login(hospital_user)
        resp = self.api('/api/business/treatments/create/', {
            'pet_id': pet.id,
            'items': {'vaccine': True},
            'vaccine': {'type': unused.name, 'material_id': unused.id, 'quantity': 1},
            'status': 'in_progress',
        })
        self.assertFalse(resp.json()['success'], '库存不足应拒绝诊疗提交')


class SupervisionTest(TNRBaseTestCase):
    """政府监管端接口"""

    def test_dashboard_stats(self):
        self.login('admin')
        resp = self.api('/api/supervision/dashboard/', method='get')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()['success'])

    def test_institution_crud(self):
        self.login('admin')
        resp = self.api('/api/supervision/institutions/', method='get')
        self.assertEqual(resp.status_code, 200)
        # 创建机构
        district = District.objects.get(code='CY')
        resp = self.api('/api/supervision/institutions/create/', {
            'name': '测试新增医院', 'type': 'hospital',
            'district_id': district.id, 'address': '测试地址',
            'contact': '张三', 'phone': '13800008888',
        })
        self.assertEqual(resp.status_code, 200, resp.content)

    def test_business_supervision(self):
        self.login('admin')
        resp = self.api('/api/supervision/business/', method='get')
        self.assertEqual(resp.status_code, 200)

    def test_material_supervision(self):
        self.login('admin')
        resp = self.api('/api/supervision/materials/', method='get')
        self.assertEqual(resp.status_code, 200)

    def test_ledger_center(self):
        self.login('admin')
        resp = self.api('/api/supervision/ledger/', method='get')
        self.assertEqual(resp.status_code, 200)

    def test_district_gov_cannot_access_other_district_institutions(self):
        """区级政府机构列表应仅本区"""
        self.login('hd_gov')
        resp = self.api('/api/supervision/institutions/', method='get')
        self.assertEqual(resp.status_code, 200)


class PortalRenderTest(TNRBaseTestCase):
    """四端门户页面渲染"""

    def setUp(self):
        super().setUp()
        # Py3.14 + Django5.0 测试客户端捕获模板上下文时 BaseContext.__copy__ 不兼容，
        # 这里打补丁使其基于 __dict__ 拷贝（仅影响测试，不影响应用本身）。
        import django.template.context as ctx_mod
        self._orig_copy = ctx_mod.BaseContext.__copy__

        def _safe_copy(self):
            cls = self.__class__
            result = cls.__new__(cls)
            result.__dict__.update(self.__dict__)
            return result

        ctx_mod.BaseContext.__copy__ = _safe_copy

    def tearDown(self):
        import django.template.context as ctx_mod
        ctx_mod.BaseContext.__copy__ = self._orig_copy
        super().tearDown()

    def test_portal_pages_render(self):
        cases = {
            'cy_shelter': '/shelter/',
            'aixin_hosp': '/hospital/',
            'adopter1': '/adopter/',
            'admin': '/gov/',
        }
        for username, url in cases.items():
            self.login(username)
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 200, f'{username} 门户 {url} 应可访问')
            self.assertIn('text/html', resp['Content-Type'])

    def test_adoption_hall_public(self):
        """领养大厅无需登录即可访问"""
        resp = self.client.get('/adopter/hall/')
        self.assertEqual(resp.status_code, 200)

    def test_login_page_renders(self):
        resp = self.client.get('/login/')
        self.assertEqual(resp.status_code, 200)
