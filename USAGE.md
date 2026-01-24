# vibeStation Usage Examples

## Starting the Application

### Method 1: Using the run script
```bash
python run_vibestation.py
```

### Method 2: Using the module
```bash
python -m vibeStation.app
```

### Method 3: Direct execution (Windows EXE)
```bash
dist/vibeStation.exe
```

## Using the API

### Get Authentication Key
First, get your authentication key from the running application:

```bash
curl http://127.0.0.1:8765/auth_key
```

Or check the file:
```bash
cat .github/auth_key.txt
```

### Send Tier Logs

#### Tier A (Critical)
```bash
curl -X POST http://127.0.0.1:8765/stream \
  -H "Authorization: Bearer YOUR_AUTH_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "tier": "A",
    "message": "Critical: Database connection lost"
  }'
```

#### Tier B (Error)
```bash
curl -X POST http://127.0.0.1:8765/stream \
  -H "Authorization: Bearer YOUR_AUTH_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "tier": "B",
    "message": "Error: Failed to process request"
  }'
```

#### Tier C (Warning)
```bash
curl -X POST http://127.0.0.1:8765/stream \
  -H "Authorization: Bearer YOUR_AUTH_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "tier": "C",
    "message": "Warning: High memory usage"
  }'
```

#### Tier D (Info)
```bash
curl -X POST http://127.0.0.1:8765/stream \
  -H "Authorization: Bearer YOUR_AUTH_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "tier": "D",
    "message": "Info: Process started successfully"
  }'
```

#### Tier E (Debug)
```bash
curl -X POST http://127.0.0.1:8765/stream \
  -H "Authorization: Bearer YOUR_AUTH_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "tier": "E",
    "message": "Debug: Variable x = 42"
  }'
```

#### Tier F (Trace)
```bash
curl -X POST http://127.0.0.1:8765/stream \
  -H "Authorization: Bearer YOUR_AUTH_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "tier": "F",
    "message": "Trace: Entering function process_data()"
  }'
```

### Retrieve Logs

#### Get all logs
```bash
curl http://127.0.0.1:8765/logs \
  -H "Authorization: Bearer YOUR_AUTH_KEY"
```

#### Get logs filtered by tier
```bash
curl "http://127.0.0.1:8765/logs?tier=A&limit=10" \
  -H "Authorization: Bearer YOUR_AUTH_KEY"
```

#### Get latest 50 logs
```bash
curl "http://127.0.0.1:8765/logs?limit=50" \
  -H "Authorization: Bearer YOUR_AUTH_KEY"
```

### Send Vibe Log with Retry

```bash
curl -X POST http://127.0.0.1:8765/vibe_log \
  -H "Authorization: Bearer YOUR_AUTH_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "destination": "http://example.com/api/log",
    "data": {
      "event": "deployment",
      "status": "success",
      "version": "1.0.0"
    }
  }'
```

## Python Client Example

```python
import requests

class VibeStationClient:
    def __init__(self, base_url="http://127.0.0.1:8765", auth_key=None):
        self.base_url = base_url
        self.auth_key = auth_key or self.get_auth_key()
        
    def get_auth_key(self):
        """Get authentication key from server."""
        response = requests.get(f"{self.base_url}/auth_key")
        return response.json()['auth_key']
    
    def send_log(self, tier, message):
        """Send a tier log."""
        response = requests.post(
            f"{self.base_url}/stream",
            headers={'Authorization': f'Bearer {self.auth_key}'},
            json={'tier': tier, 'message': message}
        )
        return response.json()
    
    def get_logs(self, tier=None, limit=100):
        """Get logs."""
        params = {'limit': limit}
        if tier:
            params['tier'] = tier
        
        response = requests.get(
            f"{self.base_url}/logs",
            headers={'Authorization': f'Bearer {self.auth_key}'},
            params=params
        )
        return response.json()['logs']
    
    def send_vibe_log(self, destination, data):
        """Send vibe log with retry."""
        response = requests.post(
            f"{self.base_url}/vibe_log",
            headers={'Authorization': f'Bearer {self.auth_key}'},
            json={'destination': destination, 'data': data}
        )
        return response.json()

# Usage
client = VibeStationClient()

# Send logs
client.send_log('A', 'Critical error occurred')
client.send_log('D', 'Process completed successfully')

# Get logs
all_logs = client.get_logs()
critical_logs = client.get_logs(tier='A')

# Send vibe log
result = client.send_vibe_log(
    destination='http://example.com/api/log',
    data={'event': 'test', 'status': 'ok'}
)
```

## UI Features

### Tier Logs Tab
- View real-time logs in a table format
- Filter logs by tier (A-F)
- Color-coded tier badges
- Clear logs button
- Auto-scroll to latest logs

### Instructions Editor Tab
- Edit .github/instructions.yaml in YAML format
- Syntax validation
- Save with automatic backup
- View backup history
- Reload from file

### Info Tab
- Application documentation
- API endpoint reference
- Usage examples

## Configuration

Edit `vibeStation/config.yaml`:

```yaml
server:
  host: "127.0.0.1"
  port: 8765  # Change API server port

files:
  instructions: "instructions.yaml"
  auth_key: "auth_key.txt"
  github_dir: ".github"

logging:
  tiers: ["A", "B", "C", "D", "E", "F"]
  max_log_entries: 1000  # Maximum logs to keep in memory

vibe_log:
  retry_attempts: 3  # Number of retry attempts
  retry_delay: 5     # Delay between retries (seconds)
  timeout: 10        # Request timeout (seconds)
```

## Troubleshooting

### Port Already in Use
If port 8765 is already in use, change it in `vibeStation/config.yaml`:
```yaml
server:
  port: 8766  # Use a different port
```

### Authentication Errors
If you get 401 errors, check that you're using the correct auth key:
```bash
cat .github/auth_key.txt
```

### YAML Syntax Errors
Use the "Validate" button in the Instructions Editor to check YAML syntax before saving.

### Missing Dependencies
Install all required packages:
```bash
pip install -r requirements.txt
```

## Building for Windows

### Create EXE
```bash
# Windows
build.bat

# Linux/Mac
./build.sh
```

The executable will be created in `dist/vibeStation.exe` (or `dist/vibeStation` on Linux/Mac).

### Distributing the EXE
The built executable is standalone and includes:
- Python interpreter
- All dependencies (PyQt6, FastAPI, etc.)
- Configuration files

Users only need to:
1. Run `vibeStation.exe`
2. The .github directory and config files will be created automatically
