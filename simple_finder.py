import os
import sqlite3
import logging
from flask import Flask, request, render_template_string, jsonify
import json
import random

# 設定日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('LicensePlatePrimeFinder')

app = Flask(__name__)
# 數據庫路徑
# 使用相對路徑，這樣在 Render 上也能正常工作
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend', 'primes.db')

# 如果資料庫不存在，使用內存資料庫並添加一些測試數據
def get_db_connection():
    """連接到質數資料庫"""
    try:
        logger.info(f"嘗試連接資料庫: {DB_PATH}")
        logger.info(f"資料庫文件是否存在: {os.path.exists(DB_PATH)}")
        
        if os.path.exists(DB_PATH):
            logger.info(f"連接到實際資料庫: {DB_PATH}")
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            logger.info("資料庫連接成功")
            return conn
        else:
            # 如果資料庫不存在，使用內存資料庫
            logger.warning(f"資料庫不存在: {DB_PATH}，使用內存資料庫")
            conn = sqlite3.connect(':memory:')
            conn.row_factory = sqlite3.Row
            
            # 創建表格
            conn.execute('CREATE TABLE primes (id INTEGER PRIMARY KEY, value INTEGER, created_at TIMESTAMP)')
            
            # 添加一些測試質數數據 - 增加更多質數以提高準確性
            test_primes = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71, 
                          73, 79, 83, 89, 97, 101, 103, 107, 109, 113, 127, 131, 137, 139, 149, 151, 
                          157, 163, 167, 173, 179, 181, 191, 193, 197, 199, 211, 223, 227, 229, 233, 
                          239, 241, 251, 257, 263, 269, 271, 277, 281, 283, 293, 307, 311, 313, 317, 
                          331, 337, 347, 349, 353, 359, 367, 373, 379, 383, 389, 397, 401, 409, 419, 
                          421, 431, 433, 439, 443, 449, 457, 461, 463, 467, 479, 487, 491, 499, 503, 
                          509, 521, 523, 541, 547, 557, 563, 569, 571, 577, 587, 593, 599, 601, 607, 
                          613, 617, 619, 631, 641, 643, 647, 653, 659, 661, 673, 677, 683, 691, 701, 
                          709, 719, 727, 733, 739, 743, 751, 757, 761, 769, 773, 787, 797, 809, 811, 
                          821, 823, 827, 829, 839, 853, 857, 859, 863, 877, 881, 883, 887, 907, 911, 
                          919, 929, 937, 941, 947, 953, 967, 971, 977, 983, 991, 997, 1009, 1013, 1019, 1021, 
                          1031, 1033, 1039, 1049, 1051, 1061, 1063, 1069, 1087, 1091, 1093, 1097, 1103, 1109, 1117, 
                          1123, 1129, 1151, 1153, 1163, 1171, 1181, 1187, 1193, 1201, 1213, 1217, 1223, 1229, 1231, 
                          1237, 1249, 1259, 1277, 1279, 1283, 1289, 1291, 1297, 1301, 1303, 1307, 1319, 1321, 1327, 
                          1361, 1367, 1373, 1381, 1399, 1409, 1423, 1427, 1429, 1433, 1439, 1447, 1451, 1453, 1459, 
                          1471, 1481, 1483, 1487, 1489, 1493, 1499, 1511, 1523, 1531, 1543, 1549, 1553, 1559, 1567, 
                          1571, 1579, 1583, 1597, 1601, 1607, 1609, 1613, 1619, 1621, 1627, 1637, 1657, 1663, 1667, 
                          1669, 1693, 1697, 1699, 1709, 1721, 1723, 1733, 1741, 1747, 1753, 1759, 1777, 1783, 1787, 
                          1789, 1801, 1811, 1823, 1831, 1847, 1861, 1867, 1871, 1873, 1877, 1879, 1889, 1901, 1907, 
                          1913, 1931, 1933, 1949, 1951, 1973, 1979, 1987, 1993, 1997, 1999, 2003, 2011, 2017, 2027, 
                          2029, 2039, 2053, 2063, 2069, 2081, 2083, 2087, 2089, 2099, 2111, 2113, 2129, 2131, 2137]
            
            for i, prime in enumerate(test_primes):
                conn.execute('INSERT INTO primes VALUES (?, ?, ?)', (i+1, prime, 0))
            
            conn.commit()
            logger.info("內存資料庫創建並填充測試數據成功")
            return conn
    except Exception as e:
        logger.error(f"資料庫連接錯誤: {e}")
        # 如果連接失敗，也使用內存資料庫
        conn = sqlite3.connect(':memory:')
        conn.row_factory = sqlite3.Row
        conn.execute('CREATE TABLE primes (id INTEGER PRIMARY KEY, value INTEGER, created_at TIMESTAMP)')
        conn.execute('INSERT INTO primes VALUES (1, 2, 0), (2, 3, 0), (3, 5, 0), (4, 7, 0), (5, 11, 0)')
        conn.commit()
        logger.warning("使用最小內存資料庫作為後備")
        return conn

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
    """找出最接近給定數字的質數"""
    conn = get_db_connection()
    
    if not conn:
        logger.error("無法獲取資料庫連接")
        return []
    
    try:
        logger.info(f"查詢最接近 {number} 的質數，數量: {count}，是否包含字母: {has_letters}")
        
        # 檢查數據庫中是否有質數表
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='primes'")
        if not cursor.fetchone():
            logger.error("數據庫中沒有primes表，創建測試數據")
            # 創建表格
            conn.execute('CREATE TABLE primes (id INTEGER PRIMARY KEY, value INTEGER, created_at TIMESTAMP)')
            
            # 添加一些測試質數數據
            test_primes = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71]
            for i, prime in enumerate(test_primes):
                conn.execute('INSERT INTO primes VALUES (?, ?, ?)', (i+1, prime, 0))
            conn.commit()
        
        # 檢查數據庫中的質數數量
        cursor.execute("SELECT COUNT(*) FROM primes")
        prime_count = cursor.fetchone()[0]
        logger.info(f"數據庫中有 {prime_count} 個質數")
        
        # 如果數據庫為空，添加一些測試數據
        if prime_count == 0:
            logger.warning("數據庫為空，添加測試數據")
            test_primes = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71]
            for i, prime in enumerate(test_primes):
                conn.execute('INSERT INTO primes VALUES (?, ?, ?)', (i+1, prime, 0))
            conn.commit()
        
        # 查詢比number大的質數
        larger_primes = conn.execute(
            'SELECT value FROM primes WHERE value >= ? ORDER BY value ASC LIMIT ?',
            (number, count)  # 直接查詢 count 個，而不是 count // 2 + 1
        ).fetchall()
        
        # 查詢比number小的質數
        smaller_primes = conn.execute(
            'SELECT value FROM primes WHERE value < ? ORDER BY value DESC LIMIT ?',
            (number, count)  # 直接查詢 count 個，而不是 count // 2 + 1
        ).fetchall()
        
        logger.info(f"查詢結果: 較大質數 {len(larger_primes)} 個, 較小質數 {len(smaller_primes)} 個")
        
        # 合併結果並按與number的距離排序
        results = []
        
        for row in smaller_primes:
            prime = row[0]  # 使用索引而不是列名
            distance = number - prime
            result = {
                'prime_base10': prime,
                'distance': distance
            }
            if has_letters:
                result['prime_base36'] = to_base36(prime)
            else:
                result['prime_base36'] = str(prime)
            results.append(result)
        
        for row in larger_primes:
            prime = row[0]  # 使用索引而不是列名
            distance = prime - number
            result = {
                'prime_base10': prime,
                'distance': distance
            }
            if has_letters:
                result['prime_base36'] = to_base36(prime)
            else:
                result['prime_base36'] = str(prime)
            results.append(result)
        
        # 按距離排序
        results.sort(key=lambda x: x['distance'])
        
        # 限制結果數量
        results = results[:count]
        
        # 記錄結果
        logger.info(f"最終結果: {results}")
        
        return results
    
    except Exception as e:
        logger.error(f"查詢質數時出錯: {e}")
        return []
    
    finally:
        conn.close()

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
