import subprocess
import sys
import os

# Define paths
SPEC_FILE = 'updater.spec'
DIST_PATH = 'dist'
WORK_PATH = os.path.join('build', 'updater_standalone')

def main():
    """
    This script builds the updater executable using PyInstaller.
    It uses the existing updater.spec file.
    """
    print("--- Building Updater Executable ---")

    # Ensure the python executable is the one running this script
    python_exe = sys.executable

    # Construct the PyInstaller command
    command = [
        python_exe,
        '-m',
        'PyInstaller',
        SPEC_FILE,
        '--distpath',
        DIST_PATH,
        '--workpath',
        WORK_PATH,
        '--clean' # Clean PyInstaller cache and remove temporary files before building.
    ]

    print(f"Running command: {' '.join(command)}")

    try:
        # Execute the command
        result = subprocess.run(command, check=True, text=True, capture_output=True, encoding='utf-8')
        print("\n--- Updater build successful! ---")
        print(f"Executable located in: {os.path.abspath(os.path.join(DIST_PATH, 'updater'))}")
        print("\nPyInstaller Output:")
        print(result.stdout)

    except subprocess.CalledProcessError as e:
        print("\n--- Updater build FAILED! ---")
        print("PyInstaller returned a non-zero exit code.")
        print("\n--- Stdout ---")
        print(e.stdout)
        print("\n--- Stderr ---")
        print(e.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print("\n--- ERROR ---")
        print("PyInstaller not found. Make sure it is installed in your environment (`pip install pyinstaller`)")
        sys.exit(1)

if __name__ == "__main__":
    main()
