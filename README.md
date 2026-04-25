# Blender Data Queue Add-on

Dieses Blender-Add-on laedt Datensaetze nacheinander in Blender. Du pruefst oder
bearbeitest den aktuellen Datensatz und klickst danach `Save & Next`. Das Add-on
speichert den aktuellen Stand und laedt automatisch den naechsten Datensatz.

Der Fortschritt wird in einer State-Datei gespeichert. Dadurch kannst du Blender
schliessen und spaeter mit `Resume` weiterarbeiten.

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

Aktuell ist dieses Suchmuster im Skript eingestellt:

```text
<SynVA Root>/*/05_submeshes/vessel_submesh.obj
```

Im Blender-Panel musst du den Stern `*` nicht eintragen. Du waehlst nur den
Hauptordner aus, der die einzelnen Datensatzordner enthaelt.

Beispiel:

```text
SynVA Root:
C:/Users/Niklas/Desktop/synva_real_data/synva_real_data
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
- `Manifest CSV`: CSV-Datei, falls der automatische Scan deaktiviert ist.
- `Output Folder`: Zielordner fuer gespeicherte `.blend`-Dateien und Reports.

Neben den Pfadfeldern gibt es in Blender normalerweise ein kleines Ordner-Symbol.
Darueber kannst du den Pfad im Dateibrowser auswaehlen. Alternativ kannst du den
Pfad direkt in das Feld schreiben.

Wichtig:

- Bei `SynVA Root` nur den Hauptordner auswaehlen, nicht den `*`-Platzhalter.
- Bei `Output Folder` einen normalen Zielordner auswaehlen.
- Wenn `Output Folder` leer bleibt, waehlt das Add-on automatisch einen
  passenden Standardordner.

Fuer den aktuellen SynVA-Standardfall ist der automatische Output-Ordner:

```text
C:/Users/Niklas/Desktop/synva_real_data/synva_queue_output
```

## Workflow

1. `Use SynVA Folder Scan` aktiviert lassen, wenn du die SynVA-Ordnerstruktur
   verwenden willst.
2. Bei `SynVA Root` den Hauptordner auswaehlen.
3. `Output Folder` leer lassen oder selbst einen Zielordner waehlen.
4. `Load First` klicken, um neu zu starten.
5. Den geladenen Datensatz pruefen oder bearbeiten.
6. Optional `Review Status` und `Comment` setzen.
7. `Save & Next` klicken.

Wenn du spaeter weitermachen willst, nicht `Load First` klicken, sondern
`Resume`. `Load First` setzt die Queue wieder auf den Anfang.

## Ausgabe

Pro gespeichertem Datensatz schreibt das Add-on:

```text
<id>.blend
<id>.report.json
```

Zusatzlich wird eine State-Datei geschrieben, damit `Resume` funktioniert.

Im SynVA-Scan-Modus heisst sie:

```text
synva_vessel_submesh.queue_state.json
```

## Suchmuster im Skript anpassen

Wenn deine Datei nicht mehr unter `05_submeshes/vessel_submesh.obj` liegt, kannst
du das Suchmuster in `data_queue_addon.py` anpassen.

Relevant sind diese Zeilen am Anfang der Datei:

```python
SYNVA_DEFAULT_ROOT = r"C:\Users\Niklas\Desktop\synva_real_data\synva_real_data"
SYNVA_SUBMESH_RELATIVE_PATH = Path("05_submeshes") / "vessel_submesh.obj"
```

Beispiele:

```python
SYNVA_SUBMESH_RELATIVE_PATH = Path("mesh") / "model.obj"
```

```python
SYNVA_SUBMESH_RELATIVE_PATH = Path("exports") / "final.glb"
```

Nach einer Skriptaenderung das Add-on in Blender deaktivieren und wieder
aktivieren. Falls Blender die Aenderung nicht uebernimmt, Blender neu starten.

## Projektlogik anpassen

Diese Funktionen in `data_queue_addon.py` sind fuer eigene Logik gedacht:

- `import_dataset(filepath)`: Import fuer weitere Dateiformate ergaenzen.
- `run_checks()`: automatische Checks fuer Namen, Materialien, Mesh-Qualitaet,
  Annotationen oder andere Regeln ergaenzen.

Standardmaessig unterstuetzt der Import GLB/GLTF, FBX, OBJ, STL und USD.
