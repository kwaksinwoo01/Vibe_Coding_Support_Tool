import importlib

candidates = [
    'langgraph',
    'langgraph.graph',
    'langgraph.builder',
    'langgraph.graph.state_graph',
]

for name in candidates:
    print('--- Trying', name)
    try:
        mod = importlib.import_module(name)
        print('Loaded:', mod)
        attrs = dir(mod)
        print('Attributes sample:', attrs[:40])
        # Try to find classes named Graph/StateGraph
        for clsname in ['Graph', 'StateGraph', 'State', 'Node', 'Transition', 'Builder']:
            if clsname in attrs:
                cls = getattr(mod, clsname)
                print(f'Found class {clsname} in {name}:', cls)
                try:
                    sig = getattr(cls, '__init__', None)
                    print('  __init__ signature present')
                except Exception:
                    pass
    except Exception as e:
        print('Error importing', name, e)
