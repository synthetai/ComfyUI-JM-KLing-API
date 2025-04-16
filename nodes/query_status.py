import json
import requests
import time
from threading import Thread, Event


# 定义一个带有结果存储的线程类
class TaskStatusThread(Thread):
    def __init__(self, target, args):
        Thread.__init__(self, target=target, args=args)
        self.result = None
        
    def run(self):
        self.result = self._target(*self._args)


class KLingAIQueryStatus:
    """
    KLingAI Query Task Status Node
    查询文生视频或图生视频或多图生视频任务状态
    """

    def __init__(self):
        self.api_base = "https://api.klingai.com"
        self.text2video_endpoint = "/v1/videos/text2video/{}"
        self.image2video_endpoint = "/v1/videos/image2video/{}"
        self.multi_image2video_endpoint = "/v1/videos/multi-image2video/{}"
        self.lip_sync_endpoint = "/v1/videos/lip-sync/{}"
        self.stop_thread = Event()
        self.current_thread = None

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "api_token": ("STRING", {"default": "", "multiline": False}),
                "task_id": ("STRING", {"default": "", "multiline": False}),
            },
            "optional": {
                "external_task_id": ("STRING", {
                    "default": "",
                    "multiline": False,
                    "placeholder": "可选: 自定义任务ID"
                }),
                "task_type": (["auto", "text2video", "image2video", "multi-image2video", "lip-sync"], {
                    "default": "auto"
                }),
                "initial_delay_seconds": ("INT", {
                    "default": 10,
                    "min": 0,
                    "max": 60,
                    "step": 1,
                    "display": "slider"
                }),
                "poll_interval_seconds": ("INT", {
                    "default": 10,
                    "min": 5,
                    "max": 30,
                    "step": 1,
                    "display": "slider"
                }),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("video_url",)
    FUNCTION = "query_task_status"
    CATEGORY = "JM-KLingAI-API"

    def poll_status(self, api_token, task_id, external_task_id, task_type="auto", initial_delay_seconds=10, poll_interval_seconds=10):
        """
        轮询任务状态直到完成
        """
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_token}"
        }

        # 初始等待时间，给服务器处理任务的时间
        if initial_delay_seconds > 0:
            print(f"等待 {initial_delay_seconds} 秒后开始查询任务状态...")
            if self.stop_thread.wait(initial_delay_seconds):
                return "查询被中断"

        print("开始查询任务状态...")

        # 确定使用哪个查询ID
        query_id = task_id if task_id else external_task_id

        # 根据任务类型确定查询端点
        endpoints = []
        if task_type == "auto":
            # 根据任务ID长度初步判断可能是哪种类型
            if len(query_id) > 10:  # 可灵AI的任务ID通常很长
                endpoints = [
                    self.multi_image2video_endpoint,
                    self.image2video_endpoint, 
                    self.text2video_endpoint,
                    self.lip_sync_endpoint
                ]
            else:
                endpoints = [
                    self.text2video_endpoint,
                    self.image2video_endpoint,
                    self.multi_image2video_endpoint,
                    self.lip_sync_endpoint
                ]
        elif task_type == "text2video":
            endpoints = [self.text2video_endpoint]
        elif task_type == "image2video":
            endpoints = [self.image2video_endpoint]
        elif task_type == "multi-image2video":
            endpoints = [self.multi_image2video_endpoint]
        elif task_type == "lip-sync":
            endpoints = [self.lip_sync_endpoint]
            
        # 记录最后找到的有效端点
        valid_endpoint = None

        while not self.stop_thread.is_set():
            success = False
            
            # 如果上一次查询找到了有效端点，只使用该端点
            if valid_endpoint:
                current_endpoints = [valid_endpoint]
            else:
                current_endpoints = endpoints.copy()
                
            for endpoint in current_endpoints:
                try:
                    url = f"{self.api_base}{endpoint.format(query_id)}"
                    print(f"查询任务 {query_id} 的状态，使用端点: {endpoint}...")
                    
                    response = requests.get(url, headers=headers)
                    
                    # 首先检查响应状态码
                    if response.status_code == 404:
                        print(f"在 {endpoint} 未找到任务，尝试其他端点...")
                        continue
                    
                    # 解析响应数据
                    try:
                        response_data = response.json()
                    except Exception as e:
                        print(f"解析响应数据失败: {str(e)}，尝试其他端点...")
                        continue
                    
                    # 检查响应中的错误信息
                    if response.status_code != 200:
                        error_message = response_data.get('message', '未知错误')
                        print(f"查询状态错误: {error_message}")
                        
                        # 任务未找到，这可能是端点错误
                        if "not found" in error_message.lower():
                            print(f"在 {endpoint} 未找到任务，尝试其他端点...")
                            continue
                        # 其他API错误情况
                        else:
                            print(f"API返回错误: {error_message}")
                            continue

                    # 获取任务状态
                    data = response_data.get("data", {})
                    status = data.get("task_status")
                    
                    # 如果能获取到状态，说明端点正确
                    if status:
                        valid_endpoint = endpoint
                        success = True
                        print(f"当前任务状态: {status}")
                        
                        # 任务成功完成
                        if status == "succeed":
                            # 检查是否是lip-sync任务类型
                            if valid_endpoint == self.lip_sync_endpoint:
                                videos = data.get("task_result", {}).get("videos", [])
                                if videos and videos[0].get("url"):
                                    video_url = videos[0].get("url")
                                    video_duration = videos[0].get("duration", "未知")
                                    print(f"口型同步任务成功完成!")
                                    print(f"视频URL: {video_url}")
                                    print(f"视频时长: {video_duration}秒")
                                    
                                    # 尝试获取并显示原视频信息
                                    parent_video = data.get("task_info", {}).get("parent_video", {})
                                    if parent_video:
                                        parent_id = parent_video.get("id", "未知")
                                        parent_url = parent_video.get("url", "未知")
                                        parent_duration = parent_video.get("duration", "未知")
                                        print(f"原视频ID: {parent_id}")
                                        print(f"原视频URL: {parent_url}")
                                        print(f"原视频时长: {parent_duration}秒")
                                    
                                    return video_url
                                print("口型同步任务成功但未返回视频URL")
                                return "口型同步任务成功但未返回视频URL"
                            else:
                                # 处理其他类型的任务
                                videos = data.get("task_result", {}).get("videos", [])
                                if videos and videos[0].get("url"):
                                    return videos[0].get("url")
                                print("任务成功但未返回视频URL")
                                return "任务成功但未返回视频URL"
                        # 任务失败
                        elif status == "failed":
                            failed_msg = f"任务失败: {data.get('task_status_msg', '未知错误')}"
                            print(failed_msg)
                            return failed_msg
                        # 任务仍在处理中，中断当前端点循环，等待下次查询
                        break
                    else:
                        print(f"API返回数据中缺少任务状态")
                        
                except Exception as e:
                    print(f"查询端点 {endpoint} 出错: {str(e)}")
            
            # 如果尝试了所有端点但都未成功
            if not success and not valid_endpoint:
                if not current_endpoints:
                    error_msg = "没有可用的端点进行查询"
                    print(error_msg)
                    return error_msg
                print("所有端点查询失败，稍后将重试...")
            
            # 按照配置的时间间隔等待再次查询
            print(f"等待 {poll_interval_seconds} 秒后再次查询...")
            if self.stop_thread.wait(poll_interval_seconds):
                return "查询被中断"

        return "查询被停止"

    def query_task_status(self, api_token, task_id, external_task_id="", task_type="auto", initial_delay_seconds=10, poll_interval_seconds=10):
        """
        开始轮询任务状态
        """
        try:
            # 验证输入
            if not api_token:
                raise ValueError("API令牌不能为空")
            if not task_id and not external_task_id:
                raise ValueError("必须提供task_id或external_task_id")

            # 显示查询配置信息
            print(f"任务ID: {task_id or external_task_id}")
            print(f"任务类型: {task_type}")
            print(f"初始等待时间: {initial_delay_seconds}秒")
            print(f"查询间隔: {poll_interval_seconds}秒")

            # 停止任何正在进行的轮询线程
            if self.current_thread and self.current_thread.is_alive():
                self.stop_thread.set()
                self.current_thread.join()

            # 重置停止事件
            self.stop_thread.clear()

            # 创建并启动新的轮询线程
            self.current_thread = TaskStatusThread(
                target=self.poll_status,
                args=(api_token, task_id, external_task_id, task_type, initial_delay_seconds, poll_interval_seconds)
            )
            self.current_thread.start()

            # 等待结果
            self.current_thread.join()

            # 获取结果
            video_url = self.current_thread.result
            if video_url is None:
                video_url = "查询未返回结果"

            if video_url and "http" in video_url:
                print(f"任务成功完成。视频URL: {video_url}")
            else:
                print(f"查询结果: {video_url}")
                
            return (video_url,)

        except ValueError as ve:
            error_msg = f"参数验证错误: {str(ve)}"
            print(error_msg)
            return (error_msg,)
        except Exception as e:
            error_msg = f"查询任务状态错误: {str(e)}"
            print(error_msg)
            return (error_msg,)

    def __del__(self):
        """
        节点销毁时清理资源
        """
        if self.current_thread and self.current_thread.is_alive():
            self.stop_thread.set()
            self.current_thread.join() 