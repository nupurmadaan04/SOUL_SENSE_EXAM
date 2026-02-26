import subprocess
import sys

def run_tests():
    # Run all tests in tests/test_otp_lock.py
    cmd = ["pytest", "-v", "--tb=long", "tests/test_otp_lock.py"]
    print(f"Running command: {' '.join(cmd)}")
    
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace'
    )
    
    print("\n--- STDOUT ---")
    print(result.stdout)
    
    print("\n--- STDERR ---")
    print(result.stderr)
    
    if result.returncode != 0:
        print(f"\nTests failed with return code {result.returncode}")
    else:
        print("\nTests passed!")

if __name__ == "__main__":
    run_tests()
