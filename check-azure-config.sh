#!/bin/bash
# CRITICAL FIX CHECKLIST FOR BADGATEWAY ERROR
# Run these commands to verify your Azure Function App settings

FUNCTION_APP_NAME="$1"
RESOURCE_GROUP="$2"

if [ -z "$FUNCTION_APP_NAME" ] || [ -z "$RESOURCE_GROUP" ]; then
    echo "Usage: $0 <function-app-name> <resource-group>"
    exit 1
fi

echo "🔍 Checking Azure Function App Configuration..."
echo "=============================================="

# 1. Check Python version
echo ""
echo "1️⃣  Checking PYTHON VERSION:"
PYTHON_VERSION=$(az functionapp config show --name "$FUNCTION_APP_NAME" --resource-group "$RESOURCE_GROUP" --query "linuxFxVersion" -o tsv 2>/dev/null)
echo "   Current: $PYTHON_VERSION"
echo "   Required: Python|3.9, Python|3.10, or Python|3.11"
if [[ ! "$PYTHON_VERSION" =~ Python\|3\.(9|10|11) ]]; then
    echo "   ❌ ISSUE: Wrong Python version!"
    echo "   FIX: az functionapp config set --name '$FUNCTION_APP_NAME' --resource-group '$RESOURCE_GROUP' --linux-fx-version 'Python|3.11'"
fi

# 2. Check runtime
echo ""
echo "2️⃣  Checking FUNCTIONS_WORKER_RUNTIME:"
RUNTIME=$(az functionapp config appsettings list --name "$FUNCTION_APP_NAME" --resource-group "$RESOURCE_GROUP" --query "[?name=='FUNCTIONS_WORKER_RUNTIME'].value" -o tsv 2>/dev/null)
echo "   Current: $RUNTIME"
if [ "$RUNTIME" != "python" ]; then
    echo "   ❌ ISSUE: Runtime not set to 'python'!"
    echo "   FIX: az functionapp config appsettings set --name '$FUNCTION_APP_NAME' --resource-group '$RESOURCE_GROUP' --settings 'FUNCTIONS_WORKER_RUNTIME=python'"
fi

# 3. Check extension version
echo ""
echo "3️⃣  Checking FUNCTIONS_EXTENSION_VERSION:"
EXT_VERSION=$(az functionapp config appsettings list --name "$FUNCTION_APP_NAME" --resource-group "$RESOURCE_GROUP" --query "[?name=='FUNCTIONS_EXTENSION_VERSION'].value" -o tsv 2>/dev/null)
echo "   Current: $EXT_VERSION"
echo "   Required: ~4"
if [ "$EXT_VERSION" != "~4" ]; then
    echo "   ⚠️  WARNING: Should be ~4"
    echo "   FIX: az functionapp config appsettings set --name '$FUNCTION_APP_NAME' --resource-group '$RESOURCE_GROUP' --settings 'FUNCTIONS_EXTENSION_VERSION=~4'"
fi

# 4. Check build settings
echo ""
echo "4️⃣  Checking BUILD FLAGS:"
BUILD_FLAGS=$(az functionapp config appsettings list --name "$FUNCTION_APP_NAME" --resource-group "$RESOURCE_GROUP" --query "[?name=='SCM_DO_BUILD_DURING_DEPLOYMENT'].value" -o tsv 2>/dev/null)
echo "   SCM_DO_BUILD_DURING_DEPLOYMENT: ${BUILD_FLAGS:-'not set (default: true)'}"

ENABLE_ORYX=$(az functionapp config appsettings list --name "$FUNCTION_APP_NAME" --resource-group "$RESOURCE_GROUP" --query "[?name=='ENABLE_ORYX_BUILD'].value" -o tsv 2>/dev/null)
echo "   ENABLE_ORYX_BUILD: ${ENABLE_ORYX:-'not set (default: true)'}"

# 5. Check required env vars
echo ""
echo "5️⃣  Checking REQUIRED ENVIRONMENT VARIABLES:"
ADE_SUB=$(az functionapp config appsettings list --name "$FUNCTION_APP_NAME" --resource-group "$RESOURCE_GROUP" --query "[?name=='ADE_SUBSCRIPTION_ID'].value" -o tsv 2>/dev/null)
echo "   ADE_SUBSCRIPTION_ID: ${ADE_SUB:0:8}... $([ -z "$ADE_SUB" ] && echo '❌ MISSING' || echo '✅')"

SLACK_URL=$(az functionapp config appsettings list --name "$FUNCTION_APP_NAME" --resource-group "$RESOURCE_GROUP" --query "[?name=='SLACK_WEBHOOK_URL'].value" -o tsv 2>/dev/null)
echo "   SLACK_WEBHOOK_URL: $([ -z "$SLACK_URL" ] && echo '❌ MISSING' || echo '✅ Set')"

echo ""
echo "=============================================="
echo ""
echo "📦 Now deploy with:"
echo "   az functionapp deployment source config-zip \\"
echo "     --resource-group '$RESOURCE_GROUP' \\"
echo "     --name '$FUNCTION_APP_NAME' \\"
echo "     --src function.zip \\"
echo "     --timeout 300"
