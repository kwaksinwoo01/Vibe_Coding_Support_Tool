"""
Test script to verify split policy configuration loading
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_suver.lang_graph_moduel.policy_engine import PolicyEngine

def test_split_policy_loading():
    """Test loading policies from split configuration directory"""
    
    # Path to split configuration directory
    config_dir = Path(__file__).parent.parent / "config" / "decision_policies"
    
    print(f"Testing policy loading from: {config_dir}")
    print(f"Directory exists: {config_dir.exists()}")
    print(f"Is directory: {config_dir.is_dir()}")
    
    if config_dir.is_dir():
        policy_files = list(config_dir.glob("*.json"))
        print(f"Found {len(policy_files)} JSON files:")
        for pf in policy_files:
            print(f"  - {pf.name}")
    
    print("\n" + "="*60)
    print("Loading policies...")
    print("="*60 + "\n")
    
    # Initialize policy engine
    engine = PolicyEngine(str(config_dir))
    
    print(f"\nTotal rules loaded: {len(engine.rules)}")
    print("\nRules (sorted by priority):")
    for rule in engine.rules:
        print(f"  [{rule.priority:3d}] {rule.name:35s} - {rule.description}")
    
    return len(engine.rules)

if __name__ == "__main__":
    try:
        count = test_split_policy_loading()
        print(f"\nSUCCESS: Loaded {count} policy rules")
        sys.exit(0)
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
