#!/usr/bin/env python3

# curl -fsSL https://ollama.com/install.sh | OLLAMA_VERSION=0.4.0-rc6 sh

import argparse
import subprocess
import getpass
import os
import sys
import shutil
import hashlib

__version__ = "1.3.3"

def execute_shell_command(command, require_sudo=False):
    if require_sudo:
        command = f"sudo {command}"
    try:
        subprocess.run(command, shell=True, check=True, executable='/bin/bash')
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {e}")

def update_ollama(version=None):
    # Define the temporary directory path
    tmp_dir = '/tmp/ollama-update'

    # Check if the directory exists
    if os.path.exists(tmp_dir):
        # Remove the directory
        shutil.rmtree(tmp_dir)

    # Step 1: Download the script
    execute_shell_command("curl -fsSL -o /tmp/update_ollama.sh https://ollama.com/install.sh")
    # Step 2: Make the script executable
    execute_shell_command("chmod +x /tmp/update_ollama.sh")
    # Step 3: Execute the script with elevated privileges
    if version:
        execute_shell_command(f"OLLAMA_VERSION={version} /tmp/update_ollama.sh", require_sudo=True)
    else:
        execute_shell_command("/tmp/update_ollama.sh", require_sudo=True)

def check_version_mismatch():
    """Check for potential version mismatch between client and server."""
    if 'OLLAMA_HOST' in os.environ:
        try:
            # Get client version
            result = subprocess.run(['ollama', '--version'], 
                                 capture_output=True, text=True)
            if result.returncode == 0:
                client_version = result.stdout.strip()
                print("\nWarning: OLLAMA_HOST environment variable is set.")
                print("This means you're connecting to a remote Ollama server.")
                print("There might be version mismatches between your client and server.")
                print(f"Current client version: {client_version}")
                print("Please ensure your remote server version matches your client version.")
                print("You can check the server version with: curl $OLLAMA_HOST/version")
        except Exception as e:
            print(f"Warning: Could not check Ollama version: {e}")

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
        
        # Check for version mismatch
        check_version_mismatch()
        
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
        
        # Copy the script to /usr/local/bin
        script_path = os.path.abspath(__file__)
        destination_path = f"/usr/local/bin/{os.path.basename(script_path)}"
        execute_shell_command(f"sudo cp {script_path} {destination_path}", require_sudo=True)
        execute_shell_command(f"sudo chmod +x {destination_path}", require_sudo=True)
        print(f"Script installed to {destination_path}")
        
        # Register shell completion for Bash
        completion_script = f"complete -W '--setup --version --set-version --list-versions --update' {os.path.basename(script_path)}"
        completion_file = "/etc/bash_completion.d/ollama-update"
        with open(temp_file, "w") as file:
            file.write(completion_script)
        execute_shell_command(f"sudo mv {temp_file} {completion_file}", require_sudo=True)
        execute_shell_command(f"sudo chmod 644 {completion_file}", require_sudo=True)
        print(f"Bash completion script installed to {completion_file}")
        
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

def files_are_identical(file1, file2):
    """Compare two files by their hash to determine if they are identical."""
    hash1 = hashlib.sha256()
    hash2 = hashlib.sha256()

    with open(file1, 'rb') as f1, open(file2, 'rb') as f2:
        while chunk := f1.read(8192):
            hash1.update(chunk)
        while chunk := f2.read(8192):
            hash2.update(chunk)

    return hash1.digest() == hash2.digest()

def update_script():
    """Update the script by pulling the latest version from the Git repository."""
    repo_url = "https://github.com/draeician/ollama-update.git"  # Replace with your actual repository URL
    tmp_dir = "/tmp/ollama-update"

    # Check if the directory exists
    if os.path.exists(tmp_dir):
        # Remove the directory
        shutil.rmtree(tmp_dir)

    try:
        # Clone the repository to /tmp
        execute_shell_command(f"git clone {repo_url} {tmp_dir}")
        
        # Determine the script paths
        script_name = os.path.basename(__file__)
        updated_script_path = os.path.join(tmp_dir, script_name)
        current_script_path = os.path.abspath(__file__)

        # Check if the source and destination are the same
        if not files_are_identical(updated_script_path, current_script_path):
            # Copy the updated script to the current location
            execute_shell_command(f"sudo cp {updated_script_path} {current_script_path}", require_sudo=True)
        else:
            print("No need to copy, the files are identical.")
        
        print("Script updated successfully. Please restart the script.")
    except subprocess.CalledProcessError as e:
        print(f"Error updating script: {e}")
    except Exception as e:
        print(f"Unexpected error during update: {e}")

def main():
    username = getpass.getuser()  # Dynamically get the current username
    parser = argparse.ArgumentParser(description='Ollama service updater script.')
    parser.add_argument('--setup', action='store_true', help='Setup sudoers for the current user')
    parser.add_argument('--version', action='version', version=f'%(prog)s {__version__}')
    parser.add_argument('--set-version', type=str, help='Specify a specific version to install (e.g., 0.4.0-rc6)')
    parser.add_argument('--list-versions', action='store_true', help='List available Ollama versions')
    parser.add_argument('--update', action='store_true', help='Update the script to the latest version from the repository')
    
    try:
        args = parser.parse_args()
        
        if args.update:
            update_script()
            sys.exit(0)
        
        service_file_path = "/etc/systemd/system/ollama.service"

        if args.setup:
            setup_sudoers()
        elif args.list_versions:
            list_versions()
        else:
            update_ollama(args.set_version)
            if add_env_variables(service_file_path):
                reload_and_restart_service()
    except argparse.ArgumentError as e:
        parser.print_help()
        print(f"\nError: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

