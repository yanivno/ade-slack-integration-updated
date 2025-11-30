# expirationRunNow - Azure Function

## Overview

This is a containerized Azure Function that runs daily to monitor ALL Azure Deployment Environment (ADE) expiration dates across your subscription and sends categorized Slack notifications with owner information.

## Features

- ✅ **Daily Scheduled Execution**: Runs automatically at 9:00 AM UTC every day
- 🌍 **Subscription-Wide Monitoring**: Queries ALL environments using Azure Resource Graph (not just current user)
- � **Owner Identification**: Extracts owner email from `created_by` Azure tag
- 📊 **Categorized Alerts**: Groups environments by urgency (expired, tomorrow, 3 days, 7 days)
- 📱 **Rich Slack Notifications**: Sends formatted messages with owner details per category
- 🐳 **Containerized**: Self-contained Docker container with all dependencies
- 🔐 **Managed Identity**: Uses Azure Managed Identity for authentication

## Architecture

The function:
1. Authenticates using Azure Managed Identity (DefaultAzureCredential)
2. Queries Azure Resource Graph to get ALL resource groups with ADE tags across the subscription
3. Extracts expiration dates from resource group tags (e.g., `ade:expiresOn`)
4. Extracts owner email from `created_by` tag
5. Categorizes environments by urgency:
   - **Expired**: Already past expiration date
   - **Tomorrow**: Expiring within 24 hours
   - **3 Days**: Expiring within 3 days
   - **7 Days**: Expiring within 7 days
6. Sends categorized Slack notification with owner details
7. Logs results and errors to Application Insights

## Environment Variables

Required:
- `ADE_SUBSCRIPTION_ID`: Your Azure subscription ID
- `SLACK_WEBHOOK_URL`: Slack incoming webhook URL

Optional:
- `SLACK_MOCK`: Set to "1" to print messages instead of sending (for testing)

## Timer Schedule

The function runs on a **daily timer trigger** with the schedule: `0 0 9 * * *`

This translates to: **9:00 AM UTC every day**

CRON format: `{second} {minute} {hour} {day} {month} {day-of-week}`

To change the schedule, edit `function.json` and modify the `schedule` property.

## Building the Container

```bash
# From this directory
docker build -t ade-expiration-runnow:latest .
```

## Running Locally

1. Copy `.env.example` to `.env` and fill in your values:
   ```bash
   cp .env.example .env
   ```

2. Install Azure Functions Core Tools:
   ```bash
   brew install azure-functions-core-tools@4  # macOS
   ```

3. Run locally:
   ```bash
   func start
   ```

## Deploying to Azure

### Option 1: Deploy as Container to Azure Container Apps

```bash
# Build and push to Azure Container Registry
az acr build --registry <your-acr> --image ade-expiration-runnow:latest .

# Deploy to Container Apps with managed identity
az containerapp create \
  --name ade-expiration-runnow \
  --resource-group <your-rg> \
  --environment <your-env> \
  --image <your-acr>.azurecr.io/ade-expiration-runnow:latest \
  --assign-identity [system] \
  --env-vars \
    ADE_SUBSCRIPTION_ID=<sub-id> \
    ADE_DEV_CENTER=<devcenter> \
    ADE_PROJECT_NAME=<project> \
    SLACK_WEBHOOK_URL=<webhook>
```

### Option 2: Deploy as Azure Function (Container)

```bash
# Create Function App with container
az functionapp create \
  --name ade-expiration-func \
  --resource-group <your-rg> \
  --storage-account <storage> \
  --plan <plan> \
  --deployment-container-image-name <your-acr>.azurecr.io/ade-expiration-runnow:latest \
  --functions-version 4 \
  --assign-identity [system]

# Configure app settings
az functionapp config appsettings set \
  --name ade-expiration-func \
  --resource-group <your-rg> \
  --settings \
    ADE_SUBSCRIPTION_ID=<sub-id> \
    ADE_DEV_CENTER=<devcenter> \
    ADE_PROJECT_NAME=<project> \
    SLACK_WEBHOOK_URL=<webhook>
```

## Permissions Required

The function's Managed Identity needs:

1. **DevCenter Reader** role on the DevCenter resource
2. **Reader** role on the subscription (to access environments)

```bash
# Assign permissions
FUNC_IDENTITY=$(az functionapp identity show -n ade-expiration-func -g <rg> --query principalId -o tsv)

az role assignment create \
  --assignee $FUNC_IDENTITY \
  --role "DevCenter Project Admin" \
  --scope /subscriptions/<sub>/resourceGroups/<rg>/providers/Microsoft.DevCenter/projects/<project>
```

## Slack Webhook Setup

1. Go to your Slack workspace settings
2. Navigate to **Apps** → **Incoming Webhooks**
3. Click **Add to Slack**
4. Choose the channel for notifications
5. Copy the webhook URL
6. Add it to your function's environment variables


## Generate Token for Slack App
https://stackoverflow.com/questions/67793807/get-slack-user-token-for-slack-api



## Notification Format

The Slack notification includes:

- **Summary**: Count of expired and expiring environments
- **Details per environment**:
  - Status (expired, expires today, expires in X days)
  - Environment name
  - Project name
  - User/owner
  - Expiration date
- **Emoji indicators**: 🚨 for expired, ⚠️ for expiring soon, ✅ for healthy

## Testing

To manually trigger the function (bypass timer):

```bash
# Using HTTP trigger endpoint (if added for testing)
curl -X POST http://localhost:7071/admin/functions/expirationRunNow

# Or trigger timer manually in Azure Portal
```

## Monitoring

- View logs in **Application Insights**
- Check execution history in **Azure Functions Monitor**
- Slack notifications are sent for both success and failure

## Troubleshooting

### Function not running on schedule
- Check timer trigger is enabled
- Verify the function app is running
- Check Application Insights for execution logs

### Authentication errors
- Ensure Managed Identity is enabled
- Verify role assignments
- Check environment variables are set correctly

### No environments found
- Verify DevCenter and project names
- Check API permissions
- Review DevCenter API version compatibility

### Slack notifications not sending
- Verify webhook URL is correct
- Check webhook is active in Slack
- Review function logs for HTTP errors

## API Reference

Using [DevCenter REST API](https://learn.microsoft.com/en-us/rest/api/devcenter/developer/environments/list-environments-by-user?view=rest-devcenter-developer-2024-02-01)

Endpoint: `https://{devCenter}.devcenter.azure.com/projects/{projectName}/users/me/environments`

## License

Part of the ADE Enterprise Extensions solution.
