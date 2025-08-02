import csv
from csv_importer import import_csv, categorize_merchant


def test_import_csv(tmp_path):
    data = [
        ['Branch Cash Withdrawal 07/01 12:00:00 POS WALMART 123 GA', -10.0],
        ['Branch Cash Withdrawal 07/02 13:00:00 POS SHELL 456 TX', -20.5],
    ]
    file = tmp_path / "tx.csv"
    with file.open('w', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(data)

    rows = import_csv(str(file))
    assert len(rows) == 2
    assert set(r['category_guess'] for r in rows) == {'Groceries', 'Gas'}


def test_categorize_unknown():
    assert categorize_merchant('Random Store') is None
