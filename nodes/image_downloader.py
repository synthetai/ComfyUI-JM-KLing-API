import os
import re
import glob
import requests
from pathlib import Path
import folder_paths
import time
import json
import torch
import numpy as np
from PIL import Image


class KLingAIImageDownloader:
    """
    KLingAI Image Downloader Node
    Downloads image from URL and saves to local directory
    """

    def __init__(self):
        self.default_output_dir = folder_paths.get_output_directory()
        self.type = "image"

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "image_url": ("STRING", {"default": "", "multiline": False}),
                "filename_prefix": ("STRING", {
                    "default": "KLingAI",
                    "multiline": False,
                    "placeholder": "Base filename for downloaded image"
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

    RETURN_TYPES = ("STRING", "STRING", "IMAGE")
    RETURN_NAMES = ("image_path", "image_url", "image")
    FUNCTION = "download_image"
    CATEGORY = "JM-KLingAI-API"
    OUTPUT_NODE = True  # 标记为可作为终端节点的节点
    OUTPUT_IS_LIST = (False, False, False)  # 指示输出不是列表

    def get_next_sequence_number(self, directory, filename_prefix):
        """
        Get the next sequence number for the image file
        """
        # 支持常见的图片格式
        patterns = [
            f"{filename_prefix}_*.png",
            f"{filename_prefix}_*.jpg",
            f"{filename_prefix}_*.jpeg",
            f"{filename_prefix}_*.webp"
        ]
        
        existing_files = []
        for pattern in patterns:
            existing_files.extend(glob.glob(os.path.join(directory, pattern)))

        if not existing_files:
            return 1

        numbers = []
        for f in existing_files:
            # 匹配不同格式的文件名
            match = re.search(f"{filename_prefix}_(\d+)\.(png|jpg|jpeg|webp)$", f)
            if match:
                numbers.append(int(match.group(1)))

        return max(numbers) + 1 if numbers else 1

    def ensure_directory(self, directory):
        """
        Ensure the directory exists, create if it doesn't
        """
        Path(directory).mkdir(parents=True, exist_ok=True)
        return directory

    def download_image(self, image_url, filename_prefix="KLingAI", custom_output_dir=""):
        """
        Download image from URL and save to local directory
        """
        try:
            # 在实际执行时验证输入
            if image_url is None or (isinstance(image_url, str) and not image_url.strip()):
                error_msg = "图片URL不能为空"
                print(error_msg)
                return (error_msg, image_url, None)
                
            if not filename_prefix:
                filename_prefix = "KLingAI"

            # Determine output directory
            output_dir = custom_output_dir if custom_output_dir else self.default_output_dir
            output_dir = self.ensure_directory(output_dir)

            # Get next sequence number
            seq_num = self.get_next_sequence_number(output_dir, filename_prefix)

            # 检测图片格式
            image_format = "png"  # 默认格式
            if ".jpg" in image_url.lower() or ".jpeg" in image_url.lower():
                image_format = "jpg"
            elif ".webp" in image_url.lower():
                image_format = "webp"

            # Create filename
            filename = f"{filename_prefix}_{seq_num:04d}.{image_format}"
            filepath = os.path.join(output_dir, filename)

            # Download image
            print(f"正在从 {image_url} 下载图片")
            response = requests.get(image_url, stream=True)
            response.raise_for_status()

            # Save image
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            print(f"图片成功下载到: {filepath}")
            
            # 为了确保在历史记录中显示，创建预览信息
            self.save_image_preview_info(filepath)
            
            # 加载图片并转换为ComfyUI可用的格式
            try:
                # 打开图片并转换为RGB
                pil_image = Image.open(filepath).convert('RGB')
                # 转换为numpy数组，并规范化到0-1范围
                image_array = np.array(pil_image).astype(np.float32) / 255.0
                # 转换为PyTorch张量
                image_tensor = torch.from_numpy(image_array)[None,]
                
                print(f"成功加载图片，尺寸: {pil_image.width}x{pil_image.height}")
                return (filepath, image_url, image_tensor)
            except Exception as e:
                print(f"图片加载错误: {str(e)}")
                return (filepath, image_url, None)

        except ValueError as ve:
            error_msg = f"参数错误: {str(ve)}"
            print(error_msg)
            return (error_msg, image_url, None)  # 返回错误消息而不是None
        except requests.exceptions.RequestException as re:
            error_msg = f"下载错误: {str(re)}"
            print(error_msg)
            return (error_msg, image_url, None)  # 返回错误消息而不是None
        except Exception as e:
            error_msg = f"图片下载错误: {str(e)}"
            print(error_msg)
            return (error_msg, image_url, None)  # 返回错误消息而不是None

    def save_image_preview_info(self, filepath):
        """
        保存图片预览信息以确保在历史记录中显示
        """
        try:
            # 获取相对路径以便在UI中正确显示
            rel_path = os.path.relpath(filepath, start=self.default_output_dir)
            
            # 确定图片格式
            file_ext = os.path.splitext(filepath)[1].lower()
            mime_type = "image/png"
            if file_ext in [".jpg", ".jpeg"]:
                mime_type = "image/jpeg"
            elif file_ext == ".webp":
                mime_type = "image/webp"
            
            file_info = {
                "filename": os.path.basename(filepath),
                "type": "image",
                "subfolder": os.path.dirname(rel_path) if os.path.dirname(rel_path) else "",
                "format": mime_type
            }
            
            # 获取文件大小
            file_size = os.path.getsize(filepath)
            file_info["size"] = f"{file_size / (1024 * 1024):.2f} MB"
            
            # 打印预览信息
            print(f"图片文件信息: {json.dumps(file_info, ensure_ascii=False)}")
            
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
    def IS_CHANGED(cls, image_url, filename_prefix="KLingAI", custom_output_dir=""):
        # 返回当前时间，确保节点总是执行
        return time.time() 