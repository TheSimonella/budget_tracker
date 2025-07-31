import pandas as pd
from datetime import datetime

class BaseParser:
    def parse(self, path):
        raise NotImplementedError

class BankAParser(BaseParser):
    """Parser for Bank A CSV format with columns Date, Description, Amount"""
    def parse(self, path):
        df = pd.read_csv(path)
        required = {"Date", "Description", "Amount"}
        if not required.issubset(df.columns):
            raise ValueError("CSV missing required columns for BankA")
        df = df[list(required)]
        df["Date"] = pd.to_datetime(df["Date"]).dt.date
        return [
            {
                "date": row["Date"].isoformat(),
                "description": str(row["Description"]),
                "amount": float(row["Amount"]),
            }
            for _, row in df.iterrows()
        ]

class BankBParser(BaseParser):
    """Parser for Bank B CSV with Transaction Date, Details, Debit, Credit"""
    def parse(self, path):
        df = pd.read_csv(path)
        required = {"Transaction Date", "Details", "Debit", "Credit"}
        if not required.issubset(df.columns):
            raise ValueError("CSV missing required columns for BankB")
        df["Transaction Date"] = pd.to_datetime(df["Transaction Date"]).dt.date
        txs = []
        for _, row in df.iterrows():
            amount = 0.0
            if not pd.isna(row["Debit"]):
                amount = -float(row["Debit"])
            elif not pd.isna(row["Credit"]):
                amount = float(row["Credit"])
            txs.append({
                "date": row["Transaction Date"].isoformat(),
                "description": str(row["Details"]),
                "amount": amount,
            })
        return txs

PARSERS = {
    "banka": BankAParser(),
    "bankb": BankBParser(),
}

def parse_transactions(path, bank):
    bank = bank.lower()
    parser = PARSERS.get(bank)
    if not parser:
        raise ValueError(f"Unsupported bank type: {bank}")
    return parser.parse(path)
