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
import base64
from io import BytesIO


class KLingAIImageDownloader:
    """
    KLingAI Image Downloader Node
    Downloads image from URL and saves to local directory
    具有图片预览功能
    """

    def __init__(self):
        self.default_output_dir = folder_paths.get_output_directory()
        self.type = "image"
        self.output_dir = self.default_output_dir
        self.prefix = "KLingAI"
        self.last_downloaded_image = None

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
                "image": (["#DATA"], {"image_upload": True}),  # 添加支持上传图片的控件
                "image_data": ("STRING", {"default": "", "multiline": False}),
            },
            "optional": {
                "custom_output_dir": ("STRING", {
                    "default": "",
                    "multiline": False,
                    "placeholder": "Optional: Custom output directory path"
                }),
            }
        }

    RETURN_TYPES = ("IMAGE", "MASK", "STRING", "STRING")
    RETURN_NAMES = ("IMAGE", "MASK", "image_path", "image_url")
    FUNCTION = "process_image"
    CATEGORY = "JM-KLingAI-API"
    OUTPUT_NODE = True
    OUTPUT_IS_LIST = (False, False, False, False)

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

    def image_to_base64(self, pil_image):
        """
        将PIL图像转换为base64字符串
        """
        if pil_image is None:
            return ""
        
        buffered = BytesIO()
        pil_image.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        return f"data:image/png;base64,{img_str}"
    
    def download_image(self, image_url, filename_prefix="KLingAI", custom_output_dir=""):
        """
        Download image from URL and save to local directory
        """
        try:
            # 在实际执行时验证输入
            if image_url is None or (isinstance(image_url, str) and not image_url.strip()):
                error_msg = "图片URL不能为空"
                print(error_msg)
                # 创建小的空白图像用于显示错误信息
                empty_tensor = torch.zeros((1, 64, 64, 3), dtype=torch.float32)
                return (empty_tensor, error_msg, image_url)
                
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
                
                # 存储最后下载的图像以便在UI中显示
                self.last_downloaded_image = pil_image
                
                print(f"成功加载图片，尺寸: {pil_image.width}x{pil_image.height}")
                return (image_tensor, filepath, image_url)
            except Exception as e:
                print(f"图片加载错误: {str(e)}")
                # 创建小的空白图像
                empty_tensor = torch.zeros((1, 64, 64, 3), dtype=torch.float32)
                return (empty_tensor, filepath, image_url)

        except ValueError as ve:
            error_msg = f"参数错误: {str(ve)}"
            print(error_msg)
            # 创建小的空白图像
            empty_tensor = torch.zeros((1, 64, 64, 3), dtype=torch.float32)
            return (empty_tensor, error_msg, image_url)
        except requests.exceptions.RequestException as re:
            error_msg = f"下载错误: {str(re)}"
            print(error_msg)
            # 创建小的空白图像
            empty_tensor = torch.zeros((1, 64, 64, 3), dtype=torch.float32)
            return (empty_tensor, error_msg, image_url)
        except Exception as e:
            error_msg = f"图片下载错误: {str(e)}"
            print(error_msg)
            # 创建小的空白图像
            empty_tensor = torch.zeros((1, 64, 64, 3), dtype=torch.float32)
            return (empty_tensor, error_msg, image_url)

    def process_image(self, image_url, filename_prefix="KLingAI", image="#DATA", image_data="", custom_output_dir=""):
        """
        处理图片：如果提供了图片数据，直接处理；否则尝试下载URL中的图片
        """
        try:
            # 设置输出目录
            output_dir = custom_output_dir if custom_output_dir else self.default_output_dir
            output_dir = self.ensure_directory(output_dir)
            self.output_dir = output_dir
            self.prefix = filename_prefix
            
            # 默认掩码（全透明）
            mask = torch.zeros((64, 64), dtype=torch.float32, device="cpu").unsqueeze(0)
            
            # 如果提供了图片数据（通过上传）
            if image_data and image_data != "" and image_data.startswith("data:"):
                try:
                    # 解码base64图片数据
                    image_data_binary = base64.b64decode(image_data.split(",")[1])
                    i = Image.open(BytesIO(image_data_binary))
                    
                    # 转换图像格式
                    img_rgb = i.convert("RGB")
                    image_array = np.array(img_rgb).astype(np.float32) / 255.0
                    image_tensor = torch.from_numpy(image_array)[None,]
                    
                    # 检查是否有alpha通道，创建掩码
                    if 'A' in i.getbands():
                        alpha = np.array(i.getchannel('A')).astype(np.float32) / 255.0
                        mask = 1. - torch.from_numpy(alpha).unsqueeze(0)
                    
                    # 保存上传的图片
                    seq_num = self.get_next_sequence_number(output_dir, filename_prefix)
                    filepath = os.path.join(output_dir, f"{filename_prefix}_{seq_num:04d}.png")
                    img_rgb.save(filepath, "PNG")
                    print(f"上传的图片已保存至: {filepath}")
                    self.save_image_preview_info(filepath)
                    
                    return (image_tensor, mask, filepath, "本地上传")
                    
                except Exception as e:
                    print(f"处理上传的图片时出错: {str(e)}")
                    # 如果处理上传失败但有URL，则继续尝试下载
                    if not image_url or not image_url.strip():
                        raise ValueError(f"图片处理失败: {str(e)}")
            
            # 如果没有上传图片或处理失败，尝试从URL下载
            if image_url and image_url.strip():
                try:
                    filepath = self.download_image(image_url, output_dir, filename_prefix)
                    
                    # 加载下载的图片
                    pil_image = Image.open(filepath).convert("RGB")
                    image_array = np.array(pil_image).astype(np.float32) / 255.0
                    image_tensor = torch.from_numpy(image_array)[None,]
                    
                    # 转换为base64用于预览
                    image_data_base64 = self.image_to_base64(pil_image)
                    
                    print(f"成功加载图片，尺寸: {pil_image.width}x{pil_image.height}")
                    
                    return (image_tensor, mask, filepath, image_url)
                    
                except Exception as e:
                    print(f"从URL下载图片失败: {str(e)}")
                    if not image_data or image_data == "" or not image_data.startswith("data:"):
                        raise ValueError(f"无法下载图片: {str(e)}")
            
            # 如果没有提供有效的URL或图片数据
            if (not image_url or not image_url.strip()) and (not image_data or not image_data.startswith("data:")):
                raise ValueError("请提供有效的图片URL或上传图片")
                
            # 如果代码执行到这里，可能是前面的某个步骤成功但没有正确返回
            raise ValueError("未知错误，无法处理图片")
            
        except Exception as e:
            print(f"图片处理错误: {str(e)}")
            # 创建空白图像和掩码
            empty_tensor = torch.zeros((1, 64, 64, 3), dtype=torch.float32)
            empty_mask = torch.zeros((1, 64, 64), dtype=torch.float32)
            return (empty_tensor, empty_mask, f"错误: {str(e)}", image_url)

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
    def IS_CHANGED(cls, image_url, filename_prefix="KLingAI", image="#DATA", image_data="", custom_output_dir=""):
        # 如果有图片数据上传，返回图片数据的哈希值
        if image_data and image_data.startswith("data:"):
            import hashlib
            return hashlib.md5(image_data.encode()).hexdigest()
        # 否则使用当前时间，确保节点总是执行
        return time.time() 