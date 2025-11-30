#!/bin/bash
set -e

# Azure Function App Deployment Script
# This deploys ONLY the expirationRunNow function (not the entire /src/functions directory)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Deploying expirationRunNow Function${NC}"
echo -e "${GREEN}========================================${NC}"

# Check if required commands are available
if ! command -v az &> /dev/null; then
    echo -e "${RED}ERROR: Azure CLI (az) is not installed${NC}"
    exit 1
fi

# Get parameters
RESOURCE_GROUP="${1}"
FUNCTION_APP_NAME="${2}"

if [ -z "$RESOURCE_GROUP" ] || [ -z "$FUNCTION_APP_NAME" ]; then
    echo -e "${YELLOW}Usage: $0 <resource-group> <function-app-name>${NC}"
    echo ""
    echo "Example:"
    echo "  $0 my-rg my-function-app"
    exit 1
fi

# Get the script directory (expirationRunNow)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo -e "${YELLOW}Cleaning up old deployment artifacts...${NC}"
rm -f function.zip

echo -e "${YELLOW}Creating deployment package...${NC}"
# Exclude unnecessary files
zip -r function.zip . \
    -x "*.git*" \
    -x "*__pycache__*" \
    -x "*.pyc" \
    -x ".env*" \
    -x "venv/*" \
    -x "demo_*" \
    -x "test_*" \
    -x "*.DS_Store" \
    -x "deploy.sh" \
    -x "exec.sh" \
    -x "*.md" \
    -x "Dockerfile" \
    -x ".dockerignore" \
    -x ".funcignore"

echo -e "${YELLOW}Deploying to Azure...${NC}"
az functionapp deployment source config-zip \
    --resource-group "$RESOURCE_GROUP" \
    --name "$FUNCTION_APP_NAME" \
    --src function.zip \
    --timeout 300

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}✅ Deployment successful!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo "Function App: $FUNCTION_APP_NAME"
    echo "Resource Group: $RESOURCE_GROUP"
    echo ""
    echo "Next steps:"
    echo "1. Verify environment variables are set in Azure Portal:"
    echo "   - ADE_SUBSCRIPTION_ID"
    echo "   - SLACK_WEBHOOK_URL"
    echo ""
    echo "2. Grant the function app's managed identity 'Reader' role:"
    echo "   az role assignment create \\"
    echo "     --assignee <function-app-principal-id> \\"
    echo "     --role 'Reader' \\"
    echo "     --scope '/subscriptions/$ADE_SUBSCRIPTION_ID'"
    echo ""
    echo "3. Monitor function in Azure Portal:"
    echo "   https://portal.azure.com/#resource/subscriptions/YOUR-SUB/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.Web/sites/$FUNCTION_APP_NAME"
else
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}❌ Deployment failed!${NC}"
    echo -e "${RED}========================================${NC}"
    exit 1
fi
