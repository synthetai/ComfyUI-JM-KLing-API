import json
import os
import time
import random
import requests
import base64
import io
import glob
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import re
import tempfile
import shutil
from queue import Queue

# 尝试导入音频处理库
try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False
    print("警告：未安装pydub库，将无法进行音频处理。请使用pip install pydub安装")

# 尝试导入ffmpeg-python
try:
    import ffmpeg
    FFMPEG_PYTHON_AVAILABLE = True
except ImportError:
    FFMPEG_PYTHON_AVAILABLE = False
    print("警告：未安装ffmpeg-python库，将使用子进程方式调用ffmpeg。建议使用pip install ffmpeg-python安装")

# 获取临时目录和输出目录
import folder_paths


class KLingAILipSyncAsync:
    """
    KLingAI Lip Sync Async Node
    异步创建长音频口型同步任务节点
    """
    
    def __init__(self):
        self.api_base = "https://api.klingai.com"
        self.lip_sync_endpoint = "/v1/videos/lip-sync"
        self.query_endpoint = "/v1/videos/lip-sync/{}"
        self.default_output_dir = folder_paths.get_output_directory()
        # 将临时目录也放到output目录下，避免使用系统临时目录
        self.tmp_dir = os.path.join(self.default_output_dir, "klip_sync_async_tmp")
        Path(self.tmp_dir).mkdir(parents=True, exist_ok=True)
        
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
                    "placeholder": "视频URL地址(mp4/mov格式)"
                }),
                "mode": (["audio2video"], {"default": "audio2video"}),
                "audio_type": (["file", "url"], {"default": "file"}),
                "audio_file": ("STRING", {
                    "default": "",
                    "multiline": False,
                    "placeholder": "本地音频文件路径(mp3/wav/m4a/acc格式)"
                }),
                "audio_url": ("STRING", {
                    "default": "",
                    "multiline": False,
                    "placeholder": "音频文件下载URL(mp3/wav/m4a/acc格式)"
                }),
                "audio_segment_duration": ("INT", {
                    "default": 10,
                    "min": 5,
                    "max": 30,
                    "step": 1,
                    "display": "slider"
                }),
                "max_workers": ("INT", {
                    "default": 3,
                    "min": 1,
                    "max": 10,
                    "step": 1,
                    "display": "slider"
                }),
                "query_interval_seconds": ("INT", {
                    "default": 60,
                    "min": 10,
                    "max": 300,
                    "step": 10,
                    "display": "slider"
                }),
                "output_filename": ("STRING", {
                    "default": "lip_sync_async_output",
                    "multiline": False,
                    "placeholder": "输出视频文件名(不含扩展名)"
                }),
                "custom_output_dir": ("STRING", {
                    "default": "",
                    "multiline": False,
                    "placeholder": "自定义输出目录路径"
                }),
                "keep_temp_files": ("BOOLEAN", {"default": False}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("video_path",)
    FUNCTION = "create_lip_sync_async"
    CATEGORY = "JM-KLingAI-API/lip-sync"
    OUTPUT_NODE = True

    def check_dependencies(self):
        """检查必要的依赖是否已安装"""
        missing_deps = []
        if not PYDUB_AVAILABLE:
            missing_deps.append("pydub")
        
        # 检查ffmpeg是否可用
        try:
            subprocess.run(["ffmpeg", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        except FileNotFoundError:
            missing_deps.append("ffmpeg")
        
        return missing_deps

    def download_audio(self, audio_url, target_path):
        """下载音频文件"""
        try:
            response = requests.get(audio_url, stream=True)
            response.raise_for_status()
            
            with open(target_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            return target_path
        except Exception as e:
            raise ValueError(f"下载音频文件失败: {str(e)}")

    def split_audio(self, audio_path, segment_duration, output_dir):
        """将音频分割成指定时长的片段"""
        if not PYDUB_AVAILABLE:
            raise ValueError("未安装pydub库，无法进行音频分割。请使用pip install pydub安装")
        
        try:
            # 检查文件是否存在
            if not os.path.exists(audio_path):
                raise ValueError(f"音频文件不存在: {audio_path}")
            
            # 获取文件扩展名
            file_ext = os.path.splitext(audio_path)[1].lower()
            if file_ext not in ['.mp3', '.wav', '.m4a', '.acc']:
                raise ValueError(f"不支持的音频格式: {file_ext}，仅支持mp3/wav/m4a/acc格式")
            
            # 加载音频文件
            if file_ext == '.mp3':
                audio = AudioSegment.from_mp3(audio_path)
            elif file_ext == '.wav':
                audio = AudioSegment.from_wav(audio_path)
            elif file_ext in ['.m4a', '.acc']:
                audio = AudioSegment.from_file(audio_path, format=file_ext[1:])
            else:
                raise ValueError(f"不支持的音频格式: {file_ext}")
            
            # 转换为毫秒
            segment_duration_ms = segment_duration * 1000
            
            # 分割音频
            segments = []
            for i, start in enumerate(range(0, len(audio), segment_duration_ms)):
                end = min(start + segment_duration_ms, len(audio))
                segment = audio[start:end]
                segment_path = os.path.join(output_dir, f"segment_{i:03d}{file_ext}")
                segment.export(segment_path, format=file_ext[1:])
                segments.append(segment_path)
                print(f"已创建音频片段 {i+1}: {segment_path} ({round((end-start)/1000, 2)}秒)")
            
            return segments
        except Exception as e:
            raise ValueError(f"分割音频文件时出错: {str(e)}")

    def create_lip_sync_task(self, api_token, video_url="", video_id="", audio_path="", task_index=0, max_retries=2, retry_delay=5):
        """创建单个口型同步任务，带重试机制"""
        retries = 0
        last_error = None
        
        while retries <= max_retries:
            try:
                # 准备请求头
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_token.strip()}"
                }

                # 准备请求体
                payload = {
                    "input": {
                        "mode": "audio2video",
                        "audio_type": "file"
                    }
                }
                
                # 添加视频参数 (视频ID或视频URL)
                if video_id:
                    payload["input"]["task_id"] = video_id.strip()
                    payload["input"]["video_id"] = video_id.strip()
                    print(f"任务 {task_index}: 使用视频ID: {video_id}")
                elif video_url:
                    payload["input"]["video_url"] = video_url.strip()
                    print(f"任务 {task_index}: 使用视频URL: {video_url}")
                
                # 读取音频文件并转为base64
                try:
                    with open(audio_path, 'rb') as f:
                        audio_bytes = f.read()
                        audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
                    
                    payload["input"]["audio_file"] = audio_base64
                    print(f"任务 {task_index}: 成功读取音频文件 {audio_path}, 大小: {len(audio_bytes)/1024:.2f}KB")
                except Exception as e:
                    raise ValueError(f"处理音频文件时出错: {str(e)}")
                
                # 发送API请求
                url = f"{self.api_base}{self.lip_sync_endpoint}"
                print(f"任务 {task_index}: 正在发送请求到: {url} (尝试 {retries+1}/{max_retries+1})")
                
                response = requests.post(url, headers=headers, json=payload)
                
                # 解析响应
                try:
                    response_data = response.json()
                    print(f"任务 {task_index}: 响应状态码: {response.status_code}")
                    # 打印响应的前200个字符以便于调试，避免打印过长的base64内容
                    response_text = json.dumps(response_data)
                    print(f"任务 {task_index}: 响应内容: {response_text[:200]}...")
                except Exception as json_err:
                    print(f"任务 {task_index}: 解析响应JSON失败: {str(json_err)}")
                    print(f"任务 {task_index}: 原始响应内容: {response.text[:200]}...")
                    raise Exception(f"解析响应JSON失败: {str(json_err)}")
                
                # 检查错误
                if response.status_code != 200:
                    error_code = response_data.get('code')
                    error_message = response_data.get('message')
                    request_id = response_data.get('request_id')
                    error_msg = f"API请求失败 (错误码: {error_code}): {error_message} (请求ID: {request_id})"
                    print(f"任务 {task_index}: {error_msg}")
                    
                    # 如果这是因为服务器负载问题，我们可以重试
                    if retries < max_retries:
                        retries += 1
                        wait_time = retry_delay * retries
                        print(f"任务 {task_index}: 将在 {wait_time} 秒后重试...")
                        time.sleep(wait_time)
                        continue
                    raise Exception(error_msg)

                # 提取响应数据
                data = response_data.get("data", {})
                task_id = data.get("task_id", "")
                
                if not task_id:
                    raise Exception("API未返回任务ID")

                print(f"任务 {task_index}: 成功创建口型同步任务，任务ID: {task_id}")
                return {
                    "task_index": task_index,
                    "task_id": task_id,
                    "audio_path": audio_path
                }
                
            except Exception as e:
                last_error = e
                if retries < max_retries:
                    retries += 1
                    wait_time = retry_delay * retries
                    print(f"任务 {task_index}: 创建任务失败: {str(e)}")
                    print(f"任务 {task_index}: 将在 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                else:
                    print(f"任务 {task_index}: 达到最大重试次数，任务创建失败: {str(e)}")
                    raise

    def poll_task_status(self, api_token, task_id, task_index, interval=10, max_retries=3, retry_delay=5):
        """轮询任务状态直到完成，带重试机制"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_token.strip()}"
        }
        
        url = f"{self.api_base}{self.query_endpoint.format(task_id)}"
        
        while True:
            try:
                print(f"任务 {task_index}: 查询状态: {task_id}")
                response = requests.get(url, headers=headers)
                
                if response.status_code != 200:
                    # 尝试获取JSON响应
                    try:
                        response_data = response.json()
                        error_message = response_data.get('message', '未知错误')
                        error_code = response_data.get('code', 'unknown')
                        request_id = response_data.get('request_id', 'unknown')
                        error_detail = f"状态码: {response.status_code}, 错误码: {error_code}, 消息: {error_message}, 请求ID: {request_id}"
                        print(f"任务 {task_index}: 查询状态错误 - {error_detail}")
                    except:
                        error_detail = f"状态码: {response.status_code}, 响应: {response.text[:200]}"
                        print(f"任务 {task_index}: 查询状态错误 - {error_detail}")
                    
                    raise Exception(f"查询状态错误: {error_detail}")
                
                # 解析响应
                try:
                    response_data = response.json()
                except Exception as json_err:
                    print(f"任务 {task_index}: 解析响应JSON失败: {str(json_err)}")
                    print(f"任务 {task_index}: 原始响应内容: {response.text[:200]}...")
                    raise Exception(f"解析响应JSON失败: {str(json_err)}")
                
                data = response_data.get("data", {})
                status = data.get("task_status")
                
                if not status:
                    print(f"任务 {task_index}: 响应数据中没有任务状态: {json.dumps(data)[:200]}")
                    raise Exception("响应数据中没有任务状态")
                
                print(f"任务 {task_index}: 当前状态: {status}")
                
                if status == "succeed":
                    videos = data.get("task_result", {}).get("videos", [])
                    if videos and videos[0].get("url"):
                        video_url = videos[0].get("url")
                        video_id = videos[0].get("id", "未知")
                        duration = videos[0].get("duration", "未知")
                        print(f"任务 {task_index}: 成功完成! 视频ID: {video_id}, 视频URL: {video_url}, 时长: {duration}秒")
                        return {
                            "task_index": task_index,
                            "video_url": video_url,
                            "video_id": video_id,
                            "status": "succeed"
                        }
                    else:
                        print(f"任务 {task_index}: 任务成功但未返回视频URL: {json.dumps(videos)[:200]}")
                        raise Exception("任务成功但未返回视频URL")
                elif status == "failed":
                    error_msg = data.get('task_status_msg', '未知错误')
                    task_info = data.get('task_info', {})
                    created_at = data.get('created_at', '')
                    updated_at = data.get('updated_at', '')
                    
                    # 提供更详细的错误信息
                    error_detail = f"任务失败: {error_msg}"
                    if task_info:
                        error_detail += f", 任务信息: {json.dumps(task_info)[:100]}"
                    if created_at and updated_at:
                        error_detail += f", 创建时间: {created_at}, 更新时间: {updated_at}"
                    
                    print(f"任务 {task_index}: {error_detail}")
                    raise Exception(error_detail)
                
                # 等待指定的时间间隔
                time.sleep(interval)
                
            except Exception as e:
                # 记录详细错误信息，但继续尝试轮询
                print(f"任务 {task_index}: 查询状态出错: {str(e)}")
                
                # 某些错误可能是暂时的，如网络问题，我们等待一段时间再重试
                retry_time = retry_delay
                print(f"任务 {task_index}: 将在 {retry_time} 秒后重试查询...")
                time.sleep(retry_time)
                continue

    def download_video(self, video_url, output_path, task_index):
        """下载视频"""
        try:
            print(f"任务 {task_index}: 正在下载视频: {video_url}")
            response = requests.get(video_url, stream=True)
            response.raise_for_status()
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            print(f"任务 {task_index}: 视频已下载到: {output_path}")
            return output_path
        except Exception as e:
            print(f"任务 {task_index}: 下载视频出错: {str(e)}")
            raise

    def merge_videos(self, video_paths, output_path):
        """合并视频"""
        try:
            # 创建一个临时文件，存储要合并的文件列表
            list_file_path = os.path.join(self.tmp_dir, "files_to_merge.txt")
            with open(list_file_path, 'w') as f:
                for video_path in video_paths:
                    f.write(f"file '{video_path}'\n")
            
            # 使用ffmpeg合并视频
            cmd = [
                "ffmpeg", "-y", "-f", "concat", "-safe", "0", 
                "-i", list_file_path, "-c", "copy", output_path
            ]
            
            print(f"正在合并视频: {' '.join(cmd)}")
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            if result.returncode != 0:
                raise Exception(f"合并视频失败: {result.stderr.decode()}")
            
            print(f"视频已成功合并到: {output_path}")
            return output_path
            
        except Exception as e:
            print(f"合并视频出错: {str(e)}")
            raise

    def process_task(self, api_token, video_url="", video_id="", segment_path="", task_index=0, query_interval=60, 
                      max_poll_time=1800):  # 默认最长等待30分钟，与查询间隔增加相匹配
        """处理单个任务的完整流程"""
        try:
            # 1. 创建任务
            task_info = self.create_lip_sync_task(api_token, video_url, video_id, segment_path, task_index)
            
            # 2. 轮询任务状态（带超时）
            poll_start_time = time.time()
            
            try:
                # 设置超时时间
                while True:
                    # 检查是否已经超时
                    elapsed_poll_time = time.time() - poll_start_time
                    if elapsed_poll_time > max_poll_time:
                        raise Exception(f"任务轮询超时，已等待{elapsed_poll_time/60:.1f}分钟，超过最大等待时间{max_poll_time/60:.1f}分钟")
                        
                    # 尝试获取任务状态
                    try:
                        print(f"任务 {task_index}: 查询任务状态，将等待 {query_interval} 秒获取结果...")
                        result = self.poll_task_status(api_token, task_info["task_id"], task_index, query_interval)
                        break  # 如果成功获取结果，退出循环
                    except Exception as poll_error:
                        # 检查是否已经超时
                        elapsed_poll_time = time.time() - poll_start_time
                        if elapsed_poll_time > max_poll_time:
                            raise Exception(f"任务轮询超时，已等待{elapsed_poll_time/60:.1f}分钟，超过最大等待时间{max_poll_time/60:.1f}分钟。最后错误: {str(poll_error)}")
                        
                        # 未超时，打印错误并继续轮询
                        print(f"任务 {task_index}: 轮询出错但将继续尝试: {str(poll_error)}")
                        print(f"任务 {task_index}: 已轮询 {elapsed_poll_time/60:.1f} 分钟，将继续尝试，最大等待时间 {max_poll_time/60:.1f} 分钟")
                        time.sleep(query_interval)
                        continue
            
            except Exception as timeout_error:
                print(f"任务 {task_index}: 轮询超时或出错: {str(timeout_error)}")
                raise timeout_error
            
            # 3. 下载视频
            video_output_path = os.path.join(self.tmp_dir, f"video_segment_{task_index:03d}.mp4")
            self.download_video(result["video_url"], video_output_path, task_index)
            
            # 4. 创建完整的结果信息
            full_result = {
                "task_index": task_index,
                "video_path": video_output_path,
                "task_id": task_info["task_id"],
                "video_url": result["video_url"],
                "status": "succeed",
                "audio_path": segment_path,
                "processing_time": time.time() - poll_start_time
            }
            
            # 添加视频ID如果存在
            if "video_id" in result:
                full_result["video_id"] = result["video_id"]
                
            print(f"任务 {task_index}: 全部处理成功，总耗时: {full_result['processing_time']:.1f}秒")
            return full_result
            
        except Exception as e:
            error_detail = str(e)
            error_type = type(e).__name__
            print(f"任务 {task_index}: 处理失败 ({error_type}): {error_detail}")
            
            # 构建更详细的错误信息
            return {
                "task_index": task_index,
                "error": error_detail,
                "error_type": error_type,
                "status": "failed",
                "audio_path": segment_path,
                "timestamp": time.time()
            }

    def ensure_directory(self, directory):
        """确保目录存在，不存在则创建"""
        Path(directory).mkdir(parents=True, exist_ok=True)
        return directory

    def create_lip_sync_async(self, api_token, video_id="", video_url="", mode="audio2video", 
                            audio_type="file", audio_file="", audio_url="", 
                            audio_segment_duration=10, max_workers=3, 
                            query_interval_seconds=60, output_filename="lip_sync_async_output", 
                            custom_output_dir="", keep_temp_files=False):
        """
        异步创建口型同步任务
        """
        start_time = time.time()
        
        try:
            # 显示配置信息
            print(f"=========== KLingAI 口型同步异步处理 ===========")
            print(f"任务查询间隔: {query_interval_seconds} 秒")
            print(f"最大并发任务数: {max_workers}")
            print(f"临时文件目录: {self.tmp_dir}")
            print(f"输出目录: {custom_output_dir if custom_output_dir else self.default_output_dir}")
            print(f"==================================================")
            
            # 检查依赖
            missing_deps = self.check_dependencies()
            if missing_deps:
                raise ValueError(f"缺少必要的依赖: {', '.join(missing_deps)}。请先安装这些依赖。")
            
            # 验证必要参数
            if not api_token:
                raise ValueError("API令牌不能为空")
                
            # 检查视频参数
            if not video_id and not video_url:
                raise ValueError("视频ID和视频URL至少需要提供一个")
            if video_id and video_url:
                raise ValueError("视频ID和视频URL不能同时提供，请只选择一种方式")
            
            # 仅支持audio2video模式
            if mode != "audio2video":
                raise ValueError("异步节点仅支持audio2video模式，不支持text2video模式")
            
            # 根据音频类型验证参数
            if audio_type == "file":
                if not audio_file:
                    raise ValueError("使用file模式时，音频文件路径不能为空")
                audio_path = audio_file
                # 检查文件是否存在
                if not os.path.exists(audio_path):
                    raise ValueError(f"音频文件不存在: {audio_path}")
            else:  # audio_type == "url"
                if not audio_url:
                    raise ValueError("使用url模式时，音频URL不能为空")
                # 下载音频
                audio_path = os.path.join(self.tmp_dir, f"downloaded_audio_{int(time.time())}.mp3")
                print(f"正在从URL下载音频: {audio_url}")
                print(f"下载到: {audio_path}")
                audio_path = self.download_audio(audio_url, audio_path)
            
            # 输出目录
            output_dir = custom_output_dir if custom_output_dir else self.default_output_dir
            output_dir = self.ensure_directory(output_dir)
            
            # 最终输出文件路径
            final_output_path = os.path.join(output_dir, f"{output_filename}.mp4")
            print(f"最终视频将保存到: {final_output_path}")
            
            # 分割音频
            print(f"正在将音频分割为{audio_segment_duration}秒的片段...")
            audio_segments = self.split_audio(audio_path, audio_segment_duration, self.tmp_dir)
            print(f"音频分割完成，共创建了{len(audio_segments)}个片段")
            
            # 计算预估完成时间
            # 假设每个任务需要3-5分钟，考虑并发因素
            estimated_minutes = (len(audio_segments) / max_workers) * 5
            print(f"预估完成时间: 约 {int(estimated_minutes)} 分钟 (取决于API处理速度和任务复杂度)")
            print(f"任务会在后台运行，每 {query_interval_seconds} 秒查询一次状态")
            
            # 检查分段数量，并给出警告
            if len(audio_segments) > 10:
                print(f"警告: 音频被分割成了{len(audio_segments)}个片段，过多的并发请求可能导致API限制。")
                print(f"建议: 增加audio_segment_duration值以减少片段数，或减少max_workers值以降低并发量。")
                
            # 使用线程池异步处理任务
            results = []
            
            # 限制同时运行的任务数量
            task_semaphore = threading.Semaphore(max_workers)
            
            # 添加任务间延迟以避免API速率限制
            api_rate_limit_delay = 1.0  # 每个API请求之间的最小延迟(秒)
            
            # 创建锁来确保API请求之间有足够的间隔
            api_rate_limit_lock = threading.Lock()
            last_api_request_time = [time.time()]  # 使用列表以便在函数内可修改
            
            def process_task_with_rate_limit(api_token, video_url, video_id, segment_path, task_idx, query_interval):
                # 获取信号量，限制并发数
                with task_semaphore:
                    # 确保API请求之间有最小延迟
                    with api_rate_limit_lock:
                        time_since_last_request = time.time() - last_api_request_time[0]
                        if time_since_last_request < api_rate_limit_delay:
                            delay = api_rate_limit_delay - time_since_last_request
                            print(f"任务 {task_idx}: 等待 {delay:.2f} 秒以遵守API速率限制...")
                            time.sleep(delay)
                        last_api_request_time[0] = time.time()
                        
                    # 执行任务处理
                    return self.process_task(api_token, video_url, video_id, segment_path, task_idx, query_interval)
            
            # 使用线程池异步处理任务，但增加了速率限制
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # 提交所有任务
                futures = {
                    executor.submit(
                        process_task_with_rate_limit, 
                        api_token, 
                        video_url,
                        video_id,
                        segment_path, 
                        i, 
                        query_interval_seconds
                    ): i for i, segment_path in enumerate(audio_segments)
                }
                
                # 收集结果
                for future in as_completed(futures):
                    task_index = futures[future]
                    try:
                        result = future.result()
                        results.append(result)
                        print(f"任务 {task_index} 完成: {result['status']}")
                    except Exception as e:
                        print(f"任务 {task_index} 异常: {str(e)}")
                        results.append({
                            "task_index": task_index,
                            "error": str(e),
                            "status": "failed"
                        })
            
            # 检查是否所有任务都成功
            failed_tasks = [r for r in results if r["status"] == "failed"]
            
            # 如果有任务失败但并非全部失败，尝试仅使用成功的任务合并视频
            successful_tasks = [r for r in results if r["status"] == "succeed"]
            
            if failed_tasks:
                failed_indices = [r["task_index"] for r in failed_tasks]
                fail_percentage = len(failed_tasks) / len(results) * 100
                
                if not successful_tasks:
                    # 没有任何成功的任务，无法继续
                    raise ValueError(f"所有任务都失败了。失败的任务索引: {failed_indices}")
                
                # 根据失败的比例给出不同的处理方式
                if fail_percentage > 50:  # 如果超过50%的任务失败
                    print(f"警告: {len(failed_tasks)}/{len(results)} ({fail_percentage:.1f}%)的任务失败。")
                    print(f"失败的任务索引: {failed_indices}")
                    
                    # 询问用户是否要继续
                    print(f"仍然有 {len(successful_tasks)} 个成功的任务，继续尝试合并这些成功的部分...")
                else:
                    # 失败比例较低，仅警告并继续
                    print(f"部分任务失败 ({len(failed_tasks)}/{len(results)}), 索引: {failed_indices}")
                    print(f"继续合并 {len(successful_tasks)} 个成功的片段...")
            
            # 如果没有成功的任务，无法继续
            if not successful_tasks:
                raise ValueError(f"没有成功完成的任务，无法合并视频")
                
            # 按原顺序排序视频路径
            successful_tasks.sort(key=lambda r: r["task_index"])
            video_paths = [r["video_path"] for r in successful_tasks]
            
            # 合并视频
            print("视频片段下载完成，开始合并...")
            print(f"合并 {len(video_paths)}/{len(audio_segments)} 个视频片段")
            self.merge_videos(video_paths, final_output_path)
            
            # 清理临时文件
            if not keep_temp_files:
                print("清理临时文件...")
                for segment in audio_segments:
                    try:
                        os.remove(segment)
                        print(f"已删除音频片段: {os.path.basename(segment)}")
                    except Exception as e:
                        print(f"清理音频文件失败: {segment}, 错误: {str(e)}")
                
                for result in results:
                    if result.get("status") == "succeed" and "video_path" in result:
                        try:
                            os.remove(result["video_path"])
                            print(f"已删除视频片段: {os.path.basename(result['video_path'])}")
                        except Exception as e:
                            print(f"清理视频文件失败: {result['video_path']}, 错误: {str(e)}")
                
                # 清理下载的音频（如果是URL模式）
                if audio_type == "url":
                    try:
                        os.remove(audio_path)
                        print(f"已删除下载的音频文件: {os.path.basename(audio_path)}")
                    except Exception as e:
                        print(f"清理下载的音频文件失败: {audio_path}, 错误: {str(e)}")
                        
                # 清理合并视频使用的文件列表
                list_file_path = os.path.join(self.tmp_dir, "files_to_merge.txt")
                if os.path.exists(list_file_path):
                    try:
                        os.remove(list_file_path)
                        print(f"已删除合并视频使用的文件列表")
                    except Exception as e:
                        print(f"清理文件列表失败: {list_file_path}, 错误: {str(e)}")
            else:
                print(f"保留临时文件: 音频片段和中间视频文件将保留在 {self.tmp_dir}")
            
            elapsed_time = time.time() - start_time
            minutes = int(elapsed_time // 60)
            seconds = int(elapsed_time % 60)
            
            print(f"\n==================================================")
            print(f"所有处理完成，耗时: {minutes}分{seconds}秒")
            print(f"最终视频已保存到: {final_output_path}")
            
            # 成功与失败的统计
            if failed_tasks:
                print(f"处理统计: 总计 {len(results)} 个片段，成功 {len(successful_tasks)} 个，失败 {len(failed_tasks)} 个")
                if len(failed_tasks) > 0:
                    print(f"失败的片段索引: {[t['task_index'] for t in failed_tasks]}")
                    print("注意: 最终视频中会缺少这些片段")
            else:
                print(f"处理统计: 所有 {len(results)} 个片段处理成功")
                
            print(f"==================================================\n")
            
            # 返回视频路径
            return (final_output_path,)
        
        except ValueError as ve:
            error_msg = f"参数验证错误: {str(ve)}"
            print(error_msg)
            return (error_msg,)
        except Exception as e:
            error_msg = f"处理错误: {str(e)}"
            print(error_msg)
            return (error_msg,)
            
    @classmethod
    def IS_CHANGED(cls, api_token, video_id="", video_url="", mode="audio2video", audio_type="file", audio_file="", 
                audio_url="", audio_segment_duration=10, max_workers=3, 
                query_interval_seconds=60, output_filename="lip_sync_async_output", 
                custom_output_dir="", keep_temp_files=False):
        """
        确保节点总是被执行
        """
        return time.time() 