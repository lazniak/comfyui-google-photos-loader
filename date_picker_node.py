import datetime

class DatePickerNode:
    @classmethod
    def INPUT_TYPES(s):
        current_date = datetime.date.today()
        return {
            "required": {
                "year": ("INT", {
                    "default": current_date.year, 
                    "min": 1900, 
                    "max": 2100,
                    "step": 1,
                }),
                "month": ("INT", {
                    "default": current_date.month, 
                    "min": 1, 
                    "max": 12,
                    "step": 1,
                }),
                "day": ("INT", {
                    "default": current_date.day, 
                    "min": 1, 
                    "max": 31,
                    "step": 1,
                }),
            },
        }

    RETURN_TYPES = ("STRING",)
    FUNCTION = "pick_date"
    CATEGORY = "utils"

    def pick_date(self, year, month, day):
        try:
            date = datetime.date(year, month, day)
            return (date.strftime("%Y-%m-%d"),)
        except ValueError as e:
            print(f"Invalid date: {e}")
            return (datetime.date.today().strftime("%Y-%m-%d"),)

NODE_CLASS_MAPPINGS = {
    "DatePicker": DatePickerNode
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "DatePicker": "Date Picker 📅"
}