import os
import torch
import asyncio
import aiohttp
from .google_photos_api import batch_search_photos
from .image_processing import process_single_image
from .progress_bar import MultiProgressBar
from .credentials_manager import get_credentials
from termcolor import colored

PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(PLUGIN_DIR, "image_cache")

class GooglePhotosSearch:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "search_query": (["Animals", "Architecture", "Arts", "Birthdays", "Cityscapes", "Crafts", 
                                  "Documents", "Fashion", "Flowers", "Food and Drink", "Gardens", "Holidays", 
                                  "Houses", "Landmarks", "Landscapes", "Night", "People", "Performances", 
                                  "Pets", "Receipts", "Screenshots", "Selfies", "Sports", "Travel", 
                                  "Weddings", "Whiteboards", "Beaches", "Cars", "Concerts", "Fireworks", 
                                  "Mountains", "Museums", "Parks", "Planes", "Schools", "Snow", "Sunsets", 
                                  "Temples", "Waterfalls"],),
                "max_images": ("INT", {"default": 10, "min": 1, "max": 100}),
                "size_option": (["Original Size", "Custom Size", "Scale to Size"],),
                "sort_order": (["DESCENDING", "ASCENDING"],),
            },
            "optional": {
                "target_width": ("INT", {"default": 512, "min": 64, "max": 2048}),
                "target_height": ("INT", {"default": 512, "min": 64, "max": 2048}),
                "target_size": ("INT", {"default": 512, "min": 64, "max": 2048}),
                "use_crop": ("BOOLEAN", {"default": False}),
                "cache_images": ("BOOLEAN", {"default": True}),
                "client_secrets_file": ("STRING", {"default": os.path.join(PLUGIN_DIR, "client_secrets.json")}),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "search_photos"
    CATEGORY = "loaders"
    OUTPUT_NODE = True

    def __init__(self):
        self.log_messages = []
        self.progress_bars = MultiProgressBar()
        self.cancelled = False
        self.session = None

    def log(self, message):
        colored_message = message
        self.log_messages.append(colored_message)
        print(colored_message)

    def check_cancelled(self):
        if self.cancelled:
            self.log(colored("[search_photos] Operation cancelled", 'red'))
            raise asyncio.CancelledError("Operation cancelled by user")

    async def search_photos_async(self, search_query, max_images, size_option, sort_order, target_width=512, target_height=512, target_size=512, use_crop=False, cache_images=True, client_secrets_file=None):
        self.log(colored(f"[search_photos] Starting photo search with query: {search_query}", 'green'))
        self.log(colored(f"[search_photos] Max images: {max_images}", 'green'))

        self.check_cancelled()

        if not client_secrets_file:
            client_secrets_file = os.path.join(PLUGIN_DIR, "client_secrets.json")

        try:
            creds = get_credentials(client_secrets_file, self.log, PLUGIN_DIR)
        except Exception as e:
            error_message = colored(f"ERROR: Failed to obtain credentials. Error details: {str(e)}", 'red')
            self.log(error_message)
            raise Exception(error_message) from e
        
        self.check_cancelled()

        self.session = aiohttp.ClientSession()
        try:
            self.progress_bars.add_bar("search_photos", max_images, "Searching photos", "items")
            media_items = await batch_search_photos(self.session, creds, search_query, max_images, "creation_time", sort_order, self.log, self.progress_bars, self.check_cancelled)
            self.progress_bars.remove_bar("search_photos")
            
            if not media_items:
                self.log(colored(f"[search_photos] No images found for the query: {search_query}", 'yellow'))
                return None

            self.progress_bars.add_bar("process_images", len(media_items), "Processing images", "images")
            images = []
            for item in media_items:
                self.check_cancelled()
                img = await self.process_image(item['baseUrl'], target_width, target_height, size_option, use_crop, item.get('mediaMetadata', {}).get('width', 0), item['id'], cache_images)
                if img is not None:
                    images.append(img)
                self.progress_bars.update("process_images", 1)
                await asyncio.sleep(0)
            
            self.progress_bars.remove_bar("process_images")
            
            if not images:
                self.log(colored("[search_photos] No images were successfully processed.", 'yellow'))
                return None
            
            self.log(colored(f"[search_photos] Successfully processed {len(images)} images", 'green'))
            return torch.cat(images, dim=0)
        
        except asyncio.CancelledError:
            self.log(colored("[search_photos] Operation cancelled", 'red'))
            raise
        finally:
            await self.cleanup()

    async def process_image(self, image_url, target_width, target_height, size_option, use_crop, original_size, image_id, cache_images):
        if cache_images:
            cached_image = self.load_cached_image(image_id)
            if cached_image is not None:
                self.log(colored(f"[process_image] Using cached image for ID: {image_id}", 'cyan'))
                return cached_image

        img = await process_single_image(self.session, image_url, target_width, target_height, size_option, use_crop, self.log, self.check_cancelled, original_size)
        
        if img is not None and cache_images:
            self.cache_image(image_id, img)

        return img

    def load_cached_image(self, image_id):
        cache_path = os.path.join(CACHE_DIR, f"{image_id}.pt")
        if os.path.exists(cache_path):
            try:
                return torch.load(cache_path)
            except Exception as e:
                self.log(colored(f"[load_cached_image] Error loading cached image: {str(e)}", 'yellow'))
        return None

    def cache_image(self, image_id, img_tensor):
        os.makedirs(CACHE_DIR, exist_ok=True)
        cache_path = os.path.join(CACHE_DIR, f"{image_id}.pt")
        try:
            torch.save(img_tensor, cache_path)
        except Exception as e:
            self.log(colored(f"[cache_image] Error caching image: {str(e)}", 'yellow'))

    async def cleanup(self):
        if self.session:
            await self.session.close()

    def search_photos(self, search_query, max_images, size_option, sort_order, target_width=512, target_height=512, target_size=512, use_crop=False, cache_images=True, client_secrets_file=None):
        self.cancelled = False
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        try:
            result = loop.run_until_complete(self.search_photos_async(search_query, max_images, size_option, sort_order, target_width, target_height, target_size, use_crop, cache_images, client_secrets_file))
            if result is None:
                # If no images were found, return a single empty tensor
                return (torch.zeros((1, 3, target_height, target_width)),)
            return (result,)
        except asyncio.CancelledError:
            self.log(colored("Operation was cancelled", 'red'))
            loop.run_until_complete(self.cleanup())
            return (torch.zeros((1, 3, target_height, target_width)),)

    def cancel(self):
        self.cancelled = True
        self.log(colored("Cancellation requested", 'red'))
        for task in asyncio.all_tasks():
            task.cancel()