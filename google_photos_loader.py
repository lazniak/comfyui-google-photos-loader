import os
import torch
import asyncio
import aiohttp
import time
from .google_photos_api import batch_load_from_album
from .image_processing import process_single_image
from .credentials_manager import get_credentials
from .progress_bar import MultiProgressBar
from .logging_config import setup_logger, log_message
from datetime import datetime

PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(PLUGIN_DIR, "image_cache")

logger = setup_logger('google_photos_loader', os.path.join(PLUGIN_DIR, 'google_photos_loader.log'))

class GooglePhotosImagesLoader:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "max_images": ("INT", {"default": 10, "min": 1, "max": 5000}),
                "start_from": ("INT", {"default": 0, "min": 0, "max": 10000}),
                "size_option": (["Original Size", "Scale to Size", "Crop to Size", "Fill to Size"],),
                "target_size": ("INT", {"default": 512, "min": 64, "max": 2048}),
                "cache_images": ("BOOLEAN", {"default": True}),
                "remove_cache": ("BOOLEAN", {"default": False}),
                "advanced_logs": ("BOOLEAN", {"default": False}),
            },
            "optional": {
                "client_secrets_file": ("STRING", {"default": os.path.join(PLUGIN_DIR, "client_secrets.json"), "multiline": False}),
                "positive_custom_filters": ("CONTENT_FILTER",),
                "negative_custom_filters": ("CONTENT_FILTER",),
                "specific_year": ("INT", {"default": 0, "min": 0, "max": 9999}),
                "specific_month": ("INT", {"default": 0, "min": 0, "max": 12}),
                "specific_day": ("INT", {"default": 0, "min": 0, "max": 31}),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "load_images"
    CATEGORY = "loaders"
    OUTPUT_IS_LIST = (True,)

    def __init__(self):
        self.logger = logger  # Upewnij się, że ta linia jest obecna
        self.progress_bars = MultiProgressBar(self.logger)
        self.cancelled = False
        self.session = None
        self.advanced_logs = False

    def check_cancelled(self):
        if self.cancelled:
            log_message(self.logger, "Operation cancelled", 'warning')
            raise asyncio.CancelledError("Operation cancelled by user")

    async def load_images_async(self, max_images, start_from, size_option, target_size, cache_images, remove_cache, 
                                positive_custom_filters, negative_custom_filters, 
                                specific_year, specific_month, specific_day, client_secrets_file, advanced_logs):
        self.advanced_logs = advanced_logs
        log_message(self.logger, f"Starting image loading process. Parameters: max_images={max_images}, start_from={start_from}, size_option={size_option}, target_size={target_size}", 'info')

        self.check_cancelled()

        if remove_cache:
            self.remove_cache()

        try:
            creds = get_credentials(client_secrets_file, PLUGIN_DIR, self.logger)
            if not creds or not creds.valid:
                raise ValueError("Invalid credentials")
        except Exception as e:
            log_message(self.logger, f"Failed to obtain credentials: {str(e)}", 'error')
            raise

        self.session = aiohttp.ClientSession()
        try:
            total_images_to_fetch = start_from + max_images
            self.progress_bars.add_bar("load_images", total_images_to_fetch, "Loading images", "items")
            
            filters = self.prepare_filters(positive_custom_filters, negative_custom_filters, 
                                           specific_year, specific_month, specific_day)
            
            all_media_items = await batch_load_from_album(
                self.session, creds, None, max_images, None, "PHOTO", 
                None, None, None, False, 
                False, self.progress_bars, self.check_cancelled,
                custom_filters=filters, start_from=start_from, logger=self.logger
            )
            
            self.progress_bars.remove_bar("load_images")
            
            if not all_media_items:
                log_message(self.logger, "No images found. This may be due to an API limitation or permission issue.", 'warning')
                return []
            
            log_message(self.logger, f"Retrieved {len(all_media_items)} media items", 'info')
        
            self.progress_bars.add_bar("process_images", len(all_media_items), "Processing images", "images")
            images = await self.process_images_parallel(all_media_items, size_option, target_size, cache_images)
            self.progress_bars.remove_bar("process_images")
            
            processed_count = len(images)
            log_message(self.logger, f"Successfully processed {processed_count} out of {len(all_media_items)} images", 'info')
            
            if processed_count < max_images:
                log_message(self.logger, f"Warning: Requested {max_images} images, but only processed {processed_count}", 'warning')
            
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
        semaphore = asyncio.Semaphore(10)  # Limit concurrent processing to 10
        async def process_with_semaphore(item):
            async with semaphore:
                return await self.process_image(item['baseUrl'], size_option, target_size, item['id'], cache_images, 
                                                int(item.get('mediaMetadata', {}).get('width', 0)),
                                                int(item.get('mediaMetadata', {}).get('height', 0)))
        
        tasks = [asyncio.create_task(process_with_semaphore(item)) for item in media_items]
        processed_images = await asyncio.gather(*tasks)
        return [img for img in processed_images if img is not None]

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

    def remove_cache(self):
        log_message(self.logger, f"Attempting to remove cache directory: {CACHE_DIR}", 'info')
        if os.path.exists(CACHE_DIR):
            try:
                import shutil
                shutil.rmtree(CACHE_DIR)
                log_message(self.logger, f"Cache directory removed: {CACHE_DIR}", 'info')
            except Exception as e:
                log_message(self.logger, f"Error removing cache directory: {str(e)}", 'error')
        else:
            log_message(self.logger, f"Cache directory does not exist: {CACHE_DIR}", 'info')

    async def cleanup(self):
        log_message(self.logger, "Starting cleanup process", 'debug')
        if self.session:
            await self.session.close()
            log_message(self.logger, "Session closed", 'debug')

    def prepare_filters(self, positive_filters, negative_filters, specific_year, specific_month, specific_day):
        filters = {}
        
        # Prepare content filter
        content_filter = {}
        if positive_filters:
            included_categories = positive_filters.get("content_categories", [])
            if included_categories:
                content_filter["includedContentCategories"] = included_categories
        
        if negative_filters:
            excluded_categories = negative_filters.get("content_categories", [])
            if excluded_categories:
                content_filter["excludedContentCategories"] = excluded_categories
        
        if content_filter:
            filters["contentFilter"] = content_filter
        
        # Prepare date filter
        if specific_year or specific_month or specific_day:
            date_filter = {"dates": [{}]}
            if specific_year and 0 < specific_year <= 9999:
                date_filter["dates"][0]["year"] = specific_year
            if specific_month and 1 <= specific_month <= 12:
                date_filter["dates"][0]["month"] = specific_month
            if specific_day and 1 <= specific_day <= 31:
                date_filter["dates"][0]["day"] = specific_day
            
            if date_filter["dates"][0]:  # Only add if not empty
                filters["dateFilter"] = date_filter
        
        return filters

    def load_images(self, max_images, start_from, size_option, target_size, cache_images, remove_cache, advanced_logs,
                    client_secrets_file=None, positive_custom_filters=None, negative_custom_filters=None, 
                    specific_year=0, specific_month=0, specific_day=0):
        self.advanced_logs = advanced_logs
        log_message(self.logger, "Starting image loading process", 'info')
        self.cancelled = False
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            log_message(self.logger, "No event loop found, creating a new one", 'warning')
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        try:
            result = loop.run_until_complete(self.load_images_async(
                max_images, start_from, size_option, target_size, cache_images, remove_cache, 
                positive_custom_filters, negative_custom_filters, 
                specific_year, specific_month, specific_day, client_secrets_file, advanced_logs
            ))
        except asyncio.CancelledError:
            log_message(self.logger, "Operation was cancelled", 'warning')
            loop.run_until_complete(self.cleanup())
            result = []
        except Exception as e:
            log_message(self.logger, f"Unexpected error: {str(e)}", 'error')
            loop.run_until_complete(self.cleanup())
            result = []

        if not result:
            log_message(self.logger, "No images loaded, returning default tensor", 'warning')
            return ([torch.zeros((3, target_size, target_size))],)
        log_message(self.logger, f"Successfully loaded {len(result)} images", 'info')
        return (result,)

    def cancel(self):
        self.cancelled = True
        log_message(self.logger, "Cancellation requested", 'warning')
        for task in asyncio.all_tasks():
            task.cancel()

# Usage in ComfyUI
NODE_CLASS_MAPPINGS = {
    "Google Photos Images Loader": GooglePhotosImagesLoader
}