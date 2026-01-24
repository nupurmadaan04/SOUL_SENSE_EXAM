#!/bin/bash
# Deployment script for Soul Sense Backend - Production Environment
# Usage: ./deploy-production.sh [version]

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DEPLOYMENT_VERSION="${1:-$(date +%Y%m%d-%H%M%S)}"
BACKUP_DIR="./backups"
LOGS_DIR="./logs"
ROLLBACK_INFO_FILE=".rollback_info"

echo -e "${RED}======================================${NC}"
echo -e "${RED}Soul Sense - PRODUCTION Deployment${NC}"
echo -e "${RED}Version: $DEPLOYMENT_VERSION${NC}"
echo -e "${RED}======================================${NC}"

# Safety confirmation
echo -e "${YELLOW}WARNING: You are about to deploy to PRODUCTION!${NC}"
read -p "Are you sure you want to continue? (yes/no): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
    echo -e "${RED}Deployment cancelled.${NC}"
    exit 1
fi

# Check if .env.production exists
if [ ! -f ".env.production" ]; then
    echo -e "${RED}Error: .env.production not found!${NC}"
    echo -e "${YELLOW}Please copy .env.production.template to .env.production and configure it.${NC}"
    exit 1
fi

# Save current version for rollback
CURRENT_VERSION=""
if [ -f "$ROLLBACK_INFO_FILE" ]; then
    CURRENT_VERSION=$(cat "$ROLLBACK_INFO_FILE" | grep "DEPLOYMENT_VERSION" | cut -d'=' -f2)
fi

# Create necessary directories
echo -e "${YELLOW}Creating directories...${NC}"
mkdir -p "$BACKUP_DIR"
mkdir -p "$LOGS_DIR"

# Backup current database
echo -e "${YELLOW}Backing up database...${NC}"
BACKUP_FILE="$BACKUP_DIR/production_backup_$(date +%Y%m%d_%H%M%S).sql"
if docker ps | grep -q "soulsense-db-production"; then
    docker exec soulsense-db-production pg_dump -U ${SOULSENSE_DB_USER:-postgres} soulsense_production > "$BACKUP_FILE"
    echo -e "${GREEN}✓ Database backup created: $BACKUP_FILE${NC}"
    
    # Compress backup
    gzip "$BACKUP_FILE"
    echo -e "${GREEN}✓ Backup compressed${NC}"
fi

# Pull latest code (if in git repo)
if [ -d "../../.git" ]; then
    echo -e "${YELLOW}Pulling latest code...${NC}"
    git pull origin main
    COMMIT_HASH=$(git rev-parse --short HEAD)
    echo -e "${GREEN}✓ Code updated (commit: $COMMIT_HASH)${NC}"
fi

# Build new image
echo -e "${YELLOW}Building Docker images...${NC}"
DEPLOYMENT_VERSION=$DEPLOYMENT_VERSION \
PREVIOUS_VERSION=$CURRENT_VERSION \
docker-compose -f docker-compose.production.yml build --no-cache

# Save rollback information
echo "DEPLOYMENT_VERSION=$DEPLOYMENT_VERSION" > "$ROLLBACK_INFO_FILE"
echo "PREVIOUS_VERSION=$CURRENT_VERSION" >> "$ROLLBACK_INFO_FILE"
echo "DEPLOYMENT_TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$ROLLBACK_INFO_FILE"
echo "BACKUP_FILE=${BACKUP_FILE}.gz" >> "$ROLLBACK_INFO_FILE"

# Deploy with rolling update
echo -e "${YELLOW}Deploying new version...${NC}"
DEPLOYMENT_VERSION=$DEPLOYMENT_VERSION \
PREVIOUS_VERSION=$CURRENT_VERSION \
docker-compose -f docker-compose.production.yml up -d --no-deps --build api

# Wait for new containers to be healthy
echo -e "${YELLOW}Waiting for services to be healthy...${NC}"
sleep 15

# Health check with retries
MAX_RETRIES=60
RETRY_COUNT=0
HEALTH_CHECK_FAILED=false

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓ API is healthy!${NC}"
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo -e "${YELLOW}Waiting for API... ($RETRY_COUNT/$MAX_RETRIES)${NC}"
    sleep 2
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo -e "${RED}✗ API health check failed!${NC}"
    HEALTH_CHECK_FAILED=true
fi

# If health check failed, initiate rollback
if [ "$HEALTH_CHECK_FAILED" = true ]; then
    echo -e "${RED}======================================${NC}"
    echo -e "${RED}DEPLOYMENT FAILED - Initiating Rollback${NC}"
    echo -e "${RED}======================================${NC}"
    
    if [ ! -z "$CURRENT_VERSION" ]; then
        echo -e "${YELLOW}Rolling back to version: $CURRENT_VERSION${NC}"
        ./rollback-production.sh
    else
        echo -e "${RED}No previous version found for rollback!${NC}"
        echo -e "${YELLOW}Please check logs and fix manually.${NC}"
    fi
    
    exit 1
fi

# Verify deployment
echo -e "\n${BLUE}======================================${NC}"
echo -e "${BLUE}Verifying Deployment${NC}"
echo -e "${BLUE}======================================${NC}"

# Test endpoints
echo -e "${YELLOW}Testing API endpoints...${NC}"
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Health endpoint OK${NC}"
else
    echo -e "${RED}✗ Health endpoint failed${NC}"
fi

# Display service status
echo -e "\n${BLUE}Service Status:${NC}"
docker-compose -f docker-compose.production.yml ps

# Success
echo -e "\n${GREEN}======================================${NC}"
echo -e "${GREEN}Deployment Successful!${NC}"
echo -e "${GREEN}======================================${NC}"
echo -e "Version: ${GREEN}$DEPLOYMENT_VERSION${NC}"
echo -e "Previous Version: ${YELLOW}$CURRENT_VERSION${NC}"
echo -e "Timestamp: $(date)"
echo -e "\nBackup: ${BACKUP_FILE}.gz"
echo -e "\n${YELLOW}Rollback Info:${NC}"
cat "$ROLLBACK_INFO_FILE"

echo -e "\n${BLUE}Next Steps:${NC}"
echo -e "1. Monitor logs: docker-compose -f docker-compose.production.yml logs -f api"
echo -e "2. Check metrics and monitoring dashboards"
echo -e "3. If issues occur, run: ./rollback-production.sh"
echo -e "4. Keep backup file for at least 7 days"
