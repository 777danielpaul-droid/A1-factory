import React, { useCallback, useEffect, useState } from 'react';

const formatBytes = (bytes) => {
  if (!Number.isFinite(bytes)) return '—';
  if (bytes < 1024) return `${bytes} B`;
  const units = ['KB', 'MB', 'GB', 'TB'];
  let value = bytes / 1024;
  let unit = 0;
  while (value >= 1024 && unit < units.length - 1) { value /= 1024; unit += 1; }
  return `${value.toFixed(value >= 100 ? 0 : 1)} ${units[unit]}`;
};

export default function MediaLibraryWorkspace({ apiOrigin }) {
  const [items, setItems] = useState([]);
  const [totalBytes, setTotalBytes] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [busyFile, setBusyFile] = useState('');
  const [filter, setFilter] = useState('all');

  const refresh = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const response = await fetch(`${apiOrigin}/api/media/library`);
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Medien konnten nicht geladen werden.');
      setItems(data.items || []);
      setTotalBytes(data.total_bytes || 0);
    } catch (e) {
      setError(e.message || 'Backend nicht erreichbar.');
    } finally { setLoading(false); }
  }, [apiOrigin]);

  useEffect(() => { refresh(); }, [refresh]);

  const remove = async (item) => {
    if (!window.confirm(`„${item.filename}“ wirklich dauerhaft löschen? Diese Aktion kann nicht rückgängig gemacht werden.`)) return;
    setBusyFile(item.filename);
    setError('');
    try {
      const response = await fetch(`${apiOrigin}/api/media/library/${encodeURIComponent(item.filename)}`, { method: 'DELETE' });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Datei konnte nicht gelöscht werden.');
      setItems(current => current.filter(file => file.filename !== item.filename));
      setTotalBytes(size => Math.max(0, size - item.bytes));
    } catch (e) {
      setError(e.message || 'Datei konnte nicht gelöscht werden.');
    } finally { setBusyFile(''); }
  };

  const filtered = items.filter(item => filter === 'all' || item.kind === filter);
  return (
    <main className="mx-auto max-w-6xl space-y-5">
      <section className="rounded-2xl border border-slate-800 bg-slate-950 p-6 text-white shadow-xl">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs font-bold uppercase tracking-[.22em] text-violet-300">A1 Factory · Archiv</p>
            <h2 className="mt-2 text-3xl font-black tracking-tight">Medienbibliothek</h2>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-300">Alle erkannten Bilder, Videos und Audiodateien aus dem lokalen Ausgabeordner ansehen, abspielen, herunterladen oder löschen.</p>
          </div>
          <button type="button" onClick={refresh} disabled={loading} className="rounded-lg border border-slate-600 px-4 py-2 text-sm font-semibold hover:bg-slate-800 disabled:opacity-50">{loading ? 'Lädt…' : '↻ Aktualisieren'}</button>
        </div>
        <div className="mt-5 grid gap-3 sm:grid-cols-3">
          <div className="rounded-xl border border-slate-700 bg-slate-900 p-3"><p className="text-xs text-slate-400">Dateien</p><p className="mt-1 text-2xl font-bold">{items.length}</p></div>
          <div className="rounded-xl border border-slate-700 bg-slate-900 p-3"><p className="text-xs text-slate-400">Gesamter Speicher</p><p className="mt-1 text-2xl font-bold">{formatBytes(totalBytes)}</p></div>
          <div className="rounded-xl border border-slate-700 bg-slate-900 p-3"><p className="text-xs text-slate-400">Speicherort</p><p className="mt-1 text-sm font-semibold">backend/output/assets</p></div>
        </div>
      </section>

      {error && <p role="alert" className="rounded-lg border border-red-300 bg-red-50 p-3 text-sm text-red-800">{error}</p>}
      <section className="space-y-4 rounded-2xl border border-stone-300 bg-white p-4 md:p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div><h3 className="text-lg font-bold text-stone-900">Deine generierten Medien</h3><p className="text-sm text-stone-600">Gelöschte Dateien werden dauerhaft vom lokalen Backend entfernt.</p></div>
          <div className="flex flex-wrap gap-2" aria-label="Medien filtern">
            {[['all', 'Alle'], ['image', 'Bilder'], ['video', 'Videos'], ['audio', 'Audio']].map(([value, label]) => <button key={value} type="button" onClick={() => setFilter(value)} className={`rounded-full border px-3 py-1.5 text-sm font-semibold ${filter === value ? 'border-violet-700 bg-violet-700 text-white' : 'border-stone-300 bg-white text-stone-700 hover:bg-stone-100'}`}>{label}</button>)}
          </div>
        </div>
        {loading ? <p className="py-10 text-center text-sm text-stone-500">Medien werden geladen…</p> : filtered.length === 0 ? <div className="rounded-xl border border-dashed border-stone-300 px-4 py-12 text-center"><p className="font-semibold text-stone-800">Keine Medien gefunden</p><p className="mt-1 text-sm text-stone-500">Generierte Dateien erscheinen hier automatisch, sobald sie im Ausgabeordner gespeichert wurden.</p></div> :
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {filtered.map(item => <article key={item.filename} className="overflow-hidden rounded-xl border border-stone-200 bg-stone-50">
              <div className="flex h-48 items-center justify-center overflow-hidden bg-stone-900">
                {item.kind === 'image' ? <img src={`${apiOrigin}${item.url}`} alt={item.filename} loading="lazy" className="h-full w-full object-contain" /> : item.kind === 'video' ? <video controls preload="metadata" className="max-h-full max-w-full" src={`${apiOrigin}${item.url}`}>Videowiedergabe nicht unterstützt.</video> : <audio controls preload="metadata" className="w-[90%]" src={`${apiOrigin}${item.url}`}>Audiowiedergabe nicht unterstützt.</audio>}
              </div>
              <div className="space-y-3 p-3">
                <div className="min-w-0"><p className="truncate text-sm font-semibold text-stone-900" title={item.filename}>{item.filename}</p><p className="mt-1 text-xs text-stone-500">{item.kind === 'image' ? 'Bild' : item.kind === 'video' ? 'Video' : 'Audio'} · {formatBytes(item.bytes)} · {new Date(item.modified_at * 1000).toLocaleString('de-DE')}</p></div>
                <div className="flex gap-2"><a href={`${apiOrigin}${item.url}`} target="_blank" rel="noreferrer" className="flex-1 rounded-lg border border-stone-300 bg-white px-3 py-2 text-center text-sm font-semibold text-stone-800 hover:bg-stone-100">Öffnen</a><a href={`${apiOrigin}${item.url}`} download={item.filename} className="flex-1 rounded-lg border border-stone-300 bg-white px-3 py-2 text-center text-sm font-semibold text-stone-800 hover:bg-stone-100">Speichern</a><button type="button" onClick={() => remove(item)} disabled={busyFile === item.filename} className="rounded-lg border border-red-300 bg-red-50 px-3 py-2 text-sm font-semibold text-red-800 hover:bg-red-100 disabled:opacity-50" aria-label={`${item.filename} löschen`}>{busyFile === item.filename ? '…' : 'Löschen'}</button></div>
              </div>
            </article>)}
          </div>}
      </section>
      <p className="text-xs text-stone-500">Hinweis: Diese Bibliothek verwaltet Medien-Dateien im lokalen Ausgabeordner, nicht Produktdatensätze, die in anderen Werkstätten gespeichert sind. Die Löschaktion entfernt die Datei dauerhaft.</p>
    </main>
  );
}
