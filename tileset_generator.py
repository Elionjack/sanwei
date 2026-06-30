import json
import os
from pathlib import Path
import math


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
        return max(1.0, 500.0 / (2 ** (lod - 14)))

    def _create_tile_node(self, b3dm_path, region, lod, has_children=False):
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

        tileset_path = output_path / "tileset.json"

        with open(str(tileset_path), 'w', encoding='utf-8') as f:
            json.dump(self.tileset, f, indent=2, ensure_ascii=False)

        print(f"Tileset.json generated at {tileset_path}")
        return True

    def _build_tile_tree(self, tile_name, lod_tree, min_lod, max_lod, regions):
        current_lod = min_lod
        root_node = None
        current_node = None

        while current_lod <= max_lod:
            if tile_name in lod_tree and current_lod in lod_tree[tile_name]:
                b3dm_files = lod_tree[tile_name][current_lod]

                for b3dm_file in b3dm_files:
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

                    has_children = (current_lod + 1) in lod_tree.get(tile_name, {})

                    tile_node = self._create_tile_node(
                        b3dm_file,
                        region,
                        current_lod,
                        has_children
                    )

                    if root_node is None:
                        root_node = tile_node
                        current_node = tile_node
                    else:
                        if "children" not in current_node:
                            current_node["children"] = []
                        current_node["children"].append(tile_node)
                        current_node = tile_node

            current_lod += 1

        return root_node

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

        west = min(r[0] for r in regions)
        south = min(r[1] for r in regions)
        east = max(r[2] for r in regions)
        north = max(r[3] for r in regions)
        min_height = min(r[4] for r in regions)
        max_height = max(r[5] for r in regions)

        return [west, south, east, north, min_height, max_height]

    def add_bounding_spheres(self, bounding_spheres):
        if not bounding_spheres:
            return

        spheres = []
        for tile_name, bs in bounding_spheres.items():
            if bs:
                spheres.append({
                    "tile_name": tile_name,
                    "center": [bs["center_x"], bs["center_y"], bs["center_z"]],
                    "radius": bs["radius"]
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