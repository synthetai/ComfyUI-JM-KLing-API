import time

class ImageUpload:
    @classmethod
    def IS_CHANGED(cls, api_key, image, callback_selection):
        # Always refresh this node
        return time.time() 