import os
import ast

def find_syntax_errors(directory):
    errors = []
    for root, dirs, files in os.walk(directory):
        if "venv" in root or ".venv" in root or "__pycache__" in root or ".git" in root:
            continue
        for file in files:
            if file.endswith(".py"):
                path = os.path.join(root, file)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        content = f.read()
                    ast.parse(content)
                except SyntaxError as e:
                    errors.append((path, e))
                except Exception:
                    # Skip files that can't be decoded
                    continue
    return errors

if __name__ == "__main__":
    for path, err in find_syntax_errors("."):
        print(f"Error in {path}: {err}")
