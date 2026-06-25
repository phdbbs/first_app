import os
import sqlite3
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, session, g, flash, jsonify
from functools import wraps

def adapt_datetime(dt):
    return dt.strftime('%Y-%m-%d %H:%M:%S')

def convert_datetime(val):
    if isinstance(val, bytes):
        val = val.decode()
    try:
        return datetime.strptime(val, '%Y-%m-%d %H:%M:%S')
    except:
        try:
            return datetime.strptime(val, '%Y-%m-%d')
        except:
            return val

sqlite3.register_adapter(datetime, adapt_datetime)
sqlite3.register_converter('datetime', convert_datetime)
sqlite3.register_converter('timestamp', convert_datetime)

app = Flask(__name__)
app.secret_key = 'tnr-secret-key-2025'
app.config['DATABASE'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tnr.db')
app.config['TEMPLATES_AUTO_RELOAD'] = True

@app.template_filter('dt')
def format_dt(value, fmt='%Y-%m-%d %H:%M'):
    if not value:
        return '-'
    if isinstance(value, str):
        try:
            if len(value) >= 19:
                value = datetime.strptime(value[:19], '%Y-%m-%d %H:%M:%S')
            elif len(value) >= 10:
                value = datetime.strptime(value[:10], '%Y-%m-%d')
            else:
                return value
        except:
            return value
    if isinstance(value, datetime):
        return value.strftime(fmt)
    return str(value)

ROLE_CONFIG = {
    'shelter': {'name': '捕捉站', 'color': 'orange', 'icon': '🏠'},
    'hospital': {'name': '宠物医院', 'color': 'green', 'icon': '🏥'},
    'adopter': {'name': '领养人', 'color': 'cyan', 'icon': '👤'},
    'government': {'name': '政府监管', 'color': 'purple', 'icon': '📊'},
}

PET_STATUS = {
    'intake': '在站',
    'transit': '转运中',
    'pending_treatment': '待诊疗',
    'treating': '诊疗中',
    'treated': '诊疗完成',
    'pending_adoption': '待领养',
    'pending_pickup': '待领取',
    'adopted': '已领养',
    'pending_release': '待放归',
    'released': '已放归',
    'euthanized': '已安乐死',
    'returned': '主人领回',
}

MATERIAL_TYPES = {
    'vaccine': '疫苗',
    'chip': '芯片',
    'dewormer': '驱虫药',
}

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(app.config['DATABASE'])
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
    return db

@app.teardown_appcontext
def close_db(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    conn = sqlite3.connect(app.config['DATABASE'])
    cursor = conn.cursor()

    cursor.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            name TEXT NOT NULL,
            phone TEXT,
            org_id INTEGER,
            is_blacklisted INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS institutions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,
            name TEXT NOT NULL,
            district TEXT,
            address TEXT,
            contact_person TEXT,
            contact_phone TEXT,
            status INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS communities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            district TEXT,
            address TEXT,
            property_name TEXT,
            contact_person TEXT,
            contact_phone TEXT,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS pets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pet_code TEXT UNIQUE NOT NULL,
            batch_no TEXT,
            species TEXT DEFAULT 'cat',
            gender TEXT,
            age TEXT,
            color TEXT,
            description TEXT,
            status TEXT DEFAULT 'intake',
            community_id INTEGER,
            property_name TEXT,
            property_contact TEXT,
            property_phone TEXT,
            address TEXT,
            intake_photo TEXT,
            intake_signature TEXT,
            intake_user_id INTEGER,
            intake_date TEXT DEFAULT (datetime('now','localtime')),
            current_hospital_id INTEGER,
            neutered INTEGER DEFAULT 0,
            vaccinated INTEGER DEFAULT 0,
            dewormed INTEGER DEFAULT 0,
            chipped INTEGER DEFAULT 0,
            chip_no TEXT,
            treatment_date TEXT,
            adoption_photo TEXT,
            adoption_desc TEXT,
            adopter_id INTEGER,
            adoption_date TEXT,
            release_community_id INTEGER,
            release_date TEXT,
            release_confirmed INTEGER DEFAULT 0,
            euthanasia_reason TEXT,
            euthanasia_date TEXT,
            return_owner_name TEXT,
            return_owner_phone TEXT,
            return_date TEXT,
            FOREIGN KEY (community_id) REFERENCES communities(id),
            FOREIGN KEY (intake_user_id) REFERENCES users(id),
            FOREIGN KEY (current_hospital_id) REFERENCES institutions(id),
            FOREIGN KEY (adopter_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS transfers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            batch_no TEXT NOT NULL,
            from_org_id INTEGER NOT NULL,
            to_hospital_id INTEGER NOT NULL,
            pet_id INTEGER NOT NULL,
            status TEXT DEFAULT 'pending',
            reject_reason TEXT,
            photo TEXT,
            created_by INTEGER,
            created_at TEXT DEFAULT (datetime('now','localtime')),
            received_at TEXT,
            FOREIGN KEY (from_org_id) REFERENCES institutions(id),
            FOREIGN KEY (to_hospital_id) REFERENCES institutions(id),
            FOREIGN KEY (pet_id) REFERENCES pets(id),
            FOREIGN KEY (created_by) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS treatments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pet_id INTEGER NOT NULL,
            hospital_id INTEGER NOT NULL,
            neuter_done INTEGER DEFAULT 0,
            neuter_record TEXT,
            vaccine_done INTEGER DEFAULT 0,
            dewormer_done INTEGER DEFAULT 0,
            chip_done INTEGER DEFAULT 0,
            chip_no TEXT,
            notes TEXT,
            treated_by INTEGER,
            treated_at TEXT DEFAULT (datetime('now','localtime')),
            completed INTEGER DEFAULT 0,
            FOREIGN KEY (pet_id) REFERENCES pets(id),
            FOREIGN KEY (hospital_id) REFERENCES institutions(id),
            FOREIGN KEY (treated_by) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS materials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,
            batch_no TEXT,
            chip_start TEXT,
            chip_end TEXT,
            quantity INTEGER DEFAULT 0,
            unit TEXT DEFAULT '支',
            supplier TEXT,
            purchase_date TEXT,
            expiry_date TEXT,
            location TEXT DEFAULT 'shelter',
            owner_id INTEGER,
            created_at TEXT DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (owner_id) REFERENCES institutions(id)
        );

        CREATE TABLE IF NOT EXISTS material_ledger (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            material_id INTEGER,
            type TEXT NOT NULL,
            action TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            from_location TEXT,
            to_location TEXT,
            from_owner_id INTEGER,
            to_owner_id INTEGER,
            chip_no TEXT,
            reason TEXT,
            operator_id INTEGER,
            operator_role TEXT,
            created_at TEXT DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (material_id) REFERENCES materials(id)
        );

        CREATE TABLE IF NOT EXISTS material_distributions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            batch_no TEXT NOT NULL,
            material_type TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            chip_start TEXT,
            chip_end TEXT,
            from_shelter_id INTEGER,
            to_hospital_id INTEGER NOT NULL,
            status TEXT DEFAULT 'pending',
            reject_reason TEXT,
            created_by INTEGER,
            created_at TEXT DEFAULT (datetime('now','localtime')),
            received_at TEXT,
            FOREIGN KEY (from_shelter_id) REFERENCES institutions(id),
            FOREIGN KEY (to_hospital_id) REFERENCES institutions(id),
            FOREIGN KEY (created_by) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS checkins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pet_id INTEGER NOT NULL,
            adopter_id INTEGER NOT NULL,
            month TEXT NOT NULL,
            photo TEXT,
            content TEXT,
            status TEXT DEFAULT 'pending',
            review_note TEXT,
            reviewed_by INTEGER,
            reviewed_at TEXT,
            created_at TEXT DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (pet_id) REFERENCES pets(id),
            FOREIGN KEY (adopter_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            content TEXT,
            type TEXT DEFAULT 'system',
            is_read INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS operation_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            role TEXT,
            action TEXT NOT NULL,
            detail TEXT,
            ip TEXT,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS adoption_applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pet_id INTEGER NOT NULL,
            adopter_id INTEGER NOT NULL,
            reason TEXT,
            experience TEXT,
            housing TEXT,
            status TEXT DEFAULT 'pending',
            review_note TEXT,
            reviewed_by INTEGER,
            reviewed_at TEXT,
            created_at TEXT DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (pet_id) REFERENCES pets(id),
            FOREIGN KEY (adopter_id) REFERENCES users(id),
            FOREIGN KEY (reviewed_by) REFERENCES users(id)
        );
    ''')

    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        cursor.executescript('''
            INSERT INTO institutions (type, name, district, address, contact_person, contact_phone) VALUES
            ('shelter', '市流浪动物捕捉站', '朝阳区', '朝阳区建国路88号', '王站长', '13800000001'),
            ('hospital', '爱心宠物医院', '朝阳区', '朝阳区望京街12号', '李医生', '13800000002'),
            ('hospital', '仁爱宠物医院', '海淀区', '海淀区中关村大街45号', '张医生', '13800000003'),
            ('hospital', '博爱宠物医院', '东城区', '东城区东单北大街18号', '刘医生', '13800000004');

            INSERT INTO communities (name, district, address, property_name, contact_person, contact_phone) VALUES
            ('阳光花园小区', '朝阳区', '朝阳区阳光路1号', '阳光物业', '张经理', '13800000010'),
            ('幸福里社区', '海淀区', '海淀区幸福路22号', '幸福物业', '王经理', '13800000011'),
            ('和谐家园', '东城区', '东城区和谐巷5号', '和谐物业', '李经理', '13800000012');

            INSERT INTO users (username, password, role, name, phone, org_id) VALUES
            ('admin', 'admin123', 'shelter', '管理员', '13800000001', 1),
            ('aixin', 'aixin123', 'hospital', '爱心医院', '13800000002', 2),
            ('renai', 'renai123', 'hospital', '仁爱医院', '13800000003', 3),
            ('boai', 'boai123', 'hospital', '博爱医院', '13800000004', 4),
            ('gov', 'gov123', 'government', '市级管理员', '13800000000', NULL);
        ''')

        cursor.executescript('''
            INSERT INTO materials (type, batch_no, quantity, unit, supplier, purchase_date, location, owner_id) VALUES
            ('vaccine', 'V20250101', 200, '支', '某生物制药', '2025-01-01', 'shelter', 1),
            ('chip', 'C20250101', 500, '个', '某科技公司', '2025-01-01', 'shelter', 1),
            ('dewormer', 'D20250101', 300, '支', '某药企', '2025-01-01', 'shelter', 1);

            INSERT INTO material_ledger (type, action, quantity, from_location, to_location, reason, operator_id, operator_role) VALUES
            ('vaccine', 'purchase', 200, NULL, 'shelter', '期初采购入库', 1, 'shelter'),
            ('chip', 'purchase', 500, NULL, 'shelter', '期初采购入库', 1, 'shelter'),
            ('dewormer', 'purchase', 300, NULL, 'shelter', '期初采购入库', 1, 'shelter');
        ''')

        pets_data = [
            ('TNR20250001', 'B202501001', 'cat', '母', '2岁', '橘色', '温顺橘猫', 'pending_treatment', 1, '阳光物业', '张经理', '13800000010', '朝阳区阳光路1号', 2, 1, '2025-01-10 09:00:00'),
            ('TNR20250002', 'B202501001', 'cat', '公', '1岁', '白色', '活泼白猫', 'pending_treatment', 1, '阳光物业', '张经理', '13800000010', '朝阳区阳光路1号', 2, 1, '2025-01-10 09:00:00'),
            ('TNR20250003', 'B202501002', 'dog', '公', '3岁', '黄色', '忠诚田园犬', 'pending_treatment', 2, '幸福物业', '王经理', '13800000011', '海淀区幸福路22号', 3, 1, '2025-01-11 10:00:00'),
            ('TNR20250004', 'B202501003', 'cat', '母', '1.5岁', '三花', '三花妹妹', 'pending_adoption', 3, '和谐物业', '李经理', '13800000012', '东城区和谐巷5号', 4, 1, '2025-01-08 14:00:00'),
            ('TNR20250005', 'B202501003', 'cat', '公', '2岁', '狸花', '健康狸花', 'pending_adoption', 3, '和谐物业', '李经理', '13800000012', '东城区和谐巷5号', 4, 1, '2025-01-08 14:00:00'),
            ('TNR20250006', 'B202501001', 'cat', '母', '8月', '纯白', '雪球小奶猫', 'pending_adoption', 1, '阳光物业', '张经理', '13800000010', '朝阳区阳光路1号', 2, 1, '2025-01-05 08:00:00'),
            ('TNR20250007', 'B202501002', 'dog', '公', '1岁', '棕色', '泰迪豆豆', 'pending_adoption', 2, '幸福物业', '王经理', '13800000011', '海淀区幸福路22号', 3, 1, '2025-01-06 11:00:00'),
            ('TNR20250008', 'B202501004', 'cat', '公', '3岁', '黑色', '黑猫警长', 'intake', 1, '阳光物业', '张经理', '138******10', '朝阳区阳光路1号', None, 1, '2025-01-15 09:30:00'),
        ]
        for p in pets_data:
            cursor.execute('''INSERT INTO pets (pet_code, batch_no, species, gender, age, color, description, status,
                community_id, property_name, property_contact, property_phone, address, current_hospital_id, intake_user_id, intake_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', p)

        cursor.execute("UPDATE pets SET neutered=1, vaccinated=1, dewormed=1, chipped=1, chip_no='CHIP000001', treatment_date='2025-01-12 15:00:00' WHERE id=4")
        cursor.execute("UPDATE pets SET neutered=1, vaccinated=1, dewormed=1, chipped=1, chip_no='CHIP000002', treatment_date='2025-01-12 16:00:00' WHERE id=5")
        cursor.execute("UPDATE pets SET neutered=1, vaccinated=1, dewormed=1, chipped=1, chip_no='CHIP000003', treatment_date='2025-01-09 10:00:00' WHERE id=6")
        cursor.execute("UPDATE pets SET neutered=1, vaccinated=1, dewormed=1, chipped=1, chip_no='CHIP000004', treatment_date='2025-01-10 14:00:00' WHERE id=7")

        treatments_seed = [
            (1, 2, 0, '', 0, 0, 0, '', '', 1, '2025-01-11 09:00:00', 0),
            (2, 2, 0, '', 0, 0, 0, '', '', 1, '2025-01-11 09:00:00', 0),
            (3, 3, 0, '', 0, 0, 0, '', '', 1, '2025-01-12 10:00:00', 0),
            (4, 4, 1, '母猫绝育手术成功，恢复良好', 1, 1, 1, 'CHIP000001', '全部完成', 2, '2025-01-12 15:00:00', 1),
            (5, 4, 1, '公猫绝育手术成功', 1, 1, 1, 'CHIP000002', '全部完成', 2, '2025-01-12 16:00:00', 1),
            (6, 2, 1, '母猫绝育，年纪小恢复快', 1, 1, 1, 'CHIP000003', '全部完成', 2, '2025-01-09 10:00:00', 1),
            (7, 3, 1, '公犬绝育', 1, 1, 1, 'CHIP000004', '全部完成', 3, '2025-01-10 14:00:00', 1),
        ]
        for t in treatments_seed:
            cursor.execute('''INSERT INTO treatments (pet_id, hospital_id, neuter_done, neuter_record, vaccine_done,
                dewormer_done, chip_done, chip_no, notes, treated_by, treated_at, completed)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', t)

        adopter_users = [
            ('adopter1', '123456', 'adopter', '李女士', '139******01', None),
            ('adopter2', '123456', 'adopter', '王先生', '139******02', None),
        ]
        for u in adopter_users:
            cursor.execute("INSERT OR IGNORE INTO users (username, password, role, name, phone, org_id) VALUES (?, ?, ?, ?, ?, ?)", u)

        cursor.execute("UPDATE pets SET adopter_id=(SELECT id FROM users WHERE username='adopter1'), adoption_date='2025-01-13 10:00:00', status='adopted', adoption_desc='温顺亲人' WHERE id=6")
        cursor.execute("UPDATE pets SET adopter_id=(SELECT id FROM users WHERE username='adopter2'), adoption_date='2025-01-14 14:00:00', status='adopted', adoption_desc='聪明听话' WHERE id=7")

        cursor.execute("INSERT INTO checkins (pet_id, adopter_id, month, photo, content, status, review_note, reviewed_by, created_at) VALUES (6, (SELECT id FROM users WHERE username='adopter1'), '2025-01', NULL, '雪球适应得很好，很活泼', 'approved', '情况良好', 1, '2025-01-20 10:00:00')")

        transfers_seed = [
            ('TR20250115001', 1, 2, 8, 'pending', None, None, 1, '2025-01-15 09:30:00', None),
        ]
        for tr in transfers_seed:
            cursor.execute('''INSERT INTO transfers (batch_no, from_org_id, to_hospital_id, pet_id, status, reject_reason, photo, created_by, created_at, received_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', tr)

        conn.commit()
    conn.close()

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def role_required(roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('login'))
            if session.get('role') not in roles:
                flash('无权限访问该页面', 'error')
                return redirect(url_for('portal'))
            return f(*args, **kwargs)
        return decorated
    return decorator

def log_action(action, detail=''):
    if 'user_id' in session:
        db = get_db()
        db.execute('INSERT INTO operation_logs (user_id, role, action, detail, ip) VALUES (?, ?, ?, ?, ?)',
                   (session['user_id'], session.get('role', ''), action, detail, request.remote_addr))
        db.commit()

def get_inventory(owner_id=None, location=None, material_type=None):
    db = get_db()
    query = '''SELECT type, SUM(quantity) as total FROM materials WHERE 1=1'''
    params = []
    if owner_id:
        query += ' AND owner_id = ?'
        params.append(owner_id)
    if location:
        query += ' AND location = ?'
        params.append(location)
    if material_type:
        query += ' AND type = ?'
        params.append(material_type)
    query += ' GROUP BY type'
    rows = db.execute(query, params).fetchall()
    result = {'vaccine': 0, 'chip': 0, 'dewormer': 0}
    for r in rows:
        result[r['type']] = r['total'] or 0
    return result

def get_counts():
    db = get_db()
    counts = {}
    counts['total_intake'] = db.execute("SELECT COUNT(*) FROM pets").fetchone()[0]
    counts['intake'] = db.execute("SELECT COUNT(*) FROM pets WHERE status='intake'").fetchone()[0]
    counts['transit'] = db.execute("SELECT COUNT(*) FROM transfers WHERE status='pending'").fetchone()[0]
    counts['pending_treatment'] = db.execute("SELECT COUNT(*) FROM pets WHERE status IN ('pending_treatment','treating')").fetchone()[0]
    counts['treated'] = db.execute("SELECT COUNT(*) FROM pets WHERE status='treated'").fetchone()[0]
    counts['pending_adoption'] = db.execute("SELECT COUNT(*) FROM pets WHERE status='pending_adoption'").fetchone()[0]
    counts['pending_pickup'] = db.execute("SELECT COUNT(*) FROM pets WHERE status='pending_pickup'").fetchone()[0]
    counts['adopted'] = db.execute("SELECT COUNT(*) FROM pets WHERE status='adopted'").fetchone()[0]
    counts['pending_release'] = db.execute("SELECT COUNT(*) FROM pets WHERE status='pending_release'").fetchone()[0]
    counts['released'] = db.execute("SELECT COUNT(*) FROM pets WHERE status='released'").fetchone()[0]
    counts['euthanized'] = db.execute("SELECT COUNT(*) FROM pets WHERE status='euthanized'").fetchone()[0]
    counts['returned'] = db.execute("SELECT COUNT(*) FROM pets WHERE status='returned'").fetchone()[0]
    counts['pending_dist'] = db.execute("SELECT COUNT(*) FROM material_distributions WHERE status='pending'").fetchone()[0]
    counts['pending_applications'] = db.execute("SELECT COUNT(*) FROM adoption_applications WHERE status='pending'").fetchone()[0]
    counts['hospitals'] = db.execute("SELECT COUNT(*) FROM institutions WHERE type='hospital' AND status=1").fetchone()[0]
    counts['adopters'] = db.execute("SELECT COUNT(*) FROM users WHERE role='adopter' AND is_blacklisted=0").fetchone()[0]
    return counts

@app.route('/')
def index():
    return redirect(url_for('portal'))

@app.route('/portal')
def portal():
    if 'user_id' in session:
        role = session.get('role')
        if role == 'shelter':
            return redirect(url_for('shelter_dashboard'))
        elif role == 'hospital':
            return redirect(url_for('hospital_dashboard'))
        elif role == 'adopter':
            return redirect(url_for('adopter_hall'))
        elif role == 'government':
            return redirect(url_for('gov_dashboard'))
    return render_template('portal.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        role = request.form.get('role', '')
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE username=? AND password=? AND role=?',
                          (username, password, role)).fetchone()
        if user:
            if user['is_blacklisted']:
                flash('该账号已被列入黑名单，请联系管理员', 'error')
                return render_template('login.html', role=role)
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['name'] = user['name']
            session['role'] = user['role']
            session['org_id'] = user['org_id']
            session['is_blacklisted'] = bool(user['is_blacklisted'])
            log_action('login', f'用户{user["name"]}登录')
            if role == 'shelter':
                return redirect(url_for('shelter_dashboard'))
            elif role == 'hospital':
                return redirect(url_for('hospital_dashboard'))
            elif role == 'adopter':
                return redirect(url_for('adopter_hall'))
            elif role == 'government':
                return redirect(url_for('gov_dashboard'))
        else:
            flash('用户名或密码错误', 'error')
    role = request.args.get('role', 'shelter')
    return render_template('login.html', role=role)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        name = request.form.get('name', '')
        phone = request.form.get('phone', '')
        db = get_db()
        existing = db.execute('SELECT id FROM users WHERE username=?', (username,)).fetchone()
        if existing:
            flash('用户名已存在', 'error')
        else:
            db.execute('INSERT INTO users (username, password, role, name, phone) VALUES (?, ?, ?, ?, ?)',
                       (username, password, 'adopter', name, phone))
            db.commit()
            flash('注册成功，请登录', 'success')
            return redirect(url_for('login', role='adopter'))
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('portal'))

def gen_batch_no(prefix):
    now = datetime.now()
    return f"{prefix}{now.strftime('%Y%m%d%H%M%S')}"

def gen_pet_code():
    db = get_db()
    row = db.execute("SELECT COUNT(*) as c FROM pets").fetchone()
    return f"TNR{datetime.now().year}{str(row['c']+1).zfill(4)}"

@app.route('/shelter')
@role_required(['shelter'])
def shelter_dashboard():
    db = get_db()
    inventory = get_inventory(owner_id=1, location='shelter')
    recent_pets = db.execute("SELECT p.*, c.name as community_name FROM pets p LEFT JOIN communities c ON p.community_id=c.id ORDER BY p.intake_date DESC LIMIT 10").fetchall()
    pending_transfers = db.execute("SELECT t.*, p.pet_code, i.name as hospital_name FROM transfers t JOIN pets p ON t.pet_id=p.id JOIN institutions i ON t.to_hospital_id=i.id WHERE t.status='pending' ORDER BY t.created_at DESC LIMIT 5").fetchall()
    stats = get_counts()
    shelter_inv = get_inventory(owner_id=1)
    alerts = []
    if shelter_inv.get('vaccine', 0) < 20:
        alerts.append(f"疫苗库存预警: 当前{shelter_inv['vaccine']}支，低于安全库存20支")
    if shelter_inv.get('chip', 0) < 50:
        alerts.append(f"芯片库存预警: 当前{shelter_inv['chip']}个，低于安全库存50个")
    tasks = []
    if stats['intake'] > 0:
        tasks.append({'priority': 'high', 'name': f'{stats["intake"]}只新收容动物待转运', 'desc': '请尽快安排转运至医院', 'time': '待处理', 'badge': '紧急'})
    if stats['transit'] > 0:
        tasks.append({'priority': 'high', 'name': f'{stats["transit"]}个转运单待医院确认', 'desc': '等待医院接收确认', 'time': '待处理', 'badge': '紧急'})
    if stats['pending_release'] > 0:
        tasks.append({'priority': 'medium', 'name': f'{stats["pending_release"]}只动物待放归', 'desc': '请安排放归至原社区', 'time': '待处理', 'badge': '普通'})
    if stats['pending_applications'] > 0:
        tasks.append({'priority': 'high', 'name': f'{stats["pending_applications"]}份领养申请待审核', 'desc': '请及时审核领养申请', 'time': '待处理', 'badge': '紧急'})
    low_stock = sum(1 for v in shelter_inv.values() if v < 20)
    if low_stock > 0:
        tasks.append({'priority': 'medium', 'name': f'{low_stock}种物料库存不足', 'desc': '请及时采购补充', 'time': '待处理', 'badge': '普通'})
    return render_template('shelter/dashboard.html', inventory=inventory, recent_pets=recent_pets,
                           pending_transfers=pending_transfers, stats=stats, alerts=alerts, tasks=tasks,
                           role_config=ROLE_CONFIG)

@app.route('/shelter/add', methods=['GET', 'POST'])
@role_required(['shelter'])
def shelter_add():
    db = get_db()
    communities = db.execute("SELECT * FROM communities ORDER BY id DESC").fetchall()
    hospitals = db.execute("SELECT * FROM institutions WHERE type='hospital' AND status=1").fetchall()
    if request.method == 'POST':
        property_name = request.form.get('property_name', '')
        community_id = request.form.get('community_id')
        community_name = request.form.get('community_name', '')
        address = request.form.get('address', '')
        contact_person = request.form.get('contact_person', '')
        contact_phone = request.form.get('contact_phone', '')
        pet_count = int(request.form.get('pet_count', 1))
        species = request.form.get('species', 'cat')
        batch_no = gen_batch_no('B')
        new_pet_ids = []
        for i in range(pet_count):
            pet_code = gen_pet_code()
            cur = db.execute('''INSERT INTO pets (pet_code, batch_no, species, status, community_id, property_name,
                property_contact, property_phone, address, intake_user_id)
                VALUES (?, ?, ?, 'intake', ?, ?, ?, ?, ?, ?)''',
                (pet_code, batch_no, species, community_id if community_id else None,
                 property_name, contact_person, contact_phone, address, session['user_id']))
            new_pet_ids.append(cur.lastrowid)
        db.execute('INSERT INTO operation_logs (user_id, role, action, detail) VALUES (?, ?, ?, ?)',
                   (session['user_id'], 'shelter', 'shelter_intake', f'批次{batch_no}收容{pet_count}只动物'))
        db.commit()
        log_action('shelter_intake', f'批次{batch_no}收容{pet_count}只')
        flash(f'成功收容{pet_count}只动物，批次号：{batch_no}', 'success')
        return redirect(url_for('shelter_transfer'))
    return render_template('shelter/add_shelter.html', communities=communities, hospitals=hospitals,
                           role_config=ROLE_CONFIG)

@app.route('/shelter/owner-return', methods=['GET', 'POST'])
@role_required(['shelter'])
def shelter_owner_return():
    db = get_db()
    intake_pets = db.execute("SELECT * FROM pets WHERE status='intake' ORDER BY intake_date DESC").fetchall()
    if request.method == 'POST':
        pet_id = request.form.get('pet_id')
        owner_name = request.form.get('owner_name', '')
        owner_phone = request.form.get('owner_phone', '')
        note = request.form.get('note', '')
        db.execute("UPDATE pets SET status='returned', return_owner_name=?, return_owner_phone=?, return_date=datetime('now','localtime') WHERE id=?",
                   (owner_name, owner_phone, pet_id))
        log_action('owner_return', f'宠物{pet_id}被主人{owner_name}领回')
        db.commit()
        flash('主人领回登记成功，已出库归档', 'success')
        return redirect(url_for('shelter_owner_return'))
    return render_template('shelter/owner_return.html', intake_pets=intake_pets, role_config=ROLE_CONFIG)

@app.route('/shelter/material', methods=['GET', 'POST'])
@role_required(['shelter'])
def shelter_material():
    db = get_db()
    if request.method == 'POST':
        action = request.form.get('action', '')
        if action == 'purchase':
            mtype = request.form.get('material_type')
            quantity = int(request.form.get('quantity', 0))
            batch_no = request.form.get('batch_no', gen_batch_no('WL'))
            supplier = request.form.get('supplier', '')
            chip_start = request.form.get('chip_start', '')
            chip_end = request.form.get('chip_end', '')
            db.execute('''INSERT INTO materials (type, batch_no, chip_start, chip_end, quantity, unit, supplier, purchase_date, location, owner_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, date('now','localtime'), 'shelter', 1)''',
                (mtype, batch_no, chip_start, chip_end, quantity, '支' if mtype != 'chip' else '个', supplier))
            mat_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
            db.execute('''INSERT INTO material_ledger (material_id, type, action, quantity, to_location, reason, operator_id, operator_role)
                VALUES (?, ?, 'purchase', ?, 'shelter', ?, ?, 'shelter')''',
                (mat_id, mtype, quantity, f'采购入库 批次{batch_no}', session['user_id']))
            log_action('material_purchase', f'采购{MATERIAL_TYPES[mtype]}{quantity}单位 批次{batch_no}')
            db.commit()
            flash('物料采购入库成功', 'success')
        elif action == 'distribute':
            mtype = request.form.get('material_type')
            quantity = int(request.form.get('quantity', 0))
            hospital_id = request.form.get('hospital_id')
            chip_start = request.form.get('chip_start', '')
            chip_end = request.form.get('chip_end', '')
            batch_no = gen_batch_no('WL')
            db.execute('''INSERT INTO material_distributions (batch_no, material_type, quantity, chip_start, chip_end, from_shelter_id, to_hospital_id, status, created_by)
                VALUES (?, ?, ?, ?, ?, 1, ?, 'pending', ?)''',
                (batch_no, mtype, quantity, chip_start, chip_end, hospital_id, session['user_id']))
            log_action('material_distribute', f'下发{MATERIAL_TYPES[mtype]}{quantity}单位至医院{hospital_id}')
            db.commit()
            flash('物料下发成功，等待医院确认接收', 'success')
        return redirect(url_for('shelter_material'))

    inventory = get_inventory(owner_id=1)
    hospitals = db.execute("SELECT * FROM institutions WHERE type='hospital' AND status=1").fetchall()
    ledger = db.execute("SELECT * FROM material_ledger ORDER BY created_at DESC LIMIT 50").fetchall()
    distributions = db.execute("SELECT d.*, i.name as hospital_name FROM material_distributions d JOIN institutions i ON d.to_hospital_id=i.id ORDER BY d.created_at DESC LIMIT 30").fetchall()
    return render_template('shelter/material.html', inventory=inventory, hospitals=hospitals, ledger=ledger,
                           distributions=distributions, MATERIAL_TYPES=MATERIAL_TYPES, role_config=ROLE_CONFIG)

@app.route('/shelter/transfer', methods=['GET', 'POST'])
@role_required(['shelter'])
def shelter_transfer():
    db = get_db()
    if request.method == 'POST':
        pet_ids = request.form.getlist('pet_ids')
        hospital_id = request.form.get('hospital_id')
        if not pet_ids:
            flash('请选择要转运的动物', 'error')
            return redirect(url_for('shelter_transfer'))
        batch_no = gen_batch_no('TR')
        for pid in pet_ids:
            db.execute('''INSERT INTO transfers (batch_no, from_org_id, to_hospital_id, pet_id, status, created_by)
                VALUES (?, 1, ?, ?, 'pending', ?)''', (batch_no, hospital_id, pid, session['user_id']))
            db.execute("UPDATE pets SET status='transit' WHERE id=?", (pid,))
        log_action('transfer_create', f'批次{batch_no}转运{len(pet_ids)}只动物至医院{hospital_id}')
        db.commit()
        flash(f'转运单{batch_no}已创建，等待医院接收', 'success')
        return redirect(url_for('shelter_transfer'))

    intake_pets = db.execute("SELECT p.*, c.name as community_name FROM pets p LEFT JOIN communities c ON p.community_id=c.id WHERE p.status='intake' ORDER BY p.intake_date DESC").fetchall()
    hospitals = db.execute("SELECT * FROM institutions WHERE type='hospital' AND status=1").fetchall()
    transfers = db.execute('''SELECT t.*, p.pet_code, p.species, i.name as hospital_name FROM transfers t
        JOIN pets p ON t.pet_id=p.id JOIN institutions i ON t.to_hospital_id=i.id
        ORDER BY t.created_at DESC LIMIT 50''').fetchall()
    return render_template('shelter/transfer.html', intake_pets=intake_pets, hospitals=hospitals, transfers=transfers,
                           role_config=ROLE_CONFIG)

@app.route('/shelter/release', methods=['GET', 'POST'])
@role_required(['shelter'])
def shelter_release():
    db = get_db()
    if request.method == 'POST':
        pet_ids = request.form.getlist('pet_ids')
        action_type = request.form.get('action_type', 'confirm')
        if action_type == 'recover':
            for pid in pet_ids:
                db.execute("UPDATE pets SET status='pending_release', current_hospital_id=NULL WHERE id=?", (pid,))
            log_action('recover_pets', f'回收{len(pet_ids)}只治愈动物')
            db.commit()
            flash(f'已回收{len(pet_ids)}只动物，等待放归', 'success')
        elif action_type == 'release':
            for pid in pet_ids:
                db.execute("UPDATE pets SET status='released', release_date=datetime('now','localtime'), release_confirmed=1 WHERE id=?", (pid,))
            log_action('release_pets', f'放归{len(pet_ids)}只动物')
            db.commit()
            flash(f'已完成{len(pet_ids)}只动物放归', 'success')
        return redirect(url_for('shelter_release'))

    treated_pets = db.execute("SELECT p.*, i.name as hospital_name, c.name as community_name FROM pets p LEFT JOIN institutions i ON p.current_hospital_id=i.id LEFT JOIN communities c ON p.community_id=c.id WHERE p.status='treated' ORDER BY p.treatment_date DESC").fetchall()
    pending_release = db.execute("SELECT p.*, c.name as community_name FROM pets p LEFT JOIN communities c ON p.community_id=c.id WHERE p.status='pending_release' ORDER BY p.intake_date DESC").fetchall()
    released_pets = db.execute("SELECT p.*, c.name as community_name FROM pets p LEFT JOIN communities c ON p.release_community_id=c.id WHERE p.status='released' ORDER BY p.release_date DESC LIMIT 30").fetchall()
    return render_template('shelter/release.html', treated_pets=treated_pets, pending_release=pending_release,
                           released_pets=released_pets, role_config=ROLE_CONFIG)

@app.route('/shelter/adoption', methods=['GET', 'POST'])
@role_required(['shelter'])
def shelter_adoption():
    db = get_db()
    if request.method == 'POST':
        action = request.form.get('action', '')
        if action == 'approve_application':
            app_id = request.form.get('application_id')
            app_data = db.execute("SELECT * FROM adoption_applications WHERE id=?", (app_id,)).fetchone()
            if app_data:
                db.execute("UPDATE adoption_applications SET status='approved', reviewed_by=?, reviewed_at=datetime('now','localtime') WHERE id=?",
                           (session['user_id'], app_id))
                db.execute("UPDATE pets SET status='pending_pickup', adopter_id=?, adoption_date=datetime('now','localtime') WHERE id=?",
                           (app_data['adopter_id'], app_data['pet_id']))
                db.execute("UPDATE adoption_applications SET status='rejected', reviewed_by=?, reviewed_at=datetime('now','localtime'), review_note='该宠物已被其他申请人领养' WHERE pet_id=? AND id!=? AND status='pending'",
                           (session['user_id'], app_data['pet_id'], app_id))
                db.execute("INSERT INTO messages (user_id, title, content, type) VALUES (?, '领养申请审核通过', '您的领养申请已审核通过，请前往对应医院完成领宠手续', 'adoption')",
                           (app_data['adopter_id'],))
                rejected = db.execute("SELECT adopter_id FROM adoption_applications WHERE pet_id=? AND id!=? AND status='rejected' AND reviewed_at IS NOT NULL",
                                     (app_data['pet_id'], app_id)).fetchall()
                for r in rejected:
                    db.execute("INSERT INTO messages (user_id, title, content, type) VALUES (?, '领养申请未通过', '很抱歉，您申请领养的宠物已被其他申请人领养', 'adoption')",
                               (r['adopter_id'],))
                log_action('adoption_approve', f'领养申请{app_id}通过，宠物{app_data["pet_id"]}分配给领养人{app_data["adopter_id"]}')
                db.commit()
                flash('领养申请已通过，已通知领养人前往医院领宠', 'success')
        elif action == 'reject_application':
            app_id = request.form.get('application_id')
            note = request.form.get('reject_note', '')
            app_data = db.execute("SELECT * FROM adoption_applications WHERE id=?", (app_id,)).fetchone()
            if app_data:
                db.execute("UPDATE adoption_applications SET status='rejected', reviewed_by=?, reviewed_at=datetime('now','localtime'), review_note=? WHERE id=?",
                           (session['user_id'], note, app_id))
                db.execute("INSERT INTO messages (user_id, title, content, type) VALUES (?, '领养申请未通过', ?, 'adoption')",
                           (app_data['adopter_id'], note or '很抱歉，您的领养申请未通过审核'))
                log_action('adoption_reject', f'领养申请{app_id}被驳回')
                db.commit()
                flash('已驳回申请', 'success')
        elif action == 'blacklist':
            user_id = request.form.get('user_id')
            db.execute("UPDATE users SET is_blacklisted=1 WHERE id=?", (user_id,))
            session['is_blacklisted'] = True
            log_action('blacklist_add', f'用户{user_id}加入黑名单')
            db.commit()
            flash('已加入黑名单', 'success')
        elif action == 'unblacklist':
            user_id = request.form.get('user_id')
            db.execute("UPDATE users SET is_blacklisted=0 WHERE id=?", (user_id,))
            log_action('blacklist_remove', f'用户{user_id}移出黑名单')
            db.commit()
            flash('已移出黑名单', 'success')
        elif action == 'review_checkin':
            checkin_id = request.form.get('checkin_id')
            result = request.form.get('result', 'approved')
            note = request.form.get('note', '')
            db.execute("UPDATE checkins SET status=?, review_note=?, reviewed_by=?, reviewed_at=datetime('now','localtime') WHERE id=?",
                       (result, note, session['user_id'], checkin_id))
            c = db.execute("SELECT adopter_id FROM checkins WHERE id=?", (checkin_id,)).fetchone()
            if result == 'rejected':
                db.execute("INSERT INTO messages (user_id, title, content, type) VALUES (?, '打卡审核未通过', ?, 'checkin')",
                           (c['adopter_id'], note or '您的打卡未通过，请按要求重新打卡'))
            else:
                db.execute("INSERT INTO messages (user_id, title, content, type) VALUES (?, '打卡审核通过', '您的回访打卡已审核通过，感谢您的照顾！', 'checkin')",
                           (c['adopter_id'],))
            db.commit()
            flash('打卡审核完成', 'success')
        return redirect(url_for('shelter_adoption'))

    pending_pets = db.execute("SELECT p.*, i.name as hospital_name FROM pets p LEFT JOIN institutions i ON p.current_hospital_id=i.id WHERE p.status='pending_adoption' ORDER BY p.treatment_date DESC").fetchall()
    pickup_pets = db.execute("SELECT p.*, u.name as adopter_name, u.phone as adopter_phone, i.name as hospital_name FROM pets p JOIN users u ON p.adopter_id=u.id LEFT JOIN institutions i ON p.current_hospital_id=i.id WHERE p.status='pending_pickup' ORDER BY p.adoption_date DESC").fetchall()
    adopters = db.execute("SELECT * FROM users WHERE role='adopter' ORDER BY created_at DESC").fetchall()
    adopted_pets = db.execute("SELECT p.*, u.name as adopter_name, u.phone as adopter_phone, i.name as hospital_name FROM pets p JOIN users u ON p.adopter_id=u.id LEFT JOIN institutions i ON p.current_hospital_id=i.id WHERE p.status='adopted' ORDER BY p.adoption_date DESC").fetchall()
    checkins = db.execute("SELECT c.*, p.pet_code, u.name as adopter_name FROM checkins c JOIN pets p ON c.pet_id=p.id JOIN users u ON c.adopter_id=u.id ORDER BY c.created_at DESC LIMIT 30").fetchall()
    blacklist = db.execute("SELECT * FROM users WHERE is_blacklisted=1").fetchall()
    applications = db.execute('''SELECT a.*, p.pet_code, u.name as adopter_name, u.phone as adopter_phone
        FROM adoption_applications a JOIN pets p ON a.pet_id=p.id JOIN users u ON a.adopter_id=u.id
        WHERE a.status='pending' ORDER BY a.created_at DESC''').fetchall()
    return render_template('shelter/adoption.html', pending_pets=pending_pets, pickup_pets=pickup_pets, adopters=adopters,
                           adopted_pets=adopted_pets, checkins=checkins, blacklist=blacklist,
                           applications=applications, role_config=ROLE_CONFIG)

@app.route('/shelter/report')
@role_required(['shelter'])
def shelter_report():
    db = get_db()
    stats = get_counts()
    pets = db.execute("SELECT p.*, c.name as community_name, i.name as hospital_name, u.name as adopter_name FROM pets p LEFT JOIN communities c ON p.community_id=c.id LEFT JOIN institutions i ON p.current_hospital_id=i.id LEFT JOIN users u ON p.adopter_id=u.id ORDER BY p.intake_date DESC").fetchall()
    return render_template('shelter/report.html', stats=stats, pets=pets, PET_STATUS=PET_STATUS, role_config=ROLE_CONFIG)

@app.route('/pet/<int:pet_id>')
@role_required(['shelter', 'hospital', 'adopter', 'government'])
def pet_archive(pet_id):
    db = get_db()
    pet = db.execute("SELECT p.*, c.name as community_name, i.name as hospital_name, u.name as adopter_name, u.phone as adopter_phone FROM pets p LEFT JOIN communities c ON p.community_id=c.id LEFT JOIN institutions i ON p.current_hospital_id=i.id LEFT JOIN users u ON p.adopter_id=u.id WHERE p.id=?", (pet_id,)).fetchone()
    if not pet:
        flash('宠物不存在', 'error')
        return redirect(url_for('portal'))
    treatments = db.execute("SELECT t.*, u.name as doctor_name FROM treatments t LEFT JOIN users u ON t.treated_by=u.id WHERE t.pet_id=? ORDER BY t.treated_at DESC", (pet_id,)).fetchall()
    transfers = db.execute("SELECT t.*, i.name as hospital_name, u.name as creator_name FROM transfers t JOIN institutions i ON t.to_hospital_id=i.id LEFT JOIN users u ON t.created_by=u.id WHERE t.pet_id=? ORDER BY t.created_at DESC", (pet_id,)).fetchall()
    checkins = db.execute("SELECT c.*, u.name as adopter_name FROM checkins c JOIN users u ON c.adopter_id=u.id WHERE c.pet_id=? ORDER BY c.created_at DESC", (pet_id,)).fetchall()
    role = session.get('role', 'shelter')
    return render_template('common/pet_archive.html', pet=pet, treatments=treatments, transfers=transfers,
                           checkins=checkins, PET_STATUS=PET_STATUS, MATERIAL_TYPES=MATERIAL_TYPES, role=role)

@app.route('/shelter/settings')
@role_required(['shelter'])
def shelter_settings():
    db = get_db()
    logs = db.execute("SELECT l.*, u.name as user_name FROM operation_logs l LEFT JOIN users u ON l.user_id=u.id ORDER BY l.created_at DESC LIMIT 50").fetchall()
    return render_template('shelter/settings.html', logs=logs, role_config=ROLE_CONFIG)

@app.route('/hospital')
@role_required(['hospital'])
def hospital_dashboard():
    db = get_db()
    org_id = session['org_id']
    inventory = get_inventory(owner_id=org_id, location='hospital')
    pending_receive = db.execute("SELECT COUNT(*) FROM transfers WHERE to_hospital_id=? AND status='pending'", (org_id,)).fetchone()[0]
    pending_material = db.execute("SELECT COUNT(*) FROM material_distributions WHERE to_hospital_id=? AND status='pending'", (org_id,)).fetchone()[0]
    pending_treat = db.execute("SELECT COUNT(*) FROM pets WHERE current_hospital_id=? AND status IN ('pending_treatment','treating')", (org_id,)).fetchone()[0]
    pending_adoption = db.execute("SELECT COUNT(*) FROM pets WHERE current_hospital_id=? AND status='treated'", (org_id,)).fetchone()[0]
    pending_pickup = db.execute("SELECT COUNT(*) FROM pets WHERE current_hospital_id=? AND status='pending_pickup'", (org_id,)).fetchone()[0]
    alerts = []
    if inventory.get('vaccine', 0) < 10:
        alerts.append(f"疫苗库存预警: 当前{inventory['vaccine']}支，请及时向捕捉站申请")
    if inventory.get('chip', 0) < 10:
        alerts.append(f"芯片库存预警: 当前{inventory['chip']}个，请及时向捕捉站申请")
    tasks = []
    pending_trans_list = db.execute("SELECT t.*, p.pet_code, p.species FROM transfers t JOIN pets p ON t.pet_id=p.id WHERE t.to_hospital_id=? AND t.status='pending' ORDER BY t.created_at DESC LIMIT 5", (org_id,)).fetchall()
    for tr in pending_trans_list:
        tasks.append({'priority': 'high', 'name': f'转运单{tr["batch_no"]}待签收', 'desc': f'宠物{tr["pet_code"]}待接收', 'time': tr['created_at'], 'badge': '紧急'})
    treat_pets = db.execute("SELECT p.* FROM pets p WHERE p.current_hospital_id=? AND p.status IN ('pending_treatment','treating') LIMIT 5", (org_id,)).fetchall()
    for p in treat_pets:
        tasks.append({'priority': 'high', 'name': f'宠物{p["pet_code"]}待诊疗', 'desc': '需完成绝育/疫苗/驱虫/芯片', 'time': p['intake_date'], 'badge': '紧急'})
    pickup_list = db.execute("SELECT p.*, u.name as adopter_name FROM pets p JOIN users u ON p.adopter_id=u.id WHERE p.current_hospital_id=? AND p.status='pending_pickup' LIMIT 5", (org_id,)).fetchall()
    for p in pickup_list:
        tasks.append({'priority': 'medium', 'name': f'宠物{p["pet_code"]}待领出', 'desc': f'领养人{p["adopter_name"]}待领走', 'time': p['adoption_date'], 'badge': '待办'})
    stats = {
        'pending_receive': pending_receive,
        'pending_treat': pending_treat,
        'pending_adoption': pending_adoption,
        'pending_pickup': pending_pickup,
        'pending_material': pending_material,
        'alerts_count': len(alerts),
    }
    recent_treatments = db.execute("SELECT t.*, p.pet_code FROM treatments t JOIN pets p ON t.pet_id=p.id WHERE t.hospital_id=? ORDER BY t.treated_at DESC LIMIT 5", (org_id,)).fetchall()
    return render_template('hospital/dashboard.html', inventory=inventory, stats=stats, alerts=alerts, tasks=tasks,
                           recent_treatments=recent_treatments, role_config=ROLE_CONFIG)

@app.route('/hospital/receive', methods=['GET', 'POST'])
@role_required(['hospital'])
def hospital_receive():
    db = get_db()
    org_id = session['org_id']
    if request.method == 'POST':
        action = request.form.get('action', '')
        transfer_id = request.form.get('transfer_id')
        if action == 'receive':
            tr = db.execute("SELECT * FROM transfers WHERE id=?", (transfer_id,)).fetchone()
            db.execute("UPDATE transfers SET status='received', received_at=datetime('now','localtime') WHERE id=?", (transfer_id,))
            db.execute("UPDATE pets SET status='pending_treatment', current_hospital_id=? WHERE id=?", (org_id, tr['pet_id']))
            existing_treatment = db.execute("SELECT id FROM treatments WHERE pet_id=? AND hospital_id=?", (tr['pet_id'], org_id)).fetchone()
            if not existing_treatment:
                db.execute("INSERT INTO treatments (pet_id, hospital_id, treated_by) VALUES (?, ?, ?)",
                           (tr['pet_id'], org_id, session['user_id']))
            log_action('transfer_receive', f'接收转运单{transfer_id}')
            db.commit()
            flash('动物已签收，状态更新为待诊疗', 'success')
        elif action == 'reject':
            reason = request.form.get('reject_reason', '')
            db.execute("UPDATE transfers SET status='rejected', reject_reason=? WHERE id=?", (reason, transfer_id))
            tr = db.execute("SELECT * FROM transfers WHERE id=?", (transfer_id,)).fetchone()
            db.execute("UPDATE pets SET status='intake' WHERE id=?", (tr['pet_id'],))
            log_action('transfer_reject', f'驳回转运单{transfer_id}，原因：{reason}')
            db.commit()
            flash('已驳回转运单', 'success')
        return redirect(url_for('hospital_receive'))

    pending = db.execute('''SELECT t.*, p.pet_code, p.species, p.color, p.description, c.name as community_name
        FROM transfers t JOIN pets p ON t.pet_id=p.id LEFT JOIN communities c ON p.community_id=c.id
        WHERE t.to_hospital_id=? AND t.status='pending' ORDER BY t.created_at DESC''', (org_id,)).fetchall()
    received = db.execute('''SELECT t.*, p.pet_code, p.species FROM transfers t JOIN pets p ON t.pet_id=p.id
        WHERE t.to_hospital_id=? AND t.status='received' ORDER BY t.received_at DESC LIMIT 30''', (org_id,)).fetchall()
    return render_template('hospital/receive.html', pending=pending, received=received, role_config=ROLE_CONFIG)

@app.route('/hospital/treatment', methods=['GET', 'POST'])
@role_required(['hospital'])
def hospital_treatment():
    db = get_db()
    org_id = session['org_id']
    if request.method == 'POST':
        pet_id = request.form.get('pet_id')
        neuter_done = 1 if request.form.get('neuter_done') else 0
        neuter_record = request.form.get('neuter_record', '')
        vaccine_done = 1 if request.form.get('vaccine_done') else 0
        dewormer_done = 1 if request.form.get('dewormer_done') else 0
        chip_done = 1 if request.form.get('chip_done') else 0
        chip_no = request.form.get('chip_no', '')
        notes = request.form.get('notes', '')
        completed = 1 if request.form.get('completed') else 0

        inventory = get_inventory(owner_id=org_id)
        if vaccine_done and inventory.get('vaccine', 0) < 1:
            flash('疫苗库存不足，无法接种', 'error')
            return redirect(url_for('hospital_treatment'))
        if dewormer_done and inventory.get('dewormer', 0) < 1:
            flash('驱虫药库存不足', 'error')
            return redirect(url_for('hospital_treatment'))
        if chip_done and inventory.get('chip', 0) < 1:
            flash('芯片库存不足', 'error')
            return redirect(url_for('hospital_treatment'))

        db.execute('''UPDATE treatments SET neuter_done=?, neuter_record=?, vaccine_done=?, dewormer_done=?,
            chip_done=?, chip_no=?, notes=?, completed=?, treated_by=?, treated_at=datetime('now','localtime')
            WHERE pet_id=? AND hospital_id=?''',
            (neuter_done, neuter_record, vaccine_done, dewormer_done, chip_done, chip_no, notes, completed,
             session['user_id'], pet_id, org_id))

        db.execute("UPDATE pets SET neutered=?, vaccinated=?, dewormed=?, chipped=?, chip_no=? WHERE id=?",
                   (neuter_done, vaccine_done, dewormer_done, chip_done, chip_no if chip_done else None, pet_id))

        if completed:
            db.execute("UPDATE pets SET status='treated', treatment_date=datetime('now','localtime') WHERE id=?", (pet_id,))

            def consume_material(mat_type, chip_val=None):
                row = db.execute("SELECT id, quantity FROM materials WHERE owner_id=? AND type=? AND quantity>0 ORDER BY id LIMIT 1", (org_id, mat_type)).fetchone()
                if row:
                    db.execute("UPDATE materials SET quantity=quantity-1 WHERE id=?", (row['id'],))
                    ledger_chip = chip_val if mat_type == 'chip' else None
                    reason = f'诊疗消耗-{MATERIAL_TYPES[mat_type]}'
                    db.execute('''INSERT INTO material_ledger (material_id, type, action, quantity, from_location, chip_no, reason, operator_id, operator_role)
                        VALUES (?, ?, 'consume', 1, 'hospital', ?, ?, ?, 'hospital')''',
                        (row['id'], mat_type, ledger_chip, reason, session['user_id']))

            if vaccine_done:
                consume_material('vaccine')
            if dewormer_done:
                consume_material('dewormer')
            if chip_done:
                consume_material('chip', chip_no)
            log_action('treatment_complete', f'宠物{pet_id}诊疗完成，已上架领养大厅')
        else:
            db.execute("UPDATE pets SET status='treating' WHERE id=? AND status='pending_treatment'", (pet_id,))
            log_action('treatment_update', f'宠物{pet_id}诊疗更新')
        db.commit()
        flash('诊疗记录已保存', 'success')
        return redirect(url_for('hospital_treatment'))

    pending_pets = db.execute("SELECT p.* FROM pets p WHERE p.current_hospital_id=? AND p.status IN ('pending_treatment','treating') ORDER BY p.intake_date", (org_id,)).fetchall()
    treated_pets = db.execute("SELECT p.*, t.neuter_done, t.vaccine_done, t.dewormer_done, t.chip_done FROM pets p JOIN treatments t ON t.pet_id=p.id WHERE p.current_hospital_id=? AND p.status='treated' ORDER BY p.treatment_date DESC LIMIT 20", (org_id,)).fetchall()
    inventory = get_inventory(owner_id=org_id)
    return render_template('hospital/treatment.html', pending_pets=pending_pets, treated_pets=treated_pets,
                           inventory=inventory, role_config=ROLE_CONFIG)

@app.route('/hospital/material', methods=['GET', 'POST'])
@role_required(['hospital'])
def hospital_material():
    db = get_db()
    org_id = session['org_id']
    if request.method == 'POST':
        action = request.form.get('action', '')
        dist_id = request.form.get('dist_id')
        if action == 'receive_mat':
            dist = db.execute("SELECT * FROM material_distributions WHERE id=?", (dist_id,)).fetchone()
            db.execute("UPDATE material_distributions SET status='received', received_at=datetime('now','localtime') WHERE id=?", (dist_id,))
            db.execute('''INSERT INTO materials (type, batch_no, chip_start, chip_end, quantity, unit, location, owner_id, purchase_date)
                VALUES (?, ?, ?, ?, ?, ?, 'hospital', ?, date('now','localtime'))''',
                (dist['material_type'], dist['batch_no'], dist['chip_start'], dist['chip_end'], dist['quantity'],
                 '个' if dist['material_type'] == 'chip' else '支', org_id))
            mat_row = db.execute("SELECT id FROM materials WHERE owner_id=1 AND type=? AND quantity>=? ORDER BY id LIMIT 1",
                                (dist['material_type'], dist['quantity'])).fetchone()
            if mat_row:
                db.execute("UPDATE materials SET quantity=quantity-? WHERE id=?", (dist['quantity'], mat_row['id']))
            db.execute('''INSERT INTO material_ledger (type, action, quantity, from_location, to_location, from_owner_id, to_owner_id, reason, operator_id, operator_role)
                VALUES (?, 'distribute_receive', ?, 'shelter', 'hospital', 1, ?, '下发接收', ?, 'hospital')''',
                (dist['material_type'], dist['quantity'], org_id, session['user_id']))
            log_action('material_receive', f'接收物料{dist["material_type"]}{dist["quantity"]}单位')
            db.commit()
            flash('物料已确认入库', 'success')
        elif action == 'reject_mat':
            reason = request.form.get('reject_reason', '')
            db.execute("UPDATE material_distributions SET status='rejected', reject_reason=? WHERE id=?", (reason, dist_id))
            log_action('material_reject', f'驳回物料{dist_id}')
            db.commit()
            flash('已拒收物料', 'success')
        return redirect(url_for('hospital_material'))

    inventory = get_inventory(owner_id=org_id)
    pending_dist = db.execute("SELECT d.*, i.name as shelter_name FROM material_distributions d JOIN institutions i ON d.from_shelter_id=i.id WHERE d.to_hospital_id=? AND d.status='pending' ORDER BY d.created_at DESC", (org_id,)).fetchall()
    ledger = db.execute("SELECT * FROM material_ledger WHERE operator_id=? OR to_owner_id=? ORDER BY created_at DESC LIMIT 50", (session['user_id'], org_id)).fetchall()
    return render_template('hospital/material.html', inventory=inventory, pending_dist=pending_dist, ledger=ledger,
                           MATERIAL_TYPES=MATERIAL_TYPES, role_config=ROLE_CONFIG)

@app.route('/hospital/adoption', methods=['GET', 'POST'])
@role_required(['hospital'])
def hospital_adoption():
    db = get_db()
    org_id = session['org_id']
    if request.method == 'POST':
        pet_id = request.form.get('pet_id')
        name = request.form.get('name', '')
        desc = request.form.get('description', '')
        gender = request.form.get('gender', '')
        age = request.form.get('age', '')
        action = request.form.get('action', 'update')
        if action == 'update':
            desc = request.form.get('description', '')
            db.execute("UPDATE pets SET adoption_desc=?, gender=COALESCE(?, gender), age=COALESCE(?, age) WHERE id=?", (desc, gender or None, age or None, pet_id))
            db.execute("UPDATE pets SET status='pending_adoption' WHERE id=? AND status='treated'", (pet_id,))
            log_action('adoption_update', f'宠物{pet_id}资料更新上架领养大厅')
            db.commit()
            flash('领养资料已更新并上架领养大厅', 'success')
        elif action == 'confirm_adopted':
            pet = db.execute("SELECT adopter_id FROM pets WHERE id=?", (pet_id,)).fetchone()
            if not pet or not pet['adopter_id']:
                flash('该宠物尚未分配领养人，无法确认领出', 'error')
                return redirect(url_for('hospital_adoption'))
            db.execute("UPDATE pets SET status='adopted', adoption_date=COALESCE(adoption_date, datetime('now','localtime')) WHERE id=?", (pet_id,))
            db.execute("INSERT INTO messages (user_id, title, content, type) VALUES (?, '领养领出确认', '您已完成领宠手续，欢迎毛孩子回家！请记得按时回访打卡。', 'adoption')",
                       (pet['adopter_id'],))
            log_action('adoption_confirm', f'宠物{pet_id}领养领出确认')
            db.commit()
            flash('领养领出已确认', 'success')
        return redirect(url_for('hospital_adoption'))

    treated_pets = db.execute("SELECT * FROM pets WHERE current_hospital_id=? AND status IN ('treated','pending_adoption') ORDER BY treatment_date DESC", (org_id,)).fetchall()
    pickup_pets = db.execute("SELECT p.*, u.name as adopter_name, u.phone as adopter_phone FROM pets p JOIN users u ON p.adopter_id=u.id WHERE p.current_hospital_id=? AND p.status='pending_pickup' ORDER BY p.adoption_date DESC", (org_id,)).fetchall()
    adopted_pets = db.execute("SELECT p.*, u.name as adopter_name FROM pets p LEFT JOIN users u ON p.adopter_id=u.id WHERE p.current_hospital_id=? AND p.status='adopted' ORDER BY p.adoption_date DESC LIMIT 20", (org_id,)).fetchall()
    return render_template('hospital/adoption.html', treated_pets=treated_pets, pickup_pets=pickup_pets, adopted_pets=adopted_pets,
                           role_config=ROLE_CONFIG)

@app.route('/hospital/euthanasia', methods=['GET', 'POST'])
@role_required(['hospital'])
def hospital_euthanasia():
    db = get_db()
    org_id = session['org_id']
    if request.method == 'POST':
        pet_id = request.form.get('pet_id')
        reason = request.form.get('reason', '')
        db.execute("UPDATE pets SET status='euthanized', euthanasia_reason=?, euthanasia_date=datetime('now','localtime'), current_hospital_id=NULL WHERE id=?", (reason, pet_id))
        log_action('euthanasia', f'宠物{pet_id}安乐死，原因：{reason}')
        db.commit()
        flash('安乐死处置已登记', 'success')
        return redirect(url_for('hospital_euthanasia'))
    pets = db.execute("SELECT * FROM pets WHERE current_hospital_id=? AND status IN ('pending_treatment','treating','treated') ORDER BY intake_date DESC", (org_id,)).fetchall()
    euthanized = db.execute("SELECT p.* FROM pets p WHERE p.status='euthanized' ORDER BY p.euthanasia_date DESC LIMIT 20").fetchall()
    return render_template('hospital/euthanasia.html', pets=pets, euthanized=euthanized, role_config=ROLE_CONFIG)

@app.route('/adopter')
@role_required(['adopter'])
def adopter_hall():
    db = get_db()
    species = request.args.get('species', '')
    query = "SELECT p.*, i.name as hospital_name FROM pets p LEFT JOIN institutions i ON p.current_hospital_id=i.id WHERE p.status='pending_adoption'"
    params = []
    if species:
        query += " AND p.species=?"
        params.append(species)
    query += " ORDER BY p.treatment_date DESC"
    pets = db.execute(query, params).fetchall()
    unread = db.execute("SELECT COUNT(*) FROM messages WHERE user_id=? AND is_read=0", (session['user_id'],)).fetchone()[0]
    return render_template('adopter/adoption_hall.html', pets=pets, unread=unread, species=species,
                           role_config=ROLE_CONFIG)

@app.route('/adopter/apply/<int:pet_id>', methods=['GET', 'POST'])
@role_required(['adopter'])
def adopter_apply(pet_id):
    db = get_db()
    pet = db.execute("SELECT * FROM pets WHERE id=? AND status='pending_adoption'", (pet_id,)).fetchone()
    if not pet:
        flash('该宠物不可申请领养', 'error')
        return redirect(url_for('adopter_hall'))
    existing = db.execute("SELECT * FROM adoption_applications WHERE pet_id=? AND adopter_id=? AND status='pending'",
                          (pet_id, session['user_id'])).fetchone()
    if request.method == 'POST':
        if existing:
            flash('您已提交过申请，请勿重复提交', 'error')
            return redirect(url_for('adopter_pet_detail', pet_id=pet_id))
        if session.get('is_blacklisted'):
            flash('您已被列入黑名单，无法申请领养', 'error')
            return redirect(url_for('adopter_hall'))
        reason = request.form.get('reason', '')
        experience = request.form.get('experience', '')
        housing = request.form.get('housing', '')
        db.execute('''INSERT INTO adoption_applications (pet_id, adopter_id, reason, experience, housing)
            VALUES (?, ?, ?, ?, ?)''', (pet_id, session['user_id'], reason, experience, housing))
        db.execute("INSERT INTO messages (user_id, title, content, type) VALUES (?, '领养申请提交成功', '您的领养申请已提交，请等待工作人员审核', 'system')",
                   (session['user_id'],))
        log_action('adoption_apply', f'申请领养宠物{pet_id}')
        db.commit()
        flash('领养申请已提交，请等待审核', 'success')
        return redirect(url_for('adopter_my'))
    already_applied = existing is not None
    return render_template('adopter/apply.html', pet=pet, already_applied=already_applied,
                           PET_STATUS=PET_STATUS, role_config=ROLE_CONFIG)

@app.route('/adopter/pet/<int:pet_id>')
@role_required(['adopter'])
def adopter_pet_detail(pet_id):
    db = get_db()
    pet = db.execute("SELECT p.*, i.name as hospital_name, i.contact_phone as hospital_phone FROM pets p LEFT JOIN institutions i ON p.current_hospital_id=i.id WHERE p.id=?", (pet_id,)).fetchone()
    treatments = db.execute("SELECT * FROM treatments WHERE pet_id=? ORDER BY treated_at DESC", (pet_id,)).fetchall()
    return render_template('adopter/pet_detail.html', pet=pet, treatments=treatments, PET_STATUS=PET_STATUS,
                           role_config=ROLE_CONFIG)

@app.route('/adopter/my')
@role_required(['adopter'])
def adopter_my():
    db = get_db()
    my_pets = db.execute("SELECT p.*, i.name as hospital_name, i.contact_phone as hospital_phone FROM pets p LEFT JOIN institutions i ON p.current_hospital_id=i.id WHERE p.adopter_id=? AND p.status IN ('adopted','pending_pickup') ORDER BY p.adoption_date DESC", (session['user_id'],)).fetchall()
    applications = db.execute('''SELECT a.*, p.pet_code, p.species, p.color FROM adoption_applications a
        JOIN pets p ON a.pet_id=p.id WHERE a.adopter_id=? ORDER BY a.created_at DESC''', (session['user_id'],)).fetchall()
    return render_template('adopter/my_adoption.html', my_pets=my_pets, applications=applications,
                           PET_STATUS=PET_STATUS, role_config=ROLE_CONFIG)

@app.route('/adopter/checkin', methods=['GET', 'POST'])
@role_required(['adopter'])
def adopter_checkin():
    db = get_db()
    if request.method == 'POST':
        pet_id = request.form.get('pet_id')
        month = request.form.get('month', datetime.now().strftime('%Y-%m'))
        content = request.form.get('content', '')
        existing = db.execute("SELECT id FROM checkins WHERE pet_id=? AND adopter_id=? AND month=?",
                              (pet_id, session['user_id'], month)).fetchone()
        if existing:
            flash('本月已打卡', 'error')
        else:
            db.execute("INSERT INTO checkins (pet_id, adopter_id, month, content) VALUES (?, ?, ?, ?)",
                       (pet_id, session['user_id'], month, content))
            log_action('checkin', f'宠物{pet_id}{month}打卡')
            db.commit()
            flash('打卡成功，等待审核', 'success')
        return redirect(url_for('adopter_checkin'))
    my_pets = db.execute("SELECT * FROM pets WHERE adopter_id=? AND status='adopted'", (session['user_id'],)).fetchall()
    checkins = db.execute("SELECT c.*, p.pet_code FROM checkins c JOIN pets p ON c.pet_id=p.id WHERE c.adopter_id=? ORDER BY c.created_at DESC", (session['user_id'],)).fetchall()
    return render_template('adopter/checkin.html', my_pets=my_pets, checkins=checkins, role_config=ROLE_CONFIG)

@app.route('/adopter/messages')
@role_required(['adopter'])
def adopter_messages():
    db = get_db()
    db.execute("UPDATE messages SET is_read=1 WHERE user_id=?", (session['user_id'],))
    db.commit()
    messages = db.execute("SELECT * FROM messages WHERE user_id=? ORDER BY created_at DESC", (session['user_id'],)).fetchall()
    return render_template('adopter/messages.html', messages=messages, role_config=ROLE_CONFIG)

@app.route('/adopter/profile', methods=['GET', 'POST'])
@role_required(['adopter'])
def adopter_profile():
    db = get_db()
    if request.method == 'POST':
        name = request.form.get('name', '')
        phone = request.form.get('phone', '')
        db.execute("UPDATE users SET name=?, phone=? WHERE id=?", (name, phone, session['user_id']))
        session['name'] = name
        db.commit()
        flash('资料已更新', 'success')
        return redirect(url_for('adopter_profile'))
    user = db.execute("SELECT * FROM users WHERE id=?", (session['user_id'],)).fetchone()
    return render_template('adopter/profile.html', user=user, role_config=ROLE_CONFIG)

@app.route('/government')
@role_required(['government'])
def gov_dashboard():
    db = get_db()
    stats = get_counts()
    inv_shelter = get_inventory(owner_id=1)
    hospitals = db.execute("SELECT i.*, (SELECT COUNT(*) FROM pets WHERE current_hospital_id=i.id AND status IN ('pending_treatment','treating')) as treating_count FROM institutions i WHERE type='hospital' AND status=1").fetchall()
    districts = db.execute("SELECT district, COUNT(*) as cnt FROM pets p LEFT JOIN communities c ON p.community_id=c.id GROUP BY c.district").fetchall()
    alerts = []
    for h in hospitals:
        inv = get_inventory(owner_id=h['id'])
        if inv.get('vaccine', 0) < 10:
            alerts.append(f"{h['name']}疫苗库存不足")
        if inv.get('chip', 0) < 10:
            alerts.append(f"{h['name']}芯片库存不足")
    return render_template('government/dashboard.html', stats=stats, inv_shelter=inv_shelter, hospitals=hospitals,
                           districts=districts, alerts=alerts, role_config=ROLE_CONFIG)

@app.route('/government/institutions', methods=['GET', 'POST'])
@role_required(['government'])
def gov_institutions():
    db = get_db()
    if request.method == 'POST':
        action = request.form.get('action', '')
        if action == 'add_hospital':
            name = request.form.get('name', '')
            district = request.form.get('district', '')
            address = request.form.get('address', '')
            contact = request.form.get('contact_person', '')
            phone = request.form.get('contact_phone', '')
            db.execute("INSERT INTO institutions (type, name, district, address, contact_person, contact_phone) VALUES ('hospital', ?, ?, ?, ?, ?)",
                       (name, district, address, contact, phone))
            db.commit()
            flash('医院添加成功', 'success')
        elif action == 'toggle':
            inst_id = request.form.get('inst_id')
            inst = db.execute("SELECT status FROM institutions WHERE id=?", (inst_id,)).fetchone()
            new_status = 0 if inst['status'] == 1 else 1
            db.execute("UPDATE institutions SET status=? WHERE id=?", (new_status, inst_id))
            db.commit()
            flash('状态已更新', 'success')
        elif action == 'add_community':
            name = request.form.get('c_name', '')
            district = request.form.get('c_district', '')
            address = request.form.get('c_address', '')
            db.execute("INSERT INTO communities (name, district, address) VALUES (?, ?, ?)", (name, district, address))
            db.commit()
            flash('小区添加成功', 'success')
        return redirect(url_for('gov_institutions'))

    hospitals = db.execute("SELECT * FROM institutions WHERE type='hospital' ORDER BY id").fetchall()
    communities = db.execute("SELECT * FROM communities ORDER BY id DESC").fetchall()
    return render_template('government/institutions.html', hospitals=hospitals, communities=communities,
                           role_config=ROLE_CONFIG)

@app.route('/government/supervision')
@role_required(['government'])
def gov_supervision():
    db = get_db()
    status_filter = request.args.get('status', '')
    query = '''SELECT p.*, c.name as community_name, i.name as hospital_name, u.name as adopter_name
        FROM pets p LEFT JOIN communities c ON p.community_id=c.id
        LEFT JOIN institutions i ON p.current_hospital_id=i.id
        LEFT JOIN users u ON p.adopter_id=u.id WHERE 1=1'''
    params = []
    if status_filter:
        query += ' AND p.status=?'
        params.append(status_filter)
    query += ' ORDER BY p.intake_date DESC LIMIT 200'
    pets = db.execute(query, params).fetchall()
    return render_template('government/supervision.html', pets=pets, PET_STATUS=PET_STATUS, status_filter=status_filter,
                           role_config=ROLE_CONFIG)

@app.route('/government/material')
@role_required(['government'])
def gov_material():
    db = get_db()
    inv_shelter = get_inventory(owner_id=1)
    hospitals = db.execute("SELECT * FROM institutions WHERE type='hospital' AND status=1").fetchall()
    hospital_inv = []
    for h in hospitals:
        inv = get_inventory(owner_id=h['id'])
        hospital_inv.append({'hospital': h, 'inventory': inv})
    ledger = db.execute("SELECT * FROM material_ledger ORDER BY created_at DESC LIMIT 100").fetchall()
    return render_template('government/material.html', inv_shelter=inv_shelter, hospital_inv=hospital_inv,
                           ledger=ledger, MATERIAL_TYPES=MATERIAL_TYPES, role_config=ROLE_CONFIG)

@app.route('/government/ledger')
@role_required(['government'])
def gov_ledger():
    db = get_db()
    pets = db.execute("SELECT p.*, c.name as community_name, i.name as hospital_name, u.name as adopter_name FROM pets p LEFT JOIN communities c ON p.community_id=c.id LEFT JOIN institutions i ON p.current_hospital_id=i.id LEFT JOIN users u ON p.adopter_id=u.id ORDER BY p.intake_date DESC").fetchall()
    return render_template('government/ledger.html', pets=pets, PET_STATUS=PET_STATUS, role_config=ROLE_CONFIG)

@app.route('/api/stats')
def api_stats():
    db = get_db()
    return jsonify(get_counts())

@app.template_filter('fmt_dt')
def fmt_dt(value):
    if not value:
        return ''
    return str(value)

@app.template_filter('status_label')
def status_label(key):
    return PET_STATUS.get(key, key)

@app.context_processor
def inject_adopter_unread():
    if session.get('role') == 'adopter' and 'user_id' in session:
        db = get_db()
        unread = db.execute("SELECT COUNT(*) FROM messages WHERE user_id=? AND is_read=0", (session['user_id'],)).fetchone()[0]
        return {'unread': unread}
    return {}

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)
