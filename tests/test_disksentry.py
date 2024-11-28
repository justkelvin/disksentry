import unittest
from unittest.mock import patch, mock_open, MagicMock
import os
import sqlite3
import json
from disksentry import DiskSentry

class TestDiskSentry(unittest.TestCase):
    def setUp(self):
        self.mock_logger = MagicMock()
        self.test_config_path = "/tmp/test_config.json"
        self.default_config = {
            "monitored_disks": ["/dev/sda", "/dev/sdb"],
            "backup_location": "/mnt/backup",
            "smart_check_interval": 3600,
            "backup_threshold": 0.7,
            "database_path": "/var/lib/disksentry/disk_health.db"
        }

    @patch("builtins.open", new_callable=mock_open, read_data=json.dumps({"key": "value"}))
    def test_load_existing_config(self, mock_file):
        ds = DiskSentry(self.test_config_path, self.mock_logger)
        config = ds._load_config(self.test_config_path)
        self.assertEqual(config, {"key": "value"})
        mock_file.assert_called_once_with(self.test_config_path, 'r')

    @patch("os.makedirs")
    @patch("builtins.open", new_callable=mock_open)
    def test_load_config_creates_default(self, mock_file, mock_makedirs):
        mock_file.side_effect = FileNotFoundError()
        ds = DiskSentry(self.test_config_path, self.mock_logger)
        config = ds._load_config(self.test_config_path)
        self.assertEqual(config, self.default_config)

    @patch("builtins.open", new_callable=mock_open, read_data="invalid json")
    def test_load_config_invalid_json(self, mock_file):
        ds = DiskSentry(self.test_config_path, self.mock_logger)
        with self.assertRaises(json.JSONDecodeError):
            ds._load_config(self.test_config_path)
