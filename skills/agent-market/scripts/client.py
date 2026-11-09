"""Use the bundled dependency-free client; never install or register implicitly."""
from pathlib import Path
import json
import sys


def main():
    root = Path(__file__).resolve().parents[3]
    package = root / 'agent_market'
    if not (package / 'cli.py').is_file() or not (package / '__init__.py').is_file():
        print(json.dumps({'ok': False, 'error': {'code': 'client_not_bundled',
            'message': 'Use the full plugin archive, or install the reviewed Alpha5 wheel and run agent-market. No installation was attempted.'}}), file=sys.stderr)
        return 2
    sys.path.insert(0, str(root))
    from agent_market.cli import main as client_main
    return client_main()


if __name__ == '__main__':
    sys.exit(main())
