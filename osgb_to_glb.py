import subprocess
import os
from pathlib import Path
import glob


class OsgbToGlbConverter:
    def __init__(self, osgconv_path=None):
        self.osgconv_path = osgconv_path or self._find_osgconv()

    def _find_osgconv(self):
        common_paths = [
            r"C:\OpenSceneGraph\bin\osgconv.exe",
            r"C:\Program Files\OpenSceneGraph\bin\osgconv.exe",
            r"D:\OpenSceneGraph\bin\osgconv.exe",
        ]
        for path in common_paths:
            if os.path.exists(path):
                return path

        for root, dirs, files in os.walk("C:\\"):
            if "osgconv.exe" in files:
                return os.path.join(root, "osgconv.exe")

        return None

    def convert_single(self, osgb_path, output_path):
        if not self.osgconv_path:
            raise RuntimeError("osgconv not found. Please specify osgconv_path parameter")

        if not os.path.exists(osgb_path):
            raise FileNotFoundError(f"OSGB file not found: {osgb_path}")

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        cmd = [
            self.osgconv_path,
            osgb_path,
            "-o",
            output_path,
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode != 0:
                print(f"Warning: osgconv returned non-zero exit code for {osgb_path}")
                print(f"stderr: {result.stderr[:500]}")
                return False

            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                return True
            else:
                print(f"Warning: Output file not created or empty: {output_path}")
                return False

        except subprocess.TimeoutExpired:
            print(f"Timeout: osgconv took too long for {osgb_path}")
            return False
        except Exception as e:
            print(f"Error converting {osgb_path}: {str(e)}")
            return False

    def convert_batch(self, data_dir, output_dir, tile_names=None):
        data_path = Path(data_dir)
        output_path = Path(output_dir)

        if tile_names is None:
            tile_dirs = [d for d in (data_path / "Data").iterdir() if d.is_dir()]
            tile_names = [d.name for d in tile_dirs]

        success_count = 0
        fail_count = 0

        for tile_name in tile_names:
            tile_dir = data_path / "Data" / tile_name
            osgb_files = sorted(tile_dir.glob("*.osgb"))

            for osgb_file in osgb_files:
                relative_path = osgb_file.relative_to(data_path / "Data")
                glb_path = output_path / "glb" / relative_path.with_suffix(".glb")

                print(f"Converting {osgb_file} -> {glb_path}")

                if self.convert_single(str(osgb_file), str(glb_path)):
                    success_count += 1
                else:
                    fail_count += 1

        print(f"\nConversion complete. Success: {success_count}, Fail: {fail_count}")
        return success_count, fail_count

    def get_osgconv_version(self):
        if not self.osgconv_path:
            return None

        try:
            result = subprocess.run(
                [self.osgconv_path, "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.stdout.strip()
        except Exception:
            return None