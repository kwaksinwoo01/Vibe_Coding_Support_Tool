"""
State Management Utilities - Refactored

Hierarchical module with nested classes for state and outline management.
Clean architecture with proper separation of concerns.
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple


class StateManager:
    """Manage agent state persistence"""
    
    class Config:
        """State storage configuration"""
        def __init__(self, base_path: Path):
            self.base_path = base_path
            self.data_dir = base_path / "data"
            self.state_file = self.data_dir / "state.json"
        
        def ensure_dir(self) -> None:
            """Ensure data directory exists"""
            self.data_dir.mkdir(parents=True, exist_ok=True)
    
    class MessageSerializer:
        """Serialize messages to lightweight format"""
        
        @staticmethod
        def serialize(messages: List[Any]) -> List[Tuple[str, str]]:
            """
            Convert messages to lightweight (role, content) tuples
            
            Args:
                messages: List of message objects (dict or object)
                
            Returns:
                List of (role, content) tuples
            """
            serialized = []
            for m in messages:
                if isinstance(m, dict) and "role" in m and "content" in m:
                    serialized.append((m["role"], m["content"]))
                else:
                    # Handle old message objects (SystemMessage, HumanMessage, etc.)
                    role = getattr(m, "role", m.__class__.__name__)
                    content = getattr(m, "content", str(m))
                    serialized.append((role, content))
            return serialized
    
    class TaskHistorySerializer:
        """Serialize task history"""
        
        @staticmethod
        def serialize(task_history: List[Any]) -> List[Dict]:
            """
            Convert task history to dict format
            
            Args:
                task_history: List of task objects
                
            Returns:
                List of task dictionaries
            """
            if not task_history:
                return []
            
            # Check if tasks have to_dict method (old structure)
            if hasattr(task_history[0], 'to_dict'):
                return [task.to_dict() for task in task_history]
            
            # Already in dict format or empty
            if isinstance(task_history, list):
                return task_history
            
            return []
    
    class ReferenceSerializer:
        """Serialize references"""
        
        @staticmethod
        def serialize(references: Dict[str, Any]) -> Dict[str, Any]:
            """
            Convert references to dict format
            
            Args:
                references: Reference data with queries and docs
                
            Returns:
                Serialized references
            """
            if not references:
                return {"queries": [], "docs": []}
            
            return {
                "queries": references.get("queries", []),
                "docs": [
                    doc if isinstance(doc, dict) else getattr(doc, "metadata", {})
                    for doc in references.get("docs", [])
                ]
            }
    
    def __init__(self, base_path: Path):
        """Initialize state manager"""
        self.config = StateManager.Config(base_path)
    
    def save(self, state: Dict[str, Any]) -> None:
        """
        Save state to file
        
        Args:
            state: State dictionary to save
        """
        self.config.ensure_dir()
        
        state_dict = {
            "messages": StateManager.MessageSerializer.serialize(
                state.get("messages", [])
            ),
            "task_history": StateManager.TaskHistorySerializer.serialize(
                state.get("task_history", [])
            ),
            "references": StateManager.ReferenceSerializer.serialize(
                state.get("references", {})
            ),
        }
        
        with open(self.config.state_file, "w", encoding='utf-8') as f:
            json.dump(state_dict, f, indent=4, ensure_ascii=False)


class OutlineManager:
    """Manage document outlines"""
    
    class Config:
        """Outline storage configuration"""
        def __init__(self, base_path: Path):
            self.base_path = base_path
            self.data_dir = base_path / "data"
            self.outline_file = self.data_dir / "outline.md"
        
        def ensure_dir(self) -> None:
            """Ensure data directory exists"""
            self.data_dir.mkdir(parents=True, exist_ok=True)
    
    DEFAULT_OUTLINE = '아직 작성된 목차가 없습니다.'
    
    def __init__(self, base_path: Path):
        """Initialize outline manager"""
        self.config = OutlineManager.Config(base_path)
    
    def get(self) -> str:
        """
        Get outline content
        
        Returns:
            Outline content or default message
        """
        if not self.config.outline_file.exists():
            return self.DEFAULT_OUTLINE
        
        return self.config.outline_file.read_text(encoding='utf-8')
    
    def save(self, outline: str) -> str:
        """
        Save outline content
        
        Args:
            outline: Outline content to save
            
        Returns:
            Saved outline content
        """
        self.config.ensure_dir()
        self.config.outline_file.write_text(outline, encoding='utf-8')
        return outline
