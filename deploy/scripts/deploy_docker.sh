#!/bin/bash
# Sensor Fuzzing Framework Docker Deployment Script
# This script provides automated deployment for the sensor fuzzing framework using Docker

set -e

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DOCKER_COMPOSE_FILE="${PROJECT_ROOT}/deploy/docker-compose.yml"
DOCKERFILE="${PROJECT_ROOT}/deploy/Dockerfile"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker first."
        exit 1
    fi

    # Check if Docker Compose is available
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_error "Docker Compose is not available. Please install Docker Compose."
        exit 1
    fi

    # Check if docker-compose.yml exists
    if [ ! -f "$DOCKER_COMPOSE_FILE" ]; then
        log_error "docker-compose.yml not found at $DOCKER_COMPOSE_FILE"
        exit 1
    fi

    log_success "Prerequisites check passed"
}

# Build Docker images
build_images() {
    log_info "Building Docker images..."

    cd "$PROJECT_ROOT"

    if command -v docker-compose &> /dev/null; then
        docker-compose -f "$DOCKER_COMPOSE_FILE" build --no-cache
    else
        docker compose -f "$DOCKER_COMPOSE_FILE" build --no-cache
    fi

    log_success "Docker images built successfully"
}

# Start services
start_services() {
    local profile="${1:-}"

    log_info "Starting services..."

    cd "$PROJECT_ROOT"

    if [ -n "$profile" ]; then
        if command -v docker-compose &> /dev/null; then
            docker-compose -f "$DOCKER_COMPOSE_FILE" --profile "$profile" up -d
        else
            docker compose -f "$DOCKER_COMPOSE_FILE" --profile "$profile" up -d
        fi
    else
        if command -v docker-compose &> /dev/null; then
            docker-compose -f "$DOCKER_COMPOSE_FILE" up -d
        else
            docker compose -f "$DOCKER_COMPOSE_FILE" up -d
        fi
    fi

    log_success "Services started successfully"
}

# Stop services
stop_services() {
    log_info "Stopping services..."

    cd "$PROJECT_ROOT"

    if command -v docker-compose &> /dev/null; then
        docker-compose -f "$DOCKER_COMPOSE_FILE" down
    else
        docker compose -f "$DOCKER_COMPOSE_FILE" down
    fi

    log_success "Services stopped successfully"
}

# Show status
show_status() {
    log_info "Service status:"

    cd "$PROJECT_ROOT"

    if command -v docker-compose &> /dev/null; then
        docker-compose -f "$DOCKER_COMPOSE_FILE" ps
    else
        docker compose -f "$DOCKER_COMPOSE_FILE" ps
    fi
}

# Show logs
show_logs() {
    local service="${1:-}"
    local follow="${2:-false}"

    cd "$PROJECT_ROOT"

    if [ "$follow" = "true" ]; then
        if command -v docker-compose &> /dev/null; then
            docker-compose -f "$DOCKER_COMPOSE_FILE" logs -f ${service:+--tail=100 "$service"}
        else
            docker compose -f "$DOCKER_COMPOSE_FILE" logs -f ${service:+"$service"}
        fi
    else
        if command -v docker-compose &> /dev/null; then
            docker-compose -f "$DOCKER_COMPOSE_FILE" logs --tail=100 ${service:+"$service"}
        else
            docker compose -f "$DOCKER_COMPOSE_FILE" logs --tail=100 ${service:+"$service"}
        fi
    fi
}

# Clean up
cleanup() {
    log_info "Cleaning up..."

    cd "$PROJECT_ROOT"

    # Stop and remove containers
    if command -v docker-compose &> /dev/null; then
        docker-compose -f "$DOCKER_COMPOSE_FILE" down -v --remove-orphans
    else
        docker compose -f "$DOCKER_COMPOSE_FILE" down -v --remove-orphans
    fi

    # Remove unused images
    docker image prune -f

    # Remove unused volumes
    docker volume prune -f

    log_success "Cleanup completed"
}

# Health check
health_check() {
    log_info "Performing health check..."

    # Wait for services to be healthy
    local max_attempts=30
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        if curl -f http://localhost:8080/api/health &> /dev/null; then
            log_success "Health check passed"
            return 0
        fi

        log_info "Waiting for services to be healthy (attempt $attempt/$max_attempts)..."
        sleep 10
        ((attempt++))
    done

    log_error "Health check failed after $max_attempts attempts"
    return 1
}

# Main function
main() {
    local command="${1:-help}"
    local profile=""
    local service=""
    local follow="false"

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --profile)
                profile="$2"
                shift 2
                ;;
            --service)
                service="$2"
                shift 2
                ;;
            --follow)
                follow="true"
                shift
                ;;
            *)
                command="$1"
                shift
                ;;
        esac
    done

    case $command in
        build)
            check_prerequisites
            build_images
            ;;
        start)
            check_prerequisites
            start_services "$profile"
            health_check
            ;;
        stop)
            stop_services
            ;;
        restart)
            stop_services
            sleep 5
            start_services "$profile"
            health_check
            ;;
        status)
            show_status
            ;;
        logs)
            show_logs "$service" "$follow"
            ;;
        cleanup)
            cleanup
            ;;
        deploy)
            check_prerequisites
            build_images
            start_services "$profile"
            health_check
            ;;
        help|*)
            echo "Sensor Fuzzing Framework Docker Deployment Script"
            echo ""
            echo "Usage: $0 <command> [options]"
            echo ""
            echo "Commands:"
            echo "  build          Build Docker images"
            echo "  start          Start services"
            echo "  stop           Stop services"
            echo "  restart        Restart services"
            echo "  status         Show service status"
            echo "  logs           Show service logs"
            echo "  cleanup        Clean up containers and volumes"
            echo "  deploy         Full deployment (build + start + health check)"
            echo "  help           Show this help message"
            echo ""
            echo "Options:"
            echo "  --profile <profile>  Docker Compose profile (e.g., dev)"
            echo "  --service <service>  Specific service for logs command"
            echo "  --follow             Follow logs output"
            echo ""
            echo "Examples:"
            echo "  $0 deploy"
            echo "  $0 start --profile dev"
            echo "  $0 logs --service sensor-fuzz --follow"
            ;;
    esac
}

# Run main function with all arguments
main "$@"