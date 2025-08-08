# K-Means Trading Strategy - Docker Deployment Guide

This guide provides comprehensive instructions for deploying the K-Means Trading Strategy using Docker containers.

## Prerequisites

- Docker and Docker Compose installed
- Interactive Brokers TWS or IB Gateway (for live data)
- At least 2GB RAM and 1GB disk space

## Quick Start

### 1. Clone and Build

```bash
# Clone the repository
git clone <repository-url>
cd kmeans_trading

# Build the Docker image
docker build -t kmeans-trading .
```

### 2. Configure Interactive Brokers (Optional)

If using live data from Interactive Brokers:

1. Start TWS Workstation or IB Gateway
2. Enable API connections in TWS settings
3. Configure API settings:
   - Socket port: 7497 (TWS) or 7496 (Gateway)
   - Enable "Download open orders on connection"
   - Trusted IPs: Add your Docker host IP

### 3. Deploy with Docker Compose

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### 4. Access the Dashboard

Open your browser and navigate to:
- Dashboard: http://localhost:8080
- WebSocket Server: ws://localhost:8765

## Configuration

### Environment Variables

Override configuration using environment variables in `docker-compose.yml`:

```yaml
environment:
  - KMEANS_IB_HOST=host.docker.internal  # IB TWS host
  - KMEANS_IB_PORT=7497                  # IB TWS port
  - KMEANS_LOG_LEVEL=DEBUG               # Logging level
  - KMEANS_WS_HOST=0.0.0.0              # WebSocket host
  - KMEANS_WS_PORT=8765                 # WebSocket port
```

### Configuration File

Modify `config.yaml` to customize:
- Strategy parameters (clustering, thresholds)
- Interactive Brokers settings
- Performance optimizations
- Logging preferences

## Services Overview

### 1. K-Means Trading Server (`kmeans-trading`)
- **Port**: 8765 (WebSocket)
- **Purpose**: Core trading strategy analysis
- **Health Check**: WebSocket connection test
- **Restart Policy**: Unless stopped

### 2. Web Dashboard (`dashboard`)
- **Port**: 8080 (HTTP)
- **Purpose**: Interactive web interface
- **Backend**: Nginx serving static files
- **Features**: Real-time charts, statistics, controls

## Testing

### Manual Testing

1. **Health Checks**:
   ```bash
   # Check service status
   docker-compose ps
   
   # Test WebSocket connection
   curl -f http://localhost:8080/health
   ```

2. **Dashboard Testing**:
   - Open http://localhost:8080
   - Enter test tickers (e.g., "AAPL, MSFT")
   - Select duration and bar size
   - Click "Analyze with K-Means Strategy"

3. **Log Monitoring**:
   ```bash
   # View real-time logs
   docker-compose logs -f kmeans-trading
   
   # Check error logs
   docker-compose logs kmeans-trading | grep ERROR
   ```

### Automated Testing

Run the provided test script:

```bash
# Test Docker setup (requires running containers)
python test_docker.py
```

## Production Deployment

### Security Considerations

1. **Network Security**:
   ```yaml
   # docker-compose.override.yml for production
   version: '3.8'
   services:
     dashboard:
       ports:
         - "127.0.0.1:8080:80"  # Bind to localhost only
     kmeans-trading:
       ports:
         - "127.0.0.1:8765:8765"  # Bind to localhost only
   ```

2. **Resource Limits**:
   ```yaml
   services:
     kmeans-trading:
       deploy:
         resources:
           limits:
             memory: 1G
             cpus: '1.0'
   ```

3. **Persistent Logging**:
   ```yaml
   volumes:
     - ./logs:/app/logs
   ```

### Performance Tuning

1. **Memory Optimization**:
   - Set `performance.enable_median_sectors: false` in config
   - Enable `performance.memory.cleanup_ib_data: true`

2. **CPU Optimization**:
   - Adjust `strategy.clustering.max_clusters` based on CPU capacity
   - Use `strategy.clustering.n_init: 3` for faster clustering

3. **Network Optimization**:
   - Increase `interactive_brokers.data_request.request_timeout` for slow connections
   - Set appropriate `websocket_server.connection_timeout`

## Troubleshooting

### Common Issues

1. **Container Won't Start**:
   ```bash
   # Check build errors
   docker build -t kmeans-trading . --no-cache
   
   # Check system resources
   docker system df
   ```

2. **Can't Connect to IB**:
   - Verify TWS is running and API is enabled
   - Check host connectivity: `docker run --rm -it busybox ping host.docker.internal`
   - Review IB connection logs: `docker-compose logs kmeans-trading | grep -i "ib\|connection"`

3. **WebSocket Connection Failed**:
   ```bash
   # Test WebSocket directly
   docker exec -it kmeans-trading python -c "
   import asyncio
   import websockets
   async def test():
       async with websockets.connect('ws://localhost:8765'):
           print('Connection OK')
   asyncio.run(test())
   "
   ```

4. **Dashboard Not Loading**:
   - Check nginx logs: `docker-compose logs dashboard`
   - Verify static files: `docker exec dashboard ls -la /usr/share/nginx/html/`
   - Test direct file access: `curl http://localhost:8080/dashboard.js`

### Performance Issues

1. **Slow Analysis**:
   - Reduce data duration in dashboard
   - Lower `max_clusters` in configuration
   - Enable performance optimizations

2. **High Memory Usage**:
   - Enable data cleanup in configuration
   - Reduce concurrent connections
   - Monitor with: `docker stats`

3. **High CPU Usage**:
   - Reduce `n_init` parameter
   - Limit concurrent analysis requests
   - Consider horizontal scaling

## Monitoring

### Health Monitoring

```bash
# Container health
docker-compose ps

# Resource usage
docker stats

# Service logs
docker-compose logs -f --tail=100
```

### Application Monitoring

```bash
# WebSocket connections
netstat -an | grep :8765

# HTTP requests
docker-compose logs dashboard | grep -E "GET|POST"

# Trading signals
docker-compose logs kmeans-trading | grep -E "BUY|SELL|HOLD"
```

## Backup and Recovery

### Configuration Backup
```bash
# Backup configuration
tar -czf kmeans-backup-$(date +%Y%m%d).tar.gz config.yaml docker-compose.yml logs/
```

### Data Recovery
```bash
# Restore from backup
tar -xzf kmeans-backup-YYYYMMDD.tar.gz
docker-compose up -d
```

## Scaling

### Horizontal Scaling

```yaml
# docker-compose.scale.yml
version: '3.8'
services:
  kmeans-trading:
    deploy:
      replicas: 3
  dashboard:
    deploy:
      replicas: 2
```

### Load Balancing

Use nginx or HAProxy for load balancing multiple instances:

```nginx
upstream kmeans_backend {
    server localhost:8765;
    server localhost:8766;
    server localhost:8767;
}
```

This deployment guide ensures professional-grade deployment with proper monitoring, security, and scalability considerations.