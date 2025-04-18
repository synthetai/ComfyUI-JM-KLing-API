import time
import jwt
from datetime import datetime


class KLingAIAPIKey:
    """
    KLingAI API Key Node
    Generates fresh JWT token for each execution
    """
    
    def __init__(self):
        self.api_base = "https://api.klingai.com"
        
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "access_key": ("STRING", {
                    "default": "", 
                    "multiline": False,
                    "placeholder": "Enter your Access Key here"
                }),
                "secret_key": ("STRING", {
                    "default": "", 
                    "multiline": False,
                    "placeholder": "Enter your Secret Key here"
                }),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("api_token",)
    FUNCTION = "generate_token"
    CATEGORY = "JM-KLingAI-API"

    def generate_token(self, access_key, secret_key):
        """
        Generate a fresh JWT token for each execution
        """
        try:
            # Validate inputs
            if not access_key or not secret_key:
                raise ValueError("Access Key and Secret Key are required")

            # Generate fresh JWT token
            headers = {
                "alg": "HS256",
                "typ": "JWT"
            }
            
            current_time = int(time.time())
            payload = {
                "iss": access_key,
                "exp": current_time + 7200,  # 30分钟后过期
                "nbf": current_time - 5  # 5秒前开始生效
            }
            
            token = jwt.encode(payload, secret_key, headers=headers)
            print(f"Generated fresh JWT token, valid until: {datetime.fromtimestamp(current_time + 1800)}")
            
            return (token,)
            
        except Exception as e:
            print(f"Error generating API token: {str(e)}")
            return (None,)

    @classmethod
    def IS_CHANGED(cls, access_key, secret_key):
        """
        Always return a different value to ensure token is regenerated each time
        """
        return time.time() 