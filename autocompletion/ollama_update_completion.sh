#!/usr/bin/env bash

_ollama_update_completions() {
    local cur prev opts
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"
    opts="--setup --version --set-version --list-versions"

    case "${prev}" in
        --set-version)
            # Fetch available versions from GitHub API
            local versions
            versions=$(curl -s https://api.github.com/repos/ollama/ollama/releases | 
                      grep -o '"tag_name": "[^"]*"' | 
                      sed 's/"tag_name": "v//;s/"//' | 
                      tr '\n' ' ')
            COMPREPLY=( $(compgen -W "${versions}" -- ${cur}) )
            return 0
            ;;
        *)
            COMPREPLY=( $(compgen -W "${opts}" -- ${cur}) )
            return 0
            ;;
    esac
}

complete -F _ollama_update_completions ollama_update.py 