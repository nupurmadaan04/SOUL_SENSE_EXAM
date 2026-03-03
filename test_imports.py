import os
import sys
import importlib

# Add necessary paths
root = os.path.abspath(os.getcwd())
fastapi_root = os.path.join(root, "backend", "fastapi")
sys.path.insert(0, fastapi_root)

# Mock app.core if it fails
try:
    import app.core
except ImportError:
    print("Warning: app.core not found in root, trying to find it in backend/fastapi")
    # This shouldn't happen if fastapi_root is in sys.path and has an app/core

def check_imports(directory, package_prefix=""):
    for root_dir, dirs, files in os.walk(directory):
        if "__pycache__" in root_dir:
            continue
        for file in files:
            if file.endswith(".py") and file != "__init__.py":
                rel_path = os.path.relpath(os.path.join(root_dir, file), directory)
                module_name = package_prefix + rel_path.replace(os.sep, ".").replace(".py", "")
                try:
                    importlib.import_module(module_name)
                    print(f"OK: {module_name}")
                except Exception as e:
                    print(f"FAIL: {module_name} -> {type(e).__name__}: {e}")
                    import traceback
                    traceback.print_exc()

if __name__ == "__main__":
    check_imports(os.path.join(fastapi_root, "api"), "api.")
