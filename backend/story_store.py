"""Persistent character and story storage for the Storytelling workspace."""
import json, os, sqlite3, time, uuid
from pathlib import Path
BASE = Path(__file__).resolve().parent
DB_PATH = Path(os.getenv('AGENT_FACTORY_DB', str(BASE / 'agent_factory.sqlite3'))).expanduser()

def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    c=sqlite3.connect(DB_PATH, timeout=10); c.row_factory=sqlite3.Row
    c.execute('PRAGMA journal_mode=WAL'); return c

def init_story_db():
    with connect() as c:
        c.execute('''CREATE TABLE IF NOT EXISTS characters (id TEXT PRIMARY KEY, payload TEXT NOT NULL, created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL)''')
        c.execute('''CREATE TABLE IF NOT EXISTS stories (id TEXT PRIMARY KEY, payload TEXT NOT NULL, created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL)''')

def _all(table):
    with connect() as c: rows=c.execute(f'SELECT payload FROM {table} ORDER BY updated_at DESC').fetchall()
    return [json.loads(r['payload']) for r in rows]
def _get(table, ident):
    with connect() as c: row=c.execute(f'SELECT payload FROM {table} WHERE id=?',(ident,)).fetchone()
    return json.loads(row['payload']) if row else None
def _save(table, item):
    now=int(time.time()); item=dict(item); ident=str(item.get('id') or uuid.uuid4()); item['id']=ident
    old=_get(table,ident); item['created_at']=(old or {}).get('created_at',now); item['updated_at']=now
    with connect() as c: c.execute(f'INSERT INTO {table}(id,payload,created_at,updated_at) VALUES(?,?,?,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload, updated_at=excluded.updated_at',(ident,json.dumps(item,ensure_ascii=False),item['created_at'],now))
    return item
def _delete(table, ident):
    with connect() as c: cur=c.execute(f'DELETE FROM {table} WHERE id=?',(ident,)); return cur.rowcount>0

def list_characters(): return _all('characters')
def get_character(i): return _get('characters',i)
def save_character(x): return _save('characters',x)
def delete_character(i): return _delete('characters',i)
def list_stories(): return _all('stories')
def get_story(i): return _get('stories',i)
def save_story(x): return _save('stories',x)
def delete_story(i): return _delete('stories',i)
