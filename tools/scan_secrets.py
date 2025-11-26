#!/usr/bin/env python3
"""Quick scanner for common secret patterns to help catch accidental secrets in code.
Use: python tools/scan_secrets.py
"""
import re
import os
from pathlib import Path

PATTERNS = {
    'GROQ_KEY': re.compile(r'gsk_[A-Za-z0-9_-]{20,}'),
    'TELEGRAM_TOKEN': re.compile(r'\d{6,}:([A-Za-z0-9_-]){20,}'),
    'SUPABASE_ANON': re.compile(r'eyJ[A-Za-z0-9\-_]{10,}'),
}

def scan_directory(root: Path):
    findings = []
    for p in root.rglob('*'):
        if p.is_file() and p.suffix not in ('.png', '.jpg', '.jpeg', '.gif', '.bin'):
            try:
                txt = p.read_text(errors='ignore')
            except Exception:
                continue
            for name, pat in PATTERNS.items():
                for m in pat.finditer(txt):
                    findings.append((str(p), name, m.group(0)))
    return findings

def main():
    root = Path(__file__).parents[1]
    print('Scanning', root)
    findings = scan_directory(root)
    if findings:
        print('Found potential secrets:')
        for fpath, kind, val in findings:
            print(f'- {kind} in {fpath}: {val[:40]}...')
        return 1
    else:
        print('No obvious secrets found.')
        return 0

if __name__ == '__main__':
    raise SystemExit(main())
