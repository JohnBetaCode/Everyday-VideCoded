#!/bin/bash
set -e

# Points git to the tracked .githooks directory so all contributors
# get the same hooks without any manual copying.
git config core.hooksPath .githooks
chmod +x .githooks/*

echo "Git hooks installed from .githooks/"
