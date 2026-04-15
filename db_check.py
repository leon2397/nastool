#!/usr/bin/env python3
import sqlite3

db_path = 'D:/415/tools415/data/relay.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# List all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print('Tables:', [t[0] for t in tables])

# Show agents
if ('agents',) in tables:
    cursor.execute('SELECT * FROM agents')
    rows = cursor.fetchall()
    print(f'\nAgents ({len(rows)}):')
    for row in rows:
        print(f'  {row}')

# Show commands
if ('commands',) in tables:
    cursor.execute('SELECT * FROM commands LIMIT 5')
    rows = cursor.fetchall()
    print(f'\nCommands:')
    for row in rows:
        print(f'  {row}')

conn.close()
