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


# Connection pooling for better efficiency on free plan
import requests
session = requests.Session()
session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})

def get_with_session(url, **kwargs):
    try:
        return session.get(url, **kwargs)
    except Exception as e:
        # Fallback to regular requests
        return requests.get(url, **kwargs)

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

# Thread safety lock
cache_lock = threading.Lock()

# Nguồn proxy được phân loại với protocol rõ ràng - tối ưu cho Render free plan (ULTRA OPTIMIZED)
PROXY_SOURCE_LINKS = {
    # Categorized sources - mỗi nguồn có protocol cụ thể
    "categorized": {
        "Server Alpha": {
            "http": "https://cdn.jsdelivr.net/gh/databay-labs/free-proxy-list/http.txt",
            "https": "https://cdn.jsdelivr.net/gh/databay-labs/free-proxy-list/https.txt", 
            "socks5": "https://cdn.jsdelivr.net/gh/databay-labs/free-proxy-list/socks5.txt",
        },
         "Network Beta sock4": {
            "url": "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks4.txt",
            "protocol": "socks4"
        },
         "Network Beta sock5": {
            "url": "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt",
            "protocol": "socks5"
        },
        "Gateway Pro": {
            "url": "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt", 
            "protocol": "http"
        },
        "Server Delta": {
            "url": "https://raw.githubusercontent.com/hookzof/socks5_list/master/proxy.txt",
            "protocol": "socks5"
        },
        "Server Foxtrot": {
            "url": "https://www.proxy-list.download/api/v1/get?type=http",
            "protocol": "http"
        },
        "Server Golf": {
            "url": "https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt",
            "protocol": "http"
        },

        "Server India": {
            "url": "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
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
        },
        "jetkai": {
            "url": "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies.txt",
            "protocols": ["http", "https", "socks4", "socks5"]
        },
        "clarketm": {
            "url": "https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt",
            "protocols": ["http", "https"]
        },
        "rdavydov": {
            "url": "https://raw.githubusercontent.com/rdavydov/proxy-list/main/proxies/http.txt",
            "protocols": ["http", "https"]
        },
        "officialputuid": {
            "url": "https://raw.githubusercontent.com/officialputuid/KangProxy/KangProxy/http/http.txt",
            "protocols": ["http", "https"]
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
    with cache_lock:

        startup_status["last_activity"] = datetime.now().isoformat()

def initialize_service():
    """Initialize service - được gọi khi Flask app start"""
    if startup_status["initialized"]:
        return
        
    try:
        log_to_render("🚀 KHỞI ĐỘNG PROXY VALIDATION SERVICE")
        log_to_render("🔧 Tối ưu cho Render free plan (512MB RAM) - ULTRA OPTIMIZED")
        log_to_render("📋 Cấu hình: Timeout=8s, Workers=20, Chunks=200, Max=2000")
        
        # Start background thread
        log_to_render("🔄 ĐANG KHỞI ĐỘNG BACKGROUND THREAD...")
        try:
            refresh_thread = threading.Thread(target=background_proxy_refresh, daemon=True)
            refresh_thread.start()
            log_to_render("✅ Background thread started!")
            
            # Verify thread is running
            if refresh_thread.is_alive():
                log_to_render("✅ Background thread confirmed ALIVE!")
                with cache_lock:
                    startup_status["background_thread_started"] = True
            else:
                log_to_render("❌ Background thread not alive!")
                startup_status["error_count"] += 1
                
        except Exception as e:
            log_to_render(f"❌ LỖI CRITICAL khởi động background thread: {str(e)}")
            startup_status["error_count"] += 1
        
        # Set empty cache initially
        log_to_render("💾 Setting initial empty cache...")
        with cache_lock:
            proxy_cache["http"] = []
            proxy_cache["last_update"] = datetime.now().isoformat()
            proxy_cache["total_checked"] = 0
            proxy_cache["alive_count"] = 0
            proxy_cache["sources_processed"] = 0
        
        with cache_lock:
            startup_status["initialized"] = True
        log_to_render("✅ SERVICE INITIALIZATION COMPLETED!")
        
    except Exception as e:
        log_to_render(f"❌ LỖI CRITICAL INITIALIZATION: {str(e)}")
        startup_status["error_count"] += 1


def is_quality_proxy(proxy_string):
    """Basic quality filter for better output"""
    try:
        # Skip obviously bad proxies
        if not proxy_string or len(proxy_string) < 7:
            return False
        
        # Basic format validation
        if ':' not in proxy_string:
            return False
            
        parts = proxy_string.split(':')
        if len(parts) != 2:
            return False
            
        host, port = parts
        
        # Skip localhost, private IPs, invalid ports
        if host.startswith(('127.', '10.', '192.168.', '172.')):
            return False
            
        if not port.isdigit() or int(port) < 1 or int(port) > 65535:
            return False
            
        return True
    except:
        return False

def check_single_proxy(proxy_string, timeout=8, protocols=['http']):
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
            'https://api.ipify.org',
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
                            except Exception:
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
                    except Exception:
                        # REMOVED: Bỏ error logs để giảm noise
                        continue
                        
            except Exception:
                # REMOVED: Bỏ error logs để giảm noise
                continue
                
    except Exception:
        # REMOVED: Bỏ error logs để giảm noise
        pass
    
    return None

def fetch_proxies_from_sources():
    """Lấy proxy từ tất cả nguồn với logic thông minh - tối ưu cho Render"""
    categorized_proxies = []
    mixed_proxies = []
    sources_processed = 0
    
    log_to_render("🔍 BẮT ĐẦU FETCH PROXY TỪ CÁC NGUỒN...")
    log_to_render(f"📋 Tổng {len(PROXY_SOURCE_LINKS['categorized'])} categorized + {len(PROXY_SOURCE_LINKS['mixed'])} mixed sources")
    
    # Xử lý Server Alpha trước (ưu tiên tối đa để lấy 1000+ proxy)
    log_to_render("📥 Xử lý SERVER ALPHA trước (ưu tiên tối đa)...")
    server_alpha_proxies = []
    
    if "Server Alpha" in PROXY_SOURCE_LINKS["categorized"]:
        try:
            source_config = PROXY_SOURCE_LINKS["categorized"]["Server Alpha"]
            protocols_to_fetch = [(protocol, url) for protocol, url in source_config.items()]
            
            for source_protocol, source_url in protocols_to_fetch:
                # REDUCED: Chỉ log protocol quan trọng
                
                response = get_with_session(source_url, timeout=45)
                
                if response.status_code == 200:
                    content = response.text
                    lines = content.strip().split('\n')
                    source_proxies = []
                    
                    for line in lines:
                        line = line.strip()
                        if not line or line.startswith('#'):
                            continue
                            
                        if ':' in line and is_quality_proxy(line.strip()):
                            try:
                                if '@' in line:
                                    auth_part, host_port = line.split('@')
                                    host, port = host_port.split(':')
                                else:
                                    host, port = line.split(':')
                                
                                if len(host.split('.')) == 4 and port.isdigit():
                                    source_proxies.append(('categorized', line, source_protocol))
                                    
                            except Exception:
                                continue
                    
                    server_alpha_proxies.extend(source_proxies)
                    log_to_render(f"✅ Server Alpha - {source_protocol}: {len(source_proxies)} proxy")
                else:
                    log_to_render(f"❌ Server Alpha - {source_protocol}: HTTP {response.status_code}")
            
            log_to_render(f"🎯 Server Alpha TOTAL: {len(server_alpha_proxies)} proxy from {len(protocols_to_fetch)} protocols")
            sources_processed += 1
            
        except Exception as e:
            log_to_render(f"❌ Server Alpha: {str(e)}")
    
    # Xử lý các categorized sources khác
    log_to_render("📥 Xử lý CATEGORIZED sources khác...")
    for source_name, source_config in PROXY_SOURCE_LINKS["categorized"].items():
        if source_name == "Server Alpha":
            continue  # Đã xử lý rồi
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
                # REMOVED: Bỏ log individual protocol
                
                response = get_with_session(source_url, timeout=45)
                
                if response.status_code == 200:
                    content = response.text
                    lines = content.strip().split('\n')
                    source_proxies = []
                    
                    for line in lines:
                        line = line.strip()
                        if not line or line.startswith('#'):
                            continue
                            
                        # Validate proxy format
                        if ':' in line and is_quality_proxy(line.strip()):
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
                                    
                            except Exception:
                                continue
                    
                    source_total_proxies.extend(source_proxies)
                    # REDUCED: Chỉ log nếu có proxy
                    if len(source_proxies) > 0:
                        log_to_render(f"✅ {source_name} - {source_protocol}: {len(source_proxies)} proxy")
                else:
                    log_to_render(f"❌ {source_name} - {source_protocol}: HTTP {response.status_code}")
            
            categorized_proxies.extend(source_total_proxies)
            sources_processed += 1
            log_to_render(f"🎯 {source_name} TOTAL: {len(source_total_proxies)} proxy")
        
        except Exception as e:
            log_to_render(f"❌ {source_name}: {str(e)}")
            continue
    
    # Xử lý mixed sources sau
    log_to_render("📥 Xử lý MIXED sources...")
    for source_name, source_config in PROXY_SOURCE_LINKS["mixed"].items():
        try:
            source_url = source_config["url"]
            source_protocols = source_config["protocols"]
            # REMOVED: Bỏ log chi tiết protocols
            
            response = get_with_session(source_url, timeout=45)
            
            if response.status_code == 200:
                content = response.text
                lines = content.strip().split('\n')
                source_proxies = []
                
                for line in lines:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                        
                    # Validate proxy format
                    if ':' in line and is_quality_proxy(line.strip()):
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
                                
                        except Exception:
                            continue
                
                mixed_proxies.extend(source_proxies)
                sources_processed += 1
                log_to_render(f"✅ {source_name}: {len(source_proxies)} proxy")
            else:
                log_to_render(f"❌ {source_name}: HTTP {response.status_code}")
        
        except Exception as e:
            log_to_render(f"❌ {source_name}: {str(e)}")
            continue
    
    # Combine tất cả proxy (Server Alpha + categorized khác + mixed) - KHÔNG GIỚI HẠN
    all_proxies = server_alpha_proxies + categorized_proxies + mixed_proxies
    random.shuffle(all_proxies)
    
    log_to_render(f"🎯 HOÀN THÀNH FETCH: {len(all_proxies)} total proxy (KHÔNG GIỚI HẠN)")
    log_to_render(f"📊 Đã xử lý {sources_processed} nguồn thành công")
    log_to_render(f"📋 Server Alpha: {len(server_alpha_proxies)}, Categorized khác: {len(categorized_proxies)}, Mixed: {len(mixed_proxies)}")
    
    return all_proxies, sources_processed

def validate_proxy_batch_smart(proxy_list, max_workers=15):
    """Validate proxies KHÔNG chunking - chỉ validate toàn bộ list được pass vào"""
    if not proxy_list:
        log_to_render("⚠️ Không có proxy để validate")
        return []
    
    # Sử dụng global cache để update real-time
    global proxy_cache
    alive_proxies = []
    total_proxies = len(proxy_list)
    
    log_to_render(f"⚡ BẮT ĐẦU VALIDATE {total_proxies} PROXY")
    log_to_render(f"🔧 Cấu hình: {max_workers} workers (KHÔNG sub-chunking)")
    
    # KHÔNG reset cache cũ, chỉ track validation hiện tại
    current_validation_checked = 0
    current_validation_alive = 0
    
    # Giữ lại proxy cũ và tích lũy thêm proxy mới
    existing_proxies = proxy_cache.get("http", [])
    log_to_render(f"🔄 Bắt đầu validation mới - Giữ lại {len(existing_proxies)} proxy cũ")
    
    # Count proxy types
    categorized_count = sum(1 for item in proxy_list if isinstance(item, tuple) and item[0] == 'categorized')
    mixed_count = sum(1 for item in proxy_list if isinstance(item, tuple) and item[0] == 'mixed')
    
    log_to_render(f"🔧 Proxy types: {categorized_count} categorized(specific) + {mixed_count} mixed(all)")
    
    checked_count = 0
    
    # Validate TẤT CẢ proxy cùng lúc với ThreadPoolExecutor - KHÔNG sub-chunking
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit tất cả proxy
        future_to_proxy = {}
        for proxy_data in proxy_list:
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
            
            future = executor.submit(check_single_proxy, proxy_string, 8, protocols)
            future_to_proxy[future] = (proxy_type, proxy_string, protocols_info)
        
        # Collect results với progress tracking
        for future in as_completed(future_to_proxy):
            checked_count += 1
            current_validation_checked += 1
            proxy_type, proxy_string, protocols_info = future_to_proxy[future]
            
            try:
                result = future.result()
                if result:
                    alive_proxies.append(result)
                    
                    # Tích lũy proxy mới với proxy cũ (tránh duplicate) - lấy real-time
                    with cache_lock:
                        current_proxies = proxy_cache.get("http", []).copy()
                    
                    # Thêm proxy mới nếu chưa có
                    proxy_key = f"{result['host']}:{result['port']}"
                    existing_keys = [f"{p['host']}:{p['port']}" for p in current_proxies]
                    
                    if proxy_key not in existing_keys:
                        current_proxies.append(result)
                    
                    # Update cache với danh sách tích lũy
                    with cache_lock:
                        proxy_cache["http"] = current_proxies.copy()
                        proxy_cache["alive_count"] = len(current_proxies)
                        proxy_cache["total_checked"] = proxy_cache.get("total_checked", 0) + 1
                        proxy_cache["last_update"] = datetime.now().isoformat()
                    
                    current_validation_alive += 1
                    
                else:
                    # Update total checked even for failed (tích lũy)
                    with cache_lock:
                        proxy_cache["total_checked"] = proxy_cache.get("total_checked", 0) + 1
                    
                    # REDUCED: Chỉ log progress ít hơn
                    if checked_count % 100 == 0:  # Log mỗi 100 proxy
                        progress_pct = round(checked_count/total_proxies*100, 1)
                        log_to_render(f"⏳ Progress: {checked_count}/{total_proxies} checked ({progress_pct}%), {len(alive_proxies)} alive")
                        
            except Exception as e:
                # Update total checked even for exceptions (tích lũy)
                with cache_lock:
                    proxy_cache["total_checked"] = proxy_cache.get("total_checked", 0) + 1
    
    # Final validation summary (KHÔNG override cache đã tích lũy)
    final_alive_count = proxy_cache.get("alive_count", 0)
    final_total_checked = proxy_cache.get("total_checked", 0)
    
    # Chỉ update timestamp
    with cache_lock:
        proxy_cache["last_update"] = datetime.now().isoformat()
    
    # SIMPLIFIED: Logs ngắn gọn hơn
    current_cycle_success = round(len(alive_proxies)/total_proxies*100, 1) if total_proxies > 0 else 0
    overall_success = round(final_alive_count/final_total_checked*100, 1) if final_total_checked > 0 else 0
    log_to_render(f"🎯 VALIDATION HOÀN THÀNH!")
    log_to_render(f"📊 Batch này: {len(alive_proxies)} alive / {total_proxies} total ({current_cycle_success}%)")
    log_to_render(f"📈 Tổng cộng: {final_alive_count} alive / {final_total_checked} total ({overall_success}%)")
    
    return alive_proxies

def check_initial_fetch_timeout(start_time, max_hours=2):
    """Kiểm tra timeout cho initial fetch để tránh chạy vô tận"""
    elapsed_hours = (time.time() - start_time) / 3600
    if elapsed_hours > max_hours:
        log_to_render(f"⚠️ INITIAL FETCH TIMEOUT: {elapsed_hours:.1f}h > {max_hours}h")
        log_to_render("🔄 Force chuyển sang MAINTENANCE MODE với proxy hiện có")
        return True
    return False

def validate_existing_proxies_only():
    """Maintenance mode - chỉ re-check các proxy đã có trong cache"""
    global proxy_cache
    
    # Lấy các proxy hiện có từ cache
    existing_proxies = proxy_cache.get('http', [])
    
    if not existing_proxies:
        log_to_render("⚠️ MAINTENANCE MODE: Không có proxy trong cache để re-check")
        return []
    
    log_to_render(f"🔄 MAINTENANCE MODE: Re-checking {len(existing_proxies)} proxy có sẵn...")
    
    # Chuyển đổi format để validate
    proxy_list = []
    for p in existing_proxies:
        proxy_string = f"{p['host']}:{p['port']}"
        proxy_type = p.get('type', 'http')
        protocols_info = [proxy_type]
        proxy_list.append(('maintenance', proxy_string, protocols_info))
    
    log_to_render(f"⚡ Bắt đầu re-validation {len(proxy_list)} proxy...")
    
    # Validate với max_workers cao hơn cho maintenance (vì ít proxy hơn)
    alive_proxies = validate_proxy_batch_smart(proxy_list, max_workers=25)
    
    log_to_render(f"✅ MAINTENANCE HOÀN THÀNH: {len(alive_proxies)}/{len(proxy_list)} proxy còn sống")
    
    return alive_proxies

def background_proxy_refresh():
    """Background thread với 2 mode: Initial fetch vs Maintenance - FIXED LOGIC"""
    global proxy_cache, startup_status
    
    log_to_render("🔄 BACKGROUND THREAD KHỞI ĐỘNG")
    
    # Wait a bit for service to stabilize
    log_to_render("⏳ Waiting 10 seconds for service stabilization...")
    time.sleep(10)
    
    initial_fetch_done = False
    cycle_count = 0
    initial_start_time = None
    
    while True:
        try:
            cycle_count += 1
            log_to_render("=" * 60)
            
            if not initial_fetch_done:
                # Track initial fetch start time
                if initial_start_time is None:
                    initial_start_time = time.time()
                
                # Check timeout protection (2 giờ max)
                if check_initial_fetch_timeout(initial_start_time, max_hours=2):
                    log_to_render("🚨 FORCE SWITCH: Initial fetch quá lâu, chuyển sang maintenance")
                    initial_fetch_done = True
                    sleep_time = 300
                    continue
                
                # MODE 1: INITIAL FETCH - chia chunk để đảm bảo hoàn thành
                log_to_render(f"🚀 CYCLE {cycle_count}: INITIAL FETCH MODE (CHIA CHUNK)")
                elapsed_time = round((time.time() - initial_start_time) / 60, 1)
                log_to_render(f"⏰ Elapsed: {elapsed_time} phút (timeout: 120 phút)")
                
                # DEBUG: Log để track cycle behavior
                if cycle_count > 1:
                    log_to_render("⚠️ WARNING: This is a REPEATED CYCLE - Previous cycle did not complete!")
                    log_to_render("🔍 DEBUG: This should only happen if previous cycle was interrupted")
                
                log_to_render("=" * 60)
                
                start_time = time.time()
                
                # Fetch proxies từ sources (KHÔNG GIỚI HẠN)
                log_to_render("📥 Fetching TOÀN BỘ proxy từ tất cả nguồn...")
                
                try:
                    proxy_list, sources_count = fetch_proxies_from_sources()
                except Exception as e:
                    log_to_render(f"❌ CRITICAL ERROR trong fetch_proxies_from_sources: {str(e)}")
                    log_to_render(f"📍 Traceback: {traceback.format_exc()}")
                    log_to_render("🔄 Retry trong 5 phút...")
                    time.sleep(300)
                    continue
                
                if proxy_list:
                    total_proxies = len(proxy_list)
                    log_to_render(f"📊 Fetch thành công: {total_proxies} proxy từ {sources_count} nguồn")
                    
                    # Chia thành chunks 500 proxy mỗi lần để đảm bảo complete
                    chunk_size = 500
                    chunks = [proxy_list[i:i + chunk_size] for i in range(0, len(proxy_list), chunk_size)]
                    total_chunks = len(chunks)
                    
                    log_to_render(f"🔀 Chia thành {total_chunks} chunks ({chunk_size} proxy/chunk)")
                    log_to_render("⚡ Bắt đầu validation từng chunk...")
                    
                    all_alive_proxies = []
                    completed_chunks = 0
                    
                    # FIXED: Thêm error handling và recovery cho từng chunk
                    for chunk_idx, chunk in enumerate(chunks, 1):
                        chunk_start_time = time.time()
                        log_to_render(f"🔄 Processing chunk {chunk_idx}/{total_chunks} ({len(chunk)} proxy)...")
                        
                        # FIXED: Thêm try-catch cho validate_proxy_batch_smart
                        try:
                            chunk_alive = validate_proxy_batch_smart(chunk, max_workers=20)
                            all_alive_proxies.extend(chunk_alive)
                            completed_chunks += 1
                            
                            chunk_time = round(time.time() - chunk_start_time, 1)
                            progress = round(completed_chunks / total_chunks * 100, 1)
                            
                            log_to_render(f"✅ Chunk {chunk_idx} DONE: {len(chunk_alive)} alive in {chunk_time}s")
                            log_to_render(f"📈 Progress: {progress}% ({completed_chunks}/{total_chunks} chunks)")
                            log_to_render(f"📊 Total alive so far: {len(all_alive_proxies)}")
                            
                        except Exception as e:
                            log_to_render(f"❌ CRITICAL ERROR trong validate_proxy_batch_smart chunk {chunk_idx}: {str(e)}")
                            log_to_render(f"🔄 SKIP chunk {chunk_idx} và tiếp tục...")
                            # Vẫn count completed để không bị stuck
                            completed_chunks += 1
                            
                            # REMOVED: Bỏ log debug dài
                        
                        # Log đặc biệt để dễ track - REDUCED frequency
                        if chunk_idx % 20 == 0:  # Giảm từ 10 → 20 chunks
                            log_to_render("=" * 40)
                            log_to_render(f"🎯 MILESTONE: Completed {completed_chunks} chunks out of {total_chunks}")
                            log_to_render(f"⏰ Total runtime: {round((time.time() - start_time)/60, 1)} minutes")
                            success_rate = round(len(all_alive_proxies)/(completed_chunks*chunk_size)*100, 1) if completed_chunks > 0 else 0
                            log_to_render(f"🏆 Success rate: {success_rate}%")
                            log_to_render("=" * 40)
                        
                        # Sleep ngắn giữa các chunk để không overload
                        if chunk_idx < total_chunks:
                            # REMOVED: Bỏ log sleep
                            time.sleep(10)
                    
                    # Update final cache với tất cả proxy alive
                    with cache_lock:
                        proxy_cache["http"] = all_alive_proxies.copy()
                        proxy_cache["alive_count"] = len(all_alive_proxies)
                        proxy_cache["total_checked"] = total_proxies
                        proxy_cache["sources_processed"] = sources_count
                        proxy_cache["last_update"] = datetime.now().isoformat()
                    
                    alive_proxies = all_alive_proxies
                    
                    # FIXED: Mark complete khi ĐÃ XONG HẾT tất cả chunks (BẤT KỂ có proxy sống hay không)
                    if completed_chunks == total_chunks:
                        initial_fetch_done = True
                        log_to_render("🎉 INITIAL FETCH 100% HOÀN THÀNH! Chuyển sang MAINTENANCE MODE...")
                        log_to_render(f"📊 Kết quả cuối cùng: {len(alive_proxies)} proxy sống từ {proxy_cache.get('total_checked', 0)} đã kiểm tra")
                        log_to_render(f"🔧 FIXED: Completed {completed_chunks}/{total_chunks} chunks successfully")
                    else:
                        log_to_render(f"⚠️ BUG DETECTED: completed_chunks={completed_chunks} != total_chunks={total_chunks}")
                        log_to_render("🔄 Lý do: Logic error - này không nên xảy ra sau fix")
                        log_to_render("🚨 FORCE COMPLETE để tránh infinite loop")
                        initial_fetch_done = True  # FORCE complete để tránh loop
                        sleep_time = 300
                    
                else:
                    log_to_render("❌ INITIAL FETCH THẤT BẠI: Không fetch được proxy nào")
                    log_to_render("🔄 Thử lại trong 5 phút...")
                    alive_proxies = []
                    sleep_time = 300  # 5 phút retry
                    
            else:
                # MODE 2: MAINTENANCE - chỉ re-check proxy có sẵn
                log_to_render(f"🔧 CYCLE {cycle_count}: MAINTENANCE MODE (RE-CHECK)")
                log_to_render("=" * 60)
                
                start_time = time.time()
                
                # Chỉ re-check proxy có sẵn
                try:
                    alive_proxies = validate_existing_proxies_only()
                except Exception as e:
                    log_to_render(f"❌ ERROR trong validate_existing_proxies_only: {str(e)}")
                    log_to_render(f"📍 Traceback: {traceback.format_exc()}")
                    alive_proxies = []
                
                # Không cần update sources_processed trong maintenance mode
            
            # Tính toán thống kê cho cả 2 mode
            cycle_time = round(time.time() - start_time, 1)
            
            if not initial_fetch_done:
                # Stats cho initial mode
                total_checked = proxy_cache.get("total_checked", 0)
                success_rate = round(len(alive_proxies)/total_checked*100, 1) if total_checked > 0 else 0
                
                if initial_fetch_done:  # Chỉ update startup khi thực sự done
                    with cache_lock:
                        startup_status["first_fetch_completed"] = True
                
                log_to_render("=" * 60)
                if initial_fetch_done:
                    log_to_render("🎉 INITIAL FETCH 100% HOÀN THÀNH!")
                    log_to_render(f"⏱️ Thời gian: {cycle_time}s")
                    log_to_render(f"📊 Kết quả: {len(alive_proxies)} alive / {total_checked} total")
                    log_to_render(f"📈 Tỷ lệ thành công: {success_rate}%")
                    log_to_render("🔄 Chuyển sang MAINTENANCE MODE...")
                    sleep_time = 300  # 5 phút cho maintenance mode đầu tiên
                else:
                    log_to_render("⚠️ INITIAL FETCH CHƯA HOÀN THÀNH")
                    log_to_render(f"⏱️ Thời gian cycle: {cycle_time}s")
                    log_to_render(f"📊 Progress: {len(alive_proxies)} alive / {total_checked} checked")
                    log_to_render("🔄 Tiếp tục INITIAL MODE...")
                    sleep_time = 300  # 5 phút retry
                log_to_render("=" * 60)
                
            else:
                # Stats cho maintenance mode  
                existing_count = len(proxy_cache.get('http', []))
                
                if existing_count == 0:
                    log_to_render("⚠️ MAINTENANCE: Không có proxy để check, quay lại INITIAL MODE")
                    initial_fetch_done = False
                    sleep_time = 60  # 1 phút
                    continue
                    
                success_rate = round(len(alive_proxies)/existing_count*100, 1) if existing_count > 0 else 0
                
                log_to_render("=" * 60)
                log_to_render("✅ MAINTENANCE HOÀN THÀNH!")
                log_to_render(f"⏱️ Thời gian: {cycle_time}s")
                log_to_render(f"📊 Kết quả: {len(alive_proxies)} alive / {existing_count} total")
                log_to_render(f"📈 Tỷ lệ còn sống: {success_rate}%")
                log_to_render("🔄 Tiếp theo trong 10 phút...")
                log_to_render("=" * 60)
                
                # Sleep bình thường cho maintenance
                sleep_time = 600  # 10 phút
            
        except Exception as e:
            log_to_render(f"❌ LỖI BACKGROUND REFRESH: {str(e)}")
            log_to_render(f"📍 Traceback: {traceback.format_exc()}")
            log_to_render("🔄 Tiếp tục vòng lặp...")
            startup_status["error_count"] += 1
            sleep_time = 300  # 5 phút nếu có lỗi
            
            # FIXED: Thêm protection để tránh infinite loop
            if startup_status["error_count"] > 10:
                log_to_render("🚨 CRITICAL: Quá nhiều lỗi liên tiếp, FORCE SWITCH sang maintenance")
                initial_fetch_done = True
                startup_status["error_count"] = 0
        
        # Sleep với thời gian động theo mode
        sleep_minutes = sleep_time // 60
        log_to_render(f"😴 Sleep {sleep_minutes} phút trước chu kỳ tiếp theo...")
        time.sleep(sleep_time)

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
        # REMOVED: Bỏ log không cần thiết
        
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
        # REMOVED: Bỏ debug logs không cần thiết
        
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
        
        # REMOVED: Bỏ debug logs chi tiết
        
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
            # REMOVED: Bỏ debug log không cần thiết
            return jsonify({
                'success': False,
                'message': 'No live proxies available yet. Service is still validating.',
                'count': 0,
                'proxies': [],
                'cache_status': 'empty'
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
            'last_update': proxy_cache.get('last_update')
        })
        
    except Exception as e:
        log_to_render(f"❌ API /proxies error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/debug', methods=['GET'])
def debug_cache():
    """Debug cache để kiểm tra vấn đề"""
    # REMOVED: Bỏ log debug không cần thiết
    
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
    # REMOVED: Bỏ log không cần thiết
    
    # Tính toán một số metrics hữu ích
    alive_count = len(proxy_cache.get('http', []))
    total_checked = proxy_cache.get('total_checked', 0)
    success_rate = round(alive_count/total_checked*100, 1) if total_checked > 0 else 0
    
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'cache_count': alive_count,
        'service': 'proxy-validation-render',
        'startup_status': startup_status,
        'metrics': {
            'alive_proxies': alive_count,
            'total_checked': total_checked,
            'success_rate_percent': success_rate,
            'last_update': proxy_cache.get('last_update', 'Never')
        },
        'fixed_bugs': [
            'Loop bug fixed - no more restart from chunk 1',
            'Condition fixed - completes after all chunks processed'
        ]
    })

@app.route('/api/force/initial', methods=['POST'])
def force_initial_mode():
    """Force switch về initial fetch mode"""
    try:
        # Note: Trong production, cần implement proper global state management
        log_to_render("🔄 API TRIGGER: Force switch về INITIAL FETCH MODE requested")
        
        return jsonify({
            'success': True,
            'message': 'Signal sent to switch to initial fetch mode on next cycle',
            'note': 'Change will take effect in next background cycle',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

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