import sys
from pathlib import Path
import importlib.util

# Add tool models to sys.path so module-level imports resolve
models_dir = Path(__file__).parent.parent / 'models'
sys.path.insert(0, str(models_dir))

# Load main_agent from tool directory (resolve relative to this file)
orchestrator_path = Path(__file__).parent.parent / 'main_agent.py'
spec = importlib.util.spec_from_file_location('t', str(orchestrator_path))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
print('Imported module:', repr(mod))
print('graph:', repr(mod.graph))
print('LANGGRAPH_AVAILABLE:', mod.LANGGRAPH_AVAILABLE)
print('build_orchestrator_graph(enrich=True):', mod.build_orchestrator_graph(enrich=True))
