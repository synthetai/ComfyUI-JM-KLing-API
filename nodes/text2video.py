import json
import random
import requests


class KLingAIText2Video:
    """
    KLingAI Text to Video Node
    Creates a text-to-video generation task
    """
    
    def __init__(self):
        self.api_base = "https://api.klingai.com"
        self.endpoint = "/v1/videos/text2video"
        
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "api_token": ("STRING", {"default": "", "multiline": False}),
                "prompt": ("STRING", {
                    "default": "", 
                    "multiline": True,
                    "placeholder": "Enter your prompt here (max 2500 characters)"
                }),
            },
            "optional": {
                "model_name": (["kling-v1", "kling-v1-6"], {"default": "kling-v1"}),
                "negative_prompt": ("STRING", {
                    "default": "",
                    "multiline": True,
                    "placeholder": "Enter negative prompt (max 2500 characters)"
                }),
                "cfg_scale": ("FLOAT", {
                    "default": 0.5,
                    "min": 0.0,
                    "max": 1.0,
                    "step": 0.1
                }),
                "mode": (["std", "pro"], {"default": "std"}),
                "aspect_ratio": (["16:9", "9:16", "1:1"], {"default": "16:9"}),
                "duration": (["5", "10"], {"default": "5"}),
                "seed": ("INT", {
                    "default": -1,
                    "min": -1,
                    "max": 0xffffffffffffffff
                }),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING", "INT")
    RETURN_NAMES = ("task_id", "task_status", "created_at", "updated_at", "seed")
    FUNCTION = "create_video_task"
    CATEGORY = "JM-KLingAI-API/text-2-video"

    def create_video_task(self, api_token, prompt, model_name="kling-v1", 
                         negative_prompt="", cfg_scale=0.5, mode="std",
                         aspect_ratio="16:9", duration="5", seed=-1):
        """
        Create a text-to-video generation task
        """
        try:
            # Validate inputs
            if not api_token:
                raise ValueError("API token is required")
            if not prompt or len(prompt) > 2500:
                raise ValueError("Prompt is required and cannot exceed 2500 characters")
            if negative_prompt and len(negative_prompt) > 2500:
                raise ValueError("Negative prompt cannot exceed 2500 characters")

            # Generate random seed if not provided or -1 (only for local use)
            if seed == -1:
                seed = random.randint(0, 0xffffffffffffffff)

            # Prepare request headers
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_token.strip()}"
            }

            # Prepare request payload
            payload = {
                "model_name": model_name,
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "cfg_scale": float(cfg_scale),
                "mode": mode,
                "aspect_ratio": aspect_ratio,
                "duration": duration
            }

            # Make API request
            url = f"{self.api_base}{self.endpoint}"
            print(f"Making request to: {url}")
            print(f"With payload: {json.dumps(payload, indent=2)}")
            print(f"Using local seed: {seed} (not sent to API)")
            
            response = requests.post(url, headers=headers, json=payload)
            response_data = response.json()
            
            print(f"Response status: {response.status_code}")
            print(f"Response data: {json.dumps(response_data, indent=2)}")

            # Check for errors and provide detailed error messages
            if response.status_code != 200:
                error_code = response_data.get('code')
                error_message = response_data.get('message')
                request_id = response_data.get('request_id')
                raise Exception(f"API request failed (Code: {error_code}): {error_message} (Request ID: {request_id})")

            # Extract response data
            data = response_data.get("data", {})
            task_id = data.get("task_id", "")
            task_status = data.get("task_status", "")
            created_at = str(data.get("created_at", ""))
            updated_at = str(data.get("updated_at", ""))

            if not task_id:
                raise Exception("No task ID received from API")

            print(f"Successfully created video task with ID: {task_id} (local seed: {seed})")
            return (task_id, task_status, created_at, updated_at, seed)

        except ValueError as ve:
            print(f"Validation Error: {str(ve)}")
            return (f"Error: {str(ve)}", "failed", "", "", seed)
        except Exception as e:
            print(f"Error creating video task: {str(e)}")
            return (f"Error: {str(e)}", "failed", "", "", seed)

    def IS_CHANGED(self, api_token, prompt, model_name="kling-v1", 
                  negative_prompt="", cfg_scale=0.5, mode="std",
                  aspect_ratio="16:9", duration="5", seed=-1):
        """
        This method is called to determine if the node should be re-executed.
        We use the seed to control re-execution.
        """
        if seed == -1:
            return random.randint(0, 0xffffffffffffffff)
        return seed 