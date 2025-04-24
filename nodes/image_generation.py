import json
import random
import requests
import base64
import io
from PIL import Image
import numpy as np
import torch
import time
import folder_paths


class KLingAIImageGeneration:
    """
    KLingAI Image Generation Node
    创建文生图任务节点
    """
    
    def __init__(self):
        self.api_base = "https://api.klingai.com"
        self.endpoint = "/v1/images/generations"
        
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "api_token": ("STRING", {"default": "", "multiline": False}),
                "prompt": ("STRING", {
                    "default": "", 
                    "multiline": True,
                    "placeholder": "正向文本提示词 (最多500字符)"
                }),
            },
            "optional": {
                "image_type": (["Base64", "URL"], {"default": "Base64"}),
                "image": ("IMAGE",),
                "image_url": ("STRING", {
                    "default": "",
                    "multiline": False,
                    "placeholder": "参考图片URL地址"
                }),
                "image_reference": (["subject", "face"], {"default": "subject"}),
                "model_name": (["kling-v1", "kling-v1-5"], {"default": "kling-v1"}),
                "negative_prompt": ("STRING", {
                    "default": "",
                    "multiline": True,
                    "placeholder": "负向文本提示词 (最多200字符)"
                }),
                "image_fidelity": ("FLOAT", {
                    "default": 0.5,
                    "min": 0.0,
                    "max": 1.0,
                    "step": 0.05
                }),
                "human_fidelity": ("FLOAT", {
                    "default": 0.45,
                    "min": 0.0,
                    "max": 1.0,
                    "step": 0.05
                }),
                "n": ("INT", {
                    "default": 1,
                    "min": 1,
                    "max": 9,
                    "step": 1
                }),
                "aspect_ratio": (["16:9", "9:16", "1:1", "4:3", "3:4", "3:2", "2:3", "21:9"], {"default": "16:9"}),
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
    FUNCTION = "create_image_generation_task"
    CATEGORY = "JM-KLingAI-API/image-generation"

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
                # 原来的处理方法 (已不再使用，保留以防万一)
                img = Image.fromarray((image[0] * 255).astype('uint8'), 'RGB')
                pil_image = img
                
            # 转换为base64
            buffered = io.BytesIO()
            pil_image.save(buffered, format="JPEG")
            return base64.b64encode(buffered.getvalue()).decode("utf-8")
            
        except Exception as e:
            print(f"图像转换base64错误: {str(e)}")
            return None

    def create_image_generation_task(self, api_token, prompt, image_type="Base64", 
                               image=None, image_url="", image_reference="subject",
                               model_name="kling-v1", negative_prompt="", 
                               image_fidelity=0.5, human_fidelity=0.45, n=1,
                               aspect_ratio="16:9", callback_url="", seed=-1):
        """
        创建文生图任务
        """
        try:
            # 验证必要参数
            if not api_token:
                raise ValueError("API令牌不能为空")
            
            if not prompt:
                raise ValueError("正向提示词不能为空")
            
            if len(prompt) > 500:
                raise ValueError("正向提示词不能超过500字符")
            
            # 生成随机种子（本地使用，不发送给API）
            if seed == -1:
                seed = random.randint(0, 0xffffffffffffffff)

            # 验证其他参数
            if negative_prompt and len(negative_prompt) > 200:
                raise ValueError("负向提示词不能超过200字符")
                
            # 准备请求头
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_token.strip()}"
            }

            # 准备请求体
            payload = {
                "model_name": model_name,
                "prompt": prompt,
                "aspect_ratio": aspect_ratio,
                "n": n
            }
            
            # 检查是否提供了参考图像，如果有，进行处理
            has_reference_image = False
            
            if image_type == "Base64" and image is not None:
                # 转换图像为base64
                image_base64 = self.image_to_base64(image)
                if image_base64:
                    payload["image"] = image_base64
                    has_reference_image = True
                    print("使用Base64方式处理参考图像")
                    
                    # 如果是v1-5模型且有参考图片，需要添加image_reference
                    if model_name == "kling-v1-5":
                        payload["image_reference"] = image_reference
                        payload["image_fidelity"] = float(image_fidelity)
                        payload["human_fidelity"] = float(human_fidelity)
                
            elif image_type == "URL" and image_url:
                # 直接使用URL
                payload["image"] = image_url.strip()
                has_reference_image = True
                print(f"使用URL方式处理参考图像: {image_url}")
                
                # 如果是v1-5模型且有参考图片，需要添加image_reference
                if model_name == "kling-v1-5":
                    payload["image_reference"] = image_reference
                    payload["image_fidelity"] = float(image_fidelity)
                    payload["human_fidelity"] = float(human_fidelity)
            
            # 添加负向提示词（图生图模式下不支持）
            if negative_prompt and not has_reference_image:
                payload["negative_prompt"] = negative_prompt
            elif negative_prompt and has_reference_image:
                print("警告：图生图模式下不支持负向提示词，将忽略负向提示词")
                
            # 添加回调URL（如果提供）
            if callback_url:
                payload["callback_url"] = callback_url.strip()

            # 发送API请求
            url = f"{self.api_base}{self.endpoint}"
            print(f"正在发送请求到: {url}")
            print(f"使用本地种子: {seed} (仅用于本地，未发送给API)")
            if has_reference_image:
                print(f"参考图像模式: {image_reference}")
            
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

            print(f"成功创建文生图任务，任务ID: {task_id} (本地种子: {seed})")
            return (task_id, task_status, created_at, updated_at, seed)

        except ValueError as ve:
            print(f"参数验证错误: {str(ve)}")
            return (f"错误: {str(ve)}", "failed", "", "", seed)
        except Exception as e:
            print(f"创建文生图任务错误: {str(e)}")
            return (f"错误: {str(e)}", "failed", "", "", seed)

    @classmethod
    def IS_CHANGED(cls, api_token, prompt, image_type="Base64", 
                 image=None, image_url="", image_reference="subject",
                 model_name="kling-v1", negative_prompt="", 
                 image_fidelity=0.5, human_fidelity=0.45, n=1,
                 aspect_ratio="16:9", callback_url="", seed=-1):
        """
        此方法用于判断节点是否需要重新执行
        我们使用种子控制重新执行逻辑
        """
        if seed == -1:
            return random.randint(0, 0xffffffffffffffff)
        return seed 