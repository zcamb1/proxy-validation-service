#!/usr/bin/env python3
"""
🚀 QUICK TEST RUNNER
Script đơn giản để test proxy validation service nhanh chóng
"""

import os
import sys
import json
import time
from datetime import datetime
import subprocess

def print_header(title):
    """Print formatted header"""
    print("\n" + "="*60)
    print(f"🧪 {title}")
    print("="*60)

def print_step(step_num, description):
    """Print test step"""
    print(f"\n📋 STEP {step_num}: {description}")
    print("-" * 40)

def run_command(cmd, description=""):
    """Run command and return success status"""
    print(f"🔧 Running: {cmd}")
    if description:
        print(f"   {description}")
    
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            print("✅ SUCCESS")
            return True, result.stdout
        else:
            print("❌ FAILED")
            print(f"Error: {result.stderr}")
            return False, result.stderr
    except subprocess.TimeoutExpired:
        print("⏰ TIMEOUT")
        return False, "Command timed out"
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False, str(e)

def check_service_health(url="http://localhost:5000"):
    """Check if service is healthy"""
    try:
        import requests
        response = requests.get(f"{url}/api/health", timeout=5)
        return response.status_code == 200
    except:
        return False

def get_proxy_stats(url="http://localhost:5000"):
    """Get proxy statistics"""
    try:
        import requests
        response = requests.get(f"{url}/api/proxy/stats", timeout=5)
        if response.status_code == 200:
            return response.json()
        return None
    except:
        return None

def main():
    """Main quick test function"""
    print_header("QUICK TEST RUNNER - Proxy Validation Service")
    
    print("🎯 Mục đích: Test nhanh service để tìm issues cơ bản")
    print("⏱️ Thời gian ước tính: 2-3 phút")
    
    results = {
        'timestamp': datetime.now().isoformat(),
        'tests': [],
        'summary': {}
    }
    
    # Step 1: Check Python environment
    print_step(1, "Kiểm tra Python Environment")
    
    success, output = run_command("python --version", "Check Python version")
    if not success:
        success, output = run_command("py --version", "Check Python version (Windows)")
    
    results['tests'].append({
        'name': 'Python Environment',
        'success': success,
        'output': output
    })
    
    # Step 2: Check dependencies
    print_step(2, "Kiểm tra Dependencies")
    
    required_modules = ['requests', 'flask']
    deps_ok = True
    
    for module in required_modules:
        try:
            __import__(module)
            print(f"✅ {module} - OK")
        except ImportError:
            print(f"❌ {module} - MISSING")
            deps_ok = False
    
    results['tests'].append({
        'name': 'Dependencies',
        'success': deps_ok,
        'output': f"Required modules: {required_modules}"
    })
    
    # Step 3: Test local functions
    print_step(3, "Test Local Functions")
    
    try:
        # Test imports
        from app import check_single_proxy, proxy_cache, PROXY_SOURCE_LINKS
        print("✅ Import functions - OK")
        
        # Test basic validation
        result = check_single_proxy("127.0.0.1:9999", timeout=2)
        if result is None:
            print("✅ Validation logic - OK (correctly rejected bad proxy)")
        else:
            print("⚠️ Validation logic - Unexpected result")
        
        # Test cache structure
        cache_keys = ['http', 'last_update', 'total_checked', 'alive_count']
        missing_keys = [k for k in cache_keys if k not in proxy_cache]
        if not missing_keys:
            print("✅ Cache structure - OK")
        else:
            print(f"❌ Cache structure - Missing keys: {missing_keys}")
        
        # Test sources config
        if 'categorized' in PROXY_SOURCE_LINKS and 'mixed' in PROXY_SOURCE_LINKS:
            print("✅ Sources config - OK")
        else:
            print("❌ Sources config - Invalid structure")
        
        local_tests_ok = True
        
    except Exception as e:
        print(f"❌ Local functions error: {e}")
        local_tests_ok = False
    
    results['tests'].append({
        'name': 'Local Functions',
        'success': local_tests_ok,
        'output': "Function imports and basic validation"
    })
    
    # Step 4: Check if service is running
    print_step(4, "Kiểm tra Service Status")
    
    service_running = check_service_health()
    if service_running:
        print("✅ Service is running and healthy")
        
        # Get service stats
        stats = get_proxy_stats()
        if stats:
            print(f"📊 Proxy stats:")
            print(f"   Alive proxies: {stats.get('alive_count', 0)}")
            print(f"   Total checked: {stats.get('total_checked', 0)}")
            print(f"   Success rate: {stats.get('success_rate', 0):.1f}%")
            
            # Health assessment
            alive_count = stats.get('alive_count', 0)
            if alive_count >= 50:
                print("🎉 Service health: EXCELLENT")
            elif alive_count >= 20:
                print("✅ Service health: GOOD")
            elif alive_count >= 5:
                print("⚠️ Service health: FAIR")
            else:
                print("❌ Service health: POOR")
        
    else:
        print("❌ Service is not running")
        print("💡 To start service: py app.py")
    
    results['tests'].append({
        'name': 'Service Status',
        'success': service_running,
        'output': "Service health check"
    })
    
    # Step 5: Quick API test (if service running)
    if service_running:
        print_step(5, "Quick API Test")
        
        api_tests = [
            ('/api/health', 'Health endpoint'),
            ('/api/proxy/stats', 'Stats endpoint'),
            ('/api/proxy/alive?count=5', 'Alive proxies endpoint'),
            ('/api/logs', 'Logs endpoint')
        ]
        
        api_success = 0
        for endpoint, description in api_tests:
            try:
                import requests
                response = requests.get(f"http://localhost:5000{endpoint}", timeout=10)
                if response.status_code == 200:
                    print(f"✅ {description} - OK")
                    api_success += 1
                else:
                    print(f"❌ {description} - HTTP {response.status_code}")
            except Exception as e:
                print(f"❌ {description} - Error: {e}")
        
        api_tests_ok = api_success >= 3
        results['tests'].append({
            'name': 'API Tests',
            'success': api_tests_ok,
            'output': f"Passed {api_success}/{len(api_tests)} API tests"
        })
    
    # Generate summary
    print_step(6, "Test Summary")
    
    total_tests = len(results['tests'])
    passed_tests = sum(1 for test in results['tests'] if test['success'])
    failed_tests = total_tests - passed_tests
    
    results['summary'] = {
        'total_tests': total_tests,
        'passed_tests': passed_tests,
        'failed_tests': failed_tests,
        'success_rate': (passed_tests / total_tests * 100) if total_tests > 0 else 0
    }
    
    print(f"📊 RESULTS:")
    print(f"   Total tests: {total_tests}")
    print(f"   ✅ Passed: {passed_tests}")
    print(f"   ❌ Failed: {failed_tests}")
    print(f"   📈 Success rate: {results['summary']['success_rate']:.1f}%")
    
    # Overall assessment
    success_rate = results['summary']['success_rate']
    if success_rate >= 90:
        print("\n🎉 OVERALL STATUS: EXCELLENT")
        print("   Service is working perfectly!")
    elif success_rate >= 70:
        print("\n✅ OVERALL STATUS: GOOD")
        print("   Service is working well with minor issues")
    elif success_rate >= 50:
        print("\n⚠️ OVERALL STATUS: NEEDS ATTENTION")
        print("   Service has some issues that need fixing")
    else:
        print("\n🚨 OVERALL STATUS: CRITICAL")
        print("   Service has major problems that need immediate attention")
    
    # Recommendations
    print("\n💡 RECOMMENDATIONS:")
    
    if not any(test['success'] for test in results['tests'] if test['name'] == 'Dependencies'):
        print("   1. Install missing dependencies: pip install -r requirements.txt")
    
    if not any(test['success'] for test in results['tests'] if test['name'] == 'Service Status'):
        print("   2. Start the service: py app.py")
    
    if failed_tests > 0:
        print("   3. Run comprehensive tests: py run_full_tests.py")
        print("   4. Check TESTING_GUIDE.md for detailed instructions")
    
    print("\n🔗 NEXT STEPS:")
    print("   - For detailed testing: py run_full_tests.py")
    print("   - For code analysis: py code_analysis.py")
    print("   - For service testing: py comprehensive_test_suite.py")
    print("   - Read TESTING_GUIDE.md for complete instructions")
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"quick_test_results_{timestamp}.json"
    
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n📄 Results saved to: {output_file}")
    
    # Return appropriate exit code
    return 0 if success_rate >= 70 else 1

if __name__ == "__main__":
    sys.exit(main()) 