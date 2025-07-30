#!/usr/bin/env python3
"""
🔍 LOGIC VALIDATION TEST
Test chi tiết các function validation logic để tìm bugs và issues
"""

import sys
import os
import time
import json
import random
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

class LogicTester:
    def __init__(self):
        self.test_results = {
            'timestamp': datetime.now().isoformat(),
            'tests': [],
            'issues_found': [],
            'recommendations': []
        }
        
    def log_result(self, test_name, passed, message="", issue=None):
        """Log test result"""
        status = "✅" if passed else "❌"
        print(f"{status} {test_name}: {message}")
        
        self.test_results['tests'].append({
            'name': test_name,
            'passed': passed,
            'message': message,
            'timestamp': datetime.now().isoformat()
        })
        
        if issue:
            self.test_results['issues_found'].append(issue)
    
    def test_check_single_proxy_function(self):
        """Test check_single_proxy function với different scenarios"""
        print("\n🔍 TESTING check_single_proxy FUNCTION...")
        
        try:
            from app import check_single_proxy
            
            # Test 1: Invalid format
            invalid_formats = [
                "invalid",
                "host:port:extra",
                "host:abc",
                "host:",
                ":port",
                "host:99999",  # Port out of range
                "host:-1",     # Negative port
                ""             # Empty string
            ]
            
            for invalid in invalid_formats:
                result = check_single_proxy(invalid, timeout=2)
                passed = result is None
                self.log_result(f"INVALID_FORMAT_{invalid}", passed,
                               f"Format '{invalid}' correctly rejected" if passed else f"Should reject '{invalid}'")
            
            # Test 2: Auth format parsing
            auth_formats = [
                "user:pass@host:port",
                "user@host:port",
                "user:@host:port",
                ":pass@host:port"
            ]
            
            for auth in auth_formats:
                try:
                    result = check_single_proxy(auth, timeout=1)
                    # Should not crash, result can be None (no proxy available)
                    self.log_result(f"AUTH_FORMAT_{auth.replace(':', '_').replace('@', '_')}", 
                                   True, "No crash on auth format")
                except Exception as e:
                    self.log_result(f"AUTH_FORMAT_{auth.replace(':', '_').replace('@', '_')}", 
                                   False, f"Crashed: {str(e)}")
            
            # Test 3: Timeout behavior
            start_time = time.time()
            result = check_single_proxy("192.168.1.1:8080", timeout=3)  # Should timeout
            end_time = time.time()
            
            took_time = end_time - start_time
            timeout_respected = took_time < 5  # Should not take much longer than timeout
            self.log_result("TIMEOUT_BEHAVIOR", timeout_respected,
                           f"Took {took_time:.2f}s for timeout=3")
            
        except ImportError:
            self.log_result("IMPORT_CHECK_SINGLE_PROXY", False, "Cannot import check_single_proxy")
        except Exception as e:
            self.log_result("CHECK_SINGLE_PROXY_TEST", False, f"Error: {str(e)}")
    
    def test_fetch_proxies_function(self):
        """Test fetch_proxies_from_sources function"""
        print("\n📥 TESTING fetch_proxies_from_sources FUNCTION...")
        
        try:
            from app import fetch_proxies_from_sources
            
            # Test basic functionality
            start_time = time.time()
            proxies, sources_count = fetch_proxies_from_sources()
            end_time = time.time()
            
            fetch_time = end_time - start_time
            
            self.log_result("FETCH_PROXIES_BASIC", len(proxies) > 0,
                           f"Fetched {len(proxies)} proxies from {sources_count} sources in {fetch_time:.2f}s")
            
            # Test proxy format consistency
            format_issues = []
            for i, proxy_data in enumerate(proxies[:50]):  # Check first 50
                if isinstance(proxy_data, tuple) and len(proxy_data) == 3:
                    proxy_type, proxy_string, protocol_info = proxy_data
                    
                    # Check proxy_string format
                    if ':' not in proxy_string:
                        format_issues.append(f"Index {i}: No colon in proxy_string '{proxy_string}'")
                    
                    # Check proxy_type
                    if proxy_type not in ['categorized', 'mixed']:
                        format_issues.append(f"Index {i}: Invalid proxy_type '{proxy_type}'")
                else:
                    format_issues.append(f"Index {i}: Invalid tuple format")
            
            self.log_result("PROXY_FORMAT_CONSISTENCY", len(format_issues) == 0,
                           f"Format issues: {len(format_issues)}")
            
            if format_issues:
                self.test_results['issues_found'].append({
                    'category': 'proxy_format',
                    'issues': format_issues[:10]  # Show first 10
                })
            
            # Test sources diversity
            categorized_count = sum(1 for p in proxies if isinstance(p, tuple) and p[0] == 'categorized')
            mixed_count = sum(1 for p in proxies if isinstance(p, tuple) and p[0] == 'mixed')
            
            self.log_result("SOURCES_DIVERSITY", categorized_count > 0 and mixed_count > 0,
                           f"Categorized: {categorized_count}, Mixed: {mixed_count}")
            
        except ImportError:
            self.log_result("IMPORT_FETCH_PROXIES", False, "Cannot import fetch_proxies_from_sources")
        except Exception as e:
            self.log_result("FETCH_PROXIES_TEST", False, f"Error: {str(e)}")
    
    def test_validate_proxy_batch_function(self):
        """Test validate_proxy_batch_smart function"""
        print("\n⚡ TESTING validate_proxy_batch_smart FUNCTION...")
        
        try:
            from app import validate_proxy_batch_smart
            
            # Test with small batch
            test_proxies = [
                ('categorized', '8.8.8.8:80', 'http'),
                ('categorized', '1.1.1.1:80', 'http'),
                ('mixed', '192.168.1.1:8080', ['http', 'https']),
                ('categorized', 'invalid_format', 'http'),
                ('categorized', '999.999.999.999:80', 'http')
            ]
            
            start_time = time.time()
            results = validate_proxy_batch_smart(test_proxies, max_workers=5)
            end_time = time.time()
            
            validation_time = end_time - start_time
            
            self.log_result("VALIDATE_BATCH_BASIC", isinstance(results, list),
                           f"Validated {len(test_proxies)} proxies in {validation_time:.2f}s, found {len(results)} alive")
            
            # Test result format
            format_issues = []
            for i, result in enumerate(results):
                required_fields = ['host', 'port', 'type', 'speed', 'status']
                missing_fields = [f for f in required_fields if f not in result]
                
                if missing_fields:
                    format_issues.append(f"Result {i}: Missing fields {missing_fields}")
            
            self.log_result("VALIDATE_RESULT_FORMAT", len(format_issues) == 0,
                           f"Format issues: {len(format_issues)}")
            
            # Test empty list
            empty_results = validate_proxy_batch_smart([])
            self.log_result("VALIDATE_EMPTY_LIST", empty_results == [],
                           "Empty list handled correctly")
            
        except ImportError:
            self.log_result("IMPORT_VALIDATE_BATCH", False, "Cannot import validate_proxy_batch_smart")
        except Exception as e:
            self.log_result("VALIDATE_BATCH_TEST", False, f"Error: {str(e)}")
    
    def test_cache_operations(self):
        """Test cache consistency and operations"""
        print("\n💾 TESTING CACHE OPERATIONS...")
        
        try:
            from app import proxy_cache
            
            # Test cache structure
            required_keys = ['http', 'last_update', 'total_checked', 'alive_count', 'sources_processed']
            missing_keys = [k for k in required_keys if k not in proxy_cache]
            
            self.log_result("CACHE_STRUCTURE", len(missing_keys) == 0,
                           f"Missing keys: {missing_keys}" if missing_keys else "All keys present")
            
            # Test cache data types
            type_issues = []
            if not isinstance(proxy_cache.get('http', []), list):
                type_issues.append("'http' should be list")
            if not isinstance(proxy_cache.get('total_checked', 0), int):
                type_issues.append("'total_checked' should be int")
            if not isinstance(proxy_cache.get('alive_count', 0), int):
                type_issues.append("'alive_count' should be int")
            
            self.log_result("CACHE_DATA_TYPES", len(type_issues) == 0,
                           f"Type issues: {type_issues}")
            
            # Test cache consistency
            http_list_count = len(proxy_cache.get('http', []))
            alive_count = proxy_cache.get('alive_count', 0)
            
            self.log_result("CACHE_CONSISTENCY", http_list_count == alive_count,
                           f"HTTP list: {http_list_count}, alive_count: {alive_count}")
            
        except ImportError:
            self.log_result("IMPORT_CACHE", False, "Cannot import proxy_cache")
        except Exception as e:
            self.log_result("CACHE_TEST", False, f"Error: {str(e)}")
    
    def test_proxy_sources_config(self):
        """Test proxy sources configuration"""
        print("\n🌐 TESTING PROXY SOURCES CONFIG...")
        
        try:
            from app import PROXY_SOURCE_LINKS
            
            # Test basic structure
            required_categories = ['categorized', 'mixed']
            missing_categories = [c for c in required_categories if c not in PROXY_SOURCE_LINKS]
            
            self.log_result("SOURCES_STRUCTURE", len(missing_categories) == 0,
                           f"Missing categories: {missing_categories}")
            
            # Test categorized sources
            categorized_issues = []
            for source_name, config in PROXY_SOURCE_LINKS.get('categorized', {}).items():
                if isinstance(config, dict):
                    if 'url' in config and 'protocol' in config:
                        # Single protocol format
                        if not isinstance(config['protocol'], str):
                            categorized_issues.append(f"{source_name}: protocol should be string")
                    else:
                        # Multiple protocols format (like Server Alpha)
                        for protocol, url in config.items():
                            if not isinstance(url, str) or not url.startswith('http'):
                                categorized_issues.append(f"{source_name}.{protocol}: invalid URL")
                else:
                    categorized_issues.append(f"{source_name}: config should be dict")
            
            self.log_result("CATEGORIZED_SOURCES", len(categorized_issues) == 0,
                           f"Issues: {len(categorized_issues)}")
            
            # Test mixed sources
            mixed_issues = []
            for source_name, config in PROXY_SOURCE_LINKS.get('mixed', {}).items():
                if not isinstance(config, dict):
                    mixed_issues.append(f"{source_name}: config should be dict")
                    continue
                
                if 'url' not in config:
                    mixed_issues.append(f"{source_name}: missing url")
                if 'protocols' not in config:
                    mixed_issues.append(f"{source_name}: missing protocols")
                elif not isinstance(config['protocols'], list):
                    mixed_issues.append(f"{source_name}: protocols should be list")
            
            self.log_result("MIXED_SOURCES", len(mixed_issues) == 0,
                           f"Issues: {len(mixed_issues)}")
            
            # Count total sources
            total_sources = len(PROXY_SOURCE_LINKS.get('categorized', {})) + len(PROXY_SOURCE_LINKS.get('mixed', {}))
            self.log_result("SOURCES_COUNT", total_sources >= 8,
                           f"Total sources: {total_sources}")
            
        except ImportError:
            self.log_result("IMPORT_SOURCES", False, "Cannot import PROXY_SOURCE_LINKS")
        except Exception as e:
            self.log_result("SOURCES_TEST", False, f"Error: {str(e)}")
    
    def test_background_thread_logic(self):
        """Test background thread logic"""
        print("\n🧵 TESTING BACKGROUND THREAD LOGIC...")
        
        try:
            from app import background_proxy_refresh, startup_status
            
            # Test startup status structure
            required_status_keys = ['initialized', 'background_thread_started', 'first_fetch_completed', 'error_count']
            missing_status_keys = [k for k in required_status_keys if k not in startup_status]
            
            self.log_result("STARTUP_STATUS_STRUCTURE", len(missing_status_keys) == 0,
                           f"Missing keys: {missing_status_keys}")
            
            # Test startup status values
            status_issues = []
            if not isinstance(startup_status.get('initialized', False), bool):
                status_issues.append("'initialized' should be bool")
            if not isinstance(startup_status.get('error_count', 0), int):
                status_issues.append("'error_count' should be int")
            
            self.log_result("STARTUP_STATUS_TYPES", len(status_issues) == 0,
                           f"Type issues: {status_issues}")
            
            # Test if background function exists and is callable
            self.log_result("BACKGROUND_FUNCTION_EXISTS", callable(background_proxy_refresh),
                           "background_proxy_refresh is callable")
            
        except ImportError:
            self.log_result("IMPORT_BACKGROUND", False, "Cannot import background functions")
        except Exception as e:
            self.log_result("BACKGROUND_TEST", False, f"Error: {str(e)}")
    
    def test_potential_race_conditions(self):
        """Test for potential race conditions"""
        print("\n🏃 TESTING POTENTIAL RACE CONDITIONS...")
        
        try:
            from app import proxy_cache
            
            # Test concurrent cache access
            original_cache = proxy_cache.copy()
            
            def read_cache():
                return proxy_cache.get('alive_count', 0)
            
            def write_cache(value):
                proxy_cache['alive_count'] = value
            
            # Simulate concurrent access
            results = []
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = []
                
                # Mix of read and write operations
                for i in range(10):
                    if i % 2 == 0:
                        futures.append(executor.submit(read_cache))
                    else:
                        futures.append(executor.submit(write_cache, i))
                
                results = [f.result() for f in as_completed(futures)]
            
            # Check if cache is still consistent
            final_count = proxy_cache.get('alive_count', 0)
            self.log_result("RACE_CONDITION_CACHE", isinstance(final_count, int),
                           f"Final count: {final_count}, type: {type(final_count)}")
            
        except Exception as e:
            self.log_result("RACE_CONDITION_TEST", False, f"Error: {str(e)}")
    
    def test_memory_usage_patterns(self):
        """Test memory usage patterns"""
        print("\n💾 TESTING MEMORY USAGE PATTERNS...")
        
        try:
            import psutil
            import os
            
            # Get current process
            process = psutil.Process(os.getpid())
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            # Simulate some operations
            from app import check_single_proxy
            
            # Test with many invalid proxies (should not accumulate memory)
            for i in range(100):
                check_single_proxy(f"invalid_{i}:80", timeout=1)
            
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = final_memory - initial_memory
            
            self.log_result("MEMORY_USAGE", memory_increase < 50,  # Less than 50MB increase
                           f"Memory increase: {memory_increase:.2f}MB")
            
        except ImportError:
            self.log_result("MEMORY_TEST", False, "psutil not available")
        except Exception as e:
            self.log_result("MEMORY_TEST", False, f"Error: {str(e)}")
    
    def generate_recommendations(self):
        """Generate recommendations based on tests"""
        print("\n💡 GENERATING RECOMMENDATIONS...")
        
        failed_tests = [t for t in self.test_results['tests'] if not t['passed']]
        
        if any('TIMEOUT' in t['name'] for t in failed_tests):
            self.test_results['recommendations'].append(
                "Consider adjusting timeout values for better performance"
            )
        
        if any('CACHE' in t['name'] for t in failed_tests):
            self.test_results['recommendations'].append(
                "Review cache management and consistency logic"
            )
        
        if any('FORMAT' in t['name'] for t in failed_tests):
            self.test_results['recommendations'].append(
                "Improve input validation and format checking"
            )
        
        if any('RACE' in t['name'] for t in failed_tests):
            self.test_results['recommendations'].append(
                "Add proper locking mechanisms for concurrent access"
            )
        
        if any('MEMORY' in t['name'] for t in failed_tests):
            self.test_results['recommendations'].append(
                "Review memory usage and implement cleanup routines"
            )
    
    def run_all_tests(self):
        """Run all logic tests"""
        print("🔍 STARTING LOGIC VALIDATION TESTS")
        print("=" * 60)
        
        self.test_check_single_proxy_function()
        self.test_fetch_proxies_function()
        self.test_validate_proxy_batch_function()
        self.test_cache_operations()
        self.test_proxy_sources_config()
        self.test_background_thread_logic()
        self.test_potential_race_conditions()
        self.test_memory_usage_patterns()
        
        self.generate_recommendations()
        self.generate_summary()
        
        return self.test_results
    
    def generate_summary(self):
        """Generate test summary"""
        print("\n" + "=" * 60)
        print("📋 LOGIC VALIDATION SUMMARY")
        print("=" * 60)
        
        total_tests = len(self.test_results['tests'])
        passed_tests = sum(1 for t in self.test_results['tests'] if t['passed'])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests*100):.1f}%")
        
        if self.test_results['issues_found']:
            print(f"\n🐛 ISSUES FOUND ({len(self.test_results['issues_found'])}):")
            for issue in self.test_results['issues_found']:
                print(f"  - {issue}")
        
        if self.test_results['recommendations']:
            print(f"\n💡 RECOMMENDATIONS ({len(self.test_results['recommendations'])}):")
            for rec in self.test_results['recommendations']:
                print(f"  - {rec}")

def main():
    """Main function"""
    tester = LogicTester()
    results = tester.run_all_tests()
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"logic_test_results_{timestamp}.json"
    
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n📄 Results saved to: {output_file}")
    return results

if __name__ == "__main__":
    main() 