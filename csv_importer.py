"""CSV Importer for bank transactions.

This module provides utilities to parse bank transaction
strings, extract merchant information, and categorize
transactions using simple keyword matching.
"""

import re
import pandas as pd
from typing import Dict, Optional

# --- text cleaning helpers (adapted from banking-class repository)

def _throw_out(df: pd.DataFrame, col: str, regex: str) -> None:
    df[col] = df[col].str.replace(regex, '', case=False, regex=True)


def _move(df: pd.DataFrame, col_in: str, col_out: str, regex: str) -> None:
    df[col_out] = df[col_in].str.extract(regex, flags=re.IGNORECASE, expand=True)
    _throw_out(df, col_in, regex)


def _strip(df: pd.DataFrame, col: str) -> None:
    df[col] = df[col].str.strip()


def _make_description(df: pd.DataFrame, col: str) -> None:
    df['description'] = df[col]


def _separate_cols(df: pd.DataFrame) -> None:
    _move(df, 'description', 'time', r'([0-9][0-9]:[0-9][0-9]:[0-9][0-9])')
    _move(df, 'description', 'date', r'([0-1][0-9]/[0-3][0-9])')
    _throw_out(df, 'description', 'Branch Cash Withdrawal')
    _move(df, 'description', 'phone', r'([0-9]{3}-[0-9]{3}-[0-9]{4})')
    _strip(df, 'description')
    _throw_out(df, 'description', r'^POS ')


def _find_locations(df: pd.DataFrame) -> None:
    _move(df, 'description', 'country', r'(US)$')
    _strip(df, 'description')
    _move(df, 'description', 'state', r'(AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|MA|MI|MN|MS|MO|MT|NE|NV|NH|NJ|NM|NY|NC|ND|OH|OK|OR|PA|RI|SC|SD|TN|TX|UT|VT|VA|WA|WV|WI|WY)$')
    _strip(df, 'description')
    df['city'] = ''


def _find_merchant(df: pd.DataFrame) -> None:
    df['merchant'] = df['description'].str.upper()
    third_parties = [r'...\*', r'LEVELUP\*', r'PAYPAL \*']
    regex = r'^(' + '|'.join(third_parties) + ')'
    _throw_out(df, 'merchant', regex)
    _throw_out(df, 'merchant', r'\s\s+.+$')
    _strip(df, 'merchant')
    _throw_out(df, 'merchant', r'X+-?X+')
    _throw_out(df, 'merchant', r'( ID:.*| PAYMENT ID:.*| PMT ID:.*)')
    _strip(df, 'merchant')
    _throw_out(df, 'merchant', r'[#]?[ ]?([0-9]){1,999}$')
    _strip(df, 'merchant')
    _throw_out(df, 'merchant', r'([ ]?-[ ]?|[_])')
    _strip(df, 'merchant')
    _throw_out(df, 'merchant', r'[.]com.*$')
    _strip(df, 'merchant')
    _throw_out(df, 'merchant', r' .$')
    _strip(df, 'merchant')
    df['merchant'] = df['merchant'].str.replace('^$', ' ', regex=True)


def parse_transactions(df: pd.DataFrame, col: str = 'raw') -> None:
    """Parse raw transaction descriptions into merchant and location fields."""
    _make_description(df, col)
    _separate_cols(df)
    _find_locations(df)
    _find_merchant(df)


# --- simple categorization ---
CATEGORY_KEYWORDS: Dict[str, str] = {
    'GROCERY': 'Groceries',
    'WALMART': 'Groceries',
    'KROGER': 'Groceries',
    'SAFEWAY': 'Groceries',
    'EXXON': 'Gas',
    'SHELL': 'Gas',
    'CHEVRON': 'Gas',
    'RENT': 'Rent/Mortgage',
    'MORTGAGE': 'Rent/Mortgage',
    'UTILITIES': 'Utilities',
    'INTERNET': 'Internet',
    'COMCAST': 'Internet',
    'PHONE': 'Phone',
}


def categorize_merchant(merchant: str) -> Optional[str]:
    upper = merchant.upper()
    for keyword, category in CATEGORY_KEYWORDS.items():
        if keyword in upper:
            return category
    return None


def import_csv(path: str) -> pd.DataFrame:
    """Import CSV of transactions. Expected columns: raw, amount."""
    df = pd.read_csv(path, header=None)
    if len(df.columns) >= 2:
        df.columns = ['raw', 'amount'] + list(df.columns[2:])
    else:
        raise ValueError('CSV must have at least two columns')

    parse_transactions(df, 'raw')

    df['category_guess'] = df['merchant'].apply(lambda m: categorize_merchant(m) or 'Uncategorized')
    return df[['date', 'merchant', 'amount', 'category_guess']]
