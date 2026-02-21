#!/usr/bin/env python3
# app.py - ملف التشغيل الرئيسي (نسخة كاملة مع جميع الملفات)

from flask import Flask, render_template, request, redirect, session, jsonify
import json
import os
import shutil
import subprocess
import hashlib
import threading
import time
import requests
from datetime import datetime, timedelta
import signal
import psutil
import sys
import glob

# استيراد دوال friend_service
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import friend_service

app = Flask(__name__)
app.secret_key = "LONELY_SECRET_KEY_2024"

# المسارات
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LONELY_SOURCE_DIR = os.path.join(BASE_DIR, 'lonely')  # المصدر الأصلي
BOTS_STORAGE = os.path.join(BASE_DIR, 'bots_storage')
USERS_STORAGE = os.path.join(BOTS_STORAGE, 'users')
DATABASE_DIR = os.path.join(BASE_DIR, 'database')  # database خارج lonely
TEMPLATES_DIR = os.path.join(LONELY_SOURCE_DIR, 'templates')
STATIC_DIR = os.path.join(LONELY_SOURCE_DIR, 'static')

# إنشاء المجلدات المطلوبة
os.makedirs(BOTS_STORAGE, exist_ok=True)
os.makedirs(USERS_STORAGE, exist_ok=True)
os.makedirs(DATABASE_DIR, exist_ok=True)  # database خارج lonely
os.makedirs(TEMPLATES_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

# ملفات قاعدة البيانات
USERS_FILE = os.path.join(DATABASE_DIR, 'users.json')
BOTS_FILE = os.path.join(DATABASE_DIR, 'bots.json')
LINKS_FILE = os.path.join(DATABASE_DIR, 'links.json')
PLAYERS_FILE = os.path.join(DATABASE_DIR, 'players.json')

# ========== إعدادات API للأصدقاء ==========
FRIEND_API_URL = "http://localhost:5000"  # نفس السيرفر المحلي
# ===========================================

# ========== دوال مساعدة ==========

def hash_password(password):
    """تشفير كلمة المرور"""
    return hashlib.sha256(password.encode()).hexdigest()

def get_users():
    """جلب جميع المستخدمين"""
    if not os.path.exists(USERS_FILE):
        return []
    try:
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []

def save_users(users):
    """حفظ المستخدمين"""
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=4)

def get_bots():
    """جلب جميع البوتات"""
    if not os.path.exists(BOTS_FILE):
        return []
    try:
        with open(BOTS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []

def save_bots(bots):
    """حفظ البوتات"""
    with open(BOTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(bots, f, ensure_ascii=False, indent=4)

def get_links():
    """جلب جميع الروابط"""
    if not os.path.exists(LINKS_FILE):
        return []
    try:
        with open(LINKS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []

def save_links(links):
    """حفظ الروابط"""
    with open(LINKS_FILE, 'w', encoding='utf-8') as f:
        json.dump(links, f, ensure_ascii=False, indent=4)

def get_players():
    """جلب جميع اللاعبين"""
    if not os.path.exists(PLAYERS_FILE):
        return []
    try:
        with open(PLAYERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []

def save_players(players):
    """حفظ اللاعبين"""
    with open(PLAYERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(players, f, ensure_ascii=False, indent=4)

def get_player_info_from_api(uid):
    """جلب معلومات اللاعب من friend_service الحقيقي"""
    try:
        name, region, level = friend_service.get_player_info(uid)
        return {
            'name': name,
            'region': region,
            'level': level
        }
    except Exception as e:
        print(f"⚠️ خطأ في جلب معلومات اللاعب {uid}: {e}")
        return {'name': 'غير معروف', 'region': 'N/A', 'level': 'N/A'}

def send_friend_request_via_api(account_uid, account_password, target_uid):
    """إرسال طلب صداقة عبر friend_service الحقيقي"""
    try:
        # أولاً: جلب التوكن
        print(f"🔑 جاري جلب التوكن للحساب {account_uid}...")
        token = friend_service.fetch_jwt_token_direct(account_uid, account_password)
        
        if not token:
            return {
                'status': 'error', 
                'message': '❌ فشل جلب التوكن. تأكد من صحة بيانات الحساب'
            }
        
        print(f"✅ تم جلب التوكن بنجاح")
        
        # ثانياً: إرسال طلب الصداقة
        print(f"📤 جاري إرسال طلب صداقة إلى {target_uid}...")
        success, message = friend_service.send_friend_request(token, target_uid)
        
        # ثالثاً: جلب معلومات اللاعب
        player_info = get_player_info_from_api(target_uid)
        
        if success:
            return {
                'status': 'success',
                'message': message,
                'player_info': player_info
            }
        else:
            return {
                'status': 'error',
                'message': message,
                'player_info': player_info
            }
            
    except Exception as e:
        print(f"⚠️ خطأ في إرسال طلب الصداقة: {e}")
        return {
            'status': 'error', 
            'message': f'حدث خطأ: {str(e)}',
            'player_info': {'name': 'غير معروف', 'region': 'N/A', 'level': 'N/A'}
        }

def remove_friend_via_api(account_uid, account_password, target_uid):
    """حذف صديق عبر friend_service الحقيقي"""
    try:
        # أولاً: جلب التوكن
        print(f"🔑 جاري جلب التوكن للحساب {account_uid}...")
        token = friend_service.fetch_jwt_token_direct(account_uid, account_password)
        
        if not token:
            return {
                'status': 'error', 
                'message': '❌ فشل جلب التوكن. تأكد من صحة بيانات الحساب'
            }
        
        print(f"✅ تم جلب التوكن بنجاح")
        
        # ثانياً: حذف الصديق
        print(f"📤 جاري حذف الصديق {target_uid}...")
        success, message = friend_service.remove_friend(token, target_uid)
        
        # جلب معلومات اللاعب
        player_info = get_player_info_from_api(target_uid)
        
        if success:
            return {
                'status': 'success',
                'message': message,
                'player_info': player_info
            }
        else:
            return {
                'status': 'error',
                'message': message,
                'player_info': player_info
            }
            
    except Exception as e:
        print(f"⚠️ خطأ في حذف الصديق: {e}")
        return {
            'status': 'error', 
            'message': f'حدث خطأ: {str(e)}',
            'player_info': {'name': 'غير معروف', 'region': 'N/A', 'level': 'N/A'}
        }

def copy_entire_folder(src, dst):
    """نسخ مجلد كامل بكل محتوياته"""
    try:
        # إذا كان المجلد الوجهة موجوداً، احذفه أولاً
        if os.path.exists(dst):
            shutil.rmtree(dst)
        
        # نسخ المجلد بالكامل
        shutil.copytree(src, dst)
        print(f"✅ تم نسخ المجلد من {src} إلى {dst}")
        return True
    except Exception as e:
        print(f"❌ خطأ في نسخ المجلد: {e}")
        return False

def update_config_file(bot_path, uid, password, bot_name, display_name):
    """تحديث ملف config.json في مجلد البوت"""
    config_path = os.path.join(bot_path, 'config.json')
    try:
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        else:
            config = {}
        
        # تحديث بيانات الحساب
        if 'account' not in config:
            config['account'] = {}
        config['account']['uid'] = uid
        config['account']['password'] = password
        
        # تحديث بيانات البوت
        if 'bot' not in config:
            config['bot'] = {}
        config['bot']['name'] = bot_name
        config['bot']['display_name'] = display_name
        
        # حفظ الملف
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
        
        print(f"✅ تم تحديث ملف config.json للبوت {uid}")
        return True
    except Exception as e:
        print(f"❌ خطأ في تحديث config.json: {e}")
        return False

# ========== إنشاء مستخدم admin ==========

def create_admin_user():
    """إنشاء مستخدم admin بشكل مباشر"""
    
    # بيانات admin
    admin = {
        'id': 1,
        'username': 'Lonely',
        'password': hash_password('Lonely1213'),
        'max_bots': 999999,
        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'expiry_date': (datetime.now() + timedelta(days=36500)).strftime('%Y-%m-%d %H:%M:%S'),
        'is_admin': True,
        'telegram': '@lonely_20072'
    }
    
    # حفظ في ملف users.json
    save_users([admin])
    
    # إنشاء مجلد للأدمن
    admin_folder = os.path.join(USERS_STORAGE, "admin_Lonely")
    os.makedirs(admin_folder, exist_ok=True)
    
    # إنشاء ملفات أخرى فارغة إذا لم تكن موجودة
    if not os.path.exists(BOTS_FILE):
        save_bots([])
    if not os.path.exists(LINKS_FILE):
        save_links([])
    if not os.path.exists(PLAYERS_FILE):
        save_players([])
    
    print("="*50)
    print("✅ تم إنشاء مستخدم admin بنجاح")
    print("👤 اسم المستخدم: Lonely")
    print("🔑 كلمة المرور: 123")
    print("="*50)
    
    return admin

# التحقق من وجود مستخدم admin
def check_admin_exists():
    """التحقق من وجود مستخدم admin"""
    users = get_users()
    
    # إذا كان الملف فارغ أو لا يوجد مستخدمين
    if not users:
        print("📁 لا يوجد مستخدمين - جاري إنشاء admin...")
        create_admin_user()
        return True
    
    # البحث عن admin
    for user in users:
        if user.get('username') == 'Lonely' and user.get('is_admin'):
            print("="*50)
            print("✅ مستخدم admin موجود بالفعل")
            print("👤 اسم المستخدم: Lonely")
            print("🔑 كلمة المرور: 123")
            print("="*50)
            return True
    
    # إذا لم يتم العثور على admin
    print("📁 لا يوجد مستخدم admin - جاري الإضافة...")
    new_admin = {
        'id': max([u['id'] for u in users], default=0) + 1,
        'username': 'Lonely',
        'password': hash_password('123'),
        'max_bots': 999999,
        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'expiry_date': (datetime.now() + timedelta(days=36500)).strftime('%Y-%m-%d %H:%M:%S'),
        'is_admin': True,
        'telegram': '@lonely_20072'
    }
    users.append(new_admin)
    save_users(users)
    
    # إنشاء مجلد للأدمن
    admin_folder = os.path.join(USERS_STORAGE, "admin_Lonely")
    os.makedirs(admin_folder, exist_ok=True)
    
    print("="*50)
    print("✅ تم إضافة مستخدم admin")
    print("👤 اسم المستخدم: Lonely")
    print("🔑 كلمة المرور: 123")
    print("="*50)
    
    return True

# تنفيذ التحقق عند بدء التشغيل
check_admin_exists()

# ========== Routes ==========

@app.route('/')
def index():
    """الصفحة الرئيسية"""
    if 'user_id' in session:
        return redirect('/admin' if session.get('is_admin') else '/dashboard')
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    """تسجيل الدخول"""
    # جلب البيانات من النموذج
    username = request.form['username'].strip()
    password = request.form['password'].strip()
    
    print(f"🔍 محاولة دخول: '{username}'")
    
    # تشفير كلمة المرور
    hashed_password = hash_password(password)
    
    # جلب المستخدمين
    users = get_users()
    
    # البحث عن المستخدم
    user = None
    for u in users:
        if u['username'] == username and u['password'] == hashed_password:
            user = u
            break
    
    if user:
        # تسجيل الدخول ناجح
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['is_admin'] = user.get('is_admin', False)
        
        print(f"✅ دخول ناجح: {username} (admin: {user.get('is_admin')})")
        
        # التوجيه حسب نوع المستخدم
        if user.get('is_admin'):
            return redirect('/admin')
        else:
            return redirect('/dashboard')
    else:
        # تسجيل الدخول فاشل
        print(f"❌ دخول فاشل: {username}")
        return render_template('login.html', error='خطأ في اسم المستخدم أو كلمة المرور')

@app.route('/logout')
def logout():
    """تسجيل الخروج"""
    session.clear()
    return redirect('/')

@app.route('/dashboard')
def dashboard():
    """لوحة تحكم المستخدم العادي"""
    if 'user_id' not in session:
        return redirect('/')
    
    if session.get('is_admin'):
        return redirect('/admin')
    
    user_id = session['user_id']
    users = get_users()
    user = next((u for u in users if u['id'] == user_id), None)
    
    if not user:
        session.clear()
        return redirect('/')
    
    bots = [b for b in get_bots() if b['user_id'] == user_id]
    links = get_links()
    
    return render_template('dashboard.html', user=user, bots=bots, links=links)

@app.route('/admin')
def admin():
    """لوحة تحكم الأدمن"""
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect('/')
    
    users = get_users()
    bots = get_bots()
    links = get_links()
    
    return render_template('admin.html', users=users, bots=bots, links=links, now=datetime.now())

@app.route('/create_user', methods=['POST'])
def create_user():
    """إنشاء مستخدم جديد (للأدمن فقط)"""
    if 'user_id' not in session or not session.get('is_admin'):
        return jsonify({'success': False, 'error': 'Unauthorized'})
    
    data = request.json
    users = get_users()
    
    # إنشاء معرف جديد
    new_id = max([u['id'] for u in users], default=0) + 1
    
    # إنشاء المستخدم
    user = {
        'id': new_id,
        'username': data['username'],
        'password': hash_password(data['password']),
        'max_bots': int(data['max_bots']),
        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'expiry_date': (datetime.now() + timedelta(days=int(data['days']))).strftime('%Y-%m-%d %H:%M:%S'),
        'is_admin': False,
        'telegram': data.get('telegram', '')
    }
    
    users.append(user)
    save_users(users)
    
    # إنشاء مجلد للمستخدم
    user_folder = os.path.join(USERS_STORAGE, f"user_{new_id}_{data['username']}")
    os.makedirs(user_folder, exist_ok=True)
    os.makedirs(os.path.join(user_folder, 'bots'), exist_ok=True)
    
    print(f"✅ تم إنشاء مستخدم جديد: {data['username']}")
    return jsonify({'success': True})

@app.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    """حذف مستخدم (للأدمن فقط)"""
    if 'user_id' not in session or not session.get('is_admin'):
        return jsonify({'success': False, 'error': 'Unauthorized'})
    
    users = get_users()
    
    # منع حذف الأدمن
    user_to_delete = next((u for u in users if u['id'] == user_id), None)
    if user_to_delete and user_to_delete.get('is_admin'):
        return jsonify({'success': False, 'error': 'لا يمكن حذف حساب الأدمن'})
    
    # حذف مجلد المستخدم
    if user_to_delete:
        user_folder = os.path.join(USERS_STORAGE, f"user_{user_id}_{user_to_delete['username']}")
        if os.path.exists(user_folder):
            shutil.rmtree(user_folder)
    
    # حذف بوتات المستخدم
    bots = get_bots()
    bots = [b for b in bots if b['user_id'] != user_id]
    save_bots(bots)
    
    # حذف المستخدم
    users = [u for u in users if u['id'] != user_id]
    save_users(users)
    
    print(f"✅ تم حذف المستخدم: ID {user_id}")
    return jsonify({'success': True})

@app.route('/create_bot')
def create_bot_page():
    """صفحة إنشاء بوت جديد"""
    if 'user_id' not in session or session.get('is_admin'):
        return redirect('/')
    return render_template('create_bot.html')

@app.route('/create_bot', methods=['POST'])
def create_bot():
    """إنشاء بوت جديد - نسخ مجلد lonely بالكامل"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'})
    
    data = request.json
    user_id = session['user_id']
    
    users = get_users()
    user = next((u for u in users if u['id'] == user_id), None)
    
    if not user:
        return jsonify({'success': False, 'error': 'User not found'})
    
    # التحقق من عدد البوتات
    user_bots = len([b for b in get_bots() if b['user_id'] == user_id])
    if user_bots >= user['max_bots']:
        return jsonify({'success': False, 'error': '❌ لقد وصلت للحد الأقصى'})
    
    bot_uid = data['uid']
    
    # مسار البوت الجديد
    user_folder = os.path.join(USERS_STORAGE, f"user_{user_id}_{user['username']}")
    bots_folder = os.path.join(user_folder, 'bots')
    bot_path = os.path.join(bots_folder, bot_uid)
    
    # التحقق من وجود البوت مسبقاً
    if os.path.exists(bot_path):
        return jsonify({'success': False, 'error': '❌ هذا الأيدي مستخدم'})
    
    # التحقق من وجود مجلد المصدر
    if not os.path.exists(LONELY_SOURCE_DIR):
        return jsonify({'success': False, 'error': '❌ مجلد lonely غير موجود في المسار المحدد'})
    
    # نسخ مجلد lonely بالكامل إلى مسار البوت الجديد
    print(f"📁 جاري نسخ مجلد lonely من {LONELY_SOURCE_DIR} إلى {bot_path}")
    copy_success = copy_entire_folder(LONELY_SOURCE_DIR, bot_path)
    
    if not copy_success:
        return jsonify({'success': False, 'error': '❌ فشل نسخ ملفات البوت'})
    
    # تحديث ملف config.json ببيانات المستخدم
    config_updated = update_config_file(
        bot_path, 
        data['uid'], 
        data['password'], 
        data['bot_name'], 
        data['display_name']
    )
    
    if not config_updated:
        # إذا فشل تحديث config، نستمر لكن مع تحذير
        print("⚠️ تحذير: فشل تحديث config.json، سيتم استخدام القيم الافتراضية")
    
    # تسجيل البوت في قاعدة البيانات
    bots = get_bots()
    new_bot = {
        'id': len(bots) + 1,
        'user_id': user_id,
        'uid': data['uid'],
        'password': data['password'],
        'name': data['bot_name'],
        'display_name': data['display_name'],
        'status': 'stopped',
        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'pid': None
    }
    bots.append(new_bot)
    save_bots(bots)
    
    print(f"✅ تم إنشاء بوت جديد للمستخدم {user['username']} بنجاح")
    return jsonify({'success': True, 'bot': new_bot})

@app.route('/bot/<int:bot_id>')
def bot_details(bot_id):
    """صفحة تفاصيل البوت"""
    if 'user_id' not in session:
        return redirect('/')
    
    bots = get_bots()
    bot = next((b for b in bots if b['id'] == bot_id), None)
    
    if not bot or (bot['user_id'] != session['user_id'] and not session.get('is_admin')):
        return redirect('/dashboard')
    
    players = [p for p in get_players() if p['bot_uid'] == bot['uid']]
    
    return render_template('bot_details.html', bot=bot, players=players)

@app.route('/bot_action', methods=['POST'])
def bot_action():
    """التحكم في البوت (تشغيل/إيقاف/إعادة)"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'})
    
    data = request.json
    bot_id = data['bot_id']
    action = data['action']
    
    bots = get_bots()
    bot = next((b for b in bots if b['id'] == bot_id), None)
    
    if not bot or (bot['user_id'] != session['user_id'] and not session.get('is_admin')):
        return jsonify({'success': False, 'error': 'Unauthorized'})
    
    # الحصول على مسار البوت
    users = get_users()
    user = next((u for u in users if u['id'] == bot['user_id']), None)
    
    if user:
        bot_path = os.path.join(USERS_STORAGE, f"user_{user['id']}_{user['username']}", 'bots', bot['uid'])
    else:
        return jsonify({'success': False, 'error': 'المستخدم غير موجود'})
    
    # التحقق من وجود ملف main.py
    main_file = os.path.join(bot_path, 'main.py')
    if not os.path.exists(main_file):
        return jsonify({'success': False, 'error': 'ملف main.py غير موجود في مجلد البوت'})
    
    if action == 'start':
        try:
            # تشغيل البوت في عملية منفصلة
            process = subprocess.Popen(
                [sys.executable, 'main.py'],
                cwd=bot_path,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            
            time.sleep(2)  # انتظار قليلاً للتأكد من بدء التشغيل
            
            if psutil.pid_exists(process.pid):
                bot['status'] = 'running'
                bot['pid'] = process.pid
                message = '✅ تم تشغيل البوت بنجاح'
            else:
                return jsonify({'success': False, 'error': '❌ فشل تشغيل البوت'})
                
        except Exception as e:
            return jsonify({'success': False, 'error': f'❌ خطأ: {str(e)}'})
    
    elif action == 'stop':
        if bot['pid']:
            try:
                # إنهاء العملية وجميع عملياتها الفرعية
                parent = psutil.Process(bot['pid'])
                for child in parent.children(recursive=True):
                    child.terminate()
                parent.terminate()
                
                # انتظار قليلاً للتأكد من الإنهاء
                gone, alive = psutil.wait_procs([parent], timeout=3)
                for p in alive:
                    p.kill()
                    
                message = '✅ تم إيقاف البوت بنجاح'
            except psutil.NoSuchProcess:
                message = '✅ البوت متوقف بالفعل'
            except Exception as e:
                try:
                    os.kill(bot['pid'], signal.SIGTERM)
                    message = '✅ تم إيقاف البوت بنجاح'
                except:
                    message = '✅ البوت متوقف بالفعل'
        else:
            message = '✅ البوت متوقف بالفعل'
        
        bot['status'] = 'stopped'
        bot['pid'] = None
    
    elif action == 'restart':
        # إيقاف البوت أولاً
        if bot['pid']:
            try:
                parent = psutil.Process(bot['pid'])
                for child in parent.children(recursive=True):
                    child.terminate()
                parent.terminate()
            except:
                try:
                    os.kill(bot['pid'], signal.SIGTERM)
                except:
                    pass
        
        # تشغيل البوت مرة أخرى
        try:
            process = subprocess.Popen(
                [sys.executable, 'main.py'],
                cwd=bot_path,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            
            time.sleep(2)
            
            if psutil.pid_exists(process.pid):
                bot['status'] = 'running'
                bot['pid'] = process.pid
                message = '✅ تم إعادة تشغيل البوت بنجاح'
            else:
                bot['status'] = 'stopped'
                bot['pid'] = None
                message = '❌ فشل إعادة تشغيل البوت'
        except:
            bot['status'] = 'stopped'
            bot['pid'] = None
            message = '❌ فشل إعادة تشغيل البوت'
    
    save_bots(bots)
    return jsonify({'success': True, 'status': bot['status'], 'message': message})

@app.route('/delete_bot/<int:bot_id>', methods=['POST'])
def delete_bot(bot_id):
    """حذف بوت"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'})
    
    bots = get_bots()
    bot = next((b for b in bots if b['id'] == bot_id), None)
    
    if not bot or (bot['user_id'] != session['user_id'] and not session.get('is_admin')):
        return jsonify({'success': False, 'error': 'Unauthorized'})
    
    # إيقاف البوت إذا كان يعمل
    if bot['pid']:
        try:
            parent = psutil.Process(bot['pid'])
            for child in parent.children(recursive=True):
                child.terminate()
            parent.terminate()
        except:
            try:
                os.kill(bot['pid'], signal.SIGTERM)
            except:
                pass
    
    # حذف مجلد البوت بالكامل
    users = get_users()
    user = next((u for u in users if u['id'] == bot['user_id']), None)
    
    if user:
        bot_path = os.path.join(USERS_STORAGE, f"user_{user['id']}_{user['username']}", 'bots', bot['uid'])
        if os.path.exists(bot_path):
            shutil.rmtree(bot_path)
            print(f"✅ تم حذف مجلد البوت: {bot_path}")
    
    # حذف اللاعبين المرتبطين بالبوت
    players = get_players()
    players = [p for p in players if p['bot_uid'] != bot['uid']]
    save_players(players)
    
    # حذف البوت من قاعدة البيانات
    bots = [b for b in bots if b['id'] != bot_id]
    save_bots(bots)
    
    return jsonify({'success': True, 'message': '✅ تم حذف البوت بنجاح'})

@app.route('/add_link', methods=['POST'])
def add_link():
    """إضافة رابط جديد (للأدمن فقط)"""
    if 'user_id' not in session or not session.get('is_admin'):
        return jsonify({'success': False, 'error': 'Unauthorized'})
    
    data = request.json
    links = get_links()
    
    new_link = {
        'id': len(links) + 1,
        'name': data['name'],
        'url': data['url'],
        'icon': data.get('icon', 'fas fa-link'),
        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    links.append(new_link)
    save_links(links)
    
    return jsonify({'success': True})

@app.route('/delete_link/<int:link_id>', methods=['POST'])
def delete_link(link_id):
    """حذف رابط (للأدمن فقط)"""
    if 'user_id' not in session or not session.get('is_admin'):
        return jsonify({'success': False, 'error': 'Unauthorized'})
    
    links = get_links()
    links = [l for l in links if l['id'] != link_id]
    save_links(links)
    
    return jsonify({'success': True})

@app.route('/add_player', methods=['POST'])
def add_player():
    """إضافة لاعب إلى بوت مع التحقق من النتيجة الحقيقية"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'})
    
    data = request.json
    bot_id = data['bot_id']
    player_uid = data['player_uid']
    duration = data['duration']
    
    bots = get_bots()
    bot = next((b for b in bots if b['id'] == bot_id), None)
    
    if not bot or bot['user_id'] != session['user_id']:
        return jsonify({'success': False, 'error': 'Unauthorized'})
    
    # حساب المدة
    if duration.endswith('d'):
        days = int(duration[:-1])
        expiry = datetime.now() + timedelta(days=days)
    elif duration.endswith('h'):
        hours = int(duration[:-1])
        expiry = datetime.now() + timedelta(hours=hours)
    else:
        return jsonify({'success': False, 'error': 'صيغة خاطئة استخدم d للأيام أو h للساعات'})
    
    # إرسال طلب الصداقة عبر friend_service الحقيقي
    print(f"📤 جاري إرسال طلب صداقة إلى {player_uid} باستخدام حساب {bot['uid']}")
    result = send_friend_request_via_api(bot['uid'], bot['password'], player_uid)
    
    # التحقق من النتيجة الحقيقية
    if result.get('status') == 'success':
        # جلب معلومات اللاعب
        player_info = result.get('player_info', {})
        player_name = player_info.get('name', 'غير معروف')
        
        # إضافة اللاعب إلى قاعدة البيانات
        players = get_players()
        new_player = {
            'id': len(players) + 1,
            'bot_uid': bot['uid'],
            'bot_id': bot_id,
            'uid': player_uid,
            'name': player_name,
            'level': player_info.get('level', 'N/A'),
            'region': player_info.get('region', 'N/A'),
            'added_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'expiry_date': expiry.strftime('%Y-%m-%d %H:%M:%S'),
            'duration': duration,
            'status': 'added'
        }
        players.append(new_player)
        save_players(players)
        
        return jsonify({
            'success': True,
            'player': new_player,
            'message': f'✅ {result.get("message")} - {player_name}',
            'api_response': result
        })
    else:
        # فشلت الإضافة - نعرض رسالة الخطأ الحقيقية
        error_message = result.get('message', 'فشل إرسال طلب الصداقة')
        player_info = result.get('player_info', {})
        player_name = player_info.get('name', player_uid)
        
        return jsonify({
            'success': False,
            'error': f'❌ {error_message}',
            'player_name': player_name,
            'api_response': result
        })

@app.route('/remove_player', methods=['POST'])
def remove_player():
    """إزالة لاعب من بوت مع التحقق من النتيجة الحقيقية"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'})
    
    data = request.json
    player_id = data['player_id']
    
    players = get_players()
    player = next((p for p in players if p['id'] == player_id), None)
    
    if not player:
        return jsonify({'success': False, 'error': 'اللاعب غير موجود'})
    
    bots = get_bots()
    bot = next((b for b in bots if b['uid'] == player['bot_uid']), None)
    
    if not bot or bot['user_id'] != session['user_id']:
        return jsonify({'success': False, 'error': 'Unauthorized'})
    
    player_name = player['name']
    player_uid = player['uid']
    
    # إرسال طلب الحذف عبر friend_service الحقيقي
    print(f"📤 جاري إرسال طلب حذف {player_uid} باستخدام حساب {bot['uid']}")
    result = remove_friend_via_api(bot['uid'], bot['password'], player_uid)
    
    # التحقق من النتيجة الحقيقية
    if result.get('status') == 'success':
        # حذف اللاعب من قاعدة البيانات
        players = [p for p in players if p['id'] != player_id]
        save_players(players)
        
        return jsonify({
            'success': True,
            'message': f'✅ {result.get("message")} - {player_name}',
            'api_response': result
        })
    else:
        # فشل الحذف - نعرض رسالة الخطأ الحقيقية
        error_message = result.get('message', 'فشل حذف اللاعب')
        
        # نتحقق إذا كان اللاعب غير موجود أصلاً (يمكن حذفه من قاعدة البيانات)
        if "غير موجود" in error_message.lower() or "not found" in error_message.lower():
            # حذف اللاعب من قاعدة البيانات على أي حال
            players = [p for p in players if p['id'] != player_id]
            save_players(players)
            return jsonify({
                'success': True,
                'message': f'✅ تم حذف {player_name} من القاعدة (اللاعب غير موجود في قائمة الأصدقاء)',
                'api_response': result
            })
        
        return jsonify({
            'success': False,
            'error': f'❌ {error_message}',
            'player_name': player_name,
            'api_response': result
        })

@app.route('/check_player_status', methods=['POST'])
def check_player_status():
    """التحقق من حالة لاعب (مضاف أم لا)"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'})
    
    data = request.json
    bot_id = data['bot_id']
    player_uid = data['player_uid']
    
    bots = get_bots()
    bot = next((b for b in bots if b['id'] == bot_id), None)
    
    if not bot or bot['user_id'] != session['user_id']:
        return jsonify({'success': False, 'error': 'Unauthorized'})
    
    # هنا يمكن إضافة API للتحقق من حالة الصداقة
    # حالياً نتحقق فقط من وجوده في قاعدة البيانات المحلية
    players = get_players()
    existing = next((p for p in players if p['bot_uid'] == bot['uid'] and p['uid'] == player_uid), None)
    
    return jsonify({
        'success': True,
        'is_added': existing is not None,
        'player': existing
    })

@app.route('/bulk_add', methods=['POST'])
def bulk_add():
    """إضافة عدة لاعبين دفعة واحدة"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'})
    
    data = request.json
    bot_id = data['bot_id']
    players_list = data['players']  # قائمة باللاعبين
    duration = data['duration']
    
    bots = get_bots()
    bot = next((b for b in bots if b['id'] == bot_id), None)
    
    if not bot or bot['user_id'] != session['user_id']:
        return jsonify({'success': False, 'error': 'Unauthorized'})
    
    # حساب المدة
    if duration.endswith('d'):
        days = int(duration[:-1])
        expiry = datetime.now() + timedelta(days=days)
    elif duration.endswith('h'):
        hours = int(duration[:-1])
        expiry = datetime.now() + timedelta(hours=hours)
    else:
        return jsonify({'success': False, 'error': 'صيغة خاطئة'})
    
    added_players = []
    failed_players = []
    
    for player_uid in players_list:
        try:
            # إرسال طلب الصداقة الحقيقي
            result = send_friend_request_via_api(bot['uid'], bot['password'], player_uid)
            player_info = result.get('player_info', {})
            player_name = player_info.get('name', player_uid)
            
            if result.get('status') == 'success':
                # إضافة اللاعب
                players = get_players()
                new_player = {
                    'id': len(players) + 1,
                    'bot_uid': bot['uid'],
                    'bot_id': bot_id,
                    'uid': player_uid,
                    'name': player_name,
                    'level': player_info.get('level', 'N/A'),
                    'region': player_info.get('region', 'N/A'),
                    'added_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'expiry_date': expiry.strftime('%Y-%m-%d %H:%M:%S'),
                    'duration': duration,
                    'status': 'added'
                }
                players.append(new_player)
                save_players(players)
                added_players.append({'uid': player_uid, 'name': player_name})
            else:
                failed_players.append({
                    'uid': player_uid, 
                    'name': player_name,
                    'error': result.get('message', 'فشل الإضافة')
                })
                
        except Exception as e:
            failed_players.append({'uid': player_uid, 'name': 'غير معروف', 'error': str(e)})
    
    return jsonify({
        'success': True,
        'added': added_players,
        'failed': failed_players,
        'message': f'✅ تمت إضافة {len(added_players)} لاعب، فشل {len(failed_players)}'
    })

@app.route('/bulk_remove', methods=['POST'])
def bulk_remove():
    """إزالة عدة لاعبين دفعة واحدة"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'})
    
    data = request.json
    bot_id = data['bot_id']
    player_ids = data['player_ids']  # قائمة بمعرفات اللاعبين في قاعدة البيانات
    
    bots = get_bots()
    bot = next((b for b in bots if b['id'] == bot_id), None)
    
    if not bot or bot['user_id'] != session['user_id']:
        return jsonify({'success': False, 'error': 'Unauthorized'})
    
    players = get_players()
    removed_players = []
    failed_players = []
    
    for player_id in player_ids:
        player = next((p for p in players if p['id'] == player_id), None)
        if not player:
            continue
        
        # إرسال طلب الحذف الحقيقي
        result = remove_friend_via_api(bot['uid'], bot['password'], player['uid'])
        
        if result.get('status') == 'success' or "غير موجود" in result.get('message', '').lower():
            # حذف اللاعب من قاعدة البيانات
            players = [p for p in players if p['id'] != player_id]
            save_players(players)
            removed_players.append({'uid': player['uid'], 'name': player['name']})
        else:
            failed_players.append({
                'uid': player['uid'], 
                'name': player['name'],
                'error': result.get('message', 'فشل الحذف')
            })
    
    return jsonify({
        'success': True,
        'removed': removed_players,
        'failed': failed_players,
        'message': f'✅ تم حذف {len(removed_players)} لاعب، فشل {len(failed_players)}'
    })

@app.route('/player_info/<player_uid>', methods=['GET'])
def get_player_info_route(player_uid):
    """الحصول على معلومات لاعب من friend_service الحقيقي"""
    try:
        name, region, level = friend_service.get_player_info(player_uid)
        return jsonify({
            'success': True,
            'name': name,
            'region': region,
            'level': level,
            'uid': player_uid
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'uid': player_uid
        })

# ========== مسارات API (محذوفة لأننا نستخدم friend_service مباشرة) ==========
# لكن سنبقيها للتوافق إذا احتاجها أحد

@app.route('/friend/add', methods=['GET'])
def friend_add_api():
    """رابط إضافة لاعب (API للتوافق مع الإصدارات القديمة)"""
    account_id = request.args.get('uid')
    account_password = request.args.get('password')
    target_id = request.args.get('target')
    
    if not all([account_id, account_password, target_id]):
        return jsonify({"status": "error", "message": "معلمات ناقصة"})
    
    # استخدام friend_service الحقيقي
    result = send_friend_request_via_api(account_id, account_password, target_id)
    
    return jsonify({
        "status": result.get('status', 'error'),
        "message": result.get('message', ''),
        "player_info": result.get('player_info', {})
    })

@app.route('/friend/remove', methods=['GET'])
def friend_remove_api():
    """رابط إزالة لاعب (API للتوافق مع الإصدارات القديمة)"""
    account_id = request.args.get('uid')
    account_password = request.args.get('password')
    target_id = request.args.get('target')
    
    if not all([account_id, account_password, target_id]):
        return jsonify({"status": "error", "message": "معلمات ناقصة"})
    
    # استخدام friend_service الحقيقي
    result = remove_friend_via_api(account_id, account_password, target_id)
    
    return jsonify({
        "status": result.get('status', 'error'),
        "message": result.get('message', ''),
        "player_info": result.get('player_info', {})
    })

@app.route('/friend/info', methods=['GET'])
def friend_info_api():
    """رابط معلومات اللاعب (API للتوافق مع الإصدارات القديمة)"""
    target_id = request.args.get('target')
    
    if not target_id:
        return jsonify({"status": "error", "message": "معلمات ناقصة"})
    
    # استخدام friend_service الحقيقي
    name, region, level = friend_service.get_player_info(target_id)
    
    return jsonify({
        "status": "success",
        "player_info": {
            "name": name,
            "id": target_id,
            "level": level,
            "region": region
        }
    })

@app.route('/friend/token', methods=['GET'])
def friend_token_api():
    """رابط جلب التوكن (API للتوافق مع الإصدارات القديمة)"""
    account_id = request.args.get('uid')
    account_password = request.args.get('password')
    
    if not all([account_id, account_password]):
        return jsonify({"status": "error", "message": "معلمات ناقصة"})
    
    token = friend_service.fetch_jwt_token_direct(account_id, account_password)
    
    if token:
        return jsonify({
            "status": "success",
            "token": token,
            "message": "✅ تم جلب التوكن بنجاح"
        })
    else:
        return jsonify({
            "status": "error",
            "message": "❌ فشل جلب التوكن. تأكد من صحة بيانات الحساب"
        })

@app.route('/friend/test', methods=['GET'])
def friend_test_api():
    """رابط اختبار"""
    return jsonify({
        "status": "success",
        "message": "خدمة الأصدقاء تعمل بنجاح",
        "version": "OB52",
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/status', methods=['GET'])
def api_status():
    """حالة جميع الـ APIs"""
    return jsonify({
        "status": "success",
        "message": "جميع الخدمات تعمل مع friend_service الحقيقي",
        "endpoints": {
            "friend_add": "/friend/add?uid=ID&password=PASS&target=PLAYER",
            "friend_remove": "/friend/remove?uid=ID&password=PASS&target=PLAYER",
            "friend_info": "/friend/info?target=PLAYER",
            "friend_token": "/friend/token?uid=ID&password=PASS",
            "friend_test": "/friend/test"
        },
        "timestamp": datetime.now().isoformat()
    })

if __name__ == '__main__':
    print("="*70)
    print("🚀 Lonely Bot Manager Starting...")
    print("="*70)
    print("📁 Base Directory:", BASE_DIR)
    print("📁 Database Directory:", DATABASE_DIR)
    print("📁 Lonely Source Directory:", LONELY_SOURCE_DIR)
    print("📁 Bots Storage Directory:", USERS_STORAGE)
    print("="*70)
    print("👤 Admin user: Lonely / 123")
    print("="*70)
    print("📡 باستخدام friend_service الحقيقي:")
    print("   ➤ جلب التوكنات مباشرة من Garena")
    print("   ➤ إرسال طلبات الصداقة الحقيقية")
    print("   ➤ حذف الأصدقاء الحقيقي")
    print("   ➤ عرض أسماء اللاعبين الحقيقية")
    print("   ➤ عرض رسائل الخطأ الحقيقية من السيرفر")
    print("="*70)
    print("✅ Bot creation will copy entire lonely folder with all files")
    print("✅ Player add/remove with REAL status verification")
    print("✅ REAL error messages shown to users")
    print("="*70)
    
    # التحقق من وجود مجلد lonely
    if not os.path.exists(LONELY_SOURCE_DIR):
        print("⚠️ تحذير: مجلد 'lonely' غير موجود في المسار:", LONELY_SOURCE_DIR)
        print("⚠️ يرجى التأكد من وجود المجلد قبل إنشاء أي بوت")
    else:
        # عرض محتويات مجلد lonely
        files = os.listdir(LONELY_SOURCE_DIR)
        print(f"📁 مجلد 'lonely' موجود ويحتوي على {len(files)} عنصر")
    
    print("="*70)
    
    # اختبار friend_service
    print("🧪 اختبار friend_service...")
    try:
        test_name, test_region, test_level = friend_service.get_player_info("123456789")
        print(f"✅ friend_service يعمل بشكل صحيح - مثال لاعب: {test_name}")
    except Exception as e:
        print(f"⚠️ تحذير: friend_service قد لا يعمل بشكل كامل: {e}")
    
    print("="*70)
    
    # تشغيل التطبيق
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)