import json
import requests
from threading import Thread, Event


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