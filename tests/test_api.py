import io
import pytest
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


def test_create_and_list_category(client):
    resp = client.post('/api/categories', json={'name': 'TestCat', 'type': 'expense'})
    assert resp.status_code == 200
    cat_id = resp.get_json()['id']

    resp = client.get('/api/categories')
    data = resp.get_json()
    assert any(c['id'] == cat_id for c in data)


def test_create_transaction(client):
    # create a category first
    resp = client.post('/api/categories', json={'name': 'Food2', 'type': 'expense'})
    cat_id = resp.get_json()['id']

    tx_data = {
        'amount': '15.5',
        'transaction_type': 'expense',
        'category_id': cat_id,
        'date': '2023-01-01'
    }
    resp = client.post('/api/transactions', json=tx_data)
    assert resp.status_code == 200
    tx_id = resp.get_json()['id']

    # retrieve transaction
    resp = client.get(f'/api/transactions/{tx_id}')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['amount'] == 15.5


def test_get_budget(client):
    resp = client.get('/api/budget/2023-01')
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, list)


def test_detect_subscriptions(client):
    resp = client.post('/api/categories', json={'name': 'Streaming', 'type': 'expense'})
    cat_id = resp.get_json()['id']

    for month in ['2023-01-01', '2023-02-01', '2023-03-01']:
        client.post('/api/transactions', json={
            'amount': '9.99',
            'transaction_type': 'expense',
            'category_id': cat_id,
            'date': month,
            'merchant': 'Netflix'
        })

    resp = client.post('/api/subscriptions/detect')
    assert resp.status_code == 200

    resp = client.get('/api/subscriptions')
    subs = resp.get_json()
    assert any('netflix' in s['merchant'] for s in subs)


def test_import_csv(client):
    csv_data = (
        "Transaction Date,Amount,Description,Merchant,Category,Type\n"
        "2023-01-01,10.00,Groceries order,Amazon,Groceries,expense\n"
    )
    data = {'file': (io.BytesIO(csv_data.encode('utf-8')), 'test.csv')}
    resp = client.post('/api/import-csv', data=data, content_type='multipart/form-data')
    assert resp.status_code == 200
    out = resp.get_json()
    assert out['imported'] == 1
    assert out['unresolved'] == []

    resp = client.get('/api/transactions')
    assert len(resp.get_json()) == 1


def test_import_csv_header_aliases(client):
    csv_data = (
        "posted date,debit,memo,payee,classification\n"
        "2023-01-02,5.00,Gas fill,Shell,Gas\n"
    )
    data = {'file': (io.BytesIO(csv_data.encode('utf-8')), 'test2.csv')}
    resp = client.post('/api/import-csv', data=data, content_type='multipart/form-data')
    assert resp.status_code == 200
    out = resp.get_json()
    assert out['imported'] == 1
    assert not out['unresolved']

    resp = client.get('/api/transactions')
    assert len(resp.get_json()) == 1

