---
name: diagnoseModulePathError
description: Diagnose and fix Python module path and import errors in subprocess execution
argument-hint: Provide the error message, the subprocess command, the calling module path, and the target module path
---

# Python Module Path Error Diagnosis & Resolution

## Problem Analysis Framework

When a subprocess fails with `ModuleNotFoundError` while attempting to invoke a Python module, systematically diagnose the root cause by examining:

### 1. Error Context
- **Error Message**: Identify which module cannot be found
- **Execution Method**: Is it using `-m` flag (module execution) or direct file path?
- **Working Directory**: Where is the subprocess being executed from?
- **sys.path Status**: Does the subprocess have access to parent package paths?

### 2. Common Root Causes

| Cause | Symptom | Solution |
|-------|---------|----------|
| Missing parent path in sys.path | `ModuleNotFoundError: No module named 'package_name'` | Add project root to sys.path before subprocess execution |
| Incorrect working directory | Module exists but subprocess doesn't find it | Set `cwd` parameter in subprocess call |
| Relative path assumptions | Imports fail in subprocess context | Use absolute paths; ensure __init__.py files exist |
| Packaging context change | Works in dev, fails in exe/packaged form | Decouple from file system paths; use module imports instead |

### 3. Investigation Steps

1. **Identify the subprocess working directory**:
   - Where is `cwd` set? If not set, it inherits from parent process
   - Print `os.getcwd()` in both calling and called modules to compare

2. **Verify package structure**:
   - Confirm all directories contain `__init__.py` files
   - Check that the full module path matches the directory structure

3. **Test sys.path configuration**:
   - In calling module: `print(sys.path)` to see available paths
   - Verify parent package directory is accessible

4. **Check module execution method**:
   - Using `-m` requires full package path from sys.path root
   - Direct file execution bypasses module path requirements

### 4. Resolution Pattern for Subprocess Execution

```python
import sys
import subprocess
from pathlib import Path

# Identify project root (adjust based on your structure)
# If calling module is: project/subpackage/module.py
# And target module is: project/package/subpackage/module.py
# Then project root is the common ancestor
calling_file = Path(__file__).resolve()
project_root = calling_file.parent.parent  # Adjust based on depth

# Ensure parent paths are in sys.path
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Execute subprocess with explicit working directory
result = subprocess.run(
    [sys.executable, "-m", "target_package.module_name", args],
    cwd=str(project_root),  # Critical: set working directory
    capture_output=True,
    text=True,
    timeout=timeout_seconds,
    env=os.environ.copy()  # Ensure environment is inherited
)
```

### 5. Special Considerations for Packaging

When code will be packaged as executable (.exe/.app):
- **Avoid file path dependencies**: Don't use `AGENT_PATH` constants pointing to script files
- **Use module imports instead**: Import the module directly rather than executing as subprocess
- **Remove path constants**: Delete constants like `AGENT_PATH` before packaging
- **Test both contexts**: Verify code works in development (with file paths) and packaged form (with module imports)

### 6. Refactoring Strategy

**Before (file path based - works in dev, breaks in exe)**:
```python
result = subprocess.run([sys.executable, AGENT_PATH, args], ...)
```

**After (module-based - works in both)**:
```python
# Direct import when available
from module_name import MainAgent
agent = MainAgent()
result = agent.route_and_execute(user_input)

# OR subprocess with module path
result = subprocess.run(
    [sys.executable, "-m", "package.module_name", args],
    cwd=project_root,
    ...
)
```

## Checklist for Resolution

- [ ] Identify the calling module and target module paths
- [ ] Determine project root (common ancestor of both)
- [ ] Add project root to sys.path in calling module
- [ ] Set `cwd` parameter in subprocess call
- [ ] Verify all `__init__.py` files are present
- [ ] Test with explicit module path in `-m` argument
- [ ] Consider refactoring from subprocess to direct import if appropriate
- [ ] Verify the solution works in both development and packaged contexts
