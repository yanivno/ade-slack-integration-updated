# Variables
RG="jfrog-ade"
LOCATION="eastus"
STORAGE="jfrogade92d6"
FUNC_NAME="expiration-date-slack-notifier"

# 1. Create resource group (if needed)
az group create --name $RG --location $LOCATION

# # 2. Create storage account (required for function app)
# az storage account create \
#   --name $STORAGE \
#   --resource-group $RG \
#   --location $LOCATION \
#   --sku Standard_LRS

# 3. Create Flex Consumption function app
az functionapp create \
  --resource-group $RG \
  --name $FUNC_NAME \
  --storage-account $STORAGE \
  --flexconsumption-location $LOCATION \
  --runtime python \
  --runtime-version 3.11 \
  --functions-version 4

# 4. Enable system-assigned managed identity
az functionapp identity assign \
  --name $FUNC_NAME \
  --resource-group $RG

# 5. Configure app settings
az functionapp config appsettings set \
  --name $FUNC_NAME \
  --resource-group $RG \
  --settings \
    ADE_SUBSCRIPTION_ID="c64fd005-b880-4802-9aa8-2dcc75068a20" \
    SLACK_WEBHOOK_URL="ttps://hooks.slack.com/services/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" \
    SLACK_MOCK="0"

# 6. Grant Reader role to managed identity
IDENTITY_ID=$(az functionapp identity show -n $FUNC_NAME -g $RG --query principalId -o tsv)
az role assignment create \
  --assignee $IDENTITY_ID \
  --role "Reader" \
  --scope /subscriptions/c64fd005-b880-4802-9aa8-2dcc75068a20