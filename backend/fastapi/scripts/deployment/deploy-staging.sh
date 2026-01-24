#!/bin/bash
# Deployment script for Soul Sense Backend - Staging Environment
# Usage: ./deploy-staging.sh [version]

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
DEPLOYMENT_VERSION="${1:-$(date +%Y%m%d-%H%M%S)}"
BACKUP_DIR="./backups"
LOGS_DIR="./logs"

echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}Soul Sense - Staging Deployment${NC}"
echo -e "${GREEN}Version: $DEPLOYMENT_VERSION${NC}"
echo -e "${GREEN}======================================${NC}"

# Check if .env.staging exists
if [ ! -f ".env.staging" ]; then
    echo -e "${RED}Error: .env.staging not found!${NC}"
    echo -e "${YELLOW}Please copy .env.staging.template to .env.staging and configure it.${NC}"
    exit 1
fi

# Create necessary directories
echo -e "${YELLOW}Creating directories...${NC}"
mkdir -p "$BACKUP_DIR"
mkdir -p "$LOGS_DIR"

# Backup current database (if exists)
echo -e "${YELLOW}Backing up database...${NC}"
BACKUP_FILE="$BACKUP_DIR/staging_backup_$(date +%Y%m%d_%H%M%S).sql"
if docker ps | grep -q "soulsense-db-staging"; then
    docker exec soulsense-db-staging pg_dump -U ${SOULSENSE_DB_USER:-postgres} soulsense_staging > "$BACKUP_FILE" 2>/dev/null || true
    echo -e "${GREEN}Database backup created: $BACKUP_FILE${NC}"
fi

# Pull latest code (if in git repo)
if [ -d "../../.git" ]; then
    echo -e "${YELLOW}Pulling latest code...${NC}"
    git pull origin main || echo -e "${YELLOW}Warning: Git pull failed or not in git repo${NC}"
fi

# Build and start services
echo -e "${YELLOW}Building Docker images...${NC}"
DEPLOYMENT_VERSION=$DEPLOYMENT_VERSION docker-compose -f docker-compose.staging.yml build --no-cache

echo -e "${YELLOW}Starting services...${NC}"
DEPLOYMENT_VERSION=$DEPLOYMENT_VERSION docker-compose -f docker-compose.staging.yml up -d

# Wait for services to be healthy
echo -e "${YELLOW}Waiting for services to be healthy...${NC}"
sleep 10

# Health check
MAX_RETRIES=30
RETRY_COUNT=0
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
    echo -e "${YELLOW}Checking logs...${NC}"
    docker-compose -f docker-compose.staging.yml logs --tail=50 api
    exit 1
fi

# Display service status
echo -e "\n${GREEN}======================================${NC}"
echo -e "${GREEN}Deployment Status${NC}"
echo -e "${GREEN}======================================${NC}"
docker-compose -f docker-compose.staging.yml ps

# Show logs
echo -e "\n${YELLOW}Recent logs:${NC}"
docker-compose -f docker-compose.staging.yml logs --tail=20 api

echo -e "\n${GREEN}======================================${NC}"
echo -e "${GREEN}Deployment Successful!${NC}"
echo -e "${GREEN}Version: $DEPLOYMENT_VERSION${NC}"
echo -e "${GREEN}======================================${NC}"
echo -e "\nAPI URL: http://localhost:8000"
echo -e "API Docs: http://localhost:8000/docs"
echo -e "\nTo view logs: docker-compose -f docker-compose.staging.yml logs -f"
echo -e "To stop: docker-compose -f docker-compose.staging.yml down"
