import pymysql
pymysql.install_as_MySQLdb()


from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime, date
import os
from decimal import Decimal
import json
from config import Config
from sqlalchemy import Numeric


app = Flask(__name__)
CORS(app)

# Database Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:Riju@localhost/finance_tracker'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your-secret-key-here'

# Initialize SQLAlchemy
db = SQLAlchemy(app)

# Transaction Model
class Transaction(db.Model):
    __tablename__ = 'transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(10), nullable=False)  # 'income' or 'expense'
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(200), nullable=False)
    date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'type': self.type,
            'amount': float(self.amount),
            'category': self.category,
            'description': self.description,
            'date': self.date.isoformat(),
            'created_at': self.created_at.isoformat()
        }

# Category Model
class Category(db.Model):
    __tablename__ = 'categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    type = db.Column(db.String(10), nullable=False)  # 'income' or 'expense'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'type': self.type
        }

# Budget Model
class Budget(db.Model):
    __tablename__ = 'budgets'
    
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    month = db.Column(db.Integer, nullable=False)
    year = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'category': self.category,
            'amount': float(self.amount),
            'month': self.month,
            'year': self.year
        }

# Create tables
from sqlalchemy import inspect

@app.before_request
def create_tables():
    inspector = inspect(db.engine)
    if not inspector.has_table('transactions'):
        db.create_all()
    
    # Add default categories if they don't exist
    if Category.query.count() == 0:
        default_categories = [
            # Income categories
            Category(name='Salary', type='income'),
            Category(name='Freelance', type='income'),
            Category(name='Investment', type='income'),
            Category(name='Gift', type='income'),
            Category(name='Other Income', type='income'),
            
            # Expense categories
            Category(name='Food', type='expense'),
            Category(name='Transportation', type='expense'),
            Category(name='Entertainment', type='expense'),
            Category(name='Bills', type='expense'),
            Category(name='Shopping', type='expense'),
            Category(name='Healthcare', type='expense'),
            Category(name='Other Expense', type='expense'),
        ]
        
        for category in default_categories:
            db.session.add(category)
        
        db.session.commit()

# Routes

@app.route('/')
def index():
    return render_template('index.html')

# API Routes

@app.route('/api/transactions', methods=['GET'])
def get_transactions():
    try:
        # Get query parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        transaction_type = request.args.get('type')
        category = request.args.get('category')
        date_filter = request.args.get('date')
        
        # Build query
        query = Transaction.query
        
        if transaction_type:
            query = query.filter(Transaction.type == transaction_type)
        
        if category:
            query = query.filter(Transaction.category == category)
        
        if date_filter:
            try:
                filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
                query = query.filter(Transaction.date == filter_date)
            except ValueError:
                pass
        
        # Order by date (newest first)
        query = query.order_by(Transaction.date.desc(), Transaction.created_at.desc())
        
        # Paginate
        transactions = query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        return jsonify({
            'transactions': [t.to_dict() for t in transactions.items],
            'total': transactions.total,
            'pages': transactions.pages,
            'current_page': page
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/transactions', methods=['POST'])
def add_transaction():
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['type', 'amount', 'category', 'description', 'date']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Validate transaction type
        if data['type'] not in ['income', 'expense']:
            return jsonify({'error': 'Invalid transaction type'}), 400
        
        # Parse date
        try:
            transaction_date = datetime.strptime(data['date'], '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
        
        # Create new transaction
        transaction = Transaction(
            type=data['type'],
            amount=Decimal(str(data['amount'])),
            category=data['category'],
            description=data['description'],
            date=transaction_date
        )
        
        db.session.add(transaction)
        db.session.commit()
        
        return jsonify({
            'message': 'Transaction added successfully',
            'transaction': transaction.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/transactions/<int:transaction_id>', methods=['PUT'])
def update_transaction(transaction_id):
    try:
        transaction = Transaction.query.get_or_404(transaction_id)
        data = request.get_json()
        
        # Update fields if provided
        if 'type' in data:
            if data['type'] not in ['income', 'expense']:
                return jsonify({'error': 'Invalid transaction type'}), 400
            transaction.type = data['type']
        
        if 'amount' in data:
            transaction.amount = Decimal(str(data['amount']))
        
        if 'category' in data:
            transaction.category = data['category']
        
        if 'description' in data:
            transaction.description = data['description']
        
        if 'date' in data:
            try:
                transaction.date = datetime.strptime(data['date'], '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
        
        db.session.commit()
        
        return jsonify({
            'message': 'Transaction updated successfully',
            'transaction': transaction.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/transactions/<int:transaction_id>', methods=['DELETE'])
def delete_transaction(transaction_id):
    try:
        transaction = Transaction.query.get_or_404(transaction_id)
        db.session.delete(transaction)
        db.session.commit()
        
        return jsonify({'message': 'Transaction deleted successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/categories', methods=['GET'])
def get_categories():
    try:
        categories = Category.query.all()
        
        # Group by type
        result = {
            'income': [c.to_dict() for c in categories if c.type == 'income'],
            'expense': [c.to_dict() for c in categories if c.type == 'expense']
        }
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/categories', methods=['POST'])
def add_category():
    try:
        data = request.get_json()
        
        # Validate required fields
        if 'name' not in data or 'type' not in data:
            return jsonify({'error': 'Missing required fields: name, type'}), 400
        
        if data['type'] not in ['income', 'expense']:
            return jsonify({'error': 'Invalid category type'}), 400
        
        # Check if category already exists
        existing = Category.query.filter_by(name=data['name'], type=data['type']).first()
        if existing:
            return jsonify({'error': 'Category already exists'}), 400
        
        # Create new category
        category = Category(
            name=data['name'],
            type=data['type']
        )
        
        db.session.add(category)
        db.session.commit()
        
        return jsonify({
            'message': 'Category added successfully',
            'category': category.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/dashboard', methods=['GET'])
def get_dashboard_data():
    try:
        # Get all transactions
        transactions = Transaction.query.all()
        
        # Calculate totals
        total_income = sum(t.amount for t in transactions if t.type == 'income')
        total_expenses = sum(t.amount for t in transactions if t.type == 'expense')
        balance = total_income - total_expenses
        
        # Calculate monthly data
        current_month = datetime.now().month
        current_year = datetime.now().year
        
        monthly_transactions = [
            t for t in transactions 
            if t.date.month == current_month and t.date.year == current_year
        ]
        
        monthly_income = sum(t.amount for t in monthly_transactions if t.type == 'income')
        monthly_expenses = sum(t.amount for t in monthly_transactions if t.type == 'expense')
        monthly_balance = monthly_income - monthly_expenses
        
        # Category breakdown
        expense_categories = {}
        for t in transactions:
            if t.type == 'expense':
                category = t.category
                expense_categories[category] = expense_categories.get(category, 0) + float(t.amount)
        
        # Monthly trends (last 6 months)
        monthly_trends = {}
        for i in range(6):
            month = (current_month - i - 1) % 12 + 1
            year = current_year if current_month - i > 0 else current_year - 1
            
            month_transactions = [
                t for t in transactions 
                if t.date.month == month and t.date.year == year
            ]
            
            month_key = f"{year}-{month:02d}"
            monthly_trends[month_key] = {
                'income': float(sum(t.amount for t in month_transactions if t.type == 'income')),
                'expense': float(sum(t.amount for t in month_transactions if t.type == 'expense'))
            }
        
        return jsonify({
            'totals': {
                'income': float(total_income),
                'expenses': float(total_expenses),
                'balance': float(balance)
            },
            'monthly': {
                'income': float(monthly_income),
                'expenses': float(monthly_expenses),
                'balance': float(monthly_balance)
            },
            'expense_categories': expense_categories,
            'monthly_trends': monthly_trends,
            'recent_transactions': [
                t.to_dict() for t in 
                Transaction.query.order_by(Transaction.date.desc()).limit(5).all()
            ]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/reports/monthly', methods=['GET'])
def get_monthly_report():
    try:
        year = request.args.get('year', datetime.now().year, type=int)
        
        monthly_data = {}
        for month in range(1, 13):
            transactions = Transaction.query.filter(
                db.extract('month', Transaction.date) == month,
                db.extract('year', Transaction.date) == year
            ).all()
            
            income = sum(t.amount for t in transactions if t.type == 'income')
            expenses = sum(t.amount for t in transactions if t.type == 'expense')
            
            monthly_data[f"{year}-{month:02d}"] = {
                'income': float(income),
                'expenses': float(expenses),
                'balance': float(income - expenses)
            }
        
        return jsonify(monthly_data)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/reports/category', methods=['GET'])
def get_category_report():
    try:
        transaction_type = request.args.get('type', 'expense')
        
        if transaction_type not in ['income', 'expense']:
            return jsonify({'error': 'Invalid transaction type'}), 400
        
        transactions = Transaction.query.filter_by(type=transaction_type).all()
        
        category_data = {}
        for transaction in transactions:
            category = transaction.category
            if category not in category_data:
                category_data[category] = {
                    'total': 0,
                    'count': 0,
                    'transactions': []
                }
            
            category_data[category]['total'] += float(transaction.amount)
            category_data[category]['count'] += 1
            category_data[category]['transactions'].append(transaction.to_dict())
        
        return jsonify(category_data)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Budget Routes
@app.route('/api/budgets', methods=['GET'])
def get_budgets():
    try:
        month = request.args.get('month', datetime.now().month, type=int)
        year = request.args.get('year', datetime.now().year, type=int)
        
        budgets = Budget.query.filter_by(month=month, year=year).all()
        
        budget_data = []
        for budget in budgets:
            # Calculate actual spending for this category
            actual_spending = db.session.query(db.func.sum(Transaction.amount)).filter(
                Transaction.category == budget.category,
                Transaction.type == 'expense',
                db.extract('month', Transaction.date) == month,
                db.extract('year', Transaction.date) == year
            ).scalar() or 0
            
            budget_info = budget.to_dict()
            budget_info['actual'] = float(actual_spending)
            budget_info['remaining'] = float(budget.amount - actual_spending)
            budget_info['percentage'] = (float(actual_spending) / float(budget.amount)) * 100 if budget.amount > 0 else 0
            
            budget_data.append(budget_info)
        
        return jsonify(budget_data)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/budgets', methods=['POST'])
def add_budget():
    try:
        data = request.get_json()
        
        required_fields = ['category', 'amount', 'month', 'year']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Check if budget already exists for this category and period
        existing = Budget.query.filter_by(
            category=data['category'],
            month=data['month'],
            year=data['year']
        ).first()
        
        if existing:
            return jsonify({'error': 'Budget already exists for this category and period'}), 400
        
        budget = Budget(
            category=data['category'],
            amount=Decimal(str(data['amount'])),
            month=data['month'],
            year=data['year']
        )
        
        db.session.add(budget)
        db.session.commit()
        
        return jsonify({
            'message': 'Budget added successfully',
            'budget': budget.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Resource not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)