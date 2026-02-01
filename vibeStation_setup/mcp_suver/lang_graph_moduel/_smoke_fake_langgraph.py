import sys
import types
from pathlib import Path
import importlib.util

# Create fake langgraph
mod = types.ModuleType('langgraph')
class FakeGraph:
    def __init__(self, name=None):
        self.name = name or "fake"
        self.nodes = []
        self.transitions = []
    def add_state(self, nid, **meta):
        self.nodes.append((nid, meta))
    def add_transition(self, src, dst, **meta):
        self.transitions.append((src, dst, meta))
    def to_dict(self):
        return {"name": self.name, "nodes": [n for n,_ in self.nodes], "transitions": [(s,d) for s,d,_ in self.transitions]}
setattr(mod, 'Graph', FakeGraph)
setattr(mod, 'StateGraph', FakeGraph)

sys.modules['langgraph'] = mod
sys.modules['langgraph.graph'] = mod

# Ensure models path available (point to sibling models directory in tool)
models_dir = Path(__file__).parent.parent / 'models'
sys.path.insert(0, str(models_dir))

# Load main_agent from tool directory (resolve relative to this file)
orchestrator_path = Path(__file__).parent.parent / 'main_agent.py'
spec = importlib.util.spec_from_file_location('tfg', str(orchestrator_path))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
print('LANGGRAPH_AVAILABLE:', getattr(mod, 'LANGGRAPH_AVAILABLE', None))
print('graph repr:', repr(mod.graph))
print('graph to_dict:', getattr(mod.graph, 'to_dict', lambda: None)())

# Cleanup
try:
    del sys.modules['langgraph']
    del sys.modules['langgraph.graph']
except Exception:
    pass
