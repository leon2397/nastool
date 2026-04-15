# nastool API Documentation

> REST API and WebSocket API for nastool v3.0.1

## Base URL

```
http://localhost:8080
```

Configure with `NASTOOL_WEB_HOST` and `NASTOOL_WEB_PORT`.

---

## REST API

### GET /

API root and available endpoints.

**Response:**
```json
{
  "name": "nastool API",
  "version": "3.0.1",
  "docs": "/docs",
  "endpoints": {
    "device": "/api/device",
    "profiles": "/api/profiles",
    "diagnose": "/api/diagnose",
    "health": "/api/health",
    "alerts": "/api/alerts"
  }
}
```

---

### GET /api/device

Get current device information.

**Response:**
```json
{
  "hostname": "jetson-xavier-nx",
  "os": "Ubuntu 20.04.6 LTS",
  "arch": "aarch64",
  "cpu": "ARMv8",
  "memory_gb": 6.7,
  "profile": {
    "id": "jetson-xavier-nx",
    "name": "NVIDIA Jetson Xavier NX",
    "vendor": "NVIDIA",
    "category": "ai_edge"
  }
}
```

---

### GET /api/profiles

List all available device profiles.

**Response:**
```json
{
  "profiles": [
    {
      "id": "jetson-xavier-nx",
      "name": "NVIDIA Jetson Xavier NX",
      "vendor": "NVIDIA",
      "category": "ai_edge"
    },
    {
      "id": "rk3588",
      "name": "Rockchip RK3588",
      "vendor": "Rockchip",
      "category": "arm_sbc"
    }
  ]
}
```

---

### POST /api/diagnose

Run diagnostic checks.

**Request Body:**
```json
{
  "profile": "jetson-xavier-nx",  // optional
  "full": false,                   // full diagnosis with benchmarks
  "fix": false,                    // apply fixes
  "auto_fix": false                // auto-apply fixes without confirmation
}
```

**Response:**
```json
{
  "status": "completed",
  "health_score": 72,
  "checks": {
    "passed": 18,
    "warnings": 3,
    "failed": 1
  },
  "results": [
    {
      "id": "python_version",
      "status": "passed",
      "message": "Python 3.11.13"
    },
    {
      "id": "disk_space",
      "status": "warning",
      "message": "Only 35GB free"
    }
  ],
  "fixes_available": [
    {
      "id": "clean_disk",
      "description": "Clean up old files",
      "risk": "low"
    }
  ]
}
```

---

### GET /api/health

Get current health status.

**Response:**
```json
{
  "status": "healthy",
  "score": 72,
  "last_check": "2026-04-12T10:30:00Z",
  "alerts": []
}
```

---

### GET /api/alerts

List active alerts.

**Response:**
```json
{
  "alerts": [
    {
      "id": "alert_001",
      "severity": "warning",
      "message": "Disk space low: 35GB free",
      "timestamp": "2026-04-12T10:30:00Z",
      "check_id": "disk_space"
    }
  ]
}
```

---

### POST /api/alerts/config

Configure alert settings.

**Request Body:**
```json
{
  "enabled": true,
  "email": "admin@example.com",
  "webhook": "https://hooks.example.com/alert"
}
```

---

## WebSocket API

### WS /ws

Real-time health updates.

**Connection:**
```javascript
const ws = new WebSocket('ws://localhost:8080/ws');
```

**Messages:**

Health update:
```json
{
  "type": "health_update",
  "data": {
    "score": 72,
    "checks": {
      "memory": {"status": "ok", "percent": 65},
      "disk": {"status": "warning", "free_gb": 35}
    }
  }
}
```

Alert:
```json
{
  "type": "alert",
  "data": {
    "severity": "critical",
    "message": "CPU temperature critical: 92°C",
    "timestamp": "2026-04-12T10:35:00Z"
  }
}
```

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `NASTOOL_WEB_HOST` | `0.0.0.0` | Web server host |
| `NASTOOL_WEB_PORT` | `8080` | Web server port |
| `NASTOOL_WEB_DEBUG` | `false` | Enable debug mode |
| `NASTOOL_LOG_LEVEL` | `INFO` | Log level |

### Example

```bash
export NASTOOL_WEB_PORT=9000
export NASTOOL_LOG_LEVEL=DEBUG
python3 arm_diagnose.py --web
```

---

## Interactive API Docs

When running the web dashboard, access interactive documentation at:

- **Swagger UI**: http://localhost:8080/docs
- **ReDoc**: http://localhost:8080/redoc

---

## Error Handling

All errors follow this format:

```json
{
  "detail": "Error message",
  "error_code": "ERROR_CODE"
}
```

Common error codes:

| Code | Description |
|------|-------------|
| `PROFILE_NOT_FOUND` | Requested profile doesn't exist |
| `CHECK_FAILED` | Diagnostic check failed |
| `FIX_FAILED` | Fix script failed |
| `INVALID_REQUEST` | Invalid request body |
