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
        ['', '', ''],
        ['', '', ''],
        ['Post Date', 'Description', 'Amount'],
        ['07/01/2025', 'Starbucks Coffee', '-4.50'],
        ['07/02/2025', 'Random Shop', '-2.00'],
    ]
    file = tmp_path / 'tx.csv'
    with file.open('w', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(data)

    rows, unknown = import_csv(str(file))
    assert len(rows) == 2
    dates = {r['date'] for r in rows}
    assert '07/01/2025' in dates and '07/02/2025' in dates
    assert 'RANDOM SHOP' in unknown


def test_categorize_unknown():
    assert categorize_merchant('Random Store') is None


def test_semicolon_with_blanks(tmp_path):
    lines = [
        '',
        '',
        'Date;Description;Amount',
        '07/01/2025;Branch Cash Withdrawal 07/01 12:00:00 POS WALMART 123 GA;-10.00',
        '07/02/2025;Branch Cash Withdrawal 07/02 13:00:00 POS SHELL 456 TX;-20.50',
    ]
    file = tmp_path / 'semi.csv'
    with file.open('w', newline='') as f:
        for line in lines:
            f.write(line + '\n')

    rows, unknown = import_csv(str(file))
    assert len(rows) == 2
    amts = {r['amount'] for r in rows}
    assert -10.0 in amts and -20.5 in amts
    assert not unknown


def test_fidelity_like_format(tmp_path):
    header = [
        'Run Date', 'Action', 'Symbol', 'Description', 'Type', 'Quantity',
        'Price ($)', 'Commission ($)', 'Fees ($)', 'Accrued Interest ($)',
        'Amount ($)', 'Cash Balance ($)', 'Settlement Date',
    ]
    rows = [
        ['7/23/2025', 'DEBIT CARD PURCHASE PAYPAL *RESUME IO', '', 'No Description',
         'Cash', '0', '', '', '', '', '-2.95', '2226.11', ''],
        ['7/17/2025', 'DIRECT DEPOSIT AMAZON RETAIDIRECT DEP', '', 'No Description',
         'Cash', '0', '', '', '', '', '1591.14', '2249.06', ''],
    ]
    file = tmp_path / 'fid.csv'
    with file.open('w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([''] * len(header))
        writer.writerow([''] * len(header))
        writer.writerow(header)
        writer.writerows(rows)

    parsed, unknown = import_csv(str(file))
    assert len(parsed) == 2
    amounts = {r['amount'] for r in parsed}
    assert -2.95 in amounts and 1591.14 in amounts
    merchants = {r['merchant'] for r in parsed}
    assert 'DEBIT CARD PURCHASE PAYPAL *RESUME IO' in merchants
    assert 'DIRECT DEPOSIT AMAZON RETAIDIRECT DEP' in merchants
