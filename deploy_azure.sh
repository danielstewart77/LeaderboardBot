#!/bin/bash

# deploy_azure.sh
# This script automates building and pushing Docker images to Azure Container Registry (ACR)
# and updating existing Azure Container Apps for both the bot and the API.

# --- Configuration Variables (IMPORTANT: Update if necessary!) ---
ACR_NAME="warriorleaderboardregistry"
RESOURCE_GROUP="Personal_Fun"

BOT_IMAGE_NAME="leaderboardbot/bot"       # Image name for the bot in ACR
API_IMAGE_NAME="leaderboardbot/api"       # Image name for the API in ACR
IMAGE_TAG="latest"                        # Or a specific version tag, e.g., "1.0.0"

# Existing Container App names in Azure
EXISTING_BOT_CONTAINER_APP_NAME="leaderboard-bot-container"
EXISTING_API_CONTAINER_APP_NAME="leaderboard-api-container" # New variable for the API app

# --- Safety Check for Placeholders (Adjust if you have different default placeholders) ---
if [[ "${ACR_NAME}" == "YOUR_ACR_NAME" || "${RESOURCE_GROUP}" == "YOUR_RESOURCE_GROUP" ]]; then
    echo "ERROR: Please replace placeholder values for ACR_NAME and RESOURCE_GROUP in this script before running."
    exit 1
fi

echo "--- Starting Azure Deployment Script ---"

# --- Azure Authentication ---
echo "
--- Step 1: Azure CLI Login ---"
echo "If you are not already logged in, a browser window will open for authentication."
if ! az account show > /dev/null 2>&1; then
    az login
else
    echo "Already logged into Azure CLI."
fi

echo "
--- Step 2: Azure Container Registry (ACR) Login ---"
az acr login --name "${ACR_NAME}"
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to login to ACR. Please check your ACR name and Azure permissions."
    exit 1
fi
echo "Successfully logged into ACR: ${ACR_NAME}"

# --- Build and Push Discord Bot Image ---
echo "
--- Step 3: Building Discord Bot Docker Image ---"
echo "Image will be tagged as: ${ACR_NAME}.azurecr.io/${BOT_IMAGE_NAME}:${IMAGE_TAG}"
docker build -t "${ACR_NAME}.azurecr.io/${BOT_IMAGE_NAME}:${IMAGE_TAG}" -f Dockerfile.bot .
if [ $? -ne 0 ]; then
    echo "ERROR: Docker build for Bot failed."
    exit 1
fi
echo "Bot image built successfully."

echo "
--- Step 4: Pushing Discord Bot Image to ACR ---"
docker push "${ACR_NAME}.azurecr.io/${BOT_IMAGE_NAME}:${IMAGE_TAG}"
if [ $? -ne 0 ]; then
    echo "ERROR: Docker push for Bot image failed."
    exit 1
fi
echo "Bot image pushed to ACR successfully."

# --- Update Existing Bot Container App ---
echo "
--- Step 5: Updating Azure Container App '${EXISTING_BOT_CONTAINER_APP_NAME}' for the Bot ---"
az containerapp update --name "${EXISTING_BOT_CONTAINER_APP_NAME}" --resource-group "${RESOURCE_GROUP}" --image "${ACR_NAME}.azurecr.io/${BOT_IMAGE_NAME}:${IMAGE_TAG}"
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to update Container App '${EXISTING_BOT_CONTAINER_APP_NAME}'."
    echo "Please ensure the app exists, the resource group is correct, and you have permissions."
    # exit 1 # Consider if you want to halt on failure
else
    echo "Container App '${EXISTING_BOT_CONTAINER_APP_NAME}' updated successfully to use the new bot image."
fi
echo "REMINDER: For '${EXISTING_BOT_CONTAINER_APP_NAME}', ensure LEADERBOARDBOT_TOKEN (secret) and API_BASE_URL environment variables are set correctly in the Azure Portal."

# --- Build and Push FastAPI API Image ---
echo "
--- Step 6: Building FastAPI API Docker Image ---"
echo "Image will be tagged as: ${ACR_NAME}.azurecr.io/${API_IMAGE_NAME}:${IMAGE_TAG}"
docker build -t "${ACR_NAME}.azurecr.io/${API_IMAGE_NAME}:${IMAGE_TAG}" -f Dockerfile.api .
if [ $? -ne 0 ]; then
    echo "ERROR: Docker build for API failed."
    exit 1
fi
echo "API image built successfully."

echo "
--- Step 7: Pushing FastAPI API Image to ACR ---"
docker push "${ACR_NAME}.azurecr.io/${API_IMAGE_NAME}:${IMAGE_TAG}"
if [ $? -ne 0 ]; then
    echo "ERROR: Docker push for API image failed."
    exit 1
fi
echo "API image pushed to ACR successfully."

# --- Update Existing API Container App ---
echo "
--- Step 8: Updating Azure Container App '${EXISTING_API_CONTAINER_APP_NAME}' for the API ---"
az containerapp update --name "${EXISTING_API_CONTAINER_APP_NAME}" --resource-group "${RESOURCE_GROUP}" --image "${ACR_NAME}.azurecr.io/${API_IMAGE_NAME}:${IMAGE_TAG}"
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to update Container App '${EXISTING_API_CONTAINER_APP_NAME}'."
    echo "Please ensure the app exists, the resource group is correct, and you have permissions."
    # exit 1 # Consider if you want to halt on failure
else
    echo "Container App '${EXISTING_API_CONTAINER_APP_NAME}' updated successfully to use the new API image."
fi
echo "REMINDER: For '${EXISTING_API_CONTAINER_APP_NAME}', ensure PostgreSQL connection variables (POSTGRES_HOST, _USER, _PASSWORD as secret, _DB, _PORT) and RUN_DISCORD_BOT=0 are set correctly in the Azure Portal."
echo "Once '${EXISTING_API_CONTAINER_APP_NAME}' is updated and running, note its Application URL."


# --- Final Reminders ---
echo "
--- Step 9: Verify API URL for Bot App ---"
echo "After the '${EXISTING_API_CONTAINER_APP_NAME}' (API) Container App is updated and you have confirmed its Application URL,"
echo "you MUST ensure the 'API_BASE_URL' environment variable for the '${EXISTING_BOT_CONTAINER_APP_NAME}' (Bot) Container App is correctly set to this URL."
echo "If it needs changing, you can update it via the Azure Portal or using a command like:"
echo "  az containerapp update --name ${EXISTING_BOT_CONTAINER_APP_NAME} --resource-group ${RESOURCE_GROUP} --set-env-vars API_BASE_URL=https://your-api-app-url.azurecontainerapps.io"

echo "
--- Azure Deployment Script Finished ---"
