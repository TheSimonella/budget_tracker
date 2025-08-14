from flask import Flask, render_template, request, jsonify, send_file, Response
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import os, json, calendar, csv, io
from werkzeug.utils import secure_filename
import werkzeug

if not getattr(werkzeug, "__version__", None):
    werkzeug.__version__ = "3"
from sqlalchemy import extract, func, or_
from csv_importer import import_csv
from categories import add_keyword_category

app = Flask(__name__)
db_uri = os.environ.get('BUDGET_DB_URI', 'sqlite:///budget_tracker.db')
app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy()
db.init_app(app)

####
# Models
####
class CategoryGroup(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    sort_order = db.Column(db.Integer, default=0)
    __table_args__ = (db.UniqueConstraint("name", "type"),)

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    type = db.Column(db.String(50), nullable=False)  # 'income', 'deduction', 'expense', 'fund'
    default_budget = db.Column(db.Float, default=0.0)
    parent_category = db.Column(db.String(100), nullable=True)
    is_custom = db.Column(db.Boolean, default=True)
    sort_order = db.Column(db.Integer, default=0)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    transaction_type = db.Column(db.String(50), nullable=False)  # 'income', 'deduction', 'expense', 'fund_contribution', 'fund_withdrawal'
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    category = db.relationship('Category')
    description = db.Column(db.String(200))
    merchant = db.Column(db.String(100))
    date = db.Column(db.Date, nullable=False)
    notes = db.Column(db.String(300))

class Fund(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    goal = db.Column(db.Float, default=0.0)
    goal_date = db.Column(db.Date, nullable=True)
    current_balance = db.Column(db.Float, default=0.0)
    monthly_contribution = db.Column(db.Float, default=0.0)

class Budget(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    month = db.Column(db.String(7), nullable=False)  # 'YYYY-MM'
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    category = db.relationship('Category')
    amount = db.Column(db.Float, nullable=False)

####
# Helper Functions
####
def validate_amount(amount):
    """Validate that amount is a positive number"""
    try:
        amt = float(amount)
        if amt < 0:
            return None, "Amount cannot be negative"
        return amt, None
    except (ValueError, TypeError):
        return None, "Invalid amount format"

def validate_date(date_str):
    """Validate date format and ensure it's not in the future for transactions"""
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        if date_obj > datetime.now().date():
            return None, "Date cannot be in the future"
        return date_obj, None
    except ValueError:
        return None, "Invalid date format"

def calculate_recommended_contribution(fund):
    """Calculate recommended monthly contribution for a fund"""
    if not fund.goal or not fund.goal_date:
        return 0
    
    now = datetime.now().date()
    if fund.goal_date <= now:
        return 0
    
    months_remaining = (fund.goal_date.year - now.year) * 12 + (fund.goal_date.month - now.month)
    if months_remaining <= 0:
        return 0
    
    remaining_amount = fund.goal - fund.current_balance
    return max(0, remaining_amount / months_remaining)
####
# Page routes
####
@app.route('/')
def dashboard():
    return render_template('dashboard.html')

@app.route('/transactions')
def transactions_view():
    return render_template('transactions.html')

@app.route('/budget')
def budget_view():
    return render_template('budget.html')

@app.route('/funds')
def funds_view():
    return render_template('funds.html')

@app.route('/reports')
def reports_view():
    return render_template('reports.html')


####
# API: Dashboard
####
@app.route('/api/dashboard-data/<year_month>')
def get_dashboard_data(year_month):
    try:
        year, month = map(int, year_month.split('-'))
        month_name = calendar.month_name[month]
        
        # Get transactions for the month
        start_date = datetime(year, month, 1).date()
        if month == 12:
            end_date = datetime(year + 1, 1, 1).date()
        else:
            end_date = datetime(year, month + 1, 1).date()
        
        transactions = Transaction.query.filter(
            Transaction.date >= start_date,
            Transaction.date < end_date
        ).all()
        
        # Calculate totals
        gross_income = sum(t.amount for t in transactions if t.transaction_type == 'income')
        deductions = sum(t.amount for t in transactions if t.transaction_type == 'deduction')
        net_income = gross_income - deductions
        total_expenses = sum(
            t.amount for t in transactions
            if t.transaction_type == 'expense' and (t.category.type != 'fund')
        )
        total_savings = sum(
            t.amount for t in transactions
            if t.transaction_type == 'fund_contribution' or
               (t.transaction_type == 'expense' and t.category.type == 'fund')
        )
        
        # Get funds data
        funds = Fund.query.all()
        funds_data = []
        for fund in funds:
            funds_data.append({
                'name': fund.name,
                'balance': fund.current_balance,
                'goal': fund.goal,
                'progress': (fund.current_balance / fund.goal * 100) if fund.goal else 0,
                'goal_date': fund.goal_date.isoformat() if fund.goal_date else None
            })
        
        # Get recent transactions
        recent_transactions = Transaction.query.order_by(Transaction.date.desc()).limit(10).all()
        recent_data = []
        for t in recent_transactions:
            recent_data.append({
                'id': t.id,
                'amount': t.amount,
                'type': t.transaction_type,
                'category': t.category.name,
                'description': t.description,
                'merchant': t.merchant,
                'date': t.date.isoformat()
            })
        
        return jsonify({
            'current_month': f"{month_name} {year}",
            'gross_income': gross_income,
            'deductions': deductions,
            'net_income': net_income,
            'total_expenses': total_expenses,
            'total_savings': total_savings,
            'funds': funds_data,
            'recent_transactions': recent_data
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

####
# API: Categories
####
@app.route('/api/categories')
def get_categories():
    try:
        cats = Category.query.order_by(Category.sort_order, Category.name).all()
        return jsonify([
            {
                'id': c.id,
                'name': c.name,
                'type': c.type,
                'default_budget': c.default_budget,
                'parent_category': c.parent_category,
                'is_custom': c.is_custom,
                'sort_order': c.sort_order,
            }
            for c in cats
        ])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/categories', methods=['POST'])
def create_category():
    try:
        data = request.json
        
        # Validate required fields
        if not data.get('name'):
            return jsonify({'error': 'Category name is required'}), 400
        if not data.get('type'):
            return jsonify({'error': 'Category type is required'}), 400
        
        parent_category = data.get('parent_category')
        if parent_category:
            group = CategoryGroup.query.filter_by(name=parent_category, type=data['type']).first()
            if not group:
                return jsonify({'error': 'Group does not exist'}), 400
        
        # Validate budget amount
        budget_amount, error = validate_amount(data.get('monthly_budget', 0))
        if error:
            return jsonify({'error': error}), 400

        # Check if category already exists
        existing = Category.query.filter_by(name=data['name']).first()
        if existing:
            return jsonify({'error': 'Category with this name already exists'}), 400

        # Place new categories at the top by giving them the smallest sort order
        min_sort = db.session.query(func.min(Category.sort_order)) \
            .filter_by(type=data['type']).scalar()
        if min_sort is None:
            min_sort = 0

        cat = Category(
            name=data['name'],
            type=data['type'],
            default_budget=budget_amount,
            parent_category=parent_category,
            is_custom=True,
            sort_order=min_sort - 1
        )
        db.session.add(cat)
        db.session.commit()
        return jsonify({'id': cat.id, 'message': 'Category created successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/categories/<int:id>', methods=['DELETE'])
def delete_category(id):
    try:
        cat = Category.query.get_or_404(id)
        # Remove related budgets & transactions
        Budget.query.filter_by(category_id=id).delete()
        Transaction.query.filter_by(category_id=id).delete()
        # If it's a fund, also delete the fund record
        if cat.type == 'fund':
            Fund.query.filter_by(name=cat.name).delete()
        db.session.delete(cat)
        db.session.commit()
        return jsonify({'message': 'Category and related records deleted'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/dashboard-data/annual/<int:year>')
def get_dashboard_data_annual(year):
    try:
        start_date = datetime(year, 1, 1).date()
        end_date = datetime(year + 1, 1, 1).date()

        transactions = Transaction.query.filter(
            Transaction.date >= start_date,
            Transaction.date < end_date
        ).all()

        gross_income = sum(t.amount for t in transactions if t.transaction_type == 'income')
        deductions = sum(t.amount for t in transactions if t.transaction_type == 'deduction')
        net_income = gross_income - deductions
        total_expenses = sum(t.amount for t in transactions if t.transaction_type == 'expense')
        total_savings = sum(t.amount for t in transactions if t.transaction_type == 'fund_contribution')

        funds = Fund.query.all()
        funds_data = []
        for fund in funds:
            funds_data.append({
                'name': fund.name,
                'balance': fund.current_balance,
                'goal': fund.goal,
                'progress': (fund.current_balance / fund.goal * 100) if fund.goal else 0,
                'goal_date': fund.goal_date.isoformat() if fund.goal_date else None
            })

        recent_transactions = Transaction.query.order_by(Transaction.date.desc()).limit(10).all()
        recent_data = []
        for t in recent_transactions:
            recent_data.append({
                'id': t.id,
                'amount': t.amount,
                'type': t.transaction_type,
                'category': t.category.name,
                'description': t.description,
                'merchant': t.merchant,
                'date': t.date.isoformat()
            })

        return jsonify({
            'current_year': year,
            'gross_income': gross_income,
            'deductions': deductions,
            'net_income': net_income,
            'total_expenses': total_expenses,
            'total_savings': total_savings,
            'funds': funds_data,
            'recent_transactions': recent_data
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/categories/<int:id>', methods=['PUT'])
def update_category(id):
    try:
        data = request.json
        cat = Category.query.get_or_404(id)

        if 'name' in data:
            cat.name = data['name']
        if 'parent_category' in data:
            parent = data['parent_category']
            if parent:
                group = CategoryGroup.query.filter_by(name=parent, type=cat.type).first()
                if not group:
                    return jsonify({'error': 'Group does not exist'}), 400
            cat.parent_category = parent
        if 'default_budget' in data:
            amount, error = validate_amount(data['default_budget'])
            if error:
                return jsonify({'error': error}), 400
            cat.default_budget = amount
        if 'sort_order' in data:
            cat.sort_order = int(data['sort_order'])

        db.session.commit()
        return jsonify({'message': 'Category updated'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/categories/reorder', methods=['POST'])
def reorder_categories():
    try:
        order_data = request.json.get('order', [])
        for item in order_data:
            cat = Category.query.get(item['id'])
            if cat:
                cat.sort_order = int(item.get('sort_order', 0))
        db.session.commit()
        return jsonify({'message': 'Order updated'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/categories/update-all-defaults', methods=['POST'])
def update_all_defaults():
    try:
        data = request.json.get('updates', [])
        for upd in data:
            cat = Category.query.get(upd['category_id'])
            if cat:
                amount, error = validate_amount(upd['amount'])
                if error:
                    return jsonify({'error': f"Invalid amount for {cat.name}: {error}"}), 400
                cat.default_budget = amount
        db.session.commit()
        return jsonify({'message': 'Default budgets updated successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
####
# API: Category Groups
####
@app.route("/api/category-groups")
def list_category_groups():
    try:
        gtype = request.args.get("type")
        q = CategoryGroup.query
        if gtype:
            q = q.filter_by(type=gtype)
        groups = q.order_by(CategoryGroup.sort_order, CategoryGroup.id).all()
        return jsonify([
            {"id": g.id, "name": g.name, "type": g.type, "sort_order": g.sort_order}
            for g in groups
        ])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/category-groups", methods=["POST"])
def create_category_group():
    try:
        data = request.json
        if not data.get("name") or not data.get("type"):
            return jsonify({"error": "Name and type required"}), 400
        existing = CategoryGroup.query.filter_by(name=data["name"], type=data["type"]).first()
        if existing:
            return jsonify({"error": "Group already exists"}), 400
        min_sort = db.session.query(func.min(CategoryGroup.sort_order)).filter_by(type=data["type"]).scalar()
        if min_sort is None:
            min_sort = 0
        g = CategoryGroup(name=data["name"], type=data["type"], sort_order=min_sort - 1)
        db.session.add(g)
        db.session.commit()
        return jsonify({"id": g.id, "message": "Group created"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route("/api/category-groups/<int:group_id>", methods=["PUT"])
def update_category_group(group_id):
    try:
        group = CategoryGroup.query.get_or_404(group_id)
        data = request.json or {}
        new_name = data.get("name")
        if not new_name:
            return jsonify({"error": "Name required"}), 400
        existing = CategoryGroup.query.filter_by(name=new_name, type=group.type).first()
        if existing and existing.id != group_id:
            return jsonify({"error": "Group already exists"}), 400
        old_name = group.name
        group.name = new_name
        Category.query.filter_by(parent_category=old_name, type=group.type).update({"parent_category": new_name})
        db.session.commit()
        return jsonify({"message": "Group updated"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route("/api/category-groups/<int:group_id>", methods=["DELETE"])
def delete_category_group(group_id):
    try:
        group = CategoryGroup.query.get_or_404(group_id)
        Category.query.filter_by(parent_category=group.name, type=group.type).update({"parent_category": None})
        db.session.delete(group)
        db.session.commit()
        return jsonify({"message": "Group deleted"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@app.route('/api/category-groups/reorder', methods=['POST'])
def reorder_category_groups():
    try:
        order_data = request.json.get('order', [])
        for item in order_data:
            grp = CategoryGroup.query.get(item['id'])
            if grp:
                grp.sort_order = int(item.get('sort_order', 0))
        db.session.commit()
        return jsonify({'message': 'Order updated'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


####
# API: Transactions
####
@app.route('/api/transactions')
def list_transactions():
    try:
        month = request.args.get('month')
        tx_type = request.args.get('type')
        cat_id = request.args.get('category')
        search = request.args.get('search')
        
        q = Transaction.query
        
        if month:
            start = datetime.strptime(month + '-01', '%Y-%m-%d').date()
            end = (start.replace(day=1) + timedelta(days=32)).replace(day=1)
            q = q.filter(Transaction.date >= start, Transaction.date < end)
        if tx_type:
            q = q.filter_by(transaction_type=tx_type)
        if cat_id:
            q = q.filter_by(category_id=cat_id)
        if search:
            q = q.filter(or_(
                Transaction.description.contains(search),
                Transaction.merchant.contains(search),
                Transaction.notes.contains(search)
            ))
        
        txs = q.order_by(Transaction.date.desc()).all()
        return jsonify([{
            'id': t.id,
            'amount': t.amount,
            'type': t.transaction_type,
            'category': t.category.name,
            'category_id': t.category_id,
            'category_type': t.category.type,
            'merchant': t.merchant,
            'date': t.date.isoformat(),
            'description': t.description,
            'notes': t.notes
        } for t in txs])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/transactions', methods=['POST'])
def create_transaction():
    try:
        data = request.json
        
        # Validate required fields
        if not data.get('amount'):
            return jsonify({'error': 'Amount is required'}), 400
        if not data.get('transaction_type'):
            return jsonify({'error': 'Transaction type is required'}), 400
        if not data.get('category_id'):
            return jsonify({'error': 'Category is required'}), 400
        if not data.get('date'):
            return jsonify({'error': 'Date is required'}), 400
        
        # Validate amount
        amount, error = validate_amount(data['amount'])
        if error:
            return jsonify({'error': error}), 400
        
        # Validate date
        date_obj, error = validate_date(data['date'])
        if error:
            return jsonify({'error': error}), 400
        
        # Check if category exists
        category = Category.query.get(data['category_id'])
        if not category:
            return jsonify({'error': 'Invalid category'}), 400
        
        tx = Transaction(
            amount=amount,
            transaction_type=data['transaction_type'],
            category_id=int(data['category_id']),
            description=data.get('description', ''),
            merchant=data.get('merchant', ''),
            date=date_obj,
            notes=data.get('notes', '')
        )
        
        # Update fund balance for contributions or withdrawals
        if category.type == 'fund':
            fund = Fund.query.filter_by(name=category.name).first()
            if fund:
                if tx.transaction_type in ['expense', 'fund_contribution']:
                    fund.current_balance += tx.amount
                elif tx.transaction_type == 'fund_withdrawal':
                    if fund.current_balance < tx.amount:
                        return jsonify({'error': 'Insufficient fund balance'}), 400
                    fund.current_balance -= tx.amount
        
        db.session.add(tx)
        db.session.commit()
        return jsonify({'message': 'Transaction added successfully', 'id': tx.id})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/transactions/<int:id>', methods=['GET'])
def get_transaction(id):
    try:
        t = Transaction.query.get_or_404(id)
        return jsonify({
            'id': t.id,
            'amount': t.amount,
            'transaction_type': t.transaction_type,
            'category_id': t.category_id,
            'description': t.description,
            'merchant': t.merchant,
            'date': t.date.isoformat(),
            'notes': t.notes
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/transactions/<int:id>', methods=['PUT'])
def update_transaction(id):
    try:
        data = request.json
        tx = Transaction.query.get_or_404(id)
        
        # Validate amount if provided
        if 'amount' in data:
            amount, error = validate_amount(data['amount'])
            if error:
                return jsonify({'error': error}), 400
        else:
            amount = tx.amount
        
        # Validate date if provided
        if 'date' in data:
            date_obj, error = validate_date(data['date'])
            if error:
                return jsonify({'error': error}), 400
        else:
            date_obj = tx.date
        
        # Rollback previous fund effect
        prev_category = tx.category
        if prev_category and prev_category.type == 'fund':
            prev_fund = Fund.query.filter_by(name=prev_category.name).first()
            if prev_fund:
                if tx.transaction_type in ['expense', 'fund_contribution']:
                    # previous transaction was a fund contribution
                    prev_fund.current_balance -= tx.amount
                elif tx.transaction_type == 'fund_withdrawal':
                    prev_fund.current_balance += tx.amount
        
        # Apply updates
        tx.amount = amount
        tx.transaction_type = data.get('transaction_type', tx.transaction_type)
        tx.category_id = int(data.get('category_id', tx.category_id))
        tx.description = data.get('description', tx.description)
        tx.merchant = data.get('merchant', tx.merchant)
        tx.date = date_obj
        tx.notes = data.get('notes', tx.notes)

        # Apply new fund effect
        new_category = Category.query.get(tx.category_id)
        if new_category and new_category.type == 'fund':
            new_fund = Fund.query.filter_by(name=new_category.name).first()
            if new_fund:
                if tx.transaction_type in ['expense', 'fund_contribution']:
                    new_fund.current_balance += tx.amount
                elif tx.transaction_type == 'fund_withdrawal':
                    if new_fund.current_balance < tx.amount:
                        db.session.rollback()
                        return jsonify({'error': 'Insufficient fund balance'}), 400
                    new_fund.current_balance -= tx.amount
        
        db.session.commit()
        return jsonify({'message': 'Transaction updated successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/transactions/<int:id>', methods=['DELETE'])
def delete_transaction(id):
    try:
        tx = Transaction.query.get_or_404(id)
        # Rollback fund if needed
        if tx.category.type == 'fund':
            f = Fund.query.filter_by(name=tx.category.name).first()
            if f:
                if tx.transaction_type in ['expense', 'fund_contribution']:
                    # deleting a fund contribution
                    f.current_balance -= tx.amount
                elif tx.transaction_type == 'fund_withdrawal':
                    f.current_balance += tx.amount
        db.session.delete(tx)
        db.session.commit()
        return jsonify({'message': 'Transaction deleted'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

####
# API: Funds
####
@app.route('/api/funds')
def list_funds():
    try:
        fs = Fund.query.order_by(Fund.name).all()
        return jsonify([{
            'id': f.id,
            'name': f.name,
            'goal': f.goal,
            'goal_date': f.goal_date.isoformat() if f.goal_date else None,
            'balance': f.current_balance,
            'progress': (f.current_balance / f.goal * 100) if f.goal else 0,
            'monthly_contribution': f.monthly_contribution,
            'recommended_contribution': calculate_recommended_contribution(f)
        } for f in fs])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/funds', methods=['POST'])
def create_fund():
    try:
        data = request.json
        
        # Validate required fields
        if not data.get('name'):
            return jsonify({'error': 'Fund name is required'}), 400
        
        # Validate amounts
        goal_amount, error = validate_amount(data.get('goal_amount', 0))
        if error:
            return jsonify({'error': f"Goal amount: {error}"}), 400
        
        balance, error = validate_amount(data.get('current_balance', 0))
        if error:
            return jsonify({'error': f"Current balance: {error}"}), 400
        
        monthly, error = validate_amount(data.get('monthly_contribution', 0))
        if error:
            return jsonify({'error': f"Monthly contribution: {error}"}), 400
        
        # Check if fund already exists
        existing = Fund.query.filter_by(name=data['name']).first()
        if existing:
            return jsonify({'error': 'Fund with this name already exists'}), 400
        
        fund = Fund(
            name=data['name'],
            goal=goal_amount,
            goal_date=datetime.strptime(data['goal_date'], '%Y-%m-%d').date() if data.get('goal_date') else None,
            current_balance=balance,
            monthly_contribution=monthly
        )
        db.session.add(fund)
        
        # Create a fund category with the monthly contribution as default budget
        cat = Category(
            name=fund.name,
            type='fund',
            default_budget=monthly,
            parent_category='Savings',
            is_custom=True
        )
        db.session.add(cat)
        db.session.commit()
        return jsonify({'message': 'Fund created successfully', 'id': fund.id})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/funds/<int:id>', methods=['GET'])
def get_fund(id):
    try:
        fund = Fund.query.get_or_404(id)
        return jsonify({
            'id': fund.id,
            'name': fund.name,
            'goal': fund.goal,
            'goal_date': fund.goal_date.isoformat() if fund.goal_date else None,
            'current_balance': fund.current_balance,
            'monthly_contribution': fund.monthly_contribution
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/funds/<int:id>', methods=['PUT'])
def update_fund(id):
    try:
        data = request.json
        fund = Fund.query.get_or_404(id)
        
        # Update fund details
        old_name = fund.name
        fund.name = data.get('name', fund.name)
        
        # Validate amounts
        if 'goal_amount' in data:
            goal_amount, error = validate_amount(data['goal_amount'])
            if error:
                return jsonify({'error': f"Goal amount: {error}"}), 400
            fund.goal = goal_amount
            
        if 'monthly_contribution' in data:
            monthly, error = validate_amount(data['monthly_contribution'])
            if error:
                return jsonify({'error': f"Monthly contribution: {error}"}), 400
            fund.monthly_contribution = monthly
        
        if 'goal_date' in data:
            fund.goal_date = datetime.strptime(data['goal_date'], '%Y-%m-%d').date() if data['goal_date'] else None
        
        # Update the associated category name if fund name changed
        if old_name != fund.name:
            category = Category.query.filter_by(name=old_name, type='fund').first()
            if category:
                category.name = fund.name
                # Also update the default budget for this category if monthly contribution changed
                category.default_budget = fund.monthly_contribution
        
        db.session.commit()
        return jsonify({'message': 'Fund updated successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/funds/<int:id>', methods=['DELETE'])
def delete_fund(id):
    try:
        fund = Fund.query.get_or_404(id)
        fund_name = fund.name
        
        # Delete associated category
        category = Category.query.filter_by(name=fund_name, type='fund').first()
        if category:
            # Delete all transactions for this fund
            Transaction.query.filter_by(category_id=category.id).delete()
            # Delete any budgets for this category
            Budget.query.filter_by(category_id=category.id).delete()
            # Delete the category
            db.session.delete(category)
        
        # Delete the fund
        db.session.delete(fund)
        db.session.commit()
        
        return jsonify({'message': 'Fund deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
def contribute_to_fund(id):
    try:
        data = request.json
        fund = Fund.query.get_or_404(id)
        
        amount, error = validate_amount(data.get('amount'))
        if error:
            return jsonify({'error': error}), 400
        
        # Create a fund contribution transaction
        category = Category.query.filter_by(name=fund.name, type='fund').first()
        if not category:
            return jsonify({'error': 'Fund category not found'}), 400
        
        tx = Transaction(
            amount=amount,
            transaction_type='fund_contribution',
            category_id=category.id,
            description=f'Contribution to {fund.name}',
            date=datetime.now().date(),
            notes=data.get('notes', '')
        )
        
        fund.current_balance += amount
        db.session.add(tx)
        db.session.commit()
        
        return jsonify({'message': 'Contribution successful', 'new_balance': fund.current_balance})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/funds/<int:id>/withdraw', methods=['POST'])
def withdraw_from_fund(id):
    try:
        data = request.json
        fund = Fund.query.get_or_404(id)
        
        amount, error = validate_amount(data.get('amount'))
        if error:
            return jsonify({'error': error}), 400
        
        if fund.current_balance < amount:
            return jsonify({'error': 'Insufficient fund balance'}), 400
        
        # Create a fund withdrawal transaction
        category = Category.query.filter_by(name=fund.name, type='fund').first()
        if not category:
            return jsonify({'error': 'Fund category not found'}), 400
        
        tx = Transaction(
            amount=amount,
            transaction_type='fund_withdrawal',
            category_id=category.id,
            description=f'Withdrawal from {fund.name}',
            date=datetime.now().date(),
            notes=data.get('notes', '')
        )
        
        fund.current_balance -= amount
        db.session.add(tx)
        db.session.commit()
        
        return jsonify({'message': 'Withdrawal successful', 'new_balance': fund.current_balance})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/funds/refresh', methods=['POST'])
def refresh_funds():
    try:
        funds = Fund.query.all()
        for fund in funds:
            category = Category.query.filter_by(name=fund.name, type='fund').first()
            if not category:
                continue
            contributions = db.session.query(func.sum(Transaction.amount)).filter(
                Transaction.category_id == category.id,
                Transaction.transaction_type.in_(['fund_contribution', 'expense'])
            ).scalar() or 0
            withdrawals = db.session.query(func.sum(Transaction.amount)).filter(
                Transaction.category_id == category.id,
                Transaction.transaction_type == 'fund_withdrawal'
            ).scalar() or 0
            fund.current_balance = contributions - withdrawals
        db.session.commit()
        return jsonify({'message': 'Funds refreshed successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

####
# API: Budget & Comparison
####
@app.route('/api/budget/<year_month>')
def get_budget_for_month(year_month):
    try:
        # Build a list of categories with their budgeted amounts
        cats = (
            Category.query
            .filter(Category.type.in_(['income', 'deduction', 'expense', 'fund']))
            .order_by(Category.sort_order, Category.name)
            .all()
        )
        resp = []
        
        for c in cats:
            # Get default monthly budget
            monthly_budget = c.default_budget
            
            # Check if there's a custom budget for this month
            b = Budget.query.filter_by(month=year_month, category_id=c.id).first()
            is_custom = False
            if b:
                monthly_budget = b.amount
                is_custom = True
            
            resp.append({
                'id': c.id,
                'name': c.name,
                'type': c.type,
                'parent_category': c.parent_category,
                'sort_order': c.sort_order,
                'monthly_budget': monthly_budget,
                'is_custom': is_custom
            })
        
        return jsonify(resp)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/budget/<year_month>/update', methods=['POST'])
def update_budget_for_month(year_month):
    try:
        data = request.json
        cat_id = data['category_id']
        
        amount, error = validate_amount(data['amount'])
        if error:
            return jsonify({'error': error}), 400
        
        b = Budget.query.filter_by(month=year_month, category_id=cat_id).first()
        if not b:
            b = Budget(month=year_month, category_id=cat_id, amount=amount)
            db.session.add(b)
        else:
            b.amount = amount

        cat = Category.query.get(cat_id)
        if cat:
            cat.default_budget = amount

        db.session.commit()
        return jsonify({'message': 'Budget updated for this month'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/budget-comparison/<year_month>')
def budget_comparison(year_month):
    try:
        year, month = map(int, year_month.split('-'))
        start_date = datetime(year, month, 1).date()
        if month == 12:
            end_date = datetime(year + 1, 1, 1).date()
        else:
            end_date = datetime(year, month + 1, 1).date()
        
        cats = Category.query.filter(Category.type.in_(['income','deduction','expense','fund'])).all()
        comparison_data = []
        
        for cat in cats:
            # Get budget amount
            budget = Budget.query.filter_by(month=year_month, category_id=cat.id).first()
            budget_amount = budget.amount if budget else cat.default_budget
            
            # Get actual spending/income
            if cat.type in ['expense', 'fund']:
                actual = db.session.query(func.sum(Transaction.amount)).filter(
                    Transaction.category_id == cat.id,
                    Transaction.date >= start_date,
                    Transaction.date < end_date,
                    Transaction.transaction_type == 'expense'
                ).scalar() or 0
            elif cat.type == 'deduction':
                actual = db.session.query(func.sum(Transaction.amount)).filter(
                    Transaction.category_id == cat.id,
                    Transaction.date >= start_date,
                    Transaction.date < end_date,
                    Transaction.transaction_type == 'deduction'
                ).scalar() or 0
            else:
                actual = db.session.query(func.sum(Transaction.amount)).filter(
                    Transaction.category_id == cat.id,
                    Transaction.date >= start_date,
                    Transaction.date < end_date,
                    Transaction.transaction_type == 'income'
                ).scalar() or 0
            
            difference = budget_amount - actual if cat.type in ['expense','fund','deduction'] else actual - budget_amount
            percentage = (actual / budget_amount * 100) if budget_amount > 0 else 0

            comparison_data.append({
                'category': cat.name,
                'type': cat.type,
                'budgeted': budget_amount,
                'actual': actual,
                'difference': difference,
                'percentage': percentage,
                'status': 'under' if (cat.type in ['expense','fund','deduction'] and actual <= budget_amount) or
                                    (cat.type == 'income' and actual >= budget_amount) else 'over'
            })
        
        return jsonify(comparison_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/sankey-data/<period>')
@app.route('/api/sankey-data/<period>/<year_month>')
def get_sankey_data(period, year_month=None):
    try:
        # If no year_month provided, use current month
        if year_month is None:
            now = datetime.now()
            year = now.year
            month = now.month
        else:
            year, month = map(int, year_month.split('-'))
        
        if period == 'monthly':
            start_date = datetime(year, month, 1).date()
            if month == 12:
                end_date = datetime(year + 1, 1, 1).date()
            else:
                end_date = datetime(year, month + 1, 1).date()
        else:  # annual
            start_date = datetime(year, 1, 1).date()
            end_date = datetime(year + 1, 1, 1).date()
        
        transactions = Transaction.query.filter(
            Transaction.date >= start_date,
            Transaction.date < end_date
        ).all()

        nodes = []
        links = []
        node_map = {}

        # Central budget node
        node_map['Budget'] = len(nodes)
        nodes.append({'name': 'Budget', 'type': 'budget'})

        for t in transactions:
            cat = t.category
            cat_name = cat.name

            if t.transaction_type == 'income':
                if cat_name not in node_map:
                    node_map[cat_name] = len(nodes)
                    nodes.append({'name': cat_name, 'type': 'income'})
                links.append({'source': node_map[cat_name], 'target': node_map['Budget'], 'value': t.amount})

            elif t.transaction_type == 'deduction':
                if cat_name not in node_map:
                    node_map[cat_name] = len(nodes)
                    nodes.append({'name': cat_name, 'type': 'deduction'})
                links.append({'source': node_map['Budget'], 'target': node_map[cat_name], 'value': t.amount})

            elif t.transaction_type in ['expense', 'fund_contribution']:
                group_name = cat.parent_category or 'Other'
                group_key = f'group_{group_name}'

                # Add group node if not exists
                if group_key not in node_map:
                    node_map[group_key] = len(nodes)
                    nodes.append({'name': group_name, 'type': 'group'})

                # Add category node if not exists
                node_type = 'fund' if cat.type == 'fund' or t.transaction_type == 'fund_contribution' else 'expense'
                if cat_name not in node_map:
                    node_map[cat_name] = len(nodes)
                    nodes.append({'name': cat_name, 'type': node_type})

                # Link from budget to group for this transaction
                links.append({'source': node_map['Budget'], 'target': node_map[group_key], 'value': t.amount})
                # Link from group to category for this transaction
                links.append({'source': node_map[group_key], 'target': node_map[cat_name], 'value': t.amount})

        return jsonify({'nodes': nodes, 'links': links})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

####
# API: Reports
####
@app.route('/api/reports/monthly-summary/<year_month>')
def get_monthly_summary_report(year_month):
    try:
        year, month = map(int, year_month.split('-'))
        
        # Get transactions for the month
        start_date = datetime(year, month, 1).date()
        if month == 12:
            end_date = datetime(year + 1, 1, 1).date()
        else:
            end_date = datetime(year, month + 1, 1).date()
        
        transactions = Transaction.query.filter(
            Transaction.date >= start_date,
            Transaction.date < end_date
        ).all()
        
        # Group by category
        income_by_category = {}
        deduction_by_category = {}
        expense_by_category = {}
        savings_by_category = {}

        for trans in transactions:
            cat = trans.category
            if trans.transaction_type == 'income':
                income_by_category[cat.name] = income_by_category.get(cat.name, 0) + trans.amount
            elif trans.transaction_type == 'deduction':
                deduction_by_category[cat.name] = deduction_by_category.get(cat.name, 0) + trans.amount
            elif cat.type == 'fund' or trans.transaction_type == 'fund_contribution':
                savings_by_category[cat.name] = savings_by_category.get(cat.name, 0) + trans.amount
            elif trans.transaction_type == 'expense':
                parent = cat.parent_category or cat.name
                expense_by_category[parent] = expense_by_category.get(parent, 0) + trans.amount

        # Calculate totals
        gross_income = sum(income_by_category.values())
        deductions = sum(deduction_by_category.values())
        net_income = gross_income - deductions
        total_expenses = sum(expense_by_category.values())
        total_savings = sum(savings_by_category.values())
        savings_rate = (total_savings / net_income * 100) if net_income > 0 else 0
        leftover = net_income - total_expenses - total_savings

        return jsonify({
            'month': f"{calendar.month_name[month]} {year}",
            'income_breakdown': income_by_category,
            'deduction_breakdown': deduction_by_category,
            'expense_breakdown': expense_by_category,
            'savings_breakdown': savings_by_category,
            'gross_income': gross_income,
            'deductions': deductions,
            'net_income': net_income,
            'total_expenses': total_expenses,
            'total_savings': total_savings,
            'savings_rate': savings_rate,
            'leftover': leftover
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/reports/annual-overview/<year>')
def get_annual_overview(year):
    try:
        year = int(year)
        months = []
        monthly_income = []
        monthly_expenses = []
        total_income = 0
        total_expenses = 0
        
        for month in range(1, 13):
            start_date = datetime(year, month, 1).date()
            if month == 12:
                end_date = datetime(year + 1, 1, 1).date()
            else:
                end_date = datetime(year, month + 1, 1).date()
            
            # Only include months up to current date
            if start_date > datetime.now().date():
                break
            
            month_transactions = Transaction.query.filter(
                Transaction.date >= start_date,
                Transaction.date < end_date
            ).all()
            
            month_income = sum(t.amount for t in month_transactions if t.transaction_type == 'income')
            month_expenses = sum(t.amount for t in month_transactions if t.transaction_type in ['expense', 'deduction'])
            
            months.append(calendar.month_abbr[month])
            monthly_income.append(month_income)
            monthly_expenses.append(month_expenses)
            total_income += month_income
            total_expenses += month_expenses
        
        return jsonify({
            'year': year,
            'months': months,
            'monthly_income': monthly_income,
            'monthly_expenses': monthly_expenses,
            'total_income': total_income,
            'total_expenses': total_expenses,
            'total_saved': total_income - total_expenses
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/reports/category-analysis/<year_month>')
def get_category_analysis(year_month):
    try:
        year, month = map(int, year_month.split('-'))
        start_date = datetime(year, month, 1).date()
        if month == 12:
            end_date = datetime(year + 1, 1, 1).date()
        else:
            end_date = datetime(year, month + 1, 1).date()
        
        expenses = Transaction.query.filter(
            Transaction.date >= start_date,
            Transaction.date < end_date,
            Transaction.transaction_type.in_(['expense','deduction'])
        ).all()
        
        category_totals = {}
        total = 0
        
        for expense in expenses:
            cat_name = expense.category.parent_category or expense.category.name
            if cat_name not in category_totals:
                category_totals[cat_name] = 0
            category_totals[cat_name] += expense.amount
            total += expense.amount
        
        categories = []
        for name, amount in sorted(category_totals.items(), key=lambda x: x[1], reverse=True):
            categories.append({
                'name': name,
                'amount': amount,
                'percentage': (amount / total * 100) if total > 0 else 0
            })
        
        return jsonify({
            'month': year_month,
            'categories': categories,
            'total': total
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/reports/spending-trends')
def get_spending_trends():
    try:
        start_param = request.args.get('start')
        end_param = request.args.get('end')

        if start_param and end_param:
            start_date = datetime.strptime(start_param, "%Y-%m").date()
            end_month = datetime.strptime(end_param, "%Y-%m").date()
        else:
            end_date = datetime.now().date()
            start_date = (end_date - timedelta(days=180)).replace(day=1)
            end_month = end_date

        months = []
        expenses = []

        current = start_date.replace(day=1)
        end_marker = end_month.replace(day=1)

        while current <= end_marker:
            month_start = current
            if current.month == 12:
                month_end = datetime(current.year + 1, 1, 1).date()
            else:
                month_end = datetime(current.year, current.month + 1, 1).date()

            month_expenses = db.session.query(func.sum(Transaction.amount)).filter(
                Transaction.date >= month_start,
                Transaction.date < month_end,
                Transaction.transaction_type.in_(['expense','deduction'])
            ).scalar() or 0

            months.append(f"{calendar.month_abbr[current.month]} {current.year}")
            expenses.append(month_expenses)

            if current.month == 12:
                current = datetime(current.year + 1, 1, 1).date()
            else:
                current = datetime(current.year, current.month + 1, 1).date()

        avg_spending = sum(expenses) / len(expenses) if expenses else 0
        highest_idx = expenses.index(max(expenses)) if expenses else 0

        if len(expenses) >= 2:
            recent_avg = sum(expenses[-2:]) / 2
            older_avg = sum(expenses[:-2]) / (len(expenses) - 2) if len(expenses) > 2 else expenses[0]
            trend = 'increasing' if recent_avg > older_avg else 'decreasing'
        else:
            trend = 'insufficient data'

        return jsonify({
            'months': months,
            'expenses': expenses,
            'average_spending': avg_spending,
            'highest_month': months[highest_idx] if months else '',
            'highest_amount': expenses[highest_idx] if expenses else 0,
            'trend': trend
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/reports/period-comparison')
def period_comparison():
    try:
        start1 = request.args.get('start1')
        end1 = request.args.get('end1')
        start2 = request.args.get('start2')
        end2 = request.args.get('end2')

        if not all([start1, end1, start2, end2]):
            return jsonify({'error': 'Missing date range parameters'}), 400

        def collect_range(start, end):
            start_date = datetime.strptime(start, "%Y-%m").date().replace(day=1)
            end_marker = datetime.strptime(end, "%Y-%m").date().replace(day=1)
            months = []
            totals = []
            current = start_date
            while current <= end_marker:
                if current.month == 12:
                    next_month = datetime(current.year + 1, 1, 1).date()
                else:
                    next_month = datetime(current.year, current.month + 1, 1).date()
                month_total = db.session.query(func.sum(Transaction.amount)).filter(
                    Transaction.date >= current,
                    Transaction.date < next_month,
                    Transaction.transaction_type.in_(['expense','deduction'])
                ).scalar() or 0
                months.append(f"{calendar.month_abbr[current.month]} {current.year}")
                totals.append(month_total)
                current = next_month
            return months, totals

        months1, totals1 = collect_range(start1, end1)
        months2, totals2 = collect_range(start2, end2)

        return jsonify({
            'period1': {'months': months1, 'totals': totals1},
            'period2': {'months': months2, 'totals': totals2}
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/reports/fund-progress')
def get_fund_progress_report():
    try:
        funds = Fund.query.all()
        fund_data = []
        
        for fund in funds:
            fund_data.append({
                'name': fund.name,
                'balance': fund.current_balance,
                'goal': fund.goal,
                'progress': (fund.current_balance / fund.goal * 100) if fund.goal else 0,
                'goal_date': fund.goal_date.isoformat() if fund.goal_date else None,
                'recommended_contribution': calculate_recommended_contribution(fund)
            })
        
        return jsonify({'funds': fund_data})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

####
# API: Export
####
@app.route('/api/export/csv')
def export_csv():
    try:
        # Create CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write headers
        writer.writerow(['Date', 'Type', 'Category', 'Description', 'Merchant', 'Amount', 'Notes'])
        
        # Get all transactions
        transactions = Transaction.query.order_by(Transaction.date.desc()).all()
        
        for t in transactions:
            writer.writerow([
                t.date.isoformat(),
                t.transaction_type,
                t.category.name,
                t.description or '',
                t.merchant or '',
                t.amount,
                t.notes or ''
            ])
        
        # Create response
        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename=budget_transactions_{datetime.now().strftime("%Y%m%d")}.csv'
            }
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/export/json')
def export_json():
    try:
        # Get all data
        data = {
            'export_date': datetime.now().isoformat(),
            'categories': [],
            'transactions': [],
            'funds': [],
            'budgets': []
        }
        
        # Categories
        for c in Category.query.all():
            data['categories'].append({
                'id': c.id,
                'name': c.name,
                'type': c.type,
                'default_budget': c.default_budget,
                'parent_category': c.parent_category
            })
        
        # Transactions
        for t in Transaction.query.all():
            data['transactions'].append({
                'id': t.id,
                'date': t.date.isoformat(),
                'type': t.transaction_type,
                'category': t.category.name,
                'amount': t.amount,
                'description': t.description,
                'merchant': t.merchant,
                'notes': t.notes
            })
        
        # Funds
        for f in Fund.query.all():
            data['funds'].append({
                'name': f.name,
                'goal': f.goal,
                'current_balance': f.current_balance,
                'goal_date': f.goal_date.isoformat() if f.goal_date else None,
                'monthly_contribution': f.monthly_contribution
            })
        
        # Budgets
        for b in Budget.query.all():
            data['budgets'].append({
                'month': b.month,
                'category': b.category.name,
                'amount': b.amount
            })
        
        return Response(
            json.dumps(data, indent=2),
            mimetype='application/json',
            headers={
                'Content-Disposition': f'attachment; filename=budget_data_{datetime.now().strftime("%Y%m%d")}.json'
            }
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/import-excel', methods=['POST'])
def import_excel():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if file and file.filename.endswith(('.xlsx', '.xls')):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        try:
            # Process the Excel file
            # This would need custom logic based on your Excel structure
            # For now, returning success
            return jsonify({'message': 'File uploaded successfully. Processing will be implemented based on your Excel structure.'})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
        finally:
            # Clean up uploaded file
            if os.path.exists(filepath):
                os.remove(filepath)

    return jsonify({'error': 'Invalid file format'}), 400

@app.route('/api/import-csv', methods=['POST'])
def import_csv_route():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not file.filename.endswith('.csv'):
        return jsonify({'error': 'Invalid file format'}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    try:
        rows, unknown = import_csv(filepath)
        created = 0
        for row in rows:
            if not row.get('date'):
                continue
            cat = Category.query.filter_by(name=row['category_guess']).first()
            if not cat:
                cat = Category(name=row['category_guess'], type='expense')
                db.session.add(cat)
                db.session.commit()
            date_str = str(row['date']).strip()
            date_obj = None
            for fmt in ('%m/%d/%Y', '%m/%d/%y', '%m/%d'):
                try:
                    dt = datetime.strptime(date_str, fmt)
                    if fmt == '%m/%d':
                        dt = dt.replace(year=datetime.now().year)
                    date_obj = dt.date()
                    break
                except ValueError:
                    continue
            if not date_obj:
                continue
            raw_amount = float(row['amount'])
            tx = Transaction(
                amount=abs(raw_amount),
                transaction_type='expense' if raw_amount < 0 else 'income',
                category_id=cat.id,
                description=row['merchant'],
                merchant=row['merchant'],
                date=date_obj
            )
            db.session.add(tx)
            created += 1
        db.session.commit()
        return jsonify({'message': f'Imported {created} transactions', 'unknown_merchants': list(unknown)}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)


@app.route('/api/category-keywords', methods=['POST'])
def add_category_keyword_route():
    data = request.get_json() or {}
    keyword = data.get('keyword')
    category = data.get('category')
    if not keyword or not category:
        return jsonify({'error': 'keyword and category required'}), 400
    add_keyword_category(keyword, category)
    return jsonify({'message': 'Keyword added'}), 200


# Database initialization function
def init_database():
    """Initialize the database with default categories"""
    # Check if we already have categories
    if Category.query.first() is None:
        default_categories = [
            # Income categories
            Category(name='Gross Salary', type='income', parent_category='Income', default_budget=0, is_custom=False),
            Category(name='401k Deduction', type='deduction', parent_category='Deductions', default_budget=0, is_custom=False),
            Category(name='Health Insurance Deduction', type='deduction', parent_category='Deductions', default_budget=0, is_custom=False),
            Category(name='Federal Tax Deduction', type='deduction', parent_category='Deductions', default_budget=0, is_custom=False),
            Category(name='State Tax Deduction', type='deduction', parent_category='Deductions', default_budget=0, is_custom=False),
            Category(name='Social Security Deduction', type='deduction', parent_category='Deductions', default_budget=0, is_custom=False),
            Category(name='Medicare Deduction', type='deduction', parent_category='Deductions', default_budget=0, is_custom=False),
            
            # Basic expense categories
            Category(name='Rent/Mortgage', type='expense', parent_category='Housing', default_budget=0, is_custom=False),
            Category(name='Groceries', type='expense', parent_category='Food', default_budget=0, is_custom=False),
            Category(name='Gas', type='expense', parent_category='Transportation', default_budget=0, is_custom=False),
            Category(name='Utilities', type='expense', parent_category='Housing', default_budget=0, is_custom=False),
            Category(name='Internet', type='expense', parent_category='Housing', default_budget=0, is_custom=False),
            Category(name='Phone', type='expense', parent_category='Personal', default_budget=0, is_custom=False),
            Category(name='Uncategorized', type='expense', parent_category='Other', default_budget=0, is_custom=False),
        ]
        
        for category in default_categories:
            db.session.add(category)
        
        try:
            db.session.commit()
            print("Default categories created successfully!")
        except Exception as e:
            db.session.rollback()
            print(f"Error creating default categories: {str(e)}")

# Initialize groups based on existing categories
def init_groups():
    if CategoryGroup.query.first() is None:
        groups = Category.query.with_entities(Category.parent_category, Category.type).distinct().all()
        order = 0
        for name, typ in groups:
            if name:
                db.session.add(CategoryGroup(name=name, type=typ, sort_order=order))
                order += 1
        db.session.commit()

# Database migration function
def migrate_database():
    """Add missing columns to existing database"""
    import sqlite3
    
    try:
        # Get database path
        db_path = app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
        if not os.path.exists(db_path):
            return  # No database to migrate
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check for missing columns in category table
        cursor.execute("PRAGMA table_info(category)")
        existing_columns = [column[1] for column in cursor.fetchall()]
        
        if 'is_custom' not in existing_columns:
            print("Adding is_custom column to category table...")
            cursor.execute("ALTER TABLE category ADD COLUMN is_custom BOOLEAN DEFAULT 1")

            # Mark default categories
            default_names = [
                'Gross Salary', '401k Deduction', 'Health Insurance Deduction',
                'Federal Tax Deduction', 'State Tax Deduction',
                'Social Security Deduction', 'Medicare Deduction',
                'Rent/Mortgage', 'Groceries', 'Gas', 'Utilities',
                'Internet', 'Phone', 'Uncategorized'
            ]
            for name in default_names:
                cursor.execute("UPDATE category SET is_custom = 0 WHERE name = ?", (name,))

            conn.commit()
            print("✓ Database migration completed")

        # Check for missing columns in category_group table
        cursor.execute("PRAGMA table_info(category_group)")
        group_columns = [column[1] for column in cursor.fetchall()]
        if 'sort_order' not in group_columns:
            cursor.execute("ALTER TABLE category_group ADD COLUMN sort_order INTEGER DEFAULT 0")
            conn.commit()
            print("✓ Added sort_order column to category_group table")

        deduction_names = [
            '401k Deduction', 'Health Insurance Deduction', 'Federal Tax Deduction',
            'State Tax Deduction', 'Social Security Deduction', 'Medicare Deduction'
        ]
        for name in deduction_names:
            cursor.execute(
                "UPDATE category SET type='deduction', parent_category='Deductions'"
                " WHERE name=? AND type='income'",
                (name,)
            )
        conn.commit()

        # Check fund table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='fund'")
        if cursor.fetchone():
            cursor.execute("PRAGMA table_info(fund)")
            fund_columns = [column[1] for column in cursor.fetchall()]
            
            if 'monthly_contribution' not in fund_columns:
                cursor.execute("ALTER TABLE fund ADD COLUMN monthly_contribution REAL DEFAULT 0.0")
                conn.commit()
                print("✓ Added monthly_contribution column to fund table")
        
        conn.close()
    except Exception as e:
        print(f"Migration warning: {str(e)}")

# Create tables and initialize default data
if __name__ == '__main__':
    with app.app_context():
        try:
            # Run migration first if database exists
            migrate_database()
            
            # Create all tables
            db.create_all()
            print("Database tables created successfully!")
            
            # Initialize default categories
            init_database()
            init_groups()
            
        except Exception as e:
            print(f"Error initializing database: {str(e)}")
            print("Make sure all required packages are installed.")
    
    try:
        print("Starting Budget Tracker application...")
        print("Access the application at: http://localhost:5000")
        print("Press Ctrl+C to stop the server")
        app.run(debug=True, host='0.0.0.0', port=5000)
    except Exception as e:
        print(f"\nError starting application: {str(e)}")
        print("\nCommon issues:")
        print("1. Port 5000 might be in use - try closing other applications")
        print("2. Missing dependencies - run: pip install -r requirements.txt")
        print("3. Python version issues - make sure you're using Python 3.8+")
        input("\nPress Enter to exit...")