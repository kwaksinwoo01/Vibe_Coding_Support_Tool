"""
tier_keywords_manager.py - Dynamic Tier Keywords Management

Provides functionality to update tier keywords dynamically through user feedback.
Manages persistence of keyword updates to maintain consistency across sessions.

Features:
- Add new keywords to tiers
- Remove keywords from tiers
- Update context bonuses
- Save/load keyword configurations
- Backup and restore functionality

Usage:
    from config.tier_keywords_manager import add_keyword, save_keywords
    
    add_keyword("C", "새 키워드", bonus_points=3.0)
    save_keywords()
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.tier_keywords import (
    get_tier_keywords,
    get_context_bonuses,
    TIER_A_KEYWORDS,
    TIER_B_KEYWORDS,
    TIER_C_KEYWORDS,
    TIER_D_KEYWORDS,
    TIER_E_KEYWORDS,
    TIER_F_KEYWORDS,
    CONTEXT_BONUSES,
)


class TierKeywordsManager:
    """Manager for tier keyword updates and persistence"""
    
    # File paths for keyword persistence
    CONFIG_DIR = Path(__file__).parent
    KEYWORDS_BACKUP_DIR = CONFIG_DIR / "backups"
    KEYWORDS_FILE = CONFIG_DIR / "tier_keywords_custom.json"
    
    def __init__(self):
        """Initialize keywords manager"""
        self.tier_keywords = get_tier_keywords()
        self.context_bonuses = get_context_bonuses()
        self.change_log: List[Dict] = []
        
        # Create backup directory if it doesn't exist
        self.KEYWORDS_BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    
    @staticmethod
    def add_keyword(tier: str, keyword: str, bonus_points: float = 0.0) -> bool:
        """
        Add a new keyword to a tier
        
        Args:
            tier: Tier letter (A-F)
            keyword: Keyword to add
            bonus_points: Optional bonus points for context
        
        Returns:
            True if successful, False otherwise
        """
        manager = TierKeywordsManager()
        
        # Validate tier
        if tier not in manager.tier_keywords:
            print(f"[ERROR] Invalid tier: {tier}. Must be A-F")
            return False
        
        # Get keywords list
        keywords_list = manager.tier_keywords[tier].get("keywords", [])
        
        # Check if keyword already exists
        if keyword.lower() in [kw.lower() for kw in keywords_list]:
            print(f"[WARN] Keyword already exists in Tier {tier}: {keyword}")
            return False
        
        # Add keyword
        keywords_list.append(keyword)
        manager.tier_keywords[tier]["keywords"] = keywords_list
        
        # Log the change
        manager.change_log.append({
            "timestamp": datetime.now().isoformat(),
            "action": "add_keyword",
            "tier": tier,
            "keyword": keyword,
            "bonus_points": bonus_points,
        })
        
        print(f"[OK] Keyword added to Tier {tier}: {keyword}")
        return True
    
    @staticmethod
    def remove_keyword(tier: str, keyword: str) -> bool:
        """
        Remove a keyword from a tier
        
        Args:
            tier: Tier letter (A-F)
            keyword: Keyword to remove
        
        Returns:
            True if successful, False otherwise
        """
        manager = TierKeywordsManager()
        
        # Validate tier
        if tier not in manager.tier_keywords:
            print(f"[ERROR] Invalid tier: {tier}")
            return False
        
        # Get keywords list
        keywords_list = manager.tier_keywords[tier].get("keywords", [])
        
        # Find and remove keyword (case-insensitive)
        original_length = len(keywords_list)
        keywords_list = [kw for kw in keywords_list if kw.lower() != keyword.lower()]
        
        if len(keywords_list) == original_length:
            print(f"[WARN] Keyword not found in Tier {tier}: {keyword}")
            return False
        
        manager.tier_keywords[tier]["keywords"] = keywords_list
        
        # Log the change
        manager.change_log.append({
            "timestamp": datetime.now().isoformat(),
            "action": "remove_keyword",
            "tier": tier,
            "keyword": keyword,
        })
        
        print(f"[OK] Keyword removed from Tier {tier}: {keyword}")
        return True
    
    @staticmethod
    def add_context_bonus(tier: str, keyword_pair: Tuple[str, str], bonus_points: float) -> bool:
        """
        Add a context bonus (two-word combination)
        
        Args:
            tier: Tier letter (A-F)
            keyword_pair: Tuple of two keywords
            bonus_points: Bonus points for the context
        
        Returns:
            True if successful, False otherwise
        """
        manager = TierKeywordsManager()
        
        # Validate tier
        if tier not in manager.context_bonuses:
            print(f"[ERROR] Invalid tier for context bonus: {tier}")
            return False
        
        # Add context bonus
        manager.context_bonuses[tier][keyword_pair] = bonus_points
        
        # Log the change
        manager.change_log.append({
            "timestamp": datetime.now().isoformat(),
            "action": "add_context_bonus",
            "tier": tier,
            "keyword_pair": keyword_pair,
            "bonus_points": bonus_points,
        })
        
        print(f"[OK] Context bonus added for Tier {tier}: {keyword_pair} (+{bonus_points})")
        return True
    
    @staticmethod
    def save_keywords() -> bool:
        """
        Save current keywords to custom keywords file
        
        Returns:
            True if successful, False otherwise
        """
        manager = TierKeywordsManager()
        
        try:
            # Create backup first
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = manager.KEYWORDS_BACKUP_DIR / f"tier_keywords_backup_{timestamp}.json"
            
            if manager.KEYWORDS_FILE.exists():
                import shutil
                shutil.copy(str(manager.KEYWORDS_FILE), str(backup_file))
                print(f"[OK] Backup created: {backup_file}")
            
            # Prepare data for saving
            data = {
                "tier_keywords": manager.tier_keywords,
                "context_bonuses": {
                    tier: {str(pair): bonus for pair, bonus in bonuses.items()}
                    for tier, bonuses in manager.context_bonuses.items()
                },
                "change_log": manager.change_log,
                "last_updated": datetime.now().isoformat(),
            }
            
            # Write to file
            with open(manager.KEYWORDS_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            print(f"[OK] Keywords saved to: {manager.KEYWORDS_FILE}")
            return True
            
        except Exception as e:
            print(f"[ERROR] Failed to save keywords: {e}")
            return False
    
    @staticmethod
    def load_keywords() -> bool:
        """
        Load custom keywords from file
        
        Returns:
            True if successful, False otherwise
        """
        manager = TierKeywordsManager()
        
        if not manager.KEYWORDS_FILE.exists():
            print(f"[INFO] No custom keywords file found: {manager.KEYWORDS_FILE}")
            return True  # Not an error, just use defaults
        
        try:
            with open(manager.KEYWORDS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Load tier keywords
            if "tier_keywords" in data:
                manager.tier_keywords = data["tier_keywords"]
                print(f"[OK] Tier keywords loaded from: {manager.KEYWORDS_FILE}")
            
            # Load context bonuses
            if "context_bonuses" in data:
                manager.context_bonuses = {
                    tier: {eval(pair): bonus for pair, bonus in bonuses.items()}
                    for tier, bonuses in data["context_bonuses"].items()
                }
                print(f"[OK] Context bonuses loaded")
            
            return True
            
        except Exception as e:
            print(f"[ERROR] Failed to load keywords: {e}")
            return False
    
    @staticmethod
    def get_keywords_summary() -> str:
        """
        Get a summary of current keywords
        
        Returns:
            Formatted summary string
        """
        manager = TierKeywordsManager()
        manager.load_keywords()
        
        summary = "Tier Keywords Summary\n"
        summary += "=" * 60 + "\n"
        
        for tier in ["A", "B", "C", "D", "E", "F"]:
            if tier in manager.tier_keywords:
                keywords = manager.tier_keywords[tier].get("keywords", [])
                max_score = manager.tier_keywords[tier].get("max_score", 10.0)
                summary += f"\nTier {tier} (max_score: {max_score})\n"
                summary += f"  Keywords: {len(keywords)}\n"
                for i, kw in enumerate(keywords[:5], 1):
                    summary += f"    {i}. {kw}\n"
                if len(keywords) > 5:
                    summary += f"    ... and {len(keywords) - 5} more\n"
        
        return summary
    
    @staticmethod
    def restore_backup(backup_file: str) -> bool:
        """
        Restore keywords from a backup file
        
        Args:
            backup_file: Backup filename (e.g., "tier_keywords_backup_20260202_120000.json")
        
        Returns:
            True if successful, False otherwise
        """
        manager = TierKeywordsManager()
        backup_path = manager.KEYWORDS_BACKUP_DIR / backup_file
        
        if not backup_path.exists():
            print(f"[ERROR] Backup file not found: {backup_path}")
            return False
        
        try:
            import shutil
            shutil.copy(str(backup_path), str(manager.KEYWORDS_FILE))
            print(f"[OK] Keywords restored from: {backup_file}")
            return True
        except Exception as e:
            print(f"[ERROR] Failed to restore backup: {e}")
            return False


# Convenience functions for direct usage
def add_keyword(tier: str, keyword: str, bonus_points: float = 0.0) -> bool:
    """Add keyword to tier"""
    return TierKeywordsManager.add_keyword(tier, keyword, bonus_points)


def remove_keyword(tier: str, keyword: str) -> bool:
    """Remove keyword from tier"""
    return TierKeywordsManager.remove_keyword(tier, keyword)


def add_context_bonus(tier: str, keyword_pair: Tuple[str, str], bonus_points: float) -> bool:
    """Add context bonus"""
    return TierKeywordsManager.add_context_bonus(tier, keyword_pair, bonus_points)


def save_keywords() -> bool:
    """Save keywords to file"""
    return TierKeywordsManager.save_keywords()


def load_keywords() -> bool:
    """Load keywords from file"""
    return TierKeywordsManager.load_keywords()


def get_keywords_summary() -> str:
    """Get keywords summary"""
    return TierKeywordsManager.get_keywords_summary()


def restore_backup(backup_file: str) -> bool:
    """Restore from backup"""
    return TierKeywordsManager.restore_backup(backup_file)


__all__ = [
    "TierKeywordsManager",
    "add_keyword",
    "remove_keyword",
    "add_context_bonus",
    "save_keywords",
    "load_keywords",
    "get_keywords_summary",
    "restore_backup",
]


if __name__ == "__main__":
    # CLI usage
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python tier_keywords_manager.py add <tier> <keyword>")
        print("  python tier_keywords_manager.py remove <tier> <keyword>")
        print("  python tier_keywords_manager.py save")
        print("  python tier_keywords_manager.py summary")
        print("  python tier_keywords_manager.py restore <backup_file>")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "add" and len(sys.argv) >= 4:
        tier = sys.argv[2]
        keyword = sys.argv[3]
        bonus = float(sys.argv[4]) if len(sys.argv) > 4 else 0.0
        add_keyword(tier, keyword, bonus)
        save_keywords()
    
    elif command == "remove" and len(sys.argv) >= 4:
        tier = sys.argv[2]
        keyword = sys.argv[3]
        remove_keyword(tier, keyword)
        save_keywords()
    
    elif command == "save":
        save_keywords()
    
    elif command == "summary":
        print(get_keywords_summary())
    
    elif command == "restore" and len(sys.argv) >= 3:
        backup_file = sys.argv[2]
        restore_backup(backup_file)
    
    else:
        print(f"[ERROR] Unknown command: {command}")
        sys.exit(1)
