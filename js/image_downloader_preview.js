import { app } from "../../scripts/app.js";

// 添加调试日志以跟踪加载
console.log("[JM-KLingAI] 开始加载KLingAI Image Downloader Preview扩展");

// 创建全局跟踪函数便于调试
function logDebug(message) {
    console.log(`[JM-KLingAI-Debug] ${message}`);
}

// 增强版调试日志，显示更多信息
function logDetailedDebug(message, object) {
    console.log(`[JM-KLingAI-DetailedDebug] ${message}`, object || "");
}

// 注册扩展
app.registerExtension({
    name: "JM.KLingAI.ImageDownloaderPreview",
    
    async setup() {
        logDebug("扩展设置完成");
        logDetailedDebug("ComfyUI应用对象:", app);
    },
    
    async beforeRegisterNodeDef(nodeType, nodeData) {
        // 打印节点数据以便调试
        logDetailedDebug(`检查节点类型: ${nodeData.name || nodeData.title || nodeData.comfyClass}`, nodeData);
        
        // 更全面的节点匹配逻辑
        if (!nodeData) {
            return;
        }
        
        // 记录节点的原始类名和名称
        logDebug(`节点类: ${nodeData.comfyClass}, 名称: ${nodeData.name}, 类别: ${nodeData.category}`);
        
        // 匹配我们的节点 - 使用多种匹配方式以确保能找到
        // KLingAIImageDownloader 是节点的Python类名
        if (nodeData.comfyClass !== "KLingAIImageDownloader") {
            // 尝试其他匹配方式
            if (!(nodeData.name && nodeData.name.includes("KLingAI Image Downloader"))) {
                return;
            }
        }
        
        logDebug(`找到KLingAIImageDownloader节点，准备添加预览功能`);
        logDetailedDebug("节点类型对象:", nodeType);
        
        // 使用computeSize确保节点尺寸
        const origComputeSize = nodeType.prototype.computeSize;
        nodeType.prototype.computeSize = function() {
            logDebug("computeSize被调用");
            if (origComputeSize) {
                const size = origComputeSize.apply(this, arguments);
                logDebug(`原始computeSize返回: [${size[0]}, ${size[1]}]`);
                const newSize = [Math.max(size[0], 350), Math.max(size[1], 450)];
                logDebug(`调整后大小: [${newSize[0]}, ${newSize[1]}]`);
                return newSize;
            }
            logDebug("使用默认大小: [350, 450]");
            return [350, 450];
        };
        
        // 保存原始的onNodeCreated方法
        const origOnNodeCreated = nodeType.prototype.onNodeCreated;
        
        // 重写onNodeCreated方法
        nodeType.prototype.onNodeCreated = function() {
            logDebug(`节点创建开始 - ${this.id}(${this.type})`);
            // 调用原始方法
            if (origOnNodeCreated) {
                logDebug("调用原始onNodeCreated方法");
                origOnNodeCreated.apply(this, arguments);
            }
            
            logDebug("KLingAIImageDownloader节点创建");
            
            // 确保节点尺寸足够大
            logDetailedDebug("节点创建前大小:", this.size);
            if (!this.size) {
                this.size = [350, 450];
                logDebug("设置初始大小: [350, 450]");
            } else {
                this.size[0] = Math.max(this.size[0], 350);
                this.size[1] = Math.max(this.size[1], 450);
                logDebug(`调整大小为: [${this.size[0]}, ${this.size[1]}]`);
            }
            
            // 创建预览图像对象
            this._preview_image = new Image();
            this._preview_path = null;
            logDebug("创建预览图像对象");
            
            // 使节点可序列化
            this.serialize_widgets = true;
            logDebug("设置节点可序列化");
            
            // 请求绘制更新
            this.setDirtyCanvas(true, true);
            logDebug("请求画布更新");
            
            // 输出节点详细信息
            logDetailedDebug("节点创建完成，详细信息:", {
                id: this.id,
                type: this.type,
                size: this.size,
                inputs: this.inputs,
                outputs: this.outputs,
                widgets: this.widgets,
                properties: this.properties
            });
        };
        
        // 保存原始的onDrawForeground方法
        const origOnDrawForeground = nodeType.prototype.onDrawForeground;
        
        // 重写onDrawForeground方法
        nodeType.prototype.onDrawForeground = function(ctx) {
            logDebug(`onDrawForeground被调用 - ${this.id}`);
            
            // 调用原始方法
            if (origOnDrawForeground) {
                logDebug("调用原始onDrawForeground方法");
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
            
            logDebug(`预览区域: x=${previewX}, y=${previewY}, width=${previewWidth}, height=${previewHeight}`);
            
            // 绘制预览区域背景
            ctx.fillStyle = "#1a1a1a";
            ctx.fillRect(previewX, previewY, previewWidth, previewHeight);
            ctx.strokeStyle = "#555555";
            ctx.lineWidth = 1;
            ctx.strokeRect(previewX, previewY, previewWidth, previewHeight);
            logDebug("绘制预览区域背景");
            
            // 如果有预览图像且已加载完成
            if (this._preview_image && this._preview_image.complete && this._preview_image.width > 0) {
                logDebug(`有预览图像: ${this._preview_image.width}x${this._preview_image.height}`);
                try {
                    // 计算图像显示大小，保持比例
                    const img = this._preview_image;
                    const imgRatio = img.width / img.height;
                    let drawWidth, drawHeight;
                    
                    if (imgRatio > previewWidth / previewHeight) {
                        // 图像较宽，以宽度为限
                        drawWidth = previewWidth - 10;
                        drawHeight = drawWidth / imgRatio;
                        logDebug(`图像较宽，调整为 ${drawWidth}x${drawHeight}`);
                    } else {
                        // 图像较高，以高度为限
                        drawHeight = previewHeight - 10;
                        drawWidth = drawHeight * imgRatio;
                        logDebug(`图像较高，调整为 ${drawWidth}x${drawHeight}`);
                    }
                    
                    // 计算居中位置
                    const drawX = previewX + (previewWidth - drawWidth) / 2;
                    const drawY = previewY + (previewHeight - drawHeight) / 2;
                    logDebug(`绘制位置: x=${drawX}, y=${drawY}`);
                    
                    // 绘制预览图像
                    ctx.drawImage(img, drawX, drawY, drawWidth, drawHeight);
                    logDebug("绘制预览图像完成");
                    
                    // 显示图像尺寸
                    ctx.fillStyle = "#ffffff";
                    ctx.font = "12px Arial";
                    ctx.textAlign = "left";
                    ctx.fillText(`${img.naturalWidth}x${img.naturalHeight}`, 
                               previewX + 5, previewY + previewHeight - 5);
                    logDebug("绘制图像尺寸信息");
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
                logDebug("无预览图像或图像未加载完成");
                if (this._preview_image) {
                    logDetailedDebug("预览图像状态:", {
                        complete: this._preview_image.complete,
                        width: this._preview_image.width,
                        src: this._preview_image.src
                    });
                }
                
                // 没有图像时显示提示
                ctx.fillStyle = "#aaaaaa";
                ctx.font = "14px Arial";
                ctx.textAlign = "center";
                ctx.fillText("图片下载后将在此处显示", 
                           previewX + previewWidth/2, previewY + previewHeight/2);
                ctx.textAlign = "left";
                logDebug("绘制提示文本");
            }
        };
        
        // 保存原始的onExecuted方法
        const origOnExecuted = nodeType.prototype.onExecuted;
        
        // 重写onExecuted方法
        nodeType.prototype.onExecuted = function(message) {
            logDebug(`节点执行完毕 - ${this.id}`);
            logDetailedDebug("执行消息:", message);
            
            // 调用原始方法
            if (origOnExecuted) {
                logDebug("调用原始onExecuted方法");
                origOnExecuted.apply(this, arguments);
            }
            
            if (!message) {
                logDebug("没有执行消息");
                return;
            }
            
            logDebug("检查输出消息");
            
            if (!message.outputs) {
                logDebug("消息中没有outputs字段");
                return;
            }
            
            // 输出消息
            logDetailedDebug("输出消息:", message.outputs);
            
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
            logDebug(`设置新的预览路径: ${this._preview_path}`);
            
            // 创建正确的预览URL
            const previewUrl = `/view?filename=${encodeURIComponent(imagePath)}&ts=${Date.now()}`;
            logDebug(`预览URL: ${previewUrl}`);
            
            // 设置图像加载事件
            this._preview_image.onload = () => {
                logDebug(`图像加载成功: ${this._preview_image.width}x${this._preview_image.height}`);
                this.setDirtyCanvas(true, true);
            };
            
            this._preview_image.onerror = (err) => {
                logDebug(`图像加载失败`);
                logDetailedDebug("加载错误:", err);
                // 尝试使用备选URL加载
                const alternativeUrl = `/output/${encodeURIComponent(imagePath)}?ts=${Date.now()}`;
                logDebug(`尝试备选URL: ${alternativeUrl}`);
                this._preview_image.src = alternativeUrl;
            };
            
            // 加载图像
            this._preview_image.src = previewUrl;
            logDebug(`开始加载图像: ${this._preview_image.src}`);
            
            // 强制请求重绘
            this.setDirtyCanvas(true, true);
            logDebug("请求画布更新");
        };
    }
});

logDebug("KLingAI Image Downloader Preview扩展加载完成"); 