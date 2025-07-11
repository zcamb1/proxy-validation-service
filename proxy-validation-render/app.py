from flask import Flask, jsonify, request
import requests
import threading
import time
import json
import os
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import random
import sys
import traceback
from collections import deque

app = Flask(__name__)

# Global log buffer để store logs cho real-time display
log_buffer = deque(maxlen=500)  # Keep last 500 log entries
startup_status = {
    "initialized": False,
    "background_thread_started": False,
    "first_fetch_completed": False,
    "error_count": 0,
    "last_activity": None
}

# Cache proxy sống
proxy_cache = {
    "http": [],
    "last_update": None,
    "total_checked": 0,
    "alive_count": 0,
    "sources_processed": 0
}

# Nguồn proxy được phân loại với protocol rõ ràng - tối ưu cho Render free plan
PROXY_SOURCE_LINKS = {
    # Categorized sources - mỗi nguồn có protocol cụ thể
    "categorized": {
        "Server Alpha": {
            "http": "https://cdn.jsdelivr.net/gh/databay-labs/free-proxy-list/http.txt",
            "https": "https://cdn.jsdelivr.net/gh/databay-labs/free-proxy-list/https.txt", 
            "socks5": "https://cdn.jsdelivr.net/gh/databay-labs/free-proxy-list/socks5.txt",
        },
        "Network Beta": {
            "url": "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
            "protocol": "http"
        },
        "Gateway Pro": {
            "url": "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt", 
            "protocol": "http"
        },
        "Server Delta": {
            "url": "https://raw.githubusercontent.com/hookzof/socks5_list/master/proxy.txt",
            "protocol": "socks5"
        },
        "Server Echo": {
            "url": "https://api.proxyscrape.com/v2/?request=get&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all&format=textplain",
            "protocol": "http"
        },
        "Server Foxtrot": {
            "url": "https://www.proxy-list.download/api/v1/get?type=http",
            "protocol": "http"
        },
        "Server Golf": {
            "url": "https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt",
            "protocol": "http"
        },
    },
    # Mixed sources - test với tất cả protocols (http, https, socks4, socks5)
    "mixed": {
        "hendrikbgr": {
            "url": "https://raw.githubusercontent.com/hendrikbgr/Free-Proxy-Repo/master/proxy_list.txt",
            "protocols": ["http", "https", "socks4", "socks5"]
        },
        "MrMarble": {
            "url": "https://raw.githubusercontent.com/MrMarble/proxy-list/main/all.txt",
            "protocols": ["http", "https", "socks4", "socks5"]
        },
        "sunny9577": {
            "url": "https://raw.githubusercontent.com/sunny9577/proxy-scraper/master/proxies.txt",
            "protocols": ["http", "https", "socks4", "socks5"]
        }
    }
}

def log_to_render(message, level="INFO"):
    """Log với format rõ ràng cho Render logs và web display"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    log_msg = f"[{level}] {timestamp} | {message}"
    
    # Console log
    print(log_msg)
    sys.stdout.flush()
    
    # Web log buffer
    log_buffer.append({
        "timestamp": timestamp,
        "level": level,
        "message": message,
        "full_log": log_msg
    })
    
    # Update activity
    startup_status["last_activity"] = datetime.now().isoformat()

def initialize_service():
    """Initialize service - được gọi khi Flask app start"""
    if startup_status["initialized"]:
        return
        
    try:
        log_to_render("🚀 KHỞI ĐỘNG PROXY VALIDATION SERVICE")
        log_to_render("🔧 Tối ưu cho Render free plan (512MB RAM)")
        log_to_render("📋 Cấu hình: Timeout=6s, Workers=15, Chunks=300, Max=800")
        log_to_render(f"🔧 Service Process ID: {os.getpid()}")
        log_to_render("🔧 Gunicorn forced to 1 worker (cache shared)")
        
        # Test logging system
        log_to_render("🧪 TESTING LOG SYSTEM...")
        log_to_render("✅ Log system hoạt động!")
        
        # Test basic imports
        log_to_render("📦 Testing imports...")
        import threading
        import requests
        import time
        log_to_render("✅ All imports OK!")
        
        # Test functions exist
        log_to_render("🔧 Testing functions...")
        if callable(background_proxy_refresh):
            log_to_render("✅ background_proxy_refresh function OK")
        if callable(fetch_proxies_from_sources):
            log_to_render("✅ fetch_proxies_from_sources function OK")
        if callable(validate_proxy_batch_smart):
            log_to_render("✅ validate_proxy_batch_smart function OK")
            
        # Start background thread
        log_to_render("🔄 ĐANG KHỞI ĐỘNG BACKGROUND THREAD...")
        try:
            log_to_render("🧵 Creating thread object...")
            refresh_thread = threading.Thread(target=background_proxy_refresh, daemon=True)
            log_to_render("🧵 Thread object created successfully")
            
            log_to_render("🚀 Starting thread...")
            refresh_thread.start()
            log_to_render("✅ Background thread started!")
            
            # Verify thread is running
            if refresh_thread.is_alive():
                log_to_render("✅ Background thread confirmed ALIVE!")
                startup_status["background_thread_started"] = True
            else:
                log_to_render("❌ Background thread not alive!")
                startup_status["error_count"] += 1
                
        except Exception as e:
            log_to_render(f"❌ LỖI CRITICAL khởi động background thread: {str(e)}")
            log_to_render(f"📍 Thread Error Traceback: {traceback.format_exc()}")
            startup_status["error_count"] += 1
        
        # Set empty cache initially
        log_to_render("💾 Setting initial empty cache...")
        proxy_cache["http"] = []
        proxy_cache["last_update"] = datetime.now().isoformat()
        proxy_cache["total_checked"] = 0
        proxy_cache["alive_count"] = 0
        proxy_cache["sources_processed"] = 0
        
        startup_status["initialized"] = True
        log_to_render("✅ SERVICE INITIALIZATION COMPLETED!")
        log_to_render("🔄 Background thread sẽ tự động fetch proxy...")
        
    except Exception as e:
        log_to_render(f"❌ LỖI CRITICAL INITIALIZATION: {str(e)}")
        log_to_render(f"📍 Init Traceback: {traceback.format_exc()}")
        startup_status["error_count"] += 1

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
    categorized_proxies = []
    mixed_proxies = []
    sources_processed = 0
    
    log_to_render("🔍 BẮT ĐẦU FETCH PROXY TỪ CÁC NGUỒN...")
    log_to_render(f"📋 Tổng {len(PROXY_SOURCE_LINKS['categorized'])} categorized + {len(PROXY_SOURCE_LINKS['mixed'])} mixed sources")
    
    # Xử lý categorized sources trước (ưu tiên)
    log_to_render("📥 Xử lý CATEGORIZED sources...")
    for source_name, source_config in PROXY_SOURCE_LINKS["categorized"].items():
        try:
            # Check if source has multiple protocols (Server Alpha style) or single protocol
            if "url" in source_config and "protocol" in source_config:
                # Single protocol format
                source_url = source_config["url"]
                source_protocol = source_config["protocol"]
                protocols_to_fetch = [(source_protocol, source_url)]
            else:
                # Multiple protocols format (Server Alpha style)
                protocols_to_fetch = [(protocol, url) for protocol, url in source_config.items()]
            
            source_total_proxies = []
            
            for source_protocol, source_url in protocols_to_fetch:
                log_to_render(f"📡 Fetching {source_name} - {source_protocol}...")
                
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
                                    source_proxies.append(('categorized', line, source_protocol))
                                    
                            except:
                                continue
                    
                    source_total_proxies.extend(source_proxies)
                    log_to_render(f"✅ {source_name} - {source_protocol}: {len(source_proxies)} proxy")
                else:
                    log_to_render(f"❌ {source_name} - {source_protocol}: HTTP {response.status_code}")
            
            categorized_proxies.extend(source_total_proxies)
            sources_processed += 1
            log_to_render(f"🎯 {source_name} TOTAL: {len(source_total_proxies)} proxy from {len(protocols_to_fetch)} protocols")
        
        except Exception as e:
            log_to_render(f"❌ {source_name}: {str(e)}")
            continue
    
    # Xử lý mixed sources sau
    log_to_render("📥 Xử lý MIXED sources...")
    for source_name, source_config in PROXY_SOURCE_LINKS["mixed"].items():
        try:
            source_url = source_config["url"]
            source_protocols = source_config["protocols"]
            log_to_render(f"📡 Fetching {source_name} (protocols: {', '.join(source_protocols)})...")
            
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
                                source_proxies.append(('mixed', line, source_protocols))
                                
                        except:
                            continue
                
                mixed_proxies.extend(source_proxies)
                sources_processed += 1
                log_to_render(f"✅ {source_name} ({', '.join(source_protocols)}): {len(source_proxies)} proxy")
            else:
                log_to_render(f"❌ {source_name}: HTTP {response.status_code}")
        
        except Exception as e:
            log_to_render(f"❌ {source_name}: {str(e)}")
            continue
    
    # Combine và shuffle
    all_proxies = categorized_proxies + mixed_proxies
    random.shuffle(all_proxies)
    limited_proxies = all_proxies[:800]  # Giới hạn 800 proxy để không quá tải
    
    log_to_render(f"🎯 HOÀN THÀNH FETCH: {len(all_proxies)} total → {len(limited_proxies)} selected")
    log_to_render(f"📊 Đã xử lý {sources_processed} nguồn thành công")
    log_to_render(f"📋 Categorized: {len(categorized_proxies)}, Mixed: {len(mixed_proxies)}")
    
    return limited_proxies, sources_processed

def validate_proxy_batch_smart(proxy_list, max_workers=15):
    """Validate proxies theo batch với real-time logging - tối ưu cho Render"""
    if not proxy_list:
        log_to_render("⚠️ Không có proxy để validate")
        return []
    
    # Sử dụng global cache để update real-time
    global proxy_cache
    alive_proxies = []
    chunk_size = 300  # Process theo chunks
    total_proxies = len(proxy_list)
    
    log_to_render(f"⚡ BẮT ĐẦU VALIDATE {total_proxies} PROXY")
    log_to_render(f"🔧 Cấu hình: {max_workers} workers, chunks={chunk_size}")
    log_to_render(f"🔧 Validate Process ID: {os.getpid()}")
    
    # Reset cache trước khi validate
    proxy_cache["total_checked"] = 0
    proxy_cache["alive_count"] = 0
    
    # Process theo chunks để tránh overload
    for chunk_start in range(0, total_proxies, chunk_size):
        chunk_end = min(chunk_start + chunk_size, total_proxies)
        chunk = proxy_list[chunk_start:chunk_end]
        
        # Count proxy types in chunk
        categorized_count = sum(1 for item in chunk if isinstance(item, tuple) and item[0] == 'categorized')
        mixed_count = sum(1 for item in chunk if isinstance(item, tuple) and item[0] == 'mixed')
        
        log_to_render(f"📦 Chunk {chunk_start//chunk_size + 1}: Validate {len(chunk)} proxy (từ {chunk_start+1} đến {chunk_end})")
        log_to_render(f"🔧 Chunk protocols: {categorized_count} categorized(specific) + {mixed_count} mixed(all)")
        
        chunk_alive = []
        checked_count = 0
        
        # Validate chunk với ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit tất cả proxy trong chunk
            future_to_proxy = {}
            for proxy_data in chunk:
                # Unpack proxy data với structure mới
                if isinstance(proxy_data, tuple) and len(proxy_data) == 3:
                    proxy_type, proxy_string, protocols_info = proxy_data
                else:
                    # Fallback for old format
                    proxy_type, proxy_string, protocols_info = 'categorized', proxy_data, 'http'
                
                # Xác định protocols để test dựa trên source type
                if proxy_type == 'mixed':
                    protocols = protocols_info  # Mixed sources sử dụng protocols từ config
                else:
                    protocols = [protocols_info]  # Categorized sources sử dụng protocol cụ thể
                
                future = executor.submit(check_single_proxy, proxy_string, 6, protocols)
                future_to_proxy[future] = (proxy_type, proxy_string, protocols_info)
            
            # Collect results với progress tracking
            for future in as_completed(future_to_proxy):
                checked_count += 1
                proxy_type, proxy_string, protocols_info = future_to_proxy[future]
                
                try:
                    result = future.result()
                    if result:
                        chunk_alive.append(result)
                        alive_proxies.append(result)
                        
                        # Update cache REALTIME với tất cả proxy sống tìm được
                        proxy_cache["http"] = alive_proxies.copy()
                        proxy_cache["alive_count"] = len(alive_proxies)
                        proxy_cache["total_checked"] = chunk_start + checked_count
                        proxy_cache["last_update"] = datetime.now().isoformat()
                        
                        # Debug log cache update + FORCE GLOBAL UPDATE
                        if len(alive_proxies) <= 5:  # Only log first few for debugging
                            log_to_render(f"🔧 CACHE UPDATE: alive_count={len(alive_proxies)}, total_checked={chunk_start + checked_count}")
                            log_to_render(f"🔧 FORCE UPDATE GLOBAL: Process {os.getpid()}")
                            # Force update globals để debug
                            globals()['proxy_cache'] = proxy_cache
                        
                        # Format protocols info for display
                        if proxy_type == 'mixed':
                            protocols_display = f"mixed|{result['type']}"
                        else:
                            protocols_display = f"{protocols_info}|{result['type']}"
                            
                        log_to_render(f"✅ SỐNG ({protocols_display}): {result['host']}:{result['port']} ({result['speed']}s) [{checked_count}/{len(chunk)}]")
                    else:
                        # Update total checked even for failed
                        proxy_cache["total_checked"] = chunk_start + checked_count
                        
                        if checked_count % 50 == 0:  # Log mỗi 50 proxy để không spam
                            log_to_render(f"⏳ Progress: {checked_count}/{len(chunk)} checked, {len(chunk_alive)} alive")
                            
                except Exception as e:
                    proxy_cache["total_checked"] = chunk_start + checked_count
                    if checked_count % 100 == 0:  # Log errors occasionally
                        log_to_render(f"❌ Error checking proxy: {str(e)}")
        
        chunk_success_rate = round(len(chunk_alive)/len(chunk)*100, 1) if chunk else 0
        
        log_to_render(f"📊 Chunk {chunk_start//chunk_size + 1} hoàn thành: {len(chunk_alive)} alive / {len(chunk)} total ({chunk_success_rate}%)")
        
        # Sleep giữa các chunks để CPU nghỉ
        if chunk_end < total_proxies:
            log_to_render("😴 Sleep 2s giữa chunks...")
            time.sleep(2)
    
    # Final cache update
    proxy_cache["http"] = alive_proxies.copy()
    proxy_cache["alive_count"] = len(alive_proxies)
    proxy_cache["total_checked"] = total_proxies
    proxy_cache["last_update"] = datetime.now().isoformat()
    
    # Debug final cache state
    log_to_render(f"🔧 FINAL CACHE UPDATE: alive_count={len(alive_proxies)}, total_checked={total_proxies}")
    log_to_render(f"🔧 FINAL proxy_cache state: alive_count={proxy_cache.get('alive_count')}, total_checked={proxy_cache.get('total_checked')}")
    
    success_rate = round(len(alive_proxies)/total_proxies*100, 1) if total_proxies > 0 else 0
    log_to_render(f"🎯 VALIDATION HOÀN THÀNH!")
    log_to_render(f"📊 Kết quả: {len(alive_proxies)} alive / {total_proxies} total ({success_rate}%)")
    
    return alive_proxies

def background_proxy_refresh():
    """Background thread để refresh proxy cache định kỳ - tối ưu cho Render"""
    log_to_render("🔄 BACKGROUND THREAD KHỞI ĐỘNG")
    
    # Wait a bit for service to stabilize
    log_to_render("⏳ Waiting 10 seconds for service stabilization...")
    time.sleep(10)
    
    while True:
        try:
            log_to_render("=" * 50)
            log_to_render("🔄 BẮT ĐẦU CHU KỲ REFRESH MỚI")
            log_to_render("=" * 50)
            
            start_time = time.time()
            
            # Fetch proxies từ sources
            log_to_render("📥 Fetching proxies từ tất cả nguồn...")
            proxy_list, sources_count = fetch_proxies_from_sources()
            
            if proxy_list:
                log_to_render(f"📊 Fetch thành công: {len(proxy_list)} proxy từ {sources_count} nguồn")
                
                # Validate proxies
                log_to_render("⚡ Bắt đầu validation...")
                alive_proxies = validate_proxy_batch_smart(proxy_list)
                
                # Cache đã được update real-time trong validate function
                # Chỉ cần update sources_processed
                proxy_cache["sources_processed"] = sources_count
                
                cycle_time = round(time.time() - start_time, 1)
                success_rate = round(len(alive_proxies)/len(proxy_list)*100, 1) if proxy_list else 0
                
                startup_status["first_fetch_completed"] = True
                
                log_to_render("=" * 50)
                log_to_render("✅ CHU KỲ REFRESH HOÀN THÀNH!")
                log_to_render(f"⏱️ Thời gian: {cycle_time}s")
                log_to_render(f"📊 Kết quả: {len(alive_proxies)} alive / {len(proxy_list)} total")
                log_to_render(f"📈 Tỷ lệ thành công: {success_rate}%")
                log_to_render(f"🔄 Tiếp theo trong 10 phút...")
                log_to_render("=" * 50)
                
            else:
                log_to_render("❌ THẤT BẠI: Không fetch được proxy nào")
                log_to_render("🔄 Thử lại trong 10 phút...")
            
        except Exception as e:
            log_to_render(f"❌ LỖI BACKGROUND REFRESH: {str(e)}")
            log_to_render(f"📍 Traceback: {traceback.format_exc()}")
            log_to_render("🔄 Tiếp tục vòng lặp...")
            startup_status["error_count"] += 1
        
        # Sleep 10 phút trước chu kỳ tiếp theo
        log_to_render("😴 Sleep 10 phút trước chu kỳ tiếp theo...")
        time.sleep(600)  # 10 minutes

# Initialize service when Flask starts
initialize_service()

@app.route('/')
def home():
    """UI chính với real-time logs"""
    html = f"""
    <!DOCTYPE html>
    <html lang="vi">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Proxy Validation Service - Real Time</title>
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 0;
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                color: white;
            }}
            .container {{
                max-width: 1400px;
                margin: 0 auto;
                background: rgba(255, 255, 255, 0.1);
                backdrop-filter: blur(10px);
                border-radius: 20px;
                padding: 30px;
                box-shadow: 0 8px 32px rgba(31, 38, 135, 0.37);
                border: 1px solid rgba(255, 255, 255, 0.18);
            }}
            .header {{
                text-align: center;
                margin-bottom: 30px;
                padding-bottom: 20px;
                border-bottom: 2px solid rgba(255, 255, 255, 0.2);
            }}
            .header h1 {{
                margin: 0;
                font-size: 2.5em;
                background: linear-gradient(45deg, #fff, #f0f0f0);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
            }}
            .status {{
                text-align: center;
                padding: 15px;
                border-radius: 10px;
                margin: 20px 0;
                font-weight: bold;
                font-size: 1.2em;
            }}
            .status-success {{
                background: rgba(76, 175, 80, 0.3);
                border: 2px solid #4CAF50;
            }}
            .status-info {{
                background: rgba(33, 150, 243, 0.3);
                border: 2px solid #2196F3;
            }}
            .status-error {{
                background: rgba(244, 67, 54, 0.3);
                border: 2px solid #f44336;
            }}
            .grid {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 20px;
                margin-top: 30px;
            }}
            .card {{
                background: rgba(255, 255, 255, 0.1);
                border-radius: 15px;
                padding: 20px;
                border: 1px solid rgba(255, 255, 255, 0.2);
            }}
            .card h3 {{
                margin-top: 0;
                color: #fff;
                border-bottom: 2px solid rgba(255, 255, 255, 0.3);
                padding-bottom: 10px;
            }}
            .logs-container {{
                grid-column: 1 / -1;
                background: rgba(0, 0, 0, 0.3);
                border-radius: 15px;
                padding: 20px;
                max-height: 500px;
                overflow-y: auto;
            }}
            .log-entry {{
                font-family: 'Courier New', monospace;
                font-size: 0.9em;
                margin: 2px 0;
                padding: 3px 8px;
                border-radius: 4px;
                word-wrap: break-word;
            }}
            .log-INFO {{ background: rgba(33, 150, 243, 0.2); }}
            .log-ERROR {{ background: rgba(244, 67, 54, 0.3); }}
            .log-SUCCESS {{ background: rgba(76, 175, 80, 0.2); }}
            .update-time {{
                font-size: 0.9em;
                opacity: 0.8;
                text-align: center;
                margin-top: 20px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🚀 Proxy Validation Service</h1>
                <p>Real-time monitoring và logging - Tối ưu cho Render Free Plan</p>
            </div>
            
            <div id="system-status" class="status status-error">
                <div id="current-status">Đang khởi động service...</div>
            </div>
            
            <div class="grid">
                <div class="card">
                    <h3>📊 Thống Kê Proxy</h3>
                    <div id="stats">
                        <p>Đang tải...</p>
                    </div>
                </div>
                
                <div class="card">
                    <h3>⚙️ Trạng Thái Hệ Thống</h3>
                    <div id="system-info">
                        <p>Đang tải...</p>
                    </div>
                </div>
                
                <div class="logs-container">
                    <h3>📜 Real-Time Logs</h3>
                    <div id="logs" style="max-height: 400px; overflow-y: auto;">
                        <p>Đang tải logs...</p>
                    </div>
                </div>
            </div>
            
            <div class="update-time">
                <p>⏱️ Tự động cập nhật mỗi 5 giây | 🔄 Logs real-time</p>
                <p>📊 Service monitoring với chi tiết từng bước</p>
            </div>
        </div>
        
        <script>
            function updateStats() {{
                fetch('/api/proxy/stats')
                    .then(response => response.json())
                    .then(data => {{
                        // Update stats
                        document.getElementById('stats').innerHTML = 
                            '<p><strong>Proxy sống:</strong> ' + data.alive_count + '</p>' +
                            '<p><strong>Tổng đã check:</strong> ' + data.total_checked + '</p>' +
                            '<p><strong>Tỷ lệ thành công:</strong> ' + data.success_rate + '%</p>' +
                            '<p><strong>Nguồn đã xử lý:</strong> ' + data.sources_processed + '/' + data.sources_count + '</p>' +
                            '<p><strong>Lần check cuối:</strong> ' + (data.last_update ? new Date(data.last_update).toLocaleString() : 'Chưa check') + '</p>';
                        
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
            
            function updateLogs() {{
                fetch('/api/logs')
                    .then(response => response.json())
                    .then(data => {{
                        const logsContainer = document.getElementById('logs');
                        
                        if (data.logs && data.logs.length > 0) {{
                            logsContainer.innerHTML = data.logs.map(log => 
                                '<div class="log-entry log-' + log.level + '">' + log.full_log + '</div>'
                            ).join('');
                            logsContainer.scrollTop = logsContainer.scrollHeight;
                        }}
                        
                        // Update system info
                        document.getElementById('system-info').innerHTML = 
                            '<p><strong>Khởi tạo:</strong> ' + (data.startup.initialized ? '✅' : '❌') + '</p>' +
                            '<p><strong>Background Thread:</strong> ' + (data.startup.background_thread_started ? '✅' : '❌') + '</p>' +
                            '<p><strong>First Fetch:</strong> ' + (data.startup.first_fetch_completed ? '✅' : '❌') + '</p>' +
                            '<p><strong>Errors:</strong> ' + data.startup.error_count + '</p>' +
                            '<p><strong>Hoạt động cuối:</strong> ' + (data.startup.last_activity ? new Date(data.startup.last_activity).toLocaleTimeString() : 'N/A') + '</p>';
                    }})
                    .catch(e => {{
                        console.log('Error fetching logs:', e);
                    }});
            }}
            
            // Update every 5 seconds
            updateStats();
            updateLogs();
            setInterval(updateStats, 5000);
            setInterval(updateLogs, 3000);  // Logs update faster
        </script>
    </body>
    </html>
    """
    return html

@app.route('/api/logs', methods=['GET'])
def get_logs():
    """API để lấy real-time logs"""
    try:
        log_to_render("🔍 API /logs được gọi")
        
        # Return recent logs
        recent_logs = list(log_buffer)[-100:]  # Last 100 logs
        
        return jsonify({
            'success': True,
            'logs': recent_logs,
            'total_logs': len(log_buffer),
            'startup': startup_status,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

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
            'sources_count': len(PROXY_SOURCE_LINKS["categorized"]) + len(PROXY_SOURCE_LINKS["mixed"]),
            'cache_alive_count': proxy_cache.get('alive_count', 0)
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
        # Log để debug khi có request
        log_to_render("📊 API /stats được gọi")
        log_to_render(f"🔧 Process ID: {os.getpid()}")
        
        last_update = proxy_cache.get('last_update')
        cache_age_minutes = 0
        
        if last_update:
            last_update_dt = datetime.fromisoformat(last_update)
            cache_age_minutes = int((datetime.now() - last_update_dt).total_seconds() / 60)
        
        # Get from cache - now properly updated
        total_checked = proxy_cache.get('total_checked', 0)
        alive_count = proxy_cache.get('alive_count', 0)
        success_rate = round(alive_count / total_checked * 100, 2) if total_checked > 0 else 0
        
        # Count total sources
        total_sources = len(PROXY_SOURCE_LINKS["categorized"]) + len(PROXY_SOURCE_LINKS["mixed"])
        
        log_to_render(f"📈 Stats: {alive_count} alive, {total_checked} checked, {success_rate}% success")
        log_to_render(f"🔍 Cache details: http_list={len(proxy_cache.get('http', []))}, alive_count_cache={proxy_cache.get('alive_count', 0)}")
        log_to_render(f"🔍 Full cache state: {proxy_cache}")
        
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
        log_to_render(f"❌ Lỗi API stats: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/proxies', methods=['GET'])
def get_proxies_simple():
    """API đơn giản để lấy proxy sống - cho tool sử dụng"""
    try:
        count = int(request.args.get('count', 100))
        format_type = request.args.get('format', 'json')  # json hoặc text
        
        # Lấy từ cache hoặc trả về empty nếu cache rỗng
        alive_proxies = proxy_cache.get('http', [])
        
        if not alive_proxies:
            # Nếu cache rỗng, có thể return empty nhưng log để debug
            log_to_render(f"🔍 API /proxies called - cache empty, process {os.getpid()}")
            return jsonify({
                'success': False,
                'message': 'No live proxies available yet. Service is still validating.',
                'count': 0,
                'proxies': [],
                'cache_status': 'empty',
                'process_id': os.getpid()
            })
        
        # Sort by speed và lấy số lượng yêu cầu
        sorted_proxies = sorted(alive_proxies, key=lambda x: x.get('speed', 999))[:count]
        
        if format_type == 'text':
            # Format text: host:port per line
            proxy_list = [f"{p['host']}:{p['port']}" for p in sorted_proxies]
            return '\n'.join(proxy_list), 200, {'Content-Type': 'text/plain'}
        
        # Format JSON (default)
        return jsonify({
            'success': True,
            'count': len(sorted_proxies),
            'total_available': len(alive_proxies),
            'proxies': [
                {
                    'host': p['host'],
                    'port': p['port'],
                    'type': p['type'],
                    'speed': p['speed'],
                    'proxy': f"{p['host']}:{p['port']}"
                } for p in sorted_proxies
            ],
            'last_update': proxy_cache.get('last_update'),
            'process_id': os.getpid()
        })
        
    except Exception as e:
        log_to_render(f"❌ API /proxies error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'process_id': os.getpid()
        }), 500

@app.route('/api/debug', methods=['GET'])
def debug_cache():
    """Debug cache để kiểm tra vấn đề"""
    log_to_render("🔧 DEBUG cache được gọi")
    
    return jsonify({
        'process_id': os.getpid(),
        'proxy_cache': proxy_cache,
        'cache_http_length': len(proxy_cache.get('http', [])),
        'cache_alive_count': proxy_cache.get('alive_count', 0),
        'cache_total_checked': proxy_cache.get('total_checked', 0),
        'startup_status': startup_status,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint để test service"""
    log_to_render("💓 Health check được gọi")
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'cache_count': len(proxy_cache.get('http', [])),
        'service': 'proxy-validation-render',
        'startup_status': startup_status
    })

if __name__ == '__main__':
    # Render production mode
    try:
        port = int(os.environ.get('PORT', 5000))
        log_to_render("🚀 STARTING RENDER PRODUCTION MODE")
        log_to_render(f"🔧 Port: {port}")
        app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
    except Exception as e:
        log_to_render(f"❌ LỖI PRODUCTION: {str(e)}")
        print(f"Error: {e}") 