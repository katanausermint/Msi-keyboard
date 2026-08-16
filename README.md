
```markdown
# MSI Keyboard Controller

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Platform: Linux](https://img.shields.io/badge/platform-Linux-lightgrey.svg)]()

**MSI Keyboard Controller** is a powerful, open-source GUI application that brings full RGB backlight control to MSI gaming laptops on Linux. After extensive reverse engineering of the proprietary MSI MysticLight protocol, this application provides a seamless experience comparable to MSI Center on Windows.

## ✨ Features

### 🎨 Color Control
- **Full RGB spectrum** — Choose from 16.7 million colors
- **Color picker** — Intuitive color selection dialog
- **RGB sliders** — Fine-tune individual red, green, and blue channels
- **Live preview** — See your color choice on a virtual keyboard before applying
- **Instant application** — Changes take effect immediately

### 🌈 Animation Effects
- **Static** — Solid color illumination
- **Breathing** — Smooth fade in/out effect
- **Wave** — Color wave flowing across the keyboard
- **Reactive** — Keys light up when pressed
- **Rainbow** — Spectrum cycling
- **Gradient** — Color transitions

### 💡 Brightness Control
- **5 brightness levels** — From off to maximum
- **Independent from color** — Set brightness separately from color
- **Smooth transitions** — No flickering

### 🎯 Zone Management
- **Full keyboard** — Control all zones at once
- **Individual zones** — 4 separate zones for custom setups
- **Per-zone colors** — Different colors for different areas

### ⚡ Animation Speed
- **5 speed settings** — From very slow to very fast
- **Real-time adjustment** — Change speed without reapplying color

### 💾 Preset Management
- **Save presets** — Store your favorite configurations
- **Load presets** — Quickly switch between setups
- **Delete presets** — Manage your collection
- **Default presets** — Gaming, Relax, Rainbow, Work

### 📦 Flash Memory
- **Save to flash** — Persist settings across reboots
- **Load from flash** — Restore saved configurations
- **Factory reset** — Return to default settings

## 🖥 Supported Devices

| Device | Status | Notes |
|--------|--------|-------|
| MSI Katana 17 B13V | ✅ Fully tested | Primary development device |
| MSI MysticLight MS-1565 | ✅ Fully tested | Keyboard controller |
| Other MSI laptops with 1462:1601 | ⚠️ Probably works | Same VID:PID |

## 📦 Installation

### Method 1: .deb Package (Recommended)

```bash
# Download the .deb package from releases
wget https://github.com/katanausermint/Msi-keyboard/releases/latest/download/msi-keyboard-controller_1.0.1_all.deb

# Install
sudo dpkg -i msi-keyboard-controller_1.0.1_all.deb

# Fix dependencies if needed
sudo apt-get install -f

# Launch
msi-keyboard-controller
```

Method 2: From Source

```bash
# Clone the repository
git clone https://github.com/katanausermint/Msi-keyboard.git
cd Msi-keyboard

# Run the installer
./scripts/install.sh

# Launch
msi-keyboard-controller
```

Method 3: Manual Installation

```bash
# Install dependencies
sudo apt-get install python3 python3-tk python3-usb

# Copy the main script
sudo cp src/main.py /usr/local/bin/msi-keyboard-controller
sudo chmod +x /usr/local/bin/msi-keyboard-controller

# Create udev rule
echo 'SUBSYSTEM=="usb", ATTR{idVendor}=="1462", ATTR{idProduct}=="1601", MODE="0666"' | sudo tee /etc/udev/rules.d/99-msi-keyboard.rules

# Reload udev
sudo udevadm control --reload-rules
sudo udevadm trigger
```

🚀 Quick Start

1. Launch the application
   ```bash
   msi-keyboard-controller
   ```
   Or find it in your application menu
2. Connect to your keyboard
   · The app auto-connects on startup
   · Green dot = connected
   · Red dot = disconnected
3. Choose a color
   · Click "Choose Color" button
   · Or use RGB sliders
4. Select a mode
   · Static — solid color
   · Breathing — fade effect
   · Wave — flowing wave
   · Rainbow — spectrum
5. Apply settings
   · Click "Apply" button

📋 Requirements

· Python 3.8+
· python3-tk — GUI toolkit
· python3-usb — USB library
· sudo — root privileges for USB access
· Linux — any modern distribution

🔧 Building from Source

Prerequisites

```bash
sudo apt-get install python3 python3-tk python3-usb dpkg-dev
```

Build .deb Package

```bash
./install.sh
```

📖 Protocol Documentation

USB Communication

The application communicates with the keyboard using HID Feature Reports over USB.

Device Information

· Vendor ID: 0x1462 (Micro-Star International)
· Product ID: 0x1601 (MysticLight MS-1565)
· Interface: 0 (HID)
· Report ID (Send): 2
· Report ID (Receive): 1
· Packet Size: 64 bytes

Command Format

```
[0x02, 0x01, 0x00, 0x00, 0x00, 0x00, 0x0F, 0x01, 0x00, 0x00, R, G, B, Brightness]
     │     │     │     │     │     │     │     │     │     │   │  │  │      │
     │     │     │     │     │     │     │     │     │     │   │  │  │      └─ Brightness (0-255)
     │     │     │     │     │     │     │     │     │     │   │  │  └─ Blue (0-255)
     │     │     │     │     │     │     │     │     │     │   │  └─ Green (0-255)
     │     │     │     │     │     │     │     │     │     │   └─ Red (0-255)
     │     │     │     │     │     │     │     │     │     └─ Always 0x00
     │     │     │     │     │     │     │     │     └─ Direction
     │     │     │     │     │     │     │     └─ Constants
     │     │     │     │     │     │     └─ Animation Type
     │     │     │     │     │     └─ Speed (little endian)
     │     │     │     │     └─ Always 0x00
     │     │     │     └─ Always 0x00
     │     │     └─ Animation Type (1=Steady, 2=Breathing, etc.)
     │     └─ Packet ID (0x02 = Effect)
     └─ Report ID (always 0x02 for sending)
```

Key Protocol Insights

1. Always read after write — The device expects a GET_REPORT after every SET_REPORT
2. Byte 10 is always 0x00 — This was the key discovery
3. 64-byte packets — Always pad with zeros
4. Zone selection first — Send zone select before color/effect

🔍 Troubleshooting

Device Not Found

```bash
# Check if device is visible
lsusb | grep 1462

# Should show:
# Bus XXX Device YYY: ID 1462:1601 Micro Star International MysticLight MS-1565
```

Permission Denied

```bash
# Check udev rules
cat /etc/udev/rules.d/99-msi-keyboard.rules

# Reload rules
sudo udevadm control --reload-rules
sudo udevadm trigger
```

No Display Error

```bash
# Set DISPLAY manually
export DISPLAY=:0
export XAUTHORITY=$HOME/.Xauthority
msi-keyboard-controller
```

Keyboard Unresponsive

```bash
# Reset USB device
sudo usbreset 1462:1601

# Or reboot
sudo reboot
```

🤝 Contributing

We welcome contributions! Here's how you can help:

Report Bugs

· Use the GitHub issue tracker
· Include your device model
· Describe the problem clearly
· Attach logs if possible

Suggest Features

· Create a feature request issue
· Explain your use case
· Provide mockups if possible

Submit Code

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

Add Device Support

· Test with your MSI device
· Document VID:PID
· Report working/not working status
· Contribute protocol findings

📊 Performance

· Latency: ~100ms per command
· Memory usage: ~30MB
· CPU usage: <1% when idle
· Startup time: <1 second

🛡 Security

· No telemetry — Works completely offline
· No data collection — Your settings stay on your machine
· Open source — Audit the code yourself
· Minimal permissions — Only needs USB access

🌍 Internationalization

Currently in Russian, with plans for:

· English
· Spanish
· German
· French
· Chinese
· Japanese

🎓 Educational Value

This project demonstrates:

· USB HID protocol reverse engineering
· Python GUI development with Tkinter
· Linux device driver interaction
· .deb package creation
· Open source collaboration

🙏 Acknowledgments

· MSI — For creating the hardware
· OpenRGB — For protocol research inspiration
· Python community — For excellent libraries
· Linux community — For tools and documentation

⚠️ Disclaimer

This is an unofficial application. It is not affiliated with, endorsed by, or sponsored by Micro-Star International (MSI). All product names, logos, and brands are property of their respective owners.

Use at your own risk. The developers are not responsible for any damage to your hardware.

📄 License

This project is licensed under the GNU General Public License v3.0 — see the LICENSE file for details.

Free Software, Free Hardware Control! 🎉

🔗 Links

· Repository: github.com/katanausermint/Msi-keyboard
· Issues: github.com/katanausermint/Msi-keyboard/issues
· Releases: github.com/katanausermint/Msi-keyboard/releases

```
