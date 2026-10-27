import React, { useEffect, useState } from 'react';

const field = 'w-full bg-white border border-stone-400 rounded px-3 py-2 text-sm focus:outline focus:outline-2 focus:outline-[#E8590C]';
const types = [['sprite', 'Sprite / Objekt'], ['character', 'Charakter-Konzept'], ['tile', 'Tile / Umgebung'], ['ui', 'Game-UI-Element'], ['background', 'Hintergrund']];
const readReference = file => new Promise((resolve, reject) => { if (!file) return resolve(''); if (!/^image\/(png|jpeg|webp)$/.test(file.type)) return reject(new Error('Bitte PNG, JPEG oder WebP auswählen.')); if (file.size > 6 * 1024 * 1024) return reject(new Error('Das Vorlagenbild darf maximal 6 MB groß sein.')); const reader = new FileReader(); reader.onload = () => { const img = new Image(); img.onload = () => { const scale = Math.min(1, 1024 / Math.max(img.width, img.height)); const canvas = document.createElement('canvas'); canvas.width = Math.max(1, Math.round(img.width * scale)); canvas.height = Math.max(1, Math.round(img.height * scale)); canvas.getContext('2d').drawImage(img, 0, 0, canvas.width, canvas.height); resolve(canvas.toDataURL('image/jpeg', 0.88)); }; img.onerror = () => reject(new Error('Vorlagenbild konnte nicht gelesen werden.')); img.src = reader.result; }; reader.onerror = () => reject(new Error('Vorlagenbild konnte nicht gelesen werden.')); reader.readAsDataURL(file); });

export default function GameAssetsWorkspace({ apiOrigin }) {
  const [apiKey, setApiKey] = useState('');
  const [name, setName] = useState('Mein Pixel-Art-Asset');
  const [prompt, setPrompt] = useState('A small fantasy forest slime monster, readable silhouette, limited color palette, classic 16-bit pixel art');
  const [assetType, setAssetType] = useState('sprite');
  const [width, setWidth] = useState(128);
  const [height, setHeight] = useState(128);
  const [transparent, setTransparent] = useState(true);
  const [assets, setAssets] = useState([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [reference, setReference] = useState(null);

  const load = async () => {
    try {
      const r = await fetch(`${apiOrigin}/api/game-assets`);
      const j = await r.json();
      if (!r.ok) throw new Error(j.detail || 'Game-Assets konnten nicht geladen werden.');
      setAssets(j.assets || []);
    } catch (e) { setError(e.message); }
  };
  useEffect(() => { load(); }, []);

  const generate = async () => {
    setError(''); setMessage(''); setBusy(true);
    try {
      const r = await fetch(`${apiOrigin}/api/game-assets/generate`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ api_key: apiKey, name, prompt, asset_type: assetType, width: Number(width), height: Number(height), transparent, reference_data_url: reference?.dataUrl || '' })
      });
      const j = await r.json();
      if (!r.ok) throw new Error(j.detail || 'PixelLab-Generierung fehlgeschlagen.');
      setAssets(current => [j, ...current.filter(a => a.id !== j.id)]);
      setMessage('Asset generiert und in SQLite gespeichert.');
    } catch (e) { setError(e.message); }
    finally { setBusy(false); }
  };

  const remove = async id => {
    if (!confirm('Dieses Game-Asset samt gespeicherter Datei löschen?')) return;
    try {
      const r = await fetch(`${apiOrigin}/api/game-assets/${encodeURIComponent(id)}`, { method: 'DELETE' });
      const j = await r.json();
      if (!r.ok) throw new Error(j.detail || 'Löschen fehlgeschlagen.');
      setAssets(current => current.filter(a => a.id !== id));
    } catch (e) { setError(e.message); }
  };

  return <div className="space-y-6">
    <header><h2 className="display text-2xl font-bold">Game Assets · PixelLab</h2><p className="text-sm text-stone-600 mt-1">PixelLab ist nur für Pixel-Art-Assets in diesem Bereich zuständig. Anime-Porträts und Webtoon-Panels bleiben beim bisherigen Bildgenerator.</p></header>
    {error && <p role="alert" className="border border-red-300 bg-red-50 text-red-800 rounded p-3 text-sm">{error}</p>}
    {message && <p role="status" className="border border-emerald-300 bg-emerald-50 text-emerald-800 rounded p-3 text-sm">{message}</p>}
    <section className="bg-white border border-stone-300 rounded-lg p-4 space-y-4">
      <h3 className="display text-lg font-bold">Neues Pixel-Art-Asset</h3>
      <label className="block text-sm">PixelLab API-Key
        <input type="password" autoComplete="off" className={`${field} mt-1`} value={apiKey} onChange={e => setApiKey(e.target.value)} placeholder="Token aus deinen PixelLab-Kontoeinstellungen" />
      </label>
      <p className="text-xs text-stone-600">Der Key wird nur für diese Anfrage an das Backend gesendet und nicht in SQLite gespeichert. In diesem Formular bleibt er nur im aktuellen React-Zustand und wird nicht in localStorage abgelegt.</p>
      <label className="block text-sm">Asset-Name<input className={`${field} mt-1`} value={name} maxLength={160} onChange={e => setName(e.target.value)} /></label>
      <label className="block text-sm">Asset-Art<select className={`${field} mt-1`} value={assetType} onChange={e => setAssetType(e.target.value)}>{types.map(([v, label]) => <option key={v} value={v}>{label}</option>)}</select></label>
      <label className="block text-sm">Basisbild / Vorlage (optional)<input type="file" accept="image/png,image/jpeg,image/webp" className="block mt-1 text-xs" disabled={busy} onChange={async e => { const file=e.target.files?.[0]; e.target.value=''; if (!file) return; try { setReference({name:file.name,dataUrl:await readReference(file)}); setError(''); } catch(err) { setError(err.message); } }} /></label>
      {reference && <div className="flex items-center gap-3 border rounded p-2"><img src={reference.dataUrl} alt="Pixel-Art-Vorlage" className="w-16 h-16 object-contain bg-stone-100 rounded"/><div className="min-w-0 flex-1 text-xs"><b>Vorlage ausgewählt</b><p className="truncate">{reference.name}</p></div><button type="button" className="text-xs underline" onClick={()=>setReference(null)} disabled={busy}>Entfernen</button></div>}
      <p className="text-xs text-stone-600">Mit Vorlage wird PixelLabs Image-to-Pixel-Art-Endpunkt verwendet, damit die Komposition als Basis dient.</p>
      <label className="block text-sm">Beschreibung / Prompt<textarea className={`${field} mt-1`} rows={4} maxLength={2000} value={prompt} onChange={e => setPrompt(e.target.value)} /></label>
      <div className="grid grid-cols-2 gap-3">
        <label className="block text-sm">Breite (px)<select className={`${field} mt-1`} value={width} onChange={e => setWidth(Number(e.target.value))}>{[16,32,64,128,256,512,768].map(n => <option key={n} value={n}>{n}px</option>)}</select></label>
        <label className="block text-sm">Höhe (px)<select className={`${field} mt-1`} value={height} onChange={e => setHeight(Number(e.target.value))}>{[16,32,64,128,256,512,768].map(n => <option key={n} value={n}>{n}px</option>)}</select></label>
      </div>
      <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={transparent} onChange={e => setTransparent(e.target.checked)} /> Hintergrund entfernen / transparent</label>
      <button disabled={busy || !apiKey.trim() || !name.trim() || !prompt.trim()} onClick={generate} className="w-full bg-[#E8590C] text-white rounded px-4 py-3 font-bold disabled:opacity-50">{busy ? 'PixelLab generiert – das kann etwas dauern…' : 'Pixel-Art generieren'}</button>
      <p className="text-xs text-stone-600">Die Integration verwendet PixelLabs schnellen Endpunkt für einzelne Bilder. Die tatsächlichen Kosten und verfügbaren Credits hängen von deinem PixelLab-Konto ab; die Generierung startet erst, wenn du auf den Button klickst.</p>
    </section>
    <section className="space-y-3"><div className="flex items-center justify-between gap-3"><h3 className="display text-xl font-bold">Gespeicherte Game-Assets ({assets.length})</h3><button className="text-sm underline" onClick={load}>Aktualisieren</button></div>
      {!assets.length && <p className="text-sm text-stone-500">Noch keine PixelLab-Assets gespeichert.</p>}
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">{assets.map(a => <article key={a.id} className="bg-white border border-stone-300 rounded-lg p-3">
        <img src={`${apiOrigin}${a.image_url}`} alt={a.name} className="w-full aspect-square object-contain image-rendering-pixelated bg-stone-100 rounded" style={{ imageRendering: 'pixelated' }} />
        <div className="flex items-start justify-between gap-2 mt-3"><div><h4 className="font-bold text-sm">{a.name}</h4><p className="text-xs text-stone-600">PixelLab · {a.width}×{a.height} · {types.find(([v]) => v === a.asset_type)?.[1] || a.asset_type}{a.reference_used ? ' · Vorlage verwendet' : ''}</p></div><button className="text-xs text-red-700 underline" onClick={() => remove(a.id)}>Löschen</button></div>
        <details className="mt-2"><summary className="cursor-pointer text-xs underline">Prompt anzeigen</summary><p className="text-xs whitespace-pre-wrap mt-2">{a.prompt}</p></details>
      </article>)}</div>
    </section>
  </div>;
}
