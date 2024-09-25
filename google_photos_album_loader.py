import os
import torch
import asyncio
import aiohttp
import time
from .google_photos_api import choose_load_method
from .image_processing import process_single_image
from .credentials_manager import get_credentials
from .progress_bar import MultiProgressBar
from .logging_config import setup_logger, log_message

PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(PLUGIN_DIR, "image_cache")

logger = setup_logger('google_photos_album_loader', os.path.join(PLUGIN_DIR, 'google_photos_album_loader.log'))

class GooglePhotosAlbumLoader:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "album_id": ("STRING", {"multiline": False}),
                "max_images": ("INT", {"default": 10, "min": 1, "max": 5000}),
                "size_option": (["Original Size", "Scale to Size", "Crop to Size", "Fill to Size"],),
                "target_size": ("INT", {"default": 512, "min": 64, "max": 2048}),
                "cache_images": ("BOOLEAN", {"default": True}),
            },
            "optional": {
                "client_secrets_file": ("STRING", {"default": os.path.join(PLUGIN_DIR, "client_secrets.json"), "multiline": False}),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "load_album_images"
    CATEGORY = "loaders"
    OUTPUT_IS_LIST = (True,)

    def __init__(self):
        self.logger = logger
        self.progress_bars = MultiProgressBar(self.logger)
        self.cancelled = False
        self.session = None

    def check_cancelled(self):
        if self.cancelled:
            log_message(self.logger, "Operation cancelled", 'warning')
            raise asyncio.CancelledError("Operation cancelled by user")

    async def load_album_images_async(self, album_id, max_images, size_option, target_size, cache_images, client_secrets_file):
        log_message(self.logger, f"Starting image loading process for album: {album_id}", 'info')

        self.check_cancelled()

        try:
            creds = get_credentials(client_secrets_file, PLUGIN_DIR, self.logger)
            if not creds or not creds.valid:
                raise ValueError("Invalid credentials")
        except Exception as e:
            log_message(self.logger, f"Failed to obtain credentials: {str(e)}", 'error')
            raise

        self.session = aiohttp.ClientSession()
        try:
            self.progress_bars.add_bar("load_images", max_images, "Loading images", "items")
            
            load_method = choose_load_method(is_album_loader=True)
            all_media_items = await load_method(
                self.session, creds, album_id, max_images, None, "PHOTO", 
                None, None, None, False, 
                False, self.progress_bars, self.check_cancelled,
                logger=self.logger
            )
            
            self.progress_bars.remove_bar("load_images")
            
            if not all_media_items:
                log_message(self.logger, f"No images found in album: {album_id}", 'warning')
                return []
            
            log_message(self.logger, f"Retrieved {len(all_media_items)} media items from album", 'info')
        
            self.progress_bars.add_bar("process_images", len(all_media_items), "Processing images", "images")
            images = await self.process_images_parallel(all_media_items, size_option, target_size, cache_images)
            self.progress_bars.remove_bar("process_images")
            
            processed_count = len(images)
            log_message(self.logger, f"Successfully processed {processed_count} out of {len(all_media_items)} images", 'info')
            
            if not images:
                log_message(self.logger, "No images were successfully processed.", 'warning')
                return []
            
            return images
        
        except asyncio.CancelledError:
            log_message(self.logger, "Operation cancelled", 'warning')
            raise
        except Exception as e:
            log_message(self.logger, f"Error during image loading: {str(e)}", 'error')
            return []
        finally:
            await self.cleanup()

    async def process_images_parallel(self, media_items, size_option, target_size, cache_images):
        semaphore = asyncio.Semaphore(20)  # Zwiększono limit do 20
        processed_images = []
        
        async def process_with_semaphore(item):
            async with semaphore:
                result = await self.process_image(item['baseUrl'], size_option, target_size, item['id'], cache_images, 
                                                int(item.get('mediaMetadata', {}).get('width', 0)),
                                                int(item.get('mediaMetadata', {}).get('height', 0)))
                await self.progress_bars.update("process_images", 1)
                return result

        tasks = []
        for item in media_items:
            task = asyncio.create_task(process_with_semaphore(item))
            tasks.append(task)
            
            # Rozpocznij przetwarzanie, gdy mamy pierwsze 5 zadań lub wszystkie, jeśli jest ich mniej
            if len(tasks) == 5 or len(tasks) == len(media_items):
                completed, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                for task in completed:
                    result = await task
                    if result is not None:
                        processed_images.append(result)
                tasks = list(pending)

        # Poczekaj na zakończenie pozostałych zadań
        if tasks:
            for task in asyncio.as_completed(tasks):
                result = await task
                if result is not None:
                    processed_images.append(result)

        return processed_images

    async def process_image(self, image_url, size_option, target_size, image_id, cache_images, original_width, original_height):
        log_message(self.logger, f"Processing image: {image_id}", 'debug')
        if cache_images:
            cached_image = self.load_cached_image(image_id, target_size, size_option, original_width, original_height)
            if cached_image is not None:
                log_message(self.logger, f"Using cached image for ID: {image_id}", 'debug')
                return cached_image

        try:
            img = await process_single_image(
                self.session, 
                image_url, 
                size_option, 
                target_size,
                self.logger,
                self.check_cancelled,
                original_width, 
                original_height
            )
            
            if img is None:
                log_message(self.logger, f"Failed to process image: {image_id}", 'warning')
            elif cache_images:
                self.cache_image(image_id, img, target_size, size_option, original_width, original_height)

            return img
        except Exception as e:
            log_message(self.logger, f"Error processing image {image_id}: {str(e)}", 'error')
            return None

    def load_cached_image(self, image_id, target_size, size_option, original_width, original_height):
        log_message(self.logger, f"Attempting to load cached image: {image_id}", 'debug')
        cache_path = self.get_cache_path(image_id, target_size, size_option, original_width, original_height)
        if os.path.exists(cache_path):
            try:
                img = torch.load(cache_path)
                log_message(self.logger, f"Successfully loaded cached image: {image_id}", 'debug')
                return img
            except Exception as e:
                log_message(self.logger, f"Error loading cached image: {str(e)}", 'warning')
        else:
            log_message(self.logger, f"No cached image found for: {image_id}", 'debug')
        return None

    def cache_image(self, image_id, img_tensor, target_size, size_option, original_width, original_height):
        log_message(self.logger, f"Caching image: {image_id}", 'debug')
        os.makedirs(CACHE_DIR, exist_ok=True)
        cache_path = self.get_cache_path(image_id, target_size, size_option, original_width, original_height)
        try:
            torch.save(img_tensor, cache_path)
            log_message(self.logger, f"Successfully cached image: {image_id}", 'debug')
        except Exception as e:
            log_message(self.logger, f"Error caching image: {str(e)}", 'warning')

    def get_cache_path(self, image_id, target_size, size_option, original_width, original_height):
        if size_option == "Original Size":
            filename = f"{image_id}_original_{original_width}x{original_height}.pt"
        elif size_option == "Scale to Size":
            filename = f"{image_id}_scale_{target_size}.pt"
        elif size_option == "Crop to Size":
            filename = f"{image_id}_crop_{target_size}.pt"
        elif size_option == "Fill to Size":
            filename = f"{image_id}_fill_{target_size}.pt"
        else:
            filename = f"{image_id}_unknown_{target_size}.pt"
        return os.path.join(CACHE_DIR, filename)

    async def cleanup(self):
        log_message(self.logger, "Starting cleanup process", 'debug')
        if self.session:
            await self.session.close()
            log_message(self.logger, "Session closed", 'debug')

    def load_album_images(self, album_id, max_images, size_option, target_size, cache_images, client_secrets_file=None):
        start_time = time.time()
        log_message(self.logger, "Starting album image loading process", 'info')
        self.cancelled = False
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            log_message(self.logger, "No event loop found, creating a new one", 'warning')
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        try:
            result = loop.run_until_complete(self.load_album_images_async(
                album_id, max_images, size_option, target_size, cache_images, client_secrets_file
            ))
        except asyncio.CancelledError:
            log_message(self.logger, "Operation was cancelled", 'warning')
            loop.run_until_complete(self.cleanup())
            result = []
        except Exception as e:
            log_message(self.logger, f"Unexpected error: {str(e)}", 'error')
            loop.run_until_complete(self.cleanup())
            result = []

        end_time = time.time()
        total_time = end_time - start_time

        if not result:
            log_message(self.logger, "No images loaded from album, returning default tensor", 'warning')
            log_message(self.logger, f"Total processing time: {total_time:.2f} seconds", 'info')
            return ([torch.zeros((3, target_size, target_size))],)
        log_message(self.logger, f"Successfully loaded {len(result)} images from album", 'info')
        log_message(self.logger, f"Total processing time: {total_time:.2f} seconds", 'info')
        return (result,)

    def cancel(self):
        self.cancelled = True
        log_message(self.logger, "Cancellation requested", 'warning')
        for task in asyncio.all_tasks():
            task.cancel()

# Usage in ComfyUI
NODE_CLASS_MAPPINGS = {
    "Google Photos Album Loader": GooglePhotosAlbumLoader
}