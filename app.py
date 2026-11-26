"""
STEP 2: Flask API server - connects to SQLite and serves the dashboard.

Run after setup_database.py:  python3 app.py
Then open http://localhost:5050
"""

from flask import Flask, jsonify, request, send_from_directory
import sqlite3

app = Flask(__name__, static_folder='static')


def get_db():
    conn = sqlite3.connect('demo.db')
    conn.row_factory = sqlite3.Row
    return conn


# --- Serve frontend ---
@app.route('/')
def index():
    return send_from_directory('static', 'index.html')


# --- API: Summary stats ---
@app.route('/api/summary')
def summary():
    db = get_db()
    status = request.args.get('status', 'all')
    where = "WHERE o.status = 'completed'" if status == 'completed' else ''

    revenue = db.execute(f'''
        SELECT COALESCE(SUM(o.quantity * p.price), 0) as revenue
        FROM orders o JOIN products p ON o.product_id = p.id {where}
    ''').fetchone()['revenue']

    total_orders = db.execute(f'SELECT COUNT(*) as cnt FROM orders o {where}').fetchone()['cnt']
    total_customers = db.execute('SELECT COUNT(*) as cnt FROM customers').fetchone()['cnt']
    total_products = db.execute('SELECT COUNT(*) as cnt FROM products').fetchone()['cnt']

    # Avg order value
    avg_order = revenue / total_orders if total_orders > 0 else 0

    db.close()
    return jsonify({
        'total_revenue': round(revenue, 2),
        'total_orders': total_orders,
        'total_customers': total_customers,
        'total_products': total_products,
        'avg_order_value': round(avg_order, 2),
    })


# --- API: Sales by category (with optional date filter) ---
@app.route('/api/sales-by-category')
def sales_by_category():
    db = get_db()
    days = request.args.get('days', None)
    where = f"AND o.order_date >= date('now', '-{int(days)} days')" if days else ''

    rows = db.execute(f'''
        SELECT p.category, ROUND(SUM(o.quantity * p.price), 2) as revenue, SUM(o.quantity) as units
        FROM orders o JOIN products p ON o.product_id = p.id
        WHERE o.status = 'completed' {where}
        GROUP BY p.category ORDER BY revenue DESC
    ''').fetchall()
    db.close()
    return jsonify([dict(r) for r in rows])


# --- API: Sales over time (with granularity option) ---
@app.route('/api/sales-over-time')
def sales_over_time():
    db = get_db()
    days = request.args.get('days', '180')
    group_by = request.args.get('group', 'day')

    if group_by == 'week':
        date_expr = "strftime('%Y-W%W', o.order_date)"
    elif group_by == 'month':
        date_expr = "strftime('%Y-%m', o.order_date)"
    else:
        date_expr = "o.order_date"

    rows = db.execute(f'''
        SELECT {date_expr} as period,
               ROUND(SUM(o.quantity * p.price), 2) as revenue,
               COUNT(o.id) as order_count
        FROM orders o JOIN products p ON o.product_id = p.id
        WHERE o.status = 'completed' AND o.order_date >= date('now', '-{int(days)} days')
        GROUP BY period ORDER BY period
    ''').fetchall()
    db.close()
    return jsonify([dict(r) for r in rows])


# --- API: Top products ---
@app.route('/api/top-products')
def top_products():
    db = get_db()
    category = request.args.get('category', None)
    where = f"AND p.category = '{category}'" if category else ''

    rows = db.execute(f'''
        SELECT p.name, p.category, SUM(o.quantity) as total_sold,
               ROUND(SUM(o.quantity * p.price), 2) as revenue
        FROM orders o JOIN products p ON o.product_id = p.id
        WHERE o.status = 'completed' {where}
        GROUP BY p.name ORDER BY revenue DESC
    ''').fetchall()
    db.close()
    return jsonify([dict(r) for r in rows])


# --- API: Top customers ---
@app.route('/api/top-customers')
def top_customers():
    db = get_db()
    city = request.args.get('city', None)
    where = f"AND c.city = '{city}'" if city else ''

    rows = db.execute(f'''
        SELECT c.name, c.city, c.email, COUNT(o.id) as order_count,
               ROUND(SUM(o.quantity * p.price), 2) as total_spent
        FROM orders o
        JOIN customers c ON o.customer_id = c.id
        JOIN products p ON o.product_id = p.id
        WHERE o.status = 'completed' {where}
        GROUP BY c.id ORDER BY total_spent DESC
    ''').fetchall()
    db.close()
    return jsonify([dict(r) for r in rows])


# --- API: Recent orders ---
@app.route('/api/recent-orders')
def recent_orders():
    db = get_db()
    limit = min(int(request.args.get('limit', 20)), 100)
    status = request.args.get('status', None)
    where = f"WHERE o.status = '{status}'" if status else ''

    rows = db.execute(f'''
        SELECT o.id, c.name as customer, p.name as product, p.category,
               o.quantity, o.status, o.order_date, ROUND(o.quantity * p.price, 2) as total
        FROM orders o
        JOIN customers c ON o.customer_id = c.id
        JOIN products p ON o.product_id = p.id
        {where}
        ORDER BY o.order_date DESC, o.id DESC
        LIMIT {limit}
    ''').fetchall()
    db.close()
    return jsonify([dict(r) for r in rows])


# --- API: Order status breakdown ---
@app.route('/api/order-status')
def order_status():
    db = get_db()
    rows = db.execute('''
        SELECT status, COUNT(*) as count FROM orders GROUP BY status ORDER BY count DESC
    ''').fetchall()
    db.close()
    return jsonify([dict(r) for r in rows])


# --- API: Cities list (for filter dropdowns) ---
@app.route('/api/cities')
def cities():
    db = get_db()
    rows = db.execute('SELECT DISTINCT city FROM customers ORDER BY city').fetchall()
    db.close()
    return jsonify([r['city'] for r in rows])


# --- API: Categories list ---
@app.route('/api/categories')
def categories():
    db = get_db()
    rows = db.execute('SELECT DISTINCT category FROM products ORDER BY category').fetchall()
    db.close()
    return jsonify([r['category'] for r in rows])


# --- API: Custom SQL query (for the AI chat / learn mode) ---
@app.route('/api/query', methods=['POST'])
def run_query():
    """Run a read-only SQL query. Only SELECT statements allowed."""
    data = request.get_json()
    sql = data.get('sql', '').strip()

    if not sql.upper().startswith('SELECT'):
        return jsonify({'error': 'Only SELECT queries are allowed'}), 400

    db = get_db()
    try:
        rows = db.execute(sql).fetchall()
        columns = rows[0].keys() if rows else []
        result = [dict(r) for r in rows]
        db.close()
        return jsonify({'columns': list(columns), 'rows': result, 'count': len(result)})
    except Exception as e:
        db.close()
        return jsonify({'error': str(e)}), 400


if __name__ == '__main__':
    print("Dashboard running at http://localhost:5050")
    print("Press Ctrl+C to stop\n")
    app.run(debug=True, port=5050)
