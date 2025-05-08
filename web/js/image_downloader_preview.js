import { app } from "../../scripts/app.js";

app.registerExtension({
    name: "JM-KLingAI.ImageDownloaderPreview",
    
    nodeCreated(node, app) {
        // 检查节点类型是否为KLingAIImageDownloader
        if (node.comfyClass === "KLingAIImageDownloader") {
            // 找到image_path小部件
            const image_path_widget = node.widgets.find(w => w.name === "image_path");
            
            if (!image_path_widget) return;
            
            // 为节点添加自动预览功能
            node.addCustomWidget({
                name: "preview",
                type: "image",
                draw(ctx, node, width, height) {
                    // 只有当有有效的图片路径时才尝试预览
                    if (!image_path_widget.value || 
                        image_path_widget.value.startsWith("错误:") || 
                        !node._img) {
                        return;
                    }
                    
                    // 计算预览图像的尺寸和位置
                    const max_size = Math.min(width, height);
                    const img = node._img;
                    
                    if (!img || !img.width) return;
                    
                    const img_ratio = img.width / img.height;
                    let w, h;
                    
                    if (img_ratio > 1) {
                        w = max_size;
                        h = max_size / img_ratio;
                    } else {
                        h = max_size;
                        w = max_size * img_ratio;
                    }
                    
                    const x = (width - w) / 2;
                    const y = (height - h) / 2;
                    
                    ctx.drawImage(img, x, y, w, h);
                }
            });

            // 定义一个图像加载函数
            const loadImage = (path) => {
                if (!path || path.startsWith("错误:")) {
                    node._img = null;
                    return;
                }
                
                // 创建一个新的图像对象
                const img = new Image();
                
                // 获取完整的图像URL
                // 注意：这里需要确保路径是相对于ComfyUI输出目录的正确路径
                let img_url;
                if (path.startsWith("/")) {
                    // 绝对路径
                    img_url = `/view?filename=${encodeURIComponent(path)}`;
                } else {
                    // 相对路径（假设是相对于输出目录）
                    img_url = `/view?filename=${encodeURIComponent(path)}`;
                }
                
                img.src = img_url;
                img.onload = () => {
                    node._img = img;
                    app.canvas.setDirty(true);
                };
            };
            
            // 监听图像路径变化
            Object.defineProperty(image_path_widget, "value", {
                get() {
                    return this._value || "";
                },
                set(value) {
                    this._value = value;
                    loadImage(value);
                    return true;
                }
            });
            
            // 设置节点尺寸以便有足够空间显示预览
            node.setSize([300, 400]);
        }
    }
}); 