import time
import jwt
import requests
import json
from threading import Thread, Event
import os
from pathlib import Path
import folder_paths
import re
import glob
import random
from datetime import datetime


class KLingAIVideoDownloader:
    """
    KLingAI Video Downloader Node
    Downloads video from URL and saves to local directory
    """

    def __init__(self):
        self.default_output_dir = folder_paths.get_output_directory()
        self.type = "video"

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "video_url": ("STRING", {"default": "", "multiline": False}),
                "filename_prefix": ("STRING", {
                    "default": "KLingAI",
                    "multiline": False,
                    "placeholder": "Base filename for downloaded video"
                }),
            },
            "optional": {
                "custom_output_dir": ("STRING", {
                    "default": "",
                    "multiline": False,
                    "placeholder": "Optional: Custom output directory path"
                }),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("video_path",)
    FUNCTION = "download_video"
    CATEGORY = "JM-KLingAI-API"

    def get_next_sequence_number(self, directory, filename_prefix):
        """
        Get the next sequence number for the video file
        """
        pattern = f"{filename_prefix}_*.mp4"
        existing_files = glob.glob(os.path.join(directory, pattern))

        if not existing_files:
            return 1

        numbers = []
        for f in existing_files:
            match = re.search(f"{filename_prefix}_(\d+)\.mp4$", f)
            if match:
                numbers.append(int(match.group(1)))

        return max(numbers) + 1 if numbers else 1

    def ensure_directory(self, directory):
        """
        Ensure the directory exists, create if it doesn't
        """
        Path(directory).mkdir(parents=True, exist_ok=True)
        return directory

    def download_video(self, video_url, filename_prefix="KLingAI", custom_output_dir=""):
        """
        Download video from URL and save to local directory
        """
        try:
            # Validate inputs
            if not video_url:
                raise ValueError("Video URL is required")
            if not filename_prefix:
                filename_prefix = "KLingAI"

            # Determine output directory
            output_dir = custom_output_dir if custom_output_dir else self.default_output_dir
            output_dir = self.ensure_directory(output_dir)

            # Get next sequence number
            seq_num = self.get_next_sequence_number(output_dir, filename_prefix)

            # Create filename
            filename = f"{filename_prefix}_{seq_num:04d}.mp4"
            filepath = os.path.join(output_dir, filename)

            # Download video
            print(f"Downloading video from {video_url}")
            response = requests.get(video_url, stream=True)
            response.raise_for_status()

            # Save video
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            print(f"Video successfully downloaded to: {filepath}")
            return (filepath,)

        except ValueError as ve:
            print(f"Validation Error: {str(ve)}")
            return (None,)
        except requests.exceptions.RequestException as re:
            print(f"Download Error: {str(re)}")
            return (None,)
        except Exception as e:
            print(f"Error downloading video: {str(e)}")
            return (None,)

class KLingAIQueryStatus:
    """
    KLingAI Query Task Status Node
    Queries the status of a text-to-video generation task
    """

    def __init__(self):
        self.api_base = "https://api.klingai.com"
        self.endpoint = "/v1/videos/text2video/{}"
        self.stop_thread = Event()
        self.current_thread = None

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "api_token": ("STRING", {"default": "", "multiline": False}),
                "task_id": ("STRING", {"default": "", "multiline": False}),
            },
            "optional": {
                "external_task_id": ("STRING", {
                    "default": "",
                    "multiline": False,
                    "placeholder": "Optional: External task ID"
                }),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("video_url",)
    FUNCTION = "query_task_status"
    CATEGORY = "JM-KLingAI-API"

    def poll_status(self, api_token, task_id, external_task_id):
        """
        Polls the task status every 10 seconds until completion
        """
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_token}"
        }

        while not self.stop_thread.is_set():
            try:
                # Determine which ID to use
                query_id = task_id if task_id else external_task_id
                url = f"{self.api_base}{self.endpoint.format(query_id)}"

                response = requests.get(url, headers=headers)
                response_data = response.json()

                if response.status_code != 200:
                    print(f"Error in status query: {response_data.get('message', 'Unknown error')}")
                    return None

                data = response_data.get("data", {})
                status = data.get("task_status")

                print(f"Current task status: {status}")

                if status == "succeed":
                    videos = data.get("task_result", {}).get("videos", [])
                    if videos:
                        return videos[0].get("url")
                    return None
                elif status == "failed":
                    print(f"Task failed: {data.get('task_status_msg', 'Unknown error')}")
                    return None

                # Wait 10 seconds before next poll
                self.stop_thread.wait(10)

            except Exception as e:
                print(f"Error during status polling: {str(e)}")
                return None

        return None

    def query_task_status(self, api_token, task_id, external_task_id=""):
        """
        Start polling task status
        """
        try:
            # Validate inputs
            if not api_token:
                raise ValueError("API token is required")
            if not task_id and not external_task_id:
                raise ValueError("Either task_id or external_task_id must be provided")

            # Stop any existing polling thread
            if self.current_thread and self.current_thread.is_alive():
                self.stop_thread.set()
                self.current_thread.join()

            # Reset stop event
            self.stop_thread.clear()

            # Start new polling thread
            self.current_thread = Thread(
                target=self.poll_status,
                args=(api_token, task_id, external_task_id)
            )
            self.current_thread.start()

            # Wait for result
            self.current_thread.join()

            # Get result
            video_url = self.poll_status(api_token, task_id, external_task_id)

            if video_url:
                print(f"Task completed successfully. Video URL: {video_url}")
                return (video_url,)
            else:
                print("Task completed but no video URL available")
                return (None,)

        except ValueError as ve:
            print(f"Validation Error: {str(ve)}")
            return (None,)
        except Exception as e:
            print(f"Error querying task status: {str(e)}")
            return (None,)

    def __del__(self):
        """
        Cleanup when node is destroyed
        """
        if self.current_thread and self.current_thread.is_alive():
            self.stop_thread.set()
            self.current_thread.join()


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
    CATEGORY = "JM-KLingAI-API"

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
            return (None, None, None, None, seed)
        except Exception as e:
            print(f"Error creating video task: {str(e)}")
            return (None, None, None, None, seed)

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
                "exp": current_time + 1800,  # 30分钟后过期
                "nbf": current_time - 5  # 5秒前开始生效
            }
            
            token = jwt.encode(payload, secret_key, headers=headers)
            print(f"Generated fresh JWT token, valid until: {datetime.fromtimestamp(current_time + 1800)}")
            
            return (token,)
            
        except Exception as e:
            print(f"Error generating API token: {str(e)}")
            return (None,)

    def IS_CHANGED(self, access_key, secret_key):
        """
        Always return a different value to ensure token is regenerated each time
        """
        return time.time()
