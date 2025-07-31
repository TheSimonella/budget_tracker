import pandas as pd
import re
from datetime import datetime


def clean_merchant(text: str) -> str:
    """Return a simplified merchant string."""
    if not isinstance(text, str):
        text = str(text)
    merchant = text.upper()
    merchant = re.sub(r"[^A-Z0-9 ]", " ", merchant)
    merchant = re.sub(r"\s{2,}", " ", merchant)
    merchant = re.sub(r"\d+$", "", merchant)
    return merchant.strip()


def _parse_bank_a(df: pd.DataFrame):
    txs = []
    for _, row in df.iterrows():
        date = pd.to_datetime(row["Date"]).date()
        amount = float(row["Amount"]) if row["Amount"] != "" else 0.0
        typ = str(row.get("Type", "")).lower()
        if typ == "debit" or amount < 0:
            tx_type = "expense"
            amount = abs(amount)
        else:
            tx_type = "income"
        desc = str(row["Description"])
        txs.append({
            "date": date,
            "amount": amount,
            "transaction_type": tx_type,
            "description": desc,
            "merchant": clean_merchant(desc),
        })
    return txs


def _parse_bank_b(df: pd.DataFrame):
    txs = []
    for _, row in df.iterrows():
        date = pd.to_datetime(row["Transaction Date"]).date()
        amount = float(row["Value"])
        if amount < 0:
            tx_type = "expense"
            amount = abs(amount)
        else:
            tx_type = "income"
        desc = str(row["Details"])
        txs.append({
            "date": date,
            "amount": amount,
            "transaction_type": tx_type,
            "description": desc,
            "merchant": clean_merchant(desc),
        })
    return txs


def parse_csv(path: str):
    """Parse a CSV from a supported bank and return unified transaction dicts."""
    df = pd.read_csv(path)
    if {"Date", "Description", "Amount", "Type"}.issubset(df.columns):
        return _parse_bank_a(df)
    if {"Transaction Date", "Details", "Value"}.issubset(df.columns):
        return _parse_bank_b(df)
    raise ValueError("Unsupported CSV format")
