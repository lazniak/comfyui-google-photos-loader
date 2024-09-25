import os
import shutil
from .logging_config import setup_logger, log_message

PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(PLUGIN_DIR, "image_cache")
logger = setup_logger('google_photos_clear_cache', os.path.join(PLUGIN_DIR, 'google_photos_clear_cache.log'))

class GooglePhotosCacheManager:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "max_cache_size_mb": ("INT", {"default": 5000, "min": 200, "max": 100000}),
                "clear_cache": ("BOOLEAN", {"default": False}),
            }
        }

    RETURN_TYPES = ()
    FUNCTION = "manage_cache"
    OUTPUT_NODE = True
    CATEGORY = "Google Photos"

    def manage_cache(self, max_cache_size_mb, clear_cache):
        if clear_cache:
            self.clear_cache()
        else:
            self.limit_cache_size(max_cache_size_mb)
        return ()

    def clear_cache(self):
        if os.path.exists(CACHE_DIR):
            try:
                shutil.rmtree(CACHE_DIR)
                log_message(logger, f"Successfully removed cache directory: {CACHE_DIR}", 'info')
            except Exception as e:
                log_message(logger, f"Error removing cache directory: {str(e)}", 'error')
        else:
            log_message(logger, f"Cache directory does not exist: {CACHE_DIR}", 'info')

    def limit_cache_size(self, max_size_mb):
        if not os.path.exists(CACHE_DIR):
            log_message(logger, f"Cache directory does not exist: {CACHE_DIR}", 'info')
            return

        total_size = sum(os.path.getsize(os.path.join(dirpath, filename)) 
                         for dirpath, _, filenames in os.walk(CACHE_DIR) 
                         for filename in filenames)
        
        total_size_mb = total_size / (1024 * 1024)
        log_message(logger, f"Current cache size: {total_size_mb:.2f} MB", 'info')

        if total_size_mb > max_size_mb:
            files = [(os.path.join(dirpath, filename), os.path.getmtime(os.path.join(dirpath, filename)))
                     for dirpath, _, filenames in os.walk(CACHE_DIR)
                     for filename in filenames]
            files.sort(key=lambda x: x[1])  # Sort by modification time

            while total_size_mb > max_size_mb and files:
                file_path, _ = files.pop(0)
                file_size = os.path.getsize(file_path) / (1024 * 1024)
                try:
                    os.remove(file_path)
                    total_size_mb -= file_size
                    log_message(logger, f"Removed {file_path} ({file_size:.2f} MB)", 'info')
                except Exception as e:
                    log_message(logger, f"Error removing {file_path}: {str(e)}", 'error')

            log_message(logger, f"Cache size after cleanup: {total_size_mb:.2f} MB", 'info')
        else:
            log_message(logger, "Cache size is within the limit", 'info')

NODE_CLASS_MAPPINGS = {
    "Google Photos Cache Manager": GooglePhotosCacheManager
}

PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(PLUGIN_DIR, "image_cache")
logger = setup_logger('google_photos_clear_cache', os.path.join(PLUGIN_DIR, 'google_photos_clear_cache.log'))

class GooglePhotosClearCache:
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {}}

    RETURN_TYPES = ()
    FUNCTION = "clear_cache"
    OUTPUT_NODE = True
    CATEGORY = "Google Photos"

    def clear_cache(self):
        if os.path.exists(CACHE_DIR):
            try:
                shutil.rmtree(CACHE_DIR)
                log_message(logger, f"Successfully removed cache directory: {CACHE_DIR}", 'info')
            except Exception as e:
                log_message(logger, f"Error removing cache directory: {str(e)}", 'error')
        else:
            log_message(logger, f"Cache directory does not exist: {CACHE_DIR}", 'info')
        return ()

NODE_CLASS_MAPPINGS = {
    "Google Photos Clear Cache": GooglePhotosClearCache
}

import os
from .logging_config import setup_logger, log_message
from .credentials_manager import get_credentials

PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))
logger = setup_logger('google_photos_login_logout', os.path.join(PLUGIN_DIR, 'google_photos_login_logout.log'))

class GooglePhotosLoginLogout:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "action": (["NONE", "LOGIN", "LOGOUT"],),
                "client_secrets_file": ("STRING", {"default": os.path.join(PLUGIN_DIR, "client_secrets.json"), "multiline": False}),
            }
        }

    RETURN_TYPES = ()
    FUNCTION = "manage_login"
    OUTPUT_NODE = True
    CATEGORY = "Google Photos"

    def manage_login(self, action, client_secrets_file):
        if action == "LOGIN":
            self.login(client_secrets_file)
        elif action == "LOGOUT":
            self.logout()
        else:  # NONE
            log_message(logger, "No action performed", 'info')
        return ()

    def login(self, client_secrets_file):
        try:
            creds = get_credentials(client_secrets_file, PLUGIN_DIR, logger)
            if creds and creds.valid:
                log_message(logger, "Successfully logged in to Google Photos", 'info')
            else:
                log_message(logger, "Failed to log in to Google Photos", 'error')
        except Exception as e:
            log_message(logger, f"Error during login: {str(e)}", 'error')

    def logout(self):
        token_path = os.path.join(PLUGIN_DIR, 'token.pickle')
        if os.path.exists(token_path):
            try:
                os.remove(token_path)
                log_message(logger, "Successfully removed token file. User logged out.", 'info')
            except Exception as e:
                log_message(logger, f"Error removing token file: {str(e)}", 'error')
        else:
            log_message(logger, "No token file found. User might already be logged out.", 'info')

NODE_CLASS_MAPPINGS = {
    "Google Photos Login/Logout": GooglePhotosLoginLogout
}