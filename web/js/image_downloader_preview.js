import { app } from "../../scripts/app.js";

app.registerExtension({
    name: "JM-KLingAI.ImageDownloaderPreview",
    
    nodeCreated(node, app) {
        // 检查节点类型是否为KLingAIImageDownloader
        if (node.comfyClass === "KLingAIImageDownloader") {
            
            // 把节点的image_data隐藏起来
            for (const w of node.widgets) {
                if (w.name === "preview_image" || w.name === "image_data") {
                    w.hide = true;
                }
            }
            
            // 获取节点ID并设置到隐藏参数
            const node_id = node.id;
            const node_id_widget = node.widgets.find(w => w.name === "node_id");
            if (node_id_widget) {
                node_id_widget.value = node_id;
            }
            
            // 找到image_data widget
            const image_data_widget = node.widgets.find(w => w.name === "image_data");
            
            if (!image_data_widget) return;
            
            // 设置节点尺寸以便有足够空间显示预览
            node.setSize([300, 400]);
            
            // 添加预览控件
            node.addCustomWidget({
                name: "preview_widget",
                type: "image",
                
                draw(ctx, node, widget_width, widget_height) {
                    // 获取节点的标题栏高度和控件所占区域高度
                    const headerHeight = 30; // 标题栏近似高度
                    const widgetsHeight = node.widgets.filter(w => !w.hide).length * 32; // 假设每个可见控件高32像素
                    
                    // 计算预览区域的大小和位置
                    const previewX = 10;
                    const previewY = headerHeight + widgetsHeight + 5;
                    const maxWidth = node.size[0] - 20;
                    const maxHeight = node.size[1] - previewY - 10;
                    
                    // 如果没有图像数据，就不显示预览
                    if (!image_data_widget.value) {
                        // 显示提示文字
                        ctx.fillStyle = "#888";
                        ctx.font = "13px Arial";
                        ctx.textAlign = "center";
                        ctx.fillText("下载图片后在此处显示预览", 
                                    node.size[0] / 2, 
                                    previewY + maxHeight / 2);
                        return;
                    }
                    
                    // 尝试创建图像对象
                    if (!node._preview_img && image_data_widget.value) {
                        node._preview_img = new Image();
                        node._preview_img.src = image_data_widget.value;
                        node._preview_img.onload = () => {
                            app.canvas.setDirty(true);
                        };
                    }
                    
                    // 如果图像已加载，绘制它
                    if (node._preview_img && node._preview_img.complete) {
                        const img = node._preview_img;
                        const imgRatio = img.width / img.height;
                        
                        let w, h;
                        if (imgRatio > maxWidth / maxHeight) {
                            // 图像较宽，以宽度为限制
                            w = maxWidth;
                            h = w / imgRatio;
                        } else {
                            // 图像较高，以高度为限制
                            h = maxHeight;
                            w = h * imgRatio;
                        }
                        
                        // 计算居中位置
                        const x = previewX + (maxWidth - w) / 2;
                        const y = previewY + (maxHeight - h) / 2;
                        
                        // 绘制图像
                        ctx.drawImage(img, x, y, w, h);
                    }
                },
                
                // 当widget值改变时
                async value_changed(value, node) {
                    if (value) {
                        node._preview_img = new Image();
                        node._preview_img.src = value;
                        app.canvas.setDirty(true);
                    }
                }
            });
            
            // 监听图像数据变化
            image_data_widget.callback = function(value) {
                if (value && value !== node._last_image_data) {
                    node._last_image_data = value;
                    
                    if (node._preview_img) {
                        node._preview_img.src = value;
                    } else {
                        node._preview_img = new Image();
                        node._preview_img.src = value;
                    }
                    
                    app.canvas.setDirty(true);
                }
                return value;
            };
            
            // 因为自定义控件是在节点创建后添加的，我们需要手动更新节点的大小
            // 这样能确保有足够的空间显示预览
            const orig_onExecuted = node.onExecuted;
            node.onExecuted = function(message) {
                if (orig_onExecuted) {
                    orig_onExecuted.apply(this, arguments);
                }
                
                // 检查输出中是否有image_data
                if (message && message.outputs && message.outputs.image_data) {
                    const image_data = message.outputs.image_data;
                    if (image_data && image_data_widget) {
                        image_data_widget.value = image_data;
                        
                        // 强制重绘
                        app.canvas.setDirty(true);
                    }
                }
            };
        }
    }
}); 