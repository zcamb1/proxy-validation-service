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

# Nguồn proxy giống như trong tab kiểm tra proxy của tool
PROXY_SOURCE_LINKS = {
    "Server Alpha": "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/all/data.txt",
    "Server Beta": "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt", 
    "Server Gamma": "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
    "Server Delta": "https://raw.githubusercontent.com/hookzof/socks5_list/master/proxy.txt",
    "Server Echo": "https://api.proxyscrape.com/v2/?request=get&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all&format=textplain",
    "Server Foxtrot": "https://www.proxy-list.download/api/v1/get?type=http",
    "Server Golf": "https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt",
    "Server Hotel": "https://raw.githubusercontent.com/sunny9577/proxy-scraper/master/proxies.txt"
}

def check_single_proxy(proxy_string, timeout=8):
    """Kiểm tra 1 proxy có sống không - giống logic trong tool"""
    try:
        if ':' not in proxy_string:
            return None
            
        # Parse proxy format: host:port hoặc username:password@host:port
        if '@' in proxy_string:
            auth_part, host_port = proxy_string.split('@')
            if ':' in auth_part:
                username, password = auth_part.split(':')
            else:
                username, password = auth_part, ""
        else:
            username, password = None, None
            host_port = proxy_string

        if ':' not in host_port:
            return None
            
        host, port = host_port.strip().split(':')
        
        # Test URLs 
        test_urls = [
            'http://httpbin.org/ip',
            'http://ip-api.com/json',
        ]
        
        # Setup proxy
        if username and password:
            proxy_url = f"http://{username}:{password}@{host}:{port}"
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
                        'type': 'http',
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
                
    except Exception as e:
        pass
    
    return None

def fetch_proxies_from_sources():
    """Lấy proxy từ các nguồn giống tab kiểm tra proxy"""
    all_proxies = []
    
    print("🔍 Fetching proxies from sources...")
    
    for source_name, source_url in PROXY_SOURCE_LINKS.items():
        try:
            print(f"📥 Fetching from {source_name}: {source_url}")
            
            response = requests.get(source_url, timeout=30)
            
            if response.status_code == 200:
                content = response.text
                
                # Parse proxy list
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
                                # username:password@host:port format
                                auth_part, host_port = line.split('@')
                                host, port = host_port.split(':')
                            else:
                                # host:port format
                                host, port = line.split(':')
                            
                            # Basic validation
                            if len(host.split('.')) == 4 and port.isdigit():
                                source_proxies.append(line)
                                
                        except:
                            continue
                
                all_proxies.extend(source_proxies)
                print(f"✅ {source_name}: Found {len(source_proxies)} proxies")
        
        except Exception as e:
            print(f"❌ Error fetching from {source_name}: {e}")
            continue
    
    # Remove duplicates
    unique_proxies = list(set(all_proxies))
    print(f"🎯 Total unique proxies collected: {len(unique_proxies)}")
    
    return unique_proxies

def validate_proxy_batch(proxy_list, max_workers=30):
    """Validate proxy list với threading"""
    alive_proxies = []
    
    print(f"🔄 Starting validation of {len(proxy_list)} proxies with {max_workers} workers")
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all proxy checks
        future_to_proxy = {executor.submit(check_single_proxy, proxy): proxy for proxy in proxy_list}
        
        completed = 0
        for future in as_completed(future_to_proxy):
            result = future.result()
            completed += 1
            
            if result:
                alive_proxies.append(result)
                print(f"✅ Alive: {result['proxy_string']} | Speed: {result['speed']}s | IP: {result['ip']}")
            
            # Progress report every 50 proxies
            if completed % 50 == 0:
                print(f"📊 Progress: {completed}/{len(proxy_list)} checked | {len(alive_proxies)} alive")
    
    print(f"🎉 Validation complete: {len(alive_proxies)} alive out of {len(proxy_list)} total")
    return alive_proxies

def background_proxy_refresh():
    """Background task chạy mỗi 5 phút để refresh proxy"""
    while True:
        try:
            print("🔄 Starting 5-minute proxy refresh cycle...")
            
            # Fetch new proxies from sources
            raw_proxies = fetch_proxies_from_sources()
            
            if raw_proxies:
                # Limit to 400 proxies để tránh timeout
                limited_proxies = raw_proxies[:400]
                print(f"🎯 Validating {len(limited_proxies)} proxies (limited from {len(raw_proxies)})")
                
                # Validate them
                alive_proxies = validate_proxy_batch(limited_proxies)
                
                # Update cache
                proxy_cache["http"] = alive_proxies
                proxy_cache["last_update"] = datetime.now().isoformat()
                proxy_cache["total_checked"] = len(limited_proxies)
                proxy_cache["alive_count"] = len(alive_proxies)
                
                print(f"✅ Cache updated: {len(alive_proxies)} alive proxies")
            else:
                print("❌ No proxies fetched from sources")
            
            # Sleep for 5 minutes = 300 seconds
            print("😴 Sleeping for 5 minutes before next check...")
            time.sleep(5 * 60)
            
        except Exception as e:
            print(f"❌ Error in background refresh: {e}")
            # Sleep 1 minute on error then retry
            time.sleep(60)

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
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }}
            .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
            .endpoint {{ background: #f8f9fa; padding: 15px; margin: 15px 0; border-radius: 8px; border-left: 4px solid #007bff; }}
            .method {{ color: #fff; padding: 5px 10px; border-radius: 4px; font-size: 12px; font-weight: bold; }}
            .get {{ background: #28a745; }}
            .stats {{ background: #e3f2fd; padding: 20px; border-radius: 8px; margin: 20px 0; }}
            .live-count {{ font-size: 24px; color: #2e7d32; font-weight: bold; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 Proxy Validation Service</h1>
            <p>Service tự động kiểm tra proxy sống mỗi 5 phút từ {len(PROXY_SOURCE_LINKS)} nguồn khác nhau</p>
            
            <div class="stats">
                <h3>📊 Live Stats:</h3>
                <div id="stats">Loading...</div>
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
            
            <h3>🔗 Proxy Sources:</h3>
            <ul>
                {chr(10).join([f'<li><strong>{name}</strong></li>' for name in PROXY_SOURCE_LINKS.keys()])}
            </ul>
        </div>
        
        <script>
            function updateStats() {{
                fetch('/api/proxy/stats')
                    .then(r => r.json())
                    .then(data => {{
                        document.getElementById('stats').innerHTML = 
                            '<div class="live-count">' + data.alive_count + ' proxy sống</div>' +
                            '<p>Tổng đã kiểm tra: ' + data.total_checked + '</p>' +
                            '<p>Lần check cuối: ' + (data.last_update ? new Date(data.last_update).toLocaleString() : 'Chưa check') + '</p>' +
                            '<p>Tuổi cache: ' + (data.cache_age_minutes || 0) + ' phút</p>';
                    }})
                    .catch(e => {{
                        document.getElementById('stats').innerHTML = '<p>Error loading stats</p>';
                    }});
            }}
            
            updateStats();
            setInterval(updateStats, 30000); // Update every 30 seconds
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
            'check_interval': '5 minutes'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    # Start background refresh thread
    print("🚀 Starting background proxy refresh service...")
    refresh_thread = threading.Thread(target=background_proxy_refresh, daemon=True)
    refresh_thread.start()
    
    # Initial proxy load
    print("🔄 Starting initial proxy load...")
    try:
        initial_proxies = fetch_proxies_from_sources()
        if initial_proxies:
            # Limit initial load to 200 proxies
            limited_initial = initial_proxies[:200]
            initial_alive = validate_proxy_batch(limited_initial)
            proxy_cache["http"] = initial_alive
            proxy_cache["last_update"] = datetime.now().isoformat()
            proxy_cache["total_checked"] = len(limited_initial)
            proxy_cache["alive_count"] = len(initial_alive)
            print(f"✅ Initial load complete: {len(initial_alive)} alive proxies")
        else:
            print("❌ No proxies loaded initially")
    except Exception as e:
        print(f"❌ Error in initial load: {e}")
    
    # Start Flask app
    port = int(os.environ.get('PORT', 5000))
    print(f"🌐 Starting Flask app on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False) 