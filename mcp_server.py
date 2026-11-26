"""
STEP 4: MCP Server - Exposes your SQLite database to Claude.

MCP (Model Context Protocol) lets AI tools like Claude Code connect
to your database and query it directly. Once configured, you can say
"query my sales database" in Claude Code and it will use these tools.

Run with:  python3 mcp_server.py
Or configure it in Claude Code settings (see README section below).
"""

import sqlite3
import json
from mcp.server.fastmcp import FastMCP

# Create the MCP server
mcp = FastMCP("Sales Dashboard DB")

DB_PATH = "demo.db"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@mcp.tool()
def list_tables() -> str:
    """List all tables in the database with their columns."""
    db = get_db()
    tables = db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    result = []
    for t in tables:
        name = t['name']
        cols = db.execute(f"PRAGMA table_info({name})").fetchall()
        col_info = [f"  {c['name']} ({c['type']})" for c in cols]
        result.append(f"{name}:\n" + "\n".join(col_info))
    db.close()
    return "\n\n".join(result)


@mcp.tool()
def run_sql(query: str) -> str:
    """Run a read-only SQL query against the sales database.
    Only SELECT statements are allowed.
    Returns results as JSON.

    Tables available:
    - products (id, name, category, price)
    - customers (id, name, email, city, signup_date)
    - orders (id, customer_id, product_id, quantity, status, order_date)
    """
    if not query.strip().upper().startswith("SELECT"):
        return json.dumps({"error": "Only SELECT queries are allowed"})

    db = get_db()
    try:
        rows = db.execute(query).fetchall()
        result = [dict(r) for r in rows]
        db.close()
        return json.dumps(result, indent=2)
    except Exception as e:
        db.close()
        return json.dumps({"error": str(e)})


@mcp.tool()
def get_summary() -> str:
    """Get a high-level summary of the sales database:
    total revenue, orders, customers, products, and top categories."""
    db = get_db()

    revenue = db.execute('''
        SELECT ROUND(SUM(o.quantity * p.price), 2) as revenue
        FROM orders o JOIN products p ON o.product_id = p.id
        WHERE o.status = 'completed'
    ''').fetchone()['revenue']

    orders = db.execute("SELECT COUNT(*) as n FROM orders").fetchone()['n']
    customers = db.execute("SELECT COUNT(*) as n FROM customers").fetchone()['n']

    top_cats = db.execute('''
        SELECT p.category, ROUND(SUM(o.quantity * p.price), 2) as revenue
        FROM orders o JOIN products p ON o.product_id = p.id
        WHERE o.status = 'completed'
        GROUP BY p.category ORDER BY revenue DESC
    ''').fetchall()

    db.close()
    return json.dumps({
        "total_revenue": revenue,
        "total_orders": orders,
        "total_customers": customers,
        "top_categories": [dict(r) for r in top_cats]
    }, indent=2)


@mcp.tool()
def get_top_products(limit: int = 5) -> str:
    """Get the top selling products by revenue."""
    db = get_db()
    rows = db.execute('''
        SELECT p.name, p.category, SUM(o.quantity) as units_sold,
               ROUND(SUM(o.quantity * p.price), 2) as revenue
        FROM orders o JOIN products p ON o.product_id = p.id
        WHERE o.status = 'completed'
        GROUP BY p.name ORDER BY revenue DESC LIMIT ?
    ''', (limit,)).fetchall()
    db.close()
    return json.dumps([dict(r) for r in rows], indent=2)


@mcp.tool()
def get_top_customers(limit: int = 5) -> str:
    """Get the top customers by total spending."""
    db = get_db()
    rows = db.execute('''
        SELECT c.name, c.city, COUNT(o.id) as order_count,
               ROUND(SUM(o.quantity * p.price), 2) as total_spent
        FROM orders o
        JOIN customers c ON o.customer_id = c.id
        JOIN products p ON o.product_id = p.id
        WHERE o.status = 'completed'
        GROUP BY c.id ORDER BY total_spent DESC LIMIT ?
    ''', (limit,)).fetchall()
    db.close()
    return json.dumps([dict(r) for r in rows], indent=2)


if __name__ == "__main__":
    mcp.run()
