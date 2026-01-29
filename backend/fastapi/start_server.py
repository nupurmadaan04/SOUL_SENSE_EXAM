"""
Quick start script for Soul Sense API server.
Handles installation and server startup.
"""
import subprocess
import sys
import os
import argparse
from pathlib import Path

def check_dependencies():
    """Check if required packages are installed."""
    try:
        import fastapi
        import uvicorn
        import sqlalchemy
        import pydantic_settings
        return True
    except ImportError as e:
        print(f"DEBUG: Missing dependency: {e}")
        return False

def install_dependencies():
    """Install required dependencies."""
    print("Installing dependencies...")
    requirements_file = Path(__file__).parent / "requirements.txt"
    
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "-r", str(requirements_file)
        ])
        print("✅ Dependencies installed successfully!")
        return True
    except subprocess.CalledProcessError:
        print("❌ Failed to install dependencies")
        return False

def start_server(host="127.0.0.1", port=8000, reload=True):
    """Start the FastAPI server."""
    print(f"\n[START] Starting Soul Sense API server...")
    print(f"   URL: http://{host}:{port}")
    print(f"   Docs: http://{host}:{port}/docs")
    print(f"   ReDoc: http://{host}:{port}/redoc")
    print(f"   Reload: {'Enabled' if reload else 'Disabled'}")
    
    # Ensure uvicorn is available in the path
    uvicorn_cmd = [
        sys.executable, "-m", "uvicorn",
        "app.main:app",
        "--host", host,
        "--port", str(port)
    ]
    
    if reload:
        uvicorn_cmd.append("--reload")

    print(f"Running: {' '.join(uvicorn_cmd)}")
    
    # Add project root to PYTHONPATH to ensure backend.core imports work
    env = os.environ.copy()
    project_root = str(Path(__file__).resolve().parent.parent.parent)
    current_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{project_root}{os.pathsep}{current_pythonpath}"
    
    # Set working directory to backend/fastapi so 'app.main' works
    cwd = Path(__file__).parent
    
    try:
        subprocess.run(uvicorn_cmd, env=env, cwd=str(cwd))
    except KeyboardInterrupt:
        print("\n\n👋 Server stopped")

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Soul Sense API Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--reload", action="store_true", default=None, help="Enable auto-reload")
    parser.add_argument("--no-reload", action="store_false", dest="reload", help="Disable auto-reload")
    parser.add_argument("--y", action="store_true", help="Non-interactive mode (auto-confirm)")
    
    args = parser.parse_args()

    print("="*60)
    print("    SOUL SENSE API - Quick Start")
    print("="*60)
    
    # Check dependencies
    if not check_dependencies():
        print("\n⚠️  Dependencies not found.")
        
        if args.y:
            print("Non-interactive mode: installing dependencies...")
            if not install_dependencies():
                sys.exit(1)
        else:
            response = input("Install dependencies now? (y/n): ")
            if response.lower() == 'y':
                if not install_dependencies():
                    sys.exit(1)
            else:
                print("Please install dependencies manually:")
                print("  pip install -r requirements.txt")
                sys.exit(1)
    else:
        print("\n[OK] Dependencies OK")
    
    # Determine reload default (True normally, False if non-interactive and not specified)
    reload_val = args.reload
    if reload_val is None:
        reload_val = not args.y

    # Start server
    start_server(host=args.host, port=args.port, reload=reload_val)

if __name__ == "__main__":
    main()
