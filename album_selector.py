import os
import json

PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))

class GooglePhotosAlbumSelector:
    @classmethod
    def INPUT_TYPES(s):
        albums = s.load_albums_from_json()
        album_choices = [f"{album['index']:04d} | {album['title']} | count: {album['mediaItemsCount']}" for album in albums]
        return {
            "required": {
                "selected_album": (album_choices,),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("album_id",)
    FUNCTION = "select_album"
    CATEGORY = "loaders"

    @staticmethod
    def load_albums_from_json():
        json_path = os.path.join(PLUGIN_DIR, "albums_list.json")
        if os.path.exists(json_path):
            with open(json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []

    def select_album(self, selected_album):
        albums = self.load_albums_from_json()
        selected_index = int(selected_album.split('|')[0].strip()) - 1
        selected_album_data = albums[selected_index]
        return (selected_album_data['id'],)