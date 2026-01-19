
import sys
import os
import traceback

sys.path.append(os.getcwd())

try:
    print("Attempting to import app.constants...")
    import app.constants
    print("Success: app.constants")
    
    print("Attempting to import app.ui.styles...")
    from app.ui.styles import DesignTokens
    print(f"Success: DesignTokens from app.ui.styles: {DesignTokens}")
except Exception:
    print("FAILURE during import:")
    traceback.print_exc()
