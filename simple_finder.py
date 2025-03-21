import os
import sqlite3
import logging
from flask import Flask, request, render_template_string, jsonify
import json
import random
import requests
import io
import math

# 設置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('LicensePlatePrimeFinder')

app = Flask(__name__)

# PrimesDB 相關常量和函數
PRIMESDB_URL = "https://github.com/pekesoft/PrimesDB/raw/main/PrimesDB/0000.pdb"
PRIMESDB_CACHE_FILE = "primesdb_cache.bin"
primesdb_data = None

def download_primesdb():
    """下載 PrimesDB 數據文件"""
    global primesdb_data
    try:
        # 首先檢查是否有本地緩存
        if os.path.exists(PRIMESDB_CACHE_FILE):
            logger.info(f"從本地緩存加載 PrimesDB: {PRIMESDB_CACHE_FILE}")
            with open(PRIMESDB_CACHE_FILE, 'rb') as f:
                primesdb_data = f.read()
            return True
        
        # 如果沒有本地緩存，從 GitHub 下載
        logger.info(f"從 GitHub 下載 PrimesDB: {PRIMESDB_URL}")
        response = requests.get(PRIMESDB_URL)
        if response.status_code == 200:
            primesdb_data = response.content
            # 保存到本地緩存
            with open(PRIMESDB_CACHE_FILE, 'wb') as f:
                f.write(primesdb_data)
            logger.info(f"PrimesDB 下載成功，大小: {len(primesdb_data)} 字節")
            return True
        else:
            logger.error(f"下載 PrimesDB 失敗: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"下載 PrimesDB 時出錯: {e}")
        return False

def is_prime_primesdb(number):
    """使用 PrimesDB 檢查一個數字是否為質數"""
    global primesdb_data
    
    # 如果數據未加載，嘗試加載
    if primesdb_data is None:
        if not download_primesdb():
            # 如果無法加載 PrimesDB，回退到傳統方法
            return is_prime(number)
    
    # 使用 PrimesDB 算法檢查質數
    # 首先檢查基本情況
    if number < 2:
        return False
    if number == 2 or number == 3 or number == 5 or number == 7:
        return True
    if number % 2 == 0 or number % 3 == 0 or number % 5 == 0:
        return False
    
    # 只檢查末尾為 1, 3, 7, 9 的數字
    last_digit = number % 10
    if last_digit not in [1, 3, 7, 9]:
        return False
    
    # 計算 PrimesDB 中的位置
    decade = number // 10
    address = int(decade / 2 + 0.5) - 1
    
    # 檢查地址是否在數據範圍內
    if address < 0 or address >= len(primesdb_data):
        # 如果超出範圍，回退到傳統方法
        return is_prime(number)
    
    # 計算位偏移
    bit_positions = {1: 0, 3: 1, 7: 2, 9: 3}
    bit_pos = bit_positions[last_digit]
    
    # 如果十位數是偶數，使用高位元組
    if decade % 2 == 0:
        bit_pos += 4
    
    # 獲取字節並檢查相應的位
    byte_value = primesdb_data[address]
    is_prime_value = (byte_value >> bit_pos) & 1
    
    return is_prime_value == 1

def find_primes_near(number, count, direction):
    """查找指定數字附近的質數"""
    global primesdb_data
    
    # 如果數據未加載，嘗試加載
    if primesdb_data is None:
        if not download_primesdb():
            # 如果無法加載 PrimesDB，回退到傳統方法
            return []
    
    result = []
    current = number
    
    # 根據方向調整步進
    step = 1 if direction == 'larger' else -1
    
    # 如果是向下查找，先減 1
    if direction == 'smaller':
        current -= 1
    # 如果是向上查找，先加 1
    else:
        current += 1
    
    # 查找指定數量的質數
    while len(result) < count and current > 1 and current < 10**10:  # 設置一個上限，避免無限循環
        if is_prime_primesdb(current):
            result.append(current)
        current += step
    
    return result

# 列出目錄內容的函數
def list_directory_contents(directory):
    try:
        if os.path.exists(directory):
            files = os.listdir(directory)
            logger.info(f"目錄 {directory} 的內容: {files}")
            return files
        else:
            logger.warning(f"目錄 {directory} 不存在")
            return []
    except Exception as e:
        logger.error(f"列出目錄 {directory} 的內容時出錯: {e}")
        return []

# 在應用啟動時列出重要目錄的內容
def log_directories():
    # 列出當前目錄
    current_dir = os.path.dirname(os.path.abspath(__file__))
    logger.info(f"當前目錄: {current_dir}")
    list_directory_contents(current_dir)
    
    # 列出 backend 目錄（如果存在）
    backend_dir = os.path.join(current_dir, 'backend')
    list_directory_contents(backend_dir)
    
    # 列出 Render 上可能的目錄
    render_dirs = [
        '/opt/render/project/src/',
        '/opt/render/project/src/backend/',
        '/app/',
        '/app/backend/'
    ]
    for dir in render_dirs:
        list_directory_contents(dir)

# 使用 with app.app_context() 替代 before_first_request
with app.app_context():
    log_directories()
    # 預加載 PrimesDB 數據
    download_primesdb()

# 數據庫路徑
# 檢查多個可能的路徑，包括與 prime_sum.py 相關的路徑
DB_PATHS = [
    os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend', 'primes.db'),  # 本地開發路徑
    '/opt/render/project/src/backend/primes.db',  # Render 上的路徑
    os.path.join(os.path.dirname(os.path.abspath(__file__)), 'primes.db'),  # 根目錄
    '/opt/render/project/src/primes.db',  # Render 根目錄
    '/app/primes.db',  # Docker 容器中的路徑
    '/app/backend/primes.db',  # Docker 容器中的 backend 路徑
    # 與 prime_sum.py 相關的可能路徑
    '/opt/render/project/src/prime_sum_db.sqlite',
    '/opt/render/project/src/prime_numbers.db',
    '/opt/render/project/src/primes.sqlite',
    '/opt/render/project/src/prime_sum.db',
    # 嘗試查找任何 .db 或 .sqlite 文件
    '/opt/render/project/src/*.db',
    '/opt/render/project/src/*.sqlite'
]

def is_prime(n):
    """檢查一個數字是否為質數"""
    if n <= 1:
        return False
    if n <= 3:
        return True
    if n % 2 == 0 or n % 3 == 0:
        return False
    i = 5
    while i * i <= n:
        if n % i == 0 or n % (i + 2) == 0:
            return False
        i += 6
    return True

# 如果資料庫不存在，使用內存資料庫並添加一些測試數據
def get_db_connection():
    """連接到質數資料庫"""
    try:
        # 嘗試所有可能的路徑
        for db_path in DB_PATHS:
            logger.info(f"嘗試連接資料庫: {db_path}")
            if os.path.exists(db_path):
                logger.info(f"連接到實際資料庫: {db_path}")
                conn = sqlite3.connect(db_path)
                conn.row_factory = sqlite3.Row
                logger.info("資料庫連接成功")
                return conn
        
        # 如果所有路徑都不存在，使用內存資料庫並生成更多質數
        logger.warning(f"所有資料庫路徑都不存在，使用內存資料庫並生成質數")
        conn = sqlite3.connect(':memory:')
        conn.row_factory = sqlite3.Row
        
        # 創建表格
        conn.execute('CREATE TABLE primes (id INTEGER PRIMARY KEY, value INTEGER, created_at TIMESTAMP)')
        
        # 生成更多的質數，特別是大質數
        # 先添加一些小質數
        test_primes = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71]
        
        # 添加更多質數，直到 10000
        for i in range(100, 10000):
            if is_prime(i):
                test_primes.append(i)
        
        # 插入所有質數
        for i, prime in enumerate(test_primes):
            conn.execute('INSERT INTO primes VALUES (?, ?, ?)', (i+1, prime, 0))
        
        conn.commit()
        logger.info(f"內存資料庫創建成功，共添加 {len(test_primes)} 個質數")
        return conn
        
    except Exception as e:
        logger.error(f"連接資料庫時出錯: {e}")
        return None

def contains_letters(text):
    """檢查文字是否包含字母"""
    return any(c.isalpha() for c in text)

def to_base10(text):
    """將base-36字符串轉換為10進制整數"""
    result = 0
    for char in text:
        if char.isdigit():
            value = int(char)
        else:
            value = ord(char.upper()) - ord('A') + 10
        result = result * 36 + value
    return result

def to_base36(number):
    """將10進制整數轉換為base-36字符串"""
    if number == 0:
        return '0'
    
    chars = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    result = ''
    
    while number > 0:
        result = chars[number % 36] + result
        number //= 36
    
    return result

def find_closest_primes(number, count=10, has_letters=False):
    """找出離指定數字最近的質數"""
    try:
        logger.info(f"查詢最接近 {number} 的質數，數量: {count}，是否包含字母: {has_letters}")
        
        # 使用 PrimesDB 查找較大和較小的質數
        larger_primes = find_primes_near(number, count, 'larger')
        smaller_primes = find_primes_near(number, count, 'smaller')
        
        logger.info(f"查詢結果: 較大質數 {len(larger_primes)} 個, 較小質數 {len(smaller_primes)} 個")
        
        # 合併結果並計算距離
        result = []
        
        # 處理較大的質數
        for prime in larger_primes:
            distance = prime - number
            result.append((prime, distance))
        
        # 處理較小的質數
        for prime in smaller_primes:
            distance = number - prime
            result.append((prime, distance))
        
        # 按距離排序
        result.sort(key=lambda x: x[1])
        
        # 限制結果數量
        result = result[:count]
        
        # 將結果轉換為字典
        results = []
        for prime, distance in result:
            if has_letters:
                prime_base36 = to_base36(prime)
            else:
                prime_base36 = str(prime)
            results.append({
                'prime_base10': prime,
                'prime_base36': prime_base36,
                'distance': distance
            })
        
        logger.info(f"最終結果: {results}")
        
        return results
    except Exception as e:
        logger.error(f"查詢質數時出錯: {e}")
        return []

@app.route('/')
def index():
    template = '''
    <!DOCTYPE html>
    <html lang="zh-TW">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>車牌號碼與質數的距離</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            body {
                font-family: 'Microsoft JhengHei', Arial, sans-serif;
                padding: 20px;
                background-color: #f8f9fa;
            }
            .license-plate {
                font-size: 24px;
                font-weight: bold;
                background-color: #f0f0f0;
                padding: 8px 15px;
                border-radius: 4px;
                border: 2px solid #ddd;
                display: inline-block;
                margin-bottom: 15px;
            }
            .container {
                max-width: 1200px;
                width: 85%;
            }
            .prime-table {
                width: 100%;
                margin-bottom: 1rem;
            }
            .prime-table th, .prime-table td {
                padding: 0.75rem;
                text-align: center;
                border: 1px solid #dee2e6;
            }
            .prime-table th {
                background-color: #f8f9fa;
            }
            .prime-value {
                font-weight: bold;
                font-size: 1.1rem;
            }
            .celebration {
                text-align: center;
                margin: 20px 0;
                padding: 20px;
                background-color: #f8f9d7;
                border-radius: 10px;
                border: 2px solid #ffc107;
                animation: pulse 2s infinite;
            }
            .celebration-big {
                background-color: #fff3cd;
                border: 3px solid #ff9800;
                animation: pulse-big 1.5s infinite;
            }
            .celebration h3 {
                color: #d32f2f;
                margin-bottom: 15px;
            }
            .celebration-icon {
                font-size: 48px;
                margin-bottom: 15px;
                display: inline-block;
            }
            .combination-card {
                margin-bottom: 20px;
                transition: all 0.3s ease;
            }
            .combination-card:hover {
                transform: translateY(-5px);
                box-shadow: 0 10px 20px rgba(0,0,0,0.1);
            }
            @keyframes pulse {
                0% { transform: scale(1); }
                50% { transform: scale(1.05); }
                100% { transform: scale(1); }
            }
            @keyframes pulse-big {
                0% { transform: scale(1); }
                50% { transform: scale(1.1); }
                100% { transform: scale(1); }
            }
            .confetti {
                position: fixed;
                width: 10px;
                height: 10px;
                background-color: #f00;
                animation: confetti-fall 5s linear forwards;
                z-index: 1000;
            }
            @keyframes confetti-fall {
                0% { transform: translateY(-100px) rotate(0deg); opacity: 1; }
                100% { transform: translateY(100vh) rotate(360deg); opacity: 0; }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1 class="text-center my-4">車牌號碼與質數的距離</h1>
            
            <div class="card mb-4">
                <div class="card-header bg-primary text-white">
                    <h5 class="mb-0">查詢表單</h5>
                </div>
                <div class="card-body">
                    <form id="searchForm" action="/search" method="post">
                        <div class="row mb-3">
                            <div class="col-md-4">
                                <label for="part1" class="form-label">前半部 (2-5個字元)</label>
                                <input type="text" class="form-control" id="part1" name="part1" placeholder="例如: AB" required>
                            </div>
                            <div class="col-md-4">
                                <label for="part2" class="form-label">後半部 (2-5個字元)</label>
                                <input type="text" class="form-control" id="part2" name="part2" placeholder="例如: 123" required>
                            </div>
                            <div class="col-md-4">
                                <label for="count" class="form-label">顯示數量</label>
                                <input type="number" class="form-control" id="count" name="count" value="10" min="1" max="512">
                            </div>
                        </div>
                        <button type="submit" class="btn btn-primary">查詢最接近的質數</button>
                    </form>
                </div>
            </div>
            
            <div id="results"></div>
        </div>
        
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/js/bootstrap.bundle.min.js"></script>
        <hr>
        <p align=center>質人精神 2025</p>
    </body>
    </html>
    '''
    return template

@app.route('/db-info')
def db_info():
    """顯示數據庫信息的端點"""
    info = {
        'current_directory': os.path.dirname(os.path.abspath(__file__)),
        'db_paths_checked': DB_PATHS,
        'directories': {},
        'all_db_files': []
    }
    
    # 列出當前目錄
    current_dir = os.path.dirname(os.path.abspath(__file__))
    info['directories'][current_dir] = list_directory_contents(current_dir)
    
    # 列出 backend 目錄（如果存在）
    backend_dir = os.path.join(current_dir, 'backend')
    info['directories'][backend_dir] = list_directory_contents(backend_dir)
    
    # 列出 Render 上可能的目錄
    render_dirs = [
        '/opt/render/project/src/',
        '/opt/render/project/src/backend/',
        '/app/',
        '/app/backend/'
    ]
    for dir in render_dirs:
        info['directories'][dir] = list_directory_contents(dir)
        
        # 嘗試查找任何 .db 或 .sqlite 文件
        try:
            if os.path.exists(dir):
                for file in os.listdir(dir):
                    if file.endswith('.db') or file.endswith('.sqlite'):
                        db_path = os.path.join(dir, file)
                        info['all_db_files'].append(db_path)
                        # 嘗試連接到這個數據庫
                        try:
                            conn = sqlite3.connect(db_path)
                            cursor = conn.cursor()
                            # 檢查是否有 primes 表
                            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                            tables = [table[0] for table in cursor.fetchall()]
                            info[f'db_file_{file}'] = {
                                'path': db_path,
                                'tables': tables
                            }
                            # 如果有 primes 表，檢查其內容
                            if 'primes' in tables:
                                cursor.execute("SELECT COUNT(*) FROM primes")
                                count = cursor.fetchone()[0]
                                info[f'db_file_{file}']['primes_count'] = count
                            conn.close()
                        except Exception as e:
                            info[f'db_file_{file}_error'] = str(e)
        except Exception as e:
            info[f'dir_{dir}_error'] = str(e)
    
    # 檢查數據庫連接
    conn = None
    db_found = False
    db_path_used = None
    
    for db_path in DB_PATHS:
        # 如果路徑包含通配符，嘗試查找匹配的文件
        if '*' in db_path:
            import glob
            matching_files = glob.glob(db_path)
            for file_path in matching_files:
                info['all_db_files'].append(file_path)
            continue
            
        if os.path.exists(db_path):
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                # 檢查表是否存在
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='primes'")
                if cursor.fetchone():
                    # 檢查表中的數據
                    cursor.execute("SELECT COUNT(*) FROM primes")
                    count = cursor.fetchone()[0]
                    info['db_status'] = f"找到數據庫: {db_path}，包含 {count} 個質數"
                    db_found = True
                    db_path_used = db_path
                    break
                else:
                    info['db_status'] = f"找到數據庫文件: {db_path}，但沒有 primes 表"
            except Exception as e:
                info['db_status'] = f"嘗試連接數據庫 {db_path} 時出錯: {str(e)}"
            finally:
                if conn:
                    conn.close()
    
    if not db_found:
        info['db_status'] = "未找到有效的質數數據庫"
    
    # 檢查內存數據庫
    if not db_found:
        try:
            conn = get_db_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM primes")
                count = cursor.fetchone()[0]
                info['memory_db_status'] = f"使用內存數據庫，包含 {count} 個質數"
            else:
                info['memory_db_status'] = "無法創建內存數據庫"
        except Exception as e:
            info['memory_db_status'] = f"檢查內存數據庫時出錯: {str(e)}"
        finally:
            if conn:
                conn.close()
    
    return jsonify(info)

@app.route('/search', methods=['POST'])
def search():
    try:
        logger.info(f"收到搜索請求: {request.form}")
        logger.info(f"請求內容類型: {request.content_type}")
        logger.info(f"請求方法: {request.method}")
        
        # 使用表單數據
        part1 = request.form.get('part1', '').strip().upper()
        part2 = request.form.get('part2', '').strip().upper()
        count = min(int(request.form.get('count', 10)), 512)
        
        logger.info(f"處理參數: part1={part1}, part2={part2}, count={count}")
        
        # 驗證車牌部分
        if not (part1 and 2 <= len(part1) <= 5 and part2 and 2 <= len(part2) <= 5):
            error_message = '車牌號碼格式不正確，請確保前後半部各至少2個字元，最多5個字元。'
            logger.warning(f"驗證失敗: {error_message}")
            return render_template_string(get_index_template(), error=error_message)
        
        # 檢查是否包含字母
        part1_has_letters = contains_letters(part1)
        part2_has_letters = contains_letters(part2)
        
        # 轉換為數字
        try:
            if part1_has_letters:
                part1_number = to_base10(part1)
            else:
                part1_number = int(part1)
                
            if part2_has_letters:
                part2_number = to_base10(part2)
            else:
                part2_number = int(part2)
        except ValueError as e:
            logger.error(f"轉換車牌號碼時出錯: {e}")
            return render_template_string(get_index_template(), error=f"無效的車牌號碼格式: {str(e)}")
        
        # 查詢最接近的質數
        part1_primes = find_closest_primes(part1_number, count, part1_has_letters)
        part2_primes = find_closest_primes(part2_number, count, part2_has_letters)
        
        # 準備結果
        results = {
            'part1': {
                'original': part1,
                'base10': part1_number,
                'has_letters': part1_has_letters,
                'is_prime': is_prime(part1_number),
                'closest_primes': part1_primes
            },
            'part2': {
                'original': part2,
                'base10': part2_number,
                'has_letters': part2_has_letters,
                'is_prime': is_prime(part2_number),
                'closest_primes': part2_primes
            }
        }
        
        logger.info(f"搜索結果: {results}")
        
        # 生成隨機組合
        random_combinations = []
        max_combinations = 9  # 最多顯示9個組合
        
        # 如果結果數量小於等於3，顯示所有組合
        if count <= 3:
            for p1 in part1_primes:
                for p2 in part2_primes:
                    random_combinations.append({
                        "part1": p1,
                        "part2": p2,
                        "total_distance": p1["distance"] + p2["distance"]
                    })
        else:
            # 隨機選擇不重複的組合
            all_combinations = []
            for i, p1 in enumerate(part1_primes):
                for j, p2 in enumerate(part2_primes):
                    all_combinations.append({
                        "part1": p1,
                        "part2": p2,
                        "total_distance": p1["distance"] + p2["distance"],
                        "index": (i, j)  # 保存索引以確保不重複
                    })
            
            # 隨機選擇組合
            if len(all_combinations) > max_combinations:
                random_indices = random.sample(range(len(all_combinations)), max_combinations)
                random_combinations = [all_combinations[i] for i in random_indices]
            else:
                random_combinations = all_combinations
        
        # 將結果傳遞給模板
        return render_template_string(
            get_index_template(), 
            results=results,
            random_combinations=random_combinations,
            both_prime=results['part1']['is_prime'] and results['part2']['is_prime'],
            any_prime=results['part1']['is_prime'] or results['part2']['is_prime']
        )
    
    except Exception as e:
        logger.error(f"處理搜索請求時出錯: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return render_template_string(get_index_template(), error=f"處理請求時出錯: {str(e)}")

def get_index_template():
    """獲取首頁模板"""
    template = '''
    <!DOCTYPE html>
    <html lang="zh-TW">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>車牌號碼與質數的距離</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            body {
                font-family: 'Microsoft JhengHei', Arial, sans-serif;
                padding: 20px;
                background-color: #f8f9fa;
            }
            .license-plate {
                font-size: 24px;
                font-weight: bold;
                background-color: #f0f0f0;
                padding: 8px 15px;
                border-radius: 4px;
                border: 2px solid #ddd;
                display: inline-block;
                margin-bottom: 15px;
            }
            .container {
                max-width: 1200px;
                width: 85%;
            }
            .prime-table {
                width: 100%;
                margin-bottom: 1rem;
            }
            .prime-table th, .prime-table td {
                padding: 0.75rem;
                text-align: center;
                border: 1px solid #dee2e6;
            }
            .prime-table th {
                background-color: #f8f9fa;
            }
            .prime-value {
                font-weight: bold;
                font-size: 1.1rem;
            }
            .celebration {
                text-align: center;
                margin: 20px 0;
                padding: 20px;
                background-color: #f8f9d7;
                border-radius: 10px;
                border: 2px solid #ffc107;
                animation: pulse 2s infinite;
            }
            .celebration-big {
                background-color: #fff3cd;
                border: 3px solid #ff9800;
                animation: pulse-big 1.5s infinite;
            }
            .celebration h3 {
                color: #d32f2f;
                margin-bottom: 15px;
            }
            .celebration-icon {
                font-size: 48px;
                margin-bottom: 15px;
                display: inline-block;
            }
            .combination-card {
                margin-bottom: 20px;
                transition: all 0.3s ease;
            }
            .combination-card:hover {
                transform: translateY(-5px);
                box-shadow: 0 10px 20px rgba(0,0,0,0.1);
            }
            @keyframes pulse {
                0% { transform: scale(1); }
                50% { transform: scale(1.05); }
                100% { transform: scale(1); }
            }
            @keyframes pulse-big {
                0% { transform: scale(1); }
                50% { transform: scale(1.1); }
                100% { transform: scale(1); }
            }
            .confetti {
                position: fixed;
                width: 10px;
                height: 10px;
                background-color: #f00;
                animation: confetti-fall 5s linear forwards;
                z-index: 1000;
            }
            @keyframes confetti-fall {
                0% { transform: translateY(-100px) rotate(0deg); opacity: 1; }
                100% { transform: translateY(100vh) rotate(360deg); opacity: 0; }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1 class="text-center my-4">車牌號碼與質數的距離</h1>
            
            <div class="card mb-4">
                <div class="card-header bg-primary text-white">
                    <h5 class="mb-0">查詢表單</h5>
                </div>
                <div class="card-body">
                    <form id="searchForm" action="/search" method="post">
                        <div class="row mb-3">
                            <div class="col-md-4">
                                <label for="part1" class="form-label">前半部 (2-5個字元)</label>
                                <input type="text" class="form-control" id="part1" name="part1" placeholder="例如: AB" required>
                            </div>
                            <div class="col-md-4">
                                <label for="part2" class="form-label">後半部 (2-5個字元)</label>
                                <input type="text" class="form-control" id="part2" name="part2" placeholder="例如: 123" required>
                            </div>
                            <div class="col-md-4">
                                <label for="count" class="form-label">顯示數量</label>
                                <input type="number" class="form-control" id="count" name="count" value="10" min="1" max="512">
                            </div>
                        </div>
                        <button type="submit" class="btn btn-primary">查詢最接近的質數</button>
                    </form>
                </div>
            </div>
            
            <div id="results">
                {% if error %}
                <div class="alert alert-danger">{{ error }}</div>
                {% endif %}
                
                {% if both_prime %}
                <div class="celebration celebration-big">
                    <div class="celebration-icon">🎉🎊</div>
                    <h3>恭喜！您的車牌號碼前半部和後半部都是質數！</h3>
                    <p>這是非常罕見的情況，您的車牌號碼非常特別！</p>
                </div>
                <div id="confetti-container"></div>
                {% elif any_prime %}
                <div class="celebration">
                    <div class="celebration-icon">🎉</div>
                    <h3>恭喜！您的車牌號碼有一部分是質數！</h3>
                    <p>
                        {% if results.part1.is_prime %}
                        前半部 {{ results.part1.original }} 是質數！
                        {% else %}
                        後半部 {{ results.part2.original }} 是質數！
                        {% endif %}
                    </p>
                </div>
                {% endif %}
                
                {% if results %}
                <div class="row">
                    <!-- 前半部結果 -->
                    <div class="col-md-6">
                        <div class="card mb-4">
                            <div class="card-header bg-success text-white">
                                <h5 class="mb-0">前半部結果</h5>
                            </div>
                            <div class="card-body">
                                <div class="license-plate">{{ results.part1.original }}</div>
                                <p>
                                    {% if results.part1.has_letters %}
                                    36進位轉換為10進位: 
                                    {% else %}
                                    10進位: 
                                    {% endif %}
                                    <strong>{{ results.part1.base10 }}</strong>
                                    {% if results.part1.is_prime %}
                                    <span class="badge bg-warning">質數</span>
                                    {% endif %}
                                </p>
                                
                                <h6 class="mt-4">最接近的質數:</h6>
                                <table class="prime-table">
                                    <thead>
                                        <tr>
                                            <th>質數</th>
                                            <th>距離</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {% for item in results.part1.closest_primes %}
                                        <tr>
                                            <td class="prime-value">{{ item.prime_base36 }}</td>
                                            <td>{{ item.distance }}</td>
                                        </tr>
                                        {% endfor %}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                    
                    <!-- 後半部結果 -->
                    <div class="col-md-6">
                        <div class="card mb-4">
                            <div class="card-header bg-info text-white">
                                <h5 class="mb-0">後半部結果</h5>
                            </div>
                            <div class="card-body">
                                <div class="license-plate">{{ results.part2.original }}</div>
                                <p>
                                    {% if results.part2.has_letters %}
                                    36進位轉換為10進位: 
                                    {% else %}
                                    10進位: 
                                    {% endif %}
                                    <strong>{{ results.part2.base10 }}</strong>
                                    {% if results.part2.is_prime %}
                                    <span class="badge bg-warning">質數</span>
                                    {% endif %}
                                </p>
                                
                                <h6 class="mt-4">最接近的質數:</h6>
                                <table class="prime-table">
                                    <thead>
                                        <tr>
                                            <th>質數</th>
                                            <th>距離</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {% for item in results.part2.closest_primes %}
                                        <tr>
                                            <td class="prime-value">{{ item.prime_base36 }}</td>
                                            <td>{{ item.distance }}</td>
                                        </tr>
                                        {% endfor %}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- 隨機組合顯示 -->
                {% if random_combinations %}
                <div class="card mb-4">
                    <div class="card-header bg-primary text-white">
                        <h5 class="mb-0">隨機組合顯示</h5>
                    </div>
                    <div class="card-body">
                        <p class="text-muted">以下是從所有可能組合中隨機選擇的結果，每次查詢都會有不同的組合。</p>
                        
                        <div class="row">
                            {% for combo in random_combinations %}
                            <div class="col-md-4">
                                <div class="card combination-card">
                                    <div class="card-header bg-light">
                                        <h6 class="mb-0">組合 #{{ loop.index }}</h6>
                                    </div>
                                    <div class="card-body">
                                        <div class="d-flex justify-content-between mb-3">
                                            <div class="text-center">
                                                <div class="license-plate">{{ combo.part1.prime_base36 }}</div>
                                                <small>距離: {{ combo.part1.distance }}</small>
                                            </div>
                                            <div class="text-center">
                                                <div class="license-plate">{{ combo.part2.prime_base36 }}</div>
                                                <small>距離: {{ combo.part2.distance }}</small>
                                            </div>
                                        </div>
                                        <div class="text-center">
                                            <p>總距離: <strong>{{ combo.total_distance }}</strong></p>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            {% endfor %}
                        </div>
                    </div>
                </div>
                {% endif %}
                {% endif %}
            </div>
        </div>
        
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/js/bootstrap.bundle.min.js"></script>
        
        {% if both_prime %}
        <script>
            // 慶祝動畫 - 五彩紙屑效果
            document.addEventListener('DOMContentLoaded', function() {
                const colors = ['#f44336', '#e91e63', '#9c27b0', '#673ab7', '#3f51b5', '#2196f3', '#03a9f4', '#00bcd4', '#009688', '#4caf50', '#8bc34a', '#cddc39', '#ffeb3b', '#ffc107', '#ff9800', '#ff5722'];
                const container = document.getElementById('confetti-container');
                
                // 創建100個五彩紙屑
                for (let i = 0; i < 100; i++) {
                    setTimeout(() => {
                        const confetti = document.createElement('div');
                        confetti.className = 'confetti';
                        confetti.style.backgroundColor = colors[Math.floor(Math.random() * colors.length)];
                        confetti.style.left = Math.random() * 100 + 'vw';
                        confetti.style.width = (Math.random() * 10 + 5) + 'px';
                        confetti.style.height = (Math.random() * 10 + 5) + 'px';
                        confetti.style.animationDuration = (Math.random() * 3 + 2) + 's';
                        document.body.appendChild(confetti);
                        
                        // 動畫結束後移除元素
                        setTimeout(() => {
                            confetti.remove();
                        }, 5000);
                    }, Math.random() * 1000);
                }
            });
        </script>
        {% endif %}
    </body>
    </html>
    '''
    return template

if __name__ == '__main__':
    logger.info("Starting 車牌號碼與質數的距離 v1.0.0")
    app.run(host='127.0.0.1', port=5002, debug=True)
