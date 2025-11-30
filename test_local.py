#!/usr/bin/env python3
"""
Test script to run the expirationRunNow function locally without Azure Functions runtime.
This simulates the timer trigger by calling the main function directly.
"""

import sys
import os
from datetime import datetime, timezone

# Add the function directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables from local.settings.json
import json

local_settings_path = os.path.join(os.path.dirname(__file__), '..', 'local.settings.json')
if os.path.exists(local_settings_path):
    with open(local_settings_path, 'r') as f:
        settings = json.load(f)
        for key, value in settings.get('Values', {}).items():
            os.environ[key] = value
    print(f"✅ Loaded environment variables from local.settings.json")
else:
    print("⚠️  No local.settings.json found, using system environment variables")

# Import the function
try:
    from function_app import check_expiring_environments, send_slack_notification
    print("✅ Successfully imported function modules")
except ImportError as e:
    print(f"❌ Failed to import function: {e}")
    sys.exit(1)

# Mock timer object
class MockTimer:
    def __init__(self):
        self.past_due = False

def test_function():
    """Test the function by calling its logic directly."""
    print("\n" + "="*60)
    print("🧪 TESTING EXPIRATION RUNNOW FUNCTION")
    print("="*60 + "\n")
    
    # Print configuration
    print("📋 Configuration:")
    print(f"   ADE_SUBSCRIPTION_ID: {os.environ.get('ADE_SUBSCRIPTION_ID', 'NOT SET')}")
    print(f"   ADE_DEV_CENTER: {os.environ.get('ADE_DEV_CENTER', 'NOT SET')}")
    print(f"   ADE_PROJECT_NAME: {os.environ.get('ADE_PROJECT_NAME', 'NOT SET')}")
    print(f"   SLACK_WEBHOOK_URL: {'***' + os.environ.get('SLACK_WEBHOOK_URL', 'NOT SET')[-20:] if os.environ.get('SLACK_WEBHOOK_URL') else 'NOT SET'}")
    print(f"   SLACK_MOCK: {os.environ.get('SLACK_MOCK', '0')}")
    print(f"   EXPIRATION_WARN_DAYS: {os.environ.get('EXPIRATION_WARN_DAYS', '3')}")
    print()
    
    # Check required variables
    required = ['ADE_SUBSCRIPTION_ID', 'ADE_DEV_CENTER', 'ADE_PROJECT_NAME']
    missing = [var for var in required if not os.environ.get(var) or os.environ.get(var) == f'your-{var.lower().replace("_", "-")}']
    
    if missing:
        print(f"❌ Missing or invalid required environment variables: {', '.join(missing)}")
        print("\n⚠️  Please update local.settings.json with your actual Azure values:")
        print("   - ADE_SUBSCRIPTION_ID: Your Azure subscription ID")
        print("   - ADE_DEV_CENTER: Your DevCenter name")
        print("   - ADE_PROJECT_NAME: Your project name")
        print("\nℹ️  For testing without real values, set SLACK_MOCK=1")
        return False
    
    try:
        # Test fetching environments
        print("🔍 Step 1: Fetching environments from Azure DevCenter...")
        warn_days = int(os.environ.get('EXPIRATION_WARN_DAYS', '3'))
        expiring_envs = check_expiring_environments(warn_days=warn_days)
        
        print(f"✅ Successfully fetched and analyzed environments")
        print(f"   Found {len(expiring_envs)} environment(s) expiring within {warn_days} days\n")
        
        # Display results
        if expiring_envs:
            print("📊 Expiring Environments:")
            for i, env in enumerate(expiring_envs, 1):
                status_emoji = "❌" if env['status'] == 'expired' else "⚠️"
                print(f"\n   {i}. {status_emoji} {env['name']}")
                print(f"      Project: {env['project']}")
                print(f"      User: {env.get('user', 'N/A')}")
                print(f"      Expiration: {env['expirationDate']}")
                print(f"      Days until expiration: {env['daysUntilExpiration']}")
                print(f"      Status: {env['status']}")
        else:
            print("✅ No environments expiring soon - all healthy!")
        
        # Test Slack notification
        print(f"\n📨 Step 2: Sending Slack notification...")
        success = send_slack_notification(expiring_envs)
        
        if success:
            print("✅ Slack notification sent successfully")
        else:
            print("⚠️  Slack notification failed (check logs above)")
        
        print("\n" + "="*60)
        print("✅ TEST COMPLETED SUCCESSFULLY")
        print("="*60 + "\n")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        print("\n" + "="*60)
        print("❌ TEST FAILED")
        print("="*60 + "\n")
        return False

if __name__ == '__main__':
    success = test_function()
    sys.exit(0 if success else 1)
