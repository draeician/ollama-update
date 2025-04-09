#!/usr/bin/env bash

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root"
    exit 1
fi

# Copy completion script to bash_completion.d
cp ollama_update_completion.sh /etc/bash_completion.d/ollama_update

# Set correct permissions
chmod 644 /etc/bash_completion.d/ollama_update

echo "Bash completion for ollama_update.py has been installed."
echo "Please restart your terminal or run: source /etc/bash_completion.d/ollama_update" 