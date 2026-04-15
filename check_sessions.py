#!/usr/bin/env python3
import sqlite3

db_path = 'D:/415/tools415/data/relay.db'
conn = sqlite3.connect(db_path)
cur = conn.cursor()

# 查看 sessions 表
cur.execute('SELECT * FROM sessions LIMIT 10')
print('Sessions:')
for row in cur.fetchall():
    print(f'  {row}')

# 查看 agents 表的详细信息
cur.execute('SELECT * FROM agents')
print('\nAgents:')
for row in cur.fetchall():
    print(f'  {row}')

conn.close()
