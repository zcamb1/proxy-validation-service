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
    "alive_count": 0
}

# Nguồn proxy được phân loại theo yêu cầu user
PROXY_SOURCE_LINKS = {
    # Nguồn có protocol rõ ràng - kiểm tra theo đúng protocol
    "Server Alpha": {
        "http": "https://cdn.jsdelivr.net/gh/databay-labs/free-proxy-list/http.txt",
        "https": "https://cdn.jsdelivr.net/gh/databay-labs/free-proxy-list/https.txt", 
        "socks5": "https://cdn.jsdelivr.net/gh/databay-labs/free-proxy-list/socks5.txt",
    },
    "Network Beta": {
        "http": "https://raw.githubusercontent.com/casa-ls/proxy-list/main/http",
        "socks4": "https://raw.githubusercontent.com/casa-ls/proxy-list/main/socks4",
        "socks5": "https://raw.githubusercontent.com/casa-ls/proxy-list/main/socks5",
        "http_yemixzy": "https://raw.githubusercontent.com/yemixzy/proxy-list/main/proxies/http.txt",
        "socks4_yemixzy": "https://raw.githubusercontent.com/yemixzy/proxy-list/main/proxies/socks4.txt",
        "socks5_yemixzy": "https://raw.githubusercontent.com/yemixzy/proxy-list/main/proxies/socks5.txt",
    },
    "Gateway Pro": {
        "http": "https://api.proxyscrape.com/v2/?request=getproxies&protocol=http",
        "socks4": "https://api.proxyscrape.com/v2/?request=getproxies&protocol=socks4", 
        "socks5": "https://api.proxyscrape.com/v2/?request=getproxies&protocol=socks5",
        "https": "https://api.proxyscrape.com/v2/?request=getproxies&protocol=https",
    },
    
    # Mixed sources - thử tất cả protocol, cái nào live thì thêm vào (kiểm tra sau)
    "Mixed Sources": {
        "mixed_hendrikbgr": "https://raw.githubusercontent.com/hendrikbgr/Free-Proxy-Repo/master/proxy_list.txt",
        "mixed_mrmarble": "https://raw.githubusercontent.com/MrMarble/proxy-list/main/all.txt",
    }
}

def parse_proxy_line(proxy_string, default_type="auto"):
    """Parse proxy line giống y hệt tool - auto detect protocol"""
    try:
        add_log(f"🔍 Parsing proxy: {proxy_string}", "info")
        
        # Trường hợp username:password@host:port
        if '@' in proxy_string:
            auth, hostport = proxy_string.split('@', 1)
            if ':' in auth:
                username, password = auth.split(':', 1)
            else:
                username, password = auth, ""
            
            if ':' in hostport:
                host, port = hostport.split(':', 1)
            else:
                add_log(f"❌ Invalid format: no port in {hostport}", "error")
                return None
        # Trường hợp host:port
        elif ':' in proxy_string:
            username, password = "", ""
            host, port = proxy_string.split(':', 1)
        else:
            add_log(f"❌ Invalid format: no colon in {proxy_string}", "error")
            return None
        
        # Auto-detect protocol dựa trên port (giống tool)
        if default_type == "auto":
            port_num = int(port)
            if port_num in [80, 8080, 3128]:
                proxy_type = "http"
            elif port_num in [443, 8443]:
                proxy_type = "https"
            elif port_num in [1080, 1081]:
                proxy_type = "socks5"
            elif port_num in [1090, 4145]:
                proxy_type = "socks4"
            else:
                proxy_type = "http"  # Default HTTP
        else:
            proxy_type = default_type
        
        add_log(f"✅ Parsed: {host}:{port} as {proxy_type} protocol", "success")
        
        return {
            'host': host,
            'port': port,
            'username': username,
            'password': password,
            'type': proxy_type,
            'proxy_str': f"{username}:{'*'*len(password)}@{host}:{port}" if username else f"{host}:{port}"
        }
        
    except Exception as e:
        add_log(f"❌ Parse error for '{proxy_string}': {str(e)}", "error")
        return None

def check_single_proxy(proxy_string, timeout=8):
    """Kiểm tra 1 proxy - giống y hệt logic tool"""
    add_log(f"🧪 Checking proxy: {proxy_string}", "info")
    
    # Parse proxy giống tool
    parsed = parse_proxy_line(proxy_string, "auto")
    if not parsed:
        add_log(f"❌ Failed to parse: {proxy_string}", "error")
        return None
    
    host = parsed['host']
    port = parsed['port']
    proxy_type = parsed['type']
    username = parsed['username']
    password = parsed['password']
    
    add_log(f"🔧 Testing {host}:{port} as {proxy_type} protocol", "info")
    
    result = {
        'host': host,
        'port': int(port),
        'type': proxy_type,
        'username': username,
        'password': password,
        'proxy_str': parsed['proxy_str'],
        'live': False,
        'latency': 0,
        'ip': None,
        'error': None,
        'speed': 0,
        'status': 'dead',
        'checked_at': datetime.now().isoformat(),
        'proxy_string': f"{host}:{port}",
        'full_proxy': proxy_string,
        'has_auth': bool(username and password)
    }
    
    # Setup proxy URL giống tool
    if username:
        proxy_url = f"{proxy_type}://{username}:{password}@{host}:{port}"
    else:
        proxy_url = f"{proxy_type}://{host}:{port}"
        
    proxies = {
        "http": proxy_url,
        "https": proxy_url
    }
    
    # Test URLs giống tool (ipify chính xác như tool)
    test_urls = [
        "https://api.ipify.org?format=text",  # Primary - giống tool
        "https://api.elevenlabs.io/v1/models",  # ElevenLabs test
        "https://httpbin.org/ip"  # Fallback
    ]
    
    try:
        start_time = time.time()
        
        for i, test_url in enumerate(test_urls):
            try:
                add_log(f"🌐 Testing {host}:{port} với {test_url}", "info")
                
                response = requests.get(
                    test_url,
                    proxies=proxies,
                    timeout=timeout,
                    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                )
                
                end_time = time.time()
                latency = round((end_time - start_time) * 1000)  # milliseconds
                speed = round(end_time - start_time, 2)  # seconds
                
                # Handle response giống tool
                if "api.ipify.org" in test_url:
                    if response.status_code == 200:
                        ip = response.text.strip()
                        add_log(f"✅ IPIFY SUCCESS: {host}:{port} → IP: {ip} | Latency: {latency}ms", "success")
                        result.update({
                            'live': True,
                            'latency': latency,
                            'speed': speed,
                            'ip': ip,
                            'status': 'alive',
                            'error': None
                        })
                        return result
                    else:
                        add_log(f"❌ IPIFY failed: HTTP {response.status_code}", "error")
                        
                elif "api.elevenlabs.io" in test_url:
                    # ElevenLabs chấp nhận 401, 403, 404, 200
                    if response.status_code in [401, 403, 404, 200]:
                        add_log(f"✅ ELEVENLABS SUCCESS: {host}:{port} → HTTP {response.status_code} | Latency: {latency}ms", "success")
                        result.update({
                            'live': True,
                            'latency': latency,
                            'speed': speed,
                            'ip': f"ElevenLabs HTTP {response.status_code}",
                            'status': 'alive',
                            'error': None
                        })
                        return result
                    else:
                        add_log(f"❌ ElevenLabs failed: HTTP {response.status_code}", "error")
                        
                else:  # httpbin
                    if response.status_code == 200:
                        try:
                            ip_data = response.json()
                            ip = ip_data.get('origin', 'Unknown')
                            if ',' in ip:
                                ip = ip.split(',')[0]
                        except:
                            ip = "HttpBin Response"
                        
                        add_log(f"✅ HTTPBIN SUCCESS: {host}:{port} → IP: {ip} | Latency: {latency}ms", "success")
                        result.update({
                            'live': True,
                            'latency': latency,
                            'speed': speed,
                            'ip': ip,
                            'status': 'alive',
                            'error': None
                        })
                        return result
                    else:
                        add_log(f"❌ HttpBin failed: HTTP {response.status_code}", "error")
                        
            except requests.exceptions.ProxyError as e:
                add_log(f"❌ Proxy error with {test_url}: {str(e)}", "error")
                result['error'] = f"Proxy error: {e}"
            except requests.exceptions.ConnectTimeout:
                add_log(f"❌ Connect timeout with {test_url}", "error")
                result['error'] = "Connect timeout"
            except requests.exceptions.ReadTimeout:
                add_log(f"❌ Read timeout with {test_url}", "error")
                result['error'] = "Read timeout"
            except requests.exceptions.ConnectionError as e:
                add_log(f"❌ Connection error with {test_url}: {str(e)}", "error")
                result['error'] = f"Connection error: {e}"
            except Exception as e:
                add_log(f"❌ Unknown error with {test_url}: {str(e)}", "error")
                result['error'] = f"Error: {e}"
                
        # Nếu tất cả test URLs đều fail
        add_log(f"💀 PROXY DEAD: {host}:{port} - All tests failed", "error")
        return result
        
    except Exception as e:
        add_log(f"❌ Critical error checking {host}:{port}: {str(e)}", "error")
        result['error'] = f"Critical error: {e}"
        return result

def check_mixed_proxy_all_protocols(proxy_string, timeout=8):
    """
    Kiểm tra mixed proxy với tất cả protocol (http, https, socks4, socks5)
    Trả về kết quả cho protocol đầu tiên thành công
    """
    protocols_to_try = ['http', 'https', 'socks4', 'socks5']
    
    # Parse proxy
    parsed = parse_proxy_line(proxy_string, "auto")
    if not parsed:
        add_log(f"❌ Mixed proxy parse failed: {proxy_string}", "error")
        return None
    
    host = parsed['host']
    port = parsed['port']
    username = parsed.get('username', '')
    password = parsed.get('password', '')
    
    for protocol in protocols_to_try:
        try:
            add_log(f"🧪 Testing mixed proxy {host}:{port} với protocol {protocol}", "info")
            
            result = {
                'host': host,
                'port': int(port),
                'type': protocol,
                'username': username,
                'password': password,
                'proxy_str': parsed['proxy_str'],
                'live': False,
                'latency': 0,
                'ip': None,
                'error': None,
                'speed': 0,
                'status': 'dead',
                'checked_at': datetime.now().isoformat(),
                'proxy_string': f"{host}:{port}",
                'full_proxy': proxy_string,
                'has_auth': bool(username and password)
            }
            
            # Setup proxy URL
            if username:
                proxy_url = f"{protocol}://{username}:{password}@{host}:{port}"
            else:
                proxy_url = f"{protocol}://{host}:{port}"
                
            proxies = {
                "http": proxy_url,
                "https": proxy_url
            }
            
            # Test URLs
            test_urls = [
                "https://api.ipify.org?format=text",
                "https://api.elevenlabs.io/v1/models",
                "https://httpbin.org/ip"
            ]
            
            start_time = time.time()
            
            for test_url in test_urls:
                try:
                    response = requests.get(
                        test_url,
                        proxies=proxies,
                        timeout=timeout,
                        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                    )
                    
                    end_time = time.time()
                    latency = round((end_time - start_time) * 1000)
                    speed = round(end_time - start_time, 2)
                    
                    # Check response based on test URL
                    if "api.ipify.org" in test_url and response.status_code == 200:
                        ip = response.text.strip()
                        add_log(f"✅ Mixed proxy {host}:{port} LIVE với {protocol} → IP: {ip}", "success")
                        result.update({
                            'live': True,
                            'latency': latency,
                            'speed': speed,
                            'ip': ip,
                            'status': 'alive',
                            'type': protocol,  # Update to working protocol
                            'error': None
                        })
                        return result
                        
                    elif "api.elevenlabs.io" in test_url and response.status_code in [401, 403, 404, 200]:
                        add_log(f"✅ Mixed proxy {host}:{port} LIVE với {protocol} → ElevenLabs OK", "success")
                        result.update({
                            'live': True,
                            'latency': latency,
                            'speed': speed,
                            'ip': f"ElevenLabs HTTP {response.status_code}",
                            'status': 'alive',
                            'type': protocol,
                            'error': None
                        })
                        return result
                        
                    elif "httpbin.org" in test_url and response.status_code == 200:
                        try:
                            ip_data = response.json()
                            ip = ip_data.get('origin', 'Unknown')
                            if ',' in ip:
                                ip = ip.split(',')[0]
                        except:
                            ip = "HttpBin Response"
                        
                        add_log(f"✅ Mixed proxy {host}:{port} LIVE với {protocol} → HttpBin OK", "success")
                        result.update({
                            'live': True,
                            'latency': latency,
                            'speed': speed,
                            'ip': ip,
                            'status': 'alive',
                            'type': protocol,
                            'error': None
                        })
                        return result
                
                except requests.exceptions.RequestException:
                    continue  # Try next URL
                    
        except Exception as e:
            add_log(f"❌ Mixed proxy {host}:{port} failed với {protocol}: {e}", "error")
            continue  # Try next protocol
    
    add_log(f"💀 Mixed proxy {host}:{port} DEAD với tất cả protocol", "error")
    return None

def add_log(message, log_type="info"):
    """Add log entry"""
    service_status["logs"] = service_status.get("logs", [])
    service_status["logs"].append({
        "timestamp": datetime.now().isoformat(),
        "message": message,
        "type": log_type
    })
    # Keep only last 100 logs
    if len(service_status["logs"]) > 100:
        service_status["logs"] = service_status["logs"][-100:]
    print(f"[{log_type.upper()}] {message}")

def fetch_proxies_from_sources():
    """Lấy proxy từ các nguồn với logic thông minh: categorized trước, mixed sau"""
    service_status["is_fetching"] = True
    service_status["sources_checked"] = 0
    service_status["current_progress"] = 0
    
    all_proxies = []
    categorized_proxies = []
    mixed_proxies = []
    
    add_log("🔍 Bắt đầu fetch proxy từ các nguồn - CATEGORIZED trước, MIXED sau...", "info")
    
    # Step 1: Process categorized sources first (Server Alpha, Network Beta, Gateway Pro)
    categorized_sources = {k: v for k, v in PROXY_SOURCE_LINKS.items() if k != "Mixed Sources"}
    
    for i, (source_name, source_urls) in enumerate(categorized_sources.items()):
        try:
            add_log(f"📥 [CATEGORIZED] Đang fetch từ {source_name}...", "info")
            
            for protocol, source_url in source_urls.items():
                try:
                    add_log(f"🔗 Fetching {source_name} - {protocol}: {source_url[:50]}...", "info")
                    response = requests.get(source_url, timeout=30)
                    
                    if response.status_code == 200:
                        content = response.text
                        lines = content.strip().split('\n')
                        source_proxies = []
                        
                        for line in lines:
                            line = line.strip()
                            if not line or line.startswith('#'):
                                continue
                                
                            if ':' in line:
                                proxy_candidate = line.strip()
                                
                                # Remove common prefixes
                                for prefix in ['http://', 'https://', 'socks4://', 'socks5://']:
                                    if proxy_candidate.startswith(prefix):
                                        proxy_candidate = proxy_candidate[len(prefix):]
                                
                                # For categorized sources, force the protocol from URL
                                parsed = parse_proxy_line(proxy_candidate, protocol.split('_')[0])  # Remove suffix like _yemixzy
                                if parsed:
                                    clean_proxy = f"{parsed['host']}:{parsed['port']}"
                                    source_proxies.append(clean_proxy)
                        
                        categorized_proxies.extend(source_proxies)
                        add_log(f"✅ {source_name} ({protocol}): Tìm thấy {len(source_proxies)} proxy", "success")
                    else:
                        add_log(f"❌ {source_name} ({protocol}): HTTP {response.status_code}", "error")
                
                except Exception as e:
                    add_log(f"❌ {source_name} ({protocol}): {str(e)}", "error")
            
        except Exception as e:
            add_log(f"❌ {source_name}: {str(e)}", "error")
            
        service_status["sources_checked"] = i + 1
        service_status["current_progress"] = i + 1
    
    add_log(f"🎯 CATEGORIZED hoàn thành: {len(categorized_proxies)} proxy", "success")
    
    # Step 2: Process mixed sources (will be checked with all protocols later)
    if "Mixed Sources" in PROXY_SOURCE_LINKS:
        mixed_source_urls = PROXY_SOURCE_LINKS["Mixed Sources"]
        
        for protocol, source_url in mixed_source_urls.items():
            try:
                add_log(f"📥 [MIXED] Đang fetch từ {protocol}: {source_url[:50]}...", "info")
                response = requests.get(source_url, timeout=30)
                
                if response.status_code == 200:
                    content = response.text
                    lines = content.strip().split('\n')
                    source_proxies = []
                    
                    for line in lines:
                        line = line.strip()
                        if not line or line.startswith('#'):
                            continue
                            
                        if ':' in line:
                            proxy_candidate = line.strip()
                            
                            # Remove common prefixes
                            for prefix in ['http://', 'https://', 'socks4://', 'socks5://']:
                                if proxy_candidate.startswith(prefix):
                                    proxy_candidate = proxy_candidate[len(prefix):]
                            
                            # For mixed, use auto detection
                            parsed = parse_proxy_line(proxy_candidate, "auto")
                            if parsed:
                                clean_proxy = f"{parsed['host']}:{parsed['port']}"
                                source_proxies.append(clean_proxy)
                    
                    mixed_proxies.extend(source_proxies)
                    add_log(f"✅ MIXED {protocol}: Tìm thấy {len(source_proxies)} proxy", "success")
                else:
                    add_log(f"❌ MIXED {protocol}: HTTP {response.status_code}", "error")
            
            except Exception as e:
                add_log(f"❌ MIXED {protocol}: {str(e)}", "error")
    
    add_log(f"🎯 MIXED hoàn thành: {len(mixed_proxies)} proxy", "success")
    
    # Combine: categorized first, then mixed
    all_proxies = categorized_proxies + mixed_proxies
    
    # Remove duplicates
    unique_proxies = list(set(all_proxies))
    add_log(f"🎉 Tổng cộng thu thập {len(unique_proxies)} proxy unique (Categorized: {len(categorized_proxies)}, Mixed: {len(mixed_proxies)})", "success")
    
    service_status["is_fetching"] = False
    return unique_proxies

def validate_proxy_batch_fast(proxy_list, max_workers=40, target_alive=50, chunk_size=80, timeout=8):
    """Validate proxy list NHANH với early stopping và real-time updates"""
    service_status["is_validating"] = True
    service_status["total_to_check"] = len(proxy_list)
    service_status["current_progress"] = 0
    
    alive_proxies = []
    dead_count = 0
    total_completed = 0
    
    add_log(f"⚡ BẮT ĐẦU VALIDATION NHANH: {len(proxy_list)} proxy với {max_workers} workers | Target: {target_alive} alive", "info")
    
    # Chia proxy thành chunks nhỏ để có kết quả sớm
    for chunk_start in range(0, len(proxy_list), chunk_size):
        chunk_end = min(chunk_start + chunk_size, len(proxy_list))
        chunk = proxy_list[chunk_start:chunk_end]
        
        add_log(f"🚀 Chunk {chunk_start//chunk_size + 1}: Testing {len(chunk)} proxies...", "info")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit chunk với timeout nhanh
            future_to_proxy = {
                executor.submit(check_single_proxy, proxy, timeout): proxy 
                for proxy in chunk
            }
            
            chunk_completed = 0
            for future in as_completed(future_to_proxy):
                try:
                    result = future.result(timeout=1)  # Quick result retrieval
                    chunk_completed += 1
                    total_completed += 1
                    service_status["current_progress"] = total_completed
                    
                    if result and result.get('status') == 'alive':
                        alive_proxies.append(result)
                        add_log(f"✅ ALIVE #{len(alive_proxies)}: {result['proxy_string']} → {result.get('ip', 'N/A')} | {result.get('latency', 0)}ms", "success")
                        
                        # EARLY STOPPING - Đủ proxy sống rồi!
                        if len(alive_proxies) >= target_alive:
                            add_log(f"🎯 ĐẠT TARGET: {len(alive_proxies)}/{target_alive} proxy sống! DỪNG VALIDATION SỚM.", "success")
                            service_status["is_validating"] = False
                            
                            # Update final cache ngay lập tức
                            proxy_cache["http"] = alive_proxies
                            proxy_cache["last_update"] = datetime.now().isoformat()
                            proxy_cache["total_checked"] = total_completed
                            proxy_cache["alive_count"] = len(alive_proxies)
                            
                            return alive_proxies
                    else:
                        dead_count += 1
                    
                    # Real-time progress update mỗi 10 proxy
                    if chunk_completed % 10 == 0:
                        progress_percent = round((total_completed / len(proxy_list)) * 100, 1)
                        success_rate = round((len(alive_proxies) / total_completed) * 100, 1) if total_completed > 0 else 0
                        add_log(f"📊 Progress: {total_completed}/{len(proxy_list)} ({progress_percent}%) | ✅{len(alive_proxies)} ALIVE | 💀{dead_count} dead | Rate: {success_rate}%", "info")
                        
                        # Update cache real-time cho UI
                        proxy_cache["http"] = alive_proxies
                        proxy_cache["last_update"] = datetime.now().isoformat()
                        proxy_cache["total_checked"] = total_completed
                        proxy_cache["alive_count"] = len(alive_proxies)
                
                except Exception as e:
                    total_completed += 1
                    dead_count += 1
                    add_log(f"❌ Validation error: {str(e)}", "error")
        
        # Sau mỗi chunk, check nếu đã có đủ proxy sống
        if len(alive_proxies) >= target_alive:
            break
            
        add_log(f"✅ Chunk hoàn thành: {len(alive_proxies)} alive từ {total_completed} tested", "info")
    
    service_status["is_validating"] = False
    service_status["current_progress"] = 0
    service_status["total_to_check"] = 0
    
    # Final update
    proxy_cache["http"] = alive_proxies
    proxy_cache["last_update"] = datetime.now().isoformat()
    proxy_cache["total_checked"] = total_completed
    proxy_cache["alive_count"] = len(alive_proxies)
    
    success_rate = round((len(alive_proxies) / total_completed) * 100, 1) if total_completed > 0 else 0
    add_log(f"🎉 VALIDATION HOÀN THÀNH: {len(alive_proxies)} proxy sống / {total_completed} tested | Success rate: {success_rate}%", "success")
    return alive_proxies

def validate_proxy_batch(proxy_list, max_workers=30):
    """Legacy function - redirect to fast version"""
    return validate_proxy_batch_fast(proxy_list, max_workers, target_alive=50)

def background_proxy_refresh():
    """Background task HỢP LÝ - refresh proxy mỗi 8 phút với cân bằng tốc độ/chính xác"""
    while True:
        try:
            add_log("🔄 BẮT ĐẦU CHU KỲ REFRESH HỢP LÝ (8 phút)...", "info")
            
            # Fetch new proxies from sources
            raw_proxies = fetch_proxies_from_sources()
            
            if raw_proxies:
                # STRATEGY: Cân bằng giữa tốc độ và độ chính xác
                limited_proxies = raw_proxies[:600]  # Pool hợp lý 600 proxy
                add_log(f"🎯 Pool: {len(limited_proxies)} proxy từ {len(raw_proxies)} tổng | Target: 80 alive", "info")
                
                # Use validation cân bằng với timeout 8s
                alive_proxies = validate_proxy_batch_fast(
                    limited_proxies, 
                    max_workers=35,      # Workers hợp lý 
                    target_alive=80,     # Target 80 proxy sống
                    chunk_size=60,       # Chunks vừa phải
                    timeout=8           # Timeout chuẩn 8s
                )
                
                # Update cache ngay lập tức
                proxy_cache["http"] = alive_proxies
                proxy_cache["last_update"] = datetime.now().isoformat()
                proxy_cache["total_checked"] = proxy_cache.get("total_checked", 0) + len(limited_proxies)
                proxy_cache["alive_count"] = len(alive_proxies)
                
                success_rate = round((len(alive_proxies) / len(limited_proxies)) * 100, 1)
                add_log(f"✅ CACHE UPDATED: {len(alive_proxies)} proxy sống | Success rate: {success_rate}%", "success")
                
                # Nếu có đủ proxy sống thì nghỉ chuẩn 8 phút
                if len(alive_proxies) >= 40:
                    sleep_time = 8 * 60  # 8 phút chuẩn
                    add_log(f"😴 Đủ proxy sống ({len(alive_proxies)}), nghỉ {sleep_time//60} phút...", "info")
                else:
                    sleep_time = 4 * 60  # 4 phút nếu ít proxy
                    add_log(f"⚠️ Ít proxy sống ({len(alive_proxies)}), refresh lại sau {sleep_time//60} phút...", "info")
                    
            else:
                add_log("❌ Không fetch được proxy từ các nguồn", "error")
                sleep_time = 5 * 60  # 5 phút nếu lỗi
            
            time.sleep(sleep_time)
            
        except Exception as e:
            add_log(f"❌ Lỗi trong background refresh: {str(e)}", "error")
            # Sleep 1 minute on error then retry
            time.sleep(60)

# Service status tracking
service_status = {
    "is_fetching": False,
    "is_validating": False,
    "current_progress": 0,
    "total_to_check": 0,
    "sources_checked": 0,
    "total_sources": len(PROXY_SOURCE_LINKS),
    "last_log": "",
    "errors": []
}

# API Routes
@app.route('/')
def home():
    """Homepage với thông tin service"""
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>🚀 Proxy Validation Service</title>
        <meta charset="UTF-8">
        <meta http-equiv="refresh" content="10">
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; }}
            .container {{ max-width: 1000px; margin: 0 auto; background: white; padding: 30px; border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.2); }}
            .header {{ text-align: center; margin-bottom: 30px; }}
            .stats {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 25px; border-radius: 15px; margin: 20px 0; }}
            .live-count {{ font-size: 36px; font-weight: bold; text-align: center; margin-bottom: 15px; }}
            .status-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 15px 0; }}
            .status-item {{ background: rgba(255,255,255,0.1); padding: 15px; border-radius: 10px; }}
            .status-item h4 {{ margin: 0 0 10px 0; font-size: 14px; opacity: 0.8; }}
            .status-item .value {{ font-size: 20px; font-weight: bold; }}
            .progress-container {{ margin: 20px 0; }}
            .progress-bar {{ width: 100%; height: 25px; background: rgba(255,255,255,0.2); border-radius: 12px; overflow: hidden; }}
            .progress-fill {{ height: 100%; background: linear-gradient(90deg, #00c851, #007e33); transition: width 0.3s ease; border-radius: 12px; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; }}
            .endpoint {{ background: #f8f9fa; padding: 20px; margin: 15px 0; border-radius: 10px; border-left: 5px solid #007bff; }}
            .method {{ color: #fff; padding: 8px 12px; border-radius: 6px; font-size: 12px; font-weight: bold; }}
            .get {{ background: #28a745; }}
            .logs {{ background: #2c3e50; color: #ecf0f1; padding: 20px; border-radius: 10px; margin: 20px 0; height: 200px; overflow-y: auto; font-family: 'Courier New', monospace; font-size: 12px; }}
            .log-item {{ margin: 5px 0; padding: 5px; border-radius: 3px; }}
            .log-info {{ background: rgba(52, 152, 219, 0.1); }}
            .log-success {{ background: rgba(39, 174, 96, 0.1); }}
            .log-error {{ background: rgba(231, 76, 60, 0.1); }}
            .controls {{ text-align: center; margin: 20px 0; }}
            .btn {{ background: #007bff; color: white; padding: 12px 24px; border: none; border-radius: 8px; cursor: pointer; font-size: 16px; margin: 0 10px; transition: all 0.3s; }}
            .btn:hover {{ background: #0056b3; transform: translateY(-2px); }}
            .btn-success {{ background: #28a745; }}
            .btn-success:hover {{ background: #1e7e34; }}
            .sources-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 10px; }}
            .source-item {{ padding: 10px; background: #f8f9fa; border-radius: 8px; border-left: 4px solid #007bff; }}
            .status-indicator {{ display: inline-block; width: 12px; height: 12px; border-radius: 50%; margin-right: 8px; }}
            .status-active {{ background: #28a745; animation: pulse 2s infinite; }}
            .status-idle {{ background: #6c757d; }}
            .status-error {{ background: #dc3545; }}
            @keyframes pulse {{ 0% {{ opacity: 1; }} 50% {{ opacity: 0.5; }} 100% {{ opacity: 1; }} }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🚀 Proxy Validation Service</h1>
                <p>Service tự động kiểm tra proxy sống mỗi 5 phút từ {len(PROXY_SOURCE_LINKS)} nguồn khác nhau</p>
            </div>
            
            <div class="stats">
                <div class="live-count" id="proxy-count">0 proxy sống</div>
                
                <div class="status-grid">
                    <div class="status-item">
                        <h4>📊 Tổng kiểm tra</h4>
                        <div class="value" id="total-checked">0</div>
                    </div>
                    <div class="status-item">
                        <h4>🔄 Trạng thái</h4>
                        <div class="value" id="service-status">
                            <span class="status-indicator status-idle"></span>Chờ...
                        </div>
                    </div>
                    <div class="status-item">
                        <h4>⏰ Lần check cuối</h4>
                        <div class="value" id="last-update">Chưa check</div>
                    </div>
                    <div class="status-item">
                        <h4>📈 Tuổi cache</h4>
                        <div class="value" id="cache-age">0 phút</div>
                    </div>
                </div>
                
                <div class="progress-container" id="progress-container" style="display: none;">
                    <div class="progress-bar">
                        <div class="progress-fill" id="progress-fill" style="width: 0%">0%</div>
                    </div>
                </div>
            </div>
            
            <div class="controls">
                <button class="btn btn-success" onclick="forceRefresh()">🔄 Force Refresh</button>
                <button class="btn" onclick="testAPI()">🧪 Test API</button>
                <button class="btn" onclick="toggleLogs()">📋 Show/Hide Logs</button>
                <button class="btn" onclick="debugStatus()" style="background: #ff6b6b;">🔍 Debug Status</button>
                <button class="btn" onclick="testFetch()" style="background: #4ecdc4;">📥 Test Fetch</button>
                <button class="btn" onclick="testValidation()" style="background: #ffe66d;">⚡ Test Validation</button>
                <button class="btn" onclick="quickCheck()" style="background: #ff9ff3;">🚀 Quick Check</button>
            </div>
            
            <div class="logs" id="logs-container" style="display: none;">
                <div id="logs">Đang tải logs...</div>
            </div>
            
            <h2>📡 API Endpoints:</h2>
            
            <div class="endpoint">
                <span class="method get">GET</span>
                <strong>/api/proxy/alive</strong>
                <p>Lấy danh sách proxy sống</p>
                <p>Params: <code>count</code> (số lượng, default: 50)</p>
                <p>Example: <code>/api/proxy/alive?count=100</code></p>
            </div>
            
            <div class="endpoint">
                <span class="method get">GET</span>
                <strong>/api/proxy/stats</strong>
                <p>Thống kê proxy hiện có</p>
            </div>
            
            <div class="endpoint">
                <span class="method get">GET</span>
                <strong>/api/proxy/force-refresh</strong>
                <p>Buộc refresh proxy ngay lập tức</p>
            </div>
            
            <div class="endpoint">
                <span class="method get">GET</span>
                <strong>/api/proxy/debug</strong>
                <p>Debug - xem toàn bộ service status và cache</p>
            </div>
            
            <div class="endpoint">
                <span class="method get">POST</span>
                <strong>/api/proxy/test-fetch</strong>
                <p>Test fetch proxy từ 1 source để debug</p>
            </div>
            
            <div class="endpoint">
                <span class="method get">POST</span>
                <strong>/api/proxy/test-single</strong>
                <p>Test validation logic với proxy mẫu</p>
            </div>
            
            <div class="endpoint">
                <span class="method get">POST</span>
                <strong>/api/proxy/quick-check</strong>
                <p>Quick check - parse 20 proxy và validate 5 để test toàn bộ flow</p>
            </div>
            
            <h3>🔗 Proxy Sources:</h3>
            <div class="sources-grid">
                {chr(10).join([f'<div class="source-item"><strong>{name}</strong></div>' for name in PROXY_SOURCE_LINKS.keys()])}
            </div>
        </div>
        
        <script>
            let logsVisible = false;
            
            function updateStats() {{
                fetch('/api/proxy/stats')
                    .then(r => r.json())
                    .then(data => {{
                        // Update main stats
                        document.getElementById('proxy-count').textContent = data.alive_count + ' proxy sống';
                        document.getElementById('total-checked').textContent = data.total_checked || 0;
                        document.getElementById('last-update').textContent = data.last_update ? 
                            new Date(data.last_update).toLocaleString() : 'Chưa check';
                        document.getElementById('cache-age').textContent = (data.cache_age_minutes || 0) + ' phút';
                        
                        // Update status indicator
                        const statusEl = document.getElementById('service-status');
                        if (data.is_fetching) {{
                            statusEl.innerHTML = '<span class="status-indicator status-active"></span>Đang fetch...';
                        }} else if (data.is_validating) {{
                            statusEl.innerHTML = '<span class="status-indicator status-active"></span>Đang validate...';
                        }} else {{
                            statusEl.innerHTML = '<span class="status-indicator status-idle"></span>Chờ cycle kế';
                        }}
                        
                        // Update progress bar
                        if (data.total_to_check > 0 && (data.is_fetching || data.is_validating)) {{
                            const progress = Math.round((data.current_progress / data.total_to_check) * 100);
                            document.getElementById('progress-container').style.display = 'block';
                            document.getElementById('progress-fill').style.width = progress + '%';
                            document.getElementById('progress-fill').textContent = progress + '%';
                        }} else {{
                            document.getElementById('progress-container').style.display = 'none';
                        }}
                    }})
                    .catch(e => {{
                        console.error('Error updating stats:', e);
                    }});
            }}
            
            function forceRefresh() {{
                document.getElementById('service-status').innerHTML = 
                    '<span class="status-indicator status-active"></span>Đang force refresh...';
                fetch('/api/proxy/force-refresh', {{method: 'POST'}})
                    .then(r => r.json())
                    .then(data => {{
                        alert(data.message || 'Force refresh started!');
                    }})
                    .catch(e => alert('Error: ' + e));
            }}
            
            function testAPI() {{
                fetch('/api/proxy/alive?count=5')
                    .then(r => r.json())
                    .then(data => {{
                        alert('API Response:\\n' + 
                              'Success: ' + data.success + '\\n' +
                              'Available: ' + data.total_available + '\\n' +
                              'Returned: ' + data.returned_count);
                    }})
                    .catch(e => alert('API Error: ' + e));
            }}
            
            function toggleLogs() {{
                const logsContainer = document.getElementById('logs-container');
                logsVisible = !logsVisible;
                logsContainer.style.display = logsVisible ? 'block' : 'none';
                
                if (logsVisible) {{
                    updateLogs();
                }}
            }}
            
            function updateLogs() {{
                if (!logsVisible) return;
                
                fetch('/api/proxy/logs')
                    .then(r => r.json())
                    .then(data => {{
                        const logsEl = document.getElementById('logs');
                        logsEl.innerHTML = data.logs.map(log => 
                            '<div class="log-item log-' + log.type + '">' +
                            '[' + new Date(log.timestamp).toLocaleTimeString() + '] ' +
                            log.message + '</div>'
                        ).reverse().join('');
                        logsEl.scrollTop = logsEl.scrollHeight;
                    }})
                    .catch(e => {{
                        document.getElementById('logs').innerHTML = '<div class="log-item log-error">Error loading logs</div>';
                    }});
            }}
            
            function debugStatus() {{
                fetch('/api/proxy/debug')
                    .then(r => r.json())
                    .then(data => {{
                        alert('🔍 DEBUG STATUS:\\n' +
                              'Service Status: ' + JSON.stringify(data.service_status, null, 2) + '\\n\\n' +
                              'Proxy Cache: ' + JSON.stringify(data.proxy_cache, null, 2) + '\\n\\n' +
                              'Current Time: ' + data.current_time);
                    }})
                    .catch(e => alert('Debug Error: ' + e));
            }}
            
            function testFetch() {{
                document.getElementById('service-status').innerHTML = 
                    '<span class="status-indicator status-active"></span>Testing fetch...';
                
                fetch('/api/proxy/test-fetch', {{method: 'POST'}})
                    .then(r => r.json())
                    .then(data => {{
                        if (data.success) {{
                            alert('📥 FETCH TEST SUCCESS:\\n' +
                                  'Source: ' + data.source + '\\n' +
                                  'Status: ' + data.status_code + '\\n' +
                                  'Total Lines: ' + data.total_lines + '\\n' +
                                  'Valid Proxies: ' + data.valid_proxies_found + '\\n' +
                                  'Sample: ' + data.sample_proxies.join(', '));
                        }} else {{
                            alert('❌ FETCH TEST FAILED:\\n' + data.error);
                        }}
                    }})
                    .catch(e => alert('Fetch Test Error: ' + e));
            }}
            
            function testValidation() {{
                document.getElementById('service-status').innerHTML = 
                    '<span class="status-indicator status-active"></span>Testing validation...';
                
                fetch('/api/proxy/test-single', {{method: 'POST'}})
                    .then(r => r.json())
                    .then(data => {{
                        if (data.success) {{
                            let results = data.test_results.map(r => 
                                r.proxy + ' = ' + r.status.toUpperCase()
                            ).join('\\n');
                            alert('⚡ VALIDATION TEST:\\n' + results + '\\n\\nCheck logs for details!');
                        }} else {{
                            alert('❌ VALIDATION TEST FAILED:\\n' + data.error);
                        }}
                    }})
                    .catch(e => alert('Validation Test Error: ' + e));
            }}
            
            function quickCheck() {{
                document.getElementById('service-status').innerHTML = 
                    '<span class="status-indicator status-active"></span>Quick checking...';
                
                fetch('/api/proxy/quick-check', {{method: 'POST'}})
                    .then(r => r.json())
                    .then(data => {{
                        if (data.success) {{
                            let resultText = '🚀 QUICK CHECK RESULTS:\\n\\n' +
                                'Source: ' + data.source + '\\n' +
                                'Total Lines: ' + data.total_lines + '\\n' +
                                'Parsed Proxies: ' + data.parsed_count + '\\n' +
                                'Tested: ' + data.tested_count + '\\n' +
                                'Alive: ' + data.alive_count + '\\n' +
                                'Conclusion: ' + data.conclusion + '\\n\\n' +
                                'Validation Results:\\n' +
                                data.validation_results.map(r => 
                                    r.proxy + ' = ' + (r.alive ? 'ALIVE (' + r.speed + 's)' : 'DEAD')
                                ).join('\\n') + '\\n\\n' +
                                'Sample Parsed Proxies:\\n' +
                                data.sample_parsed.slice(0, 5).join('\\n');
                                
                            alert(resultText);
                            
                            if (data.conclusion === 'WORKING') {{
                                // If working, trigger force refresh
                                setTimeout(() => {{
                                    if (confirm('🎉 Proxy parsing WORKS! Do you want to trigger full refresh?')) {{
                                        forceRefresh();
                                    }}
                                }}, 1000);
                            }}
                        }} else {{
                            alert('❌ QUICK CHECK FAILED:\\n' + data.error + '\\n\\nSource: ' + (data.source || 'unknown'));
                        }}
                    }})
                    .catch(e => alert('Quick Check Error: ' + e));
            }}
            
            // Auto-update
            updateStats();
            setInterval(updateStats, 5000); // Update every 5 seconds
            setInterval(() => {{ if (logsVisible) updateLogs(); }}, 3000);
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
            'sources_count': len(PROXY_SOURCE_LINKS)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/proxy/stats', methods=['GET'])
def get_proxy_stats():
    """API thống kê proxy"""
    try:
        last_update = proxy_cache.get('last_update')
        cache_age_minutes = 0
        
        if last_update:
            last_update_dt = datetime.fromisoformat(last_update)
            cache_age_minutes = int((datetime.now() - last_update_dt).total_seconds() / 60)
        
        return jsonify({
            'success': True,
            'alive_count': len(proxy_cache.get('http', [])),
            'total_checked': proxy_cache.get('total_checked', 0),
            'last_update': last_update,
            'cache_age_minutes': cache_age_minutes,
            'sources_count': len(PROXY_SOURCE_LINKS),
            'sources': list(PROXY_SOURCE_LINKS.keys()),
            'service_status': 'running',
            'check_interval': '5 minutes',
            # Status tracking
            'is_fetching': service_status.get('is_fetching', False),
            'is_validating': service_status.get('is_validating', False),
            'current_progress': service_status.get('current_progress', 0),
            'total_to_check': service_status.get('total_to_check', 0),
            'sources_checked': service_status.get('sources_checked', 0),
            'total_sources': service_status.get('total_sources', len(PROXY_SOURCE_LINKS))
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/proxy/force-refresh', methods=['POST'])
def force_refresh():
    """API buộc refresh proxy ngay lập tức"""
    try:
        if service_status.get('is_fetching') or service_status.get('is_validating'):
            return jsonify({
                'success': False,
                'message': 'Service đang bận, vui lòng đợi...'
            })
        
        # Start force refresh in background
        def force_refresh_task():
            try:
                add_log("🚀 FORCE REFRESH được kích hoạt bởi user!", "info")
                
                # Fetch new proxies from sources
                raw_proxies = fetch_proxies_from_sources()
                
                if raw_proxies:
                    # Process more proxies for better coverage
                    limited_proxies = raw_proxies[:1000]
                    add_log(f"🎯 Force refresh: validate {len(limited_proxies)} proxy", "info")
                    
                    # Validate them
                    alive_proxies = validate_proxy_batch(limited_proxies)
                    
                    # Update cache
                    proxy_cache["http"] = alive_proxies
                    proxy_cache["last_update"] = datetime.now().isoformat()
                    proxy_cache["total_checked"] = len(limited_proxies)
                    proxy_cache["alive_count"] = len(alive_proxies)
                    
                    add_log(f"🎉 Force refresh hoàn thành: {len(alive_proxies)} proxy sống!", "success")
                else:
                    add_log("❌ Force refresh: Không fetch được proxy", "error")
                    
            except Exception as e:
                add_log(f"❌ Lỗi force refresh: {str(e)}", "error")
        
        # Start in background thread
        refresh_thread = threading.Thread(target=force_refresh_task, daemon=True)
        refresh_thread.start()
        
        return jsonify({
            'success': True,
            'message': 'Force refresh đã bắt đầu! Kiểm tra logs để theo dõi tiến độ.'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/proxy/logs', methods=['GET'])
def get_logs():
    """API lấy logs của service"""
    try:
        logs = service_status.get('logs', [])
        
        return jsonify({
            'success': True,
            'logs': logs[-50:],  # Return last 50 logs
            'total_logs': len(logs)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/proxy/debug', methods=['GET'])
def debug_status():
    """API debug - kiểm tra tất cả thông tin service"""
    try:
        return jsonify({
            'success': True,
            'service_status': service_status,
            'proxy_cache': {
                'http_count': len(proxy_cache.get('http', [])),
                'last_update': proxy_cache.get('last_update'),
                'total_checked': proxy_cache.get('total_checked', 0),
                'alive_count': proxy_cache.get('alive_count', 0)
            },
            'current_time': datetime.now().isoformat(),
            'sources': list(PROXY_SOURCE_LINKS.keys())
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/proxy/test-single', methods=['POST'])
def test_single_proxy():
    """API test 1 proxy để debug validation logic"""
    try:
        # Test với proxy mẫu
        test_proxies = [
            "8.8.8.8:80",  # Google DNS (sẽ fail vì không phải proxy)
            "proxy.example.com:8080",  # Fake proxy
            "1.1.1.1:80"   # Cloudflare DNS (sẽ fail)
        ]
        
        results = []
        for proxy in test_proxies:
            add_log(f"🧪 Test proxy: {proxy}", "info")
            result = check_single_proxy(proxy, timeout=5)  # Shorter timeout for test
            results.append({
                'proxy': proxy,
                'result': result,
                'status': 'alive' if result else 'dead'
            })
            add_log(f"🧪 Result: {proxy} = {'ALIVE' if result else 'DEAD'}", "success" if result else "error")
        
        return jsonify({
            'success': True,
            'test_results': results,
            'message': f'Tested {len(test_proxies)} proxies'
        })
        
    except Exception as e:
        add_log(f"❌ Error in test-single: {str(e)}", "error")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/proxy/test-fetch', methods=['POST'])
def test_fetch_sources():
    """API test fetch từ 1 source để debug"""
    try:
        # Test với 1 source đầu tiên
        source_name = list(PROXY_SOURCE_LINKS.keys())[0]
        source_urls = PROXY_SOURCE_LINKS[source_name]
        
        add_log(f"🧪 Test fetch từ {source_name}...", "info")
        
        for protocol, source_url in source_urls.items():
            try:
                response = requests.get(source_url, timeout=10)
                
                if response.status_code == 200:
                    content = response.text
                    lines = content.strip().split('\n')
                    
                    # Use NEW relaxed validation logic
                    valid_proxies = []
                    parse_errors = []
                    
                    for i, line in enumerate(lines[:100]):  # Check more lines for better parsing
                        line = line.strip()
                        if not line or line.startswith('#'):
                            continue
                            
                        if ':' in line:
                            try:
                                # Use same logic as in fetch_proxies_from_sources
                                proxy_candidate = line.strip()
                                
                                # Remove common prefixes
                                for prefix in ['http://', 'https://', 'socks4://', 'socks5://']:
                                    if proxy_candidate.startswith(prefix):
                                        proxy_candidate = proxy_candidate[len(prefix):]
                                
                                # Parse proxy format
                                if '@' in proxy_candidate:
                                    auth_part, host_port = proxy_candidate.split('@', 1)
                                    if ':' in host_port:
                                        host, port = host_port.split(':', 1)
                                    else:
                                        parse_errors.append(f"Line {i}: No port in auth format")
                                        continue
                                else:
                                    parts = proxy_candidate.split(':')
                                    if len(parts) >= 2:
                                        host, port = parts[0], parts[1]
                                    else:
                                        parse_errors.append(f"Line {i}: Not enough parts")
                                        continue
                                
                                # Relaxed validation
                                if (host and port and 
                                    port.isdigit() and 
                                    1 <= int(port) <= 65535 and
                                    '.' in host and 
                                    len(host) > 7):
                                    
                                    clean_proxy = f"{host.strip()}:{port.strip()}"
                                    valid_proxies.append(clean_proxy)
                                else:
                                    parse_errors.append(f"Line {i}: Validation failed - host='{host}', port='{port}'")
                                    
                            except Exception as e:
                                parse_errors.append(f"Line {i}: Exception - {str(e)}")
                                continue
                    
                    add_log(f"✅ {source_name} ({protocol}): Tìm thấy {len(valid_proxies)} proxy valid từ {len(lines)} dòng (NEW logic)", "success")
                    
                    return jsonify({
                        'success': True,
                        'source': source_name,
                        'protocol': protocol,
                        'url': source_url,
                        'status_code': response.status_code,
                        'total_lines': len(lines),
                        'valid_proxies_found': len(valid_proxies),
                        'sample_proxies': valid_proxies[:5],
                        'raw_sample': lines[:10],
                        'parse_errors': parse_errors[:5],  # First 5 errors for debug
                        'validation_method': 'NEW_RELAXED'
                    })
                else:
                    add_log(f"❌ {source_name} ({protocol}): HTTP {response.status_code}", "error")
                    return jsonify({
                        'success': False,
                        'source': source_name,
                        'protocol': protocol,
                        'status_code': response.status_code,
                        'error': f'HTTP {response.status_code}'
                    })
            except Exception as e:
                add_log(f"❌ Error test-fetch for {source_name} ({protocol}): {str(e)}", "error")
                return jsonify({
                    'success': False,
                    'source': source_name,
                    'protocol': protocol,
                    'error': str(e)
                }), 500
        
        return jsonify({
            'success': False,
            'message': f'Không thể test fetch từ {source_name} do lỗi không xác định.'
        }), 500
        
    except Exception as e:
        add_log(f"❌ Error test-fetch: {str(e)}", "error")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/proxy/quick-check', methods=['POST'])
def quick_check():
    """API quick check - fetch và validate 20 proxy nhanh"""
    try:
        add_log("🚀 QUICK CHECK bắt đầu...", "info")
        
        # Fetch từ source đầu tiên
        source_name = list(PROXY_SOURCE_LINKS.keys())[0]
        source_urls = PROXY_SOURCE_LINKS[source_name]
        
        add_log(f"🔍 Fetching from {source_name}...", "info")
        
        for protocol, source_url in source_urls.items():
            try:
                response = requests.get(source_url, timeout=15)
                
                if response.status_code != 200:
                    add_log(f"❌ {source_name} ({protocol}): HTTP {response.status_code}", "error")
                    continue
                
                # Parse với TOOL LOGIC
                content = response.text
                lines = content.strip().split('\n')
                parsed_proxies = []
                parse_stats = {'total_lines': 0, 'valid_format': 0, 'auto_detected': {}}
                
                add_log(f"📝 Parsing {len(lines)} lines from {source_name} ({protocol})...", "info")
                
                for line in lines:  # Process ALL lines from source
                    line = line.strip()
                    parse_stats['total_lines'] += 1
                    
                    if not line or line.startswith('#'):
                        continue
                        
                    if ':' in line:
                        # Clean prefixes
                        proxy_candidate = line.strip()
                        for prefix in ['http://', 'https://', 'socks4://', 'socks5://']:
                            if proxy_candidate.startswith(prefix):
                                proxy_candidate = proxy_candidate[len(prefix):]
                        
                        # Use tool's parse logic
                        parsed = parse_proxy_line(proxy_candidate, "auto")
                        if parsed:
                            clean_proxy = f"{parsed['host']}:{parsed['port']}"
                            parsed_proxies.append(clean_proxy)
                            parse_stats['valid_format'] += 1
                            
                            # Track auto-detected protocols
                            protocol = parsed['type']
                            parse_stats['auto_detected'][protocol] = parse_stats['auto_detected'].get(protocol, 0) + 1
                            
                            if len(parsed_proxies) >= 1000:  # Allow up to 1000 proxies per source
                                break
                
                protocol_summary = ", ".join([f"{k}: {v}" for k, v in parse_stats['auto_detected'].items()])
                add_log(f"🎯 Parsed {len(parsed_proxies)} proxy từ {source_name} ({protocol}) | Protocols: {protocol_summary}", "success")
                
                if not parsed_proxies:
                    add_log(f"❌ {source_name} ({protocol}): Không parse được proxy nào", "error")
                    continue
                
                # Test validate 5 proxy đầu tiên giống tool
                test_proxies = parsed_proxies[:5]
                validated_results = []
                
                add_log(f"🧪 Testing {len(test_proxies)} proxies from {source_name} ({protocol})...", "info")
                
                for i, proxy in enumerate(test_proxies):
                    add_log(f"🔍 Testing {i+1}/{len(test_proxies)}: {proxy}", "info")
                    
                    # Check if this is from mixed source -> use special validation
                    if source_name == "Mixed Sources":
                        result = check_mixed_proxy_all_protocols(proxy, timeout=8)
                        if result:
                            validated_results.append({
                                'proxy': proxy,
                                'alive': True,
                                'speed': result['speed'],
                                'latency': result['latency'],
                                'ip': result['ip'],
                                'type': result['type'],
                                'method': 'mixed_protocol_test'
                            })
                            add_log(f"✅ MIXED ALIVE: {proxy} → {result['ip']} | {result['latency']}ms | Protocol: {result['type']}", "success")
                        else:
                            validated_results.append({
                                'proxy': proxy,
                                'alive': False,
                                'speed': None,
                                'error': 'Failed all protocols',
                                'method': 'mixed_protocol_test'
                            })
                            add_log(f"💀 MIXED DEAD: {proxy} → Failed all protocols", "error")
                    else:
                        # Standard validation for categorized sources
                        result = check_single_proxy(proxy, timeout=8)
                        if result and result['status'] == 'alive':
                            validated_results.append({
                                'proxy': proxy,
                                'alive': True,
                                'speed': result['speed'],
                                'latency': result['latency'],
                                'ip': result['ip'],
                                'type': result['type'],
                                'method': 'categorized_test'
                            })
                            add_log(f"✅ ALIVE: {proxy} → {result['ip']} | {result['latency']}ms", "success")
                        else:
                            error_msg = result.get('error', 'Unknown error') if result else 'Parse failed'
                            validated_results.append({
                                'proxy': proxy,
                                'alive': False,
                                'speed': None,
                                'error': error_msg,
                                'method': 'categorized_test'
                            })
                            add_log(f"💀 DEAD: {proxy} → {error_msg}", "error")
                
                alive_count = sum(1 for r in validated_results if r['alive'])
                success_rate = (alive_count/len(test_proxies)*100) if test_proxies else 0
                add_log(f"📊 Quick check complete for {source_name} ({protocol}): {alive_count}/{len(test_proxies)} alive ({success_rate:.1f}%)", "info")
                
                # If any source is working, return success
                if alive_count > 0:
                    return jsonify({
                        'success': True,
                        'source': source_name,
                        'protocol': protocol,
                        'total_lines': len(lines),
                        'parsed_count': len(parsed_proxies),
                        'tested_count': len(test_proxies),
                        'alive_count': alive_count,
                        'sample_parsed': parsed_proxies[:10],
                        'validation_results': validated_results,
                        'parse_stats': parse_stats,
                        'parse_ratio': f"{len(parsed_proxies)}/{len(lines)} ({len(parsed_proxies)/len(lines)*100:.1f}%)",
                        'alive_ratio': f"{alive_count}/{len(test_proxies)} ({success_rate:.1f}%)",
                        'conclusion': 'WORKING'
                    })
            
            except Exception as e:
                add_log(f"❌ Quick check error for {source_name} ({protocol}): {str(e)}", "error")
                continue
        
        return jsonify({
            'success': False,
            'error': 'Không tìm thấy proxy sống từ bất kỳ nguồn nào trong danh sách nhanh kiểm tra.',
            'sources_checked': list(PROXY_SOURCE_LINKS.keys()),
            'conclusion': 'NEED_INVESTIGATION'
        })
        
    except Exception as e:
        add_log(f"❌ Quick check error: {str(e)}", "error")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    # Initialize logging
    add_log("🚀 Khởi động Proxy Validation Service...", "info")
    
    # Start background refresh thread
    add_log("🔧 Khởi động background refresh thread...", "info")
    refresh_thread = threading.Thread(target=background_proxy_refresh, daemon=True)
    refresh_thread.start()
    
    # INITIAL PROXY LOAD NHANH - Có kết quả trong 30-60 giây
    add_log("⚡ BẮT ĐẦU INITIAL LOAD NHANH...", "info")
    try:
        initial_proxies = fetch_proxies_from_sources()
        if initial_proxies:
            # STRATEGY: Load hợp lý để có kết quả chính xác
            limited_initial = initial_proxies[:400]  # Pool 400 proxy cho initial load
            add_log(f"🚀 INITIAL BALANCED LOAD: {len(limited_initial)} proxy từ {len(initial_proxies)} tổng | Target: 40 alive", "info")
            
            # Use cân bằng validation cho initial load
            initial_alive = validate_proxy_batch_fast(
                limited_initial,
                max_workers=50,      # Workers cân bằng
                target_alive=40,     # Target 40 proxy để bắt đầu tốt
                chunk_size=40,       # Chunks hợp lý
                timeout=8           # Timeout chuẩn 8s
            )
            
            proxy_cache["http"] = initial_alive
            proxy_cache["last_update"] = datetime.now().isoformat()
            proxy_cache["total_checked"] = len(limited_initial)
            proxy_cache["alive_count"] = len(initial_alive)
            
            if len(initial_alive) > 0:
                add_log(f"🎉 INITIAL LOAD THÀNH CÔNG: {len(initial_alive)} proxy sống! Service sẵn sàng.", "success")
            else:
                add_log("⚠️ Initial load: Chưa có proxy sống, background sẽ tiếp tục tìm...", "info")
        else:
            add_log("❌ Initial load: Không fetch được proxy từ sources", "error")
    except Exception as e:
        add_log(f"❌ Lỗi initial load: {str(e)}", "error")
        # Set empty cache để service vẫn chạy được
        proxy_cache["http"] = []
        proxy_cache["last_update"] = datetime.now().isoformat()
        proxy_cache["total_checked"] = 0
        proxy_cache["alive_count"] = 0
    
    # Start Flask app
    port = int(os.environ.get('PORT', 5000))
    add_log(f"🌐 Khởi động Flask app trên port {port}", "info")
    print(f"🌐 Starting Flask app on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False) 