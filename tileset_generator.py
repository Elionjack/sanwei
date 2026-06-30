import json
import os
import sys
from pathlib import Path
import math

sys.setrecursionlimit(10000)


def _clean_nan_inf(value):
    stack = [(value, None, None)]
    while stack:
        current, parent, key = stack.pop()
        if isinstance(current, dict):
            for k, v in list(current.items()):
                if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
                    current[k] = 0.0
                elif isinstance(v, (dict, list)):
                    stack.append((v, current, k))
        elif isinstance(current, list):
            for i, v in enumerate(current):
                if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
                    current[i] = 0.0
                elif isinstance(v, (dict, list)):
                    stack.append((v, current, i))
    return value


class TilesetGenerator:
    def __init__(self):
        self.tileset = {
            "asset": {
                "version": "1.0",
                "tilesetVersion": "1.0"
            },
            "geometricError": 1000,
            "root": {}
        }

    def _parse_tile_name(self, filename):
        basename = os.path.splitext(filename)[0]

        if "_L" in basename:
            parts = basename.split("_L")
            tile_name = parts[0]
            lod_part = parts[1].split("_")[0]
            try:
                lod = int(lod_part)
            except ValueError:
                lod = 0
        else:
            tile_name = basename
            lod = 0

        return tile_name, lod

    def _build_lod_tree(self, b3dm_files):
        tree = {}

        for b3dm_file in b3dm_files:
            relative_path = str(b3dm_file)
            filename = os.path.basename(relative_path)
            tile_name, lod = self._parse_tile_name(filename)

            if tile_name not in tree:
                tree[tile_name] = {}

            if lod not in tree[tile_name]:
                tree[tile_name][lod] = []

            tree[tile_name][lod].append(relative_path)

        return tree

    def _calculate_geometric_error(self, lod):
        try:
            error = max(1.0, 500.0 / (2 ** (lod - 14)))
            if math.isnan(error) or math.isinf(error):
                return 1.0
            return error
        except (OverflowError, ValueError):
            return 1.0

    def _create_tile_node(self, b3dm_path, region, lod, has_children=False):
        region = self._clean_region(region)

        tile = {
            "boundingVolume": {
                "region": region
            },
            "geometricError": self._calculate_geometric_error(lod),
            "refine": "ADD" if has_children else None,
            "content": {
                "uri": b3dm_path
            }
        }

        if tile["refine"] is None:
            del tile["refine"]

        return tile

    def _clean_region(self, region):
        if not region:
            return [
                math.radians(114.29),
                math.radians(30.67),
                math.radians(114.31),
                math.radians(30.68),
                0,
                100
            ]

        cleaned = []
        for val in region:
            if isinstance(val, float):
                if math.isnan(val) or math.isinf(val):
                    cleaned.append(0.0)
                else:
                    cleaned.append(val)
            else:
                cleaned.append(val)
        return cleaned

    def generate(self, b3dm_dir, output_dir, regions, bounding_spheres=None):
        b3dm_path = Path(b3dm_dir)
        output_path = Path(output_dir)

        b3dm_files = sorted(b3dm_path.rglob("*.b3dm"))

        if not b3dm_files:
            print("No B3DM files found")
            return False

        lod_tree = self._build_lod_tree(b3dm_files)

        all_lods = set()
        for tile_name, lods in lod_tree.items():
            all_lods.update(lods.keys())

        min_lod = min(all_lods) if all_lods else 14
        max_lod = max(all_lods) if all_lods else 21

        root_tiles = []

        for tile_name in lod_tree.keys():
            tile_root = self._build_tile_tree(
                tile_name,
                lod_tree,
                min_lod,
                max_lod,
                regions
            )
            if tile_root:
                root_tiles.append(tile_root)

        if len(root_tiles) == 1:
            self.tileset["root"] = root_tiles[0]
        else:
            root_region = self._merge_regions([r for r in regions.values() if r])
            self.tileset["root"] = {
                "boundingVolume": {
                    "region": root_region
                },
                "geometricError": self._calculate_geometric_error(min_lod - 1),
                "refine": "ADD",
                "children": root_tiles
            }

        self.tileset = _clean_nan_inf(self.tileset)

        tileset_path = output_path / "tileset.json"

        with open(str(tileset_path), 'w', encoding='utf-8') as f:
            json.dump(self.tileset, f, indent=2, ensure_ascii=False)

        print(f"Tileset.json generated at {tileset_path}")
        return True

    def _build_tile_tree(self, tile_name, lod_tree, min_lod, max_lod, regions):
        lod_nodes = {}

        for lod in range(min_lod, max_lod + 1):
            if tile_name in lod_tree and lod in lod_tree[tile_name]:
                b3dm_files = lod_tree[tile_name][lod]

                region = regions.get(tile_name)
                if not region:
                    region = [
                        math.radians(114.29),
                        math.radians(30.67),
                        math.radians(114.31),
                        math.radians(30.68),
                        0,
                        100
                    ]

                has_children = (lod + 1) in lod_tree.get(tile_name, {})

                if len(b3dm_files) == 1:
                    node = self._create_tile_node(
                        b3dm_files[0],
                        region,
                        lod,
                        has_children
                    )
                    lod_nodes[lod] = node
                else:
                    children = []
                    for b3dm_file in b3dm_files:
                        child_node = self._create_tile_node(
                            b3dm_file,
                            region,
                            lod,
                            has_children=False
                        )
                        children.append(child_node)

                    parent_node = {
                        "boundingVolume": {
                            "region": region
                        },
                        "geometricError": self._calculate_geometric_error(lod),
                        "refine": "ADD",
                        "children": children
                    }
                    lod_nodes[lod] = parent_node

        for lod in range(min_lod, max_lod):
            if lod in lod_nodes and (lod + 1) in lod_nodes:
                parent_node = lod_nodes[lod]
                child_node = lod_nodes[lod + 1]

                if "children" not in parent_node:
                    parent_node["children"] = []
                parent_node["children"].append(child_node)

                if "refine" not in parent_node:
                    parent_node["refine"] = "ADD"

        return lod_nodes.get(min_lod)

    def _merge_regions(self, regions):
        if not regions:
            return [
                math.radians(114.29),
                math.radians(30.67),
                math.radians(114.31),
                math.radians(30.68),
                0,
                100
            ]

        west = float('inf')
        south = float('inf')
        east = float('-inf')
        north = float('-inf')
        min_height = float('inf')
        max_height = float('-inf')

        for r in regions:
            if r:
                try:
                    west = min(west, r[0] if not (math.isnan(r[0]) or math.isinf(r[0])) else west)
                    south = min(south, r[1] if not (math.isnan(r[1]) or math.isinf(r[1])) else south)
                    east = max(east, r[2] if not (math.isnan(r[2]) or math.isinf(r[2])) else east)
                    north = max(north, r[3] if not (math.isnan(r[3]) or math.isinf(r[3])) else north)
                    min_height = min(min_height, r[4] if not (math.isnan(r[4]) or math.isinf(r[4])) else min_height)
                    max_height = max(max_height, r[5] if not (math.isnan(r[5]) or math.isinf(r[5])) else max_height)
                except (IndexError, TypeError):
                    continue

        if math.isnan(west) or math.isinf(west):
            west = math.radians(114.29)
        if math.isnan(south) or math.isinf(south):
            south = math.radians(30.67)
        if math.isnan(east) or math.isinf(east):
            east = math.radians(114.31)
        if math.isnan(north) or math.isinf(north):
            north = math.radians(30.68)
        if math.isnan(min_height) or math.isinf(min_height):
            min_height = 0
        if math.isnan(max_height) or math.isinf(max_height):
            max_height = 100

        return [west, south, east, north, min_height, max_height]

    def add_bounding_spheres(self, bounding_spheres):
        if not bounding_spheres:
            return

        spheres = []
        for tile_name, bs in bounding_spheres.items():
            if bs:
                center_x = bs.get("center_x", 0)
                center_y = bs.get("center_y", 0)
                center_z = bs.get("center_z", 0)
                radius = bs.get("radius", 0)

                if math.isnan(center_x) or math.isinf(center_x):
                    center_x = 0
                if math.isnan(center_y) or math.isinf(center_y):
                    center_y = 0
                if math.isnan(center_z) or math.isinf(center_z):
                    center_z = 0
                if math.isnan(radius) or math.isinf(radius):
                    radius = 0

                spheres.append({
                    "tile_name": tile_name,
                    "center": [center_x, center_y, center_z],
                    "radius": radius
                })

        self.tileset["boundingSpheres"] = spheres

    def validate_tileset(self, tileset_path):
        if not os.path.exists(tileset_path):
            return False, "tileset.json not found"

        try:
            with open(tileset_path, 'r', encoding='utf-8') as f:
                tileset = json.load(f)
        except json.JSONDecodeError as e:
            return False, f"Invalid JSON: {e}"

        required_fields = ["asset", "geometricError", "root"]
        for field in required_fields:
            if field not in tileset:
                return False, f"Missing required field: {field}"

        if "version" not in tileset["asset"]:
            return False, "Missing asset version"

        if "boundingVolume" not in tileset["root"]:
            return False, "Missing root boundingVolume"

        return True, "Valid tileset.json"

    def get_tile_count(self):
        def count_tiles(node):
            count = 1
            if "children" in node:
                for child in node["children"]:
                    count += count_tiles(child)
            return count

        if "root" in self.tileset:
            return count_tiles(self.tileset["root"])
        return 0