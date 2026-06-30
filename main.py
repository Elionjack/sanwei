from pathlib import Path
import os

from config_reader import ConfigReader
from osgb_to_glb import OsgbToGlbConverter
from b3dm_generator import B3dmGenerator
from coordinate_transform import CoordinateTransformer
from tileset_generator import TilesetGenerator


INPUT_DIR = r"E:\learning\data\1"
OUTPUT_DIR = r"E:\learning\data\output"
OSGCONV_PATH = r"E:\learning\data\OpenSceneGraph-3.6.5-VC2022-64-2025-04\bin\osgconv.exe"
SKIP_GLB = False
SKIP_B3DM = False


def main():
    input_dir = Path(INPUT_DIR)
    output_dir = Path(OUTPUT_DIR)

    if not input_dir.exists():
        print(f"Error: Input directory not found: {input_dir}")
        return 1

    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("OSGB to 3D Tiles Converter")
    print("=" * 60)
    print(f"Input: {input_dir}")
    print(f"Output: {output_dir}")
    print("=" * 60)

    config_reader = ConfigReader(input_dir)
    config_reader.read_all()

    print("\n[1/5] Reading configuration files...")
    print(f"  Metadata: {config_reader.metadata}")
    print(f"  Tiles count: {len(config_reader.boundary)}")
    print(f"  CRS: {config_reader.config_scp.get('crs', {}).get('name', 'Unknown')}")

    origin = config_reader.get_origin()
    srs_wkt = config_reader.config_scp.get('crs', {}).get('srs') or config_reader.metadata.get('srs')

    if not srs_wkt:
        print("Error: SRS not found in metadata")
        return 1

    print(f"  Origin: {origin}")
    print("  Done!")

    print("\n[2/5] Converting OSGB to GLB...")
    if not SKIP_GLB:
        glb_dir = output_dir / "glb"
        osgconv_converter = OsgbToGlbConverter(osgconv_path=OSGCONV_PATH)

        if not osgconv_converter.osgconv_path:
            print("  Warning: osgconv not found. Please install OpenSceneGraph or set OSGCONV_PATH variable")
            print("  Skipping OSGB to GLB conversion")
        else:
            print(f"  Using osgconv: {osgconv_converter.osgconv_path}")
            success, fail = osgconv_converter.convert_batch(input_dir, output_dir)
            print(f"  GLB conversion: {success} success, {fail} fail")
    else:
        print("  Skipped (SKIP_GLB=True)")
    print("  Done!")

    print("\n[3/5] Converting GLB to B3DM...")
    if not SKIP_B3DM:
        glb_dir = output_dir / "glb"
        b3dm_dir = output_dir / "tiles"

        if not glb_dir.exists():
            print("  Error: GLB directory not found. Set SKIP_GLB=False and run again")
            return 1

        b3dm_generator = B3dmGenerator()
        success, fail = b3dm_generator.batch_convert(str(glb_dir), str(b3dm_dir))
        print(f"  B3DM conversion: {success} success, {fail} fail")
    else:
        print("  Skipped (SKIP_B3DM=True)")
    print("  Done!")

    print("\n[4/5] Preparing coordinate transformations...")
    transformer = CoordinateTransformer(srs_wkt, origin)

    regions = {}
    for tile_name, boundary in config_reader.boundary.items():
        region = transformer.get_tile_region(tile_name, boundary)
        regions[tile_name] = region
        print(f"  {tile_name}: {region}")

    bounding_spheres = config_reader.get_tile_bounding_spheres()
    print(f"  Bounding spheres loaded: {len(bounding_spheres)}")
    print("  Done!")

    print("\n[5/5] Generating tileset.json...")
    b3dm_dir = output_dir / "tiles"

    if not b3dm_dir.exists():
        print("  Error: B3DM directory not found")
        return 1

    tileset_generator = TilesetGenerator()
    tileset_generator.add_bounding_spheres(bounding_spheres)

    if tileset_generator.generate(str(b3dm_dir), str(output_dir), regions, bounding_spheres):
        tile_count = tileset_generator.get_tile_count()
        print(f"  Tileset generated with {tile_count} tiles")

        tileset_path = output_dir / "tileset.json"
        valid, msg = tileset_generator.validate_tileset(str(tileset_path))
        print(f"  Validation: {'PASS' if valid else 'FAIL'} - {msg}")
    else:
        print("  Error: Failed to generate tileset.json")
        return 1
    print("  Done!")

    print("\n" + "=" * 60)
    print("Conversion complete!")
    print(f"Output directory: {output_dir}")
    print(f"Files generated:")
    print(f"  - tileset.json")
    print(f"  - tiles/ (B3DM files)")
    print(f"  - glb/ (GLB files, if not skipped)")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    exit(main())