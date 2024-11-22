# DiskSentry 🔍

> Predictive disk health monitoring and management system for Linux

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

DiskSentry is an intelligent disk monitoring system that uses SMART data and machine learning to predict potential disk failures before they occur. It implements automated backup strategies and provides comprehensive health reporting for system administrators.

## 🚀 Features

- **Predictive Monitoring**: Uses machine learning to detect potential disk failures
- **SMART Data Analysis**: Continuously monitors disk health metrics
- **Automated Backup**: Triggers backups when disk health deteriorates
- **Health Reporting**: Generates detailed disk health reports
- **Space Management**: Monitors disk space usage and trends
- **Historical Analysis**: Maintains historical health data for trend analysis

## 📋 Prerequisites

### System Requirements
- Linux-based operating system (tested on Arch Linux)
- Python 3.8 or higher
- Root access (for SMART data collection)

### Required Packages

```bash
# Arch Linux
sudo pacman -S smartmontools rsync python-pandas python-scikit-learn

# Python packages
pip install pandas numpy scikit-learn
```

## 🔧 Installation

1. Clone the repository:
```bash
git clone https://github.com/justkelvin/disksentry.git
cd disksentry
```

2. Create required directories:
```bash
sudo mkdir -p /etc/disksentry
sudo mkdir -p /var/lib/disksentry
```

3. Copy the configuration file:
```bash
sudo cp config.json.example /etc/disksentry/config.json
```

4. Install Python dependencies:
```bash
pip install -r requirements.txt
```

## ⚙️ Configuration

Edit `/etc/disksentry/config.json`:

```json
{
    "monitored_disks": ["/dev/sda", "/dev/sdb"],
    "backup_location": "/mnt/backup",
    "smart_check_interval": 3600,
    "backup_threshold": 0.7,
    "database_path": "/var/lib/disksentry/disk_health.db"
}
```

### Configuration Options

| Option | Description | Default |
|--------|-------------|---------|
| monitored_disks | List of disks to monitor | ["/dev/sda"] |
| backup_location | Backup destination path | "/mnt/backup" |
| smart_check_interval | Check interval in seconds | 3600 |
| backup_threshold | Health score threshold for backup | 0.7 |
| database_path | Path to SQLite database | "/var/lib/disksentry/disk_health.db" |

## 🚀 Usage

### Running as a Service

1. Create a systemd service file:
```bash
sudo nano /etc/systemd/system/disksentry.service
```

2. Add the following content:
```ini
[Unit]
Description=DiskSentry Monitoring Service
After=multi-user.target

[Service]
Type=simple
ExecStart=/usr/bin/python /path/to/disksentry.py
Restart=always
User=root

[Install]
WantedBy=multi-user.target
```

3. Enable and start the service:
```bash
sudo systemctl enable disksentry
sudo systemctl start disksentry
```

### Manual Execution

Run directly with Python:
```bash
sudo python disksentry.py
```

### Generating Reports

```bash
sudo python disksentry.py --report
```

## 📊 Health Scoring

DiskSentry uses a combination of factors to calculate disk health:

- SMART attribute values and thresholds
- Historical trends
- Anomaly detection using Isolation Forest
- Space usage patterns

Health scores range from 0 (critical) to 1 (healthy).

## 🔄 Backup Strategy

The system implements an intelligent backup strategy:

1. Monitors disk health continuously
2. Triggers backup when health score drops below threshold
3. Uses rsync for efficient incremental backups
4. Maintains backup history with timestamps

## 📝 Logging

Logs are stored in `/var/log/disksentry.log` with the following levels:
- INFO: Regular operation events
- WARNING: Potential issues detected
- ERROR: Operation failures
- CRITICAL: System failures

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch:
```bash
git checkout -b feature/amazing-feature
```
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- The scikit-learn team for their machine learning tools
- The Linux SMART tools community
- All contributors and testers

## 📫 Contact

Project Link: https://github.com/justkelvin/disksentry

## 🔮 Roadmap

- [ ] Web interface for monitoring
- [ ] Email notifications
- [ ] Integration with popular monitoring systems
- [ ] Support for network-attached storage
- [ ] Advanced prediction models
