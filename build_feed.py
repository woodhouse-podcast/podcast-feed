#!/usr/bin/env python3
"""Minimal feed builder placeholder.

Later we'll:
- read podcasts.txt
- fetch each RSS
- pick episodes by rules
- write docs/curated.xml

For now it just keeps the skeleton valid.
"""
from pathlib import Path

def main():
    # no-op for now
    p = Path('docs/curated.xml')
    if not p.exists():
        raise SystemExit('Missing docs/curated.xml')
    print('OK (no-op)')

if __name__ == '__main__':
    main()
