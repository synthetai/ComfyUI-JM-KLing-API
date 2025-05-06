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
    查询文生视频、图生视频、多图生视频、口型同步或文生图任务状态
    """

    def __init__(self):
        self.api_base = "https://api.klingai.com"
        self.text2video_endpoint = "/v1/videos/text2video/{}"
        self.image2video_endpoint = "/v1/videos/image2video/{}"
        self.multi_image2video_endpoint = "/v1/videos/multi-image2video/{}"
        self.lip_sync_endpoint = "/v1/videos/lip-sync/{}"
        self.image_generation_endpoint = "/v1/images/generations/{}"
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
                "task_type": (["auto", "text2video", "image2video", "multi-image2video", "lip-sync", "image-generation"], {
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

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("url", "id")
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
        print(f"[DEBUG] 查询参数: task_id={task_id}, external_task_id={external_task_id}, task_type={task_type}")

        # 确定使用哪个查询ID
        query_id = task_id if task_id else external_task_id
        print(f"[DEBUG] 使用查询ID: {query_id}")

        # 根据任务类型确定查询端点
        endpoints = []
        if task_type == "auto":
            # 根据任务ID长度初步判断可能是哪种类型
            if len(query_id) > 10:  # 可灵AI的任务ID通常很长
                endpoints = [
                    self.text2video_endpoint,    # 将text2video放在第一位
                    self.image2video_endpoint, 
                    self.multi_image2video_endpoint,
                    self.lip_sync_endpoint,
                    self.image_generation_endpoint
                ]
            else:
                endpoints = [
                    self.text2video_endpoint,    # 将text2video放在第一位
                    self.image2video_endpoint,
                    self.multi_image2video_endpoint,
                    self.lip_sync_endpoint,
                    self.image_generation_endpoint
                ]
        elif task_type == "text2video":
            endpoints = [self.text2video_endpoint]
        elif task_type == "image2video":
            endpoints = [self.image2video_endpoint]
        elif task_type == "multi-image2video":
            endpoints = [self.multi_image2video_endpoint]
        elif task_type == "lip-sync":
            endpoints = [self.lip_sync_endpoint]
        elif task_type == "image-generation":
            endpoints = [self.image_generation_endpoint]
        
        print(f"[DEBUG] 将尝试以下端点: {endpoints}")
            
        # 记录最后找到的有效端点
        valid_endpoint = None

        while not self.stop_thread.is_set():
            success = False
            
            # 如果上一次查询找到了有效端点，只使用该端点
            if valid_endpoint:
                current_endpoints = [valid_endpoint]
                print(f"[DEBUG] 使用上次成功的端点: {valid_endpoint}")
            else:
                current_endpoints = endpoints.copy()
                print(f"[DEBUG] 尚未找到有效端点，将尝试所有可能端点")
                
            for endpoint in current_endpoints:
                try:
                    url = f"{self.api_base}{endpoint.format(query_id)}"
                    print(f"查询任务 {query_id} 的状态，使用端点: {endpoint}...")
                    print(f"[DEBUG] 完整请求URL: {url}")
                    print(f"[DEBUG] 请求头: {json.dumps(headers, indent=2)}")
                    
                    response = requests.get(url, headers=headers)
                    
                    # 首先检查响应状态码
                    print(f"[DEBUG] 响应状态码: {response.status_code}")
                    
                    if response.status_code == 404:
                        print(f"在 {endpoint} 未找到任务，尝试其他端点...")
                        continue
                    
                    # 解析响应数据
                    try:
                        response_data = response.json()
                        print(f"[DEBUG] 完整响应数据: {json.dumps(response_data, indent=2, ensure_ascii=False)}")
                    except Exception as e:
                        print(f"解析响应数据失败: {str(e)}，尝试其他端点...")
                        print(f"[DEBUG] 原始响应内容: {response.text}")
                        continue
                    
                    # 检查响应中的错误信息
                    if response.status_code != 200:
                        error_message = response_data.get('message', '未知错误')
                        error_code = response_data.get('code', 'unknown')
                        request_id = response_data.get('request_id', 'unknown')
                        print(f"查询状态错误: {error_message}")
                        print(f"[DEBUG] 错误详情: 错误码={error_code}, 请求ID={request_id}")
                        
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
                    status_msg = data.get("task_status_msg", "")
                    
                    # 如果能获取到状态，说明端点正确
                    if status:
                        # 如果状态消息是"task not found"，可能是端点不对
                        if status == "failed" and status_msg == "task not found":
                            print(f"端点 {endpoint} 返回 task not found，尝试其他端点...")
                            continue
                            
                        # 找到了有效端点
                        valid_endpoint = endpoint
                        success = True
                        print(f"找到有效端点: {endpoint}")
                        print(f"当前任务状态: {status}")
                        print(f"[DEBUG] 任务详情: task_id={data.get('task_id')}, created_at={data.get('created_at')}, updated_at={data.get('updated_at')}")
                        
                        # 如果有状态消息，显示它
                        if 'task_status_msg' in data:
                            print(f"[DEBUG] 状态消息: {data.get('task_status_msg')}")
                        
                        # 任务成功完成
                        if status == "succeed":
                            # 检查是否是lip-sync任务类型
                            if valid_endpoint == self.lip_sync_endpoint:
                                videos = data.get("task_result", {}).get("videos", [])
                                if videos and videos[0].get("url"):
                                    video_url = videos[0].get("url")
                                    video_id = videos[0].get("id", "")
                                    video_duration = videos[0].get("duration", "未知")
                                    print(f"口型同步任务成功完成!")
                                    print(f"视频ID: {video_id}")
                                    print(f"视频URL: {video_url}")
                                    print(f"视频时长: {video_duration}秒")
                                    
                                    # 打印任务结果完整信息
                                    print(f"[DEBUG] 完整任务结果: {json.dumps(data.get('task_result', {}), indent=2, ensure_ascii=False)}")
                                    
                                    # 尝试获取并显示原视频信息
                                    parent_video = data.get("task_info", {}).get("parent_video", {})
                                    if parent_video:
                                        parent_id = parent_video.get("id", "未知")
                                        parent_url = parent_video.get("url", "未知")
                                        parent_duration = parent_video.get("duration", "未知")
                                        print(f"原视频ID: {parent_id}")
                                        print(f"原视频URL: {parent_url}")
                                        print(f"原视频时长: {parent_duration}秒")
                                        
                                        # 打印任务信息完整信息
                                        print(f"[DEBUG] 完整任务信息: {json.dumps(data.get('task_info', {}), indent=2, ensure_ascii=False)}")
                                    
                                    return (video_url, video_id)
                                print("口型同步任务成功但未返回视频URL")
                                print(f"[DEBUG] 接口返回数据但缺少预期的视频URL: {json.dumps(videos, indent=2, ensure_ascii=False)}")
                                return ("口型同步任务成功但未返回视频URL", "")
                            # 检查是否是文生图任务类型
                            elif valid_endpoint == self.image_generation_endpoint:
                                images = data.get("task_result", {}).get("images", [])
                                if images and len(images) > 0:
                                    # 如果有多张图片，使用第一张图片的URL
                                    image_url = images[0].get("url", "")
                                    image_index = images[0].get("index", 0)
                                    
                                    print(f"文生图任务成功完成!")
                                    print(f"生成图片数量: {len(images)}")
                                    print(f"图片URL: {image_url}")
                                    
                                    # 打印所有图片的URL
                                    for i, img in enumerate(images):
                                        img_url = img.get("url", "")
                                        img_idx = img.get("index", i)
                                        print(f"图片 {img_idx}: {img_url}")
                                    
                                    # 打印任务结果完整信息
                                    print(f"[DEBUG] 完整任务结果: {json.dumps(data.get('task_result', {}), indent=2, ensure_ascii=False)}")
                                    
                                    return (image_url, str(image_index))
                                print("文生图任务成功但未返回图片URL")
                                print(f"[DEBUG] 接口返回数据但缺少预期的图片URL: {json.dumps(images, indent=2, ensure_ascii=False)}")
                                return ("文生图任务成功但未返回图片URL", "")
                            else:
                                # 处理其他类型的任务
                                videos = data.get("task_result", {}).get("videos", [])
                                if videos and videos[0].get("url"):
                                    video_url = videos[0].get("url")
                                    video_id = videos[0].get("id", "")
                                    video_duration = videos[0].get("duration", "未知")
                                    print(f"任务成功完成!")
                                    print(f"视频ID: {video_id}")
                                    print(f"视频URL: {video_url}")
                                    print(f"视频时长: {video_duration}秒")
                                    
                                    # 打印任务结果完整信息
                                    print(f"[DEBUG] 完整任务结果: {json.dumps(data.get('task_result', {}), indent=2, ensure_ascii=False)}")
                                    
                                    return (video_url, video_id)
                                print("任务成功但未返回视频URL")
                                print(f"[DEBUG] 接口返回数据但缺少预期的视频URL: {json.dumps(videos, indent=2, ensure_ascii=False)}")
                                return ("任务成功但未返回视频URL", "")
                        # 任务失败
                        elif status == "failed":
                            failed_msg = f"任务失败: {data.get('task_status_msg', '未知错误')}"
                            print(failed_msg)
                            print(f"[DEBUG] 失败详情: {json.dumps(data, indent=2, ensure_ascii=False)}")
                            return (failed_msg, "")
                        # 任务仍在处理中，打印详细信息
                        else:
                            print(f"[DEBUG] 任务处理中，当前进度信息: {json.dumps(data, indent=2, ensure_ascii=False)}")
                            # 中断当前端点循环，等待下次查询
                            break
                    else:
                        print(f"API返回数据中缺少任务状态")
                        print(f"[DEBUG] 响应中缺少任务状态，完整响应: {json.dumps(response_data, indent=2, ensure_ascii=False)}")
                        
                except Exception as e:
                    print(f"查询端点 {endpoint} 出错: {str(e)}")
                    print(f"[DEBUG] 异常详细信息: {type(e).__name__}: {str(e)}")
                    import traceback
                    print(f"[DEBUG] 异常堆栈: {traceback.format_exc()}")
            
            # 如果尝试了所有端点但都未成功
            if not success and not valid_endpoint:
                if not current_endpoints:
                    error_msg = "没有可用的端点进行查询"
                    print(error_msg)
                    return (error_msg, "")
                print("所有端点查询失败，稍后将重试...")
            
            # 按照配置的时间间隔等待再次查询
            print(f"等待 {poll_interval_seconds} 秒后再次查询...")
            if self.stop_thread.wait(poll_interval_seconds):
                return ("查询被中断", "")

        return ("查询被停止", "")

    def query_task_status(self, api_token, task_id, external_task_id="", task_type="auto", initial_delay_seconds=10, poll_interval_seconds=10):
        """
        开始轮询任务状态
        """
        try:
            print("[DEBUG] ======== 开始查询任务状态 ========")
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
            
            # 显示更多调试信息
            print(f"[DEBUG] API令牌前10个字符: {api_token[:10]}..." if api_token else "[DEBUG] API令牌为空")
            print(f"[DEBUG] 完整配置: task_id={task_id}, external_task_id={external_task_id}, task_type={task_type}, initial_delay={initial_delay_seconds}, poll_interval={poll_interval_seconds}")

            # 停止任何正在进行的轮询线程
            if self.current_thread and self.current_thread.is_alive():
                print("[DEBUG] 发现正在运行的查询线程，正在停止...")
                self.stop_thread.set()
                self.current_thread.join()
                print("[DEBUG] 之前的查询线程已停止")

            # 重置停止事件
            self.stop_thread.clear()
            print("[DEBUG] 停止事件已重置")

            # 创建并启动新的轮询线程
            print("[DEBUG] 创建新的轮询线程...")
            self.current_thread = TaskStatusThread(
                target=self.poll_status,
                args=(api_token, task_id, external_task_id, task_type, initial_delay_seconds, poll_interval_seconds)
            )
            self.current_thread.start()
            print("[DEBUG] 轮询线程已启动")

            # 等待结果
            print("[DEBUG] 等待轮询线程完成...")
            self.current_thread.join()
            print("[DEBUG] 轮询线程已完成")

            # 获取结果
            result = self.current_thread.result
            print(f"[DEBUG] 线程返回结果类型: {type(result)}")
            
            if result is None:
                print("[DEBUG] 警告: 线程返回了None结果")
                video_url = "查询未返回结果"
                video_id = ""
            else:
                # 解包结果，它应该是一个包含两个元素的元组
                if isinstance(result, tuple) and len(result) == 2:
                    print(f"[DEBUG] 正确解析到元组结果")
                    video_url, video_id = result
                else:
                    # 兼容处理可能的旧格式返回值
                    print(f"[DEBUG] 警告: 结果不是预期的元组格式，而是 {type(result)}，进行兼容处理")
                    video_url = str(result)
                    video_id = ""

            if video_url and "http" in video_url:
                print(f"任务成功完成。视频URL: {video_url}")
                if video_id:
                    print(f"视频ID: {video_id}")
                print("[DEBUG] 返回成功的视频URL和ID")
            else:
                print(f"查询结果: {video_url}")
                print("[DEBUG] 未返回有效的视频URL")
                
            print("[DEBUG] ======== 查询任务完成 ========")
            return (video_url, video_id)

        except ValueError as ve:
            error_msg = f"参数验证错误: {str(ve)}"
            print(error_msg)
            print(f"[DEBUG] 参数验证异常: {str(ve)}")
            return (error_msg, "")
        except Exception as e:
            error_msg = f"查询任务状态错误: {str(e)}"
            print(error_msg)
            print(f"[DEBUG] 异常详细信息: {type(e).__name__}: {str(e)}")
            import traceback
            print(f"[DEBUG] 异常堆栈: {traceback.format_exc()}")
            return (error_msg, "")

    def __del__(self):
        """
        节点销毁时清理资源
        """
        if self.current_thread and self.current_thread.is_alive():
            self.stop_thread.set()
            self.current_thread.join() 