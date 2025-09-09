
# update_repo.py
import argparse
import os
from pathlib import Path
import shutil
from tufup.repo import Repository

# --- configuration ---
APP_NAME = 'MangaTranslatorUI'
REPO_DIR = 'update_repository'
KEYS_DIR = 'keys'
# Note: This should match the `app_version_attr` in your app's `__init__.py` if you have one.
# If your app executable has a `__version__` attribute, you can leave this as is.
APP_VERSION_ATTR = '__version__' 

# --- main ---
def main():
    parser = argparse.ArgumentParser(description='Update TUF repository.')
    parser.add_argument('version', help='Application version, e.g. 1.2.3')
    parser.add_argument('--bundle-path', required=True, help='Path to the application bundle (e.g., dist/manga-translator-cpu)')
    parser.add_argument('--variant', required=True, choices=['cpu', 'gpu'], help='The application variant (cpu or gpu)')
    parser.add_argument('--create-keys', action='store_true', help='Create new keys if they don't exist.')
    args = parser.parse_args()

    repo_dir = Path(REPO_DIR)
    bundle_path = Path(args.bundle_path)
    
    if not bundle_path.exists():
        print(f"Error: Bundle path does not exist: {bundle_path}")
        return

    # Initialize the repository
    # This will load existing keys and metadata if they exist,
    # or create them if they don't (if --create-keys is specified)
    repo = Repository(
        repo_dir=repo_dir,
        keys_dir=KEYS_DIR,
        app_name=APP_NAME,
        app_version_attr=APP_VERSION_ATTR
    )

    if args.create_keys:
        if not os.path.exists(KEYS_DIR):
            os.makedirs(KEYS_DIR)
        print("Creating new keys...")
        repo.initialize()
        print("Keys created. Please securely back up the 'keys' directory.")
        # We stop here after creating keys. The user should run again to add bundles.
        return

    # Add the new application bundle to the repository
    print(f"Adding bundle from: {bundle_path}")
    repo.add_bundle(
        new_bundle_dir=bundle_path,
        new_version=args.version,
        # Use custom metadata to distinguish between cpu and gpu versions
        custom_metadata={'variant': args.variant},
        # Set required=True if you want to force users to update to this version
        required=False 
    )

    # Sign and publish the changes
    print("Publishing changes to repository...")
    repo.publish_changes(private_key_dirs=[KEYS_DIR])
    print("Repository update complete.")

if __name__ == '__main__':
    main()
