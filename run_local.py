#!/usr/bin/env python3
"""
Local test runner for the ADE expiration monitor.
Runs the main logic without Azure Functions runtime.
"""

import os
import sys
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Import the functions from function_app
from function_app import check_expiring_environments, send_slack_notification

def main():
    """Run the expiration check locally."""
    print("="*60)
    print("LOCAL TEST: ADE Expiration Monitor")
    print("="*60)
    
    # Check required env vars
    subscription_id = os.environ.get("ADE_SUBSCRIPTION_ID")
    if not subscription_id:
        print("❌ ERROR: ADE_SUBSCRIPTION_ID environment variable not set")
        print("   Set it with: export ADE_SUBSCRIPTION_ID=c64fd005-b880-4802-9aa8-2dcc75068a20")
        sys.exit(1)
    
    print(f"✓ Subscription ID: {subscription_id}")
    print(f"✓ Slack Mock Mode: {os.environ.get('SLACK_MOCK', '0')}")
    print()
    
    try:
        print("Starting expiration check...")
        categorized_envs, total_count = check_expiring_environments()
        
        print()
        print("="*60)
        print(f"RESULTS: Found {total_count} environment(s) requiring attention")
        print("="*60)
        
        print(f"  Expired: {len(categorized_envs['expired'])}")
        print(f"  Tomorrow: {len(categorized_envs['tomorrow'])}")
        print(f"  3 Days: {len(categorized_envs['3_days'])}")
        print(f"  7 Days: {len(categorized_envs['7_days'])}")
        print()
        
        # Send notification
        print("Sending Slack notification...")
        success = send_slack_notification(categorized_envs, total_count)
        
        if success:
            print("✓ Notification sent successfully")
        else:
            print("⚠ Notification failed or skipped")
        
        print()
        print("="*60)
        print("✓ LOCAL TEST COMPLETED")
        print("="*60)
        
    except Exception as e:
        print()
        print("="*60)
        print(f"❌ ERROR: {str(e)}")
        print("="*60)
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
