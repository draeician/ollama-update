# Ollama Update Script

This repository contains a Python script to automate the process of downloading, installing, and configuring the Ollama service on your system.  I wrote this so I wouldn't have to lookup the update script, and handle little tweaks I have to do after updates.  It still uses the installation scripts that the Ollama team provides, but insures I don't miss anything.

## Features

- Automatically installs or updates to the latest version of Ollama.
- Allows specifying a specific version to install.
- Adds optional environment variables to the Ollama systemd service.
- Provides command-line autocompletion support.
- Optionally sets up passwordless sudo for updating.
- Warns about potential version mismatches if using a remote OLLAMA\_HOST.
- Automatically restarts the Ollama service if the systemd service file is updated.

## Installation

Clone the repository:

```bash
git clone https://github.com/draeician/ollama-update.git
cd ollama-update
```

Make sure the script is executable:

```bash
chmod +x ollama-update.py
./ollama-update.py --setup
```

You will be prompted for your password, as installation requires sudo access.

Run the script with any of the following options:

- `--setup`: Install the script to `/usr/local/bin`, configure sudoers to allow updates without a password, and set up autocompletion.
- `--version`: Display the current version of the script.
- `--set-version <version>`: Install a specific Ollama version.
- `--list-versions`: List available Ollama versions from GitHub.
- `--update`: Pull the latest version of this script from the GitHub repository and overwrite the local script.

### Examples

Install the latest version of Ollama:

```bash
./ollama-update.py
```

Install a specific version:

```bash
./ollama-update.py --set-version 0.4.0-rc6
```

List available versions:

```bash
./ollama-update.py --list-versions
```

Update this script from the GitHub repo:

```bash
./ollama-update.py --update
```

Setup system for passwordless updates, copy to /usr/local/bin,  and autocompletion:

```bash
./ollama-update.py --setup
```

## Author

- **Draeician**
- Email: [draeician@gmail.com](mailto\:draeician@gmail.com)

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

