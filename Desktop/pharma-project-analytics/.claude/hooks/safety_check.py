#!/usr/bin/env python3
"""
PreToolUse safety hook for Pharma Project Analytics.
Blocks dangerous commands and unauthorized access.
"""

import sys
import re
from pathlib import Path


def is_dangerous_deletion(command: str) -> bool:
    """Detect destructive deletion patterns."""
    dangerous_patterns = [
        r'\brm\s+-[a-z]*f',  # rm -f, rm -rf, etc.
        r'\brm\s+.*\*',       # rm with wildcards
        r'\brmdir\b',         # rmdir command
    ]
    for pattern in dangerous_patterns:
        if re.search(pattern, command):
            return True
    return False


def is_secret_access(command: str) -> bool:
    """Detect attempts to access .env, credentials, or secrets."""
    secret_patterns = [
        r'\.env',
        r'secret',
        r'credential',
        r'password',
        r'token',
        r'api.?key',
        r'private.?key',
    ]
    for pattern in secret_patterns:
        if re.search(pattern, command, re.IGNORECASE):
            return True
    return False


def is_credential_exposure(command: str) -> bool:
    """Detect attempts to print/echo credentials or expose sensitive vars."""
    if 'echo' in command or 'cat' in command:
        if any(word in command.lower() for word in ['secret', 'password', 'token', 'key']):
            return True
    return False


def is_outside_project(command: str, project_root: str) -> bool:
    """Detect commands operating outside the project directory."""
    # Allow certain safe system commands
    safe_commands = ['python', 'pip', 'git', 'mkdir', 'touch', 'ls', 'pwd', 'cd']
    if any(command.strip().startswith(cmd) for cmd in safe_commands):
        return False

    # Block absolute paths outside project
    if command.startswith('/') and not command.startswith(project_root):
        return True

    # Block parent directory traversal attempts
    if '../' in command and command.count('../') > 2:
        return True

    return False


def check_safety(command: str, tool_name: str, project_root: str = '.') -> tuple[bool, str]:
    """
    Check if a command is safe to execute.
    Returns (is_safe, reason).
    """
    # Skip empty commands
    if not command.strip():
        return True, ''

    # Check for dangerous deletions
    if is_dangerous_deletion(command):
        return False, 'Destructive deletion blocked (rm -rf, rm -f patterns)'

    # Check for secret file access
    if is_secret_access(command):
        return False, 'Access to .env, secrets, or credentials blocked'

    # Check for credential exposure
    if is_credential_exposure(command):
        return False, 'Credential exposure pattern detected'

    # Check for operations outside project
    if is_outside_project(command, project_root):
        return False, 'Command operates outside project directory'

    return True, ''


if __name__ == '__main__':
    # Example usage for testing
    test_cases = [
        ('rm -rf .env', False),
        ('rm -f src/*.py', False),
        ('cat .env', False),
        ('echo $DB_PASSWORD', False),
        ('git add .', True),
        ('python src/main.py', True),
        ('mkdir src', True),
        ('ls -la docs/', True),
        ('../../../etc/passwd', False),
    ]

    for command, expected_safe in test_cases:
        is_safe, reason = check_safety(command, 'bash')
        status = '✓' if is_safe == expected_safe else '✗'
        result = f"{status} {command}: {'safe' if is_safe else 'blocked'}"
        if reason:
            result += f" ({reason})"
        print(result)
