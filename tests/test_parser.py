import io
import csv
import pandas as pd
import pytest
from transaction_parser import parse_csv
from app import app, db, init_database


@pytest.fixture
def client(tmp_path):
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + str(tmp_path / 'test.db')
    with app.app_context():
        db.create_all()
        init_database()
        yield app.test_client()
        db.session.remove()

def make_csv(content: str, path):
    with open(path, 'w', newline='') as f:
        f.write(content)
    return str(path)


def test_parse_bank_a(tmp_path):
    data = """Date,Description,Amount,Type\n2023-01-01,Coffee Shop,-5.50,DEBIT\n2023-01-02,Salary,1000.00,CREDIT\n"""
    path = make_csv(data, tmp_path / 'a.csv')
    txs = parse_csv(path)
    assert len(txs) == 2
    assert txs[0]['transaction_type'] == 'expense'
    assert txs[1]['transaction_type'] == 'income'


def test_parse_bank_b(tmp_path):
    data = """Transaction Date,Details,Value\n2023-01-03,Shop,-20.00\n2023-01-04,Refund,30.00\n"""
    path = make_csv(data, tmp_path / 'b.csv')
    txs = parse_csv(path)
    assert len(txs) == 2
    assert txs[0]['merchant'] == 'SHOP'
    assert txs[0]['transaction_type'] == 'expense'


def test_import_endpoint(client, tmp_path):
    data = """Date,Description,Amount,Type\n2023-01-05,Book Store,-15.00,DEBIT\n"""
    csv_path = make_csv(data, tmp_path / 'import.csv')
    with open(csv_path, 'rb') as f:
        resp = client.post('/api/import-csv', data={'file': (f, 'import.csv')})
        assert resp.status_code == 200
        assert resp.get_json()['imported'] == 1
