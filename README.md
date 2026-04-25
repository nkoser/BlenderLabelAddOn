# Blender Data Queue Add-on

Dieses Blender-Add-on laedt Datensaetze nacheinander in Blender. Du pruefst oder
bearbeitest den aktuellen Datensatz und klickst danach `Save & Next`. Das Add-on
exportiert den aktuellen Stand als `.obj` und laedt automatisch den naechsten
Datensatz.

Pro Datensatz wird nur eine OBJ-Datei exportiert. Zusaetzlich gibt es eine
Queue-State-Datei, damit `Resume` funktioniert. Es werden keine Report-JSONs,
Kommentare, Review-Status-Dateien oder `.blend`-Dateien geschrieben.

## Installation

1. Blender oeffnen.
2. `Edit > Preferences > Add-ons` oeffnen.
3. Je nach Blender-Version `Install...` oder `Install from Disk...` anklicken.
4. Diese Datei auswaehlen:

```text
C:/Users/Niklas/Desktop/BlenderLabelAddOn/data_queue_addon.py
```

5. Das Add-on `Data Queue Pipeline` aktivieren.
6. Im 3D Viewport `N` druecken.
7. Rechts den Tab `Data Queue` oeffnen.

## Zwei Arbeitsmodi

Das Add-on kann die Queue auf zwei Arten laden.

### 1. Ordner automatisch scannen

Dieser Modus ist fuer Ordnerstrukturen gedacht, bei denen jeder Datensatz in
einem eigenen Unterordner liegt und die relevante Datei immer denselben relativen
Pfad hat.

Das Suchmuster ist im Blender-Panel einstellbar. Der Standardwert ist:

```text
<SynVA Root>/*/05_submeshes/vessel_submesh.obj
```

Im Blender-Panel musst du den Stern `*` nicht eintragen. Du waehlst nur den
Hauptordner aus, der die einzelnen Datensatzordner enthaelt.

Beispiel:

```text
SynVA Root:
C:/Users/Niklas/Desktop/synva_real_data/synva_real_data

File Pattern:
*/05_submeshes/vessel_submesh.obj
```

Das Add-on sucht dann automatisch nach:

```text
C:/Users/Niklas/Desktop/synva_real_data/synva_real_data/<dataset>/05_submeshes/vessel_submesh.obj
```

Also zum Beispiel:

```text
C:/Users/Niklas/Desktop/synva_real_data/synva_real_data/aneux_ANSYS_UNIGE_09/05_submeshes/vessel_submesh.obj
```

### 2. CSV-Manifest verwenden

Wenn deine Dateien nicht alle nach demselben Muster liegen, kannst du
`Use SynVA Folder Scan` deaktivieren und eine CSV-Datei verwenden.

Beispiel:

```csv
id,input_path
item_001,C:/data/item_001.glb
item_002,C:/data/item_002.obj
item_003,C:/data/item_003.fbx
```

Die Spalte `input_path` ist Pflicht. Die Spalte `id` ist empfohlen, weil sie fuer
die Namen der gespeicherten Dateien verwendet wird. Relative Pfade werden relativ
zur CSV-Datei aufgeloest.

## Pfade im Blender-Panel auswaehlen

Im Tab `Data Queue` gibt es diese Felder:

- `Use SynVA Folder Scan`: aktiviert den automatischen Ordner-Scan.
- `SynVA Root`: Hauptordner, unter dem die Datensatzordner liegen.
- `File Pattern`: Suchmuster relativ zu `SynVA Root`.
- `Manifest CSV`: CSV-Datei, falls der automatische Scan deaktiviert ist.
- `Output Folder`: Zielordner fuer exportierte `.obj`-Dateien.

Neben den Pfadfeldern gibt es in Blender normalerweise ein kleines Ordner-Symbol.
Darueber kannst du den Pfad im Dateibrowser auswaehlen. Alternativ kannst du den
Pfad direkt in das Feld schreiben.

Wichtig:

- Bei `SynVA Root` nur den Hauptordner auswaehlen, nicht den `*`-Platzhalter.
- Bei `File Pattern` kommt der variable Dateiteil rein, zum Beispiel
  `*/05_submeshes/vessel_submesh.obj`.
- Bei `Output Folder` einen normalen Zielordner auswaehlen.
- Wenn `Output Folder` leer bleibt, waehlt das Add-on automatisch einen
  passenden Standardordner.

Fuer den aktuellen SynVA-Standardfall ist der automatische Output-Ordner:

```text
C:/Users/Niklas/Desktop/synva_real_data/synva_queue_output
```

Die Originaldateien im Eingabeordner werden dabei nicht ueberschrieben.

## Workflow

1. `Use SynVA Folder Scan` aktiviert lassen, wenn du die SynVA-Ordnerstruktur
   verwenden willst.
2. Bei `SynVA Root` den Hauptordner auswaehlen.
3. Bei `File Pattern` das Suchmuster eintragen.
4. `Output Folder` leer lassen oder selbst einen Zielordner waehlen.
5. `Load First` klicken, um neu zu starten.
6. Den geladenen Datensatz pruefen oder bearbeiten.
7. `Save & Next` klicken.

Wenn du spaeter weitermachen willst, `Resume` klicken. `Load First` setzt die
Queue wieder auf den Anfang.

## Ausgabe

Pro gespeichertem Datensatz schreibt das Add-on nur eine OBJ-Datei. Damit
gleichnamige Eingabedateien wie `vessel_submesh.obj` nicht kollidieren, wird pro
Datensatz ein Unterordner im Output-Ordner angelegt.

```text
<Output Folder>/<id>/<original-name>.obj
```

Zusaetzlich wird genau eine State-Datei fuer den Fortschritt geschrieben:

```text
<Output Folder>/synva_vessel_submesh.queue_state.json
```

## Suchmuster einstellen

Wenn deine Datei nicht mehr unter `05_submeshes/vessel_submesh.obj` liegt, kannst
du das Suchmuster direkt im Blender-Panel bei `File Pattern` anpassen.

Beispiele:

```text
*/05_submeshes/vessel_submesh.obj
```

```text
*/mesh/model.obj
```

```text
*/exports/final.glb
```

Wenn die Datei nicht nur in direkten Unterordnern liegen kann, kannst du `**`
verwenden:

```text
**/vessel_submesh.obj
```

Das verwendet Blenders/Pythons Glob-Syntax, keine vollstaendige Regex-Syntax.
`*` steht fuer einen Ordner- oder Dateinamen auf einer Ebene, `**` fuer beliebig
viele Unterordner.

Wenn du nur den Standardwert dauerhaft im Skript aendern willst, ist diese Zeile
am Anfang von `data_queue_addon.py` relevant:

```python
SYNVA_DEFAULT_FILE_PATTERN = "*/05_submeshes/vessel_submesh.obj"
```

## Projektlogik anpassen

Diese Funktionen in `data_queue_addon.py` sind fuer eigene Logik gedacht:

- `import_dataset(filepath)`: Import fuer weitere Dateiformate ergaenzen.
- `run_checks()`: automatische Checks fuer Namen, Materialien, Mesh-Qualitaet,
  Annotationen oder andere Regeln ergaenzen.

Standardmaessig unterstuetzt der Import GLB/GLTF, FBX, OBJ, STL und USD.
