import os
import csv
import pytest


@pytest.fixture
def client(tmp_path):
    os.environ['BUDGET_DB_URI'] = 'sqlite:///' + str(tmp_path / 'test.db')
    from app import app, db, init_database
    app.config['TESTING'] = True
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

    resp = client.get(f'/api/transactions/{tx_id}')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['amount'] == 15.5


def test_get_budget(client):
    resp = client.get('/api/budget/2023-01')
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, list)


def test_add_category_keyword_endpoint(client):
    resp = client.post('/api/category-keywords', json={'keyword': 'MyCafe', 'category': 'Coffee'})
    assert resp.status_code == 200
    from categories import categorize_merchant
    assert categorize_merchant('Spent at MyCafe') == 'Coffee'


def test_import_csv_endpoint_handles_year_and_blanks(client, tmp_path):
    data = [
        ['', '', ''],
        ['', '', ''],
        ['Post Date', 'Description', 'Amount'],
        ['07/01/2025', 'Starbucks', '-5.00'],
    ]
    file_path = tmp_path / 'tx.csv'
    with file_path.open('w', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(data)

    from app import Transaction
    with client.application.app_context():
        before = Transaction.query.count()

    with file_path.open('rb') as f:
        resp = client.post('/api/import-csv', data={'file': (f, 'tx.csv')}, content_type='multipart/form-data')
    assert resp.status_code == 200

    from datetime import date as date_cls
    with client.application.app_context():
        after = Transaction.query.count()
        assert after == before + 1
        tx = Transaction.query.order_by(Transaction.id.desc()).first()
        assert tx.date == date_cls(2025, 7, 1)


def test_dashboard_annual_endpoint(client):
    resp = client.get('/api/dashboard-data/annual/2023')
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'net_income' in data


def test_spending_trends_range(client):
    resp = client.get('/api/reports/spending-trends?start=2023-01&end=2023-03')
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data['months']) == 3


def test_period_comparison_endpoint(client):
    resp = client.get('/api/reports/period-comparison?start1=2023-01&end1=2023-02&start2=2024-01&end2=2024-02')
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'period1' in data and 'period2' in data


def test_new_category_and_group_at_top(client):
    # Add two categories and ensure the second one appears first
    client.post('/api/categories', json={'name': 'FirstCat', 'type': 'expense'})
    client.post('/api/categories', json={'name': 'SecondCat', 'type': 'expense'})

    resp = client.get('/api/budget/2023-01')
    data = resp.get_json()
    first = next(c for c in data if c['name'] == 'FirstCat')
    second = next(c for c in data if c['name'] == 'SecondCat')
    assert second['sort_order'] < first['sort_order']
    assert first['parent_category'] is None and second['parent_category'] is None

    # No group should be created automatically
    resp = client.get('/api/category-groups?type=expense')
    groups = resp.get_json()
    assert all(g['name'] not in ['FirstCat', 'SecondCat'] for g in groups)

    # Add two groups and check that the newest is first
    client.post('/api/category-groups', json={'name': 'GroupA', 'type': 'expense'})
    client.post('/api/category-groups', json={'name': 'GroupB', 'type': 'expense'})
    resp = client.get('/api/category-groups?type=expense')
    groups = resp.get_json()
    assert groups[0]['name'] == 'GroupB'

    id_a = next(g['id'] for g in groups if g['name'] == 'GroupA')
    id_b = next(g['id'] for g in groups if g['name'] == 'GroupB')
    client.post('/api/category-groups/reorder', json={'order': [
        {'id': id_a, 'sort_order': 0},
        {'id': id_b, 'sort_order': 1}
    ]})
    resp = client.get('/api/category-groups?type=expense')
    groups = resp.get_json()
    assert groups[0]['name'] == 'GroupA'
