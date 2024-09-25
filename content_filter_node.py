class ContentFilterNode:
    @classmethod
    def INPUT_TYPES(s):
        categories = [
            "LANDSCAPES", "RECEIPTS", "CITYSCAPES", "LANDMARKS", "SELFIES", "PEOPLE",
            "PETS", "WEDDINGS", "BIRTHDAYS", "DOCUMENTS", "TRAVEL", "ANIMALS", "FOOD",
            "SPORT", "NIGHT", "PERFORMANCES", "WHITEBOARDS", "SCREENSHOTS", "UTILITY",
            "ARTS", "CRAFTS", "FASHION", "HOUSES", "GARDENS", "FLOWERS", "HOLIDAYS"
        ]
        
        return {
            "required": {
                **{cat.lower(): ("BOOLEAN", {"default": False}) for cat in categories},
            }
        }

    RETURN_TYPES = ("CONTENT_FILTER",)
    FUNCTION = "create_filter"
    CATEGORY = "Google Photos"

    def create_filter(self, **kwargs):
        selected_categories = [k.upper() for k, v in kwargs.items() if v]
        
        filter_dict = {
            "content_categories": selected_categories
        }
        
        return (filter_dict,)