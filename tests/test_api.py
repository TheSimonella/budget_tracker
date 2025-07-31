import pytest
from app import app, db, init_database

@pytest.fixture
def client(tmp_path):
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with app.app_context():
        db.drop_all()
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

