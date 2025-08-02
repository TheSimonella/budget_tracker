import csv
from csv_importer import import_csv
from categories import categorize_merchant


def test_import_csv(tmp_path):
    data = [
        ['Branch Cash Withdrawal 07/01 12:00:00 POS WALMART 123 GA', -10.0],
        ['Branch Cash Withdrawal 07/02 13:00:00 POS SHELL 456 TX', -20.5],
    ]
    file = tmp_path / "tx.csv"
    with file.open('w', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(data)

    rows, unknown = import_csv(str(file))
    assert len(rows) == 2
    assert not unknown
    assert set(r['category_guess'] for r in rows) == {'Groceries', 'Gas'}


def test_header_and_unknown(tmp_path):
    data = [
        [],
        [],
        ['Post Date', 'Description', 'Amount'],
        ['07/01', 'Starbucks Coffee', '-4.50'],
        ['07/02', 'Random Shop', '-2.00'],
    ]
    file = tmp_path / 'tx.csv'
    with file.open('w', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(data)

    rows, unknown = import_csv(str(file))
    assert len(rows) == 2
    dates = {r['date'] for r in rows}
    assert '07/01' in dates and '07/02' in dates
    assert 'RANDOM SHOP' in unknown


def test_categorize_unknown():
    assert categorize_merchant('Random Store') is None
