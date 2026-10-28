"""SQLite persistence for game assets generated through the dedicated PixelLab provider."""
import json, os, sqlite3, time, uuid
from pathlib import Path
BASE = Path(__file__).resolve().parent
DB_PATH = Path(os.getenv('AGENT_FACTORY_DB', str(BASE / 'agent_factory.sqlite3'))).expanduser()

def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB_PATH, timeout=10); c.row_factory = sqlite3.Row
    c.execute('PRAGMA journal_mode=WAL')
    return c

def init_game_asset_db():
    with connect() as c:
        c.execute('''CREATE TABLE IF NOT EXISTS game_assets (id TEXT PRIMARY KEY, name TEXT NOT NULL, prompt TEXT NOT NULL, asset_type TEXT NOT NULL, width INTEGER NOT NULL, height INTEGER NOT NULL, transparent INTEGER NOT NULL, provider TEXT NOT NULL, image_url TEXT NOT NULL, created_at INTEGER NOT NULL, reference_used INTEGER NOT NULL DEFAULT 0)''')
        columns = {row[1] for row in c.execute('PRAGMA table_info(game_assets)').fetchall()}
        if 'reference_used' not in columns:
            c.execute('ALTER TABLE game_assets ADD COLUMN reference_used INTEGER NOT NULL DEFAULT 0')

def save_game_asset(item):
    row = dict(item); row.setdefault('id', str(uuid.uuid4())); row.setdefault('created_at', int(time.time()))
    with connect() as c:
        c.execute('''INSERT INTO game_assets(id,name,prompt,asset_type,width,height,transparent,provider,image_url,created_at,reference_used) VALUES(?,?,?,?,?,?,?,?,?,?,?)''',
          (row['id'], row['name'], row['prompt'], row['asset_type'], row['width'], row['height'], int(row['transparent']), row['provider'], row['image_url'], row['created_at'], int(bool(row.get('reference_used', False)))))
    row['transparent'] = bool(row['transparent'])
    return row

def list_game_assets():
    with connect() as c: rows = c.execute('SELECT * FROM game_assets ORDER BY created_at DESC').fetchall()
    return [{**dict(r), 'transparent': bool(r['transparent']), 'reference_used': bool(r['reference_used'])} for r in rows]

def delete_game_asset(asset_id):
    with connect() as c:
        row = c.execute('SELECT image_url FROM game_assets WHERE id=?', (asset_id,)).fetchone()
        if not row: return False
        c.execute('DELETE FROM game_assets WHERE id=?', (asset_id,))
    return row['image_url']
