import os
import ast

def check_syntax(directory):
    if not os.path.exists(directory):
        return
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(".py"):
                path = os.path.join(root, file)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        source = f.read()
                    ast.parse(source)
                except SyntaxError as e:
                    print(f"SyntaxError in {path}: {e}")
                except Exception as e:
                    # Ignore binary null byte errors for now as we saw them in some test files
                    pass

if __name__ == "__main__":
    print("Checking root...")
    check_syntax(".")
