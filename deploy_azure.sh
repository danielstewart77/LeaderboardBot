#!/bin/bash

# deploy_azure.sh
# Automates build/push to Azure Container Registry (ACR) and updates Azure Container Apps.

# --- Configuration ---
ACR_NAME="warriorleaderboardregistry"
RESOURCE_GROUP="Personal_Fun"

BOT_IMAGE_NAME="leaderboardbot/bot"
API_IMAGE_NAME="leaderboardbot/api"
IMAGE_TAG=$(date +%Y%m%d-%H%M%S)  # ⬅️ Dynamic tag per deploy

EXISTING_BOT_CONTAINER_APP_NAME="leaderboard-bot-container"
EXISTING_API_CONTAINER_APP_NAME="leaderboard-api-container"

# --- Verify Configuration ---
if [[ "${ACR_NAME}" == "YOUR_ACR_NAME" || "${RESOURCE_GROUP}" == "YOUR_RESOURCE_GROUP" ]]; then
    echo "ERROR: Replace ACR_NAME and RESOURCE_GROUP in the script."
    exit 1
fi

echo "--- Starting Azure Deployment ---"
echo "🕓 Using image tag: ${IMAGE_TAG}"

# --- Azure CLI Login ---
if ! az account show > /dev/null 2>&1; then
    az login
else
    echo "✅ Already logged into Azure CLI."
fi

# --- ACR Login ---
echo "🔐 Logging into ACR..."
az acr login --name "${ACR_NAME}" || {
    echo "❌ Failed to login to ACR."
    exit 1
}

# --- Build and Push Bot Image ---
echo "🐳 Building Bot Docker Image..."
docker build -t "${ACR_NAME}.azurecr.io/${BOT_IMAGE_NAME}:${IMAGE_TAG}" -f Dockerfile.bot . || {
    echo "❌ Docker build failed for bot."
    exit 1
}

echo "📤 Pushing Bot Image..."
docker push "${ACR_NAME}.azurecr.io/${BOT_IMAGE_NAME}:${IMAGE_TAG}" || {
    echo "❌ Docker push failed for bot."
    exit 1
}

# --- Update Bot Container App ---
echo "🚀 Updating Bot Container App..."
az containerapp update \
  --name "${EXISTING_BOT_CONTAINER_APP_NAME}" \
  --resource-group "${RESOURCE_GROUP}" \
  --image "${ACR_NAME}.azurecr.io/${BOT_IMAGE_NAME}:${IMAGE_TAG}" \
  --min-replicas 1 \
  --max-replicas 1 \
  --revision-suffix "${IMAGE_TAG}" || {
    echo "❌ Failed to update bot container app."
}

# --- Build and Push API Image ---
echo "🐳 Building API Docker Image..."
docker build -t "${ACR_NAME}.azurecr.io/${API_IMAGE_NAME}:${IMAGE_TAG}" -f Dockerfile.api . || {
    echo "❌ Docker build failed for API."
    exit 1
}

echo "📤 Pushing API Image..."
docker push "${ACR_NAME}.azurecr.io/${API_IMAGE_NAME}:${IMAGE_TAG}" || {
    echo "❌ Docker push failed for API."
    exit 1
}

# --- Update API Container App ---
echo "🚀 Updating API Container App..."
az containerapp update \
  --name "${EXISTING_API_CONTAINER_APP_NAME}" \
  --resource-group "${RESOURCE_GROUP}" \
  --image "${ACR_NAME}.azurecr.io/${API_IMAGE_NAME}:${IMAGE_TAG}" \
  --min-replicas 1 \
  --max-replicas 3 \
  --revision-suffix "${IMAGE_TAG}" || {
    echo "❌ Failed to update API container app."
}

# --- Check Status ---
echo "🔍 Verifying Container Status..."

echo "📦 Bot Container:"
az containerapp revision list \
  --name "${EXISTING_BOT_CONTAINER_APP_NAME}" \
  --resource-group "${RESOURCE_GROUP}" \
  --query "[0].{name:name,active:properties.active,healthy:properties.healthState,replicas:properties.replicas}" \
  --output table

echo "📦 API Container:"
az containerapp revision list \
  --name "${EXISTING_API_CONTAINER_APP_NAME}" \
  --resource-group "${RESOURCE_GROUP}" \
  --query "[0].{name:name,active:properties.active,healthy:properties.healthState,replicas:properties.replicas}" \
  --output table

# --- Optional: Restart Revisions ---
echo "🔁 Restarting Active Revisions..."

BOT_REVISION=$(az containerapp revision list \
  --name "${EXISTING_BOT_CONTAINER_APP_NAME}" \
  --resource-group "${RESOURCE_GROUP}" \
  --query "[?properties.active].{name:name}[0].name" \
  --output tsv)

if [ -n "$BOT_REVISION" ]; then
  echo "Restarting bot: $BOT_REVISION"
  az containerapp revision restart \
    --name "${EXISTING_BOT_CONTAINER_APP_NAME}" \
    --resource-group "${RESOURCE_GROUP}" \
    --revision "$BOT_REVISION"
fi

API_REVISION=$(az containerapp revision list \
  --name "${EXISTING_API_CONTAINER_APP_NAME}" \
  --resource-group "${RESOURCE_GROUP}" \
  --query "[?properties.active].{name:name}[0].name" \
  --output tsv)

if [ -n "$API_REVISION" ]; then
  echo "Restarting API: $API_REVISION"
  az containerapp revision restart \
    --name "${EXISTING_API_CONTAINER_APP_NAME}" \
    --resource-group "${RESOURCE_GROUP}" \
    --revision "$API_REVISION"
fi

echo "✅ Deployment Complete"
echo "📋 Monitor logs: az containerapp logs show --name <app-name> --resource-group ${RESOURCE_GROUP} --follow"
