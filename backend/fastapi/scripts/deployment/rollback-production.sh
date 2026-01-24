#!/bin/bash
# Rollback script for Soul Sense Backend - Production Environment
# Usage: ./rollback-production.sh [version]

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

ROLLBACK_INFO_FILE=".rollback_info"

echo -e "${RED}======================================${NC}"
echo -e "${RED}Soul Sense - PRODUCTION ROLLBACK${NC}"
echo -e "${RED}======================================${NC}"

# Check if rollback info exists
if [ ! -f "$ROLLBACK_INFO_FILE" ]; then
    echo -e "${RED}Error: Rollback information not found!${NC}"
    echo -e "${YELLOW}Cannot determine previous version.${NC}"
    exit 1
fi

# Load rollback information
source "$ROLLBACK_INFO_FILE"

# Determine version to rollback to
ROLLBACK_VERSION="${1:-$PREVIOUS_VERSION}"

if [ -z "$ROLLBACK_VERSION" ]; then
    echo -e "${RED}Error: No previous version specified!${NC}"
    echo -e "${YELLOW}Usage: ./rollback-production.sh [version]${NC}"
    exit 1
fi

echo -e "${YELLOW}Current Version: $DEPLOYMENT_VERSION${NC}"
echo -e "${YELLOW}Rolling back to: $ROLLBACK_VERSION${NC}"

# Safety confirmation
echo -e "\n${RED}WARNING: You are about to ROLLBACK PRODUCTION!${NC}"
read -p "Continue rollback to version $ROLLBACK_VERSION? (yes/no): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
    echo -e "${RED}Rollback cancelled.${NC}"
    exit 1
fi

# Stop current version
echo -e "${YELLOW}Stopping current deployment...${NC}"
docker-compose -f docker-compose.production.yml down --remove-orphans

# Restore from backup if specified
if [ ! -z "$BACKUP_FILE" ] && [ -f "$BACKUP_FILE" ]; then
    echo -e "${YELLOW}Database backup available: $BACKUP_FILE${NC}"
    read -p "Restore database from backup? (yes/no): " RESTORE_DB
    
    if [ "$RESTORE_DB" = "yes" ]; then
        echo -e "${YELLOW}Restoring database...${NC}"
        
        # Decompress if needed
        if [[ "$BACKUP_FILE" == *.gz ]]; then
            gunzip -c "$BACKUP_FILE" > "${BACKUP_FILE%.gz}"
            BACKUP_SQL="${BACKUP_FILE%.gz}"
        else
            BACKUP_SQL="$BACKUP_FILE"
        fi
        
        # Start database
        docker-compose -f docker-compose.production.yml up -d db
        sleep 10
        
        # Restore backup
        docker exec -i soulsense-db-production psql -U ${SOULSENSE_DB_USER:-postgres} soulsense_production < "$BACKUP_SQL"
        echo -e "${GREEN}✓ Database restored from backup${NC}"
    fi
fi

# Deploy previous version
echo -e "${YELLOW}Deploying version $ROLLBACK_VERSION...${NC}"
DEPLOYMENT_VERSION=$ROLLBACK_VERSION \
docker-compose -f docker-compose.production.yml up -d

# Wait for services
echo -e "${YELLOW}Waiting for services to start...${NC}"
sleep 15

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
    echo -e "${RED}✗ Rollback health check failed!${NC}"
    echo -e "${YELLOW}Checking logs...${NC}"
    docker-compose -f docker-compose.production.yml logs --tail=50 api
    exit 1
fi

# Update rollback info
echo "DEPLOYMENT_VERSION=$ROLLBACK_VERSION" > "$ROLLBACK_INFO_FILE"
echo "ROLLBACK_TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$ROLLBACK_INFO_FILE"
echo "ROLLBACK_FROM=$DEPLOYMENT_VERSION" >> "$ROLLBACK_INFO_FILE"

# Display status
echo -e "\n${GREEN}======================================${NC}"
echo -e "${GREEN}Rollback Successful!${NC}"
echo -e "${GREEN}======================================${NC}"
echo -e "Rolled back to version: ${GREEN}$ROLLBACK_VERSION${NC}"
echo -e "From version: ${RED}$DEPLOYMENT_VERSION${NC}"
echo -e "Timestamp: $(date)"

echo -e "\n${YELLOW}Service Status:${NC}"
docker-compose -f docker-compose.production.yml ps

echo -e "\n${YELLOW}Recent logs:${NC}"
docker-compose -f docker-compose.production.yml logs --tail=20 api

echo -e "\n${RED}IMPORTANT:${NC}"
echo -e "1. Investigate the cause of the rollback"
echo -e "2. Monitor logs for any issues"
echo -e "3. Notify team about the rollback"
echo -e "4. Fix issues before attempting redeployment"
