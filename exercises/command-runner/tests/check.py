"""Verify command parsing and ownership without spawning parsed commands."""
import subprocess
import sys
import tempfile
from pathlib import Path

def run(line):
    return subprocess.run([sys.argv[1], line], capture_output=True, text=True, timeout=8)

def main():
    cases = {
        'echo hello': '0:0:echo\n0:1:hello\n',
        'echo "two words" \'\'': '0:0:echo\n0:1:two words\n0:2:\n',
        r'echo a\ b | cat': '0:0:echo\n0:1:a b\n1:0:cat\n',
        'echo ' + 'a' * 2048: '0:0:echo\n0:1:' + 'a' * 2048 + '\n',
    }
    for line, expected in cases.items():
        result = run(line)
        assert result.returncode == 0 and result.stdout == expected, result
    for line in ('', ' ', '| echo', 'echo |', 'a | b | c', 'echo "open', 'echo > file', 'a; b', 'a & b', 'echo \\'):
        result = run(line)
        assert result.returncode == 2 and not result.stdout and 'Syntax error' in result.stderr, result
    with tempfile.TemporaryDirectory() as directory:
        marker = Path(directory) / 'must-not-exist'
        result = run(f'touch {marker}')
        assert result.returncode == 0 and not marker.exists()
    print('Parser contracts passed')

if __name__ == '__main__':
    main()
