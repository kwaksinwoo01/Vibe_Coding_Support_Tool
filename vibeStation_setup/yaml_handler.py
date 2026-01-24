"""
YAML Handler for secure read/write operations on .github instructions file.
Implements backup, atomic replacement, and verification.
"""
import os
import shutil
import yaml
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path


class YAMLHandler:
    """Handler for secure YAML file operations with backup and verification."""
    
    def __init__(self, file_path: str):
        """
        Initialize the YAML handler.
        
        Args:
            file_path: Path to the YAML file
        """
        self.file_path = Path(file_path)
        self.backup_dir = self.file_path.parent
        
    def read(self) -> Dict[str, Any]:
        """
        Read YAML file content.
        
        Returns:
            Dictionary containing YAML data
            
        Raises:
            FileNotFoundError: If file doesn't exist
            yaml.YAMLError: If file is not valid YAML
        """
        if not self.file_path.exists():
            raise FileNotFoundError(f"YAML file not found: {self.file_path}")
            
        with open(self.file_path, 'r', encoding='utf-8') as f:
            try:
                data = yaml.safe_load(f)
                return data if data is not None else {}
            except yaml.YAMLError as e:
                raise yaml.YAMLError(f"Invalid YAML format: {e}")
    
    def _create_backup(self) -> Optional[Path]:
        """
        Create a backup of the current file.
        
        Returns:
            Path to backup file, or None if original doesn't exist
        """
        if not self.file_path.exists():
            return None
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{self.file_path.stem}_backup_{timestamp}{self.file_path.suffix}"
        backup_path = self.backup_dir / backup_name
        
        shutil.copy2(self.file_path, backup_path)
        return backup_path
    
    def _verify_yaml(self, data: Dict[str, Any]) -> bool:
        """
        Verify that data can be serialized to valid YAML.
        
        Args:
            data: Data to verify
            
        Returns:
            True if data is valid YAML-serializable
        """
        try:
            yaml_str = yaml.safe_dump(data, allow_unicode=True, sort_keys=False)
            # Verify we can read it back
            yaml.safe_load(yaml_str)
            return True
        except (yaml.YAMLError, TypeError, ValueError):
            return False
    
    def write(self, data: Dict[str, Any], create_backup: bool = True) -> bool:
        """
        Write data to YAML file with atomic replacement.
        
        Args:
            data: Data to write
            create_backup: Whether to create a backup before writing
            
        Returns:
            True if write was successful
            
        Raises:
            ValueError: If data cannot be serialized to YAML
            IOError: If write operation fails
        """
        # Verify data can be serialized
        if not self._verify_yaml(data):
            raise ValueError("Data cannot be serialized to valid YAML")
        
        # Create backup if requested and file exists
        backup_path = None
        if create_backup and self.file_path.exists():
            backup_path = self._create_backup()
        
        # Write to temporary file first (atomic replacement)
        temp_path = self.file_path.with_suffix('.tmp')
        
        try:
            # Ensure parent directory exists
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write to temp file
            with open(temp_path, 'w', encoding='utf-8') as f:
                yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False, indent=2)
            
            # Verify the written file
            with open(temp_path, 'r', encoding='utf-8') as f:
                verified_data = yaml.safe_load(f)
                if verified_data != data:
                    raise ValueError("Verification failed: Written data doesn't match input")
            
            # Atomic replace - Path objects are supported directly
            shutil.move(temp_path, self.file_path)
            
            return True
            
        except Exception as e:
            # Clean up temp file if it exists
            if temp_path.exists():
                temp_path.unlink()
            
            # Restore from backup if write failed
            if backup_path and backup_path.exists():
                shutil.copy2(backup_path, self.file_path)
            
            raise IOError(f"Failed to write YAML file: {e}")
    
    def validate_structure(self, required_keys: list = None) -> bool:
        """
        Validate that the YAML file has required structure.
        
        Args:
            required_keys: List of required top-level keys
            
        Returns:
            True if structure is valid
        """
        try:
            data = self.read()
            
            if required_keys:
                for key in required_keys:
                    if key not in data:
                        return False
            
            return True
        except (FileNotFoundError, yaml.YAMLError):
            return False
    
    def get_backups(self) -> list:
        """
        Get list of backup files.
        
        Returns:
            List of backup file paths
        """
        pattern = f"{self.file_path.stem}_backup_*{self.file_path.suffix}"
        backups = sorted(self.backup_dir.glob(pattern), reverse=True)
        return backups
    
    def restore_backup(self, backup_path: Path) -> bool:
        """
        Restore from a backup file.
        
        Args:
            backup_path: Path to backup file
            
        Returns:
            True if restore was successful
        """
        if not backup_path.exists():
            return False
            
        try:
            # Create a backup of current file before restoring
            self._create_backup()
            
            # Restore from backup
            shutil.copy2(backup_path, self.file_path)
            return True
        except Exception:
            return False
