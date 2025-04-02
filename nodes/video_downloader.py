import os
import re
import glob
import requests
from pathlib import Path
import folder_paths


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