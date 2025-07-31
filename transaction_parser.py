import pandas as pd
import re
from datetime import datetime


def clean_merchant(text: str) -> str:
    """Simple normalization of merchant names"""
    if not isinstance(text, str):
        return ""
    text = text.strip()
    text = re.sub(r"\s{2,}", " ", text)
    text = re.sub(r"[^A-Za-z0-9 &]", "", text)
    return text


def parse_bank1(df: pd.DataFrame):
    """Parse CSV exported from Bank1 with columns Date, Description, Amount"""
    transactions = []
    for _, row in df.iterrows():
        date = pd.to_datetime(row.get("Date")).date()
        desc = str(row.get("Description", ""))
        amount = float(row.get("Amount", 0))
        t_type = "income" if amount > 0 else "expense"
        transactions.append(
            {
                "date": date,
                "description": desc,
                "merchant": clean_merchant(desc),
                "amount": abs(amount),
                "transaction_type": t_type,
            }
        )
    return transactions


def parse_bank2(df: pd.DataFrame):
    """Parse CSV exported from Bank2 with Transaction Date, Details, Debit, Credit"""
    transactions = []
    for _, row in df.iterrows():
        date = pd.to_datetime(row.get("Transaction Date")).date()
        details = str(row.get("Details", ""))
        debit = row.get("Debit")
        credit = row.get("Credit")
        if pd.notnull(credit) and credit != "":
            amount = float(credit)
        else:
            amount = -float(debit or 0)
        t_type = "income" if amount > 0 else "expense"
        transactions.append(
            {
                "date": date,
                "description": details,
                "merchant": clean_merchant(details),
                "amount": abs(amount),
                "transaction_type": t_type,
            }
        )
    return transactions


BANK_PARSERS = {
    "bank1": parse_bank1,
    "bank2": parse_bank2,
}


def parse_csv(file_path, bank: str = "bank1"):
    """Parse a CSV file from the given bank and return normalized transactions."""
    df = pd.read_csv(file_path)
    parser = BANK_PARSERS.get(bank, parse_bank1)
    return parser(df)
