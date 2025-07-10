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
            'http://icanhazip.com'
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
    """Lấy proxy từ các nguồn giống tab kiểm tra proxy"""
    service_status["is_fetching"] = True
    service_status["sources_checked"] = 0
    service_status["current_progress"] = 0
    
    all_proxies = []
    
    add_log("🔍 Bắt đầu fetch proxy từ các nguồn...", "info")
    
    for i, (source_name, source_url) in enumerate(PROXY_SOURCE_LINKS.items()):
        try:
            add_log(f"📥 Đang fetch từ {source_name}...", "info")
            
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
                add_log(f"✅ {source_name}: Tìm thấy {len(source_proxies)} proxy", "success")
            else:
                add_log(f"❌ {source_name}: HTTP {response.status_code}", "error")
        
        except Exception as e:
            add_log(f"❌ {source_name}: {str(e)}", "error")
            
        service_status["sources_checked"] = i + 1
        service_status["current_progress"] = i + 1
    
    # Remove duplicates
    unique_proxies = list(set(all_proxies))
    add_log(f"🎯 Tổng cộng thu thập {len(unique_proxies)} proxy unique", "success")
    
    service_status["is_fetching"] = False
    return unique_proxies

def validate_proxy_batch(proxy_list, max_workers=30):
    """Validate proxy list với threading"""
    service_status["is_validating"] = True
    service_status["total_to_check"] = len(proxy_list)
    service_status["current_progress"] = 0
    
    alive_proxies = []
    
    add_log(f"🔄 Bắt đầu validate {len(proxy_list)} proxy với {max_workers} workers", "info")
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all proxy checks
        future_to_proxy = {executor.submit(check_single_proxy, proxy): proxy for proxy in proxy_list}
        
        completed = 0
        for future in as_completed(future_to_proxy):
            result = future.result()
            completed += 1
            service_status["current_progress"] = completed
            
            if result:
                alive_proxies.append(result)
                add_log(f"✅ Proxy sống: {result['proxy_string']} | Tốc độ: {result['speed']}s", "success")
            
            # Progress report every 25 proxies
            if completed % 25 == 0:
                progress_percent = round((completed / len(proxy_list)) * 100, 1)
                add_log(f"📊 Tiến độ: {completed}/{len(proxy_list)} ({progress_percent}%) | {len(alive_proxies)} proxy sống", "info")
    
    service_status["is_validating"] = False
    service_status["current_progress"] = 0
    service_status["total_to_check"] = 0
    
    add_log(f"🎉 Validation hoàn thành: {len(alive_proxies)} proxy sống / {len(proxy_list)} tổng cộng", "success")
    return alive_proxies

def background_proxy_refresh():
    """Background task chạy mỗi 5 phút để refresh proxy"""
    while True:
        try:
            add_log("🔄 Bắt đầu chu kỳ refresh 5 phút...", "info")
            
            # Fetch new proxies from sources
            raw_proxies = fetch_proxies_from_sources()
            
            if raw_proxies:
                # Limit to 400 proxies để tránh timeout
                limited_proxies = raw_proxies[:400]
                add_log(f"🎯 Giới hạn validate {len(limited_proxies)} proxy (từ {len(raw_proxies)} tổng)", "info")
                
                # Validate them
                alive_proxies = validate_proxy_batch(limited_proxies)
                
                # Update cache
                proxy_cache["http"] = alive_proxies
                proxy_cache["last_update"] = datetime.now().isoformat()
                proxy_cache["total_checked"] = len(limited_proxies)
                proxy_cache["alive_count"] = len(alive_proxies)
                
                add_log(f"✅ Cache updated: {len(alive_proxies)} proxy sống từ {len(limited_proxies)} đã kiểm tra", "success")
            else:
                add_log("❌ Không fetch được proxy từ các nguồn", "error")
            
            # Sleep for 5 minutes = 300 seconds
            add_log("😴 Nghỉ 5 phút trước chu kỳ tiếp theo...", "info")
            time.sleep(5 * 60)
            
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
                    # Limit to 200 proxies for faster refresh
                    limited_proxies = raw_proxies[:200]
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
        source_url = PROXY_SOURCE_LINKS[source_name]
        
        add_log(f"🧪 Test fetch từ {source_name}: {source_url}", "info")
        
        response = requests.get(source_url, timeout=10)
        
        if response.status_code == 200:
            content = response.text
            lines = content.strip().split('\n')
            
            valid_proxies = []
            for line in lines[:10]:  # Only check first 10 lines
                line = line.strip()
                if ':' in line:
                    try:
                        host, port = line.split(':')
                        if len(host.split('.')) == 4 and port.isdigit():
                            valid_proxies.append(line)
                    except:
                        continue
            
            add_log(f"✅ {source_name}: Tìm thấy {len(valid_proxies)} proxy valid từ {len(lines)} dòng", "success")
            
            return jsonify({
                'success': True,
                'source': source_name,
                'url': source_url,
                'status_code': response.status_code,
                'total_lines': len(lines),
                'valid_proxies_found': len(valid_proxies),
                'sample_proxies': valid_proxies[:5],
                'raw_sample': lines[:5]
            })
        else:
            add_log(f"❌ {source_name}: HTTP {response.status_code}", "error")
            return jsonify({
                'success': False,
                'source': source_name,
                'status_code': response.status_code,
                'error': f'HTTP {response.status_code}'
            })
        
    except Exception as e:
        add_log(f"❌ Error test-fetch: {str(e)}", "error")
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
    
    # Initial proxy load
    add_log("🔄 Bắt đầu initial proxy load...", "info")
    try:
        initial_proxies = fetch_proxies_from_sources()
        if initial_proxies:
            # Limit initial load to 200 proxies
            limited_initial = initial_proxies[:200]
            add_log(f"🎯 Initial load: giới hạn {len(limited_initial)} proxy từ {len(initial_proxies)} tổng", "info")
            initial_alive = validate_proxy_batch(limited_initial)
            proxy_cache["http"] = initial_alive
            proxy_cache["last_update"] = datetime.now().isoformat()
            proxy_cache["total_checked"] = len(limited_initial)
            proxy_cache["alive_count"] = len(initial_alive)
            add_log(f"✅ Initial load hoàn thành: {len(initial_alive)} proxy sống!", "success")
        else:
            add_log("❌ Initial load: Không có proxy nào được load", "error")
    except Exception as e:
        add_log(f"❌ Lỗi initial load: {str(e)}", "error")
    
    # Start Flask app
    port = int(os.environ.get('PORT', 5000))
    add_log(f"🌐 Khởi động Flask app trên port {port}", "info")
    print(f"🌐 Starting Flask app on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False) 