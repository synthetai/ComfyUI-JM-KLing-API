import { app } from "../../scripts/app.js";

app.registerExtension({
    name: "JM.KLingAI.ImageDownloaderPreview",
    
    async setup() {
        console.log("KLingAI Image Downloader Preview Extension 加载成功");
    },
    
    // 当节点被添加到画布上时调用
    async nodeCreated(node) {
        // 检查节点类型是否为KLingAIImageDownloader
        if (node.comfyClass !== "KLingAIImageDownloader") return;
        
        console.log("创建KLingAIImageDownloader节点，添加预览功能");
        
        // 调整节点大小，添加足够的预览空间
        node.size = [320, 420];
        
        // 创建一个图像对象用于预览
        node._previewImg = null;
        node._previewPath = null;
        
        // 保存原始的onDrawForeground方法（如果存在）
        const origDrawForeground = node.onDrawForeground;
        
        // 重写onDrawForeground方法，绘制图片预览
        node.onDrawForeground = function(ctx) {
            if (origDrawForeground) {
                origDrawForeground.call(this, ctx);
            }
            
            // 计算预览区域
            const nodeWidth = this.size[0];
            const nodeHeight = this.size[1];
            const headerHeight = 30;  // 标题栏高度
            const widgetsHeight = this.widgets ? this.widgets.length * 30 : 60;  // 控件区域高度
            const margin = 10;
            
            // 计算可用于预览的区域
            const previewWidth = nodeWidth - margin * 2;
            const previewHeight = nodeHeight - headerHeight - widgetsHeight - margin * 2;
            const previewX = margin;
            const previewY = headerHeight + widgetsHeight + margin;
            
            // 绘制预览区域背景
            ctx.fillStyle = "#2A2A2A";
            ctx.fillRect(previewX, previewY, previewWidth, previewHeight);
            
            // 如果有预览图片，显示它
            if (this._previewImg && this._previewImg.complete && this._previewImg.width > 0) {
                const img = this._previewImg;
                
                // 计算图像显示大小，保持比例
                const imgRatio = img.width / img.height;
                let drawWidth, drawHeight;
                
                if (imgRatio > previewWidth / previewHeight) {
                    // 图像较宽，以宽度为限
                    drawWidth = previewWidth;
                    drawHeight = drawWidth / imgRatio;
                } else {
                    // 图像较高，以高度为限
                    drawHeight = previewHeight;
                    drawWidth = drawHeight * imgRatio;
                }
                
                // 计算居中位置
                const drawX = previewX + (previewWidth - drawWidth) / 2;
                const drawY = previewY + (previewHeight - drawHeight) / 2;
                
                // 绘制预览图像
                ctx.drawImage(img, drawX, drawY, drawWidth, drawHeight);
                
                // 绘制图像尺寸信息
                ctx.fillStyle = "#CCC";
                ctx.font = "12px Arial";
                ctx.textAlign = "right";
                ctx.fillText(`${img.naturalWidth}x${img.naturalHeight}`, 
                             previewX + previewWidth - 5, 
                             previewY + previewHeight - 5);
                ctx.textAlign = "left";
            } else {
                // 没有图像时显示提示文本
                ctx.fillStyle = "#999";
                ctx.font = "14px Arial";
                ctx.textAlign = "center";
                ctx.fillText("下载图片后将在此处显示预览", 
                            previewX + previewWidth / 2, 
                            previewY + previewHeight / 2);
                ctx.textAlign = "left";
            }
        };
        
        // 保存原始的onExecuted方法（如果存在）
        const origExecuted = node.onExecuted;
        
        // 重写onExecuted方法，在节点执行后加载并显示图片
        node.onExecuted = function(message) {
            if (origExecuted) {
                origExecuted.call(this, message);
            }
            
            // 检查是否有图像路径输出
            if (message && message.outputs && message.outputs.image_path) {
                const imagePath = message.outputs.image_path;
                
                // 如果路径无效或与上次相同，则不重新加载
                if (!imagePath || typeof imagePath !== "string" || 
                    imagePath.startsWith("错误:") || 
                    imagePath === this._previewPath) {
                    return;
                }
                
                this._previewPath = imagePath;
                
                // 创建预览URL
                let previewUrl = `/view?filename=${encodeURIComponent(imagePath.trim())}`;
                console.log(`加载预览图片: ${previewUrl}`);
                
                // 加载图片
                if (!this._previewImg) {
                    this._previewImg = new Image();
                }
                
                this._previewImg.onload = () => {
                    console.log(`图片加载成功: ${this._previewImg.width}x${this._previewImg.height}`);
                    app.canvas.setDirty(true); // 通知Canvas需要重绘
                };
                
                this._previewImg.onerror = (err) => {
                    console.error(`图片加载失败: ${previewUrl}`, err);
                };
                
                // 添加时间戳防止缓存
                this._previewImg.src = `${previewUrl}&ts=${Date.now()}`;
            }
        };
    }
}); 