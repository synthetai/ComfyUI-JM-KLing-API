from .nodes.api_key import KLingAIAPIKey
from .nodes.text2video import KLingAIText2Video
from .nodes.query_status import KLingAIQueryStatus
from .nodes.video_downloader import KLingAIVideoDownloader
from .nodes.image2video import KLingAIImage2Video
from .nodes.multi_image2video import KLingAIMultiImage2Video
from .nodes.lip_sync import KLingAILipSync
from .nodes.lip_sync_async import KLingAILipSyncAsync
from .nodes.image_generation import KLingAIImageGeneration
from .nodes.image_downloader import KLingAIImageDownloader
from .nodes.hybrid_video import KLingAIHybridVideo
import os
import folder_paths

# 设置WEB_DIRECTORY指向js子目录
# js目录应位于插件根目录下
current_dir = os.path.dirname(os.path.realpath(__file__))
WEB_DIRECTORY = os.path.join(current_dir, "js")
print(f"JM-KLingAI-API: WEB_DIRECTORY设置为: {WEB_DIRECTORY}")

# 检查js目录是否存在
if os.path.exists(WEB_DIRECTORY):
    js_files = os.listdir(WEB_DIRECTORY)
    print(f"JM-KLingAI-API: js目录存在，包含文件: {js_files}")
else:
    print(f"JM-KLingAI-API: 警告! js目录不存在: {WEB_DIRECTORY}")
    # 尝试创建
    try:
        os.makedirs(WEB_DIRECTORY, exist_ok=True)
        print(f"JM-KLingAI-API: 已创建js目录: {WEB_DIRECTORY}")
    except Exception as e:
        print(f"JM-KLingAI-API: 创建js目录失败: {str(e)}")

NODE_CLASS_MAPPINGS = {
    "JM-KLingAI-API/api-key": KLingAIAPIKey,
    "JM-KLingAI-API/text2video": KLingAIText2Video,
    "JM-KLingAI-API/image2video": KLingAIImage2Video,
    "JM-KLingAI-API/multi-image2video": KLingAIMultiImage2Video,
    "JM-KLingAI-API/query-status": KLingAIQueryStatus,
    "JM-KLingAI-API/video-downloader": KLingAIVideoDownloader,
    "JM-KLingAI-API/lip-sync": KLingAILipSync,
    "JM-KLingAI-API/lip-sync-async": KLingAILipSyncAsync,
    "JM-KLingAI-API/image-generation": KLingAIImageGeneration,
    "JM-KLingAI-API/image-downloader": KLingAIImageDownloader,
    "JM-KLingAI-API/hybrid-video": KLingAIHybridVideo
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "JM-KLingAI-API/api-key": "KLingAI API Key",
    "JM-KLingAI-API/text2video": "KLingAI Text to Video",
    "JM-KLingAI-API/image2video": "KLingAI Image to Video",
    "JM-KLingAI-API/multi-image2video": "KLingAI Multi-Image to Video",
    "JM-KLingAI-API/query-status": "KLingAI Query Status",
    "JM-KLingAI-API/video-downloader": "KLingAI Video Downloader",
    "JM-KLingAI-API/lip-sync": "KLingAI Lip Sync",
    "JM-KLingAI-API/lip-sync-async": "KLingAI Lip Sync Async",
    "JM-KLingAI-API/image-generation": "KLingAI Image Generation",
    "JM-KLingAI-API/image-downloader": "KLingAI Image Downloader",
    "JM-KLingAI-API/hybrid-video": "KLingAI 混合视频生成"
}

# 确保正确导出WEB_DIRECTORY
__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]

print(f"JM-KLingAI-API: 插件初始化完成，导出变量: {__all__}")
