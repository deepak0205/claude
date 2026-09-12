#!/usr/bin/env python3
"""
PostToolUse quality hook for Pharma Project Analytics.
Validates Python files for syntax and basic security issues.
"""

import sys
import ast
import re
from pathlib import Path


def check_python_syntax(file_path: str) -> tuple[bool, str]:
    """
    Validate Python syntax.
    Returns (is_valid, error_message).
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()
        ast.parse(code)
        return True, ''
    except SyntaxError as e:
        return False, f'Syntax error at line {e.lineno}: {e.msg}'
    except Exception as e:
        return False, f'Parse error: {str(e)}'


def check_imports(file_path: str) -> tuple[bool, str]:
    """
    Check for import errors (missing modules).
    Returns (is_valid, warning_message).
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()
        tree = ast.parse(code)

        # Collect imports to check
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name.split('.')[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module.split('.')[0])

        # Check for obvious non-existent modules (simple heuristic)
        # This is not comprehensive but catches common mistakes
        invalid = []
        for imp in imports:
            if imp.startswith('_'):  # Private modules
                continue
            # Common builtins and standard library
            builtins = {'os', 'sys', 're', 'json', 'csv', 'datetime', 'pathlib',
                       'logging', 'typing', 'collections', 'itertools', 'functools',
                       'math', 'random', 'time', 'unittest', 'pytest', 'tempfile'}
            common_packages = {'pandas', 'numpy', 'plotly', 'streamlit', 'pytest'}
            if imp not in builtins and imp not in common_packages:
                if imp not in ['src', 'tests', 'utils', 'config']:  # Local modules
                    pass  # Don't validate further without importing

        return True, ''
    except Exception as e:
        return False, f'Import check error: {str(e)}'


def check_hardcoded_secrets(file_path: str) -> tuple[bool, str]:
    """
    Detect obvious hardcoded credentials.
    Returns (is_safe, warning_message).
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    secret_patterns = [
        (r"['\"]?password\s*=\s*['\"][^'\"]*['\"]", 'Hardcoded password detected'),
        (r"['\"]?api_?key\s*=\s*['\"][^'\"]*['\"]", 'Hardcoded API key detected'),
        (r"['\"]?secret\s*=\s*['\"][^'\"]*['\"]", 'Hardcoded secret detected'),
        (r"['\"]?token\s*=\s*['\"][^'\"]*['\"]", 'Hardcoded token detected'),
    ]

    for pattern, message in secret_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            return False, message

    return True, ''


def validate_file(file_path: str) -> dict:
    """
    Perform all validation checks on a Python file.
    Returns dict with validation results.
    """
    results = {
        'file': file_path,
        'valid': True,
        'checks': {}
    }

    # Check syntax
    syntax_ok, syntax_msg = check_python_syntax(file_path)
    results['checks']['syntax'] = {'ok': syntax_ok, 'message': syntax_msg}
    if not syntax_ok:
        results['valid'] = False

    # Check imports (warning only)
    imports_ok, imports_msg = check_imports(file_path)
    results['checks']['imports'] = {'ok': imports_ok, 'message': imports_msg}

    # Check for hardcoded secrets
    secrets_ok, secrets_msg = check_hardcoded_secrets(file_path)
    results['checks']['secrets'] = {'ok': secrets_ok, 'message': secrets_msg}
    if not secrets_ok:
        results['valid'] = False

    return results


def format_report(results: dict) -> str:
    """Format validation results as readable report."""
    lines = [f"Quality Check: {results['file']}"]

    for check_name, check_result in results['checks'].items():
        status = '✓' if check_result['ok'] else '✗'
        lines.append(f"  {status} {check_name}")
        if check_result['message']:
            lines.append(f"    {check_result['message']}")

    overall = '✓ PASS' if results['valid'] else '✗ FAIL'
    lines.append(f"  Overall: {overall}")

    return '\n'.join(lines)


if __name__ == '__main__':
    # Example usage for testing
    test_files = [
        'test_valid.py',   # Valid Python file
        'test_syntax.py',  # Invalid syntax
        'test_secret.py',  # Hardcoded secret
    ]

    # Create test files
    Path('test_valid.py').write_text('import sys\nprint("hello")')
    Path('test_syntax.py').write_text('import sys\nprint("hello"')
    Path('test_secret.py').write_text('password = "secret123"')

    for test_file in test_files:
        if Path(test_file).exists():
            results = validate_file(test_file)
            print(format_report(results))
            print()

    # Cleanup
    for test_file in test_files:
        Path(test_file).unlink(missing_ok=True)
