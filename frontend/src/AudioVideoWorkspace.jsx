import React, { useEffect, useState } from 'react';

const STORE = 'agent-factory.media.v1';
const defaults = {
  elevenlabsKey: '', voiceId: 'JBFqnCBsd6RMkjVDRZzb', speechModel: 'eleven_multilingual_v2',
  replicateKey: '', videoModel: 'minimax/video-01', duration: 5,
};
const field = 'w-full rounded border border-stone-300 bg-white px-3 py-2 text-sm focus:outline focus:outline-2 focus:outline-violet-500';
const button = 'rounded-lg bg-violet-600 px-4 py-2.5 font-semibold text-white hover:bg-violet-700 disabled:cursor-not-allowed disabled:opacity-50';

export default function AudioVideoWorkspace({ apiOrigin }) {
  const [cfg, setCfg] = useState(() => {
    try { return { ...defaults, ...JSON.parse(localStorage.getItem(STORE) || '{}') }; }
    catch { return defaults; }
  });
  const [mode, setMode] = useState('audio');
  const [speech, setSpeech] = useState('Hallo! Willkommen bei Agent Factory. Aus deiner Idee wird etwas Neues.');
  const [prompt, setPrompt] = useState('A tiny fantasy village in a lush green valley, cinematic camera movement, warm sunset, whimsical atmosphere');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);
  const [saved, setSaved] = useState(true);

  useEffect(() => {
    if (saved) localStorage.setItem(STORE, JSON.stringify(cfg));
  }, [cfg, saved]);

  const update = (key, value) => setCfg(prev => ({ ...prev, [key]: value }));
  const generate = async () => {
    setBusy(true); setError(''); setResult(null);
    try {
      const isAudio = mode === 'audio';
      const response = await fetch(`${apiOrigin}/api/media/${isAudio ? 'audio' : 'video'}`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(isAudio ? {
          api_key: cfg.elevenlabsKey, text: speech, voice_id: cfg.voiceId, model_id: cfg.speechModel,
        } : {
          api_key: cfg.replicateKey, prompt, model_slug: cfg.videoModel, duration_seconds: Number(cfg.duration),
        }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Die Generierung ist fehlgeschlagen.');
      setResult({ ...data, url: `${apiOrigin}${data.url}` });
    } catch (e) {
      setError(e.message || 'Verbindung zum Backend fehlgeschlagen.');
    } finally { setBusy(false); }
  };

  const keyReady = mode === 'audio' ? !!cfg.elevenlabsKey.trim() : !!cfg.replicateKey.trim();
  const inputReady = mode === 'audio' ? !!speech.trim() : !!prompt.trim() && !!cfg.videoModel.trim();
  return (
    <div className="mx-auto max-w-5xl space-y-5">
      <section className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-950 text-white shadow-xl">
        <div className="grid gap-4 p-6 md:grid-cols-[1.3fr_1fr] md:items-center">
          <div>
            <p className="mb-2 text-xs font-bold uppercase tracking-[.22em] text-violet-300">Neue Werkstatt</p>
            <h2 className="text-3xl font-black tracking-tight">Audio & Video</h2>
            <p className="mt-2 max-w-xl text-sm leading-6 text-slate-300">Mach aus deinem Text eine Stimme oder verwandle eine Szene in einen kurzen Videoclip. Deine API-Zugangsdaten werden lokal in diesem Browser gespeichert und für die Generierung an dein Backend gesendet.</p>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <button onClick={() => { setMode('audio'); setError(''); setResult(null); }} className={`rounded-xl border p-4 text-left transition ${mode === 'audio' ? 'border-violet-400 bg-violet-500/20' : 'border-slate-700 bg-slate-900'}`}>
              <span className="text-2xl">🎙️</span><span className="mt-2 block font-bold">Audio</span><span className="mt-1 block text-xs text-slate-300">Text zu Sprache</span>
            </button>
            <button onClick={() => { setMode('video'); setError(''); setResult(null); }} className={`rounded-xl border p-4 text-left transition ${mode === 'video' ? 'border-sky-400 bg-sky-500/20' : 'border-slate-700 bg-slate-900'}`}>
              <span className="text-2xl">🎬</span><span className="mt-2 block font-bold">Video</span><span className="mt-1 block text-xs text-slate-300">Text zu Clip</span>
            </button>
          </div>
        </div>
      </section>

      <div className="grid gap-5 lg:grid-cols-[1.15fr_.85fr]">
        <section className="space-y-4 rounded-2xl border border-stone-300 bg-white p-5">
          <div><h3 className="text-lg font-bold">{mode === 'audio' ? 'Was soll gesprochen werden?' : 'Welche Szene sollen wir animieren?'}</h3><p className="mt-1 text-sm text-stone-600">{mode === 'audio' ? 'Gut für Figurenstimmen, Intros, Erklärungen und Voice-over.' : 'Beschreibe Motiv, Bewegung, Kamera und Stimmung möglichst konkret.'}</p></div>
          {mode === 'audio' ? <>
            <label className="block text-sm font-semibold">Dein Text<textarea className={`${field} mt-1 min-h-40`} maxLength={5000} value={speech} onChange={e => setSpeech(e.target.value)} placeholder="Schreibe hier den Text für die Stimme…" /></label>
            <div className="grid gap-3 sm:grid-cols-2">
              <label className="block text-sm font-semibold">Voice-ID<input className={`${field} mt-1`} value={cfg.voiceId} onChange={e => update('voiceId', e.target.value)} /></label>
              <label className="block text-sm font-semibold">Sprachmodell<select className={`${field} mt-1`} value={cfg.speechModel} onChange={e => update('speechModel', e.target.value)}><option value="eleven_multilingual_v2">Multilingual v2</option><option value="eleven_turbo_v2_5">Turbo v2.5</option><option value="eleven_flash_v2_5">Flash v2.5</option></select></label>
            </div>
            <p className="text-xs text-stone-500">Die Voice-ID muss zu einer Stimme gehören, auf die dein ElevenLabs-Konto Zugriff hat.</p>
          </> : <>
            <label className="block text-sm font-semibold">Videoprompt<textarea className={`${field} mt-1 min-h-40`} maxLength={2000} value={prompt} onChange={e => setPrompt(e.target.value)} placeholder="Beschreibe die Szene und die Bewegung…" /></label>
            <div className="grid gap-3 sm:grid-cols-2">
              <label className="block text-sm font-semibold">Replicate-Modell<input className={`${field} mt-1`} value={cfg.videoModel} onChange={e => update('videoModel', e.target.value)} placeholder="anbieter/modell" /></label>
              <label className="block text-sm font-semibold">Länge<select className={`${field} mt-1`} value={cfg.duration} onChange={e => update('duration', Number(e.target.value))}><option value={3}>3 Sekunden</option><option value={5}>5 Sekunden</option><option value={8}>8 Sekunden</option><option value={10}>10 Sekunden</option></select></label>
            </div>
            <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs leading-5 text-amber-900">Wichtig: Nicht jedes Replicate-Modell verwendet dieselben Eingabefelder. Die erste Version sendet Prompt und Dauer; falls dein gewähltes Modell andere Parameter erwartet, zeigt es einen Anbieterfehler an. Videogenerierung kann kostenpflichtig sein.</div>
          </>}
          <button className={`${button} w-full`} disabled={busy || !keyReady || !inputReady} onClick={generate}>{busy ? 'Wird erzeugt …' : mode === 'audio' ? '🎙️ Sprache erzeugen' : '🎬 Video erzeugen'}</button>
          {!keyReady && <p className="text-sm text-amber-700">Trage rechts zuerst deinen API-Key ein, damit der Startknopf aktiv wird.</p>}
        </section>

        <section className="space-y-4 rounded-2xl border border-stone-300 bg-white p-5">
          <div><h3 className="text-lg font-bold">Anbieter einrichten</h3><p className="mt-1 text-sm text-stone-600">Bring deine eigenen Zugangsdaten mit (BYOK).</p></div>
          {mode === 'audio' ? <>
            <label className="block text-sm font-semibold">ElevenLabs API-Key<input className={`${field} mt-1`} type="password" autoComplete="off" value={cfg.elevenlabsKey} onChange={e => update('elevenlabsKey', e.target.value)} placeholder="xi-api-key …" /></label>
            <a className="inline-block text-sm font-semibold text-violet-700 underline" href="https://elevenlabs.io/app/settings/api-keys" target="_blank" rel="noreferrer">ElevenLabs API-Keys öffnen ↗</a>
            <p className="rounded-lg bg-stone-100 p-3 text-xs leading-5 text-stone-600">ElevenLabs kann je nach Konto, Stimme und Zeichenmenge Guthaben verbrauchen. Prüfe Kosten und Nutzungsrechte vor der Veröffentlichung.</p>
          </> : <>
            <label className="block text-sm font-semibold">Replicate API-Token<input className={`${field} mt-1`} type="password" autoComplete="off" value={cfg.replicateKey} onChange={e => update('replicateKey', e.target.value)} placeholder="r8_…" /></label>
            <a className="inline-block text-sm font-semibold text-violet-700 underline" href="https://replicate.com/account/api-tokens" target="_blank" rel="noreferrer">Replicate API-Tokens öffnen ↗</a>
            <p className="rounded-lg bg-stone-100 p-3 text-xs leading-5 text-stone-600">Modelle, Dauer und Preise unterscheiden sich. Prüfe auf der Replicate-Modellseite, ob dein Modell Prompt und duration unterstützt.</p>
          </>}
          <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={saved} onChange={e => setSaved(e.target.checked)} /> Zugangsdaten in diesem Browser merken</label>
          {!saved && <p className="text-xs text-stone-500">Die Schlüssel werden nicht mehr in localStorage aktualisiert; bereits gespeicherte Werte bleiben dort bis zum Löschen der Website-Daten.</p>}
        </section>
      </div>

      {(error || result) && <section className="rounded-2xl border border-stone-300 bg-white p-5">
        {error && <div role="alert" className="rounded-lg border border-red-300 bg-red-50 p-4 text-sm text-red-800"><strong>Das hat nicht geklappt.</strong><p className="mt-1">{error}</p></div>}
        {result && <div><div className="mb-3 flex items-center justify-between gap-3"><h3 className="text-lg font-bold">Fertig – dein Ergebnis</h3><a className="text-sm font-semibold text-violet-700 underline" href={result.url} download={result.filename}>Datei herunterladen ↗</a></div>
          {mode === 'audio' ? <audio className="w-full" controls src={result.url} /> : <video className="max-h-[520px] w-full rounded-xl bg-black" controls src={result.url} />}
          <p className="mt-2 text-xs text-stone-500">Gespeichert in der lokalen Agent-Factory-Asset-Bibliothek: {result.filename}</p>
        </div>}
      </section>}
      <p className="text-xs leading-5 text-stone-500">Diese Werkstatt ist eine erste Integration: Die API-Anbindungen sind vorbereitet, aber echte Generierung kann erst mit gültigen Schlüsseln und einem kompatiblen Modell live getestet werden. Die Dateien liegen lokal im Ausgabeordner des Backends.</p>
    </div>
  );
}
