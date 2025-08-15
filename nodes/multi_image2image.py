import os
import json
import time
import random
import requests
import folder_paths
from io import BytesIO
import base64
import numpy as np
from PIL import Image
import torch



class KLingAIMultiImage2Image:
    """
    可灵AI多图参考生图节点
    
    该节点使用可灵AI的多图参考生图API，支持2-4张图片作为主体参考，
    可选择性地添加场景参考图和风格参考图。
    """
    
    def __init__(self):
        self.api_base = "https://api.klingai.com"
        self.endpoint = "/v1/images/multi-image2image"
        self.query_endpoint = "/v1/images/multi-image2image/{}"
        
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "api_token": ("STRING", {
                    "multiline": False,
                    "default": "",
                    "placeholder": "输入你的可灵AI API Token"
                }),
                "prompt": ("STRING", {
                    "multiline": True,
                    "default": "",
                    "placeholder": "输入图片生成描述（最多2500字符）"
                }),
                "subject_image1": ("IMAGE",),
                "subject_image2": ("IMAGE",),
            },
            "optional": {
                "subject_image3": ("IMAGE",),
                "subject_image4": ("IMAGE",),
                "scene_image": ("IMAGE",),
                "style_image": ("IMAGE",),
                "filename_prefix": ("STRING", {
                    "default": "kling_multi_image2image",
                    "placeholder": "输出文件名前缀"
                }),
                "output_dir": ("STRING", {
                    "default": "",
                    "placeholder": "自定义输出目录（留空使用默认output目录）"
                }),
                "model_name": (["kling-v2"], {"default": "kling-v2"}),
                "n": ("INT", {
                    "default": 1,
                    "min": 1,
                    "max": 9,
                    "step": 1,
                    "display": "number"
                }),
                "aspect_ratio": (["16:9", "9:16", "1:1", "4:3", "3:4", "3:2", "2:3", "21:9"], {
                    "default": "16:9"
                }),
                "seed": ("INT", {
                    "default": -1,
                    "min": -1,
                    "max": 0xffffffffffffffff,
                    "step": 1,
                    "display": "number"
                }),
                "external_task_id": ("STRING", {
                    "default": "",
                    "placeholder": "自定义任务ID（可选）"
                }),
                "callback_url": ("STRING", {
                    "default": "",
                    "placeholder": "回调URL（可选）"
                }),
            }
        }
    
    RETURN_TYPES = ("IMAGE", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("image", "image_url", "task_id", "output_dir")
    FUNCTION = "create_multi_image2image_task"
    CATEGORY = "JM-KLingAI-API"
    OUTPUT_NODE = True
    OUTPUT_IS_LIST = (True, True, False, False)

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return time.time()
    
    def tensor_to_pil(self, tensor):
        """将ComfyUI的张量转换为PIL图像"""
        # 确保张量是正确的形状 [H, W, C]
        if len(tensor.shape) == 4:
            tensor = tensor.squeeze(0)  # 移除批次维度
        
        # 转换为numpy数组并缩放到0-255
        numpy_image = tensor.cpu().numpy()
        if numpy_image.max() <= 1.0:
            numpy_image = (numpy_image * 255).astype(np.uint8)
        else:
            numpy_image = numpy_image.astype(np.uint8)
        
        # 转换为PIL图像
        return Image.fromarray(numpy_image)
    
    def image_to_base64(self, image_tensor):
        """将图像张量转换为base64字符串"""
        try:
            # 转换为PIL图像
            pil_image = self.tensor_to_pil(image_tensor)
            
            # 转换为RGB格式（确保兼容性）
            if pil_image.mode != 'RGB':
                pil_image = pil_image.convert('RGB')
            
            # 转换为base64
            buffer = BytesIO()
            pil_image.save(buffer, format='PNG')
            image_bytes = buffer.getvalue()
            base64_string = base64.b64encode(image_bytes).decode('utf-8')
            
            # 计算图片大小（MB）
            size_mb = len(image_bytes) / (1024 * 1024)
            print(f"成功转换图像为base64, 大小: {size_mb:.2f}MB")
            
            return base64_string
        except Exception as e:
            print(f"图像转换为base64失败: {str(e)}")
            return None

    def download_and_convert_image(self, image_url, filename_prefix, output_dir, index=0):
        """下载图片并转换为ComfyUI张量格式"""
        try:
            # 确定输出目录
            if output_dir and os.path.isdir(output_dir):
                save_dir = output_dir
            else:
                save_dir = folder_paths.get_output_directory()
            
            # 生成文件名
            filename = f"{filename_prefix}_{index+1:04d}.png"
            filepath = os.path.join(save_dir, filename)
            
            # 下载图片
            response = requests.get(image_url, timeout=30)
            response.raise_for_status()
            
            # 保存图片
            with open(filepath, 'wb') as f:
                f.write(response.content)
            
            # 转换为ComfyUI张量
            pil_image = Image.open(filepath)
            if pil_image.mode != 'RGB':
                pil_image = pil_image.convert('RGB')
            
            # 转换为numpy数组
            image_array = np.array(pil_image).astype(np.float32) / 255.0
            
            # 转换为torch张量并添加批次维度
            image_tensor = torch.from_numpy(image_array)[None,]
            
            print(f"成功下载并转换图片: {filepath}")
            return image_tensor, filepath
            
        except Exception as e:
            print(f"下载图片失败: {str(e)}")
            return None, None

    def create_multi_image2image_task(self, api_token, prompt="", subject_image1=None, subject_image2=None, 
                                     subject_image3=None, subject_image4=None, scene_image=None, style_image=None,
                                     filename_prefix="kling_multi_image2image", output_dir="", model_name="kling-v2",
                                     n=1, aspect_ratio="16:9", seed=-1, external_task_id="", callback_url=""):
        try:
            # 验证API token
            if not api_token or not api_token.strip():
                raise ValueError("API Token不能为空，请在节点中输入")
            
            # 生成随机种子（本地使用，不发送给API）
            if seed == -1:
                seed = random.randint(0, 0xffffffffffffffff)
            
            # 准备主体图片列表，按照官方API格式，至少需要2张图片
            subject_image_list = []
            
            # 转换主体图片1为base64
            if subject_image1 is not None:
                image1_base64 = self.image_to_base64(subject_image1)
                if not image1_base64:
                    raise ValueError("主体图片1转换为base64失败")
                subject_image_list.append({"subject_image": image1_base64})
            
            # 转换主体图片2为base64
            if subject_image2 is not None:
                image2_base64 = self.image_to_base64(subject_image2)
                if not image2_base64:
                    raise ValueError("主体图片2转换为base64失败")
                subject_image_list.append({"subject_image": image2_base64})
            
            # 转换主体图片3为base64（如果提供）
            if subject_image3 is not None:
                image3_base64 = self.image_to_base64(subject_image3)
                if image3_base64:
                    subject_image_list.append({"subject_image": image3_base64})
            
            # 转换主体图片4为base64（如果提供）
            if subject_image4 is not None:
                image4_base64 = self.image_to_base64(subject_image4)
                if image4_base64:
                    subject_image_list.append({"subject_image": image4_base64})
            
            # 验证图片数量
            if len(subject_image_list) < 2:
                raise ValueError("至少需要提供2张主体图片")
            if len(subject_image_list) > 4:
                raise ValueError("最多只能提供4张主体图片")
            
            print(f"提供的主体图片数量: {len(subject_image_list)}")
            
            # 准备请求头
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_token.strip()}"
            }

            # 准备请求体，按照官方API文档格式
            payload = {
                "model_name": model_name,
                "subject_image_list": subject_image_list,
                "n": n,
                "aspect_ratio": aspect_ratio
            }
            
            # 添加可选参数
            if prompt:
                payload["prompt"] = prompt
            
            # 处理场景参考图
            if scene_image is not None:
                scene_base64 = self.image_to_base64(scene_image)
                if scene_base64:
                    payload["scence_image"] = scene_base64  # 注意API文档中是"scence_image"而不是"scene_image"
                    print("添加了场景参考图")
            
            # 处理风格参考图
            if style_image is not None:
                style_base64 = self.image_to_base64(style_image)
                if style_base64:
                    payload["style_image"] = style_base64
                    print("添加了风格参考图")
            
            if external_task_id:
                payload["external_task_id"] = external_task_id
            if callback_url:
                payload["callback_url"] = callback_url
            
            # 发送请求
            url = f"{self.api_base}{self.endpoint}"
            print(f"正在发送请求到: {url}")
            print(f"使用本地种子: {seed} (仅用于本地，未发送给API)")
            
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            
            print(f"响应状态码: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"响应数据: {json.dumps(result, indent=2, ensure_ascii=False)}")
                
                if result.get("code") == 0 and "data" in result:
                    task_id = result["data"]["task_id"]
                    print(f"成功创建多图参考生图任务，任务ID: {task_id} (本地种子: {seed})")
                    
                    # 等待并查询任务结果
                    return self.wait_and_get_result(api_token, task_id, filename_prefix, output_dir)
                else:
                    error_msg = f"创建多图参考生图任务失败: {result.get('message', '未知错误')}"
                    print(error_msg)
                    return ([], [], error_msg, output_dir or folder_paths.get_output_directory())
            else:
                try:
                    error_data = response.json()
                    error_msg = f"API请求失败 (错误码: {error_data.get('code', 'unknown')}): {error_data.get('message', '未知错误')} (请求ID: {error_data.get('request_id', 'unknown')})"
                except:
                    error_msg = f"API请求失败，状态码: {response.status_code}"
                
                print(f"创建多图参考生图任务错误: {error_msg}")
                return ([], [], error_msg, output_dir or folder_paths.get_output_directory())
                
        except Exception as e:
            error_msg = f"创建多图参考生图任务异常: {str(e)}"
            print(error_msg)
            return ([], [], error_msg, output_dir or folder_paths.get_output_directory())

    def wait_and_get_result(self, api_token, task_id, filename_prefix, output_dir, max_wait_time=600, poll_interval=10):
        """等待任务完成并获取结果"""
        start_time = time.time()
        
        print(f"[DEBUG] ======== 开始查询任务状态 ========")
        print(f"任务ID: {task_id}")
        print(f"最大等待时间: {max_wait_time}秒")
        print(f"查询间隔: {poll_interval}秒")
        
        while time.time() - start_time < max_wait_time:
            try:
                # 查询任务状态
                query_url = f"{self.api_base}{self.query_endpoint.format(task_id)}"
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_token.strip()}"
                }
                
                print(f"查询任务状态: {query_url}")
                response = requests.get(query_url, headers=headers, timeout=30)
                
                if response.status_code == 200:
                    result = response.json()
                    
                    if result.get("code") == 0 and "data" in result:
                        data = result["data"]
                        task_status = data.get("task_status")
                        
                        print(f"当前任务状态: {task_status}")
                        
                        if task_status == "succeed":
                            # 任务成功，下载图片
                            task_result = data.get("task_result", {})
                            images = task_result.get("images", [])
                            
                            if images:
                                print(f"任务成功完成，共生成 {len(images)} 张图片")
                                
                                # 下载所有图片
                                downloaded_images = []
                                image_urls = []
                                
                                for image_info in images:
                                    image_url = image_info.get("url")
                                    index = image_info.get("index", 0)
                                    
                                    if image_url:
                                        image_tensor, filepath = self.download_and_convert_image(
                                            image_url, filename_prefix, output_dir, index
                                        )
                                        
                                        if image_tensor is not None:
                                            downloaded_images.append(image_tensor)
                                            image_urls.append(image_url)
                                
                                if downloaded_images:
                                    print(f"[DEBUG] ======== 任务完成 ========")
                                    return (downloaded_images, image_urls, task_id, output_dir or folder_paths.get_output_directory())
                                else:
                                    error_msg = "图片下载失败"
                                    print(error_msg)
                                    return ([], [], error_msg, output_dir or folder_paths.get_output_directory())
                            else:
                                error_msg = "任务完成但未返回图片"
                                print(error_msg)
                                return ([], [], error_msg, output_dir or folder_paths.get_output_directory())
                        
                        elif task_status == "failed":
                            error_msg = f"任务失败: {data.get('task_status_msg', '未知原因')}"
                            print(error_msg)
                            return ([], [], error_msg, output_dir or folder_paths.get_output_directory())
                        
                        elif task_status in ["submitted", "processing"]:
                            # 任务还在处理中，继续等待
                            print(f"任务处理中，等待 {poll_interval} 秒后再次查询...")
                        
                        else:
                            print(f"未知任务状态: {task_status}")
                    
                    else:
                        print(f"查询任务状态失败: {result.get('message', '未知错误')}")
                
                else:
                    print(f"查询任务状态请求失败，状态码: {response.status_code}")
                
                # 等待一段时间后再次查询
                time.sleep(poll_interval)
                
            except Exception as e:
                print(f"查询任务状态异常: {str(e)}")
                time.sleep(poll_interval)
        
        # 超时
        error_msg = f"任务查询超时 ({max_wait_time}秒)"
        print(error_msg)
        return ([], [], error_msg, output_dir or folder_paths.get_output_directory())
