# Budget Tracker

A personal budgeting application built with **Flask** and **SQLite**. It lets you track income and expenses, manage monthly budgets, create savings funds and view a variety of reports. The project is self contained and requires only Python and the packages listed in `requirements.txt`.

## Features

- Dashboard with monthly cash flow summary and Sankey diagram
- CRUD management of categories and category groups
- Transaction tracking for income, expenses, fund contributions and withdrawals
- Monthly budget setup per category with comparison against actual spending
- Savings funds with progress tracking and recommended contributions
- Report pages (monthly summary, annual overview, category analysis, spending trends)
- CSV and JSON export of all data and placeholder support for Excel import
- REST style API endpoints used by the front end (can also be reused by other tools)

## Repository structure

```
.
├── app.py                 # Main Flask application
├── index.html             # Landing page / simple introduction
├── templates/             # Jinja2 templates for each page
│   ├── base.html          # Common layout used by other templates
│   ├── dashboard.html     # Dashboard view
│   ├── transactions.html  # Transaction management
│   ├── budget.html        # Monthly budget setup
│   ├── funds.html         # Savings goals management
│   └── reports.html       # Reporting section
├── start_budget_tracker.bat  # Convenience launcher for Windows
├── start_budget_tracker.ps1  # PowerShell version of the launcher
├── debug_start.bat          # Script to help debug Windows setup issues
├── requirements.txt         # Python dependencies
├── test_setup.py            # Environment verification helper
└── README.md                # This file
```

All application logic including database models and API routes lives in `app.py`. The database file (`budget_tracker.db`) is created automatically on first run and populated with a set of default categories. A simple migration helper ensures new columns are added if the schema evolves.

## Getting started

### Prerequisites

- Python **3.8** or newer
- `pip` for installing packages

### Windows

Run `start_budget_tracker.bat` or the PowerShell equivalent `start_budget_tracker.ps1`. The script will:

1. Create a virtual environment in `venv/` if one does not exist
2. Install packages from `requirements.txt`
3. Launch the Flask server and open [http://localhost:5000](http://localhost:5000) in your browser

A debug version is available via `debug_start.bat` which prints additional diagnostics and logs output to `debug.log`.

### Linux / macOS

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

The application will start on port 5000 and create `budget_tracker.db` in the project directory.

## Customization

Most configuration lives in `app.py`. The models defined with SQLAlchemy (`Category`, `Transaction`, `Fund`, etc.) map directly to tables in the SQLite database. API routes are grouped by purpose and include inline comments describing their behaviour. Adjusting validation rules or adding new endpoints can be done directly in this file.

The HTML templates under `templates/` use Bootstrap 5 and minimal inline JavaScript. You can modify the look and feel or extend the pages by editing these templates. JavaScript on each page communicates with the Flask API using standard `fetch` calls.

If database changes are required, the helper function `migrate_database()` in `app.py` runs on startup and will add missing columns where possible. For more complex migrations you may want to create your own scripts.

## Export / import

The app can export transactions and other data to CSV or JSON via `/api/export/csv` and `/api/export/json`. An Excel import endpoint exists (`/api/import-excel`) as a placeholder – adapt the implementation to match your spreadsheet format if needed.

## Troubleshooting

- Ensure all dependencies from `requirements.txt` are installed in your virtual environment.
- Delete `budget_tracker.db` to reset data (the database will be recreated on next start).
- For Windows specific issues run `debug_start.bat` which checks Python versions and logs server output.

## Running tests

Unit tests are written with **pytest**. To run them locally, install the
dependencies from `requirements.txt` and then execute:

```bash
pytest
```

The `test_setup.py` module can also be executed directly with
`python test_setup.py` to verify that required files and packages are
available. When running checks from another script or test suite, call
`test_setup.run_checks(interactive=False)` to skip the final input prompt.

Continuous integration is configured with **GitHub Actions**. Every push or pull
request triggers the workflow in `.github/workflows/python-tests.yml` which
installs dependencies and runs `pytest` automatically.

## License

This project is provided as-is under the MIT license.
