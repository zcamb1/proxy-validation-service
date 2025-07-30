#!/usr/bin/env python3
"""
🧪 MASTER TEST RUNNER
Chạy tất cả tests và generate comprehensive report
"""

import json
import time
import sys
import os
from datetime import datetime
import argparse

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def run_local_tests():
    """Run local logic tests"""
    print("🔍 RUNNING LOCAL LOGIC TESTS...")
    try:
        from logic_validation_test import LogicTester
        tester = LogicTester()
        return tester.run_all_tests()
    except Exception as e:
        print(f"❌ Error running local tests: {e}")
        return None

def run_service_tests(service_url):
    """Run service API tests"""
    print(f"🌐 RUNNING SERVICE TESTS FOR: {service_url}")
    try:
        from comprehensive_test_suite import ProxyServiceTester
        tester = ProxyServiceTester(service_url)
        return tester.run_all_tests()
    except Exception as e:
        print(f"❌ Error running service tests: {e}")
        return None

def check_service_availability(service_url):
    """Check if service is available"""
    try:
        import requests
        response = requests.get(f"{service_url}/api/health", timeout=10)
        return response.status_code == 200
    except:
        return False

def generate_comprehensive_report(local_results, service_results, service_url):
    """Generate comprehensive test report"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    report = {
        'timestamp': timestamp,
        'service_url': service_url,
        'local_tests': local_results,
        'service_tests': service_results,
        'overall_summary': {},
        'critical_issues': [],
        'recommendations': [],
        'action_items': []
    }
    
    # Calculate overall statistics
    total_tests = 0
    passed_tests = 0
    failed_tests = 0
    
    if local_results:
        local_total = len(local_results.get('tests', []))
        local_passed = sum(1 for t in local_results.get('tests', []) if t['passed'])
        total_tests += local_total
        passed_tests += local_passed
        failed_tests += (local_total - local_passed)
    
    if service_results:
        service_total = service_results.get('total_tests', 0)
        service_passed = service_results.get('passed_tests', 0)
        total_tests += service_total
        passed_tests += service_passed
        failed_tests += service_results.get('failed_tests', 0)
    
    report['overall_summary'] = {
        'total_tests': total_tests,
        'passed_tests': passed_tests,
        'failed_tests': failed_tests,
        'success_rate': (passed_tests / total_tests * 100) if total_tests > 0 else 0
    }
    
    # Collect critical issues
    if local_results and local_results.get('issues_found'):
        report['critical_issues'].extend(local_results['issues_found'])
    
    if service_results and service_results.get('critical_issues'):
        report['critical_issues'].extend(service_results['critical_issues'])
    
    # Collect recommendations
    if local_results and local_results.get('recommendations'):
        report['recommendations'].extend(local_results['recommendations'])
    
    if service_results and service_results.get('recommendations'):
        report['recommendations'].extend(service_results['recommendations'])
    
    # Generate action items based on results
    if failed_tests > 0:
        report['action_items'].append(f"Fix {failed_tests} failing tests")
    
    if report['critical_issues']:
        report['action_items'].append("Address critical issues immediately")
    
    if report['overall_summary']['success_rate'] < 80:
        report['action_items'].append("Improve overall test success rate")
    
    return report

def print_report_summary(report):
    """Print comprehensive report summary"""
    print("\n" + "=" * 80)
    print("🎯 COMPREHENSIVE TEST REPORT SUMMARY")
    print("=" * 80)
    
    summary = report['overall_summary']
    print(f"📊 OVERALL STATISTICS:")
    print(f"   Total Tests: {summary['total_tests']}")
    print(f"   ✅ Passed: {summary['passed_tests']}")
    print(f"   ❌ Failed: {summary['failed_tests']}")
    print(f"   📈 Success Rate: {summary['success_rate']:.1f}%")
    
    # Service status
    print(f"\n🌐 SERVICE STATUS:")
    print(f"   URL: {report['service_url']}")
    if report['service_tests']:
        print(f"   Status: ✅ Available")
    else:
        print(f"   Status: ❌ Not Available")
    
    # Health assessment
    print(f"\n🏥 HEALTH ASSESSMENT:")
    success_rate = summary['success_rate']
    if success_rate >= 95:
        print("   🎉 EXCELLENT - Service is working perfectly")
    elif success_rate >= 85:
        print("   ✅ GOOD - Service is working well with minor issues")
    elif success_rate >= 70:
        print("   ⚠️ FAIR - Service has some issues that need attention")
    elif success_rate >= 50:
        print("   🔴 POOR - Service has significant issues")
    else:
        print("   🚨 CRITICAL - Service has major problems")
    
    # Critical issues
    if report['critical_issues']:
        print(f"\n🚨 CRITICAL ISSUES ({len(report['critical_issues'])}):")
        for i, issue in enumerate(report['critical_issues'][:5], 1):
            print(f"   {i}. {issue}")
        if len(report['critical_issues']) > 5:
            print(f"   ... and {len(report['critical_issues']) - 5} more")
    
    # Recommendations
    if report['recommendations']:
        print(f"\n💡 RECOMMENDATIONS ({len(report['recommendations'])}):")
        for i, rec in enumerate(report['recommendations'][:5], 1):
            print(f"   {i}. {rec}")
        if len(report['recommendations']) > 5:
            print(f"   ... and {len(report['recommendations']) - 5} more")
    
    # Action items
    if report['action_items']:
        print(f"\n🎯 ACTION ITEMS ({len(report['action_items'])}):")
        for i, item in enumerate(report['action_items'], 1):
            print(f"   {i}. {item}")
    
    print("\n" + "=" * 80)

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Run comprehensive proxy service tests')
    parser.add_argument('--service-url', default='http://localhost:5000',
                       help='Service URL to test')
    parser.add_argument('--local-only', action='store_true',
                       help='Run only local tests')
    parser.add_argument('--service-only', action='store_true',
                       help='Run only service tests')
    parser.add_argument('--output-dir', default='.',
                       help='Output directory for results')
    
    args = parser.parse_args()
    
    print("🧪 COMPREHENSIVE PROXY SERVICE TESTING")
    print("=" * 80)
    
    local_results = None
    service_results = None
    
    # Run local tests
    if not args.service_only:
        local_results = run_local_tests()
    
    # Run service tests
    if not args.local_only:
        if check_service_availability(args.service_url):
            service_results = run_service_tests(args.service_url)
        else:
            print(f"❌ Service not available at {args.service_url}")
    
    # Generate comprehensive report
    report = generate_comprehensive_report(local_results, service_results, args.service_url)
    
    # Print summary
    print_report_summary(report)
    
    # Save detailed results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(args.output_dir, f"comprehensive_test_report_{timestamp}.json")
    
    with open(output_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n📄 Detailed report saved to: {output_file}")
    
    # Return exit code based on results
    success_rate = report['overall_summary']['success_rate']
    if success_rate >= 80:
        print("🎉 TESTS PASSED - Service is healthy")
        return 0
    else:
        print("❌ TESTS FAILED - Service needs attention")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 