"""
Encoding Utilities - Handle UTF-8 encoding across all tiers

Provides safe file I/O and logging with proper UTF-8 encoding
to prevent cp949 and other encoding-related errors.

Usage:
    from common.encoding_utils import safe_read_file, safe_write_file, safe_print
    
    content = safe_read_file("file.md")
    safe_write_file("file.md", content)
    safe_print("Message with special chars: Part #1.0.1")
"""

import sys
from pathlib import Path
from typing import Optional


def setup_encoding():
    """
    Configure Python to use UTF-8 for all I/O operations
    
    This should be called once at module initialization
    """
    if sys.stdout is not None:
        if hasattr(sys.stdout, 'reconfigure'):
            try:
                sys.stdout.reconfigure(encoding='utf-8', errors='replace')
            except Exception as e:
                pass  # Python < 3.7 doesn't support reconfigure
    
    if sys.stderr is not None:
        if hasattr(sys.stderr, 'reconfigure'):
            try:
                sys.stderr.reconfigure(encoding='utf-8', errors='replace')
            except Exception as e:
                pass


def safe_read_file(file_path: str, encoding: str = 'utf-8', errors: str = 'replace') -> str:
    """
    Safely read file with UTF-8 encoding
    
    Args:
        file_path: Path to file
        encoding: Encoding to use (default: utf-8)
        errors: Error handling strategy ('replace', 'ignore', 'strict')
    
    Returns:
        File content as string
    
    Raises:
        FileNotFoundError: If file doesn't exist
    """
    try:
        path = Path(file_path)
        content = path.read_text(encoding=encoding, errors=errors)
        return content
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {file_path}")
    except Exception as e:
        raise IOError(f"Error reading file {file_path}: {e}")


def safe_write_file(file_path: str, content: str, encoding: str = 'utf-8', errors: str = 'replace') -> bool:
    """
    Safely write file with UTF-8 encoding
    
    Args:
        file_path: Path to file
        content: Content to write
        encoding: Encoding to use (default: utf-8)
        errors: Error handling strategy ('replace', 'ignore', 'strict')
    
    Returns:
        True if successful
    
    Raises:
        IOError: If write fails
    """
    try:
        path = Path(file_path)
        # Create parent directories if needed
        path.parent.mkdir(parents=True, exist_ok=True)
        # Write with UTF-8 encoding
        path.write_text(content, encoding=encoding, errors=errors)
        return True
    except Exception as e:
        raise IOError(f"Error writing file {file_path}: {e}")


def safe_print(*args, **kwargs) -> None:
    """
    Safely print to console with UTF-8 encoding
    
    Handles special characters and emojis gracefully
    
    Args:
        *args: Arguments to print
        **kwargs: Keyword arguments for print()
    """
    try:
        # Ensure encoding is UTF-8
        if 'encoding' not in kwargs:
            kwargs['encoding'] = 'utf-8'
        
        # Use errors='replace' to replace unencodable characters
        message = ' '.join(str(arg) for arg in args)
        
        # Try normal print first
        try:
            print(message, **kwargs)
        except UnicodeEncodeError:
            # If that fails, use errors='replace'
            print(message, **{k: v for k, v in kwargs.items() if k != 'encoding'})
    except Exception as e:
        # Last resort - print with repr
        print(repr(args), file=sys.stderr)


def sanitize_string(text: str) -> str:
    """
    Sanitize string to be safe for cp949 encoding
    
    Removes problematic Unicode characters that cp949 can't handle
    
    Args:
        text: Input string
    
    Returns:
        Sanitized string safe for any encoding
    """
    # Replace common problematic characters
    replacements = {
        '\U0001f539': '[INFO]',  # Blue circle with exclamation mark
        '\u2713': '[OK]',        # Checkmark
        '\u2717': '[FAIL]',      # Cross mark
        '\u26a0': '[WARN]',      # Warning sign
        '\u2192': '->',          # Right arrow
        '\u2713': 'OK',          # Check mark
        '\u2717': 'NG',          # Cross mark
    }
    
    result = text
    for char, replacement in replacements.items():
        result = result.replace(char, replacement)
    
    return result


def with_encoding_fallback(func):
    """
    Decorator to safely handle encoding errors in functions
    
    Usage:
        @with_encoding_fallback
        def my_function():
            # Function that might raise UnicodeEncodeError
            pass
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except UnicodeEncodeError as e:
            # Log the error safely
            safe_print(f"[WARNING] Encoding error in {func.__name__}: {e}")
            # Try again with error handling
            try:
                # Modify kwargs to use safer encoding
                if 'encoding' in kwargs:
                    kwargs['encoding'] = 'utf-8'
                    kwargs['errors'] = 'replace'
                return func(*args, **kwargs)
            except Exception as retry_error:
                safe_print(f"[ERROR] Retry failed: {retry_error}")
                raise
        except Exception as e:
            raise
    
    return wrapper


# Initialize encoding on import
setup_encoding()

__all__ = [
    'setup_encoding',
    'safe_read_file',
    'safe_write_file',
    'safe_print',
    'sanitize_string',
    'with_encoding_fallback',
]
