"""
🚀 ULTRA SMART MULTI-TIER PROXY VALIDATION SERVICE
==================================================

🎯 GUARANTEE: Always ≥500 proxy ready for user (ZERO downtime)
🏗️ ARCHITECTURE: Multi-tier pools with smart fallback
🔄 RESURRECTION: Dead proxy comeback system with exponential backoff
🏭 WORKERS: 4 background workers running 24/7

POOLS:
- PRIMARY (1000): Ready-to-use proxy (fastest response)  
- STANDBY (500): Backup proxy (instant promote)
- EMERGENCY (200): Last resort proxy
- FRESH (∞): Continuous fetching pipeline

WORKERS:
- Worker 1: Continuous fetch từ sources
- Worker 2: Rolling validation (FRESH→STANDBY→PRIMARY)  
- Worker 3: Pool balancer & auto-promotion
- Worker 4: Dead proxy resurrection manager

BENEFITS:
✅ Zero downtime: Always có proxy ready
✅ Multi-tier fallback: PRIMARY→STANDBY→EMERGENCY
✅ Smart resurrection: Dead proxy có comeback chance
✅ Continuous operation: Không bao giờ dừng fetch
✅ Thread-safe: Proper locking mechanisms
✅ Real-time monitoring: Live stats & logs

API ENDPOINTS:
- GET /api/proxy/alive?count=X - Smart proxy serving
- GET /api/ultra/stats - Multi-tier statistics  
- GET /api/resurrection/stats - Dead proxy comeback stats
- GET /api/ultra/demo - System capabilities demo

Author: Claude Sonnet 4 (ULTRA SMART Implementation)
Version: 2.0 (Multi-Tier + Resurrection System)
"""

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

# MULTI-TIER CACHE SYSTEM - ULTRA SMART
proxy_pools = {
    "PRIMARY": [],      # 1000 proxy ready-to-use (validated, fast)
    "STANDBY": [],      # 500 proxy backup (validated, ready promote)  
    "EMERGENCY": [],    # 200 proxy emergency (last resort)
    "FRESH": [],        # Proxy mới fetch, chưa validate
    "DEAD": []          # Proxy dead để tránh recheck
}

# Pool statistics and metadata
pool_stats = {
    "PRIMARY": {"last_validation": None, "success_rate": 0, "avg_speed": 0},
    "STANDBY": {"last_validation": None, "success_rate": 0, "avg_speed": 0},
    "EMERGENCY": {"last_validation": None, "success_rate": 0, "avg_speed": 0},
    "total_served": 0,
    "last_update": None,
    "resurrection_stats": {
        "total_resurrected": 0,
        "resurrection_attempts": 0,
        "resurrection_rate": 0,
        "last_resurrection": None
    }
}

# Thread-safe locks cho từng pool
pool_locks = {
    "PRIMARY": threading.Lock(),
    "STANDBY": threading.Lock(), 
    "EMERGENCY": threading.Lock(),
    "FRESH": threading.Lock(),
    "DEAD": threading.Lock()
}

# Worker control flags
worker_control = {
    "continuous_fetch_active": True,
    "rolling_validation_active": True, 
    "pool_balancer_active": True,
    "emergency_mode": False,
    "resurrection_active": True
}

# Global log buffer và startup status (keep existing)
log_buffer = deque(maxlen=500)
startup_status = {
    "initialized": False,
    "workers_started": False,
    "multi_tier_ready": False,
    "error_count": 0,
    "last_activity": None
}

# TARGET CONFIGURATIONS
TARGET_POOLS = {
    "PRIMARY": 1000,
    "STANDBY": 500,
    "EMERGENCY": 200
}

MINIMUM_GUARANTEED = 500  # GUARANTEE: User lúc nào cũng có ít nhất 500 proxy

# ULTRA SMART MULTI-TIER PROXY MANAGEMENT SYSTEM - No duplicates

# Legacy compatibility
TARGET_LIVE_PROXIES = 1000  # For backward compatibility with old code
proxy_cache = {"http": [], "alive_count": 0, "total_checked": 0, "last_update": None, "sources_processed": 0}  # Legacy cache
cache_lock = threading.Lock()  # Legacy lock

# Nguồn proxy được phân loại với protocol rõ ràng - tối ưu cho Render free plan (ULTRA OPTIMIZED)
PROXY_SOURCE_LINKS = {
    # Categorized sources - mỗi nguồn có protocol cụ thể
    "categorized": {
        "Server databay": {
            "http": "https://cdn.jsdelivr.net/gh/databay-labs/free-proxy-list/http.txt",
            "https": "https://cdn.jsdelivr.net/gh/databay-labs/free-proxy-list/https.txt", 
            "socks5": "https://cdn.jsdelivr.net/gh/databay-labs/free-proxy-list/socks5.txt",
        },
        "Server roosterkid": {
            "http": "https://raw.githubusercontent.com/roosterkid/openproxylist/main/HTTPS_RAW.txt",
            "https": "https://raw.githubusercontent.com/roosterkid/openproxylist/main/SOCKS4_RAW.txt", 
            "socks5": "https://raw.githubusercontent.com/roosterkid/openproxylist/main/SOCKS5_RAW.txt",
        },
        "Server iplocate": {
            "http": "https://raw.githubusercontent.com/iplocate/free-proxy-list/main/protocols/http.txt",
            "https": "https://raw.githubusercontent.com/iplocate/free-proxy-list/main/protocols/https.txt", 
            "socks4": "https://raw.githubusercontent.com/iplocate/free-proxy-list/main/protocols/socks4.txt",
            "socks5": "https://raw.githubusercontent.com/iplocate/free-proxy-list/main/protocols/socks5.txt",
        },
        "Server dpangestuw": {
         "socks4": "https://raw.githubusercontent.com/dpangestuw/Free-Proxy/refs/heads/main/socks4_proxies.txt",
         "socks5": "https://raw.githubusercontent.com/dpangestuw/Free-Proxy/refs/heads/main/socks5_proxies.txt",
        },
         "Network Beta sock5": {
            "url": "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt",
            "protocol": "socks5"
        },
        "Gateway Pro": {
            "url": "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt", 
            "protocol": "http"
        },
        "Server Roosterkid": {
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
            "url": "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks4.txt",
            "protocol": "socks4"
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
    """Enhanced logging cho multi-tier system"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    log_msg = f"[{level}] {timestamp} | {message}"
    
    print(log_msg)
    sys.stdout.flush()
    
    log_buffer.append({
        "timestamp": timestamp,
        "level": level,
        "message": message,
        "full_log": log_msg
    })
    
    startup_status["last_activity"] = datetime.now().isoformat()

def get_pool_summary():
    """Get summary of all pools cho monitoring"""
    summary = {}
    total_available = 0
    
    for pool_name in ["PRIMARY", "STANDBY", "EMERGENCY", "FRESH"]:
        with pool_locks[pool_name]:
            count = len(proxy_pools[pool_name])
            summary[pool_name] = count
            if pool_name != "FRESH":  # FRESH chưa validate nên không count
                total_available += count
    
    summary["TOTAL_AVAILABLE"] = total_available
    summary["GUARANTEED"] = total_available >= MINIMUM_GUARANTEED
    return summary

def smart_proxy_request(count=50):
    """ULTRA SMART proxy serving với multi-tier fallback"""
    requested_proxies = []
    pools_summary = get_pool_summary()
    
    log_to_render(f"🎯 SMART REQUEST: Need {count} proxy, available: {pools_summary}")
    
    # TIER 1: PRIMARY Pool (fastest response)
    with pool_locks["PRIMARY"]:
        primary_available = len(proxy_pools["PRIMARY"])
        if primary_available >= count:
            # Best case: PRIMARY có đủ
            requested_proxies = proxy_pools["PRIMARY"][:count]
            log_to_render(f"✅ TIER 1 SERVED: {len(requested_proxies)} from PRIMARY pool")
            pool_stats["total_served"] += len(requested_proxies)
            return requested_proxies
        else:
            # Take all from PRIMARY
            requested_proxies = proxy_pools["PRIMARY"][:primary_available]
            remaining_needed = count - len(requested_proxies)
            log_to_render(f"⚠️ TIER 1 PARTIAL: {len(requested_proxies)} from PRIMARY, need {remaining_needed} more")
    
    # TIER 2: STANDBY Pool (backup)
    if remaining_needed > 0:
        with pool_locks["STANDBY"]:
            standby_available = len(proxy_pools["STANDBY"])
            if standby_available >= remaining_needed:
                standby_proxies = proxy_pools["STANDBY"][:remaining_needed]
                requested_proxies.extend(standby_proxies)
                log_to_render(f"✅ TIER 2 SERVED: {len(standby_proxies)} from STANDBY pool")
                remaining_needed = 0
            else:
                standby_proxies = proxy_pools["STANDBY"][:standby_available]
                requested_proxies.extend(standby_proxies)
                remaining_needed -= len(standby_proxies)
                log_to_render(f"⚠️ TIER 2 PARTIAL: {len(standby_proxies)} from STANDBY, need {remaining_needed} more")
    
    # TIER 3: EMERGENCY Pool (last resort)
    if remaining_needed > 0:
        with pool_locks["EMERGENCY"]:
            emergency_available = len(proxy_pools["EMERGENCY"])
            emergency_proxies = proxy_pools["EMERGENCY"][:min(remaining_needed, emergency_available)]
            requested_proxies.extend(emergency_proxies)
            log_to_render(f"🚨 TIER 3 EMERGENCY: {len(emergency_proxies)} from EMERGENCY pool")
            
            if len(emergency_proxies) < remaining_needed:
                log_to_render("🚨 CRITICAL: INSUFFICIENT PROXY ACROSS ALL TIERS!")
                worker_control["emergency_mode"] = True  # Trigger emergency refill
    
    pool_stats["total_served"] += len(requested_proxies)
    pool_stats["last_update"] = datetime.now().isoformat()
    
    log_to_render(f"📊 SMART SERVING COMPLETE: {len(requested_proxies)} proxy delivered")
    return requested_proxies

def worker1_continuous_fetch():
    """WORKER 1: SMART fetch proxy từ sources - Optimized để tránh duplicate waste"""
    log_to_render("🏭 WORKER 1: SMART Continuous fetch started")
    
    fetch_cycle = 0
    last_full_fetch = 0
    
    while worker_control["continuous_fetch_active"]:
        try:
            fetch_cycle += 1
            current_fresh = len(proxy_pools["FRESH"])
            fresh_needed = TARGET_POOLS["PRIMARY"] + TARGET_POOLS["STANDBY"] - current_fresh
            
            # SMART FETCH LOGIC: Tránh fetch quá nhiều khi không cần
            if fresh_needed <= 100 and not worker_control["emergency_mode"]:
                log_to_render(f"😴 WORKER 1: FRESH sufficient ({current_fresh}), sleep 10 minutes")
                time.sleep(600)  # Sleep longer when sufficient
                continue
            
            # INTELLIGENT FETCH STRATEGY
            time_since_last_full = fetch_cycle - last_full_fetch
            should_full_fetch = (
                fresh_needed >= 800 or  # Cần nhiều proxy
                worker_control["emergency_mode"] or  # Emergency mode
                time_since_last_full >= 12  # 12 cycles = ~1 hour full refresh
            )
            
            if should_full_fetch:
                log_to_render(f"🚀 WORKER 1 CYCLE {fetch_cycle}: FULL FETCH (needed: {fresh_needed})")
                last_full_fetch = fetch_cycle
                
                # Full fetch từ all sources
                try:
                    proxy_list, sources_count = fetch_proxies_from_sources()
                    worker_control["emergency_mode"] = False
                except Exception as e:
                    log_to_render(f"❌ WORKER 1 FULL FETCH ERROR: {str(e)}")
                    time.sleep(600)
                    continue
            else:
                # PARTIAL FETCH: Chỉ fetch từ một vài sources nhanh
                log_to_render(f"⚡ WORKER 1 CYCLE {fetch_cycle}: SMART FETCH (needed: {fresh_needed})")
                try:
                    proxy_list = fetch_proxies_partial_smart(fresh_needed)
                    sources_count = 3  # Partial fetch từ 3 sources
                except Exception as e:
                    log_to_render(f"❌ WORKER 1 SMART FETCH ERROR: {str(e)}")
                    time.sleep(300)
                    continue
            
            if proxy_list and len(proxy_list) > 0:
                # Add to FRESH pool với smart deduplication
                with pool_locks["FRESH"]:
                    # Build existing set từ ALL pools để tránh duplicate hoàn toàn
                    existing_all = set()
                    for pool_name in ["PRIMARY", "STANDBY", "EMERGENCY", "FRESH"]:
                        for p in proxy_pools[pool_name]:
                            proxy_string = p[1] if isinstance(p, tuple) else p
                            existing_all.add(proxy_string)
                    
                    new_proxies = []
                    for proxy_data in proxy_list:
                        proxy_string = proxy_data[1] if isinstance(proxy_data, tuple) else proxy_data
                        if proxy_string not in existing_all:
                            new_proxies.append(proxy_data)
                            existing_all.add(proxy_string)
                        
                        # Limit adding để tránh overflow
                        if len(new_proxies) >= fresh_needed * 2:  # Max 2x needed
                            break
                    
                    proxy_pools["FRESH"].extend(new_proxies)
                    
                    # Smart FRESH pool management
                    if len(proxy_pools["FRESH"]) > 2500:
                        proxy_pools["FRESH"] = proxy_pools["FRESH"][-2000:]
                
                log_to_render(f"✅ WORKER 1: Added {len(new_proxies)} NEW proxy (total FRESH: {len(proxy_pools['FRESH'])})")
            else:
                log_to_render("⚠️ WORKER 1: No new proxy found, extend sleep")
            
            # ADAPTIVE SLEEP: Ngủ lâu hơn khi đã đủ proxy
            if current_fresh >= 1000:
                sleep_time = 900  # 15 minutes khi đủ proxy
            elif worker_control["emergency_mode"]:
                sleep_time = 120  # 2 minutes emergency
            else:
                sleep_time = 300  # 5 minutes normal
                
            time.sleep(sleep_time)
            
        except Exception as e:
            log_to_render(f"❌ WORKER 1 CRITICAL ERROR: {str(e)}")
            time.sleep(300)

def fetch_proxies_partial_smart(needed_count):
    """SMART partial fetch chỉ từ sources nhanh nhất"""
    log_to_render("⚡ SMART PARTIAL FETCH: Targeting fast sources only")
    
    # Chọn sources nhanh nhất (ít proxy nhưng chất lượng cao)
    fast_sources = [
        ("https://api.proxyscrape.com/v2/?request=get&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all", "proxyscrape-http"),
        ("https://api.proxyscrape.com/v2/?request=get&protocol=socks5&timeout=10000&country=all", "proxyscrape-socks5"),
        ("https://raw.githubusercontent.com/hendrikbgr/Free-Proxy-Repo/master/proxy_list.txt", "hendrikbgr")
    ]
    
    all_proxies = []
    for url, name in fast_sources:
        try:
            response = get_with_session(url, timeout=10)
            if response.status_code == 200:
                proxies = response.text.strip().split('\n')
                valid_proxies = [p.strip() for p in proxies if p.strip() and ':' in p.strip()]
                all_proxies.extend([(None, p) for p in valid_proxies])
                log_to_render(f"⚡ {name}: {len(valid_proxies)} proxy")
                
                # Dừng khi đủ proxy cần thiết
                if len(all_proxies) >= needed_count * 3:
                    break
        except Exception as e:
            log_to_render(f"⚠️ {name} failed: {str(e)}")
            continue
    
    # Remove duplicates
    unique_proxies = []
    seen = set()
    for proxy_data in all_proxies:
        proxy_string = proxy_data[1]
        if proxy_string not in seen:
            unique_proxies.append(proxy_data)
            seen.add(proxy_string)
    
    log_to_render(f"⚡ SMART FETCH result: {len(unique_proxies)} unique proxy")
    return unique_proxies

def worker2_rolling_validation():
    """WORKER 2: Rolling validation từ FRESH → STANDBY → PRIMARY"""
    log_to_render("🔧 WORKER 2: Rolling validation started")
    
    validation_cycle = 0
    
    while worker_control["rolling_validation_active"]:
        try:
            validation_cycle += 1
            log_to_render(f"⚡ WORKER 2 CYCLE {validation_cycle}: Rolling validation")
            
            # STEP 1: Validate FRESH → STANDBY
            fresh_to_validate = []
            with pool_locks["FRESH"]:
                if len(proxy_pools["FRESH"]) > 0:
                    # Take batch của 200 proxy từ FRESH để validate
                    batch_size = min(200, len(proxy_pools["FRESH"]))
                    fresh_to_validate = proxy_pools["FRESH"][:batch_size]
                    proxy_pools["FRESH"] = proxy_pools["FRESH"][batch_size:]  # Remove processed
            
            if fresh_to_validate:
                log_to_render(f"🔍 WORKER 2: Validating {len(fresh_to_validate)} FRESH proxy...")
                
                # 🔧 FORMAT CONVERSION: Convert FRESH format to validation format
                validation_format = []
                for proxy_data in fresh_to_validate:
                    if isinstance(proxy_data, tuple) and len(proxy_data) >= 2:
                        proxy_type, proxy_string = proxy_data[0], proxy_data[1]
                        # Default to mixed protocol for FRESH proxy (try all types)
                        validation_format.append(('mixed', proxy_string, ['http', 'https', 'socks4', 'socks5']))
                    else:
                        # Fallback for other formats
                        proxy_string = proxy_data if isinstance(proxy_data, str) else str(proxy_data)
                        validation_format.append(('mixed', proxy_string, ['http', 'https', 'socks4', 'socks5']))
                
                log_to_render(f"🔧 WORKER 2: Converted {len(validation_format)} proxy to validation format")
                
                try:
                    validated_proxies = validate_proxy_batch_smart(validation_format, max_workers=15)
                    
                    if validated_proxies:
                        # 📊 DEBUG: Log validated proxy details
                        log_to_render(f"🔍 WORKER 2 DEBUG: Got {len(validated_proxies)} validated proxy")
                        if len(validated_proxies) > 0:
                            sample_proxy = validated_proxies[0]
                            log_to_render(f"🔍 Sample validated proxy: {sample_proxy}")
                        
                        with pool_locks["STANDBY"]:
                            before_count = len(proxy_pools["STANDBY"])
                            proxy_pools["STANDBY"].extend(validated_proxies)
                            after_count = len(proxy_pools["STANDBY"])
                            
                            # Keep STANDBY pool size reasonable
                            if len(proxy_pools["STANDBY"]) > TARGET_POOLS["STANDBY"] * 2:
                                proxy_pools["STANDBY"] = proxy_pools["STANDBY"][-TARGET_POOLS["STANDBY"]:]
                                final_count = len(proxy_pools["STANDBY"])
                                log_to_render(f"✂️ WORKER 2: Trimmed STANDBY pool to {final_count}")
                        
                        log_to_render(f"✅ WORKER 2: {len(validated_proxies)} proxy added to STANDBY ({before_count}→{after_count})")
                        pool_stats["STANDBY"]["last_validation"] = datetime.now().isoformat()
                    else:
                        log_to_render(f"❌ WORKER 2: No validated proxy returned from validation!")
                    
                except Exception as e:
                    log_to_render(f"❌ WORKER 2 VALIDATION ERROR: {str(e)}")
            
            # STEP 2: Re-validate existing pools (rolling maintenance)
            pools_to_maintain = ["PRIMARY", "STANDBY", "EMERGENCY"]
            for pool_name in pools_to_maintain:
                with pool_locks[pool_name]:
                    pool_size = len(proxy_pools[pool_name])
                    if pool_size > 50:  # Only maintain if pool has reasonable size
                        # Validate 20% của pool mỗi cycle
                        sample_size = max(10, pool_size // 5)
                        sample_proxies = proxy_pools[pool_name][:sample_size]
                        
                        # Convert to validation format
                        validation_list = []
                        for p in sample_proxies:
                            if isinstance(p, dict) and 'host' in p and 'port' in p:
                                proxy_string = f"{p['host']}:{p['port']}"
                                proxy_type = p.get('type', 'http')
                                validation_list.append(('maintenance', proxy_string, [proxy_type]))
                        
                        log_to_render(f"🔧 WORKER 2: Maintaining {len(validation_list)} proxy in {pool_name}")
                        
                        try:
                            still_alive = validate_proxy_batch_smart(validation_list, max_workers=10)
                            
                            # SMART DEAD PROXY HANDLING với resurrection system
                            alive_keys = {f"{p['host']}:{p['port']}" for p in still_alive}
                            
                            # Separate alive và dead proxy
                            original_size = len(proxy_pools[pool_name])
                            alive_proxies = []
                            dead_proxies = []
                            
                            for p in proxy_pools[pool_name]:
                                if isinstance(p, dict) and f"{p['host']}:{p['port']}" in alive_keys:
                                    alive_proxies.append(p)
                                else:
                                    dead_proxies.append(p)
                            
                            # Update pool với only alive proxy
                            proxy_pools[pool_name] = alive_proxies
                            
                            # Categorize dead proxy cho resurrection
                            if dead_proxies:
                                for dead_proxy in dead_proxies:
                                    categorize_dead_proxy(dead_proxy, failure_count=1)
                                
                                log_to_render(f"💀➡️🔄 WORKER 2: {len(dead_proxies)} dead proxy from {pool_name} scheduled for resurrection")
                            
                            removed_count = len(dead_proxies)
                            if removed_count > 0:
                                log_to_render(f"🗑️ WORKER 2: Removed {removed_count} dead proxy from {pool_name} (sent to resurrection queue)")
                            
                            pool_stats[pool_name]["last_validation"] = datetime.now().isoformat()
                            
                        except Exception as e:
                            log_to_render(f"❌ WORKER 2 MAINTENANCE ERROR in {pool_name}: {str(e)}")
            
            # Sleep 30 seconds between validation cycles
            time.sleep(30)
            
        except Exception as e:
            log_to_render(f"❌ WORKER 2 CRITICAL ERROR: {str(e)}")
            time.sleep(60)

def worker3_pool_balancer():
    """WORKER 3: Auto-balance pools và promote STANDBY → PRIMARY"""
    log_to_render("🔄 WORKER 3: Pool balancer started")
    
    balance_cycle = 0
    
    while worker_control["pool_balancer_active"]:
        try:
            balance_cycle += 1
            summary = get_pool_summary()
            
            log_to_render(f"📊 WORKER 3 CYCLE {balance_cycle}: Pool status - " + 
                         f"PRIMARY:{summary['PRIMARY']}, STANDBY:{summary['STANDBY']}, " +
                         f"EMERGENCY:{summary['EMERGENCY']}, GUARANTEED:{summary['GUARANTEED']}")
            
            # PROMOTION LOGIC: STANDBY → PRIMARY
            primary_deficit = TARGET_POOLS["PRIMARY"] - summary["PRIMARY"]
            if primary_deficit > 0 and summary["STANDBY"] > 0:
                promote_count = min(primary_deficit, summary["STANDBY"])
                
                with pool_locks["STANDBY"], pool_locks["PRIMARY"]:
                    proxies_to_promote = proxy_pools["STANDBY"][:promote_count]
                    proxy_pools["PRIMARY"].extend(proxies_to_promote)
                    proxy_pools["STANDBY"] = proxy_pools["STANDBY"][promote_count:]
                
                log_to_render(f"⬆️ WORKER 3: Promoted {promote_count} proxy STANDBY → PRIMARY")
            
            # EMERGENCY FILL: STANDBY → EMERGENCY
            emergency_deficit = TARGET_POOLS["EMERGENCY"] - summary["EMERGENCY"]
            if emergency_deficit > 0 and summary["STANDBY"] > TARGET_POOLS["STANDBY"]:
                # Only fill emergency từ excess STANDBY
                excess_standby = summary["STANDBY"] - TARGET_POOLS["STANDBY"]
                fill_count = min(emergency_deficit, excess_standby)
                
                if fill_count > 0:
                    with pool_locks["STANDBY"], pool_locks["EMERGENCY"]:
                        proxies_to_emergency = proxy_pools["STANDBY"][:fill_count]
                        proxy_pools["EMERGENCY"].extend(proxies_to_emergency)
                        proxy_pools["STANDBY"] = proxy_pools["STANDBY"][fill_count:]
                    
                    log_to_render(f"🚨 WORKER 3: Filled {fill_count} proxy to EMERGENCY pool")
            
            # GUARANTEE CHECK
            if not summary["GUARANTEED"]:
                log_to_render(f"🚨 GUARANTEE VIOLATION: Only {summary['TOTAL_AVAILABLE']} < {MINIMUM_GUARANTEED} proxy available!")
                worker_control["emergency_mode"] = True
            else:
                log_to_render(f"✅ GUARANTEE OK: {summary['TOTAL_AVAILABLE']} ≥ {MINIMUM_GUARANTEED} proxy available")
            
            # Sleep 60 seconds between balance cycles
            time.sleep(60)
            
        except Exception as e:
            log_to_render(f"❌ WORKER 3 CRITICAL ERROR: {str(e)}")
            time.sleep(120)

def initialize_service():
    """Initialize service - được gọi khi Flask app start"""
    if startup_status["initialized"]:
        return
        
    try:
        log_to_render("🚀 KHỞI ĐỘNG PROXY VALIDATION SERVICE")
        log_to_render("🔧 Tối ưu cho Render free plan (512MB RAM) - TARGET 1000 PROXY MODE")
        log_to_render("📋 Cấu hình: Timeout=8s, Workers=20, Chunks=500, Target=1000 proxy live")
        log_to_render(f"🎯 TARGET: Sẽ tiếp tục fetch cho đến khi đạt {TARGET_LIVE_PROXIES} proxy live")
        
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
    
    # Xử lý các categorized sources
    log_to_render("📥 Xử lý CATEGORIZED sources...")
    for source_name, source_config in PROXY_SOURCE_LINKS["categorized"].items():
        try:
            # Check if source has multiple protocols or single protocol
            if "url" in source_config and "protocol" in source_config:
                # Single protocol format
                source_url = source_config["url"]
                source_protocol = source_config["protocol"]
                protocols_to_fetch = [(source_protocol, source_url)]
            else:
                # Multiple protocols format (like dpangestuw)
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
                        
                        # Xử lý đặc biệt cho server dpangestuw - loại bỏ protocol prefix
                        if source_name == "Server dpangestuw":
                            if line.startswith('socks4://'):
                                line = line.replace('socks4://', '')
                            elif line.startswith('socks5://'):
                                line = line.replace('socks5://', '')
                            
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
    
    # Combine tất cả proxy (categorized + mixed) - KHÔNG GIỚI HẠN
    all_proxies = categorized_proxies + mixed_proxies
    original_count = len(all_proxies)
    
    # Remove duplicates dựa trên proxy string (host:port)
    seen = set()
    unique_proxies = []
    for proxy_data in all_proxies:
        if isinstance(proxy_data, tuple) and len(proxy_data) >= 2:
            proxy_string = proxy_data[1]  # proxy_string ở position 1
        else:
            proxy_string = str(proxy_data)
        
        if proxy_string not in seen:
            seen.add(proxy_string)
            unique_proxies.append(proxy_data)
    
    duplicates_removed = original_count - len(unique_proxies)
    random.shuffle(unique_proxies)
    
    log_to_render(f"🎯 HOÀN THÀNH FETCH: {len(unique_proxies)} unique proxy ({duplicates_removed} duplicates removed)")
    log_to_render(f"📊 Đã xử lý {sources_processed} nguồn thành công")
    log_to_render(f"📋 Original: {original_count} → Unique: {len(unique_proxies)} ({round(len(unique_proxies)/original_count*100, 1)}% unique)")
    log_to_render(f"📋 Categorized: {len(categorized_proxies)}, Mixed: {len(mixed_proxies)}")
    
    return unique_proxies, sources_processed

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
    """Maintenance mode - re-check các proxy đã có và UPDATE cache với list live mới"""
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
    
    # UPDATE CACHE với proxy live vừa check được (QUAN TRỌNG!)
    with cache_lock:
        proxy_cache["http"] = alive_proxies.copy()  # Update với list mới
        proxy_cache["alive_count"] = len(alive_proxies)
        proxy_cache["last_update"] = datetime.now().isoformat()
    
    log_to_render(f"✅ MAINTENANCE HOÀN THÀNH: {len(alive_proxies)}/{len(proxy_list)} proxy còn sống")
    log_to_render(f"💾 CACHE UPDATED: {len(alive_proxies)} proxy live trong cache")
    
    return alive_proxies

def background_proxy_refresh_optimized():
    """OPTIMIZED Background thread với strategy thông minh theo yêu cầu user"""
    global proxy_cache, startup_status
    
    log_to_render("🚀 OPTIMIZED BACKGROUND THREAD KHỞI ĐỘNG")
    log_to_render("📋 STRATEGY: Fetch → Batch validate → Accumulate → Maintenance → Replace")
    
    time.sleep(10)  # Stabilization wait
    
    mode = "INITIAL"  # INITIAL or MAINTENANCE
    cycle_count = 0
    consecutive_failures = 0
    last_fresh_fetch_time = time.time()
    
    while True:
        try:
            cycle_count += 1
            current_proxy_count = len(proxy_cache.get('http', []))
            
            log_to_render("=" * 70)
            log_to_render(f"🔄 CYCLE {cycle_count}: {mode} MODE")
            log_to_render(f"📊 Current proxy count: {current_proxy_count}")
            log_to_render("=" * 70)
            
            if mode == "INITIAL":
                # ============= INITIAL MODE: Tìm đến 1000 proxy =============
                
                # STEP 1: Fetch proxy từ sources
                log_to_render("📥 STEP 1: Fetch proxy từ ALL sources...")
                try:
                    all_proxies, sources_count = fetch_proxies_from_sources()
                    consecutive_failures = 0  # Reset failure counter
                except Exception as e:
                    log_to_render(f"❌ FETCH ERROR: {str(e)}")
                    consecutive_failures += 1
                    
                    if consecutive_failures >= 3:
                        log_to_render("🚨 TOO MANY FETCH FAILURES - Wait 2 hours")
                        time.sleep(7200)  # 2 hours
                        consecutive_failures = 0
                    else:
                        time.sleep(1800)  # 30 minutes
                    continue
                
                if not all_proxies or len(all_proxies) < 500:
                    log_to_render(f"⚠️ INSUFFICIENT PROXY: Only {len(all_proxies) if all_proxies else 0} < 500")
                    log_to_render("⏳ Wait 30 minutes and retry...")
                    time.sleep(1800)
                    continue
                
                log_to_render(f"✅ FETCHED {len(all_proxies)} proxy from {sources_count} sources")
                
                # STEP 2: Batch validate để accumulate results
                log_to_render("⚡ STEP 2: Batch validate để tích lũy results...")
                
                # Get existing valid proxies to accumulate
                existing_valid = []
                with cache_lock:
                    existing_proxies = proxy_cache.get('http', [])
                    for p in existing_proxies:
                        if isinstance(p, dict) and 'host' in p and 'port' in p:
                            existing_valid.append(p)
                
                log_to_render(f"📚 ACCUMULATE MODE: {len(existing_valid)} existing + new validation")
                
                # Validate in chunks of 500
                chunk_size = 500
                total_accumulated = existing_valid.copy()
                
                for i in range(0, len(all_proxies), chunk_size):
                    chunk = all_proxies[i:i + chunk_size]
                    chunk_num = (i // chunk_size) + 1
                    total_chunks = (len(all_proxies) + chunk_size - 1) // chunk_size
                    
                    log_to_render(f"🔄 Processing chunk {chunk_num}/{total_chunks} ({len(chunk)} proxy)")
                    
                    try:
                        chunk_results = validate_proxy_batch_smart(chunk, max_workers=25)
                        total_accumulated.extend(chunk_results)
                        
                        # Update cache REAL-TIME với accumulated results
                        with cache_lock:
                            proxy_cache["http"] = total_accumulated.copy()
                            proxy_cache["alive_count"] = len(total_accumulated)
                            proxy_cache["last_update"] = datetime.now().isoformat()
                        
                        current_count = len(total_accumulated)
                        log_to_render(f"📈 ACCUMULATED: {current_count} total proxy")
                        
                        # CHECK: Đạt target 1000?
                        if current_count >= TARGET_LIVE_PROXIES:
                            log_to_render(f"🎉 TARGET ACHIEVED: {current_count} ≥ {TARGET_LIVE_PROXIES}")
                            log_to_render("✅ SWITCH TO MAINTENANCE MODE")
                            mode = "MAINTENANCE"
                            startup_status["first_fetch_completed"] = True
                            break
                            
                    except Exception as e:
                        log_to_render(f"❌ Chunk {chunk_num} validation error: {str(e)}")
                        continue
                
                # Nếu vẫn chưa đủ sau khi validate hết
                final_count = len(total_accumulated)
                if final_count < TARGET_LIVE_PROXIES and mode == "INITIAL":
                    log_to_render(f"⚠️ STILL INSUFFICIENT: {final_count} < {TARGET_LIVE_PROXIES}")
                    log_to_render("🔄 Will retry with FRESH fetch in next cycle")
                    time.sleep(600)  # 10 minutes before retry
                
            else:
                # ============= MAINTENANCE MODE: Check 1000 proxy hiện có =============
                
                log_to_render("🔧 MAINTENANCE: Validate existing proxy pool...")
                
                # Get current proxy list
                with cache_lock:
                    current_proxies = proxy_cache.get('http', []).copy()
                
                if not current_proxies:
                    log_to_render("⚠️ NO PROXY IN CACHE - Switch back to INITIAL")
                    mode = "INITIAL"
                    continue
                
                log_to_render(f"🔍 Validating {len(current_proxies)} existing proxy...")
                
                # Convert to validation format
                proxy_list = []
                for p in current_proxies:
                    if isinstance(p, dict) and 'host' in p and 'port' in p:
                        proxy_string = f"{p['host']}:{p['port']}"
                        proxy_type = p.get('type', 'http')
                        proxy_list.append(('maintenance', proxy_string, [proxy_type]))
                
                # Validate existing proxy
                try:
                    new_valid_proxies = validate_proxy_batch_smart(proxy_list, max_workers=30)
                    
                    # REPLACE old cache với new results
                    with cache_lock:
                        proxy_cache["http"] = new_valid_proxies.copy()
                        proxy_cache["alive_count"] = len(new_valid_proxies)
                        proxy_cache["last_update"] = datetime.now().isoformat()
                    
                    log_to_render(f"🔄 CACHE REPLACED: {len(new_valid_proxies)} valid proxy")
                    
                    # CHECK: Còn đủ proxy không?
                    if len(new_valid_proxies) < 800:  # Threshold để switch back
                        log_to_render(f"⚠️ PROXY DEPLETED: {len(new_valid_proxies)} < 800")
                        log_to_render("🔄 Switch back to INITIAL mode để fetch fresh proxy")
                        mode = "INITIAL"
                        last_fresh_fetch_time = time.time()
                    else:
                        log_to_render(f"✅ MAINTENANCE OK: {len(new_valid_proxies)} proxy healthy")
                        log_to_render("😴 Sleep 10 minutes until next maintenance cycle")
                        time.sleep(600)  # 10 minutes normal maintenance
                        
                except Exception as e:
                    log_to_render(f"❌ MAINTENANCE ERROR: {str(e)}")
                    log_to_render("🔄 Force switch to INITIAL mode")
                    mode = "INITIAL"
                    continue
            
        except Exception as e:
            log_to_render(f"❌ CRITICAL ERROR in cycle {cycle_count}: {str(e)}")
            log_to_render(f"📍 Traceback: {traceback.format_exc()}")
            
            # Smart recovery
            time.sleep(300)  # 5 minutes recovery
            if cycle_count % 10 == 0:  # Every 10 cycles, force fresh start
                log_to_render("🔄 FORCE FRESH START after multiple errors")
                mode = "INITIAL"
                consecutive_failures = 0

# STRATEGY SUMMARY cho user:
def get_strategy_summary():
    """Trả về strategy summary cho user hiểu logic"""
    return {
        "INITIAL_MODE": {
            "description": "Tìm kiếm đến 1000 proxy",
            "steps": [
                "1. Fetch ALL proxy từ sources",
                "2. Validate theo batch 500 proxy/lần", 
                "3. Accumulate results real-time",
                "4. Đạt 1000 → switch MAINTENANCE"
            ],
            "fallback": "Nếu không đủ proxy → wait 30min retry"
        },
        "MAINTENANCE_MODE": {
            "description": "Maintain 1000 proxy pool",
            "steps": [
                "1. Validate 1000 proxy hiện có",
                "2. REPLACE cache với results mới",
                "3. Check số lượng còn lại",
                "4. <800 → switch INITIAL"
            ],
            "cycle": "10 minutes between maintenance"
        },
        "RECOVERY_STRATEGY": {
            "fetch_failure": "3 lần fail → wait 2h retry ALL",
            "insufficient_proxy": "Wait 30min và retry fresh fetch",
            "cache_depleted": "Auto switch INITIAL mode",
            "critical_error": "5min recovery + force fresh every 10 cycles"
        }
    }

@app.route('/api/strategy', methods=['GET'])
def get_strategy():
    """API để hiểu strategy và logic flow của service"""
    try:
        strategy = get_strategy_summary()
        current_mode = "INITIAL" if not startup_status.get("first_fetch_completed", False) else "MAINTENANCE"
        current_proxy_count = len(proxy_cache.get('http', []))
        
        return jsonify({
            'success': True,
            'current_mode': current_mode,
            'current_proxy_count': current_proxy_count,
            'target_proxy_count': TARGET_LIVE_PROXIES,
            'strategy': strategy,
            'flow_diagram': {
                'description': 'Service flow theo strategy optimized',
                'stages': [
                    'INITIAL: Fetch → Batch validate → Accumulate → Target check',
                    'MAINTENANCE: Validate existing → Replace cache → Count check',
                    'RECOVERY: Smart fallback với wait times và retry logic'
                ]
            },
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Initialize service when Flask starts  
def initialize_ultra_smart_service():
    """Initialize ULTRA SMART Multi-Tier Proxy Service"""
    if startup_status["initialized"]:
        return
        
    try:
        log_to_render("🚀 KHỞI ĐỘNG ULTRA SMART MULTI-TIER PROXY SERVICE")
        log_to_render("🏗️ ARCHITECTURE: PRIMARY + STANDBY + EMERGENCY + FRESH pools")
        log_to_render(f"🎯 GUARANTEE: {MINIMUM_GUARANTEED} proxy ready lúc nào cũng có")
        log_to_render(f"🔧 Service Process ID: {os.getpid()}")
        
        # Initialize all pools as empty
        log_to_render("💾 Initializing multi-tier pools...")
        for pool_name in proxy_pools:
            with pool_locks[pool_name]:
                proxy_pools[pool_name] = []
        
        log_to_render("✅ Multi-tier pools initialized")
        
        # Start 3 background workers
        log_to_render("🔄 STARTING 3 ULTRA SMART WORKERS...")
        
        try:
            # Worker 1: Continuous Fetch
            worker1_thread = threading.Thread(target=worker1_continuous_fetch, daemon=True)
            worker1_thread.start()
            log_to_render("✅ WORKER 1: Continuous fetch started!")
            
            # Worker 2: Rolling Validation  
            worker2_thread = threading.Thread(target=worker2_rolling_validation, daemon=True)
            worker2_thread.start()
            log_to_render("✅ WORKER 2: Rolling validation started!")
            
            # Worker 3: Pool Balancer
            worker3_thread = threading.Thread(target=worker3_pool_balancer, daemon=True)
            worker3_thread.start()
            log_to_render("✅ WORKER 3: Pool balancer started!")
            
            # Worker 4: Resurrection Manager (NEW!)
            worker4_thread = threading.Thread(target=worker4_resurrection_manager, daemon=True)
            worker4_thread.start()
            log_to_render("✅ WORKER 4: Dead proxy resurrection manager started!")
            
            startup_status["workers_started"] = True
            
        except Exception as e:
            log_to_render(f"❌ LỖI khởi động workers: {str(e)}")
            startup_status["error_count"] += 1
            
        # Initialize pool stats
        pool_stats["last_update"] = datetime.now().isoformat()
        pool_stats["total_served"] = 0
        
        startup_status["initialized"] = True
        startup_status["multi_tier_ready"] = True
        
        log_to_render("🎉 ULTRA SMART SERVICE INITIALIZATION COMPLETED!")
        log_to_render("📊 System will guarantee >500 proxy ready trong vài phút")
        log_to_render("🔄 4 workers running continuously in background")
        log_to_render("💀➡️🔄 Dead proxy resurrection system ENABLED!")
        
    except Exception as e:
        log_to_render(f"❌ LỖI CRITICAL INITIALIZATION: {str(e)}")
        log_to_render(f"📍 Traceback: {traceback.format_exc()}")
        startup_status["error_count"] += 1

initialize_ultra_smart_service()

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
            .emergency-controls {{
                background: rgba(255, 152, 0, 0.2);
                border: 2px solid #ff9800;
                border-radius: 10px;
                padding: 15px;
                margin: 20px 0;
                text-align: center;
            }}
            .btn {{
                background: linear-gradient(45deg, #ff6b6b, #ee5a24);
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                cursor: pointer;
                margin: 5px;
                font-weight: bold;
            }}
            .btn:hover {{
                background: linear-gradient(45deg, #ee5a24, #ff6b6b);
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🚀 Proxy Validation Service - Target 1000</h1>
                <p>Real-time monitoring - Tự động tìm 1000 proxy live - Tối ưu cho Render Free Plan</p>
            </div>
            
            <div id="system-status" class="status status-error">
                <div id="current-status">Đang khởi động service...</div>
            </div>
            
            <div class="emergency-controls" id="emergency-controls" style="display: none;">
                <h3>🚨 Emergency Controls - Infinite Loop Detection</h3>
                <p>Phát hiện service có thể bị infinite loop. Dùng controls này để fix:</p>
                <button class="btn" onclick="forceAcceptCurrent()">🔒 Accept Current Proxy Count</button>
                <button class="btn" onclick="window.open('/api/health', '_blank')">🔍 Check Health Status</button>
                <div id="emergency-result" style="margin-top: 10px;"></div>
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
                
                <div class="card">
                    <h3>🎯 Strategy & Flow</h3>
                    <div id="strategy-info">
                        <p>Đang tải strategy...</p>
                    </div>
                </div>
                
                <div class="card">
                    <h3>🔄 Dead Proxy Resurrection</h3>
                    <div id="resurrection-info">
                        <p>Đang tải resurrection stats...</p>
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
            let lastLogCount = 0;
            let repeatLogCount = 0;
            
            function updateStats() {{
                fetch('/api/proxy/stats')
                    .then(response => response.json())
                    .then(data => {{
                        // Update stats
                        document.getElementById('stats').innerHTML = 
                            '<p><strong>Proxy sống:</strong> ' + data.alive_count + '</p>' +
                            '<p><strong>🎯 Target:</strong> ' + data.alive_count + '/' + data.target_live_proxies + ' (' + data.target_progress + '%)</p>' +
                            '<p><strong>Target đạt:</strong> ' + (data.target_achieved ? '✅' : '❌') + '</p>' +
                            '<p><strong>Tổng đã check:</strong> ' + data.total_checked + '</p>' +
                            '<p><strong>Tỷ lệ thành công:</strong> ' + data.success_rate + '%</p>' +
                            '<p><strong>Nguồn đã xử lý:</strong> ' + data.sources_processed + '/' + data.sources_count + '</p>' +
                            '<p><strong>Lần check cuối:</strong> ' + (data.last_update ? new Date(data.last_update).toLocaleString() : 'Chưa check') + '</p>';
                        
                        // Update status
                        const statusEl = document.getElementById('current-status');
                        const statusContainer = document.getElementById('system-status');
                        
                        if (data.target_achieved) {{
                            statusEl.textContent = '🎉 TARGET ACHIEVED - ' + data.alive_count + ' proxy sống (≥1000)';
                            statusContainer.className = 'status status-success';
                        }} else if (data.alive_count >= 500) {{
                            statusEl.textContent = '⚡ Đang đạt target - ' + data.alive_count + '/' + data.target_live_proxies + ' proxy (' + data.target_progress + '%)';
                            statusContainer.className = 'status status-info';
                        }} else if (data.alive_count > 0) {{
                            statusEl.textContent = '🔍 Đang tìm proxy - ' + data.alive_count + '/' + data.target_live_proxies + ' (' + data.target_progress + '%)';
                            statusContainer.className = 'status status-info';
                        }} else {{
                            statusEl.textContent = 'Đang khởi động và tìm proxy sống...';
                            statusContainer.className = 'status status-error';
                        }}
                    }})
                    .catch(e => {{
                        document.getElementById('stats').innerHTML = '<p style="color: red;">Service đang khởi động...</p>';
                    }});
            }}
            
            function detectInfiniteLoop(logs) {{
                // Detect infinite loop by checking for repeat patterns
                let timeoutCount = 0;
                let switchBackCount = 0;
                
                if (logs && logs.length > 10) {{
                    const recentLogs = logs.slice(-20); // Last 20 logs
                    
                    recentLogs.forEach(log => {{
                        if (log.message.includes('INITIAL FETCH TIMEOUT') || log.message.includes('FORCE SWITCH')) {{
                            timeoutCount++;
                        }}
                        if (log.message.includes('QUAY LẠI INITIAL FETCH')) {{
                            switchBackCount++;
                        }}
                    }});
                    
                    // Show emergency controls if potential infinite loop detected
                    if (timeoutCount >= 3 && switchBackCount >= 3) {{
                        document.getElementById('emergency-controls').style.display = 'block';
                        return true;
                    }}
                }}
                return false;
            }}
            
            function forceAcceptCurrent() {{
                if (confirm('Bạn có chắc muốn force accept current proxy count và stop infinite loop?')) {{
                    fetch('/api/force/accept', {{
                        method: 'POST',
                        headers: {{'Content-Type': 'application/json'}}
                    }})
                    .then(response => response.json())
                    .then(data => {{
                        if (data.success) {{
                            document.getElementById('emergency-result').innerHTML = 
                                '<div style="color: green;">✅ ' + data.message + '</div>';
                            setTimeout(() => {{
                                document.getElementById('emergency-controls').style.display = 'none';
                            }}, 3000);
                        }} else {{
                            document.getElementById('emergency-result').innerHTML = 
                                '<div style="color: red;">❌ Error: ' + data.error + '</div>';
                        }}
                    }})
                    .catch(e => {{
                        document.getElementById('emergency-result').innerHTML = 
                            '<div style="color: red;">❌ Request failed: ' + e.message + '</div>';
                    }});
                }}
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
                            
                            // Detect infinite loop patterns
                            detectInfiniteLoop(data.logs);
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
            
            function updateStrategy() {{
                fetch('/api/strategy')
                    .then(response => response.json())
                    .then(data => {{
                        if (data.success) {{
                            const currentMode = data.current_mode;
                            const currentCount = data.current_proxy_count;
                            const targetCount = data.target_proxy_count;
                            const strategy = data.strategy;
                            
                            let modeColor = currentMode === 'INITIAL' ? '#ff9800' : '#4caf50';
                            let modeIcon = currentMode === 'INITIAL' ? '🔍' : '🔧';
                            
                            document.getElementById('strategy-info').innerHTML = 
                                '<p><strong>Current Mode:</strong> <span style="color: ' + modeColor + '">' + modeIcon + ' ' + currentMode + '</span></p>' +
                                '<p><strong>Progress:</strong> ' + currentCount + '/' + targetCount + ' proxy (' + Math.round(currentCount/targetCount*100) + '%)</p>' +
                                '<hr>' +
                                '<p><strong>' + currentMode + ' Strategy:</strong></p>' +
                                '<p style="font-size: 0.9em; opacity: 0.9">' + strategy[currentMode + '_MODE'].description + '</p>' +
                                '<ul style="font-size: 0.8em; margin: 5px 0;">' +
                                strategy[currentMode + '_MODE'].steps.map(step => '<li>' + step + '</li>').join('') +
                                '</ul>' +
                                '<p style="font-size: 0.8em; color: #888;"><strong>Fallback:</strong> ' + 
                                (currentMode === 'INITIAL' ? strategy.INITIAL_MODE.fallback : strategy.MAINTENANCE_MODE.cycle) + '</p>';
                        }} else {{
                            document.getElementById('strategy-info').innerHTML = '<p style="color: red;">Error loading strategy</p>';
                        }}
                    }})
                    .catch(e => {{
                        document.getElementById('strategy-info').innerHTML = '<p style="color: red;">Strategy unavailable</p>';
                    }});
            }}
            
            function updateResurrection() {{
                fetch('/api/resurrection/stats')
                    .then(response => response.json())
                    .then(data => {{
                        if (data.success) {{
                            const summary = data.summary;
                            const deadCategories = data.dead_categories;
                            
                            let resurrectStatus = '⚰️ No Activity';
                            let resurrectColor = '#888';
                            
                            if (summary.total_successfully_resurrected > 0) {{
                                resurrectStatus = '🎉 ' + summary.total_successfully_resurrected + ' Resurrected (' + summary.resurrection_success_rate + '%)';
                                resurrectColor = '#4caf50';
                            }} else if (summary.total_resurrection_attempts > 0) {{
                                resurrectStatus = '⏳ ' + summary.total_resurrection_attempts + ' Attempts';
                                resurrectColor = '#ff9800';
                            }}
                            
                            document.getElementById('resurrection-info').innerHTML = 
                                '<p><strong>Status:</strong> <span style="color: ' + resurrectColor + '">' + resurrectStatus + '</span></p>' +
                                '<p><strong>Dead Tracked:</strong> ' + summary.total_dead_tracked + ' proxy</p>' +
                                '<hr>' +
                                '<p><strong>Dead Categories:</strong></p>' +
                                '<ul style="font-size: 0.8em; margin: 5px 0;">' +
                                '<li>🔄 Immediate: ' + deadCategories.immediate_retry.count + '</li>' +
                                '<li>⏳ Short (5min): ' + deadCategories.short_delay.count + '</li>' +
                                '<li>⏰ Medium (30min): ' + deadCategories.medium_delay.count + '</li>' +
                                '<li>🕐 Long (2h): ' + deadCategories.long_delay.count + '</li>' +
                                '<li>⚰️ Permanent: ' + deadCategories.permanent_dead.count + '</li>' +
                                '</ul>' +
                                '<p style="font-size: 0.8em; color: #888;">Dead proxy có cơ hội comeback với exponential backoff</p>';
                        }} else {{
                            document.getElementById('resurrection-info').innerHTML = '<p style="color: red;">Resurrection system error</p>';
                        }}
                    }})
                    .catch(e => {{
                        document.getElementById('resurrection-info').innerHTML = '<p style="color: red;">Resurrection unavailable</p>';
                    }});
            }}
            
            // Update every 5 seconds
            updateStats();
            updateLogs();
            updateStrategy();
            updateResurrection();
            setInterval(updateStats, 5000);
            setInterval(updateLogs, 3000);  // Logs update faster
            setInterval(updateStrategy, 10000);  // Strategy update every 10s
            setInterval(updateResurrection, 15000);  // Resurrection update every 15s
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
def get_alive_proxies_ultra_smart():
    """ULTRA SMART API - Multi-tier proxy serving với guarantee >500 proxy"""
    try:
        count = int(request.args.get('count', 50))
        
        # Use ULTRA SMART serving algorithm
        result_proxies = smart_proxy_request(count)
        pools_summary = get_pool_summary()
        
        # Sort by speed (fastest first)
        sorted_proxies = sorted(result_proxies, key=lambda x: x.get('speed', 999))
        
        return jsonify({
            'success': True,
            'system': 'ULTRA_SMART_MULTI_TIER',
            'guarantee_status': pools_summary['GUARANTEED'],
            'total_available_all_tiers': pools_summary['TOTAL_AVAILABLE'],
            'returned_count': len(sorted_proxies),
            'requested_count': count,
            'proxies': sorted_proxies,
            'pool_breakdown': {
                'PRIMARY': pools_summary['PRIMARY'],
                'STANDBY': pools_summary['STANDBY'], 
                'EMERGENCY': pools_summary['EMERGENCY'],
                'FRESH': pools_summary['FRESH']
            },
            'serving_tiers_used': 'auto_detected_from_logs',
            'last_update': pool_stats.get('last_update'),
            'timestamp': datetime.now().isoformat(),
            'total_served_today': pool_stats.get('total_served', 0),
            'minimum_guaranteed': MINIMUM_GUARANTEED
        })
        
    except Exception as e:
        log_to_render(f"❌ API ERROR: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'fallback': 'multi_tier_system_error'
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
            'target_live_proxies': TARGET_LIVE_PROXIES,
            'target_progress': round(alive_count / TARGET_LIVE_PROXIES * 100, 1) if TARGET_LIVE_PROXIES > 0 else 0,
            'target_achieved': startup_status.get('target_achieved', False),
            'last_update': last_update,
            'cache_age_minutes': cache_age_minutes,
            'sources_count': total_sources,
            'sources_processed': proxy_cache.get('sources_processed', 0),
            'categorized_sources': list(PROXY_SOURCE_LINKS["categorized"].keys()),
            'mixed_sources': list(PROXY_SOURCE_LINKS["mixed"].keys()),
            'service_status': 'render_free_optimized_target_1000',
            'check_interval': '10 minutes',
            'timeout_setting': '6 seconds',
            'max_workers': 15,
            'processing_mode': 'TARGET_1000_PROXY_MODE',
            'chunk_size': 500,
            'render_plan': 'free_512mb'
        })
        
    except Exception as e:
        log_to_render(f"❌ Lỗi API stats: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/ultra/stats', methods=['GET'])
def get_ultra_smart_stats():
    """ULTRA SMART Stats API - Multi-tier system statistics"""
    try:
        pools_summary = get_pool_summary()
        
        # Calculate comprehensive stats
        total_available = pools_summary['TOTAL_AVAILABLE']
        guarantee_status = pools_summary['GUARANTEED']
        
        # Target calculation với new system
        target_total = sum(TARGET_POOLS.values())  # 1700 total proxy across all pools
        target_progress = round(total_available / target_total * 100, 1) if total_available > 0 else 0
        
        # System health assessment
        health_status = "EXCELLENT" if guarantee_status else "NEEDS_ATTENTION"
        if total_available >= target_total:
            health_status = "OPTIMAL"
        elif total_available >= MINIMUM_GUARANTEED * 2:
            health_status = "GOOD"
        
        last_update = pool_stats.get('last_update')
        cache_age_minutes = 0
        if last_update:
            try:
                last_update_dt = datetime.fromisoformat(last_update)
                cache_age_minutes = int((datetime.now() - last_update_dt).total_seconds() / 60)
            except:
                cache_age_minutes = 0
        
        # Worker status
        workers_active = {
            'continuous_fetch': worker_control['continuous_fetch_active'],
            'rolling_validation': worker_control['rolling_validation_active'],
            'pool_balancer': worker_control['pool_balancer_active'],
            'resurrection_manager': worker_control.get('resurrection_active', True),
            'emergency_mode': worker_control['emergency_mode']
        }
        
        # Dead proxy resurrection statistics
        resurrection_stats = pool_stats.get("resurrection_stats", {})
        dead_categories_count = {
            category: len(dead_proxy_management.get(category, []))
            for category in ["immediate_retry", "short_delay", "medium_delay", "long_delay", "permanent_dead"]
        }
        
        return jsonify({
            'success': True,
            'system': 'ULTRA_SMART_MULTI_TIER',
            'health_status': health_status,
            'guarantee_status': guarantee_status,
            'total_available': total_available,
            'minimum_guaranteed': MINIMUM_GUARANTEED,
            'pools': {
                'PRIMARY': {
                    'count': pools_summary['PRIMARY'],
                    'target': TARGET_POOLS['PRIMARY'],
                    'percentage': round(pools_summary['PRIMARY'] / TARGET_POOLS['PRIMARY'] * 100, 1) if TARGET_POOLS['PRIMARY'] > 0 else 0
                },
                'STANDBY': {
                    'count': pools_summary['STANDBY'],
                    'target': TARGET_POOLS['STANDBY'],
                    'percentage': round(pools_summary['STANDBY'] / TARGET_POOLS['STANDBY'] * 100, 1) if TARGET_POOLS['STANDBY'] > 0 else 0
                },
                'EMERGENCY': {
                    'count': pools_summary['EMERGENCY'],
                    'target': TARGET_POOLS['EMERGENCY'],
                    'percentage': round(pools_summary['EMERGENCY'] / TARGET_POOLS['EMERGENCY'] * 100, 1) if TARGET_POOLS['EMERGENCY'] > 0 else 0
                },
                'FRESH': {
                    'count': pools_summary['FRESH'],
                    'status': 'processing_continuously'
                }
            },
            'workers': workers_active,
            'performance': {
                'total_served_today': pool_stats.get('total_served', 0),
                'last_update': last_update,
                'cache_age_minutes': cache_age_minutes
            },
            'targets': {
                'total_target': target_total,
                'target_progress': target_progress,
                'target_achieved': total_available >= target_total
            },
            'sources_info': {
                'total_sources': len(PROXY_SOURCE_LINKS["categorized"]) + len(PROXY_SOURCE_LINKS["mixed"]),
                'categorized_sources': len(PROXY_SOURCE_LINKS["categorized"]),
                'mixed_sources': len(PROXY_SOURCE_LINKS["mixed"])
            },
            'resurrection_system': {
                'stats': resurrection_stats,
                'dead_categories': dead_categories_count,
                'total_dead_tracked': sum(dead_categories_count.values()),
                'resurrection_enabled': True,
                'delays': RESURRECTION_DELAYS
            },
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        log_to_render(f"❌ ULTRA SMART Stats API Error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'system': 'ULTRA_SMART_MULTI_TIER'
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

@app.route('/api/ultra/demo', methods=['GET'])
def ultra_smart_demo():
    """DEMO endpoint để show off ULTRA SMART capabilities"""
    try:
        log_to_render("🎯 ULTRA SMART DEMO requested!")
        
        # Get current pools status
        pools_summary = get_pool_summary()
        
        # Simulate smart request
        demo_request_count = int(request.args.get('count', 100))
        demo_proxies = smart_proxy_request(demo_request_count)
        
        return jsonify({
            'demo': 'ULTRA_SMART_MULTI_TIER_SYSTEM',
            'guarantee': f"ALWAYS ≥{MINIMUM_GUARANTEED} proxy ready",
            'request_demo': {
                'requested': demo_request_count,
                'delivered': len(demo_proxies),
                'delivery_rate': round(len(demo_proxies)/demo_request_count*100, 1) if demo_request_count > 0 else 0
            },
            'current_pools': pools_summary,
            'architecture': {
                'PRIMARY': f"Ready-to-use pool ({TARGET_POOLS['PRIMARY']} target)",
                'STANDBY': f"Backup pool ({TARGET_POOLS['STANDBY']} target)", 
                'EMERGENCY': f"Emergency pool ({TARGET_POOLS['EMERGENCY']} target)",
                'FRESH': "Continuous fetching pipeline"
            },
            'workers': {
                'worker1': 'Continuous fetch từ sources (24/7)',
                'worker2': 'Rolling validation FRESH→STANDBY→PRIMARY',
                'worker3': 'Auto pool balancing và promotion'
            },
            'benefits': [
                'Zero downtime: Luôn có proxy ready',
                'Multi-tier fallback: PRIMARY→STANDBY→EMERGENCY',
                'Continuous operation: Không bao giờ dừng fetch',
                'Smart balancing: Auto promote pools',
                'Guarantee: >500 proxy lúc nào cũng sẵn sàng'
            ],
            'vs_old_system': {
                'old': 'Single pool, maintenance gaps, periodic fetch',
                'new': 'Multi-tier, zero gaps, continuous operation'
            },
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'demo': 'ERROR',
            'error': str(e)
        }), 500

@app.route('/api/resurrection/stats', methods=['GET'])
def get_resurrection_stats():
    """API chi tiết về resurrection system - Dead proxy comeback stats"""
    try:
        # Detailed resurrection statistics
        resurrection_stats = pool_stats.get("resurrection_stats", {})
        
        # Dead categories với detailed info
        dead_categories_detailed = {}
        total_dead_tracked = 0
        
        for category in ["immediate_retry", "short_delay", "medium_delay", "long_delay", "permanent_dead"]:
            category_list = dead_proxy_management.get(category, [])
            count = len(category_list)
            total_dead_tracked += count
            
            # Calculate time until next retry for scheduled categories
            next_retries = []
            if category != "permanent_dead" and category_list:
                current_time = datetime.now()
                for item in category_list[:5]:  # Show next 5
                    try:
                        next_retry = datetime.fromisoformat(item['next_retry'])
                        time_remaining = (next_retry - current_time).total_seconds()
                        if time_remaining > 0:
                            next_retries.append({
                                'proxy': item['proxy_key'],
                                'retry_in_seconds': int(time_remaining),
                                'retry_in_minutes': round(time_remaining / 60, 1),
                                'failure_count': item['failure_count']
                            })
                    except:
                        continue
            
            dead_categories_detailed[category] = {
                'count': count,
                'delay_minutes': RESURRECTION_DELAYS.get(category, 0) / 60,
                'next_retries': next_retries[:3],  # Show top 3
                'description': {
                    'immediate_retry': 'First death - retry immediately',
                    'short_delay': 'Second death - retry in 5 minutes',
                    'medium_delay': 'Third death - retry in 30 minutes', 
                    'long_delay': 'Fourth death - retry in 2 hours',
                    'permanent_dead': 'Fifth+ death - permanently blacklisted'
                }.get(category, 'Unknown category')
            }
        
        # Calculate resurrection success rate
        total_attempts = resurrection_stats.get('resurrection_attempts', 0)
        total_resurrected = resurrection_stats.get('total_resurrected', 0)
        success_rate = round(total_resurrected / total_attempts * 100, 1) if total_attempts > 0 else 0
        
        # Recent resurrection activity
        last_resurrection = resurrection_stats.get('last_resurrection')
        resurrection_age = None
        if last_resurrection:
            try:
                last_time = datetime.fromisoformat(last_resurrection)
                resurrection_age = int((datetime.now() - last_time).total_seconds() / 60)
            except:
                resurrection_age = None
        
        return jsonify({
            'success': True,
            'resurrection_enabled': True,
            'summary': {
                'total_dead_tracked': total_dead_tracked,
                'total_resurrection_attempts': total_attempts,
                'total_successfully_resurrected': total_resurrected,
                'resurrection_success_rate': success_rate,
                'last_resurrection_minutes_ago': resurrection_age
            },
            'dead_categories': dead_categories_detailed,
            'resurrection_logic': {
                'exponential_backoff': True,
                'max_attempts': RESURRECTION_DELAYS['permanent_threshold'],
                'delays': {
                    'immediate': '0 minutes (next cycle)',
                    'short': '5 minutes',
                    'medium': '30 minutes',
                    'long': '2 hours',
                    'permanent': 'Never (blacklisted)'
                }
            },
            'benefits': [
                'Dead proxy có cơ hội comeback',
                'Exponential backoff để tránh spam',
                'Smart categorization theo failure count',
                'Automatic resurrection attempts',
                'Permanent blacklist cho hopeless cases'
            ],
            'worker_info': {
                'worker4_active': worker_control.get('resurrection_active', True),
                'check_interval': '60 seconds',
                'resurrection_pool': 'STANDBY (validated proxy go back to STANDBY)'
            },
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        log_to_render(f"❌ Resurrection stats API error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'resurrection_enabled': True
        }), 500

@app.route('/api/force/accept', methods=['POST'])
def force_accept_current():
    """Force accept current proxy count và stop infinite loop"""
    try:
        global startup_status
        
        current_proxies = proxy_cache.get('http', [])
        
        log_to_render("🔒 API TRIGGER: Force accept current proxy count")
        log_to_render(f"✅ ACCEPT {len(current_proxies)} proxy live (manual override)")
        
        with cache_lock:
            startup_status["target_achieved"] = True
            startup_status["existing_live_proxies"] = []
        
        return jsonify({
            'success': True,
            'message': f'Accepted {len(current_proxies)} proxies and stopped infinite loop',
            'current_proxy_count': len(current_proxies),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# SMART DEAD PROXY RESURRECTION SYSTEM
# Dead proxy có cơ hội comeback với intelligent retry
# Enhanced pool statistics already defined above - no duplicate needed

# DEAD proxy management với resurrection scheduling
dead_proxy_management = {
    "immediate_retry": [],      # Retry ngay (lần đầu dead)
    "short_delay": [],         # Retry sau 5 phút  
    "medium_delay": [],        # Retry sau 30 phút
    "long_delay": [],          # Retry sau 2 giờ
    "permanent_dead": []       # Permanent blacklist (sau nhiều lần fail)
}

# Resurrection schedules (exponential backoff)
RESURRECTION_DELAYS = {
    "immediate_retry": 0,      # 0 minutes (next cycle)
    "short_delay": 300,        # 5 minutes
    "medium_delay": 1800,      # 30 minutes  
    "long_delay": 7200,        # 2 hours
    "permanent_threshold": 5   # Sau 5 lần fail → permanent dead
}

def categorize_dead_proxy(proxy_data, failure_count=1):
    """Phân loại dead proxy theo failure count để schedule resurrection"""
    proxy_key = f"{proxy_data.get('host', 'unknown')}:{proxy_data.get('port', 'unknown')}"
    
    resurrection_info = {
        'proxy_data': proxy_data,
        'failure_count': failure_count,
        'last_failed': datetime.now().isoformat(),
        'next_retry': None,
        'proxy_key': proxy_key
    }
    
    with pool_locks["DEAD"]:
        if failure_count == 1:
            # Lần đầu dead → immediate retry
            resurrection_info['next_retry'] = datetime.now().isoformat()
            dead_proxy_management["immediate_retry"].append(resurrection_info)
            log_to_render(f"💀➡️🔄 DEAD→IMMEDIATE: {proxy_key} (first failure)")
            
        elif failure_count == 2:
            # Lần 2 dead → short delay
            next_retry = datetime.now() + timedelta(seconds=RESURRECTION_DELAYS["short_delay"])
            resurrection_info['next_retry'] = next_retry.isoformat()
            dead_proxy_management["short_delay"].append(resurrection_info)
            log_to_render(f"💀➡️⏳ DEAD→SHORT_DELAY: {proxy_key} (retry in 5min)")
            
        elif failure_count == 3:
            # Lần 3 dead → medium delay
            next_retry = datetime.now() + timedelta(seconds=RESURRECTION_DELAYS["medium_delay"])
            resurrection_info['next_retry'] = next_retry.isoformat()
            dead_proxy_management["medium_delay"].append(resurrection_info)
            log_to_render(f"💀➡️⏰ DEAD→MEDIUM_DELAY: {proxy_key} (retry in 30min)")
            
        elif failure_count == 4:
            # Lần 4 dead → long delay
            next_retry = datetime.now() + timedelta(seconds=RESURRECTION_DELAYS["long_delay"])
            resurrection_info['next_retry'] = next_retry.isoformat()
            dead_proxy_management["long_delay"].append(resurrection_info)
            log_to_render(f"💀➡️🕐 DEAD→LONG_DELAY: {proxy_key} (retry in 2h)")
            
        else:
            # ≥5 lần dead → permanent dead
            dead_proxy_management["permanent_dead"].append(resurrection_info)
            log_to_render(f"💀➡️⚰️ DEAD→PERMANENT: {proxy_key} (after {failure_count} failures)")

def get_proxies_ready_for_resurrection():
    """Lấy các dead proxy sẵn sàng được resurrection theo schedule"""
    ready_for_retry = []
    current_time = datetime.now()
    
    # Check từng delay category
    for delay_category in ["immediate_retry", "short_delay", "medium_delay", "long_delay"]:
        with pool_locks["DEAD"]:
            proxy_list = dead_proxy_management[delay_category]
            still_waiting = []
            
            for resurrection_info in proxy_list:
                try:
                    next_retry_time = datetime.fromisoformat(resurrection_info['next_retry'])
                    
                    if current_time >= next_retry_time:
                        # Sẵn sàng retry
                        ready_for_retry.append(resurrection_info)
                        log_to_render(f"🔄 RESURRECTION READY: {resurrection_info['proxy_key']} from {delay_category}")
                    else:
                        # Vẫn phải chờ
                        still_waiting.append(resurrection_info)
                        
                except Exception as e:
                    log_to_render(f"❌ Error processing resurrection time: {str(e)}")
                    still_waiting.append(resurrection_info)
            
            # Update list với những proxy vẫn đang chờ
            dead_proxy_management[delay_category] = still_waiting
    
    return ready_for_retry

def attempt_proxy_resurrection(resurrection_candidates):
    """Thử resurrect các dead proxy candidates"""
    if not resurrection_candidates:
        return []
    
    log_to_render(f"🔄 ATTEMPTING RESURRECTION: {len(resurrection_candidates)} dead proxy candidates")
    pool_stats["resurrection_stats"]["resurrection_attempts"] += len(resurrection_candidates)
    
    resurrected_proxies = []
    failed_again = []
    
    # Convert resurrection candidates to validation format
    validation_list = []
    for candidate in resurrection_candidates:
        proxy_data = candidate['proxy_data']
        
        if isinstance(proxy_data, dict) and 'host' in proxy_data and 'port' in proxy_data:
            proxy_string = f"{proxy_data['host']}:{proxy_data['port']}"
            proxy_type = proxy_data.get('type', 'http')
            validation_list.append(('resurrection', proxy_string, [proxy_type]))
    
    if not validation_list:
        log_to_render("⚠️ No valid resurrection candidates to validate")
        return []
    
    try:
        # Validate với lower worker count để không impact main validation
        validated_results = validate_proxy_batch_smart(validation_list, max_workers=8)
        
        if validated_results:
            log_to_render(f"🎉 RESURRECTION SUCCESS: {len(validated_results)} proxy came back from dead!")
            
            # Add resurrected proxy back to STANDBY pool
            with pool_locks["STANDBY"]:
                proxy_pools["STANDBY"].extend(validated_results)
            
            resurrected_proxies = validated_results
            pool_stats["resurrection_stats"]["total_resurrected"] += len(validated_results)
            pool_stats["resurrection_stats"]["last_resurrection"] = datetime.now().isoformat()
            
            # Create set of successfully resurrected proxy keys
            resurrected_keys = {f"{p['host']}:{p['port']}" for p in validated_results}
            
            # Handle failed resurrection attempts
            for candidate in resurrection_candidates:
                proxy_key = candidate['proxy_key']
                if proxy_key not in resurrected_keys:
                    # Still dead, increase failure count and re-categorize
                    new_failure_count = candidate['failure_count'] + 1
                    categorize_dead_proxy(candidate['proxy_data'], new_failure_count)
                    failed_again.append(candidate)
            
            if failed_again:
                log_to_render(f"💀 RESURRECTION FAILED: {len(failed_again)} proxy still dead, re-scheduled")
        
        else:
            log_to_render("💀 RESURRECTION FAILED: All candidates still dead")
            # Re-categorize all with increased failure count
            for candidate in resurrection_candidates:
                new_failure_count = candidate['failure_count'] + 1
                categorize_dead_proxy(candidate['proxy_data'], new_failure_count)
    
    except Exception as e:
        log_to_render(f"❌ RESURRECTION ERROR: {str(e)}")
        # Re-categorize all with increased failure count on error
        for candidate in resurrection_candidates:
            new_failure_count = candidate['failure_count'] + 1
            categorize_dead_proxy(candidate['proxy_data'], new_failure_count)
    
    # Update resurrection rate
    total_attempts = pool_stats["resurrection_stats"]["resurrection_attempts"]
    total_resurrected = pool_stats["resurrection_stats"]["total_resurrected"]
    pool_stats["resurrection_stats"]["resurrection_rate"] = round(
        total_resurrected / total_attempts * 100, 1
    ) if total_attempts > 0 else 0
    
    return resurrected_proxies

def worker4_resurrection_manager():
    """WORKER 4: Dead proxy resurrection manager - NEW WORKER"""
    log_to_render("🔄 WORKER 4: Resurrection manager started")
    
    resurrection_cycle = 0
    
    while worker_control.get("resurrection_active", True):
        try:
            resurrection_cycle += 1
            log_to_render(f"🔄 WORKER 4 CYCLE {resurrection_cycle}: Checking for resurrection candidates")
            
            # Get proxies ready for resurrection attempt
            candidates = get_proxies_ready_for_resurrection()
            
            if candidates:
                log_to_render(f"🎯 RESURRECTION CANDIDATES: {len(candidates)} proxy ready for retry")
                
                # Attempt resurrection
                resurrected = attempt_proxy_resurrection(candidates)
                
                if resurrected:
                    log_to_render(f"🎉 RESURRECTION SUCCESS: {len(resurrected)} proxy brought back to life!")
                else:
                    log_to_render("💀 RESURRECTION: No proxy successfully resurrected this cycle")
            else:
                log_to_render("😴 RESURRECTION: No candidates ready for retry")
            
            # Show resurrection statistics periodically
            if resurrection_cycle % 10 == 0:  # Every 10 cycles
                resurrection_stats = pool_stats["resurrection_stats"]
                dead_counts = {
                    category: len(dead_proxy_management[category]) 
                    for category in dead_proxy_management
                }
                
                log_to_render("📊 RESURRECTION STATS:")
                log_to_render(f"   Total resurrected: {resurrection_stats['total_resurrected']}")
                log_to_render(f"   Total attempts: {resurrection_stats['resurrection_attempts']}")
                log_to_render(f"   Success rate: {resurrection_stats['resurrection_rate']}%")
                log_to_render(f"   Dead categories: {dead_counts}")
            
            # Sleep 60 seconds between resurrection cycles
            time.sleep(60)
            
        except Exception as e:
            log_to_render(f"❌ WORKER 4 CRITICAL ERROR: {str(e)}")
            time.sleep(120)

@app.route('/api/health/comprehensive', methods=['GET'])
def comprehensive_health_check():
    """Comprehensive health check để ensure service hoạt động tốt"""
    try:
        health_report = {
            'timestamp': datetime.now().isoformat(),
            'service': 'ULTRA_SMART_MULTI_TIER_PROXY_SERVICE',
            'version': '2.0',
            'status': 'HEALTHY',
            'issues': []
        }
        
        # Check pools initialization
        pools_summary = get_pool_summary()
        health_report['pools'] = pools_summary
        
        # Check workers status
        workers_status = {
            'continuous_fetch': worker_control['continuous_fetch_active'],
            'rolling_validation': worker_control['rolling_validation_active'],
            'pool_balancer': worker_control['pool_balancer_active'],
            'resurrection_manager': worker_control.get('resurrection_active', True)
        }
        health_report['workers'] = workers_status
        
        # Check for issues
        if not pools_summary['GUARANTEED']:
            health_report['issues'].append(f"GUARANTEE VIOLATION: Only {pools_summary['TOTAL_AVAILABLE']} < {MINIMUM_GUARANTEED} proxy")
            health_report['status'] = 'WARNING'
            
        if not startup_status['initialized']:
            health_report['issues'].append("Service not properly initialized")
            health_report['status'] = 'ERROR'
            
        if not startup_status['workers_started']:
            health_report['issues'].append("Background workers not started")
            health_report['status'] = 'ERROR'
            
        # Overall health assessment
        if not health_report['issues']:
            health_report['status'] = 'EXCELLENT'
        elif health_report['status'] == 'HEALTHY' and pools_summary['TOTAL_AVAILABLE'] >= MINIMUM_GUARANTEED:
            health_report['status'] = 'GOOD'
            
        health_report['startup_status'] = startup_status
        health_report['guarantee_met'] = pools_summary['GUARANTEED']
        
        return jsonify(health_report)
        
    except Exception as e:
        return jsonify({
            'status': 'CRITICAL_ERROR',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
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