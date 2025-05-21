import unittest
import sys
import os
# Assuming backup.py is in the same directory or PYTHONPATH is set
from backup import _generate_windows_schedule_command 

class TestBackupSchedule(unittest.TestCase):
    def test_generate_windows_schedule_command(self):
        mock_backup_time = "03:00"
        mock_executable = sys.executable
        # Use a fixed path for script_path for predictable test output
        mock_script_path = os.path.abspath("backup.py") 
        
        expected_command = f"schtasks /create /sc DAILY /ST {mock_backup_time} /tn \"RoundTable自动备份\" /tr \"{mock_executable} {mock_script_path} --auto\" /f"
        
        generated_command = _generate_windows_schedule_command(
            mock_backup_time, 
            mock_executable, 
            mock_script_path
        )
        self.assertEqual(generated_command, expected_command)

if __name__ == '__main__':
    unittest.main()
