"""
STEP 1: Create and populate a SQLite database with sample data.

SQLite is a SQL database stored in a single file - no server needed.
Run this first:  python3 setup_database.py
"""

import sqlite3
import random
from datetime import datetime, timedelta

conn = sqlite3.connect('demo.db')
cursor = conn.cursor()

# --- CREATE TABLES ---
cursor.execute('''
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        price REAL NOT NULL
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL,
        city TEXT NOT NULL,
        signup_date TEXT NOT NULL
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL,
        status TEXT NOT NULL DEFAULT 'completed',
        order_date TEXT NOT NULL,
        FOREIGN KEY (customer_id) REFERENCES customers(id),
        FOREIGN KEY (product_id) REFERENCES products(id)
    )
''')

print("Tables created!")

# --- INSERT SAMPLE DATA ---
products = [
    ('Wireless Headphones', 'Electronics', 79.99),
    ('USB-C Hub', 'Electronics', 49.99),
    ('Mechanical Keyboard', 'Electronics', 129.99),
    ('Standing Desk Mat', 'Office', 39.99),
    ('Monitor Light Bar', 'Office', 59.99),
    ('Webcam HD', 'Electronics', 89.99),
    ('Desk Organizer', 'Office', 24.99),
    ('Laptop Stand', 'Office', 44.99),
    ('Noise Machine', 'Wellness', 34.99),
    ('Blue Light Glasses', 'Wellness', 29.99),
    ('Ergonomic Mouse', 'Electronics', 69.99),
    ('Cable Management Kit', 'Office', 19.99),
]

cities = ['New York', 'San Francisco', 'Chicago', 'Austin', 'Seattle',
          'Denver', 'Boston', 'Portland', 'Miami', 'Los Angeles']

first_names = ['Alice', 'Bob', 'Carol', 'David', 'Eva', 'Frank', 'Grace',
               'Henry', 'Iris', 'Jack', 'Karen', 'Leo', 'Mia', 'Noah', 'Olivia']
last_names = ['Johnson', 'Smith', 'Williams', 'Brown', 'Martinez', 'Lee',
              'Kim', 'Davis', 'Garcia', 'Wilson', 'Chen', 'Taylor']

random.seed(42)

# Clear existing data
cursor.execute('DELETE FROM orders')
cursor.execute('DELETE FROM customers')
cursor.execute('DELETE FROM products')

# Insert products
cursor.executemany('INSERT INTO products (name, category, price) VALUES (?, ?, ?)', products)
print(f"Inserted {len(products)} products")

# Generate 30 customers
customers = []
today = datetime.now()
for i in range(30):
    name = f"{random.choice(first_names)} {random.choice(last_names)}"
    email = name.lower().replace(' ', '.') + f"{i}@example.com"
    city = random.choice(cities)
    signup = (today - timedelta(days=random.randint(30, 365))).strftime('%Y-%m-%d')
    customers.append((name, email, city, signup))

cursor.executemany('INSERT INTO customers (name, email, city, signup_date) VALUES (?, ?, ?, ?)', customers)
print(f"Inserted {len(customers)} customers")

# Generate 500 orders over the past 180 days
statuses = ['completed', 'completed', 'completed', 'completed', 'pending', 'shipped', 'refunded']
orders = []
for _ in range(500):
    customer_id = random.randint(1, len(customers))
    product_id = random.randint(1, len(products))
    quantity = random.randint(1, 5)
    days_ago = random.randint(0, 180)
    order_date = (today - timedelta(days=days_ago)).strftime('%Y-%m-%d')
    status = random.choice(statuses)
    orders.append((customer_id, product_id, quantity, status, order_date))

cursor.executemany(
    'INSERT INTO orders (customer_id, product_id, quantity, status, order_date) VALUES (?, ?, ?, ?, ?)',
    orders
)
print(f"Inserted {len(orders)} orders")

conn.commit()

# Verify
cursor.execute('''
    SELECT p.name, SUM(o.quantity) as total_sold, ROUND(SUM(o.quantity * p.price), 2) as revenue
    FROM orders o JOIN products p ON o.product_id = p.id
    WHERE o.status = 'completed'
    GROUP BY p.name ORDER BY revenue DESC
''')

print("\n--- Top products by revenue ---")
for row in cursor.fetchall():
    print(f"  {row[0]}: {row[1]} sold, ${row[2]:,.2f}")

conn.close()
print("\nDatabase 'demo.db' is ready!")
