import io
from transaction_parser import parse_csv, clean_merchant
from app import app, db, init_database, Transaction


def test_clean_merchant():
    assert clean_merchant('  Store #123 ') == 'Store 123'


def test_parse_bank1(tmp_path):
    csv_content = 'Date,Description,Amount\n2023-01-01,Coffee,-3.50\n2023-01-02,Salary,1000'
    txs = parse_csv(io.StringIO(csv_content), 'bank1')
    assert len(txs) == 2
    assert txs[0]['merchant'] == 'Coffee'
    assert txs[0]['transaction_type'] == 'expense'
    assert txs[1]['transaction_type'] == 'income'


def test_import_csv_endpoint(tmp_path):
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + str(tmp_path / 'test.db')
    with app.app_context():
        db.create_all()
        init_database()
        client = app.test_client()
        data = {
            'file': (io.BytesIO(b'Date,Description,Amount\n2023-01-01,Coffee,-3.50'), 'tx.csv'),
            'bank': 'bank1'
        }
        before = Transaction.query.count()
        resp = client.post('/api/import-csv', data=data, content_type='multipart/form-data')
        assert resp.status_code == 200
        assert Transaction.query.count() == before + 1

