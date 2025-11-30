# How to Create a Slack Webhook (5 minutes)

## Quick Steps:

### 1. Go to Slack API
Visit: https://api.slack.com/apps

### 2. Create a New App
- Click **"Create New App"**
- Choose **"From scratch"**
- Enter:
  - **App Name**: "ADE Expiration Alerts" (or any name)
  - **Workspace**: Select your workspace
- Click **"Create App"**

### 3. Enable Incoming Webhooks
- In the left sidebar, click **"Incoming Webhooks"**
- Toggle **"Activate Incoming Webhooks"** to **ON**

### 4. Add Webhook to Workspace
- Scroll down and click **"Add New Webhook to Workspace"**
- Select the channel where you want notifications (e.g., #ade-alerts, #general)
- Click **"Allow"**

### 5. Copy Webhook URL
- You'll see a webhook URL like:
  ```
  https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXX
  ```
- **Copy this URL** - you'll need it for your function

### 6. Update Your Configuration
Add the webhook URL to `/src/functions/local.settings.json`:

```json
{
  "Values": {
    "SLACK_WEBHOOK_URL": "https://hooks.slack.com/services/YOUR/WEBHOOK/URL",
    ...
  }
}
```

## Quick Test

You can test it immediately with curl:

```bash
curl -X POST -H 'Content-type: application/json' \
  --data '{"text":"Hello from ADE Expiration Alerts! 🎉"}' \
  YOUR_WEBHOOK_URL
```

Replace `YOUR_WEBHOOK_URL` with your actual webhook URL.

## Done! ✅

Your webhook is ready to use. The demo script will now send real messages to your Slack channel.

---

**Note:** Keep your webhook URL secret - anyone with it can post to your channel!
