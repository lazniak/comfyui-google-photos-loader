import os
import json
import asyncio
import aiohttp
from .google_photos_api import batch_list_albums
from .credentials_manager import get_credentials
from .progress_bar import MultiProgressBar
from .logging_config import setup_logger, log_message

PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))

logger = setup_logger('google_photos_album_lister', os.path.join(PLUGIN_DIR, 'google_photos_album_lister.log'))

class GooglePhotosAlbumLister:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "client_secrets_file": ("STRING", {"default": os.path.join(PLUGIN_DIR, "client_secrets.json"), "multiline": False}),
                "print_log": ("BOOLEAN", {"default": False}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("album_list",)
    FUNCTION = "list_albums"
    CATEGORY = "loaders"

    def __init__(self):
        self.logger = logger
        self.progress_bars = MultiProgressBar(self.logger)
        self.cancelled = False
        self.session = None
        self.print_log = False

    def log(self, message, level='info'):
        log_message(self.logger, message, level)
        if self.print_log:
            print(message)

    def check_cancelled(self):
        if self.cancelled:
            self.log("Operation cancelled", 'warning')
            raise asyncio.CancelledError("Operation cancelled by user")

    def save_albums_to_json(self, albums):
        json_path = os.path.join(PLUGIN_DIR, "albums_list.json")
        album_data = []
        for idx, album in enumerate(albums):
            album_data.append({
                "index": idx + 1,
                "id": album.get('id', 'No ID'),
                "title": album.get('title', 'Untitled'),
                "mediaItemsCount": album.get('mediaItemsCount', 'Unknown')
            })
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(album_data, f, ensure_ascii=False, indent=2)
        self.log(f"Albums list saved to {json_path}", 'info')

    async def list_albums_async(self, client_secrets_file, print_log):
        self.print_log = print_log
        self.log("Starting album listing", 'info')

        try:
            creds = get_credentials(client_secrets_file, PLUGIN_DIR, self.logger)
        except Exception as e:
            error_message = f"ERROR: Failed to obtain credentials. Error details: {str(e)}"
            self.log(error_message, 'error')
            raise Exception(error_message) from e

        self.session = aiohttp.ClientSession()
        try:
            self.progress_bars.add_bar("list_albums", 1, "Listing albums", "batch")
            albums = await batch_list_albums(self.session, creds, self.logger, self.progress_bars, self.check_cancelled)
            self.progress_bars.remove_bar("list_albums")
            
            if not albums:
                self.log("No albums found", 'warning')
                return ""
            
            self.save_albums_to_json(albums)
            
            album_list = []
            for idx, album in enumerate(albums):
                title = album.get('title', 'Untitled')
                album_id = album.get('id', 'No ID')
                media_items_count = album.get('mediaItemsCount', 'Unknown')
                album_list.append(f"[ {idx+1:04d} | {album_id} | count: {media_items_count} | \"{title}\" ]")
            
            self.log(f"Found {len(albums)} albums", 'info')
            return "\n".join(album_list)
        
        except asyncio.CancelledError:
            self.log("Operation cancelled", 'warning')
            raise
        finally:
            await self.cleanup()

    async def cleanup(self):
        if self.session:
            await self.session.close()
            self.log("Session closed", 'debug')

    def list_albums(self, client_secrets_file, print_log):
        self.cancelled = False
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        try:
            result = loop.run_until_complete(self.list_albums_async(client_secrets_file, print_log))
        except asyncio.CancelledError:
            self.log("Operation was cancelled", 'warning')
            loop.run_until_complete(self.cleanup())
            result = ""
        except Exception as e:
            self.log(f"An error occurred: {str(e)}", 'error')
            result = ""
        return (result,)

    def cancel(self):
        self.cancelled = True
        self.log("Cancellation requested", 'warning')
        for task in asyncio.all_tasks():
            task.cancel()

# Usage in ComfyUI
NODE_CLASS_MAPPINGS = {
    "Google Photos Album Lister": GooglePhotosAlbumLister
}