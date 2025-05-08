import { app } from "../../scripts/app.js";

app.registerExtension({
    name: "JM-KLingAI.ImageDownloaderPreview",
    
    nodeCreated(node, app) {
        // 检查节点类型是否为KLingAIImageDownloader
        if (node.comfyClass === "KLingAIImageDownloader") {
            // 获取节点原始的大小
            const origSize = node.size || [200, 100];
            // 设置节点的大小，增加足够的空间来显示预览
            node.size = [Math.max(origSize[0], 300), Math.max(origSize[1], 400)];
            
            // 保存原始的onDrawBackground方法
            const origDrawBackground = node.onDrawBackground;
            
            // 重写onDrawBackground，增加图片预览功能
            node.onDrawBackground = function(ctx) {
                // 调用原始的绘制方法
                if (origDrawBackground) {
                    origDrawBackground.call(this, ctx);
                }
                
                // 检查是否有图像需要预览
                if (this.imgs && this.imgs.length > 0) {
                    const img = this.imgs[0];
                    if (!img || !img.width) return;
                    
                    // 计算预览区域
                    const headerHeight = 30;  // 标题栏高度
                    const widgetsHeight = this.widgets.length * 28;  // 控件区域高度
                    const margin = 10;
                    
                    // 计算可用于预览的区域
                    const previewAreaX = margin;
                    const previewAreaY = headerHeight + widgetsHeight + margin;
                    const previewAreaWidth = this.size[0] - margin * 2;
                    const previewAreaHeight = this.size[1] - previewAreaY - margin;
                    
                    // 计算图像显示大小，保持比例
                    const imgRatio = img.width / img.height;
                    let drawWidth, drawHeight;
                    
                    if (imgRatio > previewAreaWidth / previewAreaHeight) {
                        // 图像较宽，以宽度为限
                        drawWidth = previewAreaWidth;
                        drawHeight = drawWidth / imgRatio;
                    } else {
                        // 图像较高，以高度为限
                        drawHeight = previewAreaHeight;
                        drawWidth = drawHeight * imgRatio;
                    }
                    
                    // 计算居中位置
                    const drawX = previewAreaX + (previewAreaWidth - drawWidth) / 2;
                    const drawY = previewAreaY + (previewAreaHeight - drawHeight) / 2;
                    
                    // 绘制预览图像
                    ctx.drawImage(img, drawX, drawY, drawWidth, drawHeight);
                    
                    // 绘制图像尺寸信息
                    ctx.fillStyle = "#CCC";
                    ctx.font = "12px Arial";
                    ctx.fillText(`${img.naturalWidth}x${img.naturalHeight}`, 
                                 drawX + drawWidth - 70, drawY + drawHeight - 10);
                } else {
                    // 没有图像时显示提示文本
                    ctx.fillStyle = "#999";
                    ctx.font = "14px Arial";
                    ctx.textAlign = "center";
                    ctx.fillText("下载图片后将在此处显示预览", 
                                this.size[0] / 2, 
                                this.size[1] / 2);
                    ctx.textAlign = "left";
                }
            };
            
            // 重写onExecuted方法，在节点执行后更新图像
            const origOnExecuted = node.onExecuted;
            node.onExecuted = function(message) {
                if (origOnExecuted) {
                    origOnExecuted.call(this, message);
                }
                
                // 检查是否有图像输出
                if (message && message.outputs && message.outputs.image) {
                    // 触发预览图像的更新
                    app.canvas.setDirty(true);
                }
            };
        }
    }
}); 