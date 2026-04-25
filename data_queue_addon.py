bl_info = {
    "name": "Data Queue Pipeline",
    "author": "Pipeline Helper",
    "version": (0, 3, 1),
    "blender": (3, 6, 0),
    "location": "View3D > Sidebar > Data Queue",
    "description": "Load datasets one by one, export edited OBJ files, and continue",
    "category": "Pipeline",
}

import csv
import json
from pathlib import Path

import bpy
from bpy.props import BoolProperty, IntProperty, PointerProperty, StringProperty
from bpy.types import Operator, Panel, PropertyGroup


SYNVA_DEFAULT_ROOT = r"C:\Users\Niklas\Desktop\synva_real_data\synva_real_data"
SYNVA_DEFAULT_FILE_PATTERN = "*/05_submeshes/vessel_submesh.obj"
SYNVA_STATE_FILENAME = "synva_vessel_submesh.queue_state.json"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def abspath(path):
    return Path(bpy.path.abspath(path)).expanduser()


def get_settings(context):
    return context.scene.data_queue_settings


def item_id_from_match(root, input_path):
    relative_parts = input_path.relative_to(root).parts
    if len(relative_parts) > 1:
        return relative_parts[0]

    return input_path.stem


def scan_synva_rows(settings):
    root = abspath(settings.synva_root)
    file_pattern = settings.synva_file_pattern.strip().replace("\\", "/")

    if not root.exists():
        raise FileNotFoundError("SynVA root not found: {}".format(root))

    if not root.is_dir():
        raise NotADirectoryError("SynVA root is not a folder: {}".format(root))

    if not file_pattern:
        raise ValueError("Set a file pattern, for example: {}".format(SYNVA_DEFAULT_FILE_PATTERN))

    rows = []
    seen_ids = {}

    for input_path in sorted(path for path in root.glob(file_pattern) if path.is_file()):
        item_id = item_id_from_match(root, input_path)
        original_item_id = item_id
        duplicate_count = seen_ids.get(item_id, 0)
        seen_ids[item_id] = duplicate_count + 1

        if duplicate_count:
            item_id = "{}_{:03d}".format(original_item_id, duplicate_count + 1)

        dataset_dir = input_path.parent
        relative_parts = input_path.relative_to(root).parts
        if len(relative_parts) > 1:
            dataset_dir = root / relative_parts[0]

        if not input_path.exists():
            continue

        rows.append(
            {
                "id": item_id,
                "input_path": str(input_path),
                "dataset_dir": str(dataset_dir),
                "row_index": len(rows),
                "source_format": "folder_pattern",
                "file_pattern": file_pattern,
            }
        )

    return rows


def read_csv_manifest(settings):
    manifest_path = abspath(settings.manifest_path)

    if not manifest_path.exists():
        raise FileNotFoundError("Manifest not found: {}".format(manifest_path))

    rows = []
    with manifest_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []

        if "input_path" not in fieldnames:
            raise ValueError("Manifest must contain at least this column: input_path")

        for index, row in enumerate(reader):
            input_path = (row.get("input_path") or "").strip()
            if not input_path:
                continue

            item_id = (row.get("id") or "").strip()
            if not item_id:
                item_id = Path(input_path).stem or "item_{:04d}".format(index)

            resolved_input = Path(input_path)
            if not resolved_input.is_absolute():
                resolved_input = manifest_path.parent / resolved_input

            item = {
                "id": item_id,
                "input_path": str(resolved_input),
                "row_index": index,
            }

            for key, value in row.items():
                if key not in item and key is not None:
                    item[key] = value

            rows.append(item)

    return rows


def read_manifest(settings):
    if settings.use_synva_scan:
        return scan_synva_rows(settings)

    if not settings.manifest_path:
        raise ValueError("Set a manifest CSV or enable SynVA folder scan.")

    return read_csv_manifest(settings)


def default_output_dir(settings):
    if settings.output_dir:
        return abspath(settings.output_dir)

    if settings.use_synva_scan:
        return abspath(settings.synva_root).parent / "synva_queue_output"

    return abspath(settings.manifest_path).parent / "output"


def state_path(settings):
    if settings.use_synva_scan:
        return default_output_dir(settings) / SYNVA_STATE_FILENAME

    return abspath(settings.manifest_path).with_suffix(".queue_state.json")


def default_state():
    return {
        "current_index": 0,
        "done": {},
        "skipped": {},
    }


def load_state(settings):
    path = state_path(settings)
    if not path.exists():
        return default_state()

    with path.open("r", encoding="utf-8") as handle:
        state = json.load(handle)

    state.setdefault("current_index", 0)
    state.setdefault("done", {})
    state.setdefault("skipped", {})
    return state


def save_state(settings, state):
    path = state_path(settings)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as handle:
        json.dump(state, handle, indent=2, ensure_ascii=True)


def output_dir(settings):
    path = default_output_dir(settings)
    path.mkdir(parents=True, exist_ok=True)
    return path


def obj_output_path(settings, item):
    source_path = Path(item["input_path"])
    item_dir = output_dir(settings) / item["id"]
    item_dir.mkdir(parents=True, exist_ok=True)
    target_path = item_dir / source_path.with_suffix(".obj").name

    if target_path.resolve() == source_path.resolve():
        raise RuntimeError("Refusing to overwrite the original input OBJ: {}".format(source_path))

    return target_path


def call_operator_with_supported_kwargs(operator, **kwargs):
    supported = {prop.identifier for prop in operator.get_rna_type().properties}
    filtered_kwargs = {key: value for key, value in kwargs.items() if key in supported}
    return operator(**filtered_kwargs)


def ensure_object_mode():
    active = bpy.context.view_layer.objects.active
    if active and active.mode != "OBJECT":
        if not bpy.ops.object.mode_set.poll():
            raise RuntimeError("Switch to Object Mode before saving.")
        bpy.ops.object.mode_set(mode="OBJECT")


def clear_scene():
    ensure_object_mode()

    for obj in list(bpy.context.scene.objects):
        bpy.data.objects.remove(obj, do_unlink=True)


def import_dataset(filepath):
    """Import one dataset. Extend this function for project-specific formats."""

    path = Path(filepath)
    ext = path.suffix.lower()

    if not path.exists():
        raise FileNotFoundError("Input file not found: {}".format(path))

    if ext in {".glb", ".gltf"}:
        bpy.ops.import_scene.gltf(filepath=str(path))
    elif ext == ".fbx":
        bpy.ops.import_scene.fbx(filepath=str(path))
    elif ext == ".obj":
        if hasattr(bpy.ops.wm, "obj_import"):
            bpy.ops.wm.obj_import(filepath=str(path))
        else:
            bpy.ops.import_scene.obj(filepath=str(path))
    elif ext == ".stl":
        if hasattr(bpy.ops.wm, "stl_import"):
            bpy.ops.wm.stl_import(filepath=str(path))
        else:
            bpy.ops.import_mesh.stl(filepath=str(path))
    elif ext in {".usd", ".usdc", ".usda"}:
        bpy.ops.wm.usd_import(filepath=str(path))
    else:
        raise ValueError(
            "Unsupported format: {}. Extend import_dataset() for this format.".format(ext)
        )


def export_obj_dataset(filepath):
    ensure_object_mode()

    mesh_objects = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    if not mesh_objects:
        raise RuntimeError("No mesh objects to export.")

    if hasattr(bpy.ops.wm, "obj_export"):
        call_operator_with_supported_kwargs(
            bpy.ops.wm.obj_export,
            filepath=str(filepath),
            export_selected_objects=False,
            apply_modifiers=True,
            export_materials=False,
            export_uv=True,
            export_normals=True,
        )
    else:
        call_operator_with_supported_kwargs(
            bpy.ops.export_scene.obj,
            filepath=str(filepath),
            use_selection=False,
            use_mesh_modifiers=True,
            use_materials=False,
            use_uvs=True,
            use_normals=True,
        )


def run_checks():
    """Run lightweight default checks. Replace or extend for production rules."""

    issues = []
    mesh_objects = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]

    if not mesh_objects:
        issues.append("No mesh objects found.")

    for obj in mesh_objects:
        if not obj.data.vertices:
            issues.append("{}: mesh has no vertices.".format(obj.name))

        if not obj.data.polygons:
            issues.append("{}: mesh has no faces.".format(obj.name))

    return {
        "ok": not issues,
        "issues": issues,
        "mesh_object_count": len(mesh_objects),
    }


def update_check_text(settings, check_result):
    if check_result["ok"]:
        settings.last_check_text = "OK: no problems found."
    else:
        settings.last_check_text = "Problems:\n" + "\n".join(check_result["issues"])


def load_item(context, index):
    settings = get_settings(context)
    rows = read_manifest(settings)

    if not rows:
        raise RuntimeError("Manifest is empty.")

    if index < 0:
        index = 0

    if index >= len(rows):
        settings.status_text = "Done. No more datasets."
        settings.current_id = ""
        settings.current_index = len(rows)
        return None

    item = rows[index]

    if settings.clear_scene_before_load:
        clear_scene()

    import_dataset(item["input_path"])

    settings.current_index = index
    settings.current_id = item["id"]

    check_result = run_checks()
    update_check_text(settings, check_result)
    settings.status_text = "Loaded: {} ({}/{})".format(item["id"], index + 1, len(rows))

    state = load_state(settings)
    state["current_index"] = index
    save_state(settings, state)

    return item


def next_unfinished_index(rows, state):
    done = set(state.get("done", {}).keys())
    skipped = set(state.get("skipped", {}).keys())
    start = max(int(state.get("current_index", 0)), 0)

    for index in range(start, len(rows)):
        if rows[index]["id"] not in done and rows[index]["id"] not in skipped:
            return index

    for index, item in enumerate(rows):
        if item["id"] not in done and item["id"] not in skipped:
            return index

    return len(rows)


# ---------------------------------------------------------------------------
# Properties
# ---------------------------------------------------------------------------


class DATAQUEUE_Settings(PropertyGroup):
    use_synva_scan: BoolProperty(
        name="Use SynVA Folder Scan",
        description="Scan files below the SynVA root using the file pattern",
        default=True,
    )

    synva_root: StringProperty(
        name="SynVA Root",
        description="Folder that contains the SynVA dataset folders",
        default=SYNVA_DEFAULT_ROOT,
        subtype="DIR_PATH",
    )

    synva_file_pattern: StringProperty(
        name="File Pattern",
        description="Glob pattern relative to SynVA Root, for example */05_submeshes/vessel_submesh.obj",
        default=SYNVA_DEFAULT_FILE_PATTERN,
    )

    manifest_path: StringProperty(
        name="Manifest CSV",
        description="CSV with at least id,input_path columns",
        subtype="FILE_PATH",
    )

    output_dir: StringProperty(
        name="Output Folder",
        description="Folder for exported OBJ files",
        subtype="DIR_PATH",
    )

    current_index: IntProperty(
        name="Current Index",
        default=0,
    )

    current_id: StringProperty(
        name="Current ID",
        default="",
    )

    status_text: StringProperty(
        name="Status",
        default="No manifest loaded.",
    )

    last_check_text: StringProperty(
        name="Last Check",
        default="No check yet.",
    )

    clear_scene_before_load: BoolProperty(
        name="Clear Scene Before Load",
        default=True,
    )

# ---------------------------------------------------------------------------
# Operators
# ---------------------------------------------------------------------------


class DATAQUEUE_OT_load_first(Operator):
    bl_idname = "data_queue.load_first"
    bl_label = "Load First"
    bl_description = "Load the first dataset from the manifest"

    def execute(self, context):
        settings = get_settings(context)

        try:
            rows = read_manifest(settings)
            if not rows:
                self.report({"ERROR"}, "Manifest is empty.")
                return {"CANCELLED"}

            save_state(settings, default_state())
            load_item(context, 0)
            self.report({"INFO"}, "First dataset loaded.")
            return {"FINISHED"}
        except Exception as exc:
            self.report({"ERROR"}, str(exc))
            settings.status_text = "Error: {}".format(exc)
            return {"CANCELLED"}


class DATAQUEUE_OT_resume(Operator):
    bl_idname = "data_queue.resume"
    bl_label = "Resume"
    bl_description = "Load the current or next unfinished dataset from state"

    def execute(self, context):
        settings = get_settings(context)

        try:
            rows = read_manifest(settings)
            if not rows:
                self.report({"ERROR"}, "Manifest is empty.")
                return {"CANCELLED"}

            state = load_state(settings)
            index = next_unfinished_index(rows, state)

            if index >= len(rows):
                settings.current_index = len(rows)
                settings.current_id = ""
                settings.status_text = "Done. All datasets are already handled."
                self.report({"INFO"}, "All datasets are already handled.")
                return {"FINISHED"}

            load_item(context, index)
            self.report({"INFO"}, "Queue resumed.")
            return {"FINISHED"}
        except Exception as exc:
            self.report({"ERROR"}, str(exc))
            settings.status_text = "Error: {}".format(exc)
            return {"CANCELLED"}


class DATAQUEUE_OT_reload_current(Operator):
    bl_idname = "data_queue.reload_current"
    bl_label = "Reload Current"
    bl_description = "Reload the current dataset"

    def execute(self, context):
        settings = get_settings(context)

        try:
            load_item(context, settings.current_index)
            self.report({"INFO"}, "Current dataset reloaded.")
            return {"FINISHED"}
        except Exception as exc:
            self.report({"ERROR"}, str(exc))
            settings.status_text = "Error: {}".format(exc)
            return {"CANCELLED"}


class DATAQUEUE_OT_save_next(Operator):
    bl_idname = "data_queue.save_next"
    bl_label = "Save & Next"
    bl_description = "Export the current dataset as OBJ and load the next one"

    def execute(self, context):
        settings = get_settings(context)

        try:
            rows = read_manifest(settings)
            index = settings.current_index

            if index < 0 or index >= len(rows):
                self.report({"ERROR"}, "No valid current dataset.")
                return {"CANCELLED"}

            item = rows[index]
            ensure_object_mode()
            check_result = run_checks()
            update_check_text(settings, check_result)

            obj_path = obj_output_path(settings, item)
            export_obj_dataset(obj_path)

            state = load_state(settings)
            state.setdefault("done", {})
            state["done"][item["id"]] = {
                "index": index,
                "input_path": item["input_path"],
                "obj_path": str(obj_path),
                "check_ok": check_result["ok"],
            }

            next_index = index + 1
            state["current_index"] = next_index
            save_state(settings, state)

            if next_index >= len(rows):
                settings.current_index = next_index
                settings.current_id = ""
                settings.status_text = "Done. All datasets are handled."
                self.report({"INFO"}, "Done. All datasets are handled.")
                return {"FINISHED"}

            load_item(context, next_index)
            self.report(
                {"INFO"},
                "Saved. Loaded next dataset: {}/{}".format(next_index + 1, len(rows)),
            )
            return {"FINISHED"}
        except Exception as exc:
            self.report({"ERROR"}, str(exc))
            settings.status_text = "Error: {}".format(exc)
            return {"CANCELLED"}


class DATAQUEUE_OT_skip(Operator):
    bl_idname = "data_queue.skip"
    bl_label = "Skip"
    bl_description = "Skip the current dataset and load the next one"

    def execute(self, context):
        settings = get_settings(context)

        try:
            rows = read_manifest(settings)
            index = settings.current_index

            if index < 0 or index >= len(rows):
                self.report({"ERROR"}, "No valid current dataset.")
                return {"CANCELLED"}

            item = rows[index]
            state = load_state(settings)
            state.setdefault("skipped", {})
            state["skipped"][item["id"]] = {
                "index": index,
                "input_path": item["input_path"],
            }

            next_index = index + 1
            state["current_index"] = next_index
            save_state(settings, state)

            if next_index >= len(rows):
                settings.current_index = next_index
                settings.current_id = ""
                settings.status_text = "Done. No more datasets."
                self.report({"INFO"}, "No more datasets.")
                return {"FINISHED"}

            load_item(context, next_index)
            self.report({"INFO"}, "Dataset skipped.")
            return {"FINISHED"}
        except Exception as exc:
            self.report({"ERROR"}, str(exc))
            settings.status_text = "Error: {}".format(exc)
            return {"CANCELLED"}


# ---------------------------------------------------------------------------
# UI Panel
# ---------------------------------------------------------------------------


class DATAQUEUE_PT_panel(Panel):
    bl_label = "Data Queue"
    bl_idname = "DATAQUEUE_PT_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Data Queue"

    def draw(self, context):
        layout = self.layout
        settings = get_settings(context)

        layout.prop(settings, "use_synva_scan")
        if settings.use_synva_scan:
            layout.prop(settings, "synva_root")
            layout.prop(settings, "synva_file_pattern")
        else:
            layout.prop(settings, "manifest_path")

        layout.prop(settings, "output_dir")
        layout.prop(settings, "clear_scene_before_load")

        layout.separator()

        row = layout.row(align=True)
        row.operator("data_queue.load_first", icon="PLAY")
        row.operator("data_queue.resume", icon="FILE_REFRESH")

        row = layout.row()
        row.operator("data_queue.reload_current", icon="LOOP_BACK")

        row = layout.row()
        row.scale_y = 1.4
        row.operator("data_queue.save_next", icon="CHECKMARK")

        row = layout.row()
        row.operator("data_queue.skip", icon="NEXT_KEYFRAME")

        layout.separator()
        layout.label(text="Index: {}".format(settings.current_index))
        layout.label(text="Current ID: {}".format(settings.current_id or "-"))

        layout.separator()
        layout.label(text="Status:")
        layout.label(text=settings.status_text)

        layout.separator()
        layout.label(text="Check:")
        for line in settings.last_check_text.splitlines()[:8]:
            layout.label(text=line)


# ---------------------------------------------------------------------------
# Register
# ---------------------------------------------------------------------------


classes = (
    DATAQUEUE_Settings,
    DATAQUEUE_OT_load_first,
    DATAQUEUE_OT_resume,
    DATAQUEUE_OT_reload_current,
    DATAQUEUE_OT_save_next,
    DATAQUEUE_OT_skip,
    DATAQUEUE_PT_panel,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.data_queue_settings = PointerProperty(type=DATAQUEUE_Settings)


def unregister():
    del bpy.types.Scene.data_queue_settings

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
