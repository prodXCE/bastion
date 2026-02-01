import sys
from pathlib import Path


def create_structure():
    root = Path.cwd()

    # Source / package directories
    src_dirs = [
        root / "bastion",
        root / "bastion" / "core",
        root / "bastion" / "runner",
        root / "tests",
    ]

    # Runtime / variable directories
    var_dirs = [
        root / "var",
        root / "var" / "logs",
        root / "var" / "workspace",
        root / "var" / "artifacts",
    ]

    print(f"Initializing Bastion CI Project at: {root}")

    # Create directories
    for d in src_dirs + var_dirs:
        try:
            d.mkdir(parents=True, exist_ok=True)
            print(f" [OK] Created: {d.relative_to(root)}")
        except PermissionError:
            print(f" [ERR] Permission denied: {d}")
            sys.exit(1)

    # Mark Python packages
    for d in src_dirs:
        init_file = d / "__init__.py"
        if not init_file.exists():
            init_file.touch()
            print(f" [OK] Touched: {init_file.relative_to(root)}")

    # Create .gitignore
    gitignore = root / ".gitignore"
    if not gitignore.exists():
        gitignore.write_text(
            "var/\n"
            "__pycache__/\n"
            "*.pyc\n"
            ".env\n"
        )
        print(" [OK] Created .gitignore")


if __name__ == "__main__":
    create_structure()
