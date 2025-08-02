import pandas as pd
from csv_importer import import_csv, categorize_merchant


def test_import_csv(tmp_path):
    data = [
        ['Branch Cash Withdrawal 07/01 12:00:00 POS WALMART 123 GA', -10.0],
        ['Branch Cash Withdrawal 07/02 13:00:00 POS SHELL 456 TX', -20.5],
    ]
    file = tmp_path / "tx.csv"
    pd.DataFrame(data).to_csv(file, index=False, header=False)

    df = import_csv(file)
    assert len(df) == 2
    assert set(df['category_guess']) == {'Groceries', 'Gas'}


def test_categorize_unknown():
    assert categorize_merchant('Random Store') is None
