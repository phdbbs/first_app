import urllib.request
import urllib.parse
import http.cookiejar
import sqlite3
import sys
import re

BASE = 'http://127.0.0.1:5001'
passed = 0
failed = 0
errors = []

class Browser:
    def __init__(self):
        self.cj = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cj))
    def login(self, role, username, password):
        data = urllib.parse.urlencode({'username': username, 'password': password, 'role': role}).encode()
        resp = self.opener.open(f'{BASE}/login', data)
        return resp.geturl()
    def logout(self):
        try:
            self.opener.open(f'{BASE}/logout')
        except:
            pass
    def get(self, path):
        resp = self.opener.open(f'{BASE}{path}')
        return resp.read().decode('utf-8', errors='ignore')
    def post(self, path, data):
        encoded = urllib.parse.urlencode(data).encode()
        try:
            resp = self.opener.open(f'{BASE}{path}', encoded)
            return resp.geturl(), resp.read().decode('utf-8', errors='ignore')
        except urllib.error.HTTPError as e:
            body = e.read().decode('utf-8', errors='ignore')
            return f'HTTP_{e.code}', body

def check(label, condition, detail=''):
    global passed, failed
    if condition:
        passed += 1
        print(f'  ✓ {label}')
    else:
        failed += 1
        msg = f'{label}'
        if detail:
            msg += f'  [{detail}]'
        errors.append(msg)
        print(f'  ✗ {msg}')

def db():
    c = sqlite3.connect('/workspace/tnr.db')
    c.row_factory = sqlite3.Row
    return c

def extract_csrf_or_get_hidden(html, name):
    return None

print('=' * 70)
print('TNR流浪动物管理系统 - 全链路业务流程测试')
print('（所有数据均从前端录入，模拟真实用户操作）')
print('=' * 70)

# ============================================================
# 阶段1：政府端 - 添加社区
# ============================================================
print('\n【阶段1】政府端：添加社区（3个小区）')
gov = Browser()
gov.login('government', 'gov', 'gov123')

communities = [
    ('阳光花园小区', '朝阳区', '朝阳区阳光路1号'),
    ('幸福里社区', '海淀区', '海淀区幸福路22号'),
    ('和谐家园', '东城区', '东城区和谐巷5号'),
]
for name, district, addr in communities:
    url, body = gov.post('/government/institutions', {
        'action': 'add_community', 'c_name': name, 'c_district': district, 'c_address': addr
    })
    check(f'添加社区: {name}', '/government/institutions' in url)

conn = db()
comms = conn.execute("SELECT * FROM communities ORDER BY id").fetchall()
check(f'社区总数=3', len(comms) == 3, f'实际{len(comms)}')
community_ids = [c['id'] for c in comms]
conn.close()

# ============================================================
# 阶段2：捕捉站 - 物料采购
# ============================================================
print('\n【阶段2】捕捉站端：物料采购入库')
shelter = Browser()
shelter.login('shelter', 'admin', 'admin123')

purchases = [
    ('vaccine', 200, 'V20250601', '瑞生物制药'),
    ('chip', 500, 'C20250601', '智芯科技'),
    ('dewormer', 300, 'D20250601', '宠康药业'),
    ('vaccine', 100, 'V20250615', '瑞生物制药'),
]
for mtype, qty, batch, supplier in purchases:
    url, body = shelter.post('/shelter/material', {
        'action': 'purchase', 'material_type': mtype, 'quantity': str(qty),
        'batch_no': batch, 'supplier': supplier
    })
    check(f'采购 {mtype} x{qty}', '/shelter/material' in url)

conn = db()
stock = {r['type']: r['q'] for r in conn.execute("SELECT type, SUM(quantity) as q FROM materials WHERE owner_id=1 GROUP BY type")}
check('疫苗库存=300', stock.get('vaccine', 0) == 300, f'实际{stock.get("vaccine",0)}')
check('芯片库存=500', stock.get('chip', 0) == 500, f'实际{stock.get("chip",0)}')
check('驱虫药库存=300', stock.get('dewormer', 0) == 300, f'实际{stock.get("dewormer",0)}')
ledger_count = conn.execute("SELECT COUNT(*) as c FROM material_ledger WHERE action='purchase'").fetchone()['c']
check('采购台账记录=4', ledger_count == 4, f'实际{ledger_count}')
conn.close()

# ============================================================
# 阶段3：捕捉站 - 新增捕捉（6只动物）
# ============================================================
print('\n【阶段3】捕捉站端：新增捕捉登记')
captures = [
    # (community_id, property_name, contact_person, contact_phone, address, species, pet_count)
    (community_ids[0], '阳光物业', '张经理', '13800000010', '朝阳区阳光路1号3号楼', 'cat', 1),
    (community_ids[0], '阳光物业', '张经理', '13800000010', '朝阳区阳光路1号花园', 'cat', 1),
    (community_ids[1], '幸福物业', '王经理', '13800000011', '海淀区幸福路22号门口', 'dog', 1),
    (community_ids[1], '幸福物业', '王经理', '13800000011', '海淀区幸福路22号车棚', 'cat', 1),
    (community_ids[2], '和谐物业', '李经理', '13800000012', '东城区和谐巷5号花坛', 'cat', 1),
    (community_ids[2], '和谐物业', '李经理', '13800000012', '东城区和谐巷5号地下车库', 'dog', 1),
]
pet_ids = []
for cid, prop, contact, phone, addr, species, count in captures:
    url, body = shelter.post('/shelter/add', {
        'community_id': str(cid), 'property_name': prop,
        'contact_person': contact, 'contact_phone': phone,
        'address': addr, 'species': species, 'pet_count': str(count)
    })
    check(f'捕捉登记: {species} at {prop}', '/shelter/transfer' in url)

conn = db()
all_intake = conn.execute("SELECT id, pet_code, species, status, community_id FROM pets WHERE status='intake' ORDER BY id").fetchall()
check(f'在站动物总数=6', len(all_intake) == 6, f'实际{len(all_intake)}')
pet_ids = [p['id'] for p in all_intake]
pet_codes = {p['id']: p['pet_code'] for p in all_intake}
for pid in pet_ids:
    print(f'    Pet {pid}: {pet_codes[pid]}')
conn.close()

# ============================================================
# 阶段4：捕捉站 - 下发物料到医院
# ============================================================
print('\n【阶段4】捕捉站端：下发物料到各医院')
distributions = [
    # (hospital_id, material_type, quantity)
    (2, 'chip', 30), (2, 'vaccine', 30), (2, 'dewormer', 30),
    (3, 'chip', 20), (3, 'vaccine', 20), (3, 'dewormer', 20),
    (4, 'chip', 20), (4, 'vaccine', 20), (4, 'dewormer', 20),
]
for hid, mtype, qty in distributions:
    url, body = shelter.post('/shelter/material', {
        'action': 'distribute', 'hospital_id': str(hid),
        'material_type': mtype, 'quantity': str(qty)
    })
    check(f'下发 {mtype}x{qty} → 医院{hid}', '/shelter/material' in url)

conn = db()
pending_dists = conn.execute("SELECT COUNT(*) as c FROM material_distributions WHERE status='pending'").fetchone()['c']
check(f'待确认物料单=9', pending_dists == 9, f'实际{pending_dists}')
conn.close()

# ============================================================
# 阶段5：各医院 - 签收物料
# ============================================================
print('\n【阶段5】医院端：签收物料')
hospitals = [
    ('aixin', 'aixin123', 2, '爱心'),
    ('renai', 'renai123', 3, '仁爱'),
    ('boai', 'boai123', 4, '博爱'),
]
hospital_browsers = {}
for user, pwd, hid, name in hospitals:
    h = Browser()
    h.login('hospital', user, pwd)
    hospital_browsers[hid] = (h, name)
    conn = db()
    dists = conn.execute("SELECT id, material_type, quantity FROM material_distributions WHERE to_hospital_id=? AND status='pending'", (hid,)).fetchall()
    for d in dists:
        url, body = h.post('/hospital/material', {'action': 'receive_mat', 'dist_id': str(d['id'])})
        check(f'{name}医院签收 {d["material_type"]}x{d["quantity"]}', '/hospital/material' in url)
    conn.close()

# Verify stock at each hospital
for hid, (h, name) in hospital_browsers.items():
    conn = db()
    inv = {r['type']: r['q'] for r in conn.execute("SELECT type, SUM(quantity) as q FROM materials WHERE owner_id=? GROUP BY type", (hid,))}
    check(f'{name}医院库存完整', inv.get('chip',0) > 0 and inv.get('vaccine',0) > 0 and inv.get('dewormer',0) > 0,
          f'chip={inv.get("chip",0)} vaccine={inv.get("vaccine",0)} dewormer={inv.get("dewormer",0)}')
    conn.close()

conn = db()
shelter_after = {r['type']: r['q'] for r in conn.execute("SELECT type, SUM(quantity) as q FROM materials WHERE owner_id=1 GROUP BY type")}
check('捕捉站芯片剩余=430', shelter_after.get('chip',0) == 430, f'实际{shelter_after.get("chip",0)}')
check('捕捉站疫苗剩余=230', shelter_after.get('vaccine',0) == 230, f'实际{shelter_after.get("vaccine",0)}')
check('捕捉站驱虫药剩余=230', shelter_after.get('dewormer',0) == 230, f'实际{shelter_after.get("dewormer",0)}')
conn.close()

# ============================================================
# 阶段6：捕捉站 - 转运到医院（4只转运，2只其他处理）
# ============================================================
print('\n【阶段6】捕捉站端：创建转运单')
# 转运4只到不同医院: pet_ids[0]->爱心(2), pet_ids[1]->爱心(2), pet_ids[2]->仁爱(3), pet_ids[3]->仁爱(3), pet_ids[4]->博爱(4)
transfer_plan = [
    (pet_ids[0], 2, '成年橘猫，请尽快安排绝育'),
    (pet_ids[1], 2, '白色小猫，约1岁，注意检查传染病'),
    (pet_ids[2], 3, '黄色田园犬，性格温顺'),
    (pet_ids[3], 3, '狸花猫，比较警惕'),
    (pet_ids[4], 4, '三花母猫，疑似怀孕'),
]
transfer_ids = {}
for pid, hid, note in transfer_plan:
    url, body = shelter.post('/shelter/transfer', {
        'pet_ids': str(pid), 'hospital_id': str(hid), 'notes': note
    })
    check(f'转运 {pet_codes[pid]} → 医院{hid}', '/shelter/transfer' in url)
    conn = db()
    tr = conn.execute("SELECT id FROM transfers WHERE pet_id=? AND status='pending' ORDER BY id DESC LIMIT 1", (pid,)).fetchone()
    if tr:
        transfer_ids[pid] = tr['id']
    conn.close()

conn = db()
pending_trans = conn.execute("SELECT COUNT(*) as c FROM transfers WHERE status='pending'").fetchone()['c']
check(f'待签收转运单=5', pending_trans == 5, f'实际{pending_trans}')
for pid in transfer_plan:
    p = conn.execute("SELECT status FROM pets WHERE id=?", (pid[0],)).fetchone()
    check(f'{pet_codes[pid[0]]}状态=transit', p['status'] == 'transit', f'实际{p["status"]}')
conn.close()

# ============================================================
# 阶段7：医院 - 签收转运
# ============================================================
print('\n【阶段7】医院端：签收转运动物')
for pid, hid, note in transfer_plan:
    h, name = hospital_browsers[hid]
    tid = transfer_ids.get(pid)
    if tid:
        url, body = h.post('/hospital/receive', {'action': 'receive', 'transfer_id': str(tid)})
        check(f'{name}医院签收 {pet_codes[pid]}', '/hospital/receive' in url)

conn = db()
for pid, hid, _ in transfer_plan:
    p = conn.execute("SELECT status, current_hospital_id FROM pets WHERE id=?", (pid,)).fetchone()
    check(f'{pet_codes[pid]}待诊疗 at 医院{hid}', p['status'] == 'pending_treatment' and p['current_hospital_id'] == hid,
          f'status={p["status"]}, hospital={p["current_hospital_id"]}')
    t = conn.execute("SELECT id FROM treatments WHERE pet_id=? AND hospital_id=?", (pid, hid)).fetchone()
    check(f'{pet_codes[pid]}诊疗记录已创建', t is not None)
conn.close()

# ============================================================
# 阶段8：医院 - 诊疗（每只动物做完全部四项）
# ============================================================
print('\n【阶段8】医院端：完成诊疗（绝育+疫苗+驱虫+芯片）')
treatment_data = [
    # (pet_id, hospital_id, gender, neuter_record, chip_no, notes)
    (pet_ids[0], 2, '公', '公猫绝育手术顺利，恢复良好', f'CHIP-AIX-{pet_ids[0]:03d}', '成年橘猫，体重4.2kg，体温正常'),
    (pet_ids[1], 2, '母', '母猫绝育，年纪小恢复快', f'CHIP-AIX-{pet_ids[1]:03d}', '白色小猫，体重2.8kg，健康'),
    (pet_ids[2], 3, '公', '公犬去势手术成功', f'CHIP-REN-{pet_ids[2]:03d}', '田园犬，体重8.5kg，温顺'),
    (pet_ids[3], 3, '公', '公猫绝育完成', f'CHIP-REN-{pet_ids[3]:03d}', '狸花猫，体重3.5kg，有点胆小'),
    (pet_ids[4], 4, '母', '母猫绝育+引产，恢复稳定', f'CHIP-BOA-{pet_ids[4]:03d}', '三花，体重3.1kg，引产+绝育'),
]
for pid, hid, gender, neuter_rec, chip_no, notes in treatment_data:
    h, name = hospital_browsers[hid]
    url, body = h.post('/hospital/treatment', {
        'pet_id': str(pid), 'neuter_done': '1', 'neuter_record': neuter_rec,
        'vaccine_done': '1', 'dewormer_done': '1', 'chip_done': '1',
        'chip_no': chip_no, 'notes': notes, 'completed': '1'
    })
    check(f'{name}医院完成诊疗: {pet_codes[pid]}', '/hospital/treatment' in url)

# Verify treatment results
conn = db()
for pid, hid, _, _, chip_no, _ in treatment_data:
    p = conn.execute("SELECT status, neutered, vaccinated, dewormed, chipped, chip_no FROM pets WHERE id=?", (pid,)).fetchone()
    check(f'{pet_codes[pid]}诊疗完成(状态=treated)', p['status'] == 'treated')
    check(f'{pet_codes[pid]}四项全完成', p['neutered']==1 and p['vaccinated']==1 and p['dewormed']==1 and p['chipped']==1)
    check(f'{pet_codes[pid]}芯片号正确', p['chip_no'] == chip_no)
    t = conn.execute("SELECT completed FROM treatments WHERE pet_id=? AND hospital_id=?", (pid, hid)).fetchone()
    check(f'{pet_codes[pid]}治疗记录completed=1', t['completed'] == 1)

# Verify material consumption after adoption-path treatments
for hid, (h, name) in hospital_browsers.items():
    inv = {r['type']: r['q'] for r in conn.execute("SELECT type, SUM(quantity) as q FROM materials WHERE owner_id=? GROUP BY type", (hid,))}
    pets_at_h = sum(1 for pid, h2, *_ in treatment_data if h2 == hid)
    expected_chip = 30 - pets_at_h if hid == 2 else (20 - pets_at_h if hid in [3,4] else 0)
    check(f'{name}医院芯片消耗正确(剩余{expected_chip})', inv.get('chip',0) == expected_chip,
          f'实际{inv.get("chip",0)}, 该院已诊疗{pets_at_h}只')
conn.close()

# ============================================================
# 阶段9：医院 - 上架领养大厅
# ============================================================
print('\n【阶段9】医院端：上架领养大厅')
adoption_listings = [
    (pet_ids[0], 2, '公', '2岁', '橘色', '大橘为重，性格亲人，已绝育驱虫打疫苗打芯片，适合有爱心的家庭'),
    (pet_ids[1], 2, '母', '1岁', '白色', '雪白小美人，温柔亲人，非常适合陪伴老人'),
    (pet_ids[2], 3, '公', '3岁', '黄色', '忠诚大黄，性格温顺听话，会握手等指令'),
    (pet_ids[3], 3, '公', '2岁', '狸花', '健康梨花猫，抓鼠小能手，需要有耐心的主人'),
    (pet_ids[4], 4, '母', '2岁', '三花', '三花妹妹，引产绝育后恢复良好，温柔可爱'),
]
for pid, hid, gender, age, color, desc in adoption_listings:
    h, name = hospital_browsers[hid]
    url, body = h.post('/hospital/adoption', {
        'pet_id': str(pid), 'action': 'update',
        'gender': gender, 'age': age, 'description': desc
    })
    check(f'{name}医院上架: {pet_codes[pid]}', '/hospital/adoption' in url)

conn = db()
for pid, hid, _, _, _, _ in adoption_listings:
    p = conn.execute("SELECT status, adoption_desc FROM pets WHERE id=?", (pid,)).fetchone()
    check(f'{pet_codes[pid]}已上架(pending_adoption)', p['status'] == 'pending_adoption')
    check(f'{pet_codes[pid]}有领养简介', p['adoption_desc'] is not None and len(p['adoption_desc']) > 0)
pending_count = conn.execute("SELECT COUNT(*) as c FROM pets WHERE status='pending_adoption'").fetchone()['c']
check(f'待领养宠物总数=5', pending_count == 5, f'实际{pending_count}')
conn.close()

# ============================================================
# 阶段10：领养人注册（3位领养人）
# ============================================================
print('\n【阶段10】领养人注册账号（3位）')
adopters_data = [
    ('zhangxiaojie', '123456', '张小姐', '13900000001'),
    ('lixiansheng', '123456', '李先生', '13900000002'),
    ('wangnvs', '123456', '王女士', '13900000003'),
]
adopter_browsers = {}
adopter_ids = {}
import random
# Register each adopter
for username, pwd, name, phone in adopters_data:
    reg_browser = Browser()
    url, body = reg_browser.post('/register', {
        'username': username, 'password': pwd, 'name': name, 'phone': phone
    })
    check(f'注册领养人: {name}({username})', '/login' in url)

# Login each adopter
for username, pwd, name, phone in adopters_data:
    a = Browser()
    url = a.login('adopter', username, pwd)
    check(f'领养人{name}登录', '/adopter' in url)
    adopter_browsers[username] = (a, name)
    conn = db()
    u = conn.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone()
    adopter_ids[username] = u['id']
    conn.close()

# ============================================================
# 阶段11：领养人浏览大厅并提交申请
# ============================================================
print('\n【阶段11】领养人：浏览领养大厅并提交申请')
# 张小姐申请橘猫和白猫
# 李先生申请黄狗
# 王女士申请梨花和三花
applications = [
    # (adopter_username, pet_id, reason, experience, housing)
    ('zhangxiaojie', pet_ids[0], '一直想养一只橘猫，家里已经封窗，准备了猫爬架猫砂盆', '之前帮朋友养过半年猫，有基本养猫经验', '自有住房，两室一厅，封窗封阳台，家人同意'),
    ('zhangxiaojie', pet_ids[1], '白猫太美了，想给它一个温暖的家', '新手但是做了很多功课，准备好所有用品', '自有住房，封窗，独居'),
    ('lixiansheng', pet_ids[2], '喜欢狗狗，家里有院子可以遛弯', '小时候养过狗，有经验', '一楼带院子，自有住房'),
    ('wangnvs', pet_ids[3], '想给家里的老人找个伴，梨花猫看起来有灵气', '家里老人之前养过猫，经验丰富', '父母家有院子，老人常住'),
    ('wangnvs', pet_ids[4], '三花很可爱，心疼它引产，想好好照顾它', '有养猫经验，家里已有一只猫可以做伴', '自有住房120平，封窗'),
]
app_ids = {}
for username, pid, reason, exp, housing in applications:
    a, name = adopter_browsers[username]
    # First verify pet is in adoption hall
    body = a.get('/adopter')
    check(f'{name}领养大厅可看到{pet_codes[pid]}', pet_codes[pid] in body)
    # Apply
    url, body = a.post(f'/adopter/apply/{pid}', {
        'reason': reason, 'experience': exp, 'housing': housing
    })
    check(f'{name}申请{pet_codes[pid]}', '/adopter' in url)
    conn = db()
    app = conn.execute("SELECT id FROM adoption_applications WHERE pet_id=? AND adopter_id=? ORDER BY id DESC LIMIT 1",
                       (pid, adopter_ids[username])).fetchone()
    if app:
        app_ids[(username, pid)] = app['id']
    conn.close()

conn = db()
total_apps = conn.execute("SELECT COUNT(*) as c FROM adoption_applications WHERE status='pending'").fetchone()['c']
check(f'待审核申请总数=5', total_apps == 5, f'实际{total_apps}')
conn.close()

# ============================================================
# 阶段12：捕捉站审核领养申请（通过3只，驳回2只）
# ============================================================
print('\n【阶段12】捕捉站：审核领养申请')
# 通过：zhangxiaojie->橘猫, lixiansheng->黄狗, wangnvs->三花
# 驳回：zhangxiaojie->白猫(一人限领一只), wangnvs->梨花(已有猫不适合多只)
approvals = [
    ('zhangxiaojie', pet_ids[0], 'approve', ''),
    ('lixiansheng', pet_ids[2], 'approve', ''),
    ('wangnvs', pet_ids[4], 'approve', ''),
]
rejections = [
    ('zhangxiaojie', pet_ids[1], '每位领养人限领养一只动物，请谅解'),
    ('wangnvs', pet_ids[3], '您已有一只猫，不建议多只混养'),
]
for username, pid, action, note in approvals:
    aid = app_ids.get((username, pid))
    if aid:
        url, body = shelter.post('/shelter/adoption', {'action': 'approve_application', 'application_id': str(aid)})
        check(f'通过 {pet_codes[pid]} → {username}', '/shelter/adoption' in url)

for username, pid, note in rejections:
    aid = app_ids.get((username, pid))
    if aid:
        url, body = shelter.post('/shelter/adoption', {'action': 'reject_application', 'application_id': str(aid), 'reject_note': note})
        check(f'驳回 {pet_codes[pid]} → {username}', '/shelter/adoption' in url)

conn = db()
approved = conn.execute("SELECT COUNT(*) as c FROM adoption_applications WHERE status='approved'").fetchone()['c']
rejected = conn.execute("SELECT COUNT(*) as c FROM adoption_applications WHERE status='rejected'").fetchone()['c']
pending_after = conn.execute("SELECT COUNT(*) as c FROM adoption_applications WHERE status='pending'").fetchone()['c']
check(f'审核通过=3', approved == 3, f'实际{approved}')
check(f'审核驳回=2', rejected == 2, f'实际{rejected}')
check(f'剩余待审核=0', pending_after == 0, f'实际{pending_after}')

for username, pid, _, _ in approvals:
    p = conn.execute("SELECT status, adopter_id FROM pets WHERE id=?", (pid,)).fetchone()
    check(f'{pet_codes[pid]}待领取', p['status'] == 'pending_pickup')
    check(f'{pet_codes[pid]}分配给{username}', p['adopter_id'] == adopter_ids[username])

for username, pid, _ in rejections:
    p = conn.execute("SELECT status FROM pets WHERE id=?", (pid,)).fetchone()
    check(f'{pet_codes[pid]}仍待领养(未被领走)', p['status'] == 'pending_adoption')
conn.close()

# ============================================================
# 阶段13：医院确认领养人领出
# ============================================================
print('\n【阶段13】医院端：确认领养人领出宠物')
for username, pid, _, _ in approvals:
    conn = db()
    p = conn.execute("SELECT current_hospital_id FROM pets WHERE id=?", (pid,)).fetchone()
    hid = p['current_hospital_id']
    conn.close()
    h, name = hospital_browsers[hid]
    url, body = h.post('/hospital/adoption', {'pet_id': str(pid), 'action': 'confirm_adopted'})
    check(f'{name}医院确认领出: {pet_codes[pid]}', '/hospital/adoption' in url)

conn = db()
for username, pid, _, _ in approvals:
    p = conn.execute("SELECT status FROM pets WHERE id=?", (pid,)).fetchone()
    check(f'{pet_codes[pid]}已领养(adopted)', p['status'] == 'adopted')
adopted_count = conn.execute("SELECT COUNT(*) as c FROM pets WHERE status='adopted'").fetchone()['c']
check(f'已领养宠物=3', adopted_count == 3, f'实际{adopted_count}')
conn.close()

# ============================================================
# 阶段14：一只宠物主人领回
# ============================================================
print('\n【阶段14】捕捉站：主人领回(pet_ids[5]还在站)')
pid_return = pet_ids[5]
conn = db()
p = conn.execute("SELECT status FROM pets WHERE id=?", (pid_return,)).fetchone()
check(f'{pet_codes[pid_return]}在站可领回', p['status'] == 'intake')
conn.close()

url, body = shelter.post('/shelter/owner-return', {
    'pet_id': str(pid_return), 'owner_name': '陈先生', 'owner_phone': '13700000001', 'notes': '找到原主人，确认领回'
})
check(f'主人领回{pet_codes[pid_return]}', '/shelter' in url)

conn = db()
p = conn.execute("SELECT status FROM pets WHERE id=?", (pid_return,)).fetchone()
check(f'{pet_codes[pid_return]}状态=returned', p['status'] == 'returned')
conn.close()

# ============================================================
# 阶段15：领养人回访打卡
# ============================================================
print('\n【阶段15】领养人：回访打卡')
checkin_records = [
    ('zhangxiaojie', pet_ids[0], '大橘适应得很好，能吃能睡，很亲人，喜欢蹭腿'),
    ('lixiansheng', pet_ids[2], '大黄很乖，每天遛两次，学会了定点大小便'),
    ('wangnvs', pet_ids[4], '三花已经和家里的猫熟悉了，两只猫一起玩得很开心'),
]
checkin_ids = {}
for username, pid, content in checkin_records:
    a, name = adopter_browsers[username]
    url, body = a.post('/adopter/checkin', {'pet_id': str(pid), 'content': content})
    check(f'{name}打卡: {pet_codes[pid]}', '/adopter/checkin' in url)
    conn = db()
    ci = conn.execute("SELECT id FROM checkins WHERE pet_id=? AND adopter_id=? ORDER BY id DESC LIMIT 1",
                      (pid, adopter_ids[username])).fetchone()
    if ci:
        checkin_ids[(username, pid)] = ci['id']
    conn.close()

conn = db()
pending_ci = conn.execute("SELECT COUNT(*) as c FROM checkins WHERE status='pending'").fetchone()['c']
check(f'待审核打卡=3', pending_ci == 3, f'实际{pending_ci}')
conn.close()

# ============================================================
# 阶段16：捕捉站审核打卡（通过2，驳回1让重新提交）
# ============================================================
print('\n【阶段16】捕捉站：审核回访打卡')
# 通过前两个，驳回第三个让重写
for i, (username, pid, _) in enumerate(checkin_records):
    cid = checkin_ids.get((username, pid))
    if not cid:
        continue
    if i < 2:
        url, body = shelter.post('/shelter/adoption', {
            'action': 'review_checkin', 'checkin_id': str(cid), 'result': 'approved', 'note': '回访情况良好'
        })
        check(f'通过{pet_codes[pid]}打卡', '/shelter/adoption' in url)
    else:
        url, body = shelter.post('/shelter/adoption', {
            'action': 'review_checkin', 'checkin_id': str(cid), 'result': 'rejected', 'note': '请提供更多宠物健康和饮食情况'
        })
        check(f'驳回{pet_codes[pid]}打卡(需补充)', '/shelter/adoption' in url)

conn = db()
approved_ci = conn.execute("SELECT COUNT(*) as c FROM checkins WHERE status='approved'").fetchone()['c']
rejected_ci = conn.execute("SELECT COUNT(*) as c FROM checkins WHERE status='rejected'").fetchone()['c']
check(f'打卡通过=2', approved_ci == 2, f'实际{approved_ci}')
check(f'打卡驳回=1', rejected_ci == 1, f'实际{rejected_ci}')
conn.close()

# 王女士重新打卡
username, pid = 'wangnvs', pet_ids[4]
a, name = adopter_browsers[username]
import datetime
next_month = (datetime.date(2026, 7, 1)).strftime('%Y-%m')
url, body = a.post('/adopter/checkin', {
    'pet_id': str(pid), 'month': next_month,
    'content': '三花身体很健康，食欲好，便便正常，每天和原住民一起玩耍，很活泼'
})
check(f'{name}重新打卡(下月)', '/adopter/checkin' in url)
conn = db()
new_ci = conn.execute("SELECT id FROM checkins WHERE pet_id=? AND adopter_id=? AND status='pending' ORDER BY id DESC LIMIT 1",
                     (pid, adopter_ids[username])).fetchone()
if new_ci:
    url, body = shelter.post('/shelter/adoption', {
        'action': 'review_checkin', 'checkin_id': str(new_ci['id']), 'result': 'approved', 'note': '补充内容合格，通过'
    })
    check(f'重新打卡审核通过', '/shelter/adoption' in url)
conn.close()

# ============================================================
# 阶段16.5：放归流程（捕捉→转运→诊疗→回收→放归，3只）
# ============================================================
print('\n【阶段16.5】捕捉站端：新增3只放归动物并走通放归流程')
release_captures = [
    (community_ids[0], '阳光物业', '张经理', '13800000010', '朝阳区阳光路1号车库', 'cat'),
    (community_ids[1], '幸福物业', '王经理', '13800000011', '海淀区幸福路22号花坛', 'cat'),
    (community_ids[2], '和谐物业', '李经理', '13800000012', '东城区和谐巷5号后院', 'dog'),
]
release_pet_ids = []
for cid, prop, contact, phone, addr, species in release_captures:
    url, body = shelter.post('/shelter/add', {
        'community_id': str(cid), 'property_name': prop,
        'contact_person': contact, 'contact_phone': phone,
        'address': addr, 'species': species, 'pet_count': '1'
    })
    check(f'放归动物捕捉登记: {species} at {prop}', '/shelter/transfer' in url)

conn = db()
new_intake = conn.execute("SELECT id, pet_code FROM pets WHERE status='intake' ORDER BY id").fetchall()
release_pet_ids = [p['id'] for p in new_intake]
for p in new_intake:
    pet_codes[p['id']] = p['pet_code']
    pet_ids.append(p['id'])
conn.close()

# 转运到爱心、仁爱、博爱医院各1只
release_transfer_plan = [
    (release_pet_ids[0], 2),
    (release_pet_ids[1], 3),
    (release_pet_ids[2], 4),
]
release_transfer_ids = {}
for pid, hid in release_transfer_plan:
    url, body = shelter.post('/shelter/transfer', {
        'pet_ids': str(pid), 'hospital_id': str(hid), 'notes': '成年流浪猫，适合放归'
    })
    check(f'转运放归动物 {pet_codes[pid]} → 医院{hid}', '/shelter/transfer' in url)
    conn = db()
    tr = conn.execute("SELECT id FROM transfers WHERE pet_id=? AND status='pending' ORDER BY id DESC LIMIT 1", (pid,)).fetchone()
    if tr:
        release_transfer_ids[pid] = tr['id']
    conn.close()

# 医院签收
for pid, hid in release_transfer_plan:
    h, name = hospital_browsers[hid]
    tid = release_transfer_ids.get(pid)
    if tid:
        url, body = h.post('/hospital/receive', {'action': 'receive', 'transfer_id': str(tid)})
        check(f'{name}医院签收放归动物 {pet_codes[pid]}', '/hospital/receive' in url)

# 医院完成诊疗
release_treatment = [
    (release_pet_ids[0], 2, '公', '公猫绝育', f'CHIP-AIXR-{release_pet_ids[0]:03d}', '成年公猫，野性大，不适合家养，建议放归'),
    (release_pet_ids[1], 3, '母', '母猫绝育', f'CHIP-RENR-{release_pet_ids[1]:03d}', '母猫，极度警惕，建议放归原社区'),
    (release_pet_ids[2], 4, '公', '公犬去势', f'CHIP-BOAR-{release_pet_ids[2]:03d}', '公犬，警惕性高，适合放归'),
]
for pid, hid, gender, neuter_rec, chip_no, notes in release_treatment:
    h, name = hospital_browsers[hid]
    url, body = h.post('/hospital/treatment', {
        'pet_id': str(pid), 'neuter_done': '1', 'neuter_record': neuter_rec,
        'vaccine_done': '1', 'dewormer_done': '1', 'chip_done': '1',
        'chip_no': chip_no, 'notes': notes, 'completed': '1'
    })
    check(f'{name}医院完成诊疗: {pet_codes[pid]}', '/hospital/treatment' in url)

# 捕捉站回收（从已治愈动物中选择回收，不走领养）
for pid, hid in release_transfer_plan:
    url, body = shelter.post('/shelter/release', {
        'pet_ids': str(pid), 'action_type': 'recover'
    })
    check(f'捕捉站回收 {pet_codes[pid]}', '/shelter/release' in url)
    conn = db()
    p = conn.execute("SELECT status FROM pets WHERE id=?", (pid,)).fetchone()
    check(f'{pet_codes[pid]}状态=pending_release', p['status'] == 'pending_release', f'实际{p["status"]}')
    conn.close()

# 捕捉站确认放归
for pid, hid in release_transfer_plan:
    url, body = shelter.post('/shelter/release', {
        'pet_ids': str(pid), 'action_type': 'release'
    })
    check(f'捕捉站放归 {pet_codes[pid]}', '/shelter/release' in url)
    conn = db()
    p = conn.execute("SELECT status FROM pets WHERE id=?", (pid,)).fetchone()
    check(f'{pet_codes[pid]}状态=released', p['status'] == 'released', f'实际{p["status"]}')
    conn.close()

# ============================================================
# 阶段17：黑名单管理
# ============================================================
print('\n【阶段17】捕捉站：黑名单管理')
# 把驳回的白猫申请人拉入黑名单测试
bad_adopter = 'zhangxiaojie'
bid = adopter_ids[bad_adopter]
url, body = shelter.post('/shelter/adoption', {'action': 'blacklist', 'user_id': str(bid), 'reason': '测试黑名单'})
check(f'将{bad_adopter}加入黑名单', '/shelter/adoption' in url)
conn = db()
u = conn.execute("SELECT is_blacklisted FROM users WHERE id=?", (bid,)).fetchone()
check(f'黑名单状态=1', u['is_blacklisted'] == 1)
conn.close()

# 测试黑名单用户无法登录，更无法申请
a, name = adopter_browsers[bad_adopter]
# Logout then try to re-login (should be rejected at login page)
a.logout()
login_resp = a.post('/login', {'username': bad_adopter, 'password': '123456', 'role': 'adopter'})
# 黑名单用户登录被拒，停留在login页面
conn = db()
before_apps = conn.execute("SELECT COUNT(*) as c FROM adoption_applications WHERE adopter_id=?", (bid,)).fetchone()['c']
conn.close()
# Since login failed, trying to POST to apply should redirect to login (no session)
url, body = a.post(f'/adopter/apply/{pet_ids[3]}', {
    'reason': '还想申请梨花', 'experience': '有经验', 'housing': '有房'
})
conn = db()
after_apps = conn.execute("SELECT COUNT(*) as c FROM adoption_applications WHERE adopter_id=?", (bid,)).fetchone()['c']
# Application was NOT created (login blocked, so no valid session to apply)
check('黑名单用户无法提交申请', after_apps == before_apps, f'申请数: before={before_apps}, after={after_apps}')
check('黑名单用户登录被拒(停留在登录页)', '/login' in login_resp[0] or '黑名单' in login_resp[1], f'url={login_resp[0]}')
conn.close()

# 移出黑名单
url, body = shelter.post('/shelter/adoption', {'action': 'unblacklist', 'user_id': str(bid)})
check(f'移出黑名单', '/shelter/adoption' in url)
conn = db()
u = conn.execute("SELECT is_blacklisted FROM users WHERE id=?", (bid,)).fetchone()
check(f'黑名单状态=0(已移出)', u['is_blacklisted'] == 0)
conn.close()

# ============================================================
# 阶段19：验证报表统计准确性
# ============================================================
print('\n' + '=' * 70)
print('【阶段19】验证报表与数据统计准确性')
print('=' * 70)

conn = db()

# 1. 总体统计
total_pets = conn.execute("SELECT COUNT(*) as c FROM pets").fetchone()['c']
check(f'宠物档案总数=9(5领养流+1领回+3放归)', total_pets == 9, f'实际{total_pets}')

status_counts = {}
for row in conn.execute("SELECT status, COUNT(*) as c FROM pets GROUP BY status"):
    status_counts[row['status']] = row['c']
print(f'    宠物状态分布: {status_counts}')
check(f'已领养=3', status_counts.get('adopted',0) == 3)
check(f'待领养=2(白猫+梨花)', status_counts.get('pending_adoption',0) == 2, f'实际{status_counts.get("pending_adoption",0)}')
check(f'主人领回=1', status_counts.get('returned',0) == 1)
check(f'已放归=3', status_counts.get('released',0) == 3, f'实际{status_counts.get("released",0)}')

# 2. 领养申请统计
app_stats = {}
for row in conn.execute("SELECT status, COUNT(*) as c FROM adoption_applications GROUP BY status"):
    app_stats[row['status']] = row['c']
print(f'    申请状态分布: {app_stats}')
check(f'申请通过=3', app_stats.get('approved',0) == 3)
check(f'申请驳回=2', app_stats.get('rejected',0) == 2)

# 3. 物料台账统计
ledger_stats = {}
for row in conn.execute("SELECT action, COUNT(*) as c FROM material_ledger GROUP BY action"):
    ledger_stats[row['action']] = row['c']
print(f'    台账操作分布: {ledger_stats}')
check(f'采购入库记录=4', ledger_stats.get('purchase',0) == 4)
check(f'下发接收记录=9', ledger_stats.get('distribute_receive',0) == 9)
# consumption = 8 treated pets x 3 materials = 24
check(f'诊疗消耗记录=24', ledger_stats.get('consume',0) == 24, f'实际{ledger_stats.get("consume",0)}')

# 4. 回访打卡统计
checkin_stats = {}
for row in conn.execute("SELECT status, COUNT(*) as c FROM checkins GROUP BY status"):
    checkin_stats[row['status']] = row['c']
print(f'    打卡状态分布: {checkin_stats}')
check(f'打卡通过=3', checkin_stats.get('approved',0) == 3, f'实际{checkin_stats.get("approved",0)}')
check(f'打卡驳回=1', checkin_stats.get('rejected',0) == 1)

# 5. 用户统计
total_users = conn.execute("SELECT COUNT(*) as c FROM users").fetchone()['c']
adopter_user_count = conn.execute("SELECT COUNT(*) as c FROM users WHERE role='adopter'").fetchone()['c']
check(f'用户总数=8(5基础+3领养人)', total_users == 8, f'实际{total_users}')
check(f'领养人账号=3', adopter_user_count == 3, f'实际{adopter_user_count}')

# 6. 社区统计
comm_count = conn.execute("SELECT COUNT(*) as c FROM communities").fetchone()['c']
check(f'社区总数=3', comm_count == 3, f'实际{comm_count}')

# 7. 消息通知统计
msg_count = conn.execute("SELECT COUNT(*) as c FROM messages").fetchone()['c']
print(f'    消息通知总数: {msg_count}')
check('系统消息已发送', msg_count > 15, f'实际{msg_count}')

# 8. 操作日志统计
log_count = conn.execute("SELECT COUNT(*) as c FROM operation_logs").fetchone()['c']
print(f'    操作日志总数: {log_count}')
check('操作日志有记录', log_count > 30, f'实际{log_count}')

# 9. 转运统计
transfer_stats = {}
for row in conn.execute("SELECT status, COUNT(*) as c FROM transfers GROUP BY status"):
    transfer_stats[row['status']] = row['c']
print(f'    转运状态分布: {transfer_stats}')
check(f'已接收转运=8(5领养流+3放归流)', transfer_stats.get('received',0) == 8, f'实际{transfer_stats.get("received",0)}')

conn.close()

# ============================================================
# 阶段20：验证前端页面渲染正常
# ============================================================
print('\n【阶段20】验证各角色页面渲染')
pages_to_test = [
    (shelter, [
        ('/shelter', '捕捉站首页'),
        ('/shelter/report', '一宠一档报表'),
        ('/shelter/adoption', '领养管理'),
        ('/shelter/material', '物料管理'),
        ('/shelter/settings', '操作日志'),
    ]),
    (hospital_browsers[2][0], [
        ('/hospital', '爱心医院首页'),
        ('/hospital/adoption', '领养维护'),
        ('/hospital/treatment', '诊疗操作'),
        ('/hospital/material', '物料库存'),
    ]),
    (adopter_browsers['zhangxiaojie'][0], [
        ('/adopter', '领养大厅'),
        ('/adopter/my', '我的领养'),
        ('/adopter/messages', '消息中心'),
        ('/adopter/checkin', '回访打卡'),
    ]),
    (gov, [
        ('/government', '监管首页'),
        ('/government/supervision', '监管面板'),
        ('/government/ledger', '物料台账'),
        ('/government/material', '物料监管'),
    ]),
]
for browser, pages in pages_to_test:
    for path, name in pages:
        try:
            body = browser.get(path)
            has_error = 'Traceback' in body or 'BuildError' in body or 'UndefinedError' in body
            check(f'页面[{name}]渲染正常', not has_error and len(body) > 500,
                  '有错误' if has_error else f'内容太短({len(body)})')
        except Exception as e:
            check(f'页面[{name}]可访问', False, str(e)[:80])

# ============================================================
# 最终结果
# ============================================================
print('\n' + '=' * 70)
print(f'测试结果: {passed} 通过, {failed} 失败')
print('=' * 70)
if errors:
    print('\n失败项明细:')
    for e in errors:
        print(f'  - {e}')

sys.exit(0 if failed == 0 else 1)
