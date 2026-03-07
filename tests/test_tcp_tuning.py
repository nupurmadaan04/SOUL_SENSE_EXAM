import unittest
import os
import tempfile
from unittest.mock import patch, MagicMock
from app.infra.tcp_tuning import TCPTuningValidator, ValidationStatus, TCPParameter

class TestTCPTuningValidation(unittest.TestCase):
    def setUp(self):
        self.validator = TCPTuningValidator(profile_name="default")

    @patch("os.name", "posix")
    @patch("os.path.exists")
    def test_get_sysctl_value_success(self, mock_exists):
        mock_exists.return_value = True
        # Mock file reading
        with patch("builtins.open", unittest.mock.mock_open(read_data="1024\n")):
            val = self.validator.get_sysctl_value("net.core.somaxconn")
            self.assertEqual(val, "1024")

    @patch("os.name", "posix")
    @patch("os.path.exists")
    def test_get_sysctl_value_not_found(self, mock_exists):
        mock_exists.return_value = False
        val = self.validator.get_sysctl_value("non.existent.param")
        self.assertIsNone(val)

    @patch("os.name", "posix")
    @patch("app.infra.tcp_tuning.TCPTuningValidator.get_sysctl_value")
    def test_validate_all_mismatch(self, mock_get_val):
        # Mock values to return one mismatch
        # default profile has net.core.somaxconn = 1024
        mock_get_val.side_effect = lambda name: "512" if name == "net.core.somaxconn" else "valid"
        
        # Override parameters for predictable testing
        self.validator.parameters = [
            TCPParameter("net.core.somaxconn", 1024, "desc", "impact")
        ]
        
        results = self.validator.validate_all()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].status, ValidationStatus.MISMATCH)
        self.assertEqual(results[0].actual, "512")

    def test_rollback_script_generation(self):
        with patch("app.infra.tcp_tuning.TCPTuningValidator.get_sysctl_value", return_value="1024"):
            script = self.validator.generate_rollback_script()
            self.assertIn("sysctl -w net.core.somaxconn='1024'", script)

    def test_metrics_export(self):
        results = [
            MagicMock(status=ValidationStatus.PASSED),
            MagicMock(status=ValidationStatus.MISMATCH)
        ]
        metrics = self.validator.export_metrics(results)
        self.assertEqual(metrics["tcp_tuning_total_params"], 2)
        self.assertEqual(metrics["tcp_tuning_passed"], 1)
        self.assertEqual(metrics["tcp_tuning_mismatches"], 1)
        self.assertEqual(metrics["tcp_tuning_status"], "unhealthy")

if __name__ == "__main__":
    unittest.main()
