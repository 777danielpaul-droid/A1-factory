import React, { useState, useEffect, useRef, useCallback } from 'react';
import StorytellingWorkspace from './StorytellingWorkspace.jsx';
import GameAssetsWorkspace from './GameAssetsWorkspace.jsx';
import AudioVideoWorkspace from './AudioVideoWorkspace.jsx';
import MediaLibraryWorkspace from './MediaLibraryWorkspace.jsx';
import GlobeBackground from './GlobeBackground.jsx';

const API = import.meta.env.VITE_API_URL || 'localhost:8000';
const API_ORIGIN = `http://${API}`;
const PROVIDERS = [
  ['groq', 'Groq'], ['openai', 'OpenAI'], ['anthropic', 'Anthropic'],
  ['grok', 'xAI Grok'], ['openrouter', 'OpenRouter'], ['zai', 'Z.ai (GLM)'],
  ['huggingface', 'Hugging Face'], ['custom', 'Eigener Anbieter (OpenAI-kompatibel)'],
];
const STATIONS = {
  scout: { name: 'Scout', job: 'Findet die Produktidee' },
  designer: { name: 'Designer', job: 'Erzeugt das Motiv' },
  publisher: { name: 'Publisher', job: 'Schreibt und legt den Entwurf an' },
  merch: { name: 'Merch-Designer', job: 'Front-Logo und Backprint' },
  brand: { name: 'Brand-Designer', job: 'Logos, Farben, Schriften, Muster' },
  mockup: { name: 'Mockup-Bot', job: 'Legt Designs auf Produkte' },
  thumb: { name: 'Thumbnail-Designer', job: 'Hintergrund, Charakter, Text' },
  stream: { name: 'Streamer-Designer', job: 'Szenen, Overlay, Panels, Alerts' },
  banner: { name: 'Banner-Designer', job: 'Banner im gleichen Look' },
  shopify: { name: 'Shopify', job: '' },
};
const TABS = { factory: ['scout', 'designer', 'publisher'], studio: ['merch', 'brand', 'mockup'], content: ['thumb', 'stream', 'banner'] };
const CONTENT_MODULES = [['thumbnails', 'Thumbnails (Hintergrund, Charakter, knackiger Text)'], ['streamer', 'Streamer-Paket (Szenen, Overlay, Chat-Box, Panels, Alerts)'], ['banners', 'Banner und Header (einheitlicher Look)']];
const FORMAT_LIST = [['yt', 'YouTube 16:9'], ['square', 'Quadrat 1:1'], ['story', 'Hochkant 9:16']];
const BANNER_LIST = [['youtube', 'YouTube'], ['x', 'X/Twitter'], ['discord', 'Discord'], ['linkedin', 'LinkedIn']];
const MODULES = [['merch', 'Merch-Designs (Front-Logo + Backprint)'], ['brand', 'Brand-Kit (Logos, Farben, Schriften, Muster)'], ['mockups', 'Mockups (T-Shirt, Tasse, Handyhülle, Poster)']];
const STATE = {
  idle: { dot: 'bg-stone-400', text: 'Wartet', card: 'border-stone-400 bg-[#EFEDE7]' },
  working: { dot: 'bg-[#E8590C] animate-pulse', text: 'Arbeitet', card: 'border-[#E8590C] bg-white' },
  done: { dot: 'bg-emerald-700', text: 'Fertig', card: 'border-emerald-700 bg-white' },
  error: { dot: 'bg-red-700', text: 'Fehler', card: 'border-red-700 bg-white' },
};
const ETSY_FIELDS = [
  ['api_key', 'Etsy API-Keystring'], ['shop_id', 'Shop-ID'], ['taxonomy_id', 'Kategorie-ID (Taxonomy)'],
  ['access_token', 'Access-Token'], ['refresh_token', 'Refresh-Token'],
];
const SHOPIFY_FIELDS = [
  ['shop', 'Shop-Adresse (z. B. mein-shop.myshopify.com)', 'text'], ['access_token', 'Admin-API-Token (shpat_…), falls vorhanden', 'password'],
  ['client_id', 'oder Client-ID (Dev Dashboard)', 'text'], ['client_secret', 'und Client-Secret', 'password'],
  ['api_version', 'API-Version (leer = 2026-04)', 'text'],
];
const field = 'w-full bg-white border border-stone-400 rounded px-3 py-2 text-sm focus:outline focus:outline-2 focus:outline-[#E8590C]';
const STORE = 'agent-factory.byok.v1';
const EMPTY = { llm: {}, imageProvider: 'pollinations', img: {}, etsy: {}, shopify: {} };
const IMG2IMG = ['gemini', 'openai', 'local'];
const shrinkImage = (file) => new Promise((resolve, reject) => {
  const url = URL.createObjectURL(file), img = new Image();
  img.onload = () => {
    const k = Math.min(1, 1024 / Math.max(img.width, img.height));
    const cv = document.createElement('canvas');
    cv.width = Math.round(img.width * k); cv.height = Math.round(img.height * k);
    const ctx = cv.getContext('2d');
    ctx.fillStyle = '#fff'; ctx.fillRect(0, 0, cv.width, cv.height);
    ctx.drawImage(img, 0, 0, cv.width, cv.height);
    URL.revokeObjectURL(url);
    resolve(cv.toDataURL('image/jpeg', 0.88));
  };
  img.onerror = () => { URL.revokeObjectURL(url); reject(new Error('Bild konnte nicht gelesen werden')); };
  img.src = url;
});
const K = (label = 'API-Key', required = true) => ['key', label, 'password', required];
const IMAGE_PROVIDERS = {
  placeholder: { label: 'Testmodus: Platzhalter-Bild (kostenlos, ohne Key)', fields: [],
    note: 'Erzeugt lokal ein einfaches Bild mit deinem Prompt. Gut, um den ganzen Ablauf inklusive Etsy zu testen. Kein echtes Motiv, nicht zum Verkaufen.' },
  pollinations: { label: 'Pollinations (kostenlos, ohne Key)', fields: [K('Pollinations-Key (optional, gegen die Drosselung)', false)],
    note: 'Ohne Konto nutzbar, aber anonym gedrosselt (zuletzt ein Bild alle 45 Sekunden) und manchmal überlastet. Die App wartet dann automatisch, ein Lauf dauert länger. Bilder können ein Wasserzeichen tragen. Prüfe die Nutzungsrechte, bevor du verkaufst.' },
  cloudflare: { label: 'Cloudflare Workers AI (Gratis-Tageskontingent)', fields: [['account_id', 'Account-ID', 'text', true], K('API-Token')],
    note: 'Laut Cloudflare gibt es ein kostenloses Tageskontingent (10.000 Neurons pro Tag, nach Angaben Dritter reicht das für grob 170 Bilder in 1024 Pixeln). Account-ID und API-Token (mit Workers-AI-Berechtigung) findest du im Cloudflare-Dashboard unter Workers AI, "Use REST API". Ist das Kontingent leer, kommt ein Fehler bis zum nächsten Tag.' },
  huggingface: { label: 'Hugging Face (Gratis-Guthaben)', fields: [K('Hugging-Face-Token'), ['model', 'Modell (leer = FLUX.1-schnell)', 'text', false]],
    note: 'Läuft über das Guthaben deines Hugging-Face-Kontos. Der Token braucht die Berechtigung für Inference Providers. Du kannst denselben Token wie beim Text-Anbieter nehmen.' },
  gemini: { label: 'Google Gemini (Gratis-Kontingent unsicher)', fields: [K('Gemini-API-Key'), ['model', 'Modell (leer = gemini-2.5-flash-image)', 'text', false]],
    note: 'Das Gratis-Kontingent für Bildmodelle ist unsicher und bei manchen Konten 0. Kommt Fehler 429, brauchst du einen bezahlten Tarif.' },
  together: { label: 'Together AI (meist kostenpflichtig)', fields: [K('Together-Key'), ['model', 'Modell (leer = black-forest-labs/FLUX.1-schnell)', 'text', false]],
    note: 'Das kostenlose FLUX-Modell war ein zeitlich begrenztes Angebot von 2024. Heute ist es in der Regel kostenpflichtig. Trag den Modellnamen selbst ein, falls es ein Gratis-Modell gibt.' },
  openai: { label: 'OpenAI Bilder (kostenpflichtig)', fields: [K('OpenAI-Key'), ['model', 'Modell (leer = gpt-image-1)', 'text', false]],
    note: 'Kostenpflichtig. Für gpt-image-1 kann OpenAI eine Verifizierung deiner Organisation verlangen.' },
  stability: { label: 'Stability AI (kostenpflichtig)', fields: [K('Stability-Key')],
    note: 'Kostenpflichtig, mit Guthaben auf platform.stability.ai.' },
  local: { label: 'Lokal: Stable Diffusion WebUI (kostenlos, eigene Grafikkarte)', fields: [['base_url', 'Adresse (z. B. http://127.0.0.1:7860)', 'text', true]],
    note: 'Starte die AUTOMATIC1111-WebUI mit der Startoption --api. Kostet nichts, braucht aber eine passende Grafikkarte und Geduld.' },
};
const loadCfg = () => {
  try {
    const c = { ...EMPTY, ...JSON.parse(localStorage.getItem(STORE) || '{}') };
    c.img = { ...(c.img || {}) };  // alte Felder übernehmen
    if (c.stability && !c.img.stability) c.img.stability = { key: c.stability };
    if (c.pollinations && !c.img.pollinations) c.img.pollinations = { key: c.pollinations };
    return c;
  } catch { return EMPTY; }
};
const fresh = () => Object.fromEntries(Object.keys(STATIONS).map(k => [k, { status: 'idle', message: '' }]));

function ModelPicker({ provider, v, onChange, field, required }) {
  const [models, setModels] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [q, setQ] = useState('');
  const [onlyFree, setOnlyFree] = useState(false);

  const load = async () => {
    setLoading(true); setError('');
    try {
      const r = await fetch(`http://${API}/models`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider, api_key: v.key || '', base_url: v.base_url || '' }),
      });
      const j = await r.json();
      if (!r.ok) throw new Error(j.detail || 'Unbekannter Fehler');
      setModels(j.models);
    } catch (e) {
      setError(e instanceof TypeError ? 'Backend nicht erreichbar. Läuft es?' : String(e.message || e));
    } finally { setLoading(false); }
  };

  const hasFree = !!models?.some(m => m.free);
  const list = (models || []).filter(m => (!onlyFree || m.free) && `${m.id} ${m.name}`.toLowerCase().includes(q.trim().toLowerCase()));

  return (
    <div>
      <label className="block">{required ? 'Modellname (Pflicht)' : 'Modellname (leer = Standard)'}
        <div className="flex gap-2 mt-1">
          <input className={field} value={v.model || ''} onChange={e => onChange(e.target.value)} />
          <button type="button" onClick={load} disabled={loading}
            className="shrink-0 border border-stone-500 rounded px-3 text-xs hover:bg-stone-100 disabled:opacity-50">
            {loading ? 'Lädt…' : models ? 'Neu laden' : 'Modelle laden'}
          </button>
        </div>
      </label>
      {error && <p className="text-xs text-red-700 mt-1">{error}</p>}
      {models && (
        <div className="mt-2 border border-stone-300 rounded">
          <div className="flex flex-wrap items-center gap-3 p-2 border-b border-stone-300">
            <input value={q} onChange={e => setQ(e.target.value)} placeholder="Suchen, z. B. free, llama, gpt" aria-label="Modelle durchsuchen"
              className="flex-1 min-w-[160px] bg-white border border-stone-400 rounded px-2 py-1 text-xs focus:outline focus:outline-2 focus:outline-[#E8590C]" />
            {hasFree && (
              <label className="flex items-center gap-1 text-xs"><input type="checkbox" checked={onlyFree} onChange={e => setOnlyFree(e.target.checked)} />Nur kostenlose</label>
            )}
            <span className="text-xs text-stone-500">{list.length} von {models.length}</span>
          </div>
          <ul className="max-h-48 overflow-y-auto text-xs">
            {list.slice(0, 300).map(m => (
              <li key={m.id}>
                <button type="button" onClick={() => onChange(m.id)}
                  className={`w-full text-left px-2 py-1.5 flex justify-between gap-2 hover:bg-stone-100 ${v.model === m.id ? 'bg-[#FFF4EC] font-medium' : ''}`}>
                  <span className="break-all">{m.id}</span>
                  {m.free && <span className="shrink-0 text-emerald-800">kostenlos</span>}
                </button>
              </li>
            ))}
            {list.length === 0 && <li className="px-2 py-2 text-stone-500">Keine Treffer.</li>}
          </ul>
          {!hasFree && <p className="text-xs text-stone-500 p-2 border-t border-stone-300">Ob ein Modell kostenlos ist, zeigt nur OpenRouter an. Bei den anderen Anbietern hängt es von deinem Konto ab (zum Beispiel gibt es bei Groq ein Gratis-Kontingent mit Limits).</p>}
        </div>
      )}
    </div>
  );
}

function Pic({ src, label, api, checker }) {
  return (
    <a href={`http://${api}${src}`} target="_blank" rel="noreferrer" className="block" aria-label={`${label} groß öffnen`}>
      <img src={`http://${api}${src}`} alt={label} className={`w-full aspect-square object-contain rounded border border-stone-300 ${checker ? 'checker' : 'bg-stone-100'}`} />
      <span className="text-xs text-stone-600">{label}</span>
    </a>
  );
}

function Block({ title, children }) {
  return <section className="border-t border-stone-300 pt-3"><h3 className="display font-bold mb-2">{title}</h3>{children}</section>;
}

export function StudioResults({ studios, selectedId, onSelect, api }) {
  const s = studios.find(x => x.id === selectedId);
  return (
    <div>
      <h2 className="display font-bold mb-3">Studio-Ergebnisse ({studios.length})</h2>
      {studios.length > 1 && (
        <select className="w-full border border-stone-400 rounded px-2 py-1 text-xs mb-3" value={selectedId} onChange={e => onSelect(Number(e.target.value))} aria-label="Ergebnis wählen">
          {studios.map(x => <option key={x.id} value={x.id}>{x.niche} ({new Date(x.id).toLocaleTimeString('de-DE')})</option>)}
        </select>
      )}
      {!s ? <p className="text-sm text-stone-500">Hier erscheinen Merch-Designs, das Brand-Kit und die Mockups.</p> : (
        <div className="space-y-4 text-sm">
          <p className="font-medium">{s.niche}</p>
          {s.zip_url && <a href={`http://${api}${s.zip_url}`} className="inline-block bg-[#E8590C] text-white rounded px-3 py-1.5 text-xs font-bold">Alles als ZIP herunterladen</a>}
          {s.shopify?.length > 0 && (
            <Block title="Shopify-Entwürfe">
              <ul className="text-xs space-y-1">
                {s.shopify.map(x => (
                  <li key={x.title}>
                    {x.url ? <a className="underline text-[#B34000]" href={x.url} target="_blank" rel="noreferrer">{x.title}</a> : <span>{x.title}</span>}
                    {x.error && <span className="text-red-700"> · {x.error}</span>}
                  </li>
                ))}
              </ul>
            </Block>
          )}
          {Object.entries(s.errors || {}).map(([k, v]) => <p key={k} className="text-xs text-red-700">{k}: {v}</p>)}
          {s.merch && (
            <Block title="Merch-Designs">
              <p className="text-xs text-stone-700">{s.merch.concept} · {s.merch.style}{s.merch.slogan ? ` · "${s.merch.slogan}"` : ''}</p>
              <div className="grid grid-cols-2 gap-2 mt-2">
                <Pic src={s.merch.front_url} label="Front-Logo" api={api} checker />
                {s.merch.back_url && <Pic src={s.merch.back_url} label="Backprint" api={api} checker />}
              </div>
              {s.merch.print_notes && <p className="text-xs text-stone-600 mt-2">{s.merch.print_notes}</p>}
              {s.merch.warning && <p className="text-xs text-red-700 mt-1">{s.merch.warning}</p>}
            </Block>
          )}
          {s.brand && (
            <Block title={`Brand-Kit: ${s.brand.brand_name}`}>
              <p className="text-xs text-stone-700">{s.brand.tagline}{s.brand.voice ? ` · ${s.brand.voice}` : ''}</p>
              <div className="flex gap-1 mt-2">
                {s.brand.palette.map(c => (
                  <button key={c.hex} type="button" title={`${c.name} (${c.role}): Hex kopieren`} onClick={() => navigator.clipboard?.writeText(c.hex)}
                    className="flex-1 text-left focus:outline focus:outline-2 focus:outline-[#E8590C]">
                    <span className="block h-10 rounded border border-stone-300" style={{ background: c.hex }} />
                    <span className="text-[10px]">{c.hex}</span>
                  </button>
                ))}
              </div>
              <ul className="mt-2 text-xs space-y-0.5">
                {s.brand.fonts.map(f => (
                  <li key={f.name}>{f.role}: <a className="underline text-[#B34000]" href={f.url} target="_blank" rel="noreferrer">{f.name}</a> <span className="text-stone-500">{f.why}</span></li>
                ))}
              </ul>
              <div className="grid grid-cols-2 gap-2 mt-2">
                {s.brand.logo_urls.map((u, i) => <Pic key={u} src={u} label={`Logo ${i + 1}`} api={api} checker />)}
                {s.brand.pattern_url && <Pic src={s.brand.pattern_url} label="Muster" api={api} />}
                <Pic src={s.brand.board_url} label="Brand-Board" api={api} />
              </div>
            </Block>
          )}
          {s.mockups?.length > 0 && (
            <Block title="Mockups">
              <div className="grid grid-cols-2 gap-2">{s.mockups.map(m => <Pic key={m.url} src={m.url} label={m.label} api={api} />)}</div>
            </Block>
          )}
        </div>
      )}
    </div>
  );
}

export function ContentResults({ results, selectedId, onSelect, api }) {
  const r = results.find(x => x.id === selectedId);
  const u = (p) => `http://${api}${p}`;
  return (
    <div>
      <h2 className="display font-bold mb-3">Content-Ergebnisse ({results.length})</h2>
      {results.length > 1 && (
        <select className="w-full border border-stone-400 rounded px-2 py-1 text-xs mb-3" value={selectedId} onChange={e => onSelect(Number(e.target.value))} aria-label="Ergebnis wählen">
          {results.map(x => <option key={x.id} value={x.id}>{x.topic} ({new Date(x.id).toLocaleTimeString('de-DE')})</option>)}
        </select>
      )}
      {!r ? <p className="text-sm text-stone-500">Hier erscheinen Thumbnails, Streamer-Paket und Banner.</p> : (
        <div className="space-y-4 text-sm">
          <p className="font-medium">{r.topic}{r.vibe ? ` · ${r.vibe}` : ''}</p>
          {r.zip_url && <a href={u(r.zip_url)} className="inline-block bg-[#E8590C] text-white rounded px-3 py-1.5 text-xs font-bold">Alles als ZIP herunterladen</a>}
          {Object.entries(r.errors || {}).map(([k, v]) => <p key={k} className="text-xs text-red-700">{k}: {v}</p>)}
          {(r.warnings || []).map((w, i) => <p key={i} className="text-xs text-amber-800">{w}</p>)}
          {r.kit && (
            <Block title={`Look: ${r.kit.name}`}>
              <p className="text-xs text-stone-700">{r.kit.tagline} · Schrift {r.kit.font} · Rahmen {r.kit.frame}</p>
              <div className="flex gap-1 mt-2">
                {r.kit.palette.map(h => (
                  <button key={h} type="button" title="Hex kopieren" onClick={() => navigator.clipboard?.writeText(h)} className="flex-1 text-left focus:outline focus:outline-2 focus:outline-[#E8590C]">
                    <span className="block h-8 rounded border border-stone-300" style={{ background: h }} /><span className="text-[10px]">{h}</span>
                  </button>
                ))}
              </div>
            </Block>
          )}
          {r.groups.map(g => (
            <Block key={g.title} title={g.title}>
              <div className="grid grid-cols-2 gap-2">
                {g.items.map(it => (
                  <div key={it.url} className={it.mini || it.w > 1600 ? 'col-span-2' : ''}>
                    <a href={u(it.url)} target="_blank" rel="noreferrer" className="block" aria-label={`${it.label} groß öffnen`}>
                      <img src={u(it.url)} alt={it.label} className={`w-full max-h-52 object-contain rounded border border-stone-300 ${/Overlay|Alerts/.test(g.title) ? 'checker' : 'bg-stone-100'}`} />
                    </a>
                    <div className="flex items-end gap-2 mt-1">
                      <span className="text-xs text-stone-600 flex-1">{it.label}</span>
                      {it.mini && <span className="text-center shrink-0"><img src={u(it.url)} alt="" className="w-24 rounded border border-stone-300" /><span className="block text-[10px] text-stone-500">Handy-Größe</span></span>}
                    </div>
                  </div>
                ))}
              </div>
            </Block>
          ))}
        </div>
      )}
    </div>
  );
}

export default function App() {
  const [connected, setConnected] = useState(false);
  const [running, setRunning] = useState(false);
  const [category, setCategory] = useState('Cyberpunk Digital Downloads');
  const [provider, setProvider] = useState('groq');
  const [publish, setPublish] = useState(false);
  const [count, setCount] = useState(3);
  const [tab, setTab] = useState('boss');
  const [accentColor, setAccentColor] = useState(() => { try { return localStorage.getItem('a1-factory.accent') || '#8B5CF6'; } catch { return '#8B5CF6'; } });
  useEffect(() => { document.documentElement.style.setProperty('--a1-accent', accentColor); try { localStorage.setItem('a1-factory.accent', accentColor); } catch {} }, [accentColor]);
  const [bossMessages, setBossMessages] = useState([{ role: 'assistant', content: 'Ich bin der Boss. Beschreibe dein Ziel; ich helfe dir, den passenden Workflow und die nächsten Schritte festzulegen.' }]);
  const [bossDraft, setBossDraft] = useState('');
  const [bossAttachment, setBossAttachment] = useState(null);
  const [bossMediaMenu, setBossMediaMenu] = useState(false);
  const bossFileInputRef = useRef(null);
  const [speechListening, setSpeechListening] = useState(false);
  const [speechSupported, setSpeechSupported] = useState(false);
  const speechRef = useRef(null);
  const [bossBusy, setBossBusy] = useState(false);
  const [bossError, setBossError] = useState('');
  const [bossPlan, setBossPlan] = useState(null);
  const [bossMediaPrompt, setBossMediaPrompt] = useState('');
  const [modules, setModules] = useState({ merch: true, brand: true, mockups: true });
  const [variants, setVariants] = useState(2);
  const [withMockups, setWithMockups] = useState(true);
  const [shopifyOn, setShopifyOn] = useState(false);
  const [cModules, setCModules] = useState({ thumbnails: true, streamer: true, banners: true });
  const [formats, setFormats] = useState({ yt: true, square: false, story: false });
  const [bannerTargets, setBannerTargets] = useState({ youtube: true, x: true, discord: true, linkedin: true });
  const [lang, setLang] = useState('Deutsch');
  const [hint, setHint] = useState('');
  const [contents, setContents] = useState([]);
  const [contentId, setContentId] = useState(null);
  const [studios, setStudios] = useState([]);
  const [studioId, setStudioId] = useState(null);
  const [ref, setRef] = useState(null);
  const [refMode, setRefMode] = useState('style');
  const [cfg, setCfg] = useState(loadCfg);
  const [remember, setRemember] = useState(() => !!localStorage.getItem(STORE));
  const [showSettings, setShowSettings] = useState(() => !localStorage.getItem(STORE));
  const [stations, setStations] = useState(fresh);
  const [logs, setLogs] = useState([]);
  const [products, setProducts] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [editingProduct, setEditingProduct] = useState(false);
  const [editDraft, setEditDraft] = useState({ title: '', description: '', price: '', niche: '', tags: '' });
  const [productError, setProductError] = useState('');
  const wsRef = useRef(null);
  const logEnd = useRef(null);

  const log = useCallback((source, text, error = false) => {
    setLogs(l => [...l.slice(-199), { t: new Date().toLocaleTimeString('de-DE'), source, text, error }]);
  }, []);

  useEffect(() => {
    setSpeechSupported(typeof window !== 'undefined' && !!(window.SpeechRecognition || window.webkitSpeechRecognition));
    return () => {
      if (speechRef.current) { speechRef.current.onend = null; speechRef.current.stop(); speechRef.current = null; }
    };
  }, []);

  const toggleSpeechInput = () => {
    if (speechListening) {
      speechRef.current?.stop();
      setSpeechListening(false);
      return;
    }
    const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!Recognition) {
      setBossError('Spracherkennung wird in diesem Browser nicht unterstützt. Bitte nutze Chrome oder Edge oder tippe deinen Auftrag ein.');
      return;
    }
    const recognition = new Recognition();
    speechRef.current = recognition;
    recognition.lang = 'de-DE';
    recognition.continuous = true;
    recognition.interimResults = true;
    let finalTranscript = '';
    recognition.onstart = () => { setSpeechListening(true); setBossError(''); };
    recognition.onresult = (event) => {
      let interim = '';
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const text = event.results[i][0]?.transcript || '';
        if (event.results[i].isFinal) finalTranscript += `${text} `;
        else interim += text;
      }
      const transcript = `${finalTranscript}${interim}`.trim();
      if (transcript) setBossDraft(transcript);
    };
    recognition.onerror = (event) => {
      setSpeechListening(false);
      const message = event.error === 'not-allowed' ? 'Mikrofonzugriff verweigert. Erlaube den Mikrofonzugriff in den Browser-Einstellungen.' : `Spracherkennung fehlgeschlagen (${event.error}).`;
      setBossError(message);
    };
    recognition.onend = () => { setSpeechListening(false); speechRef.current = null; };
    try { recognition.start(); } catch (error) { setSpeechListening(false); setBossError(`Mikrofon konnte nicht gestartet werden: ${error.message}`); }
  };

  useEffect(() => {
    let closed = false, timer;
    const connect = () => {
      const ws = new WebSocket(`ws://${API}/ws/factory`);
      wsRef.current = ws;
      ws.onopen = () => { setConnected(true); log('System', 'Mit der Fabrik verbunden'); };
      ws.onclose = () => {
        setConnected(false); setRunning(false);
        if (!closed) timer = setTimeout(connect, 2000);
      };
      ws.onmessage = (e) => {
        const { type, data } = JSON.parse(e.data);
        if (type === 'ETSY_TOKENS') setCfg(c => ({ ...c, etsy: { ...c.etsy, ...data } }));
        if (type === 'AGENT_STATUS') {
          setStations(s => ({ ...s, [data.agent]: { status: data.status, message: data.message } }));
          log(STATIONS[data.agent]?.name || data.agent, data.message, data.status === 'error');
        }
        if (type === 'CONTENT_RESULT') {
          setContents(p => [data, ...p]); setContentId(data.id);
          log('Fabrik', `Content fertig: ${data.topic}`);
        }
        if (type === 'STUDIO_RESULT') {
          setStudios(p => [data, ...p]); setStudioId(data.id);
          log('Fabrik', `Studio fertig: ${data.niche}`);
        }
        if (type === 'PRODUCT_CREATED') {
          setProducts(p => [data, ...p.filter(item => String(item.id) !== String(data.id))]); setSelectedId(data.id);
          setEditingProduct(false);
          log('Fabrik', `Produkt fertig: ${data.title}`);
        }
        if (type === 'RUN_FAILED') log('Fabrik', data.error, true);
        if (type === 'RUN_FINISHED') setRunning(false);
      };
    };
    connect();
    return () => { closed = true; clearTimeout(timer); wsRef.current?.close(); };
  }, [log]);

  useEffect(() => {
    let cancelled = false;
    fetch(`${API_ORIGIN}/api/products`)
      .then(async response => { if (!response.ok) throw new Error('Produkte konnten nicht geladen werden.'); return response.json(); })
      .then(data => {
        if (cancelled) return;
        const loaded = Array.isArray(data.products) ? data.products : [];
        setProducts(loaded);
        setSelectedId(current => current ?? loaded[0]?.id ?? null);
      })
      .catch(error => { if (!cancelled) setProductError(error.message); });
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    if (!editingProduct || !product) return;
    setEditDraft({ title: product.title || '', description: product.description || '', price: String(product.price ?? ''), niche: product.niche || '', tags: (product.tags || []).join(', ') });
  }, [editingProduct, selectedId]);

  const saveProductChanges = async () => {
    if (!product) return;
    setProductError('');
    const price = Number(editDraft.price);
    if (!editDraft.title.trim() || !Number.isFinite(price) || price < 0) {
      setProductError('Bitte einen Titel und einen gültigen, nicht negativen Preis eingeben.');
      return;
    }
    try {
      const response = await fetch(`${API_ORIGIN}/api/products/${encodeURIComponent(product.id)}`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: editDraft.title.trim(), description: editDraft.description, price,
          niche: editDraft.niche.trim(), tags: editDraft.tags.split(',').map(t => t.trim()).filter(Boolean) })
      });
      const updated = await response.json();
      if (!response.ok) throw new Error(updated.detail || 'Produkt konnte nicht gespeichert werden.');
      setProducts(items => items.map(item => String(item.id) === String(updated.id) ? updated : item));
      setEditingProduct(false);
    } catch (error) { setProductError(error.message); }
  };

  const removeProduct = async () => {
    if (!product || !window.confirm(`Produkt „${product.title}“ wirklich löschen?`)) return;
    setProductError('');
    try {
      const response = await fetch(`${API_ORIGIN}/api/products/${encodeURIComponent(product.id)}`, { method: 'DELETE' });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || 'Produkt konnte nicht gelöscht werden.');
      const remaining = products.filter(item => String(item.id) !== String(product.id));
      setProducts(remaining); setSelectedId(remaining[0]?.id ?? null); setEditingProduct(false);
    } catch (error) { setProductError(error.message); }
  };

  useEffect(() => {
    try { remember ? localStorage.setItem(STORE, JSON.stringify(cfg)) : localStorage.removeItem(STORE); } catch { /* Speicher gesperrt */ }
  }, [cfg, remember]);

  const llm = cfg.llm[provider] || { key: '', model: '' };
  useEffect(() => {
    setRefMode(m => (tab === 'content' ? (m === 'direct' ? 'asset' : m) : (m === 'asset' ? 'style' : m)));
  }, [tab]);

  const setLlmFor = (p, patch) => setCfg(c => ({ ...c, llm: { ...c.llm, [p]: { ...(c.llm[p] || {}), ...patch } } }));
  const setShopify = (k, v) => setCfg(c => ({ ...c, shopify: { ...c.shopify, [k]: v } }));
  const setEtsy = (k, v) => setCfg(c => ({ ...c, etsy: { ...c.etsy, [k]: v } }));
  const clearAll = () => { setCfg(EMPTY); setRemember(false); };
  const imageProvider = IMAGE_PROVIDERS[cfg.imageProvider] ? cfg.imageProvider : 'pollinations';
  const imgDef = IMAGE_PROVIDERS[imageProvider];
  const imgCfg = cfg.img?.[imageProvider] || {};
  const setImg = (k, v) => setCfg(c => ({ ...c, img: { ...c.img, [imageProvider]: { ...(c.img?.[imageProvider] || {}), [k]: v } } }));
  const imgMissing = imgDef.fields.filter(([k, , , req]) => req && !imgCfg[k]?.trim()).map(([, l]) => l);
  const missing = [
    !category.trim() && 'Thema oder Kanal eintragen',
    ...(provider === 'custom'
      ? [!llm.base_url?.trim() && 'Base-URL', !llm.model?.trim() && 'Modellname']
      : [!llm.key?.trim() && `Key für ${PROVIDERS.find(p => p[0] === provider)[1]}`]),
    ...imgMissing,
    ref && refMode === 'direct' && !IMG2IMG.includes(imageProvider) && 'Bildanbieter für Bild-zu-Bild (Gemini, OpenAI oder Lokal)',
    tab === 'studio' && !MODULES.some(([k]) => modules[k]) && 'mindestens ein Modul',
    tab === 'content' && !CONTENT_MODULES.some(([k]) => cModules[k]) && 'mindestens ein Modul',
    tab === 'content' && cModules.thumbnails && !FORMAT_LIST.some(([k]) => formats[k]) && 'ein Thumbnail-Format',
    tab === 'content' && cModules.banners && !BANNER_LIST.some(([k]) => bannerTargets[k]) && 'ein Banner-Format',
    ...(shopifyOn && tab !== 'content' ? [
      !cfg.shopify?.shop?.trim() && 'Shopify-Shop-Adresse',
      !cfg.shopify?.access_token?.trim() && !(cfg.shopify?.client_id?.trim() && cfg.shopify?.client_secret?.trim()) && 'Shopify-Token oder Client-ID und Secret',
    ] : []),
    ...(tab === 'factory' && publish ? ETSY_FIELDS.filter(([k]) => !cfg.etsy[k]?.trim()).map(([, l]) => l) : []),
  ].filter(Boolean);
  const startBlockers = [
    ...(!connected ? ['Backend ist nicht verbunden. Starte zuerst das Backend und lade die App neu.'] : []),
    ...missing,
  ];

  useEffect(() => { logEnd.current?.scrollIntoView({ block: 'end' }); }, [logs]);

  const onRefFile = async (e) => {
    const f = e.target.files?.[0];
    e.target.value = '';
    if (!f) return;
    try { setRef({ dataUrl: await shrinkImage(f), name: f.name }); }
    catch (err) { log('System', String(err.message), true); }
  };

  const start = () => {
    if (!connected || running || !category.trim() || missing.length) return;
    setStations(fresh()); setRunning(true);
    const studio = tab === 'studio', content = tab === 'content';
    wsRef.current.send(JSON.stringify({
      action: content ? 'start_content' : studio ? 'start_studio' : 'start_production', category, provider, publish: tab === 'factory' && publish,
      image_count: tab === 'factory' ? count : variants,
      modules: content ? CONTENT_MODULES.map(([k]) => k).filter(k => cModules[k]) : studio ? MODULES.map(([k]) => k).filter(k => modules[k]) : undefined,
      formats: content ? FORMAT_LIST.map(([k]) => k).filter(k => formats[k]) : undefined,
      banners: content ? BANNER_LIST.map(([k]) => k).filter(k => bannerTargets[k]) : undefined,
      language: lang, hint,
      mockups: tab === 'factory' && withMockups,
      reference: ref ? { data_url: ref.dataUrl, name: ref.name, mode: refMode } : undefined,
      api_key: llm.key || '', model: llm.model || '', base_url: llm.base_url || '', image: { provider: imageProvider, ...imgCfg },
      etsy: cfg.etsy, shopify_enabled: tab !== 'content' && shopifyOn, shopify: cfg.shopify,
    }));
    log('Du', `Start mit ${provider}: ${category}`);
  };

  const onBossAttachment = async (event) => {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file) return;
    const isImage = file.type.startsWith('image/');
    const isVideo = file.type.startsWith('video/');
    if (!isImage && !isVideo) { setBossError('Bitte eine Bild- oder Videodatei auswählen.'); return; }
    const maxBytes = 12 * 1024 * 1024;
    if (file.size > maxBytes) { setBossError('Die Datei ist zu groß. Bitte nutze maximal 12 MB.'); return; }
    try {
      const dataUrl = await new Promise((resolve, reject) => { const reader = new FileReader(); reader.onload = () => resolve(String(reader.result)); reader.onerror = () => reject(new Error('Datei konnte nicht gelesen werden.')); reader.readAsDataURL(file); });
      setBossAttachment({ name: file.name, type: file.type, kind: isImage ? 'image' : 'video', size: file.size, dataUrl, previewUrl: URL.createObjectURL(file) });
      setBossError('');
    } catch (error) { setBossError(error.message); }
  };

  const sendBossMessage = async (event) => {
    event?.preventDefault();
    const message = bossDraft.trim();
    if ((!message && !bossAttachment) || bossBusy) return;
    const previous = bossMessages;
    const displayContent = message || `Bitte verwende diese ${bossAttachment.kind === 'image' ? 'Bildreferenz' : 'Videoreferenz'}: ${bossAttachment.name}`;
    const next = [...previous, { role: 'user', content: displayContent, attachment: bossAttachment ? { name: bossAttachment.name, type: bossAttachment.type, kind: bossAttachment.kind, previewUrl: bossAttachment.previewUrl } : null }];
    setBossMessages(next); setBossDraft(''); setBossBusy(true); setBossError(''); setBossPlan(null);
    try {
      const response = await fetch(`${API_ORIGIN}/api/boss/chat`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider, api_key: llm.key || '', model: llm.model || '', base_url: llm.base_url || '', message: message || displayContent,
          attachments: bossAttachment ? [{ name: bossAttachment.name, type: bossAttachment.type, kind: bossAttachment.kind, data_url: bossAttachment.dataUrl }] : [],
          history: previous.slice(-12).map(({ role, content }) => ({ role, content })) })
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Boss konnte nicht antworten.');
      setBossMessages(items => [...items, { role: 'assistant', content: data.reply, attachments: data.attachments || [], mediaAnalysis: data.media_analysis || [] }]);
      if (bossAttachment?.kind === 'image') { setRef({ dataUrl: bossAttachment.dataUrl, name: bossAttachment.name }); setRefMode('style'); }
      setBossAttachment(null); setBossMediaMenu(false);
      if (data.workflow && data.workflow !== 'none') {
        const visualContext = (data.media_analysis || []).map(a => `${a.name}: ${(a.frames || []).map(f => f.summary).join(' ')}`).join('\n');
        const mediaPrompt = [`Erfülle die Nutzeranweisung so genau wie möglich. Bewahre alle konkreten Aktionen, Bewegungen, Motive und Stilvorgaben; ersetze sie nicht durch eine allgemeinere Szene.`, `Aufgabe: ${data.category || 'Medienproduktion'}`, `Originalanweisung des Nutzers (maßgeblich): ${message}`, visualContext ? `Visuelle Referenzanalyse:\n${visualContext}` : ''].filter(Boolean).join('\n\n').slice(0, 2000);
        setBossMediaPrompt(mediaPrompt);
        setBossPlan({ ...data, mediaPrompt, videoReferenceFrame: data.video_reference_frame_data_url || '' });
      }
    } catch (error) { setBossError(error.message || 'Verbindung fehlgeschlagen.'); }
    finally { setBossBusy(false); }
  };

  const applyBossPlan = () => {
    if (!bossPlan) return;
    const target = ['factory', 'studio', 'content', 'story', 'game-assets', 'media'].includes(bossPlan.workflow) ? bossPlan.workflow : 'factory';
    if (bossPlan.category?.trim()) setCategory(bossPlan.category.trim());
    setTab(target); setBossPlan(null);
  };

  const executeBossPlan = () => {
    if (!bossPlan || running || (bossPlan.workflow !== 'media' && !connected)) return;
    const target = bossPlan.workflow;
    const plannedCategory = bossPlan.category?.trim() || category;
    if (target === 'media') {
      let mediaCfg = {};
      try { mediaCfg = JSON.parse(localStorage.getItem('agent-factory.media.v1') || '{}'); } catch {}
      if (!mediaCfg.replicateKey?.trim()) {
        setBossError('Für die Videogenerierung fehlt der Replicate-Token. Öffne Audio & Video, hinterlege ihn einmal und starte den Boss-Auftrag erneut.');
        setTab('media');
        return;
      }
      const originalRequest = String(bossPlan.mediaPrompt || plannedCategory).slice(0, 2000);
      const wantsSound = /\b(soundtrack|sound effects?|audio|sound|musik|tonspur|hintergrundmusik|miauen|miau|katzen?geräusch|geräusch|soundeffekt|sprechen|spricht|voice.?over|gesang|singen)\b/i.test(originalRequest);
      if (wantsSound && !mediaCfg.elevenlabsKey?.trim()) {
        setBossError('Für den gewünschten Soundtrack fehlt der ElevenLabs-API-Key. Hinterlege ihn unter Audio & Video → Zugangsdaten; der Boss kann dann Bild und Ton automatisch zusammenführen.');
        setTab('media');
        return;
      }
      const requestedAction = originalRequest.replace(/^Aufgabe:[^\n]*\n\n/, '');
      const prompt = `${requestedAction}\n\nWichtig: Setze die ausdrücklich verlangte Handlung sichtbar um. Keine Ersatzhandlung und keine bloße Vorwärtsbewegung, wenn eine konkrete Tanzbewegung verlangt ist.`.slice(0, 2000);
      setBossBusy(true); setBossError('');
      (async () => {
        const videoResponse = await fetch(`${API_ORIGIN}/api/media/video`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ api_key: mediaCfg.replicateKey, prompt, model_slug: mediaCfg.videoModel || 'minimax/video-01', duration_seconds: Number(mediaCfg.duration || 5), reference_image_data_url: bossPlan.videoReferenceFrame || '' }) });
        const video = await videoResponse.json();
        if (!videoResponse.ok) throw new Error(video.detail || 'Videogenerierung fehlgeschlagen.');
        let finalMedia = video;
        let status = `Video erstellt (${video.model || 'Replicate'}).`;
        if (wantsSound) {
          const soundPrompt = /miauen|miau|katzen?geräusch/i.test(originalRequest)
            ? 'Loud, clear, realistic cat meowing repeatedly as a prominent soundtrack. No speech, no music, no other foreground sounds.'
            : `Create the sound effects/music explicitly requested here. Soundtrack brief: ${originalRequest}. Produce audio only; preserve the requested sound type, mood, and intensity.`;
          const soundResponse = await fetch(`${API_ORIGIN}/api/media/sound-effects`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ api_key: mediaCfg.elevenlabsKey, prompt: soundPrompt, duration_seconds: Math.min(22, Math.max(3, Number(mediaCfg.duration || 5))) }) });
          const sound = await soundResponse.json();
          if (!soundResponse.ok) throw new Error(`Video wurde erstellt, aber der Soundtrack schlug fehl: ${sound.detail || 'unbekannter Fehler'}. Du kannst den Clip in Audio & Video erneut bearbeiten.`);
          const composeResponse = await fetch(`${API_ORIGIN}/api/media/compose`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ video_filename: video.filename, audio_filename: sound.filename, audio_volume: 1 }) });
          const composed = await composeResponse.json();
          if (!composeResponse.ok) throw new Error(`Video und Sound wurden erzeugt, aber nicht zusammengeführt: ${composed.detail || 'unbekannter Fehler'}.`);
          finalMedia = composed;
          status = `Fertiges Video mit Soundtrack erstellt. Video: ${video.model || 'Replicate'} · Audio: ElevenLabs Sound Effects · Audiospur vorhanden.`;
        }
        setBossMessages(items => [...items, { role: 'assistant', content: status, generatedMedia: `${API_ORIGIN}${finalMedia.url}` }]);
        setBossPlan(null); log('Boss', status);
      })()
        .catch(error => setBossError(error.message || 'Medienproduktion fehlgeschlagen.'))
        .finally(() => setBossBusy(false));
      return;
    }
    if (!['factory', 'studio', 'content'].includes(target)) {
      setCategory(plannedCategory);
      setTab(target);
      setBossPlan(null);
      log('Boss', `Auftrag vorbereitet. Für „${target}“ öffne ich die Station; dort bitte die passende Aktion starten.`);
      return;
    }
    if (!llm.key?.trim() && provider !== 'custom') {
      setBossError(`Bitte hinterlege zuerst den API-Key für ${PROVIDERS.find(p => p[0] === provider)?.[1] || provider}.`);
      return;
    }
    if (provider === 'custom' && (!llm.base_url?.trim() || !llm.model?.trim())) {
      setBossError('Beim eigenen Anbieter fehlen Base-URL oder Modellname.');
      return;
    }
    const studio = target === 'studio', content = target === 'content';
    const chosenModules = content
      ? CONTENT_MODULES.map(([k]) => k).filter(k => cModules[k])
      : studio ? MODULES.map(([k]) => k).filter(k => modules[k]) : undefined;
    if ((content || studio) && !chosenModules?.length) {
      setBossError('Wähle in der passenden Station mindestens ein Modul aus, bevor du den Auftrag ausführst.');
      setTab(target);
      return;
    }
    if (content && cModules.thumbnails && !FORMAT_LIST.some(([k]) => formats[k])) {
      setBossError('Wähle mindestens ein Thumbnail-Format in den Content-Einstellungen.'); setTab(target); return;
    }
    if (content && cModules.banners && !BANNER_LIST.some(([k]) => bannerTargets[k])) {
      setBossError('Wähle mindestens ein Banner-Format in den Content-Einstellungen.'); setTab(target); return;
    }
    setBossError(''); setStations(fresh()); setRunning(true); setTab(target); setBossPlan(null);
    const payload = {
      action: content ? 'start_content' : studio ? 'start_studio' : 'start_production',
      category: plannedCategory, provider, publish: false,
      image_count: target === 'factory' ? count : variants,
      modules: chosenModules,
      formats: content ? FORMAT_LIST.map(([k]) => k).filter(k => formats[k]) : undefined,
      banners: content ? BANNER_LIST.map(([k]) => k).filter(k => bannerTargets[k]) : undefined,
      language: lang, hint, mockups: target === 'factory' && withMockups,
      reference: ref ? { data_url: ref.dataUrl, name: ref.name, mode: refMode } : undefined,
      api_key: llm.key || '', model: llm.model || '', base_url: llm.base_url || '',
      image: { provider: imageProvider, ...imgCfg }, etsy: cfg.etsy,
      shopify_enabled: false, shopify: cfg.shopify,
    };
    try {
      wsRef.current.send(JSON.stringify(payload));
      log('Boss', `Auftrag delegiert: ${plannedCategory} → ${target === 'factory' ? 'Wallpaper-Fabrik' : target === 'studio' ? 'Marketing-Studio' : 'Content-Studio'}. Externe Veröffentlichungen bleiben deaktiviert.`);
    } catch (error) {
      setRunning(false); setBossError(`Auftrag konnte nicht gestartet werden: ${error.message}`);
    }
  };

  const product = products.find(p => p.id === selectedId);

  return (
    <div className="a1-app min-h-screen p-4 md:p-8">
      <GlobeBackground />
      <div className="max-w-6xl mx-auto a1-content">
        <header className="a1-header flex flex-wrap items-end justify-between gap-4 mb-6">
          <div>
            <div className="flex items-center gap-3"><span className="a1-mark">A1</span><h1 className="display text-3xl font-bold">A1 Factory</h1></div>
            <p className="text-sm text-stone-600 mt-2">AI CREATION WORKSPACE <span className="a1-separator">/</span> Von der Idee zum Ergebnis.</p>
          </div>
          <div className="a1-header-tools flex flex-wrap items-center gap-3">
            <label className="a1-color-control" title="Freie Akzentfarbe auswählen">
              <span className="a1-color-swatch" style={{ backgroundColor: accentColor }} />
              <span className="a1-color-label">AKZENT</span>
              <input aria-label="Akzentfarbe frei wählen" type="color" value={accentColor} onChange={e => setAccentColor(e.target.value)} />
              <span className="a1-hex">{accentColor.toUpperCase()}</span>
            </label>
            <span className={`a1-connection text-xs px-2 py-1 ${connected ? 'bg-emerald-700 text-white' : 'bg-red-700 text-white'}`}>
              <span className="a1-status-dot" />{connected ? 'Verbunden' : 'Verbindung wird aufgebaut'}
            </span>
          </div>
        </header>

        <div className="flex gap-2 mb-6" role="tablist">
          {[['boss', 'Boss-Chat'], ['factory', 'Wallpaper-Fabrik'], ['studio', 'Marketing-Studio'], ['content', 'Content-Studio'], ['story', 'Storytelling'], ['game-assets', 'Game Assets'], ['media', 'Audio & Video'], ['library', 'Medienbibliothek']].map(([k, l]) => (
            <button key={k} role="tab" aria-selected={tab === k} onClick={() => setTab(k)} disabled={running}
              className={`display font-bold px-4 py-2 rounded-t border-b-4 text-sm ${tab === k ? 'border-[#E8590C] bg-white' : 'border-transparent text-stone-600 hover:bg-[#EFEDE7]'}`}>{l}</button>
          ))}
        </div>

        {tab === 'library' ? <MediaLibraryWorkspace apiOrigin={API_ORIGIN} /> : tab === 'boss' ? <section className="bg-white border border-stone-400 rounded-lg p-4 md:p-6">
          <div className="flex flex-wrap items-start justify-between gap-3 mb-4">
            <div><h2 className="display text-2xl font-bold">Boss-Zentrale</h2><p className="text-sm text-stone-600 mt-1">Aufträge besprechen, Workflow planen und zur passenden Station wechseln.</p></div>
            <span className="text-xs rounded bg-[#FFF4EC] border border-[#E8590C] px-2 py-1">KI: {PROVIDERS.find(p => p[0] === provider)?.[1] || provider}</span>
          </div>
          <div className="h-[min(52vh,480px)] min-h-64 overflow-y-auto border border-stone-300 rounded p-3 bg-[#F8F7F3] space-y-3" aria-live="polite">
            {bossMessages.map((m, i) => <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}><div className={`max-w-[90%] whitespace-pre-wrap rounded-lg px-3 py-2 text-sm ${m.role === 'user' ? 'bg-stone-800 text-white' : 'bg-white border border-stone-300'}`}><p className="text-[11px] font-semibold mb-1 opacity-70">{m.role === 'user' ? 'Du' : 'Boss'}</p>{m.content}{m.generatedMedia && <video controls playsInline className="mt-2 max-h-80 w-full rounded border border-stone-300" src={m.generatedMedia}>Dein Browser unterstützt keine Videowiedergabe.</video>}{m.mediaAnalysis?.length > 0 && <div className="mt-3 space-y-2">{m.mediaAnalysis.map((analysis, ai) => <div key={`${analysis.name}-${ai}`} className="rounded border border-stone-300 bg-stone-50 p-2"><p className="font-semibold text-xs">Medienanalyse: {analysis.name}</p>{analysis.frames?.map((frame, fi) => <p key={`${frame.frame}-${fi}`} className="mt-1 text-xs text-stone-700"><span className="font-semibold">{frame.frame}:</span> {frame.summary}</p>)}</div>)}</div>}{m.attachment && <div className="mt-2 text-xs">{m.attachment.kind === 'image' ? <img src={m.attachment.previewUrl} alt={m.attachment.name} className="max-h-40 max-w-full rounded border border-stone-300" /> : <div className="rounded border border-stone-300 p-2">🎬 {m.attachment.name}</div>}<p className="mt-1 opacity-75">Anhang: {m.attachment.name}</p></div>}</div></div>)}
            {bossBusy && <p className="text-sm text-stone-500 animate-pulse">Boss denkt nach…</p>}
          </div>
          {bossError && <p className="text-sm text-red-700 mt-2" role="alert">{bossError}</p>}
          {bossPlan && <div className="mt-4 border border-[#E8590C] bg-[#FFF4EC] rounded p-3"><p className="font-semibold text-sm">Workflow vorgeschlagen: {({factory:'Wallpaper-Fabrik',studio:'Marketing-Studio',content:'Content-Studio',story:'Storytelling','game-assets':'Game Assets',media:'Audio & Video',library:'Medienbibliothek'})[bossPlan.workflow] || bossPlan.workflow}</p>{bossPlan.category && <p className="text-sm mt-1">Aufgabe: {bossPlan.category}</p>}{bossPlan.next_step && <p className="text-sm text-stone-700 mt-1">Nächster Schritt: {bossPlan.next_step}</p>}<div className="mt-3 flex flex-wrap gap-2"><button type="button" onClick={executeBossPlan} disabled={bossPlan.workflow === 'media' ? bossBusy : (running || !connected)} className="bg-[#E8590C] text-white font-semibold rounded px-4 py-2 text-sm hover:bg-orange-700 disabled:opacity-50">{['factory','studio','content'].includes(bossPlan.workflow) ? 'Auftrag jetzt ausführen' : bossPlan.workflow === 'media' ? 'Medienproduktion starten' : 'Station öffnen'}</button><button type="button" onClick={applyBossPlan} className="border border-stone-400 bg-white text-stone-800 font-semibold rounded px-4 py-2 text-sm">Nur übernehmen</button></div><p className="text-xs text-stone-600 mt-2">Fabrik, Marketing und Content werden direkt an die vorhandenen Produktionspipelines übergeben. Bei Medienaufträgen versucht der Boss, die Originalanweisung zu erhalten. Wenn Sound gewünscht ist, erzeugt er zusätzlich einen Soundeffekt und fügt ihn mit ffmpeg als Audiospur in das Video ein. Dafür werden Replicate und ElevenLabs benötigt; die Generierung kann kostenpflichtig sein. Veröffentlichungen bei Etsy/Shopify werden nicht automatisch ausgelöst.</p></div>}
          <form onSubmit={sendBossMessage} className="mt-4 flex flex-col gap-2"><textarea value={bossDraft} onChange={e => setBossDraft(e.target.value)} rows={3} maxLength={6000} placeholder="Schreib oder sprich deinen Auftrag… Du kannst auch direkt ein Bild oder Video anhängen." className={`${field} flex-1 resize-y`} />
            {bossAttachment && <div className="flex items-center gap-3 rounded border border-stone-300 bg-stone-50 p-3">{bossAttachment.kind === 'image' ? <img src={bossAttachment.previewUrl} alt="Vorschau" className="h-16 w-16 rounded object-cover" /> : <div className="flex h-16 w-16 items-center justify-center rounded bg-stone-200 text-2xl">🎬</div>}<div className="min-w-0 flex-1"><p className="truncate text-sm font-semibold">{bossAttachment.name}</p><p className="text-xs text-stone-500">{bossAttachment.kind === 'image' ? 'Bildreferenz' : 'Videoreferenz'} · {(bossAttachment.size / 1024 / 1024).toFixed(1)} MB</p></div><button type="button" onClick={() => { URL.revokeObjectURL(bossAttachment.previewUrl); setBossAttachment(null); }} className="text-sm underline">Entfernen</button></div>}
            <div className="flex flex-wrap gap-2"><div className="relative"><button type="button" onClick={() => setBossMediaMenu(v => !v)} aria-expanded={bossMediaMenu} className="font-semibold rounded px-4 py-3 border border-stone-400 bg-white text-stone-800 hover:bg-stone-100">＋ Medien hinzufügen ▾</button>{bossMediaMenu && <div className="absolute bottom-full left-0 z-20 mb-1 min-w-56 rounded border border-stone-300 bg-white p-1 shadow-lg"><button type="button" onClick={() => { if (bossFileInputRef.current) { bossFileInputRef.current.accept = 'image/*'; bossFileInputRef.current.click(); } setBossMediaMenu(false); }} className="block w-full rounded px-3 py-2 text-left text-sm hover:bg-stone-100">🖼️ Bild als Referenz hinzufügen</button><button type="button" onClick={() => { if (bossFileInputRef.current) { bossFileInputRef.current.accept = 'video/*'; bossFileInputRef.current.click(); } setBossMediaMenu(false); }} className="block w-full rounded px-3 py-2 text-left text-sm hover:bg-stone-100">🎬 Video als Referenz hinzufügen</button></div>}<input ref={bossFileInputRef} type="file" accept="image/*,video/*" onChange={onBossAttachment} className="hidden" /></div><button type="button" onClick={toggleSpeechInput} disabled={!speechSupported && !speechListening} aria-pressed={speechListening} className={`font-semibold rounded px-4 py-3 border disabled:opacity-50 ${speechListening ? 'bg-red-700 text-white border-red-700' : 'bg-white text-stone-800 border-stone-400 hover:bg-stone-100'}`}>{speechListening ? '■ Aufnahme stoppen' : '🎙️ Per Sprache eingeben'}</button><button type="submit" disabled={bossBusy || (!bossDraft.trim() && !bossAttachment)} className="bg-[#E8590C] text-white font-semibold rounded px-5 py-3 disabled:opacity-50">{bossBusy ? 'Denkt…' : 'An Boss senden'}</button></div>{speechListening && <p className="text-sm text-red-700" role="status">Ich höre zu … Sprich deinen Auftrag. Stoppe die Aufnahme, wenn du fertig bist.</p>}{!speechSupported && <p className="text-xs text-stone-500">Sprachsteuerung benötigt einen Browser mit Web Speech API, z. B. Chrome oder Edge, sowie Mikrofonfreigabe.</p>}<p className="text-xs text-stone-500">Bilder werden visuell analysiert und als Referenz für den nächsten Produktionsauftrag übernommen. Videos werden gespeichert und anhand von drei repräsentativen Einzelbildern visuell analysiert. Die Analyse fließt in die Workflow-Empfehlung ein; sie ist keine vollständige Einzelbild-für-Einzelbild-Prüfung. Maximal 12 MB pro Datei.</p></form>
          <p className="text-xs text-stone-500 mt-2">Der Boss nutzt den oben ausgewählten KI-Anbieter und dessen gespeicherte Zugangsdaten. Er plant und empfiehlt; externe Veröffentlichungen werden nicht ohne deinen Start ausgelöst.</p>
        </section> : tab === 'story' ? <StorytellingWorkspace apiOrigin={API_ORIGIN} /> : tab === 'game-assets' ? <GameAssetsWorkspace apiOrigin={API_ORIGIN} /> : tab === 'media' ? <AudioVideoWorkspace apiOrigin={API_ORIGIN} /> : <>
        <section className="bg-white border border-stone-400 rounded-lg mb-6">
          <button onClick={() => setShowSettings(v => !v)} aria-expanded={showSettings}
            className="w-full flex justify-between items-center px-4 py-3 text-left focus:outline focus:outline-2 focus:outline-[#E8590C]">
            <span className="display font-bold">Deine Zugangsdaten</span>
            <span className="text-xs text-stone-600">{missing.length ? `Es fehlt: ${missing.join(', ')}` : 'Alles eingetragen'} · {showSettings ? 'Einklappen' : 'Aufklappen'}</span>
          </button>
          {showSettings && (
            <div className="px-4 pb-4 grid gap-4 md:grid-cols-2 text-sm border-t border-stone-300 pt-4">
              <div className="md:col-span-2">
                <p className="font-medium mb-1">KI-Anbieter <span className="font-normal text-stone-600">(trag ein, was du hast. Mit welchem Anbieter gearbeitet wird, wählst du beim Start im Dropdown.)</span></p>
                <div className="grid gap-3">
                  {PROVIDERS.map(([p, label]) => {
                    const v = cfg.llm[p] || {};
                    return (
                      <div key={p} className={`rounded border p-3 grid gap-3 md:grid-cols-2 ${p === provider ? 'border-[#E8590C] bg-[#FFF4EC]' : 'border-stone-300'}`}>
                        <p className="md:col-span-2 text-xs font-medium flex flex-wrap items-center justify-between gap-2">
                          <span>{label}{p === provider && ' (aktiv)'}</span>
                          <span className={p === 'custom' ? ((v.base_url?.trim() && v.model?.trim()) ? 'text-emerald-700' : 'text-amber-700') : (v.key?.trim() ? 'text-emerald-700' : 'text-amber-700')}>
                            {p === 'custom' ? ((v.base_url?.trim() && v.model?.trim()) ? 'Grunddaten vorhanden' : 'Base-URL + Modell nötig') : (v.key?.trim() ? 'Key eingetragen' : 'Key fehlt')}
                          </span>
                        </p>
                        {p === 'custom' && (
                          <label className="block md:col-span-2">Base-URL (z. B. https://api.deepseek.com/v1 oder http://localhost:11434/v1)
                            <input className={`${field} mt-1`} value={v.base_url || ''} onChange={e => setLlmFor(p, { base_url: e.target.value })} />
                          </label>
                        )}
                        <label className="block">{p === 'custom' ? 'Key (leer lassen, wenn nicht nötig)' : 'Key'}
                          <input type="password" autoComplete="off" className={`${field} mt-1`} value={v.key || ''} onChange={e => setLlmFor(p, { key: e.target.value })} />
                        </label>
                        <div className="md:col-span-2">
                          <ModelPicker provider={p} v={v} field={field} required={p === 'custom'} onChange={m => setLlmFor(p, { model: m })} />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
              <div className="md:col-span-2">
                <label className="block">Bilder erzeugen mit
                  <select className={`${field} mt-1`} value={imageProvider} onChange={e => setCfg(c => ({ ...c, imageProvider: e.target.value }))}>
                    {Object.entries(IMAGE_PROVIDERS).map(([v, p]) => <option key={v} value={v}>{p.label}</option>)}
                  </select>
                </label>
                <p className="text-xs text-stone-600 mt-1">{imgDef.note}</p>
                <p className={`text-xs mt-2 font-medium ${imgMissing.length ? 'text-amber-800' : 'text-emerald-700'}`}>
                  {imgMissing.length ? `Einrichtung fehlt: ${imgMissing.join(', ')}` : 'Pflichtangaben für diesen Bildanbieter vorhanden.'}
                </p>
                {imgDef.fields.length > 0 && (
                  <div className="grid gap-3 md:grid-cols-2 mt-3">
                    {imgDef.fields.map(([k, l, type]) => (
                      <label key={k} className="block text-sm">{l}
                        <input type={type} autoComplete="off" className={`${field} mt-1`} value={imgCfg[k] || ''} onChange={e => setImg(k, e.target.value)} />
                      </label>
                    ))}
                  </div>
                )}
              </div>
              <div className="md:col-span-2">
                <p className="font-medium mb-2">Etsy <span className="font-normal text-stone-600">(nur nötig, wenn du Entwürfe anlegen willst)</span></p>
                <div className="grid gap-3 md:grid-cols-2">
                  {ETSY_FIELDS.map(([k, l]) => (
                    <label key={k} className="block">{l}
                      <input type={k.includes('token') || k === 'api_key' ? 'password' : 'text'} autoComplete="off" className={`${field} mt-1`}
                        value={cfg.etsy[k] || ''} onChange={e => setEtsy(k, e.target.value)} />
                    </label>
                  ))}
                </div>
              </div>
              <div className="md:col-span-2">
                <p className="font-medium mb-1">Shopify <span className="font-normal text-stone-600">(nur nötig, wenn du Entwürfe anlegen willst)</span></p>
                <p className="text-xs text-stone-600 mb-2">Trag entweder den Admin-Token einer älteren App ein oder Client-ID und Secret einer App aus dem Dev Dashboard. Die App braucht die Berechtigungen write_products und write_files und muss im Shop installiert sein. Produkte entstehen immer als Entwurf.</p>
                <div className="grid gap-3 md:grid-cols-2">
                  {SHOPIFY_FIELDS.map(([k, l, type]) => (
                    <label key={k} className="block text-sm">{l}
                      <input type={type} autoComplete="off" className={`${field} mt-1`} value={cfg.shopify?.[k] || ''} onChange={e => setShopify(k, e.target.value)} />
                    </label>
                  ))}
                </div>
              </div>
              <div className="md:col-span-2 flex flex-wrap items-center justify-between gap-3 text-xs text-stone-700">
                <label className="flex items-center gap-2">
                  <input type="checkbox" checked={remember} onChange={e => setRemember(e.target.checked)} />
                  Auf diesem Gerät merken (nur in diesem Browser gespeichert)
                </label>
                <button onClick={clearAll} className="underline text-red-700">Alle Zugangsdaten löschen</button>
              </div>
              <p className="md:col-span-2 text-xs text-stone-600">Die Keys gehen nur beim Start eines Laufs an dein Backend und von dort direkt an den jeweiligen Anbieter. Das Backend speichert sie nicht.</p>
            </div>
          )}
        </section>

        <section className="bg-[#1C2024] text-stone-100 rounded-lg p-4 md:p-5 mb-6 grid gap-4 md:grid-cols-[1fr_200px_130px_auto] items-end">
          <label className="block text-sm">{tab === 'content' ? 'Thema oder Kanal' : tab === 'studio' ? 'Nische oder Marke' : 'Nische'}
            <input className={`${field} mt-1 text-stone-900`} value={category} onChange={e => setCategory(e.target.value)} disabled={running} />
          </label>
          <label className="block text-sm">LLM-Anbieter
            <select className={`${field} mt-1 text-stone-900`} value={provider} onChange={e => setProvider(e.target.value)} disabled={running}>
              {PROVIDERS.map(([v, l]) => <option key={v} value={v}>{l}{cfg.llm[v]?.key ? ' ✓' : ''}</option>)}
            </select>
          </label>
          {tab === 'factory' ? (
          <label className="block text-sm">Bilder pro Produkt
            <select className={`${field} mt-1 text-stone-900`} value={count} onChange={e => setCount(Number(e.target.value))} disabled={running}>
              {[1, 2, 3, 4, 5].map(n => <option key={n} value={n}>{n}</option>)}
            </select>
          </label>
          ) : (
          <label className="block text-sm">{tab === 'content' ? 'Thumbnail-Varianten' : 'Logo-Varianten'}
            <select className={`${field} mt-1 text-stone-900`} value={variants} onChange={e => setVariants(Number(e.target.value))} disabled={running}>
              {[1, 2, 3].map(n => <option key={n} value={n}>{n}</option>)}
            </select>
          </label>
          )}
          <button onClick={start} disabled={!connected || running || missing.length > 0}
            title={startBlockers.length ? startBlockers.join(' · ') : 'Startet die gewählte Produktion'}
            className="display font-bold bg-[#E8590C] hover:bg-[#F76707] disabled:bg-stone-600 disabled:text-stone-400 text-white rounded px-6 py-2.5 focus:outline focus:outline-2 focus:outline-offset-2 focus:outline-white">
            {running ? 'Läuft…' : tab === 'content' ? 'Content erzeugen' : tab === 'studio' ? 'Studio starten' : 'Produktion starten'}
          </button>
          <div className={`md:col-span-4 rounded p-3 text-sm ${startBlockers.length ? 'border border-amber-500 bg-amber-50 text-stone-900' : 'border border-emerald-700 bg-emerald-50 text-stone-900'}`} role="status" aria-live="polite">
            <p className="font-semibold">{running ? 'Produktion läuft' : startBlockers.length ? 'Noch nicht startbereit – deshalb ist der Startknopf gesperrt' : 'Startbereit'}</p>
            {startBlockers.length ? (
              <ul className="list-disc pl-5 mt-1 space-y-1">
                {startBlockers.map((reason, i) => <li key={`${reason}-${i}`}>{reason}</li>)}
              </ul>
            ) : <p className="mt-1">Textanbieter: {PROVIDERS.find(p => p[0] === provider)?.[1]} · Bildanbieter: {imgDef.label.split(' (')[0]}. Wenn der Anbieter das Kontingent überschritten hat oder den Key ablehnt, erscheint die genaue Fehlermeldung im Laufprotokoll.</p>}
            {!connected && <p className="mt-1">Hinweis: Der Backend-Status wird über die WebSocket-Verbindung erkannt. Prüfe die Backend-Konsole und die Adresse in der Browserzeile.</p>}
          </div>
          <div className="md:col-span-4 border border-stone-600 rounded p-3 text-sm">
            <div className="flex flex-wrap items-center gap-3">
              <label className="font-medium">Referenzbild (optional)
                <input type="file" accept="image/png,image/jpeg,image/webp" onChange={onRefFile} disabled={running} className="block mt-1 text-xs" />
              </label>
              {ref && (
                <>
                  <img src={ref.dataUrl} alt="Dein Referenzbild" className="w-14 h-14 object-cover rounded border border-stone-500" />
                  <button type="button" onClick={() => setRef(null)} disabled={running} className="text-xs underline text-stone-300">Entfernen</button>
                  <label className="md:ml-auto">So nutzen
                    <select className={`${field} mt-1 text-stone-900`} value={refMode} onChange={e => setRefMode(e.target.value)} disabled={running}>
                      <option value="style">Stil übernehmen (KI beschreibt das Bild, neue Motive)</option>
                      {tab === 'content' && <option value="asset">Bild als Charakter und Emblem einsetzen</option>}<option value="direct">Bild direkt als Vorlage / Basis (Bild-zu-Bild)</option>
                    </select>
                  </label>
                </>
              )}
            </div>
            <p className="text-xs text-stone-400 mt-2">
              {!ref ? 'Gib ein eigenes Bild vor, an dessen Stil sich alle Motive orientieren sollen.'
                : refMode === 'style' ? 'Braucht bei deinem Text-Anbieter ein Modell mit Bildverständnis (Vision). Funktioniert mit jedem Bildanbieter.'
                : refMode === 'asset' ? 'Dein Bild wird freigestellt (klappt bei einfarbigem Hintergrund) und als Charakter in den Thumbnails sowie als Emblem im Streamer-Paket und in den Bannern eingesetzt.'
                : 'Geht nur mit den Bildanbietern Gemini, OpenAI und Lokal (Stable Diffusion WebUI).'}
            </p>
          </div>
          {tab === 'factory' ? (
            <div className="md:col-span-4 space-y-2">
          <label className="flex items-center gap-2 text-sm text-stone-300">
            <input type="checkbox" checked={publish} onChange={e => setPublish(e.target.checked)} disabled={running} />
            Entwurf bei Etsy anlegen (ohne Haken entsteht nur das Listing hier in der App, Etsy-Angaben sind dann nicht nötig)
          </label>
              <label className="flex items-center gap-2 text-sm text-stone-300">
                <input type="checkbox" checked={withMockups} onChange={e => setWithMockups(e.target.checked)} disabled={running} />
                Mockups dazu (Poster und Handy-Display), bei Etsy als erste Vorschaubilder
              </label>
              <label className="flex items-center gap-2 text-sm text-stone-300">
                <input type="checkbox" checked={shopifyOn} onChange={e => setShopifyOn(e.target.checked)} disabled={running} />
                Entwurf bei Shopify anlegen (Zugangsdaten unter "Deine Zugangsdaten")
              </label>
            </div>
          ) : tab === 'content' ? (
            <div className="md:col-span-4 space-y-3 text-sm text-stone-300">
              <div className="grid gap-3 md:grid-cols-[1fr_200px]">
                <label className="block">Vibe oder Stil-Hinweis (optional)
                  <input className={`${field} mt-1 text-stone-900`} value={hint} onChange={e => setHint(e.target.value)} disabled={running} placeholder="z. B. düster, episch, Retro-Neon" />
                </label>
                <label className="block">Sprache der Texte
                  <select className={`${field} mt-1 text-stone-900`} value={lang} onChange={e => setLang(e.target.value)} disabled={running}>
                    <option>Deutsch</option><option>Englisch</option>
                  </select>
                </label>
              </div>
              {CONTENT_MODULES.map(([k, l]) => (
                <div key={k}>
                  <label className="flex items-center gap-2">
                    <input type="checkbox" checked={cModules[k]} onChange={e => setCModules(m => ({ ...m, [k]: e.target.checked }))} disabled={running} />{l}
                  </label>
                  {k === 'thumbnails' && cModules.thumbnails && (
                    <div className="pl-6 mt-1 flex flex-wrap gap-4 text-xs">
                      {FORMAT_LIST.map(([f, fl]) => <label key={f} className="flex items-center gap-1"><input type="checkbox" checked={formats[f]} onChange={e => setFormats(m => ({ ...m, [f]: e.target.checked }))} disabled={running} />{fl}</label>)}
                    </div>
                  )}
                  {k === 'banners' && cModules.banners && (
                    <div className="pl-6 mt-1 flex flex-wrap gap-4 text-xs">
                      {BANNER_LIST.map(([f, fl]) => <label key={f} className="flex items-center gap-1"><input type="checkbox" checked={bannerTargets[f]} onChange={e => setBannerTargets(m => ({ ...m, [f]: e.target.checked }))} disabled={running} />{fl}</label>)}
                    </div>
                  )}
                </div>
              ))}
              <p className="text-xs text-stone-400">Text und Layout setzt die App selbst, die Bild-KI malt nur Hintergrund, Charakter und Emblem. Alles gibt es als ZIP. Mit Pollinations dauert es wegen der Wartezeiten länger, der Testmodus ist sofort fertig.</p>
            </div>
          ) : (
            <div className="md:col-span-4 space-y-2 text-sm text-stone-300">
              {MODULES.map(([k, l]) => (
                <label key={k} className="flex items-center gap-2">
                  <input type="checkbox" checked={modules[k]} onChange={e => setModules(m => ({ ...m, [k]: e.target.checked }))} disabled={running} />{l}
                </label>
              ))}
              <label className="flex items-center gap-2">
                <input type="checkbox" checked={shopifyOn} onChange={e => setShopifyOn(e.target.checked)} disabled={running} />
                Entwürfe bei Shopify anlegen (T-Shirt, Tasse, Handyhülle, Poster, je mit Mockups)
              </label>
              <p className="text-xs text-stone-400">Das Studio erzeugt ein Paket zum Herunterladen (ZIP). Bei Etsy lädt das Studio nichts hoch. Mit Pollinations dauert es wegen der Wartezeiten länger, der Testmodus ist sofort fertig.</p>
            </div>
          )}
        </section>

        <div className="grid lg:grid-cols-[1fr_380px] gap-6">
          <div className="space-y-6 min-w-0">
            <div className="grid sm:grid-cols-3 gap-3">
              {Object.entries(STATIONS).filter(([k]) => TABS[tab].includes(k)).map(([k, s]) => {
                const st = stations[k], style = STATE[st.status];
                return (
                  <div key={k} className={`border-2 rounded-lg p-4 min-h-[128px] ${style.card}`}>
                    <div className="flex items-center justify-between">
                      <h3 className="display font-bold">{s.name}</h3>
                      <span className="flex items-center gap-1.5 text-xs"><i className={`w-2.5 h-2.5 rounded-full ${style.dot}`} />{style.text}</span>
                    </div>
                    <p className="text-xs text-stone-500 mt-1">{s.job}</p>
                    <p className={`text-xs mt-3 break-words ${st.status === 'error' ? 'text-red-700' : 'text-stone-800'}`}>{st.message}</p>
                  </div>
                );
              })}
            </div>

            <div className="bg-white border border-stone-400 rounded-lg">
              <div className="flex items-center justify-between px-4 pt-3 pb-2">
                <h2 className="display font-bold text-sm">Protokoll</h2>
                <button onClick={() => setLogs([])} disabled={logs.length === 0}
                  className="text-xs border border-stone-500 rounded px-2 py-1 hover:bg-stone-100 disabled:opacity-40 focus:outline focus:outline-2 focus:outline-[#E8590C]">
                  Protokoll leeren
                </button>
              </div>
              <div className="h-52 overflow-y-auto px-4 pb-3 space-y-1 text-xs" role="log">
                {logs.length === 0 && <p className="text-stone-500">Noch keine Einträge. Starte eine Produktion.</p>}
                {logs.map((l, i) => (
                  <p key={i} className={l.error ? 'text-red-700' : ''}>
                    <span className="text-stone-500">{l.t}</span> <b>{l.source}:</b> {l.text}
                  </p>
                ))}
                <div ref={logEnd} />
              </div>
            </div>
          </div>

          {tab === 'content' ? (
            <aside className="bg-white border border-stone-400 rounded-lg p-4 min-w-0">
              <ContentResults results={contents} selectedId={contentId} onSelect={setContentId} api={API} />
            </aside>
          ) : tab === 'studio' ? (
            <aside className="bg-white border border-stone-400 rounded-lg p-4 min-w-0">
              <StudioResults studios={studios} selectedId={studioId} onSelect={setStudioId} api={API} />
            </aside>
          ) : (
          <aside className="bg-white border border-stone-400 rounded-lg p-4 min-w-0">
            <h2 className="display font-bold mb-3">Produkte ({products.length})</h2>
            {productError && <p role="alert" className="text-xs text-red-700 mb-2">{productError}</p>}
            {products.length > 1 && (
              <div className="flex gap-2 overflow-x-auto pb-3 mb-3 border-b border-stone-300">
                {products.map(p => (
                  <button key={p.id} onClick={() => setSelectedId(p.id)} aria-label={p.title}
                    className={`shrink-0 rounded border-2 ${p.id === selectedId ? 'border-[#E8590C]' : 'border-transparent'}`}>
                    <img src={`${API_ORIGIN}${p.image_url}`} alt="" className="w-14 h-14 object-cover rounded" />
                  </button>
                ))}
              </div>
            )}
            {product ? (
              <div className="space-y-3 text-sm">
                <div className={`grid gap-2 ${(product.image_urls || []).length > 1 ? 'grid-cols-2' : 'grid-cols-1'}`}>
                  {(product.image_urls || [product.image_url]).map((u, i) => (
                    <a key={u} href={`${API_ORIGIN}${u}`} target="_blank" rel="noreferrer" aria-label={`Bild ${i + 1} groß öffnen`}>
                      <img src={`${API_ORIGIN}${u}`} alt={`${product.title}, Bild ${i + 1}`} className="w-full aspect-square object-cover rounded border border-stone-300" />
                    </a>
                  ))}
                </div>
                <p className="text-xs text-stone-500">{(product.image_urls || [product.image_url]).length} Bild(er) im Paket. Klick öffnet es groß.</p>
                {product.mockup_urls?.length > 0 && (
                  <div>
                    <p className="text-xs font-medium mb-1">Mockups</p>
                    <div className="grid grid-cols-2 gap-2">
                      {product.mockup_urls.map((u, i) => <Pic key={u} src={u} label={`Mockup ${i + 1}`} api={API} />)}
                    </div>
                  </div>
                )}
                {product.style_description && (
                  <details className="text-xs text-stone-700">
                    <summary className="cursor-pointer">Stil-Analyse deines Referenzbilds</summary>
                    <p className="mt-1">{product.style_description}</p>
                  </details>
                )}
                <h3 className="display font-bold leading-snug">{product.title}</h3>
                <p><b>{Number(product.price).toFixed(2)} EUR</b> <span className="text-stone-500">· {product.niche}</span></p>
                <p className="text-xs text-stone-700 max-h-28 overflow-y-auto whitespace-pre-line">{product.description}</p>
                <div className="flex flex-wrap gap-1">
                  {(product.tags || []).map(t => <span key={t} className="bg-stone-200 px-1.5 py-0.5 rounded text-xs">{t}</span>)}
                </div>
                <div className="flex gap-2 pt-1">
                  <button onClick={() => { setProductError(''); setEditingProduct(v => !v); }} className="border border-stone-400 rounded px-3 py-2 text-sm hover:bg-stone-100">{editingProduct ? 'Bearbeitung schließen' : 'Produkt bearbeiten'}</button>
                  <button onClick={removeProduct} className="border border-red-300 text-red-700 rounded px-3 py-2 text-sm hover:bg-red-50">Löschen</button>
                </div>
                {editingProduct && (
                  <div className="border border-stone-300 rounded-lg p-3 space-y-2">
                    <h4 className="font-bold">Produkt bearbeiten</h4>
                    <label className="block text-xs">Titel<input className={field} value={editDraft.title} maxLength={300} onChange={e => setEditDraft(d => ({ ...d, title: e.target.value }))} /></label>
                    <label className="block text-xs">Beschreibung<textarea className={field} rows={4} value={editDraft.description} onChange={e => setEditDraft(d => ({ ...d, description: e.target.value }))} /></label>
                    <label className="block text-xs">Preis (EUR)<input className={field} type="number" min="0" step="0.01" value={editDraft.price} onChange={e => setEditDraft(d => ({ ...d, price: e.target.value }))} /></label>
                    <label className="block text-xs">Nische<input className={field} value={editDraft.niche} maxLength={120} onChange={e => setEditDraft(d => ({ ...d, niche: e.target.value }))} /></label>
                    <label className="block text-xs">Tags (durch Kommas trennen)<input className={field} value={editDraft.tags} onChange={e => setEditDraft(d => ({ ...d, tags: e.target.value }))} /></label>
                    <button onClick={saveProductChanges} className="w-full bg-[#E8590C] text-white rounded px-3 py-2 text-sm font-semibold hover:bg-[#c84c0b]">Änderungen speichern</button>
                  </div>
                )}
                {product.etsy_url && <a href={product.etsy_url} target="_blank" rel="noreferrer" className="inline-block text-[#B34000] underline text-sm">Entwurf bei Etsy öffnen</a>}
                {product.etsy_error && <p className="text-xs text-red-700">Etsy-Fehler: {product.etsy_error}</p>}
                {product.shopify_url && <a href={product.shopify_url} target="_blank" rel="noreferrer" className="inline-block text-[#B34000] underline text-sm">Entwurf in Shopify öffnen</a>}
                {product.shopify_error && <p className="text-xs text-red-700">Shopify-Fehler: {product.shopify_error}</p>}
              </div>
            ) : (
              <p className="text-sm text-stone-500">Noch keine Produkte gespeichert. Starte einen Durchlauf, um das erste Produkt zu erzeugen.</p>
            )}
          </aside>
          )}
        </div>
        </>}
      </div>
    </div>
  );
}
