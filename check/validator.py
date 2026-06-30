import json
import os
import struct
import math
from pathlib import Path


class TilesetValidator:
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.stats = {}

    def validate(self, output_dir):
        output_path = Path(output_dir)
        
        if not output_path.exists():
            self.errors.append(f"Output directory does not exist: {output_dir}")
            return False, self.errors, self.warnings, self.stats

        tileset_path = output_path / "tileset.json"
        if not tileset_path.exists():
            self.errors.append(f"tileset.json not found in: {output_dir}")
            return False, self.errors, self.warnings, self.stats

        tileset = self._load_tileset(tileset_path)
        if tileset is None:
            return False, self.errors, self.warnings, self.stats

        self._validate_tileset_structure(tileset)
        self._validate_all_tiles(tileset, output_path)
        self._validate_b3dm_files(output_path)
        
        self._calculate_stats(output_path)

        has_errors = len(self.errors) > 0
        return not has_errors, self.errors, self.warnings, self.stats

    def _load_tileset(self, tileset_path):
        try:
            with open(tileset_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            self.errors.append(f"Invalid JSON in tileset.json: {e}")
            return None
        except Exception as e:
            self.errors.append(f"Failed to read tileset.json: {e}")
            return None

    def _validate_tileset_structure(self, tileset):
        required_fields = ["asset", "geometricError", "root"]
        for field in required_fields:
            if field not in tileset:
                self.errors.append(f"Missing required field in tileset.json: {field}")

        if "asset" in tileset:
            if "version" not in tileset["asset"]:
                self.errors.append("Missing 'version' in asset section")
            else:
                version = tileset["asset"]["version"]
                if version != "1.0":
                    self.warnings.append(f"Asset version is {version}, expected 1.0")

        if "root" in tileset:
            self._validate_tile_node(tileset["root"], "root")

    def _validate_tile_node(self, node, path):
        if "boundingVolume" not in node:
            self.errors.append(f"Missing 'boundingVolume' in tile: {path}")
        else:
            bv = node["boundingVolume"]
            if "region" in bv:
                self._validate_region(bv["region"], path)
            elif "box" in bv:
                if len(bv["box"]) != 12:
                    self.errors.append(f"Invalid 'box' length in {path}: expected 12, got {len(bv['box'])}")
            elif "sphere" in bv:
                if len(bv["sphere"]) != 4:
                    self.errors.append(f"Invalid 'sphere' length in {path}: expected 4, got {len(bv['sphere'])}")
            else:
                self.warnings.append(f"No recognized boundingVolume type in {path}")

        if "geometricError" not in node:
            self.errors.append(f"Missing 'geometricError' in tile: {path}")
        else:
            ge = node["geometricError"]
            if not isinstance(ge, (int, float)) or ge < 0:
                self.errors.append(f"Invalid 'geometricError' in {path}: {ge}")

        if "content" in node:
            content = node["content"]
            if "uri" not in content:
                self.errors.append(f"Missing 'uri' in content of {path}")
            else:
                uri = content["uri"]
                if not uri.endswith(".b3dm") and not uri.endswith(".glb"):
                    self.warnings.append(f"Unsupported content type in {path}: {uri}")

        if "children" in node:
            children = node["children"]
            if not isinstance(children, list):
                self.errors.append(f"'children' must be an array in {path}")
            else:
                for i, child in enumerate(children):
                    child_path = f"{path}.children[{i}]"
                    self._validate_tile_node(child, child_path)

    def _validate_region(self, region, path):
        if not isinstance(region, list) or len(region) != 6:
            self.errors.append(f"Invalid 'region' in {path}: must be a list of 6 numbers")
            return

        west, south, east, north, min_height, max_height = region

        for val in [west, south, east, north]:
            if not isinstance(val, (int, float)) or math.isnan(val) or math.isinf(val):
                self.errors.append(f"Invalid longitude/latitude value in region of {path}: {val}")

        for val in [min_height, max_height]:
            if not isinstance(val, (int, float)) or math.isnan(val) or math.isinf(val):
                self.errors.append(f"Invalid height value in region of {path}: {val}")

        if west > east:
            self.warnings.append(f"West ({west}) > East ({east}) in region of {path}")
        if south > north:
            self.warnings.append(f"South ({south}) > North ({north}) in region of {path}")
        if min_height > max_height:
            self.warnings.append(f"MinHeight ({min_height}) > MaxHeight ({max_height}) in region of {path}")

        if west < -math.pi or west > math.pi:
            self.warnings.append(f"West ({math.degrees(west)}°) out of valid range [-180, 180] in {path}")
        if east < -math.pi or east > math.pi:
            self.warnings.append(f"East ({math.degrees(east)}°) out of valid range [-180, 180] in {path}")
        if south < -math.pi/2 or south > math.pi/2:
            self.warnings.append(f"South ({math.degrees(south)}°) out of valid range [-90, 90] in {path}")
        if north < -math.pi/2 or north > math.pi/2:
            self.warnings.append(f"North ({math.degrees(north)}°) out of valid range [-90, 90] in {path}")

    def _validate_all_tiles(self, tileset, output_path):
        def validate_node(node):
            if "content" in node and "uri" in node["content"]:
                uri = node["content"]["uri"]
                tile_path = output_path / uri
                if not tile_path.exists():
                    self.errors.append(f"Content file not found: {uri}")
                else:
                    file_size = os.path.getsize(tile_path)
                    if file_size == 0:
                        self.errors.append(f"Content file is empty: {uri}")
                    elif file_size < 100:
                        self.warnings.append(f"Content file is very small ({file_size} bytes): {uri}")

            if "children" in node:
                for child in node["children"]:
                    validate_node(child)

        validate_node(tileset["root"])

    def _validate_b3dm_files(self, output_path):
        b3dm_dir = output_path / "tiles"
        if not b3dm_dir.exists():
            self.warnings.append("'tiles' directory not found")
            return

        b3dm_files = list(b3dm_dir.rglob("*.b3dm"))
        self.stats["b3dm_count"] = len(b3dm_files)

        for b3dm_file in b3dm_files:
            self._validate_b3dm_header(b3dm_file)

    def _validate_b3dm_header(self, b3dm_path):
        try:
            with open(b3dm_path, 'rb') as f:
                data = f.read(28)

            if len(data) < 28:
                self.errors.append(f"B3DM file too small: {b3dm_path.name}")
                return

            magic = data[0:4]
            version = struct.unpack('<I', data[4:8])[0]
            total_size = struct.unpack('<I', data[8:12])[0]
            ft_json_len = struct.unpack('<I', data[12:16])[0]
            ft_bin_len = struct.unpack('<I', data[16:20])[0]
            bt_json_len = struct.unpack('<I', data[20:24])[0]
            bt_bin_len = struct.unpack('<I', data[24:28])[0]

            actual_size = os.path.getsize(b3dm_path)

            if magic != b'b3dm':
                self.errors.append(f"B3DM magic mismatch in {b3dm_path.name}: expected 'b3dm', got {magic}")
            if version != 1:
                self.warnings.append(f"B3DM version {version} in {b3dm_path.name}, expected 1")
            if total_size != actual_size:
                self.errors.append(f"B3DM size mismatch in {b3dm_path.name}: header says {total_size}, actual {actual_size}")

            expected_min_size = 28 + ft_json_len + ft_bin_len + bt_json_len + bt_bin_len
            if actual_size < expected_min_size:
                self.errors.append(f"B3DM file truncated: {b3dm_path.name}")

        except Exception as e:
            self.errors.append(f"Failed to validate B3DM header for {b3dm_path.name}: {e}")

    def _calculate_stats(self, output_path):
        tileset_path = output_path / "tileset.json"
        
        try:
            with open(tileset_path, 'r', encoding='utf-8') as f:
                tileset = json.load(f)

            def count_tiles(node):
                count = 1
                if "children" in node:
                    for child in node["children"]:
                        count += count_tiles(child)
                return count

            self.stats["tile_count"] = count_tiles(tileset["root"])
        except Exception:
            self.stats["tile_count"] = 0

        b3dm_dir = output_path / "tiles"
        if b3dm_dir.exists():
            b3dm_files = list(b3dm_dir.rglob("*.b3dm"))
            self.stats["b3dm_count"] = len(b3dm_files)
            if b3dm_files:
                sizes = [os.path.getsize(f) for f in b3dm_files]
                self.stats["b3dm_total_size"] = sum(sizes)
                self.stats["b3dm_avg_size"] = sum(sizes) / len(sizes)
                self.stats["b3dm_max_size"] = max(sizes)
                self.stats["b3dm_min_size"] = min(sizes)
            else:
                self.stats["b3dm_total_size"] = 0
                self.stats["b3dm_avg_size"] = 0
                self.stats["b3dm_max_size"] = 0
                self.stats["b3dm_min_size"] = 0
        else:
            self.stats["b3dm_count"] = 0
            self.stats["b3dm_total_size"] = 0
            self.stats["b3dm_avg_size"] = 0
            self.stats["b3dm_max_size"] = 0
            self.stats["b3dm_min_size"] = 0

        glb_dir = output_path / "glb"
        if glb_dir.exists():
            glb_files = list(glb_dir.rglob("*.glb"))
            self.stats["glb_count"] = len(glb_files)
            if glb_files:
                sizes = [os.path.getsize(f) for f in glb_files]
                self.stats["glb_total_size"] = sum(sizes)
                self.stats["glb_avg_size"] = sum(sizes) / len(sizes)
                self.stats["glb_max_size"] = max(sizes)
            else:
                self.stats["glb_total_size"] = 0
                self.stats["glb_avg_size"] = 0
                self.stats["glb_max_size"] = 0
        else:
            self.stats["glb_count"] = 0
            self.stats["glb_total_size"] = 0
            self.stats["glb_avg_size"] = 0
            self.stats["glb_max_size"] = 0

        self.stats["total_errors"] = len(self.errors)
        self.stats["total_warnings"] = len(self.warnings)


def _format_size(bytes):
    if bytes == 0:
        return "0 B"
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes < 1024:
            return f"{bytes:.2f} {unit}"
        bytes /= 1024
    return f"{bytes:.2f} TB"


def print_validation_report(is_valid, errors, warnings, stats):
    print("=" * 70)
    print("3D Tiles Validation Report")
    print("=" * 70)
    
    print(f"\n[Summary]")
    print(f"  Status: {'PASS' if is_valid else 'FAIL'}")
    print(f"  Total Errors: {stats.get('total_errors', 0)}")
    print(f"  Total Warnings: {stats.get('total_warnings', 0)}")
    
    print(f"\n[Statistics]")
    print(f"  Tiles in tileset.json: {stats.get('tile_count', 0)}")
    
    b3dm_count = stats.get('b3dm_count', 0)
    print(f"  B3DM files: {b3dm_count}")
    if b3dm_count > 0:
        print(f"    Total size: {_format_size(stats.get('b3dm_total_size', 0))}")
        print(f"    Average size: {_format_size(stats.get('b3dm_avg_size', 0))}")
        print(f"    Max size: {_format_size(stats.get('b3dm_max_size', 0))}")
        print(f"    Min size: {_format_size(stats.get('b3dm_min_size', 0))}")
    
    glb_count = stats.get('glb_count', 0)
    print(f"  GLB files: {glb_count}")
    if glb_count > 0:
        print(f"    Total size: {_format_size(stats.get('glb_total_size', 0))}")
        print(f"    Average size: {_format_size(stats.get('glb_avg_size', 0))}")
        print(f"    Max size: {_format_size(stats.get('glb_max_size', 0))}")
    
    if errors:
        print(f"\n[Errors]")
        for i, error in enumerate(errors, 1):
            print(f"  {i}. {error}")
    
    if warnings:
        print(f"\n[Warnings]")
        for i, warning in enumerate(warnings, 1):
            print(f"  {i}. {warning}")
    
    print("\n" + "=" * 70)
