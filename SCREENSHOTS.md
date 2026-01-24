# vibeStation UI Screenshots

Since we're in a headless environment, we cannot run the PyQt6 GUI to take actual screenshots. However, here's what the UI looks like:

## Main Window

The main window consists of three tabs:

### 1. Tier Logs Tab (📊)
```
┌─────────────────────────────────────────────────────────────────┐
│ vibeStation - Vibe Coding Support Tool                          │
├─────────────────────────────────────────────────────────────────┤
│ FastAPI Server: http://127.0.0.1:8765                           │
├─────────────────────────────────────────────────────────────────┤
│ ┌───────────────────────────────────────────────────────────┐   │
│ │ Filter by Tier: [All ▼]  [Clear Logs]                    │   │
│ ├───────────────────────────────────────────────────────────┤   │
│ │ Time                 │ Tier │ Message                     │   │
│ ├───────────────────────────────────────────────────────────┤   │
│ │ 2026-01-24 06:20:00  │  A   │ Critical error detected     │   │
│ │ 2026-01-24 06:20:15  │  C   │ Warning: High memory        │   │
│ │ 2026-01-24 06:20:30  │  D   │ Info: Process completed     │   │
│ └───────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

Features:
- Real-time log display
- Color-coded tier badges (A=Red, B=Yellow, C=Blue, D=Green, E=Gray, F=Cyan)
- Filter by tier dropdown
- Clear logs button
- Auto-scroll to latest logs

### 2. Instructions Editor Tab (📝)
```
┌─────────────────────────────────────────────────────────────────┐
│ [💾 Save] [🔄 Reload] [✓ Validate] [📋 Backups]                 │
├─────────────────────────────────────────────────────────────────┤
│ ✓ Loaded successfully                                           │
├─────────────────────────────────────────────────────────────────┤
│ # GitHub Agent Instructions                                     │
│ version: "1.0"                                                  │
│ agent_name: "Vibe Coding Assistant"                             │
│                                                                 │
│ instructions:                                                   │
│   general:                                                      │
│     - "Follow best practices for code quality"                  │
│     - "Write clear and concise commit messages"                 │
│   coding_style:                                                 │
│     - "Use meaningful variable names"                           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

Features:
- YAML syntax editor with monospaced font
- Save button (creates automatic backup)
- Reload button (discard changes)
- Validate button (check YAML syntax)
- Backups button (view backup history)
- Status indicator (green for success, red for errors)

### 3. Info Tab (ℹ️)
```
┌─────────────────────────────────────────────────────────────────┐
│ vibeStation - Vibe Coding Support Tool                          │
│                                                                 │
│ Features                                                        │
│ • Tier Logs (A-F): Monitor real-time logs via POST /stream     │
│ • Instructions Editor: Edit .github/instructions.yaml          │
│ • FastAPI Server: Built-in API server with authentication      │
│                                                                 │
│ API Endpoints                                                   │
│ • POST /stream: Send tier logs (requires auth)                 │
│ • GET /logs: Retrieve stored logs (requires auth)              │
│ • POST /vibe_log: Send logs with retry (requires auth)         │
│ • GET /health: Health check                                    │
│                                                                 │
│ Authentication                                                  │
│ Auth key is stored in .github/auth_key.txt                     │
│ Use as Bearer token in API requests                            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

Features:
- Application overview
- API documentation
- Usage examples
- Authentication instructions

## UI Features Summary

1. **Modern Design**: Clean, professional Qt6 interface
2. **Tabbed Layout**: Easy navigation between logs, editor, and info
3. **Real-time Updates**: Logs refresh every 2 seconds automatically
4. **Color Coding**: Visual distinction between log tiers
5. **Safe Editing**: Automatic backups before saving
6. **User-friendly**: Clear status messages and confirmation dialogs

## Running the GUI

To see the actual UI on Windows:

```bash
# Method 1: Run from source
python run_vibestation.py

# Method 2: Run the EXE (after building)
dist\vibeStation.exe
```

The GUI will appear with all three tabs ready to use. The FastAPI server starts automatically in the background.
