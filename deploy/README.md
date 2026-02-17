# Sensor Fuzzing Framework - Docker Deployment

This directory contains Docker configuration and deployment scripts for the Sensor Fuzzing Framework.

## Directory Structure

```
deploy/
|-- Dockerfile                    # Multi-stage Docker build configuration
|-- docker-compose.yml           # Docker Compose orchestration
|-- prometheus.yml              # Prometheus monitoring configuration
|-- grafana/                    # Grafana dashboard configurations
|   `-- provisioning/
|       |-- datasources/        # Data source configurations
|       `-- dashboards/         # Dashboard configurations
|-- k8s/                        # Kubernetes deployment manifests
`-- scripts/                    # Deployment automation scripts
   |-- deploy_docker.sh        # Docker deployment script
   |-- deploy_k8s.sh          # Kubernetes deployment script
   |-- deploy_linux.sh        # Linux native deployment
   |-- deploy_windows.ps1     # Windows native deployment
   `-- install_deps_linux.sh  # Linux dependency installation
```

## Quick Start

### Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+ (or docker-compose 1.29+)
- At least 4GB RAM available
- At least 10GB free disk space

### Deploy with Docker Compose

1. **Clone and navigate to the project:**
   ```bash
   cd /path/to/sensor-fuzzing-framework
   ```

2. **Deploy the full stack:**
   ```bash
   # Using the deployment script
   ./deploy/scripts/deploy_docker.sh deploy

   # Or manually with docker-compose
   docker-compose -f deploy/docker-compose.yml up -d
   ```

3. **Check deployment status:**
   ```bash
   ./deploy/scripts/deploy_docker.sh status
   ```

4. **View logs:**
   ```bash
   ./deploy/scripts/deploy_docker.sh logs --follow
   ```

### Access Services

After successful deployment, the following services will be available:

- **Sensor Fuzzing Framework Dashboard**: http://localhost:8080
- **Prometheus Metrics**: http://localhost:9090
- **Grafana Dashboards**: http://localhost:3000 (admin/admin)
- **Application Metrics Endpoint**: http://localhost:8000/metrics

## Development Deployment

For development with live code reloading:

```bash
# Start development environment
./deploy/scripts/deploy_docker.sh start --profile dev

# Or with docker-compose
docker-compose -f deploy/docker-compose.yml --profile dev up -d
```

The development environment mounts the source code and provides:
- Live code reloading
- Development dependencies installed
- Debug logging enabled
- Alternative ports (8081 for dashboard, 8001 for metrics)

## Configuration

### Environment Variables

The following environment variables can be configured:

- `PYTHONPATH=/app/src` - Python module path
- `SENSOR_FUZZ_CONFIG_PATH=/app/config` - Configuration directory
- `PROMETHEUS_MULTIPROC_DIR=/tmp/prometheus` - Prometheus metrics directory

### Volumes

Persistent data is stored in named volumes:
- `sensor-fuzz-data` - Application data
- `sensor-fuzz-logs` - Application logs
- `prometheus-data` - Prometheus metrics data
- `grafana-data` - Grafana dashboards and settings

## Monitoring and Observability

The deployment includes a complete monitoring stack:

### Prometheus
- Scrapes metrics from the sensor fuzzing application
- Stores time-series data for analysis
- Accessible at http://localhost:9090

### Grafana
- Provides visualization dashboards
- Pre-configured with sensor fuzzing metrics
- Default credentials: admin/admin
- Accessible at http://localhost:3000

### Application Metrics
The application exposes metrics at `/metrics` endpoint including:
- System resource usage (CPU, memory)
- Fuzzing operation statistics
- AI training progress
- Error rates and performance counters

## Deployment Scripts

### deploy_docker.sh

Comprehensive deployment script with the following commands:

```bash
# Build images
./deploy/scripts/deploy_docker.sh build

# Start services
./deploy/scripts/deploy_docker.sh start [--profile dev]

# Stop services
./deploy/scripts/deploy_docker.sh stop

# Restart services
./deploy/scripts/deploy_docker.sh restart [--profile dev]

# Show status
./deploy/scripts/deploy_docker.sh status

# Show logs
./deploy/scripts/deploy_docker.sh logs [--service <service>] [--follow]

# Full deployment
./deploy/scripts/deploy_docker.sh deploy

# Cleanup
./deploy/scripts/deploy_docker.sh cleanup
```

## Troubleshooting

### Common Issues

1. **Port conflicts**: Ensure ports 8000, 8080, 9090, 3000 are available
2. **Memory issues**: Increase Docker memory limit to at least 4GB
3. **Permission issues**: Ensure Docker daemon has access to project directory
4. **Health check failures**: Check logs with `./deploy/scripts/deploy_docker.sh logs`

### Health Checks

The deployment includes health checks for:
- Application startup
- Service availability
- Database connections
- External dependencies

### Logs

View logs for troubleshooting:

```bash
# All services
./deploy/scripts/deploy_docker.sh logs --follow

# Specific service
./deploy/scripts/deploy_docker.sh logs --service sensor-fuzz --follow

# With docker-compose directly
docker-compose -f deploy/docker-compose.yml logs -f sensor-fuzz
```

## Production Considerations

### Security
- Change default Grafana password
- Use secrets management for sensitive configuration
- Enable TLS/SSL in production
- Configure firewall rules

### Scaling
- Increase replica count in docker-compose.yml
- Use Docker Swarm or Kubernetes for orchestration
- Configure resource limits and requests

### Backup
- Backup named volumes regularly
- Export Grafana dashboards
- Preserve configuration files

### Updates
- Use rolling updates to minimize downtime
- Test updates in staging environment first
- Backup data before major updates

## Kubernetes Deployment

For production Kubernetes deployment, use the manifests in the `k8s/` directory:

```bash
./deploy/scripts/deploy_k8s.sh
```

This provides:
- Horizontal Pod Autoscaling
- ConfigMaps and Secrets management
- Persistent Volume Claims
- Ingress configuration
- RBAC policies