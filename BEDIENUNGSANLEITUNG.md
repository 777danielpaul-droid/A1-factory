# Agent Factory – Bedienungsanleitung

## 1. Starten (macOS)

Du brauchst Python 3 und Node.js (empfohlen: aktuelle LTS-Version).

1. ZIP entpacken und den Ordner `agent-factory` öffnen.
2. Terminal-Fenster 1:
   ```bash
   cd agent-factory/backend
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   uvicorn main:app --reload --port 8000
   ```
3. Terminal-Fenster 2:
   ```bash
   cd agent-factory/frontend
   npm install
   npm run dev
   ```
4. Die im Frontend-Terminal angezeigte lokale Adresse öffnen (meist `http://localhost:5173`). Beide Terminals geöffnet lassen.

## 2. Zugangsdaten einrichten

Öffne oben **Deine Zugangsdaten**. Wähle später beim Start den Textanbieter und hier den Bildanbieter aus. Ein Anbieter braucht normalerweise einen eigenen API-Key; ein Key von Grok funktioniert zum Beispiel nicht automatisch bei OpenAI.

### Text-/LLM-Anbieter

- Wähle den Anbieter, für den du einen gültigen API-Key hast.
- Trage den Key in dessen Feld ein.
- Optional kannst du den Modellnamen ändern. Lass ihn zunächst leer, wenn die Oberfläche einen Standard verwendet.
- Bei **Eigener Anbieter** sind Base-URL und Modellname Pflicht; der Key kann je nach Dienst optional sein.

### Bildanbieter

- **Pollinations:** kostenloser Einstieg, kein Key nötig. Kann gedrosselt oder zeitweise überlastet sein.
- **Testmodus: Platzhalter-Bild:** erzeugt nur ein Testbild mit Prompttext, keine fertige KI-Illustration.
- **Cloudflare:** Account-ID und API-Token mit Workers-AI-Berechtigung.
- **Hugging Face:** Token mit Berechtigung für Inference Providers; gegebenenfalls Guthaben nötig.
- **Gemini, OpenAI, Stability AI, Together AI:** Key des jeweiligen Dienstes; je nach Anbieter Modell-, Kontingent- oder Kostenbeschränkungen beachten.
- **Lokal:** Stable Diffusion WebUI muss laufen und mit `--api` gestartet sein; die URL ist häufig `http://127.0.0.1:7860`.

Die Hinweise direkt unter der Auswahl nennen Pflichtfelder. Die neue Statusanzeige am Startknopf zeigt ebenfalls, was noch fehlt und warum der Start gesperrt ist. Eine vollständige Konfiguration garantiert nicht, dass ein externer Anbieter gerade verfügbar ist; API-Fehler erscheinen im Laufprotokoll.

Mit **Auf diesem Gerät merken** bleiben Zugangsdaten im lokalen Browser gespeichert. Auf einem gemeinsam genutzten Gerät besser ausgeschaltet lassen. **Alle Zugangsdaten löschen** entfernt die gespeicherten App-Einstellungen aus diesem Browser. Keys werden beim Start eines Laufs an das Backend übermittelt und von dort an den gewählten Dienst weitergereicht.

## 3. Content erstellen

1. Oben den gewünschten Bereich wählen: Produktion, Marketing-Studio, Content-Studio, Storytelling oder Game Assets.
2. Im Content-Studio mindestens ein Modul aktiv lassen: Thumbnails, Streamer-Paket oder Banner. Bei Thumbnails mindestens ein Format wählen; bei Bannern mindestens eine Zielplattform.
3. Thema/Kanal ausfüllen und beim Start den Textanbieter wählen. In **Deine Zugangsdaten** den Bildanbieter wählen.
4. Optional Stil/Vibe und Sprache einstellen.
5. Auf **Content erzeugen** klicken. Ergebnisse und Fehlermeldungen erscheinen im Laufprotokoll und in der Ergebnisansicht.

## 4. Referenzbild verwenden

Im Startbereich kannst du PNG, JPEG oder WebP hochladen.

- **Stil übernehmen:** Die Text-KI beschreibt den Stil, danach werden neue Motive erstellt. Dafür braucht der Textanbieter ein Modell mit Bildverständnis (Vision).
- **Als Charakter und Emblem einsetzen:** In unterstützten Content-Bereichen wird das Bild als Charakter/Emblem verwendet; das Freistellen funktioniert am besten bei einfachem, einfarbigem Hintergrund.
- **Direkt als Vorlage/Basis:** Bild-zu-Bild; nur mit Gemini, OpenAI Bilder oder der lokalen Stable-Diffusion-WebUI.

Ein Referenzbild wird nicht zwangsläufig von jedem Modell gleich unterstützt. Es wird an den jeweils genutzten Dienst übermittelt, wenn der gewählte Ablauf es verwendet.

## 5. Shopify und Etsy

Shopify- und Etsy-Zugangsdaten sind nur erforderlich, wenn du einen Entwurf beim jeweiligen Dienst anlegen möchtest. Ohne aktivierte Veröffentlichung kannst du Ergebnisse zunächst nur in der App erzeugen. Shopify-Produkte werden als Entwürfe angelegt. Prüfe vor dem Veröffentlichen immer Bilder, Texte, Preise, Nutzungsrechte und Zugangsdaten.

## 6. Häufige Probleme

- **Startknopf grau:** Lies die gelbe Statusbox unter dem Knopf. Sie listet fehlende Keys, Pflichtfelder, Module/Formate oder eine fehlende Backend-Verbindung auf.
- **Backend nicht verbunden:** Backend-Terminal prüfen; es muss `uvicorn` auf Port 8000 laufen. Seite neu laden. Wenn du eine andere Adresse nutzt, prüfe `VITE_API_URL` und die Backend-Adresse.
- **401/403:** Key falsch, abgelaufen oder ohne nötige Berechtigung.
- **402/429:** Guthaben/Kontingent aufgebraucht oder Anfrage gedrosselt. Anbieter-Dashboard prüfen oder später erneut versuchen.
- **Kein Bild / Bildantwort unlesbar:** Modellname, Anbieterstatus und Laufprotokoll prüfen. Manche Anbieter bieten nicht jedem Konto Bildgenerierung an.
- **Referenzbild wird abgelehnt:** Für direkte Bild-zu-Bild-Bearbeitung einen unterstützten Bildanbieter auswählen oder den Modus auf Stilübernahme ändern.
- **Text-KI kann Referenzbild nicht lesen:** Ein Vision-fähiges Modell verwenden oder das Referenzbild entfernen.

## 7. Wichtige Hinweise

Die App ist ein Prototyp, keine Garantie für fehlerfreie Ergebnisse oder dauerhafte Verfügbarkeit externer APIs. Preise, Gratis-Kontingente, Modellnamen und Nutzungsrechte ändern sich. Prüfe die aktuellen Bedingungen beim jeweiligen Anbieter, bevor du Bilder kommerziell verwendest. Erzeuge zuerst einen kleinen Testlauf.

## 8. Neue Werkstatt: Audio & Video

Im oberen Menü findest du **Audio & Video**. Die erste Integration enthält zwei echte externe Anbieter-Anbindungen. Für beide brauchst du einen eigenen Account und API-Zugang; Generierung kann kostenpflichtig sein.

### Audio – Text zu Sprache

1. Öffne **Audio & Video → Audio**.
2. Erstelle bei [ElevenLabs](https://elevenlabs.io/app/settings/api-keys) einen API-Key und füge ihn im Feld **ElevenLabs API-Key** ein.
3. Trage den gewünschten Text ein. Du kannst das Sprachmodell auswählen und eine Voice-ID eintragen, auf die dein Konto Zugriff hat.
4. Klicke **Sprache erzeugen**. Wenn es klappt, erscheint ein Audioplayer; über **Datei herunterladen** speicherst du die MP3.

### Video – Text zu Clip

1. Öffne **Audio & Video → Video**.
2. Erstelle bei [Replicate](https://replicate.com/account/api-tokens) einen API-Token und füge ihn ein.
3. Beschreibe die Szene, Bewegung und Kameraführung. Das Modell-Feld erwartet einen Modellnamen im Format `anbieter/modell`; voreingestellt ist `minimax/video-01`.
4. Wähle eine Dauer zwischen 3 und 10 Sekunden und klicke **Video erzeugen**. Wenn das Modell erfolgreich fertig wird, erscheint der Clip im Player und kann als MP4 heruntergeladen werden.

**Wichtig für Video:** Replicate-Modelle haben unterschiedliche Eingabeparameter. Diese erste Version sendet `prompt` und `duration`. Wenn ein Modell andere Felder verlangt oder keine Dauer unterstützt, zeigt Agent Factory einen Fehler des Anbieters an. Prüfe vor dem Start die Modellbeschreibung und Preise auf Replicate.

### Wo liegen die Dateien?

Generierte MP3- und MP4-Dateien werden im lokalen Backend unter `backend/output/assets/` gespeichert und über die lokale App bereitgestellt. Sie bleiben dort, bis du sie selbst entfernst. Die Zugangsdaten werden standardmäßig in `localStorage` dieses Browsers gemerkt. Auf gemeinsam genutzten Geräten solltest du das deaktivieren und alte Website-Daten gegebenenfalls manuell löschen.

### Audio/Video: Fehler beheben

- **Startknopf deaktiviert:** API-Key und Text bzw. Prompt prüfen.
- **401/403:** API-Key ungültig oder ohne Berechtigung.
- **402/429:** Kontingent, Tarif oder Rate-Limit prüfen.
- **Modellfehler bei Video:** Modellname und dessen unterstützte Eingabefelder auf Replicate prüfen. Nicht jedes Modell akzeptiert `duration`.
- **Zeitüberschreitung:** Lange Videogenerierungen können länger als der aktuelle Request-Zeitraum dauern; prüfe den Modellstatus beim Anbieter und starte gegebenenfalls erneut.

Die Audio- und Video-Endpunkte sind mit lokalen Validierungstests geprüft. Eine Live-Generierung wurde nicht durchgeführt, da dafür persönliche API-Keys und ein kostenpflichtiger bzw. verfügbarer Anbieterzugang nötig sind.
