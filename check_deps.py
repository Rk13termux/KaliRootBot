"""
Check required Python packages for the bot service and provide actionable output for VSCode/Pylance.

Usage:
  python check_deps.py

Outputs a colored result with suggestions to pip install missing packages and how to set the VSCode interpreter.
"""

import importlib
import sys

REQUIRED = [
    ("supabase", "Supabase client (pip package: supabase or supabase-py)"),
    ("groq", "Groq client (pip package: groq)")
]


def check_pkg(name):
    try:
        importlib.import_module(name)
        return True
    except Exception:
        return False


def main():
    print("Checking required packages...")
    missing = []
    for pkg, desc in REQUIRED:
        ok = check_pkg(pkg)
        print(f"- {pkg}: {'OK' if ok else 'MISSING'} - {desc}")
        if not ok:
            missing.append(pkg)

    if missing:
        print("\nMissing packages detected:")
        for m in missing:
            print(f"* {m}")
        print("\nSuggested commands:")
        print("# Activate your virtualenv first, for example:")
        print("# python -m venv venv")
        print("# source venv/bin/activate")
        print("pip install -r requirements.txt")
        print("# or explicitly:")
        print("pip install supabase groq python-dotenv")
        print("\nIn VSCode, make sure to select the correct interpreter (Command Palette -> Python: Select Interpreter -> choose ./venv/bin/python) and then reload the window.")
        sys.exit(2)
    else:
        print("\nAll required packages appear to be present.")


if __name__ == '__main__':
    main()
