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

# 注册节点映射
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

# 导出节点映射
__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]

print(f"JM-KLingAI-API: 插件初始化完成，导出变量: {__all__}")
