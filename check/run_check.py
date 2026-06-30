import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from validator import TilesetValidator, print_validation_report
from viewer import TilesetViewer


DEFAULT_OUTPUT_DIR = r"E:\learning\data\output"


def main():
    if len(sys.argv) > 1:
        output_dir = sys.argv[1]
    else:
        output_dir = DEFAULT_OUTPUT_DIR
        print(f"No output directory specified. Using default: {output_dir}")

    print("=" * 70)
    print("3D Tiles Check Tool")
    print("=" * 70)
    print(f"Checking output directory: {output_dir}")
    print("=" * 70)

    print("\n[Step 1/2] Validating 3D Tiles structure...")
    validator = TilesetValidator()
    is_valid, errors, warnings, stats = validator.validate(output_dir)
    print_validation_report(is_valid, errors, warnings, stats)

    if not is_valid and len(errors) > 0:
        print("\nValidation failed with errors. Would you like to continue to visualization anyway?")
        print("(Note: Visualization may not work correctly if there are critical errors)")
        choice = input("Continue? [Y/n] ").strip().lower()
        if choice in ('n', 'no'):
            print("\nAborting. Please fix the errors first.")
            return 1

    print("\n[Step 2/2] Starting viewer...")
    viewer = TilesetViewer()
    url = viewer.start_server(output_dir)
    
    if url:
        print(f"\nViewer started successfully: {url}")
    else:
        print("\nFailed to start viewer")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
