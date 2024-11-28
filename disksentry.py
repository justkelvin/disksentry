#!/usr/bin/env python3

import os
import sys
import time
import json
import logging
import sqlite3
import subprocess
from datetime import datetime
from typing import Dict, List, Tuple
import pandas as pd
from sklearn.ensemble import IsolationForest
import numpy as np
import shutil

class DiskSentry:
    def __init__(self, config_path: str = "/etc/disksentry/config.json"):
        """Initialize DiskSentry with configuration."""
        self.logger = self._setup_logging()
        self.config = self._load_config(config_path)
        self.db_conn = self._setup_database()
        
    def _setup_logging(self) -> logging.Logger:
        """Configure logging for DiskSentry."""
        logger = logging.getLogger("DiskSentry")
        logger.setLevel(logging.INFO)
        
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        return logger

    def _load_config(self, config_path: str) -> dict:
        """Load configuration from JSON file."""
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            return config
        except FileNotFoundError:
            # Create default configuration if not found
            default_config = {
                "monitored_disks": ["/dev/sda", "/dev/sdb"],
                "backup_location": "/mnt/backup",
                "smart_check_interval": 3600,  # 1 hour
                "backup_threshold": 0.7,  # Trigger backup when health score < 0.7
                "database_path": "/var/lib/disksentry/disk_health.db"
            }
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            with open(config_path, 'w') as f:
                json.dump(default_config, f, indent=4)
            return default_config
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in configuration file {config_path}: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error while loading configuration: {e}")
            raise

    def _setup_database(self) -> sqlite3.Connection:
        """Initialize SQLite database for storing disk health metrics."""
        os.makedirs(os.path.dirname(self.config["database_path"]), exist_ok=True)
        conn = sqlite3.connect(self.config["database_path"])
        cursor = conn.cursor()
        
        # Create tables if they don't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS smart_data (
                timestamp TEXT,
                device TEXT,
                attribute TEXT,
                value INTEGER,
                threshold INTEGER,
                raw_value TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS disk_predictions (
                timestamp TEXT,
                device TEXT,
                health_score REAL,
                prediction_confidence REAL
            )
        ''')
        
        conn.commit()
        return conn

    def get_smart_data(self, device: str) -> List[Dict]:
        """Retrieve SMART data for a specific device using smartctl."""
        try:
            cmd = ["smartctl", "-A", device]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            smart_data = []
            for line in result.stdout.split('\n')[2:]:  # Skip header lines
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 9:
                        smart_data.append({
                            'attribute': parts[1],
                            'value': int(parts[3]),
                            'threshold': int(parts[5]),
                            'raw_value': parts[9]
                        })
            return smart_data
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to get SMART data for {device}: {e}")
            return []

    def store_smart_data(self, device: str, smart_data: List[Dict]):
        """Store SMART data in the database."""
        cursor = self.db_conn.cursor()
        timestamp = datetime.now().isoformat()
        
        for attribute in smart_data:
            cursor.execute('''
                INSERT INTO smart_data
                (timestamp, device, attribute, value, threshold, raw_value)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                timestamp,
                device,
                attribute['attribute'],
                attribute['value'],
                attribute['threshold'],
                attribute['raw_value']
            ))
        
        self.db_conn.commit()

    def predict_disk_health(self, device: str) -> Tuple[float, float]:
        """
        Predict disk health using historical SMART data and machine learning.
        Returns (health_score, prediction_confidence)
        """
        cursor = self.db_conn.cursor()
        
        # Get historical SMART data for analysis
        cursor.execute('''
            SELECT attribute, value, threshold
            FROM smart_data
            WHERE device = ?
            ORDER BY timestamp DESC
            LIMIT 1000
        ''', (device,))
        
        data = cursor.fetchall()
        if not data:
            return 1.0, 0.0  # Default to healthy if no data
            
        # Prepare data for anomaly detection
        df = pd.DataFrame(data, columns=['attribute', 'value', 'threshold'])
        df_pivot = df.pivot(columns='attribute', values='value')
        
        # Use Isolation Forest for anomaly detection
        iso_forest = IsolationForest(contamination=0.1, random_state=42)
        scores = iso_forest.fit_predict(df_pivot)
        
        # Convert scores to health score (0 to 1)
        health_score = (scores + 1).mean() / 2
        
        # Calculate prediction confidence based on data quantity
        prediction_confidence = min(len(data) / 100, 1.0)
        
        return float(health_score), prediction_confidence

    def check_disk_space(self, device: str) -> Dict:
        """Check disk space usage."""
        try:
            df = subprocess.run(['df', device], capture_output=True, text=True, check=True)
            lines = df.stdout.strip().split('\n')
            if len(lines) >= 2:
                _, total, used, available, percent, _ = lines[1].split()
                return {
                    'total': int(total),
                    'used': int(used),
                    'available': int(available),
                    'usage_percent': float(percent.strip('%'))
                }
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to check disk space for {device}: {e}")
        return {}

    def backup_critical_data(self, source_device: str):
        """Perform backup of critical data when health score is low."""
        backup_path = os.path.join(
            self.config["backup_location"],
            f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        
        try:
            # Create backup directory
            os.makedirs(backup_path, exist_ok=True)
            
            # Mount source device to temporary location
            mount_point = "/tmp/disksentry_backup"
            os.makedirs(mount_point, exist_ok=True)
            
            # Mount the device
            subprocess.run(["mount", source_device, mount_point], check=True)
            
            # Perform backup using rsync
            subprocess.run([
                "rsync",
                "-av",
                "--progress",
                f"{mount_point}/",
                backup_path
            ], check=True)
            
            # Unmount the device
            subprocess.run(["umount", mount_point], check=True)
            
            self.logger.info(f"Backup completed successfully to {backup_path}")
            
        except Exception as e:
            self.logger.error(f"Backup failed: {e}")
            raise

    def monitor_loop(self):
        """Main monitoring loop."""
        while True:
            for device in self.config["monitored_disks"]:
                try:
                    # Collect SMART data
                    smart_data = self.get_smart_data(device)
                    if smart_data:
                        self.store_smart_data(device, smart_data)
                        
                        # Predict health
                        health_score, confidence = self.predict_disk_health(device)
                        
                        # Store prediction
                        cursor = self.db_conn.cursor()
                        cursor.execute('''
                            INSERT INTO disk_predictions
                            (timestamp, device, health_score, prediction_confidence)
                            VALUES (?, ?, ?, ?)
                        ''', (
                            datetime.now().isoformat(),
                            device,
                            health_score,
                            confidence
                        ))
                        self.db_conn.commit()
                        
                        # Check if backup is needed
                        if health_score < self.config["backup_threshold"]:
                            self.logger.warning(
                                f"Low health score ({health_score}) detected for {device}. "
                                "Initiating backup..."
                            )
                            self.backup_critical_data(device)
                        
                        self.logger.info(
                            f"Device: {device}, Health Score: {health_score:.2f}, "
                            f"Confidence: {confidence:.2f}"
                        )
                    
                except Exception as e:
                    self.logger.error(f"Error monitoring device {device}: {e}")
                
            # Wait for next check interval
            time.sleep(self.config["smart_check_interval"])

    def generate_report(self) -> str:
        """Generate a health report for all monitored disks."""
        report = []
        report.append("DiskSentry Health Report")
        report.append(f"Generated at: {datetime.now().isoformat()}\n")
        
        for device in self.config["monitored_disks"]:
            report.append(f"Device: {device}")
            
            # Get latest health score
            cursor = self.db_conn.cursor()
            cursor.execute('''
                SELECT health_score, prediction_confidence
                FROM disk_predictions
                WHERE device = ?
                ORDER BY timestamp DESC
                LIMIT 1
            ''', (device,))
            
            health_data = cursor.fetchone()
            if health_data:
                health_score, confidence = health_data
                report.append(f"Health Score: {health_score:.2f}")
                report.append(f"Prediction Confidence: {confidence:.2f}")
            
            # Add space usage
            space_info = self.check_disk_space(device)
            if space_info:
                report.append(f"Space Usage: {space_info['usage_percent']}%")
                report.append(f"Available Space: {space_info['available']} KB")
            
            report.append("")  # Empty line between devices
        
        return "\n".join(report)

def main():
    """Main entry point for DiskSentry."""
    try:
        sentry = DiskSentry()
        sentry.logger.info("DiskSentry started")
        sentry.monitor_loop()
    except KeyboardInterrupt:
        sentry.logger.info("DiskSentry shutting down")
        sys.exit(0)
    except Exception as e:
        sentry.logger.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
