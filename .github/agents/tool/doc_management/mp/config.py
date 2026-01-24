"""
MP Configuration Module - Refactored

Python path configuration and environment setup for MP tools.
Clean architecture with nested classes for related functionality.
"""

import sys
import os
from pathlib import Path
from typing import Optional, List
import importlib.util


class PathResolver:
    """Resolve paths in different execution contexts"""
    
    @staticmethod
    def find_repo_root() -> Optional[Path]:
        """
        Find repository root automatically.
        
        Tries multiple methods:
        1. Walk up from current directory looking for .git
        2. Walk up from script location looking for .git
        3. Check GITHUB_WORKSPACE environment variable
        4. Look for turbo-system directory markers
        """
        # Method 1: From current working directory
        current = Path.cwd()
        result = PathResolver._walk_up_find_git(current)
        if result:
            return result
        
        # Method 2: From script location
        try:
            current = Path(__file__).resolve()
            result = PathResolver._walk_up_find_git(current)
            if result:
                return result
        except NameError:
            pass  # __file__ not available in interactive mode
        
        # Method 3: From environment variable
        if 'GITHUB_WORKSPACE' in os.environ:
            workspace = Path(os.environ['GITHUB_WORKSPACE'])
            if workspace.exists():
                return workspace
        
        return None
    
    @staticmethod
    def _walk_up_find_git(start_path: Path) -> Optional[Path]:
        """Walk up directory tree to find repository root"""
        current = start_path
        max_depth = 10
        depth = 0
        
        while current != current.parent and depth < max_depth:
            # Check for .git directory
            if (current / '.git').exists():
                return current
            
            # Check for turbo-system repository markers
            if current.name == 'turbo-system':
                if (current / '.github').exists() and (current / 'docs_2').exists():
                    return current
            
            # Check for both required directories
            if (current / '.github').exists() and (current / 'docs_2').exists():
                return current
            
            current = current.parent
            depth += 1
        
        return None
    
    @staticmethod
    def get_repo_root() -> Path:
        """Get repository root (raises error if not found)"""
        root = PathResolver.find_repo_root()
        if root is None:
            raise RuntimeError(
                "Cannot determine repository root. "
                "Ensure you are running from within the turbo-system repository."
            )
        return root


class PathConfig:
    """Configure Python sys.path for MP modules"""
    
    @staticmethod
    def setup_python_path(repo_root: Optional[Path] = None) -> Path:
        """
        Setup Python path to find MP modules.
        
        Args:
            repo_root: Optional repository root path
            
        Returns:
            Path to repository root
        """
        if repo_root is None:
            repo_root = PathResolver.get_repo_root()
        
        # Add paths in order of priority
        paths_to_add = [
            str(repo_root),
            str(repo_root / '.github' / 'agents'),
            str(repo_root / '.github' / 'agents' / 'tool'),
        ]
        
        for path in paths_to_add:
            if path not in sys.path:
                sys.path.insert(0, path)
        
        return repo_root
    
    @staticmethod
    def get_module_paths() -> List[Path]:
        """Get all MP module paths"""
        repo_root = PathResolver.get_repo_root()
        
        paths = [
            repo_root / '.github' / 'agents' / 'tool',
            repo_root / '.github' / 'agents' / 'tool' / 'models',
            repo_root / '.github' / 'agents' / 'tool' / 'doc_management' / 'mp',
            repo_root / '.github' / 'agents' / 'tool' / 'doc_management' / 'mp' / 'reporting',
        ]
        
        return [p for p in paths if p.exists()]


class ModuleValidator:
    """Validate module imports"""
    
    @staticmethod
    def verify_imports(modules: List[str]) -> bool:
        """
        Verify required modules can be imported.
        
        Args:
            modules: List of module names to verify
            
        Returns:
            True if all modules can be imported
        """
        all_success = True
        failed_modules = []
        
        for module_name in modules:
            try:
                spec = importlib.util.find_spec(module_name)
                if spec is None:
                    failed_modules.append(module_name)
                    all_success = False
            except (ImportError, ModuleNotFoundError) as e:
                failed_modules.append(f"{module_name} ({e})")
                all_success = False
        
        if not all_success:
            print(
                f"Module import verification failed for: {', '.join(failed_modules)}",
                file=sys.stderr
            )
        
        return all_success


class EnvironmentDetector:
    """Detect execution environment"""
    
    @staticmethod
    def is_github_actions() -> bool:
        """Check if running in GitHub Actions"""
        return 'GITHUB_ACTIONS' in os.environ
    
    @staticmethod
    def is_local() -> bool:
        """Check if running locally"""
        return not EnvironmentDetector.is_github_actions()
    
    @staticmethod
    def get_environment() -> str:
        """Get current environment name"""
        if EnvironmentDetector.is_github_actions():
            return 'github_actions'
        return 'local'


class MPConfigurator:
    """
    Main MP configuration interface.
    Facade for path, module, and environment configuration.
    """
    
    @staticmethod
    def setup(repo_root: Optional[Path] = None) -> Path:
        """
        Complete setup for MP tools.
        
        Args:
            repo_root: Optional repository root
            
        Returns:
            Path to repository root
        """
        return PathConfig.setup_python_path(repo_root)
    
    @staticmethod
    def verify() -> bool:
        """Verify all MP modules can be imported"""
        required_modules = [
            'models.core.mp_models',
            'doc_management.mp.constants',
            'doc_management.mp.utils',
        ]
        return ModuleValidator.verify_imports(required_modules)
    
    @staticmethod
    def get_repo_root() -> Path:
        """Get repository root"""
        return PathResolver.get_repo_root()
    
    @staticmethod
    def get_module_paths() -> List[Path]:
        """Get all module paths"""
        return PathConfig.get_module_paths()
    
    @staticmethod
    def is_github_actions() -> bool:
        """Check if in GitHub Actions"""
        return EnvironmentDetector.is_github_actions()


# Backward compatibility alias (temporary)
MPPathConfigurator = MPConfigurator
