from .google_photos_loader import GooglePhotosImagesLoader
from .album_lister import GooglePhotosAlbumLister
from .album_selector import GooglePhotosAlbumSelector
from .google_photos_album_loader import GooglePhotosAlbumLoader
from .google_photos_api import batch_load_from_album, batch_list_albums, batch_search_photos
from .image_processing import process_single_image
from .progress_bar import MultiProgressBar
from .credentials_manager import get_credentials
from .date_picker_node import DatePickerNode
from .content_filter_node import ContentFilterNode
from .google_photos_utils import GooglePhotosCacheManager, GooglePhotosLoginLogout

__all__ = [
    'GooglePhotosImagesLoader',
    'GooglePhotosAlbumLister',
    'GooglePhotosAlbumSelector',
    'GooglePhotosAlbumLoader',
    'batch_load_from_album',
    'batch_list_albums',
    'batch_search_photos',
    'process_single_image',
    'MultiProgressBar',
    'get_credentials',
    'DatePickerNode',
    'ContentFilterNode',
    'GooglePhotosCacheManager',
    'GooglePhotosLoginLogout'
]

NODE_CLASS_MAPPINGS = {
    "Google Photos Images Loader": GooglePhotosImagesLoader,
    "Google Photos Album Lister": GooglePhotosAlbumLister,
    "Google Photos Album Selector": GooglePhotosAlbumSelector,
    "Google Photos Album Loader": GooglePhotosAlbumLoader,
    "DatePicker": DatePickerNode,
    "ContentFilter": ContentFilterNode,
    "Google Photos Cache Manager": GooglePhotosCacheManager,
    "Google Photos Login/Logout": GooglePhotosLoginLogout
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "Google Photos Images Loader": "Google Photos Images Loader 📷",
    "Google Photos Album Lister": "Google Photos Album Lister 📋",
    "Google Photos Album Selector": "Google Photos Album Selector 🎚️",
    "Google Photos Album Loader": "Google Photos Album Loader 🖼️",
    "DatePicker": "Date Picker 📅",
    "ContentFilter": "Content Filter 🔍",
    "Google Photos Cache Manager": "Google Photos Cache Manager 🗑️",
    "Google Photos Login/Logout": "Google Photos Login/Logout 🔑"
}