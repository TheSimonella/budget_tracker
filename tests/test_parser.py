import io
import csv
import pytest
from app import app, db, init_database
from transaction_parser import parse_transactions

@pytest.fixture
def client(tmp_path):
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + str(tmp_path / 'test.db')
    app.config['UPLOAD_FOLDER'] = str(tmp_path)
    with app.app_context():
        db.create_all()
        init_database()
        yield app.test_client()
        db.session.remove()


def test_parse_banka(tmp_path):
    data = "Date,Description,Amount\n2023-01-01,Shop,-12.34\n2023-01-02,Salary,1000\n"
    path = tmp_path / 'a.csv'
    path.write_text(data)
    txs = parse_transactions(path, 'banka')
    assert len(txs) == 2
    assert txs[0]['description'] == 'Shop'


def test_parse_bankb(tmp_path):
    data = (
        "Transaction Date,Details,Debit,Credit\n"
        "2023-02-01,Coffee,3.5,\n"
        "2023-02-02,Refund,,5.0\n"
    )
    path = tmp_path / 'b.csv'
    path.write_text(data)
    txs = parse_transactions(path, 'bankb')
    assert len(txs) == 2
    assert txs[0]['amount'] == -3.5


def test_import_csv_endpoint(client, tmp_path):
    csv_content = "Date,Description,Amount\n2023-03-01,Book,-15.0\n"
    path = tmp_path / 'import.csv'
    path.write_text(csv_content)
    with open(path, 'rb') as f:
        data = {
            'bank': 'banka',
            'file': (f, 'import.csv')
        }
        resp = client.post('/api/import-csv', data=data, content_type='multipart/form-data')
        assert resp.status_code == 200
        msg = resp.get_json()['message']
        assert 'Imported 1' in msg

