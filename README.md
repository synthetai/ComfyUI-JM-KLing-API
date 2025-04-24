# ComfyUI-JM-KlingAI-API
This is a custom node for ComfyUI that allows you to use the KLingAI API directly within the ComfyUI environment. It is developed based on the KLingAI API documentation. For more details, please refer to the official documentation.[KLingAI API Documentation](https://app.klingai.com/global/dev/document-api/quickStart/productIntroduction/overview)。

## Requirements
Before using this node, you need to have [a KLing AI API key](https://app.klingai.com/global/dev/document-api/quickStart/userManual).

## Installation
### Installing manually
1. Navigate to the `ComfyUI/custom_nodes` directory.
2. Clone this repository: `git clone https://github.com/synthetai/ComfyUI-JM-KLing-API.git`
3. Install the dependencies:
+ <font style="color:rgb(31, 35, 40);">Windows (ComfyUI portable): </font>`python -m pip install -r ComfyUI\custom_nodes\ComfyUI-JM-KLingAI-API\requirements.txt`
+ <font style="color:rgb(31, 35, 40);">Linux or MacOS: </font>`cd ComfyUI-JM-KLingAI-API && pip install -r requirements.txt`
4. <font style="color:rgb(31, 35, 40);">Start ComfyUI and enjoy using the KLing AI API node!</font>

## <font style="color:rgb(31, 35, 40);">Nodes</font>
### <font style="color:rgb(31, 35, 40);">KLingAI API Key</font>
<font style="color:rgb(31, 35, 40);">This node generates an API Token</font>

### <font style="color:rgb(31, 35, 40);">Text2Video</font>
<font style="color:rgb(31, 35, 40);">This node is used to generate a video given a text prompt.</font>

![](https://cdn.nlark.com/yuque/0/2025/png/226202/1743648058683-c964e841-e281-4c13-ab97-5af311be4ad0.png)

### <font style="color:rgb(31, 35, 40);">Image2Video</font>
<font style="color:rgb(31, 35, 40);">This node is used to generate a video given an image.</font>

![](https://cdn.nlark.com/yuque/0/2025/png/226202/1743646162371-59f6539c-64bd-4ff7-82d7-fb10640cc427.png)

### <font style="color:rgb(31, 35, 40);">KLingAI Lip Sync</font>
<font style="color:rgb(31, 35, 40);">This node is used to create a lip sync task that makes a video's mouth movements match with provided audio.</font>

### <font style="color:rgb(31, 35, 40);">KLingAI Lip Sync Async</font>
<font style="color:rgb(31, 35, 40);">This node processes longer audio files by automatically splitting them into segments and creates lip sync tasks asynchronously. It then monitors task progress, downloads the generated videos, and merges them into a single output video.</font>

<font style="color:rgb(31, 35, 40);">Features:</font>
- <font style="color:rgb(31, 35, 40);">Splits audio into 10-second segments (configurable)</font>
- <font style="color:rgb(31, 35, 40);">Supports both local audio files and audio URLs</font>
- <font style="color:rgb(31, 35, 40);">Maintains segment order during processing and final merging</font>
- <font style="color:rgb(31, 35, 40);">Asynchronously creates tasks for all segments</font>
- <font style="color:rgb(31, 35, 40);">Monitors task status with configurable poll interval</font>
- <font style="color:rgb(31, 35, 40);">Downloads and merges videos using FFmpeg</font>
- <font style="color:rgb(31, 35, 40);">Organizes files in a structured temporary directory</font>

<font style="color:rgb(31, 35, 40);">Note: This node requires the `pydub` package and FFmpeg to be installed on your system.</font>

### <font style="color:rgb(31, 35, 40);">KLingAI Image Generation</font>
<font style="color:rgb(31, 35, 40);">This node is used to generate images from text prompts using KLingAI's image generation API.</font>

<font style="color:rgb(31, 35, 40);">Features:</font>
- <font style="color:rgb(31, 35, 40);">Text-to-image generation with customizable parameters</font>
- <font style="color:rgb(31, 35, 40);">Support for reference images (both via direct upload and URL)</font>
- <font style="color:rgb(31, 35, 40);">Different reference modes: subject (clothing, pose, etc.) and face (appearance)</font>
- <font style="color:rgb(31, 35, 40);">Adjustable fidelity settings for reference images</font>
- <font style="color:rgb(31, 35, 40);">Multiple aspect ratios to choose from</font>
- <font style="color:rgb(31, 35, 40);">Ability to generate multiple images per request (up to 9)</font>
- <font style="color:rgb(31, 35, 40);">Support for both kling-v1 and kling-v1-5 models</font>
  
### <font style="color:rgb(31, 35, 40);">KLingAI Image Downloader</font>
<font style="color:rgb(31, 35, 40);">This node downloads images from a URL and saves them to a local directory.</font>

<font style="color:rgb(31, 35, 40);">Features:</font>
- <font style="color:rgb(31, 35, 40);">Downloads images from a given URL</font>
- <font style="color:rgb(31, 35, 40);">Saves images with customizable filename prefixes</font>
- <font style="color:rgb(31, 35, 40);">Supports PNG, JPG, JPEG, and WebP formats</font>
- <font style="color:rgb(31, 35, 40);">Automatically detects image format from URL</font>
- <font style="color:rgb(31, 35, 40);">Optional custom output directory</font>
- <font style="color:rgb(31, 35, 40);">Returns the saved image path, original URL, and loaded image for further processing</font>

### <font style="color:rgb(31, 35, 40);">KLingAI Video Downloader</font>
<font style="color:rgb(31, 35, 40);">This node downloads videos from a URL and saves them to a local directory.</font>

<font style="color:rgb(31, 35, 40);">Features:</font>
- <font style="color:rgb(31, 35, 40);">Downloads videos from a specified URL</font>
- <font style="color:rgb(31, 35, 40);">Saves videos with customizable filename prefixes</font>
- <font style="color:rgb(31, 35, 40);">Supports MP4 video format</font>
- <font style="color:rgb(31, 35, 40);">Optional custom output directory</font>
- <font style="color:rgb(31, 35, 40);">Returns the saved video path and original URL for further processing</font>



