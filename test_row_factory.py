"""Test row_factory directly."""

import sqlite3
from sqlalchemy import create_engine, pool

# Test 1: Direct sqlite3 connection
print("Test 1: Direct sqlite3 connection")
conn1 = sqlite3.connect("test_direct.db")
conn1.row_factory = sqlite3.Row
conn1.execute("CREATE TABLE IF NOT EXISTS test (id INTEGER, name TEXT)")
conn1.execute("INSERT INTO test VALUES (1, 'Alice')")
conn1.commit()

cur1 = conn1.cursor()
cur1.execute("SELECT name FROM test WHERE id=1")
row1 = cur1.fetchone()
print(f"  Row type: {type(row1)}")
print(f"  Row value: {row1}")
print(f"  Row factory: {conn1.row_factory}")
try:
    result = dict(row1)
    print(f"  dict(row) works: {result}")
except Exception as e:
    print(f"  dict(row) failed: {e}")

conn1.close()

# Test 2: SQLAlchemy raw_connection
print("\nTest 2: SQLAlchemy raw_connection")
engine = create_engine(
    "sqlite:///test_pooled.db",
    poolclass=pool.QueuePool,
    pool_size=5,
    connect_args={"check_same_thread": False}
)

conn2 = engine.raw_connection()
print(f"  Connection type: {type(conn2)}")
conn2.row_factory = sqlite3.Row
conn2.execute("CREATE TABLE IF NOT EXISTS test (id INTEGER, name TEXT)")
conn2.execute("INSERT INTO test VALUES (1, 'Bob')")
conn2.commit()

cur2 = conn2.cursor()
cur2.execute("SELECT name FROM test WHERE id=1")
row2 = cur2.fetchone()
print(f"  Row type: {type(row2)}")
print(f"  Row value: {row2}")
print(f"  Row factory: {conn2.row_factory}")
try:
    result = dict(row2)
    print(f"  dict(row) works: {result}")
except Exception as e:
    print(f"  dict(row) failed: {e}")

conn2.close()
engine.dispose()

# Cleanup
import os
for db in ["test_direct.db", "test_pooled.db"]:
    if os.path.exists(db):
        os.remove(db)

print("\nDone!")
