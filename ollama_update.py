#!/usr/bin/env python3

# curl -fsSL https://ollama.com/install.sh | OLLAMA_VERSION=0.4.0-rc6 sh

import argparse
import subprocess
import getpass
import os
import sys

__version__ = "1.0.0"

def execute_shell_command(command, require_sudo=False):
    if require_sudo:
        command = f"sudo {command}"
    try:
        subprocess.run(command, shell=True, check=True, executable='/bin/bash')
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {e}")

def update_ollama(version=None):
    # Step 1: Download the script
    execute_shell_command("curl -fsSL -o /tmp/update_ollama.sh https://ollama.com/install.sh")
    # Step 2: Make the script executable
    execute_shell_command("chmod +x /tmp/update_ollama.sh")
    # Step 3: Execute the script with elevated privileges
    if version:
        execute_shell_command(f"OLLAMA_VERSION={version} /tmp/update_ollama.sh", require_sudo=True)
    else:
        execute_shell_command("/tmp/update_ollama.sh", require_sudo=True)

def setup_sudoers():
    """Setup sudoers file for the current user.
    
    This function will:
    1. Create a sudoers file for the current user
    2. Set proper permissions and ownership
    3. Ensure the user can run the update script without password
    """
    username = getpass.getuser()
    sudoers_content = f"{username} ALL=(ALL) NOPASSWD: /tmp/update_ollama.sh\n"
    sudoers_file = "/etc/sudoers.d/ollama-update"
    temp_file = "/tmp/ollama-sudoers.tmp"
    
    try:
        print(f"Setting up sudoers for user {username}")
        
        # Create temporary file with content
        with open(temp_file, "w") as file:
            file.write(sudoers_content)
        
        # Set correct permissions on temp file
        os.chmod(temp_file, 0o644)
        
        # Move temp file to sudoers.d with sudo
        result = subprocess.run(['sudo', 'mv', temp_file, sudoers_file], 
                             capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Error moving file: {result.stderr}")
            raise subprocess.CalledProcessError(result.returncode, result.args)
        
        # Set correct ownership (root:root)
        result = subprocess.run(['sudo', 'chown', 'root:root', sudoers_file], 
                             capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Error setting ownership: {result.stderr}")
            raise subprocess.CalledProcessError(result.returncode, result.args)
        
        # Set correct permissions (0440)
        result = subprocess.run(['sudo', 'chmod', '0440', sudoers_file], 
                             capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Error setting permissions: {result.stderr}")
            raise subprocess.CalledProcessError(result.returncode, result.args)
        
        print(f"Successfully set up sudoers for user {username}")
        print(f"Sudoers file created at {sudoers_file}")
        
    except IOError as e:
        print(f"IOError managing sudoers file: {e}")
        raise
    except subprocess.CalledProcessError as e:
        print(f"Command failed with error: {e}")
        print(f"Command output: {e.output if hasattr(e, 'output') else 'No output'}")
        raise
    except Exception as e:
        print(f"Unexpected error: {e}")
        raise
    finally:
        # Clean up temp file if it exists
        if os.path.exists(temp_file):
            os.remove(temp_file)

def add_env_variables(service_file_path):
    env_vars = [
        'Environment="OLLAMA_HOST=0.0.0.0:11434"',
        'Environment="OLLAMA_ORIGINS=*"'
    ]
    additional_lines = [
        'EnvironmentFile=/etc/default/ollama',
        'ExecStartPre=/bin/bash -c \'if [ -f /etc/default/ollama ]; then echo "Loaded environment file: /etc/default/ollama"; fi\''
    ]
    changes_made = False
    try:
        with open(service_file_path, "r") as file:
            lines = file.readlines()

        # Find the insert position which is either right before [Install] or at the end of the file
        insert_pos = None
        for i, line in enumerate(lines):
            if line.strip().startswith("[Install]"):
                insert_pos = i
                break

        # If [Install] section is found, ensure there's a newline before it for separation
        if insert_pos is not None:
            # Ensure there's exactly one newline before [Install]
            if lines[insert_pos - 1].strip() != "":
                lines.insert(insert_pos, "\n")
                insert_pos += 1  # Adjust insert_pos because of the new newline
        else:
            # If [Install] section wasn't found, prepare to add at the end with a preceding newline
            insert_pos = len(lines)
            if lines[-1].strip() != "":
                lines.append("\n")

        # Add additional lines if they are not already in the file
        for additional_line in additional_lines:
            if not any(additional_line in line for line in lines):
                lines.insert(insert_pos, additional_line + "\n")
                insert_pos += 1  # Increment insert position for the next variable
                changes_made = True

        # Write changes if any
        if changes_made:
            temp_file_path = "/tmp/ollama.service"
            with open(temp_file_path, "w") as temp_file:
                temp_file.writelines(lines)
            execute_shell_command(f"sudo mv {temp_file_path} {service_file_path}", require_sudo=True)

    except IOError as e:
        print(f"Error reading or writing to {service_file_path}: {e}")
    return changes_made


def reload_and_restart_service():
    execute_shell_command("sudo systemctl daemon-reload", require_sudo=True)
    execute_shell_command("sudo systemctl restart ollama.service", require_sudo=True)

def list_versions():
    """List available Ollama versions from GitHub releases."""
    try:
        import json
        import requests
        
        response = requests.get('https://api.github.com/repos/ollama/ollama/releases')
        if response.status_code == 200:
            releases = response.json()
            print("\nAvailable Ollama versions:")
            for release in releases:
                version = release['tag_name'].lstrip('v')  # Remove 'v' prefix
                print(f"  {version}")
            print("\nUse --set-version with the version number to install a specific version.")
        else:
            print(f"Error fetching versions: HTTP {response.status_code}")
    except Exception as e:
        print(f"Error listing versions: {e}")

def main():
    username = getpass.getuser()  # Dynamically get the current username
    parser = argparse.ArgumentParser(description='Ollama service updater script.')
    parser.add_argument('--setup', action='store_true', help='Setup sudoers for the current user')
    parser.add_argument('--version', action='version', version=f'%(prog)s {__version__}')
    parser.add_argument('--set-version', type=str, help='Specify a specific version to install (e.g., 0.4.0-rc6)')
    parser.add_argument('--list-versions', action='store_true', help='List available Ollama versions')
    
    try:
        args = parser.parse_args()
    except argparse.ArgumentError as e:
        parser.print_help()
        print(f"\nError: {e}")
        sys.exit(1)

    service_file_path = "/etc/systemd/system/ollama.service"

    if args.setup:
        setup_sudoers()
    elif args.list_versions:
        list_versions()
    else:
        update_ollama(args.set_version)
        if add_env_variables(service_file_path):
            reload_and_restart_service()

if __name__ == "__main__":
    main()

