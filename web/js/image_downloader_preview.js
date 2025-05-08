import { app } from "../../scripts/app.js";

app.registerExtension({
    name: "JM-KLingAI.ImageDownloaderPreview",
    
    nodeCreated(node, app) {
        // 检查节点类型是否为KLingAIImageDownloader
        if (node.comfyClass === "KLingAIImageDownloader") {
            // 获取节点原始的大小
            const origSize = node.size || [200, 100];
            // 设置节点的大小，增加足够的空间来显示预览
            node.size = [Math.max(origSize[0], 320), Math.max(origSize[1], 450)];
            
            // 创建一个图像对象用于预览
            node._previewImage = null;
            
            // 保存原始的onDrawBackground方法
            const origDrawBackground = node.onDrawBackground;
            
            // 重写onDrawBackground，增加图片预览功能
            node.onDrawBackground = function(ctx) {
                // 调用原始的绘制方法
                if (origDrawBackground) {
                    origDrawBackground.call(this, ctx);
                }
                
                // 计算预览区域
                const headerHeight = 30;  // 标题栏高度
                const widgetsHeight = this.widgets.length * 28;  // 控件区域高度
                const margin = 10;
                
                // 计算可用于预览的区域
                const previewAreaX = margin;
                const previewAreaY = headerHeight + widgetsHeight + margin;
                const previewAreaWidth = this.size[0] - margin * 2;
                const previewAreaHeight = this.size[1] - previewAreaY - margin;
                
                // 绘制预览区域的边框
                ctx.fillStyle = "#2a2a2a";
                ctx.fillRect(previewAreaX, previewAreaY, previewAreaWidth, previewAreaHeight);
                
                // 检查是否有图像需要预览
                if (this._previewImage && this._previewImage.width) {
                    const img = this._previewImage;
                    
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
                                this.size[1] / 2 + 20);
                    ctx.textAlign = "left";
                }
            };
            
            // 重写onExecuted方法，在节点执行后加载和显示图像
            const origOnExecuted = node.onExecuted;
            node.onExecuted = function(message) {
                if (origOnExecuted) {
                    origOnExecuted.call(this, message);
                }
                
                // 检查是否有图像输出和路径输出
                if (message && message.outputs) {
                    // 获取图像路径
                    const imagePath = message.outputs.image_path;
                    if (imagePath && typeof imagePath === "string" && !imagePath.startsWith("错误:")) {
                        // 创建图像预览URL
                        let previewUrl;
                        if (imagePath.startsWith("/")) {
                            // 绝对路径
                            previewUrl = `/view?filename=${encodeURIComponent(imagePath)}`;
                        } else {
                            // 相对路径
                            previewUrl = `/view?filename=${encodeURIComponent(imagePath)}`;
                        }
                        
                        // 加载预览图像
                        if (this._previewImage) {
                            this._previewImage.src = previewUrl;
                        } else {
                            this._previewImage = new Image();
                            this._previewImage.onload = () => {
                                app.canvas.setDirty(true);
                            };
                            this._previewImage.src = previewUrl;
                        }
                        
                        console.log(`正在加载预览图片: ${previewUrl}`);
                    }
                }
            };
        }
    }
}); 