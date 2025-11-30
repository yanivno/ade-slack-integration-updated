#!/bin/bash

# Assign permissions to Function App managed identity for DevCenter access

FUNCTION_APP_NAME="expiration-date-slack-notifier"
RESOURCE_GROUP="jfrog-ade"
SUBSCRIPTION_ID="c64fd005-b880-4802-9aa8-2dcc75068a20"
DEVCENTER_PROJECT_NAME="ade-sandbox-project"
DEVCENTER_RG="ade-sandbox-rg"

echo "🔍 Getting Function App managed identity principal ID..."
PRINCIPAL_ID=$(az functionapp identity show \
    --name $FUNCTION_APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --query principalId \
    --output tsv)

if [ -z "$PRINCIPAL_ID" ]; then
    echo "❌ No managed identity found. Enabling system-assigned identity..."
    az functionapp identity assign \
        --name $FUNCTION_APP_NAME \
        --resource-group $RESOURCE_GROUP
    
    PRINCIPAL_ID=$(az functionapp identity show \
        --name $FUNCTION_APP_NAME \
        --resource-group $RESOURCE_GROUP \
        --query principalId \
        --output tsv)
fi

echo "✅ Principal ID: $PRINCIPAL_ID"

# Get the DevCenter resource ID
echo "🔍 Getting DevCenter resource ID..."
DEVCENTER_ID=$(az resource list \
    --resource-group $DEVCENTER_RG \
    --resource-type "Microsoft.DevCenter/devcenters" \
    --query "[0].id" \
    --output tsv)

echo "✅ DevCenter ID: $DEVCENTER_ID"

# Assign Contributor role on the subscription (for listing DevCenters and projects)
echo "📋 Assigning Reader role on subscription..."
az role assignment create \
    --assignee $PRINCIPAL_ID \
    --role "Reader" \
    --scope "/subscriptions/$SUBSCRIPTION_ID"

# Assign DevCenter Dev Box User or Deployment Environments User role on the DevCenter
echo "📋 Assigning Deployment Environments User role on DevCenter..."
az role assignment create \
    --assignee $PRINCIPAL_ID \
    --role "Deployment Environments User" \
    --scope $DEVCENTER_ID

# Also try assigning on the project level
PROJECT_ID="/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$DEVCENTER_RG/providers/Microsoft.DevCenter/projects/$DEVCENTER_PROJECT_NAME"
echo "📋 Assigning Deployment Environments User role on Project..."
az role assignment create \
    --assignee $PRINCIPAL_ID \
    --role "Deployment Environments User" \
    --scope $PROJECT_ID

echo "✅ Permissions assigned successfully!"
echo "⏳ Wait 5-10 minutes for permissions to propagate, then restart the function app:"
echo "   az functionapp restart --name $FUNCTION_APP_NAME --resource-group $RESOURCE_GROUP"
