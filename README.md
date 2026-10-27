# Agent Factory

Scout (Idee) → Designer (Bild via Stability) → Publisher (Listing + Etsy-Entwurf). LLM-Anbieter pro Lauf wählbar.

## Backend
    cd backend
    python -m venv .venv && source .venv/bin/activate
    pip install -r requirements.txt
        uvicorn main:app --reload --port 8000

## Frontend
    cd frontend
    npm install
    npm run dev

Danach öffnest du die Adresse, die im Terminal steht (meist http://localhost:5173).

## Keys (BYOK)
Keine Keys im Code oder in Dateien. Du trägst sie in der Oberfläche unter "Deine Zugangsdaten" ein:
Keys beliebig vieler KI-Anbieter (OpenAI, Anthropic, Groq, xAI, OpenRouter, Z.ai, Hugging Face oder ein eigener OpenAI-kompatibler Dienst), einen Bildanbieter (Pollinations ist kostenlos und braucht keinen Key) und optional die Etsy-Angaben.
Sie bleiben im Browser (localStorage, abschaltbar) und gehen nur beim Start eines Laufs ans Backend.

## Marketing-Studio
Der zweite Reiter erzeugt Merch-Designs (Front-Logo und Backprint mit entferntem Hintergrund), ein Brand-Kit (Logos, Hex-Farben, Schriftempfehlungen, Muster, Brand-Board) und Mockups. Alles gibt es als ZIP.
Mockups sind einfache, selbst gezeichnete Grafiken. Eigene Vorlagen legst du in `backend/mockup_templates/` ab (siehe die README dort).

## Content-Studio
Der dritte Reiter erzeugt Thumbnails (YouTube 16:9, Quadrat, Hochkant), ein Streamer-Paket (Szenen, Overlay, Chat-Box, Panels, Alerts) und Banner (YouTube, X, Discord, LinkedIn) im gleichen Look.
Die Bild-KI malt nur Hintergrund, Charakter und Emblem. Text und Layout setzt die App selbst mit Pillow und den mitgelieferten Schriften.
Mit einem eigenen Bild (Modus "als Charakter und Emblem einsetzen") nutzt die App dein Bild direkt statt eines erzeugten.

Schriften in `backend/assets/fonts/`: Anton, Bebas Neue, Russo One und Bangers, alle unter der SIL Open Font License 1.1 (Lizenztexte liegen daneben).

## Shopify
Produkte entstehen immer als **Entwurf**. Zugang: entweder Admin-API-Token einer älteren App oder Client-ID und Client-Secret einer App aus dem Dev Dashboard (nur wenn App und Shop zur selben Organisation gehören).
Die App braucht die Berechtigungen `write_products` und `write_files` und muss im Shop installiert sein. Die API-Version steht im Feld (leer = 2026-04).
Der Download selbst (bei digitalen Produkten) und die Produktion (bei Merch) kommen nicht über diese Schnittstelle, dafür brauchst du eine passende Shopify-App.

## Hinweise
- Starte das Frontend nur mit `npm run dev`, ohne Kommentar dahinter.
- Ohne Haken bei "Entwurf bei Etsy anlegen" brauchst du keine Etsy-Angaben.
- Modellnamen kannst du in der Oberfläche überschreiben.

## Produktverwaltung (SQLite + CRUD)

Generierte Produkte werden automatisch in `backend/agent_factory.sqlite3` gespeichert und bleiben nach einem Neustart erhalten. Die React-Oberfläche lädt gespeicherte Produkte beim Öffnen und bietet Bearbeiten sowie Löschen an.

REST-Endpunkte:
- `GET /api/products` – Liste aller Produkte
- `POST /api/products` – Produkt manuell anlegen (JSON: `title`, optional `description`, `price`, `niche`, `tags`)
- `GET /api/products/{id}` – einzelnes Produkt
- `PUT /api/products/{id}` – Metadaten bearbeiten (`title`, `description`, `price`, `niche`, `tags`)
- `DELETE /api/products/{id}` – Produkt löschen

Die Agenten-Pipeline erstellt Produkte weiterhin über den vorhandenen WebSocket-Workflow; das Backend speichert `PRODUCT_CREATED` automatisch vor dem Senden an den Browser.

Optional kann der Datenbankpfad über `AGENT_FACTORY_DB` gesetzt werden. Tests für den Speicher: `cd backend && python -m unittest test_product_store.py`.

## Storytelling: Character Studio & Story Panel Agent

Neuer Tab **Storytelling** für dauerhaft gespeicherte Charakterprofile und Comic-/Webtoon-Geschichten. Charaktere und Geschichten liegen in derselben SQLite-Datei wie die Produkte (`backend/agent_factory.sqlite3`, oder der Pfad aus `AGENT_FACTORY_DB`). Die API bietet `/api/story/characters` (GET/POST), `/api/story/characters/{id}` (PUT/DELETE), `/api/story/stories` (GET/POST) und `/api/story/stories/{id}` (GET/DELETE).

Eine Geschichte erstellt 1–12 Panels mit konsistentem Charakter-Steckbrief und kopierbaren Bildprompts. Optional werden die Panels über die bereits integrierten Bildanbieter erzeugt. Wähle dafür im Storytelling-Tab einen Anbieter und gib nötige Zugangsdaten ein; Zugangsdaten werden nicht in den Story-Datensätzen gespeichert. Der lokale Testmodus erzeugt nur Platzhalterbilder, keine fertige Illustration. Gleiche Steckbriefe/Stilprompts verbessern die Kontinuität, garantieren aber keine identischen Gesichter zwischen generierten Bildern.

Für einen gespeicherten Charakter kannst du außerdem **Vier Emotionsporträts erzeugen** auswählen: neutral, wütend, glücklich und überrascht. Die Bilddateien werden im bestehenden `backend/output/assets`-Ordner abgelegt und ihre URLs im Charakterprofil gespeichert. Die Identität wird über dieselbe Beschreibung und feste Kontinuitätsregeln angeleitet; Bildmodelle können dennoch kleine Abweichungen erzeugen.

## Game Assets: PixelLab

Der separate Tab **Game Assets** nutzt PixelLab v2 für einzelne Pixel-Art-Bilder. Er ist absichtlich getrennt vom Storytelling-Tab: Anime-Porträts und Webtoon-Panels verwenden weiterhin die bisherigen Bildanbieter.

1. Lege ein PixelLab-Konto an und kopiere deinen API-Token aus den PixelLab-Kontoeinstellungen.
2. Öffne **Game Assets**, füge den Token ein und beschreibe das gewünschte Sprite/Objekt.
3. Die generierte PNG-Datei wird in `backend/output/assets/` abgelegt; Metadaten und Prompt landen in der SQLite-Tabelle `game_assets`.

Der Token wird für die jeweilige Generierungsanfrage an das Backend gesendet und nicht in der Datenbank gespeichert. Die Oberfläche speichert ihn nicht dauerhaft. PixelLab kann je nach Konto und Endpunkt Credits verbrauchen; die Kosten/Verfügbarkeit bitte vor der Generierung im eigenen PixelLab-Konto prüfen. Diese erste Integration verwendet den schnellen Endpunkt für einzelne Bilder; separate Spezial-Workflows für komplette Animationen und verbundene Tilesets sind noch nicht angebunden.

API: `GET /api/game-assets`, `POST /api/game-assets/generate`, `DELETE /api/game-assets/{id}`. Mock-basierte Tests: `cd backend && python -m unittest test_pixellab.py`.


## Bildvorlagen und Referenzbilder

- In der Produktion, im Studio und bei Thumbnails/Streamer-Paketen/Bannern kannst du ein PNG-, JPEG- oder WebP-Bild als Stilreferenz, freigestellten Charakter/Emblem oder direkte Bildbasis hochladen. Für direkte Bild-zu-Bild-Bearbeitung muss Gemini, OpenAI Bilder oder die lokale Stable-Diffusion-WebUI gewählt sein.
- Im Character Studio kannst du eine Vorlage am Charakterprofil speichern und für Emotionsporträts verwenden. Für Story-Panels kannst du zusätzlich eine Vorlage für die gesamte Geschichte setzen. Direkte Vorlagen werden mit Gemini, OpenAI Bilder oder lokaler Stable Diffusion an den Bildanbieter übergeben.
- Im Bereich Game Assets kannst du ein Basisbild für PixelLab hochladen. Mit Vorlage nutzt die Integration PixelLabs Image-to-Pixel-Art-Endpunkt; ohne Vorlage bleibt es bei der schnellen Text-zu-Pixel-Art-Generierung.
- Uploads werden im Browser auf maximal 1024 Pixel Kantenlänge verkleinert; erlaubte Eingabeformate sind PNG/JPEG/WebP und die Dateigröße ist auf 6 MB begrenzt. Bildvorlagen werden nur an den jeweils verwendeten Anbieter gesendet, wenn dessen API eine Referenzbild-Eingabe unterstützt.


## Startknopf und Fehlersuche

Wenn der Startknopf gesperrt ist, zeigt die Statusbox darunter jetzt die konkreten Gründe (z. B. fehlender Text-Key, Bildanbieter-Pflichtfelder, fehlendes Modul/Format oder Backend-Verbindung). Die ausgewählten Text- und Bildanbieter werden getrennt konfiguriert. Ein Key für einen Anbieter gilt nicht automatisch für einen anderen.

Eine ausführlichere deutsche Schritt-für-Schritt-Anleitung steht in [`BEDIENUNGSANLEITUNG.md`](./BEDIENUNGSANLEITUNG.md).

## Audio & Video (neue Werkstatt)

Im Frontend-Menü **Audio & Video** sind optionale BYOK-Integrationen für Text-zu-Sprache über ElevenLabs und Text-zu-Video über Replicate verfügbar. Die API-Schlüssel werden pro Anfrage ans Backend übergeben; generierte MP3/MP4-Dateien werden lokal unter `backend/output/assets/` gespeichert. Die Video-Integration sendet `prompt` und `duration` an das gewählte Replicate-Modell; prüfe dessen Modellkarte und Kosten, da nicht jedes Modell dieselben Eingaben unterstützt. Details und Setup: `BEDIENUNGSANLEITUNG.md`. Live-Provider wurden ohne Nutzer-API-Keys nicht getestet.
