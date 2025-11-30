#!/usr/bin/env python3
"""
DEMO SCRIPT: Simulate expiration alerts with mocked data
This script demonstrates the expiration notification system without requiring real Azure credentials.
"""

import sys
import os
import json
import requests
from datetime import datetime, timedelta, timezone

# Load environment from local.settings.json
local_settings_path = os.path.join(os.path.dirname(__file__), '..', 'local.settings.json')
if os.path.exists(local_settings_path):
    with open(local_settings_path, 'r') as f:
        settings = json.load(f)
        for key, value in settings.get('Values', {}).items():
            os.environ[key] = value

def create_mock_environments():
    """Create realistic mock ADE environments with various expiration states."""
    now = datetime.now(timezone.utc)
    
    mock_envs = [
        {
            "name": "dev-frontend-app",
            "projectName": "customer-portal",
            "user": "alice@company.com",
            "catalogName": "production-catalog",
            "environmentType": "Development",
            "resourceGroupId": "/subscriptions/abc123/resourceGroups/rg-dev-frontend",
            "expirationDate": (now - timedelta(days=2)).isoformat(),  # EXPIRED 2 days ago
            "provisioningState": "Succeeded"
        },
        {
            "name": "test-backend-api",
            "projectName": "customer-portal",
            "user": "bob@company.com",
            "catalogName": "production-catalog",
            "environmentType": "Testing",
            "resourceGroupId": "/subscriptions/abc123/resourceGroups/rg-test-backend",
            "expirationDate": now.isoformat(),  # EXPIRES TODAY
            "provisioningState": "Succeeded"
        },
        {
            "name": "demo-ml-workspace",
            "projectName": "ai-initiatives",
            "user": "carol@company.com",
            "catalogName": "ml-catalog",
            "environmentType": "Development",
            "resourceGroupId": "/subscriptions/abc123/resourceGroups/rg-demo-ml",
            "expirationDate": (now + timedelta(days=1)).isoformat(),  # EXPIRES TOMORROW
            "provisioningState": "Succeeded"
        },
        {
            "name": "staging-database",
            "projectName": "data-platform",
            "user": "david@company.com",
            "catalogName": "database-catalog",
            "environmentType": "Staging",
            "resourceGroupId": "/subscriptions/abc123/resourceGroups/rg-staging-db",
            "expirationDate": (now + timedelta(days=2)).isoformat(),  # Expires in 2 days
            "provisioningState": "Succeeded"
        },
        {
            "name": "poc-iot-simulator",
            "projectName": "iot-platform",
            "user": "eve@company.com",
            "catalogName": "iot-catalog",
            "environmentType": "Development",
            "resourceGroupId": "/subscriptions/abc123/resourceGroups/rg-poc-iot",
            "expirationDate": (now - timedelta(hours=6)).isoformat(),  # EXPIRED 6 hours ago
            "provisioningState": "Succeeded"
        }
    ]
    
    return mock_envs


def parse_expiration_date(expiration_str):
    """Parse expiration date from ISO format string."""
    if not expiration_str:
        return None
    
    try:
        if expiration_str.endswith('Z'):
            return datetime.fromisoformat(expiration_str.replace('Z', '+00:00'))
        else:
            dt = datetime.fromisoformat(expiration_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
    except Exception as e:
        print(f"⚠️  Failed to parse date '{expiration_str}': {e}")
        return None


def check_expiring_environments(mock_envs, warn_days=3):
    """Check environments and return those expiring soon or already expired."""
    now = datetime.now(timezone.utc)
    warn_threshold = now + timedelta(days=warn_days)
    
    expiring = []
    
    for env in mock_envs:
        expiration_str = env.get("expirationDate")
        
        if not expiration_str:
            continue
        
        expiration_date = parse_expiration_date(expiration_str)
        
        if not expiration_date:
            continue
        
        # Check if expired or expiring soon
        if expiration_date <= warn_threshold:
            days_until_expiration = (expiration_date - now).days
            status = "expired" if expiration_date < now else "expiring"
            
            expiring.append({
                "name": env.get("name"),
                "project": env.get("projectName"),
                "user": env.get("user"),
                "catalogName": env.get("catalogName"),
                "environmentType": env.get("environmentType"),
                "resourceGroupId": env.get("resourceGroupId"),
                "expirationDate": expiration_date.isoformat(),
                "daysUntilExpiration": days_until_expiration,
                "status": status
            })
    
    return expiring


def send_slack_notification(expiring_envs):
    """Send Slack notification about expiring environments."""
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
    mock_mode = os.environ.get("SLACK_MOCK", "0") in ("1", "true", "True")
    
    if not webhook_url:
        print("❌ SLACK_WEBHOOK_URL not configured!")
        return False
    
    if not expiring_envs:
        message = "✅ All Azure Deployment Environments are healthy - no expiration warnings."
        payload = {"text": message}
    else:
        expired_count = sum(1 for e in expiring_envs if e["status"] == "expired")
        expiring_count = len(expiring_envs) - expired_count
        
        warning_emoji = "🚨" if expired_count > 0 else "⚠️"
        
        text = f"{warning_emoji} Azure Deployment Environment Expiration Alert"
        
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{warning_emoji} ADE Expiration Alert - DEMO",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Summary:*\n• {expired_count} environment(s) already expired ❌\n• {expiring_count} environment(s) expiring soon ⏰"
                }
            },
            {"type": "divider"}
        ]
        
        # Add details for each environment
        for env in expiring_envs[:10]:
            days = env["daysUntilExpiration"]
            
            if env["status"] == "expired":
                status_text = f"❌ *EXPIRED* ({abs(days)} days ago)"
            elif days == 0:
                status_text = f"🚨 *Expires TODAY*"
            elif days == 1:
                status_text = f"⚠️ *Expires TOMORROW*"
            else:
                status_text = f"⏰ Expires in {days} days"
            
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"{status_text}\n"
                        f"*Environment:* `{env['name']}`\n"
                        f"*Project:* {env['project']}\n"
                        f"*User:* {env.get('user', 'N/A')}\n"
                        f"*Type:* {env.get('environmentType', 'N/A')}\n"
                        f"*Expiration:* {env['expirationDate'][:10]}"
                    )
                }
            })
        
        if len(expiring_envs) > 10:
            blocks.append({
                "type": "context",
                "elements": [{
                    "type": "mrkdwn",
                    "text": f"_...and {len(expiring_envs) - 10} more environment(s)_"
                }]
            })
        
        blocks.append({"type": "divider"})
        blocks.append({
            "type": "context",
            "elements": [{
                "type": "mrkdwn",
                "text": f"🤖 _Automated alert from Azure Deployment Environments | {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC_"
            }]
        })
        
        payload = {
            "text": text,
            "blocks": blocks
        }
    
    # Mock mode or actual send
    if mock_mode:
        timestamp = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        print(f"\n{'='*70}")
        print(f"[MOCK SLACK MESSAGE {timestamp}]")
        print(f"{'='*70}")
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        print(f"{'='*70}\n")
        return True
    
    try:
        print(f"📤 Sending to Slack webhook: {webhook_url[:50]}...")
        response = requests.post(
            webhook_url,
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        response.raise_for_status()
        print("✅ Successfully sent Slack notification!")
        return True
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to send Slack notification: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"   Response: {e.response.text}")
        return False


def main():
    """Main demo function."""
    print("\n" + "="*70)
    print("🎬 DEMO: Azure Deployment Environment Expiration Alerts")
    print("="*70 + "\n")
    
    print("📋 Configuration:")
    print(f"   SLACK_WEBHOOK_URL: {'✅ Configured' if os.environ.get('SLACK_WEBHOOK_URL') else '❌ NOT SET'}")
    print(f"   SLACK_MOCK: {os.environ.get('SLACK_MOCK', '0')}")
    print(f"   EXPIRATION_WARN_DAYS: {os.environ.get('EXPIRATION_WARN_DAYS', '3')}")
    print()
    
    # Create mock environments
    print("🏗️  Creating mock Azure Deployment Environments...")
    mock_envs = create_mock_environments()
    print(f"✅ Created {len(mock_envs)} mock environments\n")
    
    # Check for expiring environments
    warn_days = int(os.environ.get('EXPIRATION_WARN_DAYS', '3'))
    print(f"🔍 Checking for environments expiring within {warn_days} days...")
    expiring_envs = check_expiring_environments(mock_envs, warn_days=warn_days)
    
    print(f"✅ Found {len(expiring_envs)} environment(s) expiring within {warn_days} days\n")
    
    if expiring_envs:
        print("📊 Expiring Environments Details:")
        print("-" * 70)
        for i, env in enumerate(expiring_envs, 1):
            status_emoji = "❌" if env['status'] == 'expired' else "⚠️"
            print(f"\n{i}. {status_emoji} {env['name']}")
            print(f"   Project: {env['project']}")
            print(f"   User: {env.get('user', 'N/A')}")
            print(f"   Type: {env.get('environmentType', 'N/A')}")
            print(f"   Expiration: {env['expirationDate']}")
            print(f"   Days until expiration: {env['daysUntilExpiration']}")
            print(f"   Status: {env['status'].upper()}")
        print()
    
    # Send Slack notification
    print("📨 Sending Slack notification...")
    print("-" * 70)
    success = send_slack_notification(expiring_envs)
    
    if success:
        print("\n" + "="*70)
        print("✅ DEMO COMPLETED SUCCESSFULLY!")
        print("="*70 + "\n")
        return 0
    else:
        print("\n" + "="*70)
        print("⚠️  DEMO COMPLETED WITH WARNINGS")
        print("="*70 + "\n")
        return 1


if __name__ == '__main__':
    sys.exit(main())
