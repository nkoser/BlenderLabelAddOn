# Blender Data Queue Add-on

This repository contains a small Blender add-on for reviewing datasets one by one.
It loads a queue from a CSV manifest, imports the current dataset, lets you review
or edit it in Blender, and then saves the result with `Save & Next`.

## Installation

1. Open Blender.
2. Go to `Edit > Preferences > Add-ons > Install...`.
3. Select `data_queue_addon.py` from this repository.
4. Enable `Data Queue Pipeline`.
5. In the 3D viewport, press `N` and open the `Data Queue` tab.

## Manifest

Create a CSV file with at least an `input_path` column. An `id` column is
recommended because it controls output file names.

```csv
id,input_path
item_001,C:/data/item_001.glb
item_002,C:/data/item_002.obj
item_003,C:/data/item_003.fbx
```

Relative `input_path` values are resolved relative to the manifest file.

## Workflow

1. Set `Manifest CSV`.
2. Set `Output Folder`, or leave it empty to use an `output` folder next to the
   manifest.
3. Click `Load First` for a fresh run, or `Resume` to continue from the state
   file.
4. Review and edit the imported dataset.
5. Choose a review status and optional comment.
6. Click `Save & Next`.

For every saved item, the add-on writes:

- `<id>.blend`
- `<id>.report.json`
- `<manifest name>.queue_state.json`

## Customization Points

Most project-specific behavior belongs in these functions in
`data_queue_addon.py`:

- `import_dataset(filepath)`: add support for custom data formats.
- `run_checks()`: add validation rules for mesh quality, naming, annotations,
  bounding boxes, required materials, cameras, or other project rules.

The default importer supports GLB/GLTF, FBX, OBJ, STL, and USD files.
