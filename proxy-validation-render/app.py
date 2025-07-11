from flask import Flask, jsonify, request
import requests
import threading
import time
import json
import os
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import random

app = Flask(__name__)

# Cache proxy sống
proxy_cache = {
    "http": [],
    "last_update": None,
    "total_checked": 0,
    "alive_count": 0,
    "sources_processed": 0
}

# Nguồn proxy được phân loại - tối ưu cho Render free plan
PROXY_SOURCE_LINKS = {
    # Categorized sources - test với protocol đã biết
    "categorized": {
        "Server Alpha": "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/all/data.txt",
        "Network Beta": "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt", 
        "Gateway Pro": "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
        "Server Delta": "https://raw.githubusercontent.com/hookzof/socks5_list/master/proxy.txt",
        "Server Echo": "https://api.proxyscrape.com/v2/?request=get&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all&format=textplain",
        "Server Foxtrot": "https://www.proxy-list.download/api/v1/get?type=http",
        "Server Golf": "https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt",
    },
    # Mixed sources - test với tất cả protocols
    "mixed": {
        "hendrikbgr": "https://raw.githubusercontent.com/hendrikbgr/Free-Proxy-Repo/master/proxy_list.txt",
        "MrMarble": "https://raw.githubusercontent.com/MrMarble/proxy-list/main/all.txt",
        "sunny9577": "https://raw.githubusercontent.com/sunny9577/proxy-scraper/master/proxies.txt"
    }
}

def log_to_render(message, level="INFO"):
    """Log với format rõ ràng cho Render logs"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{level}] {timestamp} | {message}")

def check_single_proxy(proxy_string, timeout=6, protocols=['http']):
    """Kiểm tra 1 proxy với các protocols khác nhau - tối ưu cho Render"""
    try:
        if ':' not in proxy_string:
            return None
            
        # Parse proxy format: host:port hoặc username:password@host:port
        if '@' in proxy_string:
            auth_part, host_port = proxy_string.split('@')
            if ':' in auth_part:
                username, password = auth_part.split(':', 1)
            else:
                username, password = auth_part, ""
        else:
            username, password = None, None
            host_port = proxy_string

        if ':' not in host_port:
            return None
            
        host, port = host_port.strip().split(':', 1)
        
        # Test URLs 
        test_urls = [
            'http://httpbin.org/ip',
            'http://ip-api.com/json',
        ]
        
        # Test với từng protocol
        for protocol in protocols:
            try:
                # Setup proxy theo protocol
                if username and password:
                    if protocol in ['socks4', 'socks5']:
                        proxy_url = f"{protocol}://{username}:{password}@{host}:{port}"
                    else:
                        proxy_url = f"http://{username}:{password}@{host}:{port}"
                else:
                    if protocol in ['socks4', 'socks5']:
                        proxy_url = f"{protocol}://{host}:{port}"
                    else:
                        proxy_url = f"http://{host}:{port}"
                
                proxies = {
                    'http': proxy_url,
                    'https': proxy_url
                }
                
                start_time = time.time()
                
                # Test proxy với multiple URLs
                for test_url in test_urls:
                    try:
                        response = requests.get(
                            test_url,
                            proxies=proxies,
                            timeout=timeout,
                            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                        )
                        
                        if response.status_code == 200:
                            speed = round(time.time() - start_time, 2)
                            
                            # Get proxy IP
                            try:
                                ip_data = response.json()
                                proxy_ip = ip_data.get('origin', ip_data.get('query', ip_data.get('ip', 'unknown')))
                                # Clean IP (remove port if present)
                                if ',' in proxy_ip:
                                    proxy_ip = proxy_ip.split(',')[0]
                            except:
                                proxy_ip = 'unknown'
                            
                            return {
                                'host': host,
                                'port': int(port),
                                'type': protocol,
                                'speed': speed,
                                'status': 'alive',
                                'ip': proxy_ip,
                                'checked_at': datetime.now().isoformat(),
                                'proxy_string': f"{host}:{port}",
                                'full_proxy': proxy_string,
                                'has_auth': bool(username and password)
                            }
                    except:
                        continue
                        
            except:
                continue
                
    except Exception as e:
        pass
    
    return None

def fetch_proxies_from_sources():
    """Lấy proxy từ tất cả nguồn với logic thông minh - tối ưu cho Render"""
    all_proxies = []
    sources_processed = 0
    
    log_to_render("🔍 BẮT ĐẦU FETCH PROXY TỪ CÁC NGUỒN...")
    
    # Xử lý categorized sources trước (ưu tiên)
    log_to_render("📥 Xử lý CATEGORIZED sources...")
    for source_name, source_url in PROXY_SOURCE_LINKS["categorized"].items():
        try:
            log_to_render(f"📡 Fetching {source_name}...")
            
            response = requests.get(source_url, timeout=30)
            
            if response.status_code == 200:
                content = response.text
                lines = content.strip().split('\n')
                source_proxies = []
                
                for line in lines:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                        
                    # Validate proxy format
                    if ':' in line:
                        try:
                            # Check if it's valid proxy format
                            if '@' in line:
                                auth_part, host_port = line.split('@')
                                host, port = host_port.split(':')
                            else:
                                host, port = line.split(':')
                            
                            # Basic validation
                            if len(host.split('.')) == 4 and port.isdigit():
                                source_proxies.append(line)
                                
                        except:
                            continue
                
                all_proxies.extend(source_proxies)
                sources_processed += 1
                log_to_render(f"✅ {source_name}: {len(source_proxies)} proxy")
            else:
                log_to_render(f"❌ {source_name}: HTTP {response.status_code}")
        
        except Exception as e:
            log_to_render(f"❌ {source_name}: {str(e)}")
            continue
    
    # Xử lý mixed sources sau
    log_to_render("📥 Xử lý MIXED sources...")
    for source_name, source_url in PROXY_SOURCE_LINKS["mixed"].items():
        try:
            log_to_render(f"📡 Fetching {source_name}...")
            
            response = requests.get(source_url, timeout=30)
            
            if response.status_code == 200:
                content = response.text
                lines = content.strip().split('\n')
                source_proxies = []
                
                for line in lines:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                        
                    # Validate proxy format
                    if ':' in line:
                        try:
                            # Check if it's valid proxy format
                            if '@' in line:
                                auth_part, host_port = line.split('@')
                                host, port = host_port.split(':')
                            else:
                                host, port = line.split(':')
                            
                            # Basic validation
                            if len(host.split('.')) == 4 and port.isdigit():
                                source_proxies.append(line)
                                
                        except:
                            continue
                
                all_proxies.extend(source_proxies)
                sources_processed += 1
                log_to_render(f"✅ {source_name}: {len(source_proxies)} proxy")
            else:
                log_to_render(f"❌ {source_name}: HTTP {response.status_code}")
        
        except Exception as e:
            log_to_render(f"❌ {source_name}: {str(e)}")
            continue
    
    # Remove duplicates
    unique_proxies = list(set(all_proxies))
    log_to_render(f"🎯 TỔNG: {len(unique_proxies)} proxy từ {sources_processed} nguồn")
    
    return unique_proxies, sources_processed

def validate_proxy_batch_smart(proxy_list, max_workers=15):
    """Validate proxy với CHUNK processing cho Render free plan"""
    alive_proxies = []
    
    # GIỚI HẠN cho Render free plan (512MB RAM)
    CHUNK_SIZE = 300  # Xử lý 300 proxy mỗi lần
    MAX_TOTAL = 800   # Tối đa 800 proxy total
    
    # Limit total proxies để tránh timeout trên Render free
    limited_proxies = proxy_list[:MAX_TOTAL]
    
    log_to_render(f"🔄 RENDER FREE MODE: Xử lý {len(limited_proxies)} proxy (max {MAX_TOTAL})")
    log_to_render(f"📦 Chia chunks: {CHUNK_SIZE} proxy/chunk với {max_workers} workers")
    
    # Chia thành chunks nhỏ
    for i in range(0, len(limited_proxies), CHUNK_SIZE):
        chunk = limited_proxies[i:i+CHUNK_SIZE]
        chunk_num = (i // CHUNK_SIZE) + 1
        total_chunks = (len(limited_proxies) + CHUNK_SIZE - 1) // CHUNK_SIZE
        
        log_to_render(f"🧩 Chunk {chunk_num}/{total_chunks}: {len(chunk)} proxy")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit chunk proxy checks
            futures = []
            for proxy in chunk:
                future = executor.submit(check_single_proxy, proxy, 6, ['http'])  # Reduced timeout to 6s
                futures.append(future)
            
            completed = 0
            for future in as_completed(futures):
                result = future.result()
                completed += 1
                
                if result:
                    alive_proxies.append(result)
                    log_to_render(f"✅ ALIVE: {result['proxy_string']} | {result['speed']}s")
                
                # Progress trong chunk
                if completed % 100 == 0:
                    log_to_render(f"📊 Chunk {chunk_num}: {completed}/{len(chunk)} | Total alive: {len(alive_proxies)}")
        
        log_to_render(f"✅ Chunk {chunk_num} hoàn thành: {len(alive_proxies)} alive total")
        
        # Sleep giữa chunks để giảm load
        if i + CHUNK_SIZE < len(limited_proxies):
            log_to_render("😴 Nghỉ 2s giữa chunks...")
            time.sleep(2)
    
    log_to_render(f"🎉 VALIDATION HOÀN THÀNH: {len(alive_proxies)} alive từ {len(limited_proxies)} processed")
    return alive_proxies

def background_proxy_refresh():
    """Background task chạy mỗi 10 phút - tối ưu cho Render free plan"""
    while True:
        try:
            log_to_render("🔄 BẮT ĐẦU CHU KỲ REFRESH TỰ ĐỘNG (10 phút)")
            
            # Fetch proxies from sources
            raw_proxies, sources_count = fetch_proxies_from_sources()
            
            if raw_proxies:
                log_to_render(f"🎯 Lấy được {len(raw_proxies)} proxy từ {sources_count} nguồn")
                
                # Validate với chunk processing cho Render free 
                alive_proxies = validate_proxy_batch_smart(raw_proxies)
                
                # Update cache
                proxy_cache["http"] = alive_proxies
                proxy_cache["last_update"] = datetime.now().isoformat()
                proxy_cache["total_checked"] = min(len(raw_proxies), 800)  # Actual processed
                proxy_cache["alive_count"] = len(alive_proxies)
                proxy_cache["sources_processed"] = sources_count
                
                success_rate = round(len(alive_proxies)/proxy_cache["total_checked"]*100, 1) if proxy_cache["total_checked"] > 0 else 0
                log_to_render(f"✅ KẾT QUẢ: {len(alive_proxies)} PROXY SỐNG")
                log_to_render(f"📊 TỶ LỆ THÀNH CÔNG: {success_rate}% | {proxy_cache['total_checked']}/{len(raw_proxies)}")
            else:
                log_to_render("❌ Không fetch được proxy từ nguồn nào")
            
            # Sleep for 10 minutes
            log_to_render("😴 Nghỉ 10 phút trước chu kỳ tiếp theo...")
            time.sleep(10 * 60)
            
        except Exception as e:
            log_to_render(f"❌ LỖI REFRESH: {str(e)}")
            # Sleep 3 minutes on error
            time.sleep(3 * 60)

# API Routes
@app.route('/')
def home():
    """Homepage AUTO UPDATE - không có nút test/debug"""
    # Count total sources
    total_sources = len(PROXY_SOURCE_LINKS["categorized"]) + len(PROXY_SOURCE_LINKS["mixed"])
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>🚀 AUTO PROXY SERVICE</title>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }}
            .container {{ max-width: 900px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
            .stats {{ background: #e8f5e8; padding: 20px; border-radius: 8px; margin: 20px 0; border: 2px solid #4caf50; }}
            .live-count {{ font-size: 32px; color: #2e7d32; font-weight: bold; text-align: center; }}
            .success-rate {{ font-size: 18px; color: #ff6600; font-weight: bold; text-align: center; margin: 10px 0; }}
            .auto-status {{ background: #1976d2; color: white; padding: 15px; border-radius: 8px; text-align: center; margin: 15px 0; }}
            .endpoint {{ background: #f8f9fa; padding: 15px; margin: 15px 0; border-radius: 8px; border-left: 4px solid #007bff; }}
            .method {{ color: #fff; padding: 5px 10px; border-radius: 4px; font-size: 12px; font-weight: bold; }}
            .get {{ background: #28a745; }}
            .source-category {{ background: #f0f0f0; padding: 15px; border-radius: 8px; margin: 10px 0; }}
            .status {{ padding: 10px; margin: 10px 0; border-radius: 5px; }}
            .status-info {{ background: #e3f2fd; }}
            .status-success {{ background: #e8f5e8; }}
            .status-error {{ background: #ffebee; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 AUTO PROXY VALIDATION SERVICE</h1>
            
            <div class="auto-status">
                <h3>🔄 RENDER FREE PLAN - TỰ ĐỘNG</h3>
                <p>Service TỰ ĐỘNG xử lý proxy mỗi 10 phút từ {total_sources} nguồn</p>
                <p>✅ Timeout: 6s | Workers: 15 | Max: 800 proxy/cycle | Chunks: 300/batch</p>
                <p>🚀 Tối ưu cho Render free plan (512MB RAM)</p>
            </div>
            
            <div class="stats">
                <h3>📊 KẾT QUẢ LIVE:</h3>
                <div id="stats">Loading...</div>
            </div>
            
            <div id="system-status" class="status status-info">
                <strong>Trạng thái:</strong> <span id="current-status">Đang kiểm tra...</span>
            </div>
            
            <h2>📡 API Endpoints:</h2>
            
            <div class="endpoint">
                <span class="method get">GET</span>
                <strong>/api/proxy/alive</strong>
                <p>Lấy danh sách proxy sống từ cache tự động</p>
                <p>Params: <code>count</code> (số lượng, default: 50)</p>
            </div>
            
            <div class="endpoint">
                <span class="method get">GET</span>
                <strong>/api/proxy/stats</strong>
                <p>Thống kê chi tiết proxy và tỷ lệ thành công</p>
            </div>
            
            <h3>🔗 Nguồn Proxy ({total_sources} sources):</h3>
            
            <div class="source-category">
                <h4>📋 Categorized Sources (HTTP Protocol):</h4>
                <ul>
                    {chr(10).join([f'<li><strong>{name}</strong></li>' for name in PROXY_SOURCE_LINKS["categorized"].keys()])}
                </ul>
            </div>
            
            <div class="source-category">
                <h4>🔀 Mixed Sources (All Protocols):</h4>
                <ul>
                    {chr(10).join([f'<li><strong>{name}</strong></li>' for name in PROXY_SOURCE_LINKS["mixed"].keys()])}
                </ul>
            </div>
        </div>
        
        <script>
            function updateStats() {{
                fetch('/api/proxy/stats')
                    .then(r => r.json())
                    .then(data => {{
                        const successRate = data.total_checked > 0 ? (data.alive_count / data.total_checked * 100).toFixed(1) : '0';
                        document.getElementById('stats').innerHTML = 
                            '<div class="live-count">' + data.alive_count + ' PROXY SỐNG</div>' +
                            '<div class="success-rate">Tỷ lệ thành công: ' + successRate + '%</div>' +
                            '<p><strong>Tổng đã kiểm tra:</strong> ' + data.total_checked + ' proxies</p>' +
                            '<p><strong>Nguồn xử lý:</strong> ' + (data.sources_processed || 0) + '/' + data.sources_count + '</p>' +
                            '<p><strong>Lần check cuối:</strong> ' + (data.last_update ? new Date(data.last_update).toLocaleString() : 'Chưa check') + '</p>' +
                            '<p><strong>Tuổi cache:</strong> ' + (data.cache_age_minutes || 0) + ' phút (tự động làm mới mỗi 10 phút)</p>';
                        
                        // Update status
                        const statusEl = document.getElementById('current-status');
                        const statusContainer = document.getElementById('system-status');
                        
                        if (data.alive_count > 50) {{
                            statusEl.textContent = 'Service hoạt động tốt - ' + data.alive_count + ' proxy sống';
                            statusContainer.className = 'status status-success';
                        }} else if (data.alive_count > 0) {{
                            statusEl.textContent = 'Service hoạt động - ' + data.alive_count + ' proxy sống';
                            statusContainer.className = 'status status-info';
                        }} else {{
                            statusEl.textContent = 'Đang tìm proxy sống...';
                            statusContainer.className = 'status status-error';
                        }}
                    }})
                    .catch(e => {{
                        document.getElementById('stats').innerHTML = '<p style="color: red;">Service đang khởi động...</p>';
                    }});
            }}
            
            // Auto-update every 10 seconds
            updateStats();
            setInterval(updateStats, 10000);
        </script>
    </body>
    </html>
    """
    return html

@app.route('/api/proxy/alive', methods=['GET'])
def get_alive_proxies():
    """API chính - lấy danh sách proxy sống"""
    try:
        count = int(request.args.get('count', 50))
        
        alive_proxies = proxy_cache.get('http', [])
        
        # Sort by speed (fastest first)
        sorted_proxies = sorted(alive_proxies, key=lambda x: x.get('speed', 999))
        
        # Return requested count
        result_proxies = sorted_proxies[:count]
        
        return jsonify({
            'success': True,
            'total_available': len(alive_proxies),
            'returned_count': len(result_proxies),
            'proxies': result_proxies,
            'last_update': proxy_cache.get('last_update'),
            'timestamp': datetime.now().isoformat(),
            'sources_count': len(PROXY_SOURCE_LINKS["categorized"]) + len(PROXY_SOURCE_LINKS["mixed"])
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/proxy/stats', methods=['GET'])
def get_proxy_stats():
    """API thống kê proxy với thông tin chi tiết"""
    try:
        last_update = proxy_cache.get('last_update')
        cache_age_minutes = 0
        
        if last_update:
            last_update_dt = datetime.fromisoformat(last_update)
            cache_age_minutes = int((datetime.now() - last_update_dt).total_seconds() / 60)
        
        # Calculate success rate
        total_checked = proxy_cache.get('total_checked', 0)
        alive_count = len(proxy_cache.get('http', []))
        success_rate = round(alive_count / total_checked * 100, 2) if total_checked > 0 else 0
        
        # Count total sources
        total_sources = len(PROXY_SOURCE_LINKS["categorized"]) + len(PROXY_SOURCE_LINKS["mixed"])
        
        return jsonify({
            'success': True,
            'alive_count': alive_count,
            'total_checked': total_checked,
            'success_rate': success_rate,
            'last_update': last_update,
            'cache_age_minutes': cache_age_minutes,
            'sources_count': total_sources,
            'sources_processed': proxy_cache.get('sources_processed', 0),
            'categorized_sources': list(PROXY_SOURCE_LINKS["categorized"].keys()),
            'mixed_sources': list(PROXY_SOURCE_LINKS["mixed"].keys()),
            'service_status': 'render_free_optimized',
            'check_interval': '10 minutes',
            'timeout_setting': '6 seconds',
            'max_workers': 15,
            'processing_mode': 'CHUNK_PROCESSING_800_MAX',
            'chunk_size': 300,
            'render_plan': 'free_512mb'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    # Khởi tạo service
    log_to_render("🚀 KHỞI ĐỘNG PROXY VALIDATION SERVICE")
    log_to_render("🔧 Tối ưu cho Render free plan (512MB RAM)")
    
    # Start background refresh thread
    log_to_render("🔄 Khởi động background thread...")
    refresh_thread = threading.Thread(target=background_proxy_refresh, daemon=True)
    refresh_thread.start()
    
    # Initial proxy load - optimized for Render free
    log_to_render("📥 BẮT ĐẦU INITIAL LOAD...")
    try:
        initial_proxies, sources_count = fetch_proxies_from_sources()
        if initial_proxies:
            log_to_render(f"📊 Lấy được {len(initial_proxies)} proxy cho initial load")
            # Validate với chunk processing
            initial_alive = validate_proxy_batch_smart(initial_proxies)
            proxy_cache["http"] = initial_alive
            proxy_cache["last_update"] = datetime.now().isoformat()
            proxy_cache["total_checked"] = min(len(initial_proxies), 800)  # Actual processed
            proxy_cache["alive_count"] = len(initial_alive)
            proxy_cache["sources_processed"] = sources_count
            log_to_render(f"✅ INITIAL LOAD HOÀN THÀNH: {len(initial_alive)} proxy sống")
        else:
            log_to_render("❌ Không fetch được proxy trong initial load")
    except Exception as e:
        log_to_render(f"❌ LỖI INITIAL LOAD: {str(e)}")
    
    # Start Flask app
    port = int(os.environ.get('PORT', 5000))
    log_to_render(f"🌐 Khởi động Flask trên port {port}")
    app.run(host='0.0.0.0', port=port, debug=False) 