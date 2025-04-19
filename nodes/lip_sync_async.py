import json
import time
import random
import requests
import base64
import os
import io
import glob
import tempfile
import uuid
from datetime import datetime
import re
import subprocess
from pathlib import Path
import threading
import shutil
import concurrent.futures

import folder_paths
from pydub import AudioSegment


class KLingAILipSyncAsync:
    """
    KLingAI Lip Sync Async Node
    Creates video lip sync tasks asynchronously for long audio files
    by splitting them into segments
    """
    
    def __init__(self):
        self.api_base = "https://api.klingai.com"
        self.lip_sync_endpoint = "/v1/videos/lip-sync"
        self.query_endpoint = "/v1/videos/lip-sync/{}"
        
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "api_token": ("STRING", {"default": "", "multiline": False}),
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
            },
            "optional": {
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
                "segment_duration": ("INT", {
                    "default": 10,
                    "min": 5,
                    "max": 30,
                    "step": 1
                }),
                "max_concurrent_tasks": ("INT", {
                    "default": 5,
                    "min": 1,
                    "max": 10,
                    "step": 1
                }),
                "poll_interval_seconds": ("INT", {
                    "default": 30,
                    "min": 10,
                    "max": 120,
                    "step": 5
                }),
                "output_filename": ("STRING", {
                    "default": "lip_sync_combined",
                    "multiline": False,
                    "placeholder": "输出视频文件名"
                }),
                "sync_adjust_ms": ("INT", {
                    "default": 0,
                    "min": -1000,
                    "max": 1000,
                    "step": 10,
                    "display": "slider"
                })
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("video_path",)
    FUNCTION = "process_lip_sync_async"
    CATEGORY = "JM-KLingAI-API/lip-sync"
    OUTPUT_NODE = True

    def download_audio(self, audio_url, output_path):
        """
        Download audio file from URL
        """
        try:
            print(f"正在从 {audio_url} 下载音频...")
            response = requests.get(audio_url, stream=True)
            response.raise_for_status()
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            print(f"音频下载成功: {output_path}")
            return True
        except Exception as e:
            print(f"音频下载失败: {str(e)}")
            return False

    def split_audio(self, audio_file_path, segment_duration, output_dir):
        """
        Split audio file into segments of specified duration
        """
        try:
            print(f"正在分割音频文件: {audio_file_path}")
            # Determine audio format from extension
            file_ext = os.path.splitext(audio_file_path)[1].lower()
            
            # Load audio file
            audio = AudioSegment.from_file(audio_file_path, format=file_ext.replace('.', ''))
            
            # Get total duration in milliseconds
            total_duration = len(audio)
            segment_duration_ms = segment_duration * 1000
            
            segment_files = []
            
            # Split audio into segments
            for i, start_ms in enumerate(range(0, total_duration, segment_duration_ms)):
                end_ms = min(start_ms + segment_duration_ms, total_duration)
                segment = audio[start_ms:end_ms]
                
                # Skip segments shorter than 2 seconds (2000ms)
                if len(segment) < 2000:
                    print(f"跳过过短的音频片段 {i+1}: {len(segment)/1000:.1f}秒")
                    continue
                
                # Save segment
                segment_path = os.path.join(output_dir, f"segment_{i:03d}{file_ext}")
                segment.export(segment_path, format=file_ext.replace('.', ''))
                segment_files.append(segment_path)
                
                print(f"创建音频片段 {i+1}: {len(segment)/1000:.1f}秒, 保存至 {segment_path}")
            
            return segment_files
        except Exception as e:
            print(f"音频分割失败: {str(e)}")
            return []

    def create_lip_sync_task(self, api_token, video_id, video_url, audio_file_path, max_retries=3, retry_delay=5):
        """
        Create a lip sync task for a specific audio segment
        """
        retries = 0
        while retries <= max_retries:
            try:
                # Prepare headers
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_token.strip()}"
                }
                
                # Prepare payload
                payload = {
                    "input": {
                        "mode": "audio2video",
                        "audio_type": "file"
                    }
                }
                
                # Add video source (either ID or URL)
                if video_id:
                    payload["input"]["task_id"] = video_id.strip()
                    payload["input"]["video_id"] = video_id.strip()
                elif video_url:
                    payload["input"]["video_url"] = video_url.strip()
                
                # Read and encode audio file
                with open(audio_file_path, 'rb') as f:
                    audio_bytes = f.read()
                    audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
                    payload["input"]["audio_file"] = audio_base64
                
                # Send request
                url = f"{self.api_base}{self.lip_sync_endpoint}"
                response = requests.post(url, headers=headers, json=payload)
                response.raise_for_status()
                
                response_data = response.json()
                task_id = response_data.get("data", {}).get("task_id", "")
                
                if not task_id:
                    raise ValueError("未能获取任务ID")
                
                print(f"成功创建口型同步任务: {task_id} 用于音频 {os.path.basename(audio_file_path)}")
                return task_id
            except requests.exceptions.HTTPError as e:
                # 429 错误表示请求过多
                if hasattr(e.response, 'status_code') and e.response.status_code == 429:
                    retries += 1
                    wait_time = retry_delay * (2 ** retries)  # 指数退避
                    print(f"请求频率过高，等待 {wait_time} 秒后重试... ({retries}/{max_retries})")
                    time.sleep(wait_time)
                    continue
                print(f"创建口型同步任务失败: {str(e)}")
                return None
            except Exception as e:
                print(f"创建口型同步任务失败: {str(e)}")
                return None
        
        print(f"达到最大重试次数，创建口型同步任务失败")
        return None

    def create_task_worker(self, api_token, video_id, video_url, segment_file, task_semaphore, delay_seconds=2):
        """
        Worker function for concurrent task creation with rate limiting
        """
        # 使用信号量限制并发，并在释放前等待一段时间防止请求过快
        with task_semaphore:
            task_id = self.create_lip_sync_task(api_token, video_id, video_url, segment_file)
            # 在释放信号量前等待，防止API请求过快
            time.sleep(delay_seconds)
            
        return {
            "task_id": task_id,
            "audio_file": segment_file,
            "status": "pending" if task_id else "failed",
            "video_url": None,
            "video_file": None
        }

    def query_task_status(self, api_token, task_id):
        """
        Query task status
        """
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_token.strip()}"
            }
            
            url = f"{self.api_base}{self.query_endpoint.format(task_id)}"
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            response_data = response.json()
            data = response_data.get("data", {})
            status = data.get("task_status")
            
            return status, data
        except Exception as e:
            print(f"查询任务状态失败: {str(e)}")
            return "failed", {}

    def download_video(self, video_url, output_path):
        """
        Download video from URL
        """
        try:
            print(f"正在从 {video_url} 下载视频...")
            response = requests.get(video_url, stream=True)
            response.raise_for_status()
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            print(f"视频下载成功: {output_path}")
            return True
        except Exception as e:
            print(f"视频下载失败: {str(e)}")
            return False

    def merge_videos(self, video_files, output_path):
        """
        Merge video files using ffmpeg
        """
        try:
            # Create a temporary file listing all videos
            file_list_path = os.path.join(os.path.dirname(output_path), "file_list.txt")
            with open(file_list_path, 'w') as f:
                for video_file in video_files:
                    f.write(f"file '{video_file}'\n")
            
            # Execute ffmpeg command
            cmd = [
                "ffmpeg", 
                "-f", "concat", 
                "-safe", "0", 
                "-i", file_list_path, 
                "-c", "copy", 
                output_path
            ]
            
            print(f"执行合并命令: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            # Remove the temporary file list
            if os.path.exists(file_list_path):
                os.remove(file_list_path)
            
            if result.returncode != 0:
                print(f"FFmpeg错误: {result.stderr}")
                return False
            
            print(f"视频成功合并为: {output_path}")
            return True
        except Exception as e:
            print(f"视频合并失败: {str(e)}")
            return False

    def merge_videos_with_original_audio(self, video_files, original_audio_path, output_path, sync_adjust_ms=0):
        """
        Merge video files and replace the audio with the original audio file
        """
        try:
            # 1. First merge all video segments
            temp_merged_video = output_path.replace(".mp4", "_temp.mp4")
            if not self.merge_videos(video_files, temp_merged_video):
                raise ValueError("合并视频片段失败")
            
            print(f"临时视频文件已创建: {temp_merged_video}")
            
            # 2. 提取音频并创建静音视频以确保同步
            temp_audio_path = output_path.replace(".mp4", "_audio.aac")
            temp_silent_video = output_path.replace(".mp4", "_silent.mp4")
            
            # 提取音频
            cmd_extract_audio = [
                "ffmpeg",
                "-i", original_audio_path,
                "-vn",  # 不使用视频
                "-acodec", "aac",  # 使用AAC编码
                "-strict", "experimental",
                temp_audio_path
            ]
            
            print(f"提取音频命令: {' '.join(cmd_extract_audio)}")
            result = subprocess.run(cmd_extract_audio, capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"提取音频错误: {result.stderr}")
                # 继续尝试直接合并
            else:
                print(f"成功提取音频: {temp_audio_path}")
            
            # 3. 创建不带音轨的视频副本
            cmd_silent_video = [
                "ffmpeg",
                "-i", temp_merged_video,
                "-an",  # 移除音频
                "-c:v", "copy",  # 复制视频编码
                temp_silent_video
            ]
            
            print(f"创建静音视频命令: {' '.join(cmd_silent_video)}")
            result = subprocess.run(cmd_silent_video, capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"创建静音视频错误: {result.stderr}")
                # 继续尝试直接合并
            else:
                print(f"成功创建静音视频: {temp_silent_video}")
                # 使用静音视频替代原视频
                temp_merged_video = temp_silent_video
            
            # 4. 使用精确同步参数合并视频和音频
            cmd = [
                "ffmpeg",
                "-i", temp_merged_video,  # 视频输入
                "-i", original_audio_path,  # 原始音频输入
            ]
            
            # 添加音频延迟参数（如果需要）
            if sync_adjust_ms != 0:
                if sync_adjust_ms > 0:
                    # 正值表示音频需要延迟（口型比音频快）
                    delay_sec = sync_adjust_ms / 1000.0
                    cmd.extend(["-itsoffset", f"{delay_sec}", "-i", original_audio_path])
                    cmd.extend(["-map", "0:v", "-map", "2:a"])  # 使用延迟后的音频
                    print(f"应用音频延迟: {delay_sec}秒")
                else:
                    # 负值表示视频需要延迟（口型比音频慢）
                    delay_sec = abs(sync_adjust_ms) / 1000.0
                    cmd.extend(["-itsoffset", f"{delay_sec}", "-i", temp_merged_video])
                    cmd.extend(["-map", "2:v", "-map", "1:a"])  # 使用延迟后的视频
                    print(f"应用视频延迟: {delay_sec}秒")
            else:
                # 默认映射
                cmd.extend(["-map", "0:v", "-map", "1:a"])
            
            # 添加其他参数
            cmd.extend([
                "-c:v", "copy",  # 复制视频编码，不重新编码
                "-c:a", "aac",   # 使用AAC音频编码
                "-shortest",     # 最短的输入文件长度决定输出长度
                "-vsync", "2",   # 处理可变帧率，改善同步
                "-async", "1",   # 改善音频同步
                output_path
            ])
            
            print(f"执行音频替换命令: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            # 删除临时文件
            temp_files = [temp_merged_video, temp_audio_path, temp_silent_video]
            for temp_file in temp_files:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                    print(f"已删除临时文件: {temp_file}")
            
            if result.returncode != 0:
                print(f"FFmpeg音频替换错误: {result.stderr}")
                return False
            
            print(f"视频成功合并并替换原始音频: {output_path}")
            return True
        except Exception as e:
            print(f"视频合并并替换音频失败: {str(e)}")
            return False

    def process_lip_sync_async(self, api_token, video_id="", video_url="", 
                             audio_type="url", audio_url="", audio_file="",
                             segment_duration=10, max_concurrent_tasks=5,
                             poll_interval_seconds=30, sync_adjust_ms=0,
                             output_filename="lip_sync_combined"):
        """
        Main function to process lip sync asynchronously
        """
        try:
            # Validate required parameters
            if not api_token:
                raise ValueError("API令牌不能为空")
            
            if not video_id and not video_url:
                raise ValueError("视频ID和视频URL至少需要提供一个")
            
            if video_id and video_url:
                raise ValueError("视频ID和视频URL不能同时提供，请只选择一种方式")
            
            if audio_type == "url" and not audio_url:
                raise ValueError("当audio_type为url时，audio_url不能为空")
            
            if audio_type == "file" and not audio_file:
                raise ValueError("当audio_type为file时，audio_file不能为空")
            
            # Create timestamp-based temporary directory
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            temp_dir_name = f"lip_sync_temp_{timestamp}"
            output_dir = folder_paths.get_output_directory()
            temp_dir = os.path.join(output_dir, temp_dir_name)
            audio_segments_dir = os.path.join(temp_dir, "audio_segments")
            videos_dir = os.path.join(temp_dir, "videos")
            
            # Create directories
            os.makedirs(temp_dir, exist_ok=True)
            os.makedirs(audio_segments_dir, exist_ok=True)
            os.makedirs(videos_dir, exist_ok=True)
            
            print(f"创建临时工作目录: {temp_dir}")
            
            # Handle audio source
            local_audio_path = ""
            if audio_type == "url":
                # Download audio from URL
                file_ext = os.path.splitext(audio_url.split("?")[0])[1]
                if not file_ext:
                    file_ext = ".mp3"  # Default extension
                local_audio_path = os.path.join(temp_dir, f"original_audio{file_ext}")
                if not self.download_audio(audio_url, local_audio_path):
                    raise ValueError("无法下载音频文件")
            else:
                # Copy local audio file
                if not os.path.exists(audio_file):
                    raise ValueError(f"音频文件不存在: {audio_file}")
                
                file_ext = os.path.splitext(audio_file)[1]
                local_audio_path = os.path.join(temp_dir, f"original_audio{file_ext}")
                shutil.copyfile(audio_file, local_audio_path)
            
            # Split audio into segments
            segment_files = self.split_audio(local_audio_path, segment_duration, audio_segments_dir)
            
            if not segment_files:
                raise ValueError("音频分割失败或没有有效片段")
            
            print(f"音频已分割为 {len(segment_files)} 个片段")
            
            # 使用线程池并发创建口型同步任务，最多max_concurrent_tasks个并发任务
            task_mapping = {}
            print(f"开始创建口型同步任务，最大并发数: {max_concurrent_tasks}, 总片段数: {len(segment_files)}")
            
            # 分批处理音频片段，确保所有片段都被处理
            batch_size = max_concurrent_tasks
            remaining_segments = segment_files.copy()
            
            while remaining_segments:
                # 取出当前批次的片段
                current_batch = remaining_segments[:batch_size]
                remaining_segments = remaining_segments[batch_size:]
                
                print(f"处理批次: {len(current_batch)} 个片段，剩余: {len(remaining_segments)} 个片段")
                
                # 使用信号量控制实际并发请求数
                task_semaphore = threading.Semaphore(max_concurrent_tasks)
                
                # 使用线程池处理当前批次
                with concurrent.futures.ThreadPoolExecutor(max_workers=len(current_batch)) as executor:
                    # 初始化任务列表
                    future_to_segment = {}
                    
                    # 提交当前批次的所有任务
                    for segment_file in current_batch:
                        future = executor.submit(
                            self.create_task_worker, 
                            api_token, 
                            video_id, 
                            video_url, 
                            segment_file,
                            task_semaphore,
                            2  # 每个请求完成后延迟2秒再释放信号量
                        )
                        future_to_segment[future] = segment_file
                    
                    # 等待当前批次所有任务完成并收集结果
                    for future in concurrent.futures.as_completed(future_to_segment):
                        segment_file = future_to_segment[future]
                        try:
                            result = future.result()
                            if result["task_id"]:
                                task_mapping[result["task_id"]] = result
                                print(f"任务已创建: {result['task_id']} 对应音频 {os.path.basename(segment_file)}")
                            else:
                                print(f"创建任务失败，音频: {os.path.basename(segment_file)}")
                                # 任务失败时，添加回待处理队列，稍后重试（除非达到重试上限）
                                if segment_file not in remaining_segments:
                                    # 为避免无限循环，可以添加重试计数器，这里简化处理
                                    remaining_segments.append(segment_file)
                        except Exception as e:
                            print(f"处理任务时出错: {str(e)}, 音频: {os.path.basename(segment_file)}")
                            # 出错时也添加回待处理队列
                            if segment_file not in remaining_segments:
                                remaining_segments.append(segment_file)
                
                # 每处理完一批次等待一段时间，避免API限制
                if remaining_segments:
                    wait_time = 30  # 增加到30秒
                    print(f"批次完成，等待 {wait_time} 秒后处理下一批次...")
                    time.sleep(wait_time)
            
            # 检查是否所有片段都创建了任务
            created_segments = set(info["audio_file"] for info in task_mapping.values())
            missing_segments = [s for s in segment_files if s not in created_segments]
            
            if missing_segments:
                print(f"警告: 有 {len(missing_segments)} 个音频片段未创建任务: {[os.path.basename(s) for s in missing_segments]}")
                
                # 重试那些未创建任务的片段
                print("尝试为未创建任务的片段重新创建任务...")
                for segment_file in missing_segments:
                    print(f"为片段 {os.path.basename(segment_file)} 重试创建任务")
                    task_id = self.create_lip_sync_task(api_token, video_id, video_url, segment_file)
                    if task_id:
                        task_mapping[task_id] = {
                            "audio_file": segment_file,
                            "status": "pending",
                            "video_url": None,
                            "video_file": None
                        }
                        print(f"成功重新创建任务: {task_id} 用于音频 {os.path.basename(segment_file)}")
                        # 每个请求后等待几秒
                        time.sleep(3)
            
            if not task_mapping:
                raise ValueError("没有成功创建任何口型同步任务")
            
            print(f"成功创建 {len(task_mapping)} 个口型同步任务，共 {len(segment_files)} 个音频片段")
            
            # 确认所有片段是否都有对应的任务
            created_segments = set(info["audio_file"] for info in task_mapping.values())
            missing_segments = [s for s in segment_files if s not in created_segments]
            if missing_segments:
                print(f"警告: 仍有 {len(missing_segments)} 个音频片段未创建任务: {[os.path.basename(s) for s in missing_segments]}")
                print("将只处理成功创建任务的片段")

            # 成功创建所有任务后，先等待较长时间再开始检查状态
            initial_wait = 180  # 3分钟
            print(f"所有任务已创建，等待 {initial_wait} 秒后开始检查任务状态...（{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}）")
            print("-------------------------------------------------------------------")
            print(f"您可以去喝杯咖啡，{initial_wait//60}分钟后回来看进度...")
            print("-------------------------------------------------------------------")
            # 使用循环等待，每30秒打印一次提示，避免用户误以为程序卡住
            for i in range(initial_wait // 30):
                time.sleep(30)
                remaining = initial_wait - (i+1)*30
                if remaining > 0:
                    print(f"还需等待 {remaining} 秒后开始检查任务状态...（{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}）")
                
            print(f"等待结束，开始检查任务状态...（{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}）")
            
            # Monitor task status and download videos when completed
            all_completed = False
            # 默认60秒查询一次状态
            if poll_interval_seconds < 60:
                poll_interval_seconds = 60
                print(f"状态查询间隔调整为 {poll_interval_seconds} 秒")
                
            while not all_completed:
                all_completed = True
                pending_count = 0
                processed_count = 0
                
                # 打印当前时间
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(f"开始查询任务状态... [{current_time}]")
                
                for task_id, task_info in task_mapping.items():
                    if task_info["status"] not in ["succeed", "failed"]:
                        pending_count += 1
                        all_completed = False
                        
                        # Query task status
                        status, data = self.query_task_status(api_token, task_id)
                        print(f"任务 {task_id} 状态: {status}")
                        
                        if status == "succeed":
                            # Get video URL
                            videos = data.get("task_result", {}).get("videos", [])
                            if videos and videos[0].get("url"):
                                video_url = videos[0].get("url")
                                task_info["video_url"] = video_url
                                
                                # Download video
                                segment_index = os.path.basename(task_info["audio_file"]).split("_")[1].split(".")[0]
                                video_filename = f"segment_{segment_index}.mp4"
                                video_path = os.path.join(videos_dir, video_filename)
                                
                                if self.download_video(video_url, video_path):
                                    task_info["video_file"] = video_path
                                    task_info["status"] = "succeed"
                                    print(f"成功下载视频片段 {segment_index}: {video_path}")
                                    processed_count += 1
                                else:
                                    task_info["status"] = "failed"
                                    print(f"下载视频片段 {segment_index} 失败")
                            else:
                                task_info["status"] = "failed"
                                print(f"任务成功但未返回视频URL: {task_id}")
                        elif status == "failed":
                            task_info["status"] = "failed"
                            print(f"任务失败: {task_id}")
                            processed_count += 1
                        elif status:  # 添加对其他状态的详细打印
                            print(f"任务 {task_id} 正在处理中: {status}")
                            if 'task_status_msg' in data:
                                print(f"状态消息: {data.get('task_status_msg')}")
                            # 尝试获取进度信息（如果有）
                            if 'process_progress' in data:
                                print(f"进度: {data.get('process_progress')}%")
                
                if not all_completed:
                    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    print(f"[{current_time}] 还有 {pending_count} 个任务正在处理，{processed_count} 个任务已完成。")
                    print(f"将在 {poll_interval_seconds} 秒后重新检查...")
                    time.sleep(poll_interval_seconds)
            
            # Check if all tasks completed successfully
            failed_tasks = [task_id for task_id, info in task_mapping.items() if info["status"] == "failed"]
            if failed_tasks:
                print(f"警告: {len(failed_tasks)} 个任务失败: {', '.join(failed_tasks)}")
            
            # Get successful video files in correct order
            successful_videos = []
            for segment_file in segment_files:
                segment_index = os.path.basename(segment_file).split("_")[1].split(".")[0]
                for task_id, info in task_mapping.items():
                    if info["audio_file"] == segment_file and info["status"] == "succeed":
                        successful_videos.append(info["video_file"])
                        break
            
            if not successful_videos:
                raise ValueError("没有成功生成的视频片段可供合并")
            
            # 音频源路径保存下来供后续使用
            original_audio_path = local_audio_path
            
            # Merge videos with original audio
            output_video_path = os.path.join(output_dir, f"{output_filename}.mp4")
            if self.merge_videos_with_original_audio(successful_videos, original_audio_path, output_video_path, sync_adjust_ms):
                print(f"所有视频片段已成功合并并使用原始音频: {output_video_path}")
                # Clean up temp directory
                # shutil.rmtree(temp_dir)
                return (output_video_path,)
            else:
                raise ValueError("视频合并失败")
            
        except Exception as e:
            error_msg = f"处理失败: {str(e)}"
            print(error_msg)
            return (error_msg,)
    
    @classmethod
    def IS_CHANGED(cls, api_token, video_id="", video_url="", 
                 audio_type="url", audio_url="", audio_file="",
                 segment_duration=10, max_concurrent_tasks=5,
                 poll_interval_seconds=30,
                 output_filename="lip_sync_combined"):
        # Return current time to ensure node always executes
        return time.time() 