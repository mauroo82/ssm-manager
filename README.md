# SSM Manager (AWS)
A desktop application for managing SSM session on AWS cloud with a user-friendly GUI interface.

![Screenshot](image/screenshot4.jpg)

  - [Description](#description)
  - [Features](#features)
    - [Core Functionality](#core-functionality)
    - [Instance Management](#instance-management)
    - [Connection Types](#connection-types)
    - [Active Connection Management](#active-connection-management)
    - [Additional Features](#additional-features)
  - [Requirements](#Requirements)
  - [Installation](#installation)
  - [Windows Security Warning](#windows-security-warning)
  - [Usage](#usage)
  - [Development](#development)
    - [Requirements](#requirements)
    - [Setup Development Environment](#setup-development-environment)
    - [Building from Source](#building-from-source)
  - [Contributing](#contributing)
  - [Bug reports](#bug-reports)
  - [License](#license)
  - [Acknowledgments](#acknowledgments)
  - [Support](#support)


## Description

SSM Manager is a Windows desktop application that provides a graphical interface for managing AWS Systems Manager sessions. It simplifies the process of connecting to EC2 instances through AWS Systems Manager by providing an intuitive interface for SSH sessions, RDP connections, custom port forwarding, and host port forwarding.

## Features

### Core Functionality
- **Profile and Region Management**
  - Easy switching between AWS profiles
  - Region selection
  - Connection status monitoring
  - Profile preferences persistence

### Instance Management
- **Instance Listing**
  - Display of EC2 instances with SSM capability
  - Real-time instance status updates
  - Instance details (Name, ID, Type, OS, State, IP Address ecc..)

### Connection Types
- **SSH Sessions**
  - Direct SSH connection to instances
  - Session monitoring and management
  - Automatic session cleanup

- **RDP Connections**
  - Automated RDP port forwarding setup
  - Integration with Windows Remote Desktop
  - Dynamic local port allocation

- **Port Forwarding**
  - User-defined port forwarding
  - Dynamic local port assignment
  - Connection monitoring
  - Remote host connection through instances
  - Custom remote host and port configuration
  - Automatic local port management
  

### Active Connection Management
- Real-time connection status monitoring
- Active session termination
- Connection details display

### Additional Features
- Logging system with configurable levels
- Custom TPC port on local forwarding
- Refresh AWS profiles without restarting the app
- Support for AWS SSO, role_arn and Leapp profiles (reads both `~/.aws/credentials` and `~/.aws/config`)
- Paginated EC2/SSM instance listing (supports environments with more than 50 instances)
- Dark mode toggle in Settings (persisted across sessions)

## Requirements

- Windows 10 - 11 operating system
- AWS CLI installed and configured [[instructions here](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)]
- AWS SSM Plugin for AWS CLI installed [instructions here](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-install-plugin.html)
- Valid AWS credentials configured or alternative install and configure Leapp [[instructions here](https://github.com/Noovolari/leapp)]

## Installation

1. Download the latest release from the releases page [**HERE**](https://github.com/mauroo82/ssm-manager/releases/latest).
2. Run the installer `SSM-Manager-vX.Y-setup.exe`.
3. If Windows SmartScreen shows a security warning, see the [Windows Security Warning](#windows-security-warning) section below.
4. Ensure that AWS CLI and SSM Plugin are installed.
   ```bash
   aws --version
   aws ssm start-session --version
   ```
5. Choose one of the following methods to configure AWS access:
   - **Option A**: Configure AWS CLI and log in to AWS. [**Instructions here**](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
   - **Option B**: Install and configure Leapp, then log in to AWS. [**Instructions here**](https://github.com/Noovolari/leapp)
6. Launch **SSM Manager**.
7. You must have the SSM agent installed on your EC2 to show all features on SSM Manager
8. Verify proper IAM permissions for SSM sessions


## Windows Security Warning

> 🇬🇧 **English**
>
> When running the installer for the first time, Windows SmartScreen may display a warning:
> **"Windows protected your PC"**.
> This happens because the application is not yet signed with a commercial code-signing certificate.
> The application is fully open source — you can review the complete source code in this repository.
>
> **To proceed:**
> 1. Click **"More info"** in the warning dialog.
> 2. Click **"Run anyway"**.
>
> The installer will then proceed normally.

---

> 🇮🇹 **Italiano**
>
> Al primo avvio dell'installer, Windows SmartScreen potrebbe mostrare un avviso:
> **"Il PC è stato protetto da Windows"**.
> Questo accade perché l'applicazione non è ancora firmata con un certificato di firma del codice commerciale.
> L'applicazione è completamente open source — puoi verificare l'intero codice sorgente in questo repository.
>
> **Per procedere:**
> 1. Clicca su **"Ulteriori informazioni"** nella finestra di avviso.
> 2. Clicca su **"Esegui comunque"**.
>
> L'installer procederà normalmente.

---

## Usage

1. Launch the application
2. Select your AWS profile and region
3. Click "Connect" to view available instances
4. Use the action buttons to establish connections:
   - SSH: Direct terminal access
   - RDP: Remote desktop connection
   - PORT: Custom port forwarding

## Development

### Requirements
- Python 3.12+
- flask
- boto3
- psutil
- webview
- requirements.txt for more details

### Setup Development Environment
```bash
git clone https://github.com/yourusername/aws-ssm-manager.git
cd aws-ssm-manager
pip install -r requirements.txt
```

### Building from Source

Requirements: Python 3.12+, [Inno Setup 6](https://jrsoftware.org/isdl.php) installed.

```powershell
# Activate the virtual environment
.venv\Scripts\activate

# Run the build script (cleans previous output, builds exe + installer)
.\build.ps1
```

The script will:
1. Clean `build/`, `dist/` and `installer/` folders
2. Run PyInstaller to produce `dist\SSM Manager\`
3. Run Inno Setup to produce `installer\SSM-Manager-vX.Y-setup.exe`

> **Note:** The build requires `--collect-all pythonnet` and `--collect-all clr_loader` flags.
> Without these, pywebview crashes at startup on Windows. These flags are already included in `build.ps1`.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

## Bug reports

Create an issue on GitHub, please include the following (if one of them is not applicable to the issue then it's not needed):
  • The steps to reproduce the bug
  • Logs file app.log
  • The version of software
  • Your OS & Browser including server OS
What you were expecting to see

## License

MIT License
Copyright (c) 2024 

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

## Acknowledgments

- a bit support for AI (i'm not super developer...)
- All contributors who helped improve this tool

## Support

If you encounter any problems or have suggestions, please open an issue in the GitHub repository.
