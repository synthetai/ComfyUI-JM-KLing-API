import { app } from "../../scripts/app.js";

// 添加调试日志以跟踪加载
console.log("[JM-KLingAI] 开始加载KLingAI Image Downloader Preview扩展");

// 创建全局跟踪函数便于调试
function logDebug(message) {
    console.log(`[JM-KLingAI-Debug] ${message}`);
}

// 注册扩展
app.registerExtension({
    name: "JM.KLingAI.ImageDownloaderPreview",
    
    async setup() {
        logDebug("扩展设置完成");
    },
    
    async beforeRegisterNodeDef(nodeType, nodeData) {
        // 打印节点数据以便调试
        logDebug(`检查节点: ${nodeData.name}, 类: ${nodeData.comfyClass}, 类别: ${nodeData.category}`);
        
        // 匹配我们的节点 - 使用多种匹配方式以确保能找到
        if (nodeData.category !== "JM-KLingAI-API" || 
            (nodeData.comfyClass !== "KLingAIImageDownloader" && 
             !nodeData.name.includes("KLingAI Image Downloader"))) {
            return;
        }
        
        logDebug("找到KLingAIImageDownloader节点，准备添加预览功能");
        
        // 使用computeSize确保节点尺寸
        const origComputeSize = nodeType.prototype.computeSize;
        nodeType.prototype.computeSize = function() {
            if (origComputeSize) {
                const size = origComputeSize.apply(this, arguments);
                return [Math.max(size[0], 350), Math.max(size[1], 450)];
            }
            return [350, 450];
        };
        
        // 保存原始的onNodeCreated方法
        const origOnNodeCreated = nodeType.prototype.onNodeCreated;
        
        // 重写onNodeCreated方法
        nodeType.prototype.onNodeCreated = function() {
            // 调用原始方法
            if (origOnNodeCreated) {
                origOnNodeCreated.apply(this, arguments);
            }
            
            logDebug("KLingAIImageDownloader节点创建");
            
            // 确保节点尺寸足够大
            if (!this.size) {
                this.size = [350, 450];
            } else {
                this.size[0] = Math.max(this.size[0], 350);
                this.size[1] = Math.max(this.size[1], 450);
            }
            
            // 创建预览图像对象
            this._preview_image = new Image();
            this._preview_path = null;
            
            // 使节点可序列化
            this.serialize_widgets = true;
            
            // 请求绘制更新
            this.setDirtyCanvas(true, true);
        };
        
        // 保存原始的onDrawForeground方法
        const origOnDrawForeground = nodeType.prototype.onDrawForeground;
        
        // 重写onDrawForeground方法
        nodeType.prototype.onDrawForeground = function(ctx) {
            // 调用原始方法
            if (origOnDrawForeground) {
                origOnDrawForeground.apply(this, arguments);
            }
            
            // 绘制预览区域
            const headerHeight = 30;         // 节点顶部标题高度
            const widgetsHeight = 120;       // 所有输入控件的高度
            const margin = 10;
            
            // 计算预览区域
            const previewX = margin;
            const previewY = headerHeight + widgetsHeight;
            const previewWidth = this.size[0] - margin * 2;
            const previewHeight = this.size[1] - previewY - margin;
            
            // 绘制预览区域背景
            ctx.fillStyle = "#1a1a1a";
            ctx.fillRect(previewX, previewY, previewWidth, previewHeight);
            ctx.strokeStyle = "#555555";
            ctx.lineWidth = 1;
            ctx.strokeRect(previewX, previewY, previewWidth, previewHeight);
            
            // 如果有预览图像且已加载完成
            if (this._preview_image && this._preview_image.complete && this._preview_image.width > 0) {
                try {
                    // 计算图像显示大小，保持比例
                    const img = this._preview_image;
                    const imgRatio = img.width / img.height;
                    let drawWidth, drawHeight;
                    
                    if (imgRatio > previewWidth / previewHeight) {
                        // 图像较宽，以宽度为限
                        drawWidth = previewWidth - 10;
                        drawHeight = drawWidth / imgRatio;
                    } else {
                        // 图像较高，以高度为限
                        drawHeight = previewHeight - 10;
                        drawWidth = drawHeight * imgRatio;
                    }
                    
                    // 计算居中位置
                    const drawX = previewX + (previewWidth - drawWidth) / 2;
                    const drawY = previewY + (previewHeight - drawHeight) / 2;
                    
                    // 绘制预览图像
                    ctx.drawImage(img, drawX, drawY, drawWidth, drawHeight);
                    
                    // 显示图像尺寸
                    ctx.fillStyle = "#ffffff";
                    ctx.font = "12px Arial";
                    ctx.textAlign = "left";
                    ctx.fillText(`${img.naturalWidth}x${img.naturalHeight}`, 
                               previewX + 5, previewY + previewHeight - 5);
                } catch (error) {
                    logDebug(`绘制图像错误: ${error.message}`);
                    // 显示错误信息
                    ctx.fillStyle = "#ff5555";
                    ctx.font = "12px Arial";
                    ctx.textAlign = "center";
                    ctx.fillText("图像加载或绘制出错", 
                               previewX + previewWidth/2, previewY + previewHeight/2);
                    ctx.textAlign = "left";
                }
            } else {
                // 没有图像时显示提示
                ctx.fillStyle = "#aaaaaa";
                ctx.font = "14px Arial";
                ctx.textAlign = "center";
                ctx.fillText("图片下载后将在此处显示", 
                           previewX + previewWidth/2, previewY + previewHeight/2);
                ctx.textAlign = "left";
            }
        };
        
        // 保存原始的onExecuted方法
        const origOnExecuted = nodeType.prototype.onExecuted;
        
        // 重写onExecuted方法
        nodeType.prototype.onExecuted = function(message) {
            // 调用原始方法
            if (origOnExecuted) {
                origOnExecuted.apply(this, arguments);
            }
            
            logDebug("节点执行完毕，检查输出");
            
            if (!message || !message.outputs) {
                logDebug("没有输出消息");
                return;
            }
            
            // 输出消息
            logDebug(`输出消息: ${JSON.stringify(message.outputs)}`);
            
            // 检查是否有图像路径输出
            const imagePath = message.outputs.image_path;
            if (!imagePath || typeof imagePath !== "string") {
                logDebug("无效的图像路径");
                return;
            }
            
            logDebug(`获取到图像路径: ${imagePath}`);
            
            // 如果路径无效或与上次相同，则不重新加载
            if (imagePath.startsWith("错误:") || imagePath === this._preview_path) {
                logDebug("图像路径无效或与上次相同");
                return;
            }
            
            this._preview_path = imagePath;
            
            // 创建正确的预览URL
            const previewUrl = `/view?filename=${encodeURIComponent(imagePath)}&ts=${Date.now()}`;
            logDebug(`预览URL: ${previewUrl}`);
            
            // 设置图像加载事件
            this._preview_image.onload = () => {
                logDebug(`图像加载成功: ${this._preview_image.width}x${this._preview_image.height}`);
                this.setDirtyCanvas(true, true);
            };
            
            this._preview_image.onerror = (err) => {
                logDebug(`图像加载失败: ${err}`);
            };
            
            // 加载图像
            this._preview_image.src = previewUrl;
            logDebug(`开始加载图像: ${this._preview_image.src}`);
        };
    }
});

logDebug("KLingAI Image Downloader Preview扩展加载完成"); 