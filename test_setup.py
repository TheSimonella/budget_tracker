import sys
import os

print("Testing Budget Tracker Setup...")
print("=" * 50)

# Check Python version
print(f"Python version: {sys.version}")
if sys.version_info < (3, 7):
    print("ERROR: Python 3.7 or higher is required!")
    sys.exit(1)

# Check if we're in the right directory
print(f"\nCurrent directory: {os.getcwd()}")
required_files = ['app.py', 'requirements.txt']
missing_files = [f for f in required_files if not os.path.exists(f)]

if missing_files:
    print(f"ERROR: Missing files: {missing_files}")
    print("Make sure you're in the budget-tracker directory!")
    sys.exit(1)

# Try to import required packages
print("\nChecking installed packages...")
try:
    import flask
    print(f"✓ Flask version: {flask.__version__}")
except ImportError:
    print("✗ Flask is not installed")

try:
    import flask_sqlalchemy
    print(f"✓ Flask-SQLAlchemy is installed")
except ImportError:
    print("✗ Flask-SQLAlchemy is not installed")

try:
    import openpyxl
    print(f"✓ openpyxl is installed")
except ImportError:
    print("✗ openpyxl is not installed")

# Check if templates directory exists
if os.path.exists('templates'):
    template_files = os.listdir('templates')
    print(f"\n✓ Templates directory exists with {len(template_files)} files")
else:
    print("\n✗ Templates directory is missing!")

print("\n" + "=" * 50)
print("Test complete. Check for any errors above.")
input("\nPress Enter to exit...")