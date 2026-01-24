"""
Web Search and Storage Utilities - Refactored

Hierarchical module with nested classes for web search and document storage.
Clean architecture without external vector DB dependencies.
"""

import json
import os
import re
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from pathlib import Path


class WebPageStorage:
    """Storage operations for web pages"""
    
    class Config:
        """Storage configuration"""
        def __init__(self, base_path: Optional[Path] = None):
            if base_path is None:
                base_path = Path(__file__).parent.parent / "data"
            self.store_path = base_path
            self.index_file = self.store_path / "web_pages_index.json"
        
        def ensure_dir(self) -> None:
            """Ensure storage directory exists"""
            self.store_path.mkdir(parents=True, exist_ok=True)
    
    class TextProcessor:
        """Text normalization and scoring"""
        
        @staticmethod
        def normalize(text: str) -> str:
            """Normalize text by removing extra whitespace"""
            text = text or ""
            text = re.sub(r"\s+", " ", text)
            return text.strip()
        
        @staticmethod
        def score(query: str, text: str) -> int:
            """Calculate relevance score based on token matches"""
            score = 0
            for token in set(query.lower().split()):
                if token and token in text.lower():
                    score += 1
            return score
    
    class IndexManager:
        """Manage document index"""
        
        def __init__(self, config: 'WebPageStorage.Config'):
            self.config = config
        
        def load_index(self) -> List[Dict]:
            """Load document index from file"""
            if not self.config.index_file.exists():
                return []
            try:
                with open(self.config.index_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return []
        
        def save_index(self, index: List[Dict]) -> None:
            """Save document index to file"""
            self.config.ensure_dir()
            with open(self.config.index_file, "w", encoding="utf-8") as f:
                json.dump(index, f, ensure_ascii=False, indent=2)
        
        def add_documents(self, documents: List[Dict]) -> None:
            """Add documents to index, avoiding duplicates"""
            index = self.load_index()
            existing_urls = {d.get("url") for d in index}
            
            for doc in documents:
                if doc.get("url") not in existing_urls:
                    index.append({
                        "title": doc.get("title") or "",
                        "url": doc.get("url") or "",
                        "content": WebPageStorage.TextProcessor.normalize(doc.get("content") or ""),
                        "raw_content": WebPageStorage.TextProcessor.normalize(
                            doc.get("raw_content") or doc.get("content") or ""
                        ),
                        "saved_at": datetime.now().isoformat(),
                    })
            
            self.save_index(index)
    
    class Searcher:
        """Search documents in index"""
        
        def __init__(self, config: 'WebPageStorage.Config'):
            self.config = config
            self.index_manager = WebPageStorage.IndexManager(config)
        
        def search(self, query: str, top_k: int = 5) -> List[Dict]:
            """
            Search documents by query with simple keyword scoring
            
            Args:
                query: Search query
                top_k: Number of results to return
                
            Returns:
                List of matching documents
            """
            index = self.index_manager.load_index()
            
            scored = []
            for item in index:
                text = item.get("raw_content") or item.get("content") or ""
                score = WebPageStorage.TextProcessor.score(query, text)
                if score > 0:
                    scored.append((item, score))
            
            scored.sort(key=lambda x: x[1], reverse=True)
            return [s[0] for s in scored[:top_k]]
        
        def search_and_save(self, query: str) -> Tuple[List[Dict], str]:
            """
            Search and save results to timestamped file
            
            Returns:
                (matched_documents, saved_file_path)
            """
            self.config.ensure_dir()
            matched = self.search(query, top_k=100)
            
            # Save results with timestamp
            ts = datetime.now().strftime("%Y_%m%d_%H%M%S")
            resources_path = self.config.store_path / f"resources_{ts}.json"
            
            with open(resources_path, "w", encoding="utf-8") as f:
                json.dump(matched, f, ensure_ascii=False, indent=4)
            
            return matched, str(resources_path)


class WebPageLoader:
    """Load web pages from URLs"""
    
    @staticmethod
    def load(url: str, timeout: int = 15) -> str:
        """
        Load web page content from URL
        
        Args:
            url: URL to load
            timeout: Request timeout in seconds
            
        Returns:
            Normalized page content
        """
        try:
            import requests
        except ImportError:
            raise RuntimeError(
                "'requests' is not installed. Install it via: pip install requests"
            )
        
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        
        raw_content = response.text
        return WebPageStorage.TextProcessor.normalize(raw_content)
