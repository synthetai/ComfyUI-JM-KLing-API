import os
import re
import glob
import requests
from pathlib import Path
import folder_paths
import time
import json


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
    OUTPUT_NODE = True  # 标记为可作为终端节点的节点
    OUTPUT_IS_LIST = (False,)  # 指示输出不是列表

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
            # 在实际执行时验证输入
            if video_url is None or (isinstance(video_url, str) and not video_url.strip()):
                error_msg = "视频URL不能为空"
                print(error_msg)
                return (error_msg,)
                
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
            print(f"正在从 {video_url} 下载视频")
            response = requests.get(video_url, stream=True)
            response.raise_for_status()

            # Save video
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            print(f"视频成功下载到: {filepath}")
            
            # 为了确保在历史记录中显示，创建预览信息
            self.save_video_preview_info(filepath)
            
            return (filepath,)

        except ValueError as ve:
            error_msg = f"参数错误: {str(ve)}"
            print(error_msg)
            return (error_msg,)  # 返回错误消息而不是None
        except requests.exceptions.RequestException as re:
            error_msg = f"下载错误: {str(re)}"
            print(error_msg)
            return (error_msg,)  # 返回错误消息而不是None
        except Exception as e:
            error_msg = f"视频下载错误: {str(e)}"
            print(error_msg)
            return (error_msg,)  # 返回错误消息而不是None

    def save_video_preview_info(self, filepath):
        """
        保存视频预览信息以确保在历史记录中显示
        """
        try:
            # 获取相对路径以便在UI中正确显示
            rel_path = os.path.relpath(filepath, start=self.default_output_dir)
            file_info = {
                "filename": os.path.basename(filepath),
                "type": "video",
                "subfolder": os.path.dirname(rel_path) if os.path.dirname(rel_path) else "",
                "format": "video/mp4"
            }
            
            # 获取文件大小
            file_size = os.path.getsize(filepath)
            file_info["size"] = f"{file_size / (1024 * 1024):.2f} MB"
            
            # 打印预览信息
            print(f"视频文件信息: {json.dumps(file_info, ensure_ascii=False)}")
            
            # 尝试将信息写入预览文件
            preview_dir = os.path.join(self.default_output_dir, ".previews")
            if not os.path.exists(preview_dir):
                os.makedirs(preview_dir, exist_ok=True)
                
            preview_file = os.path.join(preview_dir, f"{os.path.basename(filepath)}.json")
            with open(preview_file, 'w', encoding='utf-8') as f:
                json.dump(file_info, f, ensure_ascii=False, indent=2)
                
            print(f"已保存预览信息: {preview_file}")
        except Exception as e:
            print(f"保存预览信息出错 (不影响下载): {str(e)}")

    # 确保节点可以在没有连接的情况下运行
    @classmethod
    def IS_CHANGED(cls, video_url, filename_prefix="KLingAI", custom_output_dir=""):
        # 返回当前时间，确保节点总是执行
        return time.time() 