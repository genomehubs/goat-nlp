#!/usr/bin/env python3

"""
This script is used for developing a GitHub workflow for linting.
"""

import subprocess
import os


def lint_files(directory):
    """
    Lint all Python files in the given directory using flake8.
    """
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                subprocess.run(["flake8", file_path])
    value = 1
    return value


def main():
    """
    Main function to execute the linting workflow.
    """
    directory = '/path/to/your/directory'
    lint_files(directory)

if __name__ == "__main__":
    main()
