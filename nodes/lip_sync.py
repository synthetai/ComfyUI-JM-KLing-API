import json
import time
import random
import requests
import base64
import io
import os
from PIL import Image


class KLingAILipSync:
    """
    KLingAI Lip Sync Node
    创建视频口型匹配任务节点
    """
    
    def __init__(self):
        self.api_base = "https://api.klingai.com"
        self.endpoint = "/v1/videos/lip-sync"
        
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "api_token": ("STRING", {"default": "", "multiline": False}),
            },
            "optional": {
                "video_id": ("STRING", {
                    "default": "", 
                    "multiline": False,
                    "placeholder": "通过可灵AI生成的视频ID"
                }),
                "video_url": ("STRING", {
                    "default": "", 
                    "multiline": False,
                    "placeholder": "视频URL地址(mp4/mov格式，不超过100MB，2-10秒)"
                }),
                "mode": (["text2video", "audio2video"], {"default": "text2video"}),
                "text": ("STRING", {
                    "default": "",
                    "multiline": True,
                    "placeholder": "生成对口型视频的文本内容 (最多120字符)"
                }),
                "voice_id": ("STRING", {
                    "default": "girlfriend_1_speech02",
                    "multiline": False,
                    "placeholder": "音色ID, 如girlfriend_1_speech02"
                }),
                "voice_language": (["zh", "en"], {"default": "zh"}),
                "voice_speed": ("FLOAT", {
                    "default": 1.0,
                    "min": 0.8,
                    "max": 2.0,
                    "step": 0.1
                }),
                "audio_type": (["file", "url"], {"default": "url"}),
                "audio_url": ("STRING", {
                    "default": "",
                    "multiline": False,
                    "placeholder": "音频文件下载URL(mp3/wav/m4a/acc格式)"
                }),
                "audio_file": ("STRING", {
                    "default": "",
                    "multiline": False,
                    "placeholder": "本地音频文件路径(mp3/wav/m4a/acc格式)"
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

    RETURN_TYPES = ("STRING", "STRING", "STRING", "INT")
    RETURN_NAMES = ("task_id", "task_status", "update_time", "seed")
    FUNCTION = "create_lip_sync_task"
    CATEGORY = "JM-KLingAI-API/lip-sync"

    def create_lip_sync_task(self, api_token, mode="text2video", text="", 
                           voice_id="girlfriend_1_speech02", voice_language="zh", 
                           voice_speed=1.0, audio_type="url", audio_url="", 
                           audio_file="", callback_url="", seed=-1, 
                           video_id="", video_url=""):
        """
        创建口型同步任务
        """
        try:
            # 验证必要参数
            if not api_token:
                raise ValueError("API令牌不能为空")
            
            # 检查视频参数
            if not video_id and not video_url:
                raise ValueError("视频ID和视频URL至少需要提供一个")
            if video_id and video_url:
                raise ValueError("视频ID和视频URL不能同时提供，请只选择一种方式")
            
            # 生成随机种子（本地使用，不发送给API）
            if seed == -1:
                seed = random.randint(0, 0xffffffffffffffff)

            # 处理模式参数
            if mode == "text2video":
                if not text:
                    raise ValueError("使用text2video模式时，文本内容不能为空")
                if len(text) > 120:
                    raise ValueError("文本内容不能超过120字符")
            elif mode == "audio2video":
                if audio_type == "url" and not audio_url:
                    raise ValueError("使用audio2video模式且audio_type为url时，音频URL不能为空")
                elif audio_type == "file" and not audio_file:
                    raise ValueError("使用audio2video模式且audio_type为file时，音频文件路径不能为空")

            # 调试输出
            print(f"处理模式: {mode}")
            if mode == "text2video":
                print(f"使用的文本: {text}")
            elif mode == "audio2video" and audio_type == "file":
                print(f"使用的音频文件: {audio_file}")
            elif mode == "audio2video" and audio_type == "url":
                print(f"使用的音频URL: {audio_url}")
            
            # 准备请求头
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_token.strip()}"
            }

            # 准备请求体 - 根据API文档修正结构
            payload = {
                "input": {
                    "mode": mode
                }
            }
            
            # 添加视频参数
            if video_id:
                payload["input"]["task_id"] = video_id.strip()
                payload["input"]["video_id"] = video_id.strip()
            elif video_url:
                payload["input"]["video_url"] = video_url.strip()
                
            # 根据不同模式添加参数
            if mode == "text2video":
                payload["input"]["text"] = text
                payload["input"]["voice_id"] = voice_id
                payload["input"]["voice_language"] = voice_language
                if voice_speed != 1.0:
                    payload["input"]["voice_speed"] = voice_speed
            elif mode == "audio2video":
                payload["input"]["audio_type"] = audio_type
                if audio_type == "url":
                    payload["input"]["audio_url"] = audio_url.strip()
                elif audio_type == "file":
                    # 尝试两种方法处理音频文件
                    try:
                        if not os.path.exists(audio_file):
                            raise ValueError(f"音频文件不存在: {audio_file}")
                        
                        # 检查文件扩展名
                        file_ext = os.path.splitext(audio_file)[1].lower()
                        if file_ext not in ['.mp3', '.wav', '.m4a', '.acc']:
                            raise ValueError(f"不支持的音频格式: {file_ext}，仅支持mp3/wav/m4a/acc格式")
                        
                        # 检查文件大小
                        file_size_mb = os.path.getsize(audio_file) / (1024 * 1024)
                        if file_size_mb > 5:
                            raise ValueError(f"音频文件过大: {file_size_mb:.2f}MB，最大支持5MB")
                        
                        # 首先尝试标准的方法：读取文件并转为base64
                        try:
                            with open(audio_file, 'rb') as f:
                                audio_bytes = f.read()
                                # 确保音频文件不为空
                                if not audio_bytes:
                                    raise ValueError("音频文件内容为空")
                                
                                # 使用标准的base64编码，确保编码后的字符串不包含额外字符
                                audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
                                
                                # 确保base64编码的长度是4的倍数
                                padding = len(audio_base64) % 4
                                if padding > 0:
                                    audio_base64 += '=' * (4 - padding)
                                
                                # 验证base64编码的有效性
                                try:
                                    test_decode = base64.b64decode(audio_base64)
                                    if len(test_decode) != len(audio_bytes):
                                        raise ValueError(f"Base64解码后大小不匹配: 原始={len(audio_bytes)}, 解码后={len(test_decode)}")
                                except Exception as decode_err:
                                    raise ValueError(f"Base64验证失败: {str(decode_err)}")
                                
                                # 打印编码后的Base64字符串的前10个字符和后10个字符，用于调试
                                print(f"音频Base64 - 前缀: {audio_base64[:10]}... 后缀: ...{audio_base64[-10:]}")
                                print(f"音频Base64长度: {len(audio_base64)}, 是否为4的倍数: {len(audio_base64) % 4 == 0}")
                            
                            print(f"成功读取并编码音频文件: {audio_file}, 大小: {file_size_mb:.2f}MB")
                            payload["input"]["audio_file"] = audio_base64
                        except Exception as e:
                            # 如果base64方法失败，尝试使用其他方式：先上传到外部服务或临时URL
                            print(f"Base64编码方法失败: {str(e)}，尝试替代方案...")
                            print("建议: 由于Base64编码不稳定，请考虑将音频上传到服务器并使用URL模式")
                            raise ValueError(f"Base64编码失败: {str(e)} - 建议将音频文件上传到服务器，然后使用audio_type=url模式")
                    except Exception as e:
                        raise ValueError(f"处理音频文件时出错: {str(e)}")
            
            # 添加回调URL（如果提供）
            if callback_url:
                payload["input"]["callback_url"] = callback_url.strip()

            # 发送API请求
            url = f"{self.api_base}{self.endpoint}"
            print(f"正在发送请求到: {url}")
            print(f"使用本地种子: {seed} (仅用于本地，未发送给API)")
            
            # 更详细的请求调试信息
            debug_payload = payload.copy()
            if "input" in debug_payload:
                debug_input = debug_payload["input"].copy()
                
                # 检查并记录关键字段
                for key in debug_input.keys():
                    if key == "audio_file":
                        audio_file_len = len(debug_input["audio_file"])
                        debug_input["audio_file"] = f"[BASE64 AUDIO DATA - {audio_file_len} characters]"
                        print(f"音频文件Base64长度: {audio_file_len}")
                        # 检查base64编码是否包含无效字符
                        audio_base64 = payload["input"]["audio_file"]
                        invalid_chars = [c for c in audio_base64 if c not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/="]
                        if invalid_chars:
                            print(f"警告: 音频Base64包含{len(invalid_chars)}个无效字符: {invalid_chars[:10]} ...")
                        # 检查base64编码长度是否是4的倍数
                        if len(audio_base64) % 4 != 0:
                            print(f"警告: 音频Base64长度({len(audio_base64)})不是4的倍数，可能缺少填充")
                    elif key == "video_url":
                        print(f"视频URL: {debug_input['video_url']}")
                    elif key == "video_id":
                        print(f"视频ID: {debug_input['video_id']}")
                    elif key == "audio_url":
                        print(f"音频URL: {debug_input['audio_url']}")
                
                debug_payload["input"] = debug_input
            
            print(f"请求数据: {json.dumps(debug_payload, indent=2, ensure_ascii=False)}")
            
            # 发送请求前记录详细信息
            print(f"请求类型: {'视频URL' if 'video_url' in payload['input'] else '视频ID'}")
            print(f"音频类型: {'音频文件' if audio_type == 'file' else '音频URL'}")
            print(f"工作模式: {mode}")
            
            # 发送请求
            response = requests.post(url, headers=headers, json=payload)
            
            # 尝试解析JSON响应
            try:
                response_data = response.json()
                print(f"响应状态码: {response.status_code}")
                print(f"响应数据: {json.dumps(response_data, indent=2, ensure_ascii=False)}")
            except:
                print(f"响应状态码: {response.status_code}")
                print(f"响应内容: {response.text}")
                raise Exception(f"API响应不是有效的JSON格式: {response.text}")

            # 检查错误并提供详细错误信息
            if response.status_code != 200:
                error_code = response_data.get('code')
                error_message = response_data.get('message')
                request_id = response_data.get('request_id')
                
                # 针对特定错误码提供更详细的错误分析
                if error_code == 1201 and "file base64 is invalid" in error_message:
                    # 分析是音频还是视频的base64问题
                    error_analysis = ""
                    if audio_type == "file" and "audio_file" in payload["input"]:
                        error_analysis = "检测到错误可能与音频文件的Base64编码有关。请检查：\n"
                        error_analysis += "1. 音频文件是否完整可读\n"
                        error_analysis += "2. 音频格式是否为MP3/WAV/M4A/ACC\n"
                        error_analysis += "3. 音频文件是否小于5MB\n"
                        error_analysis += "4. 尝试使用不同的音频文件测试"
                    elif "video_url" in payload["input"]:
                        error_analysis = "检测到错误可能与视频URL有关。请检查：\n"
                        error_analysis += "1. 视频URL是否可以公开访问(无需登录)\n"
                        error_analysis += "2. 视频格式是否为MP4/MOV\n"
                        error_analysis += "3. 视频时长是否在2-10秒之间\n"
                        error_analysis += "4. 视频分辨率是否为720p或1080p"
                    
                    print(f"错误分析：\n{error_analysis}")
                    raise Exception(f"API请求失败 (错误码: {error_code}): {error_message} (请求ID: {request_id})\n{error_analysis}")
                else:
                    raise Exception(f"API请求失败 (错误码: {error_code}): {error_message} (请求ID: {request_id})")

            # 提取响应数据
            data = response_data.get("data", {})
            task_id = data.get("task_id", "")
            task_status = data.get("task_status", "")
            updated_at = str(data.get("updated_at", ""))

            if not task_id:
                raise Exception("API未返回任务ID")

            print(f"成功创建口型同步任务，任务ID: {task_id} (本地种子: {seed})")
            return (task_id, task_status, updated_at, seed)

        except ValueError as ve:
            print(f"参数验证错误: {str(ve)}")
            return (f"错误: {str(ve)}", "failed", "", seed)
        except Exception as e:
            print(f"创建口型同步任务错误: {str(e)}")
            return (f"错误: {str(e)}", "failed", "", seed)

    @classmethod
    def IS_CHANGED(cls, api_token, mode="text2video", text="", 
                voice_id="girlfriend_1_speech02", voice_language="zh", 
                voice_speed=1.0, audio_type="url", audio_url="", 
                audio_file="", callback_url="", seed=-1,
                video_id="", video_url=""):
        """
        此方法用于判断节点是否需要重新执行
        我们使用种子控制重新执行逻辑
        """
        if seed == -1:
            return random.randint(0, 0xffffffffffffffff)
        return seed 