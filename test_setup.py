import sys
import os


def check_python_version(min_version=(3, 7)):
    """Return True if the running Python version meets the requirement."""
    if sys.version_info < min_version:
        raise RuntimeError("Python 3.7 or higher is required")
    return True


def check_required_files(base_path="."):
    """Verify required project files exist in the given path."""
    required = ["app.py", "requirements.txt"]
    missing = [f for f in required if not os.path.exists(os.path.join(base_path, f))]
    if missing:
        raise FileNotFoundError(f"Missing files: {missing}")
    return True


def check_packages(packages=None):
    """Ensure the given packages can be imported."""
    packages = packages or ["flask", "flask_sqlalchemy", "openpyxl"]
    for pkg in packages:
        try:
            __import__(pkg)
        except ImportError as e:
            raise ImportError(f"{pkg} is not installed") from e
    return True


def check_templates_dir(base_path="."):
    """Verify the templates directory exists."""
    path = os.path.join(base_path, "templates")
    if not os.path.exists(path):
        raise FileNotFoundError("templates directory is missing")
    return os.listdir(path)


def run_checks(interactive: bool = True):
    print("Testing Budget Tracker Setup...")
    print("=" * 50)
    print(f"Python version: {sys.version}")
    check_python_version()

    print(f"\nCurrent directory: {os.getcwd()}")
    check_required_files()

    print("\nChecking installed packages...")
    check_packages()

    try:
        files = check_templates_dir()
        print(f"\n✓ Templates directory exists with {len(files)} files")
    except FileNotFoundError:
        print("\n✗ Templates directory is missing!")

    print("\n" + "=" * 50)
    print("Test complete. Check for any errors above.")
    if interactive:
        input("\nPress Enter to exit...")


if __name__ == "__main__":
    run_checks()
