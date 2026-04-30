"""
Interactive Setup Wizard for NASTool

Provides guided configuration and setup for new users.
"""

import os
import sys
import json
from pathlib import Path
from typing import Dict, Any, Optional


class InteractiveWizard:
    """
    Interactive setup wizard for NASTool configuration.
    
    Features:
    - Guided configuration process
    - Device registration
    - Profile selection
    - Basic settings setup
    """
    
    def __init__(self, config_dir: Optional[str] = None):
        """
        Initialize wizard.
        
        Args:
            config_dir: Configuration directory
        """
        self.config_dir = Path(config_dir or Path.home() / ".nastool")
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.config_file = self.config_dir / "config.json"
    
    def run(self) -> Dict[str, Any]:
        """
        Run the interactive setup wizard.
        
        Returns:
            Configuration dictionary
        """
        print("""
==================================================
   NASTool Setup Wizard
==================================================

Welcome to NASTool! This wizard will help you set up
basic configuration for your device monitoring needs.

""")
        
        # Step 1: Basic configuration
        config = self._setup_basic_config()
        
        # Step 2: Device registration
        devices = self._setup_devices()
        config['devices'] = devices
        
        # Step 3: Profile selection
        profile = self._select_profile()
        config['profile'] = profile
        
        # Step 4: Advanced settings
        advanced = self._setup_advanced()
        config.update(advanced)
        
        # Save configuration
        self._save_config(config)
        
        print("""
==================================================
   Setup Complete!
==================================================

Your NASTool configuration has been saved to:
{config_file}

To run NASTool, use:
  nastool

To run with your selected profile:
  nastool --profile {profile}

For more options, use:
  nastool --help

""".format(config_file=self.config_file, profile=profile))
        
        return config
    
    def _setup_basic_config(self) -> Dict[str, Any]:
        """
        Set up basic configuration.
        """
        print("\n[Step 1] Basic Configuration")
        print("-" * 40)
        
        config = {
            "name": self._prompt("Enter a name for this NASTool instance", "My NASTool"),
            "log_level": self._prompt_choice(
                "Select log level",
                ["info", "debug", "warning", "error"],
                default="info"
            ),
            "update_check": self._prompt_yes_no("Check for updates automatically", True),
        }
        
        return config
    
    def _setup_devices(self) -> List[Dict[str, Any]]:
        """
        Set up devices.
        """
        print("\n[Step 2] Device Registration")
        print("-" * 40)
        
        devices = []
        
        while True:
            add_device = self._prompt_yes_no("Add a device?", True)
            if not add_device:
                break
            
            device = {
                "host": self._prompt("Device IP address or hostname"),
                "name": self._prompt("Device name (optional)", ""),
                "type": self._prompt_choice(
                    "Device type",
                    ["rk3588", "rk3568", "jetson", "nas", "generic"],
                    default="generic"
                ),
                "group": self._prompt("Group name (optional)", "default"),
            }
            
            # Generate device ID from host if not provided
            device_id = self._prompt("Device ID (optional)", "")
            if not device_id:
                device_id = device['host'].replace('.', '_').replace(':', '_')
            device['id'] = device_id
            
            devices.append(device)
            print(f"Added device: {device['name'] or device['id']}")
        
        if not devices:
            print("No devices added. You can add devices later using:")
            print("  nastool device add <host> --type <type>")
        
        return devices
    
    def _select_profile(self) -> str:
        """
        Select usage profile.
        """
        print("\n[Step 3] Usage Profile")
        print("-" * 40)
        
        profiles = {
            "nas": "NAS Server - Full detection including network and storage",
            "dev": "Development/Testing - Skip external network checks",
            "jetson": "Jetson Embedded - Focus on AI acceleration",
            "isolated": "Network Isolated - Skip all network checks",
            "ai_server": "AI Server - Enhanced AI detection",
        }
        
        print("Select a usage profile:")
        for i, (profile, desc) in enumerate(profiles.items(), 1):
            print(f"  {i}. {profile}: {desc}")
        
        choices = list(profiles.keys())
        choice = self._prompt_choice(
            "Enter profile name",
            choices,
            default="nas"
        )
        
        return choice
    
    def _setup_advanced(self) -> Dict[str, Any]:
        """
        Set up advanced settings.
        """
        print("\n[Step 4] Advanced Settings")
        print("-" * 40)
        
        advanced = {}
        
        if self._prompt_yes_no("Configure batch settings?", False):
            advanced["batch"] = {
                "parallel": int(self._prompt("Maximum parallel devices", "4")),
                "timeout": int(self._prompt("Device timeout (seconds)", "300")),
            }
        
        if self._prompt_yes_no("Configure WebSocket settings?", False):
            advanced["websocket"] = {
                "relay_url": self._prompt("WebSocket relay URL", "ws://localhost:18888"),
                "reconnect_interval": int(self._prompt("Reconnect interval (seconds)", "5")),
            }
        
        return advanced
    
    def _save_config(self, config: Dict[str, Any]):
        """
        Save configuration to file.
        """
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        print(f"\nConfiguration saved to: {self.config_file}")
    
    def _prompt(self, message: str, default: str = "") -> str:
        """
        Prompt user for input.
        
        Args:
            message: Prompt message
            default: Default value
            
        Returns:
            User input
        """
        if default:
            prompt = f"{message} [{default}]: "
        else:
            prompt = f"{message}: "
        
        while True:
            try:
                if sys.version_info[0] >= 3:
                    response = input(prompt)
                else:
                    response = raw_input(prompt)
                
                if not response and default:
                    return default
                return response
            except EOFError:
                return default
    
    def _prompt_yes_no(self, message: str, default: bool = True) -> bool:
        """
        Prompt user for yes/no input.
        
        Args:
            message: Prompt message
            default: Default value
            
        Returns:
            True for yes, False for no
        """
        default_str = "Y" if default else "N"
        prompt = f"{message} [Y/n]: " if default else f"{message} [y/N]: "
        
        while True:
            try:
                if sys.version_info[0] >= 3:
                    response = input(prompt).strip().lower()
                else:
                    response = raw_input(prompt).strip().lower()
                
                if not response:
                    return default
                elif response in ('y', 'yes'):
                    return True
                elif response in ('n', 'no'):
                    return False
                else:
                    print("Please enter 'y' or 'n'.")
            except EOFError:
                return default
    
    def _prompt_choice(self, message: str, choices: List[str], default: str = "") -> str:
        """
        Prompt user to select from choices.
        
        Args:
            message: Prompt message
            choices: List of available choices
            default: Default choice
            
        Returns:
            Selected choice
        """
        if default and default not in choices:
            default = choices[0]
        
        prompt = f"{message} [{', '.join(choices)}]: "
        if default:
            prompt = f"{message} [{default}]: "
        
        while True:
            try:
                if sys.version_info[0] >= 3:
                    response = input(prompt).strip()
                else:
                    response = raw_input(prompt).strip()
                
                if not response and default:
                    return default
                elif response in choices:
                    return response
                else:
                    print(f"Please choose from: {', '.join(choices)}")
            except EOFError:
                return default


def run_setup_wizard():
    """
    Run the setup wizard.
    """
    wizard = InteractiveWizard()
    return wizard.run()


if __name__ == "__main__":
    run_setup_wizard()
