import subprocess
import os

try:
    result = subprocess.run(
        ["pytest", "-v", "--tb=short", "tests/test_otp_lock.py::TestOTPAttemptsTracking::test_attempts_increment_on_wrong_code"],
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace'
    )
    print("STDOUT:")
    print(result.stdout)
    print("STDERR:")
    print(result.stderr)
except Exception as e:
    print(f"Error: {e}")
