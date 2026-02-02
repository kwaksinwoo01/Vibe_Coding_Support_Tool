# diagnoseModulePathError - Visual Guide

## Directory Structure and Path Calculation

```
Vibe_Coding_Support_Tool/                    <- Repository root (_PROJECT_ROOT)
│                                             <- This is where sys.path needs to point
├── .github/
│   └── prompts/
│       ├── diagnoseModulePathError.prompt.md
│       └── diagnoseModulePathError_RESOLVED.md
│
├── requirements.txt
├── build.sh
│
└── vibeStation_setup/                       <- Python package (can be imported)
    ├── __init__.py                           <- Makes it a package
    │
    ├── settings/
    │   └── config_manager.py
    │
    ├── ui/
    │   └── main_window.py
    │
    └── mcp_suver/                            <- Sub-package
        ├── __init__.py
        │
        ├── main_agent.py                     <- Target module (to execute)
        │
        └── core/                             <- Sub-sub-package
            ├── __init__.py
            └── server_thread.py              <- Calling module (subprocess here)
                                              <- We are HERE (4 levels deep)
```

## Path Calculation

```python
# In server_thread.py:
_CALLING_FILE = Path(__file__).resolve()
# Result: /path/to/Vibe_Coding_Support_Tool/vibeStation_setup/mcp_suver/core/server_thread.py

_PROJECT_ROOT = _CALLING_FILE.parent.parent.parent.parent
#                            ^      ^      ^      ^
#                            |      |      |      |
# Step 1: parent -----------┘      |      |      |
#   -> /path/to/Vibe_Coding_Support_Tool/vibeStation_setup/mcp_suver/core/
#
# Step 2: parent ------------------┘      |      |
#   -> /path/to/Vibe_Coding_Support_Tool/vibeStation_setup/mcp_suver/
#
# Step 3: parent -------------------------┘      |
#   -> /path/to/Vibe_Coding_Support_Tool/vibeStation_setup/
#
# Step 4: parent --------------------------------┘
#   -> /path/to/Vibe_Coding_Support_Tool/  ✓ CORRECT!
```

## Before vs After

### BEFORE (Broken) ❌

```
Current Working Directory: /tmp/              <- Could be anywhere!
                          
subprocess.run([
    sys.executable, 
    "-m", 
    "vibeStation_setup.mcp_suver.main_agent"  <- Looking for this module...
])

Python searches for 'vibeStation_setup' in:
  /tmp/                                       <- NOT HERE!
  /usr/lib/python3.x/                        <- NOT HERE!
  /home/user/.local/lib/python3.x/           <- NOT HERE!

Result: ModuleNotFoundError ❌
```

### AFTER (Fixed) ✅

```
Current Working Directory: /tmp/              <- Still could be anywhere

_PROJECT_ROOT = calculate_root()
# -> /path/to/Vibe_Coding_Support_Tool/

subprocess.run([
    sys.executable, 
    "-m", 
    "vibeStation_setup.mcp_suver.main_agent"
], 
cwd=str(_PROJECT_ROOT)                        <- SET THIS!
)

Now subprocess runs with:
  Working Directory: /path/to/Vibe_Coding_Support_Tool/
  
Python searches for 'vibeStation_setup' in:
  /path/to/Vibe_Coding_Support_Tool/         <- FOUND IT! ✓
  (and then finds vibeStation_setup/mcp_suver/main_agent.py)

Result: Module loads successfully ✅
```

## Import Flow

```
1. Execute command:
   python -m vibeStation_setup.mcp_suver.main_agent "user input"
   
2. Python looks for package 'vibeStation_setup' from cwd
   cwd = /path/to/Vibe_Coding_Support_Tool/
   
3. Finds: vibeStation_setup/
   Checks: vibeStation_setup/__init__.py ✓
   
4. Looks for sub-package 'mcp_suver'
   Finds: vibeStation_setup/mcp_suver/
   Checks: vibeStation_setup/mcp_suver/__init__.py ✓
   
5. Looks for module 'main_agent'
   Finds: vibeStation_setup/mcp_suver/main_agent.py ✓
   
6. Checks if it's executable (has __main__ or can run as script)
   Finds: vibeStation_setup/mcp_suver/__main__.py ✓
   OR can import main_agent.py directly ✓
   
7. SUCCESS: Module executes
```

## Why Both cwd and env?

### cwd (Working Directory)

```python
cwd=str(_PROJECT_ROOT)
```

**Purpose**: Tell subprocess WHERE to run from  
**Effect**: Makes module imports work  
**Example**: 
- Without: Looks for `vibeStation_setup` from `/tmp/` (fails)
- With: Looks for `vibeStation_setup` from `/path/to/repo/` (succeeds)

### env (Environment Variables)

```python
env=os.environ.copy()
```

**Purpose**: Pass configuration to subprocess  
**Effect**: Subprocess gets all environment variables  
**Example**:
- Without: Missing GITHUB_TOKEN, PATH, etc.
- With: Has all tokens, paths, configs

## Common Pitfalls

### ❌ Wrong: Using file path

```python
# DON'T DO THIS - won't work when packaged
subprocess.run([sys.executable, "/path/to/main_agent.py", args])
```

### ❌ Wrong: No cwd parameter

```python
# DON'T DO THIS - depends on where parent runs from
subprocess.run([sys.executable, "-m", "module", args])
```

### ❌ Wrong: Wrong number of .parent calls

```python
# TOO FEW - still in vibeStation_setup/
_PROJECT_ROOT = Path(__file__).parent.parent.parent

# TOO MANY - up to parent directory of repo
_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
```

### ✅ Correct: Module with cwd

```python
# DO THIS - works everywhere, even when packaged
_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
subprocess.run(
    [sys.executable, "-m", "vibeStation_setup.mcp_suver.main_agent", args],
    cwd=str(_PROJECT_ROOT),
    env=os.environ.copy()
)
```

## Testing the Fix

### Test Script Structure

```python
# 1. Change to different directory (proves cwd matters)
os.chdir("/tmp")

# 2. Calculate project root
project_root = Path("/path/to/Vibe_Coding_Support_Tool")

# 3. Run subprocess WITH cwd
result = subprocess.run(
    [sys.executable, "-m", "vibeStation_setup.mcp_suver.main_agent", "test"],
    cwd=str(project_root),  # This makes it work!
    ...
)

# 4. Check for ModuleNotFoundError
if "ModuleNotFoundError" in result.stderr:
    print("FAILED")
else:
    print("PASSED")
```

### Test Results

```
Changed working directory to: /tmp
Project root: /path/to/Vibe_Coding_Support_Tool
Project root exists: True

=== Test WITH cwd parameter ===
Return code: 0
✓ SUCCESS - Module executed without errors
✓ PASSED - No ModuleNotFoundError detected

Output shows:
- Loaded policy rules ✓
- [MAIN_AGENT] New Session ✓
- [CLASSIFY] Input processing ✓
```

## When to Use This Pattern

Use this pattern when:
- ✅ Running subprocess with `-m` flag (module execution)
- ✅ Target module is in a package structure
- ✅ Subprocess might run from different directories
- ✅ Code needs to work when packaged as executable

Don't need this pattern when:
- ❌ Running subprocess with direct file path (but this breaks packaging!)
- ❌ Target is a system command (like `ls`, `git`)
- ❌ Module is installed via pip (available everywhere)

## Summary

```
┌─────────────────────────────────────────────────────────┐
│  PROBLEM: ModuleNotFoundError                           │
│  CAUSE:   No cwd parameter in subprocess.run()          │
│  FIX:     Add cwd=_PROJECT_ROOT                         │
│  RESULT:  Module found and executed successfully        │
└─────────────────────────────────────────────────────────┘

Key Points:
1. Calculate project root from __file__
2. Add project root to sys.path
3. Set cwd in subprocess.run()
4. Copy parent environment
5. Use -m flag for module execution
6. Test from different working directory
```

---

**Visual Guide Created**: 2026-02-02  
**Issue**: diagnoseModulePathError  
**Status**: RESOLVED ✅
