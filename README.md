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

  



