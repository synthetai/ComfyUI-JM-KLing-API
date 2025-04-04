from .nodes.api_key import KLingAIAPIKey
from .nodes.text2video import KLingAIText2Video
from .nodes.query_status import KLingAIQueryStatus
from .nodes.video_downloader import KLingAIVideoDownloader
from .nodes.image2video import KLingAIImage2Video

NODE_CLASS_MAPPINGS = {
    "JM-KLingAI-API/api-key": KLingAIAPIKey,
    "JM-KLingAI-API/text2video": KLingAIText2Video,
    "JM-KLingAI-API/image2video": KLingAIImage2Video,
    "JM-KLingAI-API/query-status": KLingAIQueryStatus,
    "JM-KLingAI-API/video-downloader": KLingAIVideoDownloader
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "JM-KLingAI-API/api-key": "KLingAI API Key",
    "JM-KLingAI-API/text2video": "KLingAI Text to Video",
    "JM-KLingAI-API/image2video": "KLingAI Image to Video",
    "JM-KLingAI-API/query-status": "KLingAI Query Status",
    "JM-KLingAI-API/video-downloader": "KLingAI Video Downloader"
}
