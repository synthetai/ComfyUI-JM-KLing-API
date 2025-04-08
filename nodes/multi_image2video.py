import json
import random
import requests
import base64
import io
import torch
import numpy as np
from PIL import Image
import time


class KLingAIMultiImage2Video:
    """
    KLingAI Multi-Image to Video Node
    创建多图生视频任务节点
    """
    
    def __init__(self):
        self.api_base = "https://api.klingai.com"
        self.endpoint = "/v1/videos/multi-image2video"
        
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "api_token": ("STRING", {"default": "", "multiline": False}),
                "prompt": ("STRING", {
                    "default": "", 
                    "multiline": True,
                    "placeholder": "正向提示词 (必须填写，最多2500字符)"
                }),
                "image1": ("IMAGE",),
            },
            "optional": {
                "image2": ("IMAGE",),
                "image3": ("IMAGE",),
                "image4": ("IMAGE",),
                "model_name": (["kling-v1-6"], {"default": "kling-v1-6"}),
                "negative_prompt": ("STRING", {
                    "default": "",
                    "multiline": True,
                    "placeholder": "负向提示词 (最多2500字符)"
                }),
                "mode": (["std", "pro"], {"default": "std"}),
                "duration": (["5", "10"], {"default": "5"}),
                "aspect_ratio": (["16:9", "9:16", "1:1"], {"default": "16:9"}),
                "external_task_id": ("STRING", {
                    "default": "",
                    "multiline": False,
                    "placeholder": "可选：自定义任务ID（需要确保唯一性）"
                }),
                "callback_url": ("STRING", {
                    "default": "",
                    "multiline": False,
                    "placeholder": "可选：任务结果回调通知地址"
                }),
                "seed": ("INT", {
                    "default": -1,
                    "min": -1,
                    "max": 0xffffffffffffffff
                }),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING", "INT")
    RETURN_NAMES = ("task_id", "task_status", "created_at", "updated_at", "seed")
    FUNCTION = "create_multi_image2video_task"
    CATEGORY = "JM-KLingAI-API/multi-image-2-video"

    def tensor_to_pil(self, tensor):
        """将ComfyUI的Tensor图像转换为PIL图像"""
        if tensor is None:
            return None
            
        # 确保是一个单一的图像，不是批次
        if len(tensor.shape) == 4:
            tensor = tensor[0]
            
        # 转换为适合PIL的格式
        i = 255. * tensor.cpu().numpy()
        img = Image.fromarray(np.clip(i, 0, 255).astype(np.uint8))
        return img

    def image_to_base64(self, image):
        """将ComfyUI图像转换为base64字符串"""
        if image is None:
            return None
            
        try:
            # 处理tensor格式的图像
            if isinstance(image, torch.Tensor):
                pil_image = self.tensor_to_pil(image)
                if pil_image is None:
                    return None
            else:
                # 处理其他格式的图像
                if hasattr(image, "shape") and len(image.shape) == 3:
                    # 处理numpy数组格式
                    img = Image.fromarray((image * 255).astype(np.uint8))
                    pil_image = img
                elif hasattr(image, "shape") and len(image.shape) == 4:
                    # 处理批次图像，取第一张
                    img = Image.fromarray((image[0] * 255).astype(np.uint8))
                    pil_image = img
                else:
                    # 尝试最后一种可能
                    try:
                        img = Image.fromarray((image[0] * 255).astype('uint8'), 'RGB')
                        pil_image = img
                    except:
                        print(f"无法处理的图像格式: {type(image)}")
                        return None
                
            # 转换图像为RGB确保格式正确
            if pil_image.mode != 'RGB':
                pil_image = pil_image.convert('RGB')
                
            # 确保图像尺寸符合要求（不小于300x300px）
            width, height = pil_image.size
            if width < 300 or height < 300:
                # 等比例放大
                ratio = max(300 / width, 300 / height)
                new_width = int(width * ratio)
                new_height = int(height * ratio)
                pil_image = pil_image.resize((new_width, new_height), Image.LANCZOS)
                print(f"图像已调整尺寸: {width}x{height} -> {new_width}x{new_height}")
                
            # 检查宽高比是否在1:2.5~2.5:1范围内
            aspect = width / height
            if aspect < 0.4 or aspect > 2.5:  # 1/2.5 = 0.4
                # 裁剪图像使其符合要求
                if aspect < 0.4:  # 太窄
                    new_height = int(width / 0.4)
                    top = (height - new_height) // 2
                    pil_image = pil_image.crop((0, top, width, top + new_height))
                    print(f"图像已裁剪到宽高比0.4:1")
                else:  # 太宽
                    new_width = int(height * 2.5)
                    left = (width - new_width) // 2
                    pil_image = pil_image.crop((left, 0, left + new_width, height))
                    print(f"图像已裁剪到宽高比2.5:1")
                    
            # 转换为base64
            buffered = io.BytesIO()
            pil_image.save(buffered, format="JPEG", quality=95)
            img_bytes = buffered.getvalue()
            
            # 检查图像大小是否超过10MB
            img_size_mb = len(img_bytes) / (1024 * 1024)
            if img_size_mb > 9.5:  # 留一点余量
                # 缩小图像和/或降低质量
                max_size = (1500, 1500)  # 限制最大尺寸
                pil_image.thumbnail(max_size, Image.LANCZOS)
                
                # 重新保存，降低质量
                buffered = io.BytesIO()
                quality = 85
                while quality >= 60:  # 最低降到60%质量
                    buffered.seek(0)
                    buffered.truncate(0)
                    pil_image.save(buffered, format="JPEG", quality=quality)
                    img_size_mb = len(buffered.getvalue()) / (1024 * 1024)
                    if img_size_mb <= 9.5:
                        break
                    quality -= 5
                
                print(f"图像已压缩: {quality}%质量, 大小: {img_size_mb:.2f}MB")
                img_bytes = buffered.getvalue()
            
            # 返回base64编码
            base64_str = base64.b64encode(img_bytes).decode("utf-8")
            print(f"成功转换图像为base64, 大小: {len(base64_str) / 1024:.2f}KB")
            
            return base64_str
            
        except Exception as e:
            print(f"图像转换base64错误: {str(e)}")
            return None

    def create_multi_image2video_task(self, api_token, prompt, image1, 
                                    image2=None, image3=None, image4=None,
                                    model_name="kling-v1-6", negative_prompt="", 
                                    mode="std", duration="5", aspect_ratio="16:9",
                                    external_task_id="", callback_url="", seed=-1):
        """
        创建多图生视频任务
        """
        try:
            # 验证必要参数
            if not api_token:
                raise ValueError("API令牌不能为空")
            if not prompt:
                raise ValueError("正向提示词不能为空")
            if len(prompt) > 2500:
                raise ValueError("正向提示词不能超过2500字符")
            if negative_prompt and len(negative_prompt) > 2500:
                raise ValueError("负向提示词不能超过2500字符")
            if image1 is None:
                raise ValueError("至少需要提供一张图片")
            
            # 生成随机种子（本地使用，不发送给API）
            if seed == -1:
                seed = random.randint(0, 0xffffffffffffffff)

            # 准备图片列表
            image_list = []
            
            # 转换图片1为base64
            image1_base64 = self.image_to_base64(image1)
            if not image1_base64:
                raise ValueError("图片1转换为base64失败")
            image_list.append(image1_base64)
            
            # 转换图片2为base64（如果提供）
            if image2 is not None:
                image2_base64 = self.image_to_base64(image2)
                if image2_base64:
                    image_list.append(image2_base64)
            
            # 转换图片3为base64（如果提供）
            if image3 is not None:
                image3_base64 = self.image_to_base64(image3)
                if image3_base64:
                    image_list.append(image3_base64)
            
            # 转换图片4为base64（如果提供）
            if image4 is not None:
                image4_base64 = self.image_to_base64(image4)
                if image4_base64:
                    image_list.append(image4_base64)
            
            # 验证图片数量
            if len(image_list) > 4:
                raise ValueError("最多只能提供4张图片")
            
            # 准备请求头
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_token.strip()}"
            }

            # 准备请求体
            payload = {
                "model_name": model_name,
                "image_list": image_list,
                "prompt": prompt,
                "mode": mode,
                "duration": duration,
                "aspect_ratio": aspect_ratio
            }
            
            # 添加可选参数
            if negative_prompt:
                payload["negative_prompt"] = negative_prompt
            if external_task_id:
                payload["external_task_id"] = external_task_id
            if callback_url:
                payload["callback_url"] = callback_url

            # 发送API请求
            url = f"{self.api_base}{self.endpoint}"
            print(f"正在发送请求到: {url}")
            print(f"使用本地种子: {seed} (仅用于本地，未发送给API)")
            print(f"提供的图片数量: {len(image_list)}")
            
            response = requests.post(url, headers=headers, json=payload)
            response_data = response.json()
            
            print(f"响应状态码: {response.status_code}")
            print(f"响应数据: {json.dumps(response_data, indent=2)}")

            # 检查错误并提供详细错误信息
            if response.status_code != 200:
                error_code = response_data.get('code')
                error_message = response_data.get('message')
                request_id = response_data.get('request_id')
                raise Exception(f"API请求失败 (错误码: {error_code}): {error_message} (请求ID: {request_id})")

            # 提取响应数据
            data = response_data.get("data", {})
            task_id = data.get("task_id", "")
            task_status = data.get("task_status", "")
            created_at = str(data.get("created_at", ""))
            updated_at = str(data.get("updated_at", ""))

            if not task_id:
                raise Exception("API未返回任务ID")

            print(f"成功创建多图生视频任务，任务ID: {task_id} (本地种子: {seed})")
            return (task_id, task_status, created_at, updated_at, seed)

        except ValueError as ve:
            print(f"参数验证错误: {str(ve)}")
            return (f"错误: {str(ve)}", "failed", "", "", seed)
        except Exception as e:
            print(f"创建多图生视频任务错误: {str(e)}")
            return (f"错误: {str(e)}", "failed", "", "", seed)

    @classmethod
    def IS_CHANGED(cls, image, prompt, negative_prompt, callback_selection, output_format, fps, model_selection, seed):
        # Always refresh this node
        return time.time() 