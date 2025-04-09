#!/usr/bin/env python3

# curl -fsSL https://ollama.com/install.sh | OLLAMA_VERSION=0.4.0-rc6 sh

import argparse
import subprocess
import getpass
import os

__version__ = "1.0.0"

def execute_shell_command(command, require_sudo=False):
    if require_sudo:
        command = f"sudo {command}"
    try:
        subprocess.run(command, shell=True, check=True, executable='/bin/bash')
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {e}")

def update_ollama():
    # Step 1: Download the script
    execute_shell_command("curl -fsSL -o /home/draeician/pappas_bag/update_ollama.sh https://ollama.com/install.sh")
    # Step 2: Make the script executable
    execute_shell_command("chmod +x /home/draeician/pappas_bag/update_ollama.sh")
    # Step 3: Execute the script with elevated privileges
    execute_shell_command("/home/draeician/pappas_bag/update_ollama.sh", require_sudo=True)

def setup_sudoers():
    username = getpass.getuser()
    sudoers_content = f"{username} ALL=(ALL) NOPASSWD: /usr/local/bin/update_ollama.sh\n"
    sudoers_file = "/etc/sudoers.d/ollama-update"
    try:
        with open(sudoers_file, "w") as file:
            file.write(sudoers_content)
        print("Sudoers file updated. Please ensure correctness manually.")
    except IOError as e:
        print(f"Error writing to {sudoers_file}: {e}")

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

def main():
    username = getpass.getuser()  # Dynamically get the current username
    parser = argparse.ArgumentParser(description='Ollama service updater script.')
    parser.add_argument('--setup', action='store_true', help='Setup sudoers for ollama update script.')
    parser.add_argument('--version', action='version', version=f'%(prog)s {__version__}')
    args = parser.parse_args()

    service_file_path = "/etc/systemd/system/ollama.service"

    if args.setup:
        setup_sudoers()
    else:
        update_ollama()
        if add_env_variables(service_file_path):
            reload_and_restart_service()

if __name__ == "__main__":
    main()

