import json
import random
import requests
import base64
import os
from PIL import Image
import io
import numpy as np
import torch


class KLingAIImage2Video:
    """
    KLingAI Image to Video Node
    创建图生视频任务节点
    """
    
    def __init__(self):
        self.api_base = "https://api.klingai.com"
        self.endpoint = "/v1/videos/image2video"
        
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "api_token": ("STRING", {"default": "", "multiline": False}),
                "image": ("IMAGE",),
            },
            "optional": {
                "model_name": (["kling-v1", "kling-v1-5", "kling-v1-6"], {"default": "kling-v1"}),
                "positive_prompt": ("STRING", {
                    "default": "", 
                    "multiline": True,
                    "placeholder": "正向提示词 (最多2500字符)"
                }),
                "negative_prompt": ("STRING", {
                    "default": "",
                    "multiline": True,
                    "placeholder": "负向提示词 (最多2500字符)"
                }),
                "cfg_scale": ("FLOAT", {
                    "default": 0.5,
                    "min": 0.0,
                    "max": 1.0,
                    "step": 0.1
                }),
                "mode": (["std", "pro"], {"default": "std"}),
                "duration": (["5", "10"], {"default": "5"}),
                "image_tail": ("IMAGE",),
                "use_camera_control": ("BOOLEAN", {"default": False}),
                "camera_type": (["simple", "down_back", "forward_up", "right_turn_forward", "left_turn_forward"], {"default": "simple"}),
                "camera_horizontal": ("FLOAT", {
                    "default": 0.0,
                    "min": -10.0,
                    "max": 10.0,
                    "step": 0.5
                }),
                "camera_vertical": ("FLOAT", {
                    "default": 0.0,
                    "min": -10.0,
                    "max": 10.0,
                    "step": 0.5
                }),
                "camera_pan": ("FLOAT", {
                    "default": 0.0,
                    "min": -10.0,
                    "max": 10.0,
                    "step": 0.5
                }),
                "camera_tilt": ("FLOAT", {
                    "default": 0.0,
                    "min": -10.0,
                    "max": 10.0,
                    "step": 0.5
                }),
                "camera_roll": ("FLOAT", {
                    "default": 0.0,
                    "min": -10.0,
                    "max": 10.0,
                    "step": 0.5
                }),
                "camera_zoom": ("FLOAT", {
                    "default": 0.0,
                    "min": -10.0,
                    "max": 10.0,
                    "step": 0.5
                }),
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
    FUNCTION = "create_image2video_task"
    CATEGORY = "JM-KLingAI-API/image-2-video"

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

    def get_camera_control(self, camera_type, h, v, pan, tilt, roll, zoom):
        """构建摄像机控制参数"""
        camera_control = {"type": camera_type}
        
        # 如果是simple类型，添加config配置
        if camera_type == "simple":
            # 确保只有一个方向参数不为0
            non_zero_params = sum(1 for p in [h, v, pan, tilt, roll, zoom] if abs(p) > 0.001)
            
            if non_zero_params > 1:
                print("警告：simple类型摄像机控制只能设置一个方向参数，将使用第一个非零参数")
            
            camera_control["config"] = {
                "horizontal": h,
                "vertical": v,
                "pan": pan,
                "tilt": tilt,
                "roll": roll,
                "zoom": zoom
            }
        
        return camera_control

    def validate_camera_params(self, camera_type, h, v, pan, tilt, roll, zoom):
        """验证摄像机参数合法性"""
        if camera_type == "simple":
            non_zero_count = sum(1 for p in [h, v, pan, tilt, roll, zoom] if abs(p) > 0.001)
            if non_zero_count > 1:
                return False, "simple类型摄像机控制只能设置一个方向参数不为0"
            if non_zero_count == 0:
                return False, "simple类型摄像机控制至少需要一个方向参数不为0"
        return True, ""

    def create_image2video_task(self, api_token, image, model_name="kling-v1", 
                              positive_prompt="", negative_prompt="", 
                              cfg_scale=0.5, mode="std", duration="5", 
                              image_tail=None, use_camera_control=False,
                              camera_type="simple", camera_horizontal=0.0,
                              camera_vertical=0.0, camera_pan=0.0, 
                              camera_tilt=0.0, camera_roll=0.0, 
                              camera_zoom=0.0, external_task_id="", 
                              callback_url="", seed=-1):
        """
        创建图生视频任务
        """
        try:
            # 验证必要参数
            if not api_token:
                raise ValueError("API令牌不能为空")
            if image is None:
                raise ValueError("输入图像不能为空")
            
            # 生成随机种子（本地使用，不发送给API）
            if seed == -1:
                seed = random.randint(0, 0xffffffffffffffff)

            # 验证文本提示词长度
            if positive_prompt and len(positive_prompt) > 2500:
                raise ValueError("正向提示词不能超过2500字符")
            if negative_prompt and len(negative_prompt) > 2500:
                raise ValueError("负向提示词不能超过2500字符")
                
            # 验证摄像机参数
            if use_camera_control:
                valid, msg = self.validate_camera_params(
                    camera_type, camera_horizontal, camera_vertical,
                    camera_pan, camera_tilt, camera_roll, camera_zoom
                )
                if not valid:
                    raise ValueError(f"摄像机参数错误: {msg}")

            # 转换图像为base64
            image_base64 = self.image_to_base64(image)
            if not image_base64:
                raise ValueError("图像转换为base64失败")
                
            image_tail_base64 = self.image_to_base64(image_tail) if image_tail is not None else None
            
            # 准备请求头
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_token.strip()}"
            }

            # 准备请求体
            payload = {
                "model_name": model_name,
                "image": image_base64,
                "cfg_scale": float(cfg_scale),
                "mode": mode,
                "duration": duration
            }
            
            # 添加可选参数
            if positive_prompt:
                payload["prompt"] = positive_prompt
            if negative_prompt:
                payload["negative_prompt"] = negative_prompt
            if image_tail_base64:
                payload["image_tail"] = image_tail_base64
            if external_task_id:
                payload["external_task_id"] = external_task_id
            if callback_url:
                payload["callback_url"] = callback_url
                
            # 添加摄像机控制参数
            if use_camera_control:
                payload["camera_control"] = self.get_camera_control(
                    camera_type, camera_horizontal, camera_vertical,
                    camera_pan, camera_tilt, camera_roll, camera_zoom
                )

            # 发送API请求
            url = f"{self.api_base}{self.endpoint}"
            print(f"正在发送请求到: {url}")
            print(f"使用本地种子: {seed} (仅用于本地，未发送给API)")
            
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

            print(f"成功创建图生视频任务，任务ID: {task_id} (本地种子: {seed})")
            return (task_id, task_status, created_at, updated_at, seed)

        except ValueError as ve:
            print(f"参数验证错误: {str(ve)}")
            return (None, None, None, None, seed)
        except Exception as e:
            print(f"创建图生视频任务错误: {str(e)}")
            return (None, None, None, None, seed)

    def IS_CHANGED(self, api_token, image, model_name="kling-v1", 
                 positive_prompt="", negative_prompt="", 
                 cfg_scale=0.5, mode="std", duration="5", 
                 image_tail=None, use_camera_control=False,
                 camera_type="simple", camera_horizontal=0.0,
                 camera_vertical=0.0, camera_pan=0.0, 
                 camera_tilt=0.0, camera_roll=0.0, 
                 camera_zoom=0.0, external_task_id="", 
                 callback_url="", seed=-1):
        """
        此方法用于判断节点是否需要重新执行
        我们使用种子控制重新执行逻辑
        """
        if seed == -1:
            return random.randint(0, 0xffffffffffffffff)
        return seed 