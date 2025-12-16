import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk, colorchooser
from PIL import Image, ImageTk, ImageFilter, ImageEnhance, ImageOps, ImageDraw, ImageFont
import os
import platform
from io import BytesIO

# --- 配置配色方案 ---
COLORS = {
    "bg_main": "#2b2b2b",  # 主背景深灰
    "bg_panel": "#333333",  # 面板背景
    "bg_tool": "#3c3f41",  # 工具栏背景
    "fg_text": "#e0e0e0",  # 文字颜色
    "accent": "#4a90e2",  # 强调色(蓝)
    "accent_hover": "#357abd",  # 强调色悬停
    "border": "#1a1a1a"  # 边框色
}

# --- 新功能模块 --- #

# 1. 涂鸦模块
class DoodleEditor:
    def __init__(self, base_img: Image.Image):
        self.base = base_img
        self.layer = Image.new("RGBA", base_img.size, (0, 0, 0, 0))  # 透明图层
        self.draw = ImageDraw.Draw(self.layer)
        self.size = 20
        self.color = (255, 0, 0, 255)

    def set_brush(self, size, color):
        self.size = size
        self.color = color

    def draw_line(self, x1, y1, x2, y2):
        self.draw.line((x1, y1, x2, y2), fill=self.color, width=self.size)

    def merge(self):
        return Image.alpha_composite(self.base.convert("RGBA"), self.layer).convert("RGB")

# 2. 马赛克模块
class MosaicEditor:
    def __init__(self, base_img: Image.Image):
        self.base = base_img
        self.layer = Image.new("RGBA", base_img.size, (0, 0, 0, 0))  # 透明图层
        self.size = 20
        self.type = "pixel"  # 马赛克类型: pixel, blur, triangle
        self.base_copy = base_img.copy()  # 保存原始图像副本，用于多次马赛克处理

    def set_mosaic_params(self, size, type_):
        self.size = size
        self.type = type_

    def apply_mosaic_area(self, x, y):
        r = self.size // 2
        box = (x - r, y - r, x + r, y + r)
        # 边界检查
        box = (max(0, box[0]), max(0, box[1]), min(self.base.width, box[2]), min(self.base.height, box[3]))
        if box[0] >= box[2] or box[1] >= box[3]:
            return
        
        region = self.base_copy.crop(box)
        
        if self.type == "pixel":
            # 像素化马赛克
            small = region.resize((8, 8), Image.NEAREST)
            mosaic = small.resize(region.size, Image.NEAREST)
        elif self.type == "blur":
            # 模糊马赛克
            mosaic = region.filter(ImageFilter.GaussianBlur(radius=10))
        elif self.type == "triangle":
            # 三角形马赛克（简单模拟）
            small = region.resize((8, 8), Image.NEAREST)
            mosaic = small.resize(region.size, Image.Resampling.BICUBIC)
            mosaic = mosaic.filter(ImageFilter.SHARPEN)
        else:
            # 默认像素化
            small = region.resize((8, 8), Image.NEAREST)
            mosaic = small.resize(region.size, Image.NEAREST)
        
        self.layer.paste(mosaic, box)

    def merge(self):
        return Image.alpha_composite(self.base.convert("RGBA"), self.layer).convert("RGB")

# 2. 可拖动文字水印模块
class DraggableTextWatermark:
    """可拖动 + 可删除 + 支持描边 + 支持透明度 + 支持时间水印"""

    def __init__(self, base_img, is_time=False):
        from datetime import datetime
        self.base = base_img
        self.text = datetime.now().strftime("%Y-%m-%d %H:%M:%S") if is_time else ""
        self.color = (255, 255, 255, 200)
        self.stroke = (0, 0, 0)
        self.stroke_width = 3
        self.size = 42

        # 默认放在中心
        self.x = base_img.width // 2
        self.y = base_img.height // 2


    def set_text(self, text):
        self.text = text

    def set_style(self, rgb_color, size, alpha, stroke_color, stroke_width):
        self.color = (*rgb_color, alpha)
        self.size = size
        self.stroke = stroke_color
        self.stroke_width = stroke_width

    def move_to(self, x, y):
        """绝对移动（用于拖动）"""
        self.x = x
        self.y = y

    def get_bbox(self):
        """获取水印文字的像素边界框"""
        try:
            font = ImageFont.truetype("msyh.ttc", self.size)
        except:
            font = ImageFont.load_default()

        dummy = Image.new("RGBA", (1, 1))
        draw = ImageDraw.Draw(dummy)
        return draw.textbbox((0, 0), self.text, font=font)

    def apply(self):
        """真正绘制到新图层，用于预览和最终应用"""
        img = self.base.convert("RGBA")
        layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(layer)

        try:
            font = ImageFont.truetype("msyh.ttc", self.size)
        except:
            font = ImageFont.load_default()

        # 描边
        if self.stroke_width > 0:
            for dx in (-self.stroke_width, self.stroke_width):
                for dy in (-self.stroke_width, self.stroke_width):
                    draw.text((self.x + dx, self.y + dy), self.text, font=font, fill=self.stroke)

        # 主文字
        draw.text((self.x, self.y), self.text, font=font, fill=self.color)

        return Image.alpha_composite(img, layer).convert("RGB")

# 3. 裁剪比例控制器
class CropController:
    RATIOS = {
        "自由": None,
        "1:1": (1, 1),
        "4:3": (4, 3),
        "3:4": (3, 4),
        "16:9": (16, 9),
        "9:16": (9, 16),
    }

    def __init__(self, img):
        self.img = img
        self.ratio = None

    def set_ratio(self, name):
        self.ratio = self.RATIOS[name]

    def enforce_ratio(self, x1, y1, x2, y2):
        if not self.ratio:
            return x1, y1, x2, y2

        w = abs(x2 - x1)
        h = abs(y2 - y1)
        rw, rh = self.ratio
        if w / h > rw / rh:
            w = h * rw / rh
        else:
            h = w * rh / rw
        return x1, y1, x1 + w, y1 + h

    def crop(self, box):
        return self.img.crop(box)

# 4. LUT 滤镜应用函数
def apply_LUT(img, lut_img):
    lut = lut_img.resize(img.size)
    return Image.blend(img, lut, 0.6)

# 5. 自动压缩函数
def auto_compress(img, target_kb=800):
    buffer = BytesIO()
    quality = 95
    while quality > 10:
        buffer.seek(0)
        img.save(buffer, format="JPEG", quality=quality, optimize=True)
        if len(buffer.getvalue()) / 1024 <= target_kb:
            break
        quality -= 5
    return buffer.getvalue()


class ModernEditor(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ProEditor")
        self.geometry("1280x800")
        self.configure(bg=COLORS["bg_main"])

        # --- 核心数据模型 ---
        self.filepath = None
        self.original_image = None  # 磁盘读取的原始图（作为撤销基准）
        self.editing_image = None  # 当前已应用修改的图片（作为图层基底）
        self.preview_image = None  # 用于显示的图片（叠加了未应用的滤镜/调节）
        self.tk_image = None  # Canvas用的ImageTk对象
        self.history = []  # 撤销栈

        # --- 画布视图状态 ---
        self.zoom_scale = 1.0
        self.pan_offset_x = 0
        self.pan_offset_y = 0
        self.last_mouse_pos = (0, 0)

        # --- 当前工具状态 ---
        self.current_tool = None
        self.temp_adjustments = {  # 暂存调节参数
            "brightness": 1.0,
            "contrast": 1.0,
            "saturation": 1.0,
            "sharpness": 1.0
        }
        
        # --- 新功能实例 ---
        self.doodle_editor = None  # 涂鸦编辑器实例
        self.mosaic_editor = None  # 马赛克编辑器实例
        self.text_watermark = None  # 文字水印实例
        self.crop_controller = None  # 裁剪控制器实例
        self.is_dragging_text = False  # 是否正在拖动文字
        self.text_drag_offset = (0, 0)  # 文字拖动偏移量
        # 水印删除相关变量
        self.show_delete_button = False
        self.delete_button = None
        self.delete_button_rect = None

        # --- UI 初始化 ---
        self._setup_styles()
        self._init_layout()
        self._bind_events()

    def _setup_styles(self):
        """配置自定义 TTK 样式"""
        style = ttk.Style()
        style.theme_use('clam')

        # 一般按钮
        style.configure("TButton", background=COLORS["bg_tool"], foreground=COLORS["fg_text"],
                        borderwidth=0, focuscolor=COLORS["bg_tool"])
        style.map("TButton", background=[("active", COLORS["accent"])])

        # 标签
        style.configure("TLabel", background=COLORS["bg_panel"], foreground=COLORS["fg_text"], font=("Segoe UI", 10))
        style.configure("Header.TLabel", font=("Segoe UI", 11, "bold"), foreground=COLORS["accent"])

        # 框架
        style.configure("TFrame", background=COLORS["bg_panel"])
        style.configure("Main.TFrame", background=COLORS["bg_main"])

        # 滑块
        style.configure("Horizontal.TScale", background=COLORS["bg_panel"], troughcolor=COLORS["bg_main"])

    def _init_layout(self):
        """三栏布局：工具栏(左) | 画布(中) | 属性面板(右)"""

        # 1. 顶部菜单栏 (Header)
        header = tk.Frame(self, bg=COLORS["bg_tool"], height=40)
        header.pack(side=tk.TOP, fill=tk.X)
        self._create_header_btn(header, "📂 打开图片", self.open_image)
        self._create_header_btn(header, "💾 保存", self.save_image)
        self._create_header_btn(header, "↩ 撤销 (Ctrl+Z)", self.undo)
        self._create_header_btn(header, "✨ 自动优化", self.auto_enhance)

        # 2. 主容器
        main_container = ttk.Frame(self, style="Main.TFrame")
        main_container.pack(fill=tk.BOTH, expand=True)

        # 2.1 左侧工具栏 (Sidebar)
        self.sidebar = tk.Frame(main_container, bg=COLORS["bg_tool"], width=80)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar.pack_propagate(False)  # 固定宽度

        # 工具按钮
        self._add_sidebar_tool("基础\n调节", "adjust", lambda: self.show_panel("adjust"))
        self._add_sidebar_tool("滤镜\n特效", "filter", lambda: self.show_panel("filter"))
        self._add_sidebar_tool("裁剪\n旋转", "crop", lambda: self.show_panel("crop"))
        self._add_sidebar_tool("添加\n水印", "text", lambda: self.show_panel("text"))
        self._add_sidebar_tool("涂鸦\n笔刷", "doodle", lambda: self.show_panel("doodle"))
        self._add_sidebar_tool("马赛克", "mosaic", lambda: self.show_panel("mosaic"))

        # 2.2 右侧属性面板 (Properties) - 默认隐藏，动态显示
        self.prop_panel = tk.Frame(main_container, bg=COLORS["bg_panel"], width=280)
        self.prop_panel.pack(side=tk.RIGHT, fill=tk.Y)
        self.prop_panel.pack_propagate(False)

        # 属性面板标题
        self.panel_title = ttk.Label(self.prop_panel, text="工具属性", style="Header.TLabel")
        self.panel_title.pack(pady=10)

        # 属性内容容器
        self.panel_content = tk.Frame(self.prop_panel, bg=COLORS["bg_panel"])
        self.panel_content.pack(fill=tk.BOTH, expand=True, padx=10)

        # 2.3 中间画布 (Canvas)
        canvas_frame = tk.Frame(main_container, bg=COLORS["bg_main"])
        canvas_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(canvas_frame, bg=COLORS["bg_main"], highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # 状态提示
        self.status_label = tk.Label(self.canvas, text="请打开一张图片开始编辑",
                                     bg=COLORS["bg_main"], fg="#666666", font=("Arial", 14))
        self.status_label.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

    def _create_header_btn(self, parent, text, cmd):
        btn = tk.Button(parent, text=text, command=cmd, bg=COLORS["bg_tool"], fg=COLORS["fg_text"],
                        bd=0, activebackground=COLORS["accent"], padx=15, pady=8, font=("Segoe UI", 9))
        btn.pack(side=tk.LEFT, padx=1)

    def _add_sidebar_tool(self, text, tag, cmd):
        btn = tk.Button(self.sidebar, text=text, command=cmd, bg=COLORS["bg_tool"], fg=COLORS["fg_text"],
                        bd=0, activebackground=COLORS["accent"], height=3, font=("Segoe UI", 9))
        btn.pack(fill=tk.X, pady=1)

    def _bind_events(self):
        # 窗口改变大小
        self.canvas.bind("<Configure>", self._on_resize)
        # 鼠标滚轮缩放
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)  # Windows
        self.canvas.bind("<Button-4>", self._on_mousewheel)  # Linux
        self.canvas.bind("<Button-5>", self._on_mousewheel)  # Linux
        # 右键拖拽画布
        self.canvas.bind("<ButtonPress-3>", self._on_pan_start)
        self.canvas.bind("<B3-Motion>", self._on_pan_move)
        # 快捷键
        self.bind("<Control-z>", lambda e: self.undo())
        self.bind("<Control-s>", lambda e: self.save_image())

    # --- 核心逻辑: 图片加载与显示 ---

    def open_image(self):
        path = filedialog.askopenfilename(filetypes=[("Images", "*.jpg *.png *.jpeg *.bmp *.webp")])
        if path:
            try:
                self.filepath = path
                # 尝试打开图片并转换为RGB格式
                image = Image.open(path).convert("RGB")
                # 限制最大尺寸以防卡顿
                if max(image.size) > 4000:
                    image.thumbnail((4000, 4000))

                self.original_image = image
                self.editing_image = image.copy()
                self.preview_image = image.copy()

                # 初始化新功能实例
                self.doodle_editor = DoodleEditor(self.editing_image.copy())
                self.text_watermark = DraggableTextWatermark(self.editing_image.copy())
                self.crop_controller = CropController(self.editing_image.copy())

                self.history.clear()
                self._reset_view()
                
                # 检查status_label是否存在再销毁
                if hasattr(self, 'status_label') and self.status_label.winfo_exists():
                    self.status_label.destroy()
                
                self.show_panel("adjust")  # 默认打开调节面板
                self._update_canvas()
                
            except Exception as e:
                # 显示错误信息
                messagebox.showerror("错误", f"无法打开图片: {str(e)}")
                print(f"打开图片失败: {str(e)}")

    def _reset_view(self):
        """重置视图缩放和偏移"""
        self.zoom_scale = 1.0
        self.pan_offset_x = 0
        self.pan_offset_y = 0
        # 自动适应窗口
        if self.editing_image:
            cw = self.canvas.winfo_width()
            ch = self.canvas.winfo_height()
            iw, ih = self.editing_image.size
            self.zoom_scale = min(cw / iw, ch / ih) * 0.9

    def _update_canvas(self):
        """渲染画布 (核心渲染循环)"""
        if not self.preview_image:
            return

        # 1. 计算显示尺寸
        orig_w, orig_h = self.preview_image.size
        new_w = int(orig_w * self.zoom_scale)
        new_h = int(orig_h * self.zoom_scale)

        # 2. 性能优化：如果缩放太小，用 thumbnail，否则 resize
        # 这里为了简单直接 resize，实际项目可加缓存
        try:
            display_img = None
            
            # 如果正在拖动水印，或者当前正在编辑水印，显示临时水印
            if (self.is_dragging_text or self.current_tool == "text") and self.text_watermark:
                # 生成带临时水印的预览图
                temp_img = self.text_watermark.apply()
                display_img = temp_img.resize((new_w, new_h),
                                            Image.Resampling.NEAREST if self.zoom_scale > 2 else Image.Resampling.LANCZOS)
            else:
                # 正常渲染，只显示已应用的水印
                display_img = self.preview_image.resize((new_w, new_h),
                                            Image.Resampling.NEAREST if self.zoom_scale > 2 else Image.Resampling.LANCZOS)
            
            self.tk_image = ImageTk.PhotoImage(display_img)

            # 3. 计算居中坐标 + 偏移量
            cx = self.canvas.winfo_width() // 2 + self.pan_offset_x
            cy = self.canvas.winfo_height() // 2 + self.pan_offset_y

            # 保存删除按钮状态
            show_delete = self.show_delete_button
            self._hide_delete_button()

            self.canvas.delete("all")
            self.canvas.create_image(cx, cy, anchor=tk.CENTER, image=self.tk_image, tags="img")

            # 如果有裁剪框等覆盖层，需重新绘制
            if self.current_tool == "crop":
                self._draw_crop_rect(cx, cy, new_w, new_h)
            
            # 如果之前显示了删除按钮，重新绘制
            if show_delete:
                self.show_delete_button = True
                self._show_delete_button()

        except Exception as e:
            error_msg = f"渲染错误: {str(e)}"
            print(error_msg)
            # 在画布上显示错误信息
            self.canvas.delete("all")
            self.canvas.create_text(
                self.canvas.winfo_width() // 2,
                self.canvas.winfo_height() // 2,
                text=error_msg,
                fill="red",
                font=("Arial", 12),
                tags="error"
            )

    # --- 交互逻辑: 缩放与平移 ---

    def _on_mousewheel(self, event):
        if not self.editing_image: return
        # Windows: event.delta, Linux: 4/5 buttons
        if event.num == 5 or event.delta < 0:
            self.zoom_scale *= 0.9
        else:
            self.zoom_scale *= 1.1
        self._update_canvas()

    def _on_pan_start(self, event):
        self.last_mouse_pos = (event.x, event.y)
        self.canvas.config(cursor="fleur")

    def _on_pan_move(self, event):
        dx = event.x - self.last_mouse_pos[0]
        dy = event.y - self.last_mouse_pos[1]
        self.pan_offset_x += dx
        self.pan_offset_y += dy
        self.last_mouse_pos = (event.x, event.y)
        self._update_canvas()

    def _on_resize(self, event):
        if self.editing_image:
            self._update_canvas()

    # --- 历史记录与保存 ---

    def _push_history(self):
        """保存当前 editing_image 到历史栈"""
        if self.editing_image:
            self.history.append(self.editing_image.copy())
            if len(self.history) > 15: self.history.pop(0)

    def undo(self):
        if self.history:
            self.editing_image = self.history.pop()
            self.preview_image = self.editing_image.copy()
            self._reset_adjust_params()
            # 重新初始化所有功能实例，确保它们基于撤销后的图像
            self.doodle_editor = DoodleEditor(self.editing_image.copy())
            self.text_watermark = DraggableTextWatermark(self.editing_image.copy())
            self.crop_controller = CropController(self.editing_image.copy())
            self._update_canvas()

    def save_image(self):
        if not self.editing_image: return
        
        # 询问是否需要压缩
        response = messagebox.askyesno("压缩选项", "是否需要压缩图片？")
        
        if response:
            # 显示压缩设置对话框
            target_kb = simpledialog.askinteger("压缩设置", "目标大小 (KB):", minvalue=50, maxvalue=2048, initialvalue=800)
            if target_kb is None:
                return  # 用户取消
            
            # 执行压缩
            compressed_data = auto_compress(self.editing_image, target_kb)
            
            # 保存压缩后的图片
            path = filedialog.asksaveasfilename(defaultextension=".jpg",
                                                filetypes=[("JPG", "*.jpg")])
            if path:
                with open(path, "wb") as f:
                    f.write(compressed_data)
                messagebox.showinfo("成功", f"图片已压缩并保存，大小约 {len(compressed_data)/1024:.1f} KB")
        else:
            # 普通保存
            path = filedialog.asksaveasfilename(defaultextension=".jpg",
                                                filetypes=[("JPG", "*.jpg"), ("PNG", "*.png")])
            if path:
                self.editing_image.save(path, quality=95)
                messagebox.showinfo("成功", "保存成功")

    def auto_enhance(self):
        """自动美化（示例功能）"""
        if not self.editing_image: return
        self._push_history()
        self.editing_image = ImageOps.autocontrast(self.editing_image)
        self.preview_image = self.editing_image.copy()
        self._update_canvas()

    # --- 面板管理 (Panel Router) ---

    def show_panel(self, tool_name):
        """切换右侧面板内容"""
        # 如果从其他工具切换过来，先应用更改（例如裁剪）
        self._apply_pending_changes()

        self.current_tool = tool_name
        self.canvas.delete("overlay")  # 清除辅助线
        # 解绑所有可能的事件，包括右键点击事件
        self.canvas.unbind("<ButtonPress-1>")
        self.canvas.unbind("<B1-Motion>")
        self.canvas.unbind("<ButtonRelease-1>")
        self.canvas.unbind("<ButtonPress-3>")
        self.canvas.config(cursor="")

        # 清空面板
        for widget in self.panel_content.winfo_children():
            widget.destroy()

        # 根据工具构建 UI
        titles = {
            "adjust": "光效调节", "filter": "滤镜库",
            "crop": "裁剪构图", "text": "添加水印", "doodle": "画笔涂鸦", "mosaic": "马赛克工具"
        }
        self.panel_title.config(text=titles.get(tool_name, "工具"))

        if tool_name == "adjust":
            self._build_adjust_panel()
        elif tool_name == "filter":
            self._build_filter_panel()
        elif tool_name == "crop":
            self._build_crop_panel()
        elif tool_name == "text":
            self._build_text_panel()
        elif tool_name == "doodle":
            self._build_doodle_panel()
        elif tool_name == "mosaic":
            self._build_mosaic_panel()

    def _apply_pending_changes(self):
        """应用当前面板的临时修改"""
        if self.current_tool == "adjust":
            # 调节是实时的，不需要特殊应用，因为 preview 已经是 adjust 后的结果
            # 但我们需要把 preview 固化到 editing_image
            if self.preview_image != self.editing_image:
                self._push_history()
                self.editing_image = self.preview_image.copy()
                self._reset_adjust_params()

        if self.current_tool == "crop":
            # 裁剪需要显式确认，切换工具时自动取消裁剪框
            pass
        
        # 切换工具时隐藏删除按钮
        if self.show_delete_button:
            self._hide_delete_button()

            # --- 1. 基础调节模块 (Real-time) ---

    def _build_adjust_panel(self):
        """构建调节滑块"""
        self._create_slider("亮度", "brightness", 0.5, 1.5)
        self._create_slider("对比度", "contrast", 0.5, 1.5)
        self._create_slider("饱和度", "saturation", 0.0, 2.0)
        self._create_slider("锐化", "sharpness", 0.0, 2.0)

        ttk.Button(self.panel_content, text="应用调节", command=self._apply_adjust).pack(pady=20, fill=tk.X)
        ttk.Label(self.panel_content, text="* 拖动滑块实时预览", foreground="#888888").pack()

    def _create_slider(self, label, param_key, min_v, max_v):
        frame = tk.Frame(self.panel_content, bg=COLORS["bg_panel"])
        frame.pack(fill=tk.X, pady=5)

        ttk.Label(frame, text=label).pack(anchor=tk.W)
        scale = ttk.Scale(frame, from_=min_v, to=max_v, value=self.temp_adjustments[param_key],
                          command=lambda v: self._on_adjust_change(param_key, float(v)))
        scale.pack(fill=tk.X)

    def _on_adjust_change(self, key, value):
        self.temp_adjustments[key] = value
        # 实时处理 (Pipeline)
        if not self.editing_image: return

        # 基于 editing_image (底图) 进行计算
        img = self.editing_image.copy()

        if self.temp_adjustments["brightness"] != 1.0:
            img = ImageEnhance.Brightness(img).enhance(self.temp_adjustments["brightness"])
        if self.temp_adjustments["contrast"] != 1.0:
            img = ImageEnhance.Contrast(img).enhance(self.temp_adjustments["contrast"])
        if self.temp_adjustments["saturation"] != 1.0:
            img = ImageEnhance.Color(img).enhance(self.temp_adjustments["saturation"])
        if self.temp_adjustments["sharpness"] != 1.0:
            img = ImageEnhance.Sharpness(img).enhance(self.temp_adjustments["sharpness"])

        self.preview_image = img
        self._update_canvas()

    def _apply_adjust(self):
        self._push_history()
        self.editing_image = self.preview_image.copy()
        self._reset_adjust_params()
        self.show_panel("adjust")  # 重置滑块

    def _reset_adjust_params(self):
        self.temp_adjustments = {k: 1.0 for k in self.temp_adjustments}

    # --- 2. 滤镜模块 (支持LUT上传) ---

    def _build_filter_panel(self):
        # 内置滤镜
        ttk.Label(self.panel_content, text="内置滤镜:").pack(anchor=tk.W, pady=5)
        filters = ["原始", "黑白", "怀旧", "模糊", "浮雕", "轮廓"]
        for f in filters:
            btn = tk.Button(self.panel_content, text=f, bg=COLORS["bg_tool"], fg="white",
                            command=lambda mode=f: self._apply_filter_preview(mode))
            btn.pack(fill=tk.X, pady=2)
        
        # LUT滤镜
        ttk.Separator(self.panel_content, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
        ttk.Label(self.panel_content, text="LUT滤镜:").pack(anchor=tk.W, pady=5)
        ttk.Button(self.panel_content, text="选择LUT文件", command=self._load_lut_file).pack(fill=tk.X, pady=5)
        ttk.Label(self.panel_content, text="* 支持 .cube 或 .png 格式", foreground="#888888").pack()

        ttk.Button(self.panel_content, text="✔ 确认应用", command=self._confirm_filter).pack(pady=20, fill=tk.X)
        ttk.Label(self.panel_content, text="* 实时预览效果", foreground="#888888").pack()

    def _apply_filter_preview(self, mode):
        if not self.editing_image: return
        img = self.editing_image.copy()

        if mode == "黑白":
            img = img.convert("L").convert("RGB")
        elif mode == "怀旧":
            # 简单的棕褐色滤镜模拟
            sepia = []
            r, g, b = (239, 224, 198)
            for i in range(255):
                sepia.extend((int(r * i / 255), int(g * i / 255), int(b * i / 255)))
            img = img.convert("L")
            img.putpalette(sepia)
            img = img.convert("RGB")
        elif mode == "模糊":
            img = img.filter(ImageFilter.GaussianBlur(5))
        elif mode == "浮雕":
            img = img.filter(ImageFilter.EMBOSS)
        elif mode == "轮廓":
            img = img.filter(ImageFilter.CONTOUR)
        elif mode == "原始":
            img = self.editing_image.copy()

        self.preview_image = img
        self._update_canvas()

    def _load_lut_file(self):
        if not self.editing_image: return
        
        # 打开文件选择对话框，支持 .cube 和 .png 文件
        path = filedialog.askopenfilename(filetypes=[("LUT Files", "*.cube *.png"), ("All Files", "*.*")])
        if not path:
            return
        
        try:
            # 加载LUT图片
            lut_img = Image.open(path).convert("RGB")
            # 应用LUT效果
            self.preview_image = apply_LUT(self.editing_image, lut_img)
            self._update_canvas()
            messagebox.showinfo("提示", "LUT滤镜已加载")
        except Exception as e:
            messagebox.showerror("错误", f"无法加载LUT文件: {str(e)}")

    def _confirm_filter(self):
        self._push_history()
        self.editing_image = self.preview_image.copy()
        # 更新其他功能实例
        self.doodle_editor = DoodleEditor(self.editing_image.copy())
        self.text_watermark = DraggableTextWatermark(self.editing_image.copy())
        self._update_canvas()
        messagebox.showinfo("提示", "滤镜已应用")

    # --- 3. 裁剪模块 (带比例选项) ---

    def _build_crop_panel(self):
        ttk.Label(self.panel_content, text="裁剪比例:").pack(anchor=tk.W)
        
        # 裁剪比例按钮组
        ratio_frame = tk.Frame(self.panel_content, bg=COLORS["bg_panel"])
        ratio_frame.pack(fill=tk.X, pady=5)
        
        # 比例选项列表
        ratios = ["自由", "1:1", "4:3", "3:4", "16:9", "9:16"]
        self.selected_ratio = tk.StringVar(value="自由")
        
        for ratio in ratios:
            btn = ttk.Radiobutton(ratio_frame, text=ratio, variable=self.selected_ratio, value=ratio, 
                                 command=self._update_crop_ratio)
            btn.pack(side=tk.LEFT, padx=3)
        
        # 添加旋转和翻转按钮组
        ttk.Label(self.panel_content, text="旋转/翻转:").pack(anchor=tk.W, pady=(10, 0))
        rotate_frame = tk.Frame(self.panel_content, bg=COLORS["bg_panel"])
        rotate_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(rotate_frame, text="左旋转90°", command=self._rotate_left).pack(side=tk.LEFT, padx=3, fill=tk.X, expand=True)
        ttk.Button(rotate_frame, text="右旋转90°", command=self._rotate_right).pack(side=tk.LEFT, padx=3, fill=tk.X, expand=True)
        ttk.Button(rotate_frame, text="左右翻转", command=self._flip_horizontal).pack(side=tk.LEFT, padx=3, fill=tk.X, expand=True)
        ttk.Button(rotate_frame, text="上下翻转", command=self._flip_vertical).pack(side=tk.LEFT, padx=3, fill=tk.X, expand=True)
        
        # 添加自定义旋转角度控制
        ttk.Label(self.panel_content, text="旋转角度:").pack(anchor=tk.W, pady=(10, 0))
        rotate_angle_frame = tk.Frame(self.panel_content, bg=COLORS["bg_panel"])
        rotate_angle_frame.pack(fill=tk.X, pady=5)
        
        self.rotate_angle_var = tk.IntVar(value=0)
        
        # 旋转角度滑块
        angle_scale = ttk.Scale(rotate_angle_frame, from_=0, to=360, variable=self.rotate_angle_var, 
                               command=lambda v: self._on_rotate_angle_change())
        angle_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=3)
        
        # 旋转角度输入框
        angle_entry = ttk.Entry(rotate_angle_frame, textvariable=self.rotate_angle_var, width=5)
        angle_entry.pack(side=tk.LEFT, padx=3)
        
        # 旋转角度应用按钮
        ttk.Button(rotate_angle_frame, text="旋转", command=self._rotate_by_angle).pack(side=tk.LEFT, padx=3)
        
        ttk.Button(self.panel_content, text="开始/重置裁剪框", command=self._init_crop_tool).pack(fill=tk.X, pady=5)
        ttk.Button(self.panel_content, text="✔ 确认裁剪", command=self._do_crop).pack(fill=tk.X, pady=20)

        # 初始化裁剪控制器
        self.crop_controller = CropController(self.editing_image.copy()) if self.editing_image else None
        
        self.crop_start = None
        self.crop_end = None
        self.is_cropping = False

    def _update_crop_ratio(self):
        if self.crop_controller:
            self.crop_controller.set_ratio(self.selected_ratio.get())
            # 如果已经有裁剪框，重新绘制
            if self.crop_start and self.crop_end:
                self._update_canvas()

    def _init_crop_tool(self):
        self.is_cropping = True
        self.canvas.config(cursor="cross")
        self.crop_start = None
        self.resize_mode = None  # 调整模式：None, 'n', 'ne', 'e', 'se', 's', 'sw', 'w', 'nw'
        self.resize_corner = None
        self.canvas.bind("<ButtonPress-1>", self._on_crop_press)
        self.canvas.bind("<B1-Motion>", self._on_crop_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_crop_release)
        self.canvas.bind("<Motion>", self._on_crop_motion)

    def _on_crop_press(self, event):
        if not self.is_cropping: return
        
        # 检查是否点击在裁剪框内部
        if self.crop_start and self.crop_end:
            # 确保x1 < x2, y1 < y2
            crop_x1 = min(self.crop_start[0], self.crop_end[0])
            crop_y1 = min(self.crop_start[1], self.crop_end[1])
            crop_x2 = max(self.crop_start[0], self.crop_end[0])
            crop_y2 = max(self.crop_start[1], self.crop_end[1])
            
            mouse_x, mouse_y = event.x, event.y
            
            # 检查距离边缘的距离
            edge_threshold = 10
            
            # 计算与各边的距离
            dist_left = abs(mouse_x - crop_x1)
            dist_right = abs(mouse_x - crop_x2)
            dist_top = abs(mouse_y - crop_y1)
            dist_bottom = abs(mouse_y - crop_y2)
            
            # 检查是否在边缘或角点
            is_left = dist_left <= edge_threshold
            is_right = dist_right <= edge_threshold
            is_top = dist_top <= edge_threshold
            is_bottom = dist_bottom <= edge_threshold
            
            if is_left or is_right or is_top or is_bottom:
                # 设置调整模式
                if is_top:
                    if is_left:
                        self.resize_mode = 'nw'
                        self.resize_corner = 'start'
                    elif is_right:
                        self.resize_mode = 'ne'
                        self.resize_corner = 'end'
                    else:
                        self.resize_mode = 'n'
                        self.resize_corner = 'top'
                elif is_bottom:
                    if is_left:
                        self.resize_mode = 'sw'
                        self.resize_corner = 'start'
                    elif is_right:
                        self.resize_mode = 'se'
                        self.resize_corner = 'end'
                    else:
                        self.resize_mode = 's'
                        self.resize_corner = 'bottom'
                elif is_left:
                    self.resize_mode = 'w'
                    self.resize_corner = 'start'
                elif is_right:
                    self.resize_mode = 'e'
                    self.resize_corner = 'end'
                
                return
            # 检查是否在裁剪框内部
            elif crop_x1 < mouse_x < crop_x2 and crop_y1 < mouse_y < crop_y2:
                # 设置为移动模式
                self.resize_mode = 'move'
                self.move_offset = (mouse_x - crop_x1, mouse_y - crop_y1)
                self.canvas.config(cursor="fleur")
                return
        
        # 正常创建新的裁剪框
        self.resize_mode = None
        self.crop_start = (event.x, event.y)
        self.crop_end = (event.x, event.y)

    def _on_crop_drag(self, event):
        if not self.is_cropping: return
        
        mouse_x, mouse_y = event.x, event.y
        
        if self.resize_mode:
            if self.resize_mode == 'move':
                # 移动整个裁剪框
                crop_x1 = min(self.crop_start[0], self.crop_end[0])
                crop_y1 = min(self.crop_start[1], self.crop_end[1])
                crop_x2 = max(self.crop_start[0], self.crop_end[0])
                crop_y2 = max(self.crop_start[1], self.crop_end[1])
                
                # 计算裁剪框的宽度和高度
                crop_width = crop_x2 - crop_x1
                crop_height = crop_y2 - crop_y1
                
                # 计算新的裁剪框位置
                new_crop_x1 = mouse_x - self.move_offset[0]
                new_crop_y1 = mouse_y - self.move_offset[1]
                new_crop_x2 = new_crop_x1 + crop_width
                new_crop_y2 = new_crop_y1 + crop_height
                
                # 更新裁剪框坐标
                self.crop_start = (new_crop_x1, new_crop_y1)
                self.crop_end = (new_crop_x2, new_crop_y2)
            else:
                # 调整裁剪框大小
                # 确保x1 < x2, y1 < y2
                crop_x1 = min(self.crop_start[0], self.crop_end[0])
                crop_y1 = min(self.crop_start[1], self.crop_end[1])
                crop_x2 = max(self.crop_start[0], self.crop_end[0])
                crop_y2 = max(self.crop_start[1], self.crop_end[1])
                
                # 根据调整模式更新裁剪框
                if self.resize_mode in ['nw', 'w', 'sw']:
                    crop_x1 = mouse_x
                elif self.resize_mode in ['ne', 'e', 'se']:
                    crop_x2 = mouse_x
                
                if self.resize_mode in ['nw', 'n', 'ne']:
                    crop_y1 = mouse_y
                elif self.resize_mode in ['sw', 's', 'se']:
                    crop_y2 = mouse_y
                
                # 确保裁剪框有最小尺寸
                min_size = 20
                if crop_x2 - crop_x1 < min_size:
                    if self.resize_mode in ['nw', 'w', 'sw']:
                        crop_x1 = crop_x2 - min_size
                    else:
                        crop_x2 = crop_x1 + min_size
                
                if crop_y2 - crop_y1 < min_size:
                    if self.resize_mode in ['nw', 'n', 'ne']:
                        crop_y1 = crop_y2 - min_size
                    else:
                        crop_y2 = crop_y1 + min_size
                
                # 更新裁剪框坐标
                if self.resize_corner == 'start':
                    self.crop_start = (crop_x1, crop_y1)
                    self.crop_end = (crop_x2, crop_y2)
                else:
                    self.crop_start = (crop_x1, crop_y1)
                    self.crop_end = (crop_x2, crop_y2)
        else:
            # 正常绘制新的裁剪框
            self.crop_end = (event.x, event.y)
        
        self._update_canvas()  # 重绘会触发 _draw_crop_rect
    
    def _on_crop_release(self, event):
        # 结束裁剪或调整
        self.resize_mode = None
    
    def _on_crop_motion(self, event):
        if not self.is_cropping or not self.crop_start or not self.crop_end:
            return
        
        # 检查是否在裁剪框边缘或角点
        crop_x1 = min(self.crop_start[0], self.crop_end[0])
        crop_y1 = min(self.crop_start[1], self.crop_end[1])
        crop_x2 = max(self.crop_start[0], self.crop_end[0])
        crop_y2 = max(self.crop_start[1], self.crop_end[1])
        
        edge_threshold = 10
        mouse_x, mouse_y = event.x, event.y
        
        dist_left = abs(mouse_x - crop_x1)
        dist_right = abs(mouse_x - crop_x2)
        dist_top = abs(mouse_y - crop_y1)
        dist_bottom = abs(mouse_y - crop_y2)
        
        is_left = dist_left <= edge_threshold
        is_right = dist_right <= edge_threshold
        is_top = dist_top <= edge_threshold
        is_bottom = dist_bottom <= edge_threshold
        
        # 检查是否在裁剪框内部
        is_inside = crop_x1 < mouse_x < crop_x2 and crop_y1 < mouse_y < crop_y2
        
        # 改变光标样式
        if is_left or is_right or is_top or is_bottom:
            if (is_top and is_left) or (is_bottom and is_right):
                self.canvas.config(cursor="size_nw_se")
            elif (is_top and is_right) or (is_bottom and is_left):
                self.canvas.config(cursor="size_ne_sw")
            elif is_left or is_right:
                self.canvas.config(cursor="size_we")
            elif is_top or is_bottom:
                self.canvas.config(cursor="size_ns")
        elif is_inside:
            self.canvas.config(cursor="fleur")
        else:
            self.canvas.config(cursor="cross")

    def _draw_crop_rect(self, cx, cy, img_w, img_h):
        if self.crop_start and self.crop_end:
            # 应用裁剪比例
            x1, y1 = self.crop_start
            x2, y2 = self.crop_end
            
            # 屏幕坐标转相对坐标
            rel_x1 = 0
            rel_y1 = 0
            rel_x2 = x2 - x1
            rel_y2 = y2 - y1
            
            # 应用比例约束
            if self.crop_controller and self.crop_controller.ratio:
                rel_x1, rel_y1, rel_x2, rel_y2 = self.crop_controller.enforce_ratio(rel_x1, rel_y1, rel_x2, rel_y2)
                x2 = x1 + rel_x2
                y2 = y1 + rel_y2
            
            # 获取画布尺寸
            canvas_w = self.canvas.winfo_width()
            canvas_h = self.canvas.winfo_height()
            
            # 确保x1 < x2, y1 < y2
            crop_x1 = min(x1, x2)
            crop_y1 = min(y1, y2)
            crop_x2 = max(x1, x2)
            crop_y2 = max(y1, y2)
            
            # 绘制半透明遮罩
            # 左侧遮罩
            self.canvas.create_rectangle(0, 0, crop_x1, canvas_h,
                                        fill="#000000", stipple="gray50", tags="overlay")
            # 右侧遮罩
            self.canvas.create_rectangle(crop_x2, 0, canvas_w, canvas_h,
                                        fill="#000000", stipple="gray50", tags="overlay")
            # 上侧遮罩
            self.canvas.create_rectangle(crop_x1, 0, crop_x2, crop_y1,
                                        fill="#000000", stipple="gray50", tags="overlay")
            # 下侧遮罩
            self.canvas.create_rectangle(crop_x1, crop_y2, crop_x2, canvas_h,
                                        fill="#000000", stipple="gray50", tags="overlay")
            
            # 画裁剪矩形
            self.canvas.create_rectangle(crop_x1, crop_y1, crop_x2, crop_y2,
                                         outline=COLORS["accent"], width=2, dash=(5, 2), tags="overlay")
            # 绘制裁剪框角点
            corner_size = 8
            corners = [
                (crop_x1 - corner_size, crop_y1 - corner_size, crop_x1 + corner_size, crop_y1 + corner_size),  # 左上
                (crop_x2 - corner_size, crop_y1 - corner_size, crop_x2 + corner_size, crop_y1 + corner_size),  # 右上
                (crop_x1 - corner_size, crop_y2 - corner_size, crop_x1 + corner_size, crop_y2 + corner_size),  # 左下
                (crop_x2 - corner_size, crop_y2 - corner_size, crop_x2 + corner_size, crop_y2 + corner_size),  # 右下
            ]
            for corner in corners:
                self.canvas.create_rectangle(*corner, fill=COLORS["accent"], outline="white", width=1, tags="overlay")

    def _rotate_left(self):
        """左旋转90°"""
        if not self.editing_image: return
        
        self._push_history()
        # 左旋转90°（PIL的rotate方法，逆时针旋转）
        self.editing_image = self.editing_image.rotate(90, expand=True)
        self.preview_image = self.editing_image.copy()
        
        # 更新其他功能实例
        self.doodle_editor = DoodleEditor(self.editing_image.copy())
        self.text_watermark = DraggableTextWatermark(self.editing_image.copy())
        self.crop_controller = CropController(self.editing_image.copy())
        
        self._reset_view()
        self._update_canvas()
    
    def _rotate_right(self):
        """右旋转90°"""
        if not self.editing_image: return
        
        self._push_history()
        # 右旋转90°（PIL的rotate方法，顺时针旋转）
        self.editing_image = self.editing_image.rotate(-90, expand=True)
        self.preview_image = self.editing_image.copy()
        
        # 更新其他功能实例
        self.doodle_editor = DoodleEditor(self.editing_image.copy())
        self.text_watermark = DraggableTextWatermark(self.editing_image.copy())
        self.crop_controller = CropController(self.editing_image.copy())
        
        self._reset_view()
        self._update_canvas()
    
    def _flip_horizontal(self):
        """镜面左右翻转"""
        if not self.editing_image: return
        
        self._push_history()
        # 左右翻转
        self.editing_image = ImageOps.mirror(self.editing_image)
        self.preview_image = self.editing_image.copy()
        
        # 更新其他功能实例
        self.doodle_editor = DoodleEditor(self.editing_image.copy())
        self.text_watermark = DraggableTextWatermark(self.editing_image.copy())
        self.crop_controller = CropController(self.editing_image.copy())
        
        self._reset_view()
        self._update_canvas()
    
    def _flip_vertical(self):
        """镜面上下翻转"""
        if not self.editing_image: return
        
        self._push_history()
        # 上下翻转
        self.editing_image = ImageOps.flip(self.editing_image)
        self.preview_image = self.editing_image.copy()
        
        # 更新其他功能实例
        self.doodle_editor = DoodleEditor(self.editing_image.copy())
        self.text_watermark = DraggableTextWatermark(self.editing_image.copy())
        self.crop_controller = CropController(self.editing_image.copy())
        
        self._reset_view()
        self._update_canvas()
    
    def _on_rotate_angle_change(self):
        """旋转角度变化时的处理"""
        # 确保角度在0-360范围内
        angle = self.rotate_angle_var.get()
        if angle < 0:
            self.rotate_angle_var.set(0)
        elif angle > 360:
            self.rotate_angle_var.set(360)
        
        # 实时预览旋转效果
        if self.editing_image and self.preview_image:
            # 基于原始图片进行旋转，而不是累积旋转
            self.preview_image = self.editing_image.rotate(angle, expand=True)
            self._update_canvas()
    
    def _rotate_by_angle(self):
        """根据自定义角度旋转图片"""
        if not self.editing_image: return
        
        self._push_history()
        
        # 将实时预览的旋转效果应用到编辑图像
        self.editing_image = self.preview_image.copy()
        
        # 更新其他功能实例
        self.doodle_editor = DoodleEditor(self.editing_image.copy())
        self.text_watermark = DraggableTextWatermark(self.editing_image.copy())
        self.crop_controller = CropController(self.editing_image.copy())
        
        # 重置旋转角度滑块
        self.rotate_angle_var.set(0)
        
        self._reset_view()
        self._update_canvas()
    
    def _do_crop(self):
        if not self.crop_start or not self.crop_end: return

        # 1. 屏幕坐标转图片坐标
        # 计算图片左上角在 Canvas 上的位置
        cx = self.canvas.winfo_width() // 2 + self.pan_offset_x
        cy = self.canvas.winfo_height() // 2 + self.pan_offset_y

        current_w = int(self.editing_image.width * self.zoom_scale)
        current_h = int(self.editing_image.height * self.zoom_scale)

        img_x1 = cx - current_w // 2
        img_y1 = cy - current_h // 2

        # 裁剪框的屏幕坐标
        x1, y1 = self.crop_start
        x2, y2 = self.crop_end
        
        # 应用比例约束
        rel_x1 = 0
        rel_y1 = 0
        rel_x2 = x2 - x1
        rel_y2 = y2 - y1
        
        if self.crop_controller and self.crop_controller.ratio:
            rel_x1, rel_y1, rel_x2, rel_y2 = self.crop_controller.enforce_ratio(rel_x1, rel_y1, rel_x2, rel_y2)
            x2 = x1 + rel_x2
            y2 = y1 + rel_y2
        
        x_min, x_max = sorted([x1, x2])
        y_min, y_max = sorted([y1, y2])

        # 相对图片的偏移
        rel_x1 = (x_min - img_x1) / self.zoom_scale
        rel_y1 = (y_min - img_y1) / self.zoom_scale
        rel_x2 = (x_max - img_x1) / self.zoom_scale
        rel_y2 = (y_max - img_y1) / self.zoom_scale

        # 边界检查
        rel_x1 = max(0, rel_x1)
        rel_y1 = max(0, rel_y1)
        rel_x2 = min(self.editing_image.width, rel_x2)
        rel_y2 = min(self.editing_image.height, rel_y2)

        if rel_x2 - rel_x1 < 10 or rel_y2 - rel_y1 < 10:
            return  # 太小

        self._push_history()
        self.editing_image = self.editing_image.crop((rel_x1, rel_y1, rel_x2, rel_y2))
        self.preview_image = self.editing_image.copy()
        
        # 更新其他功能实例
        self.doodle_editor = DoodleEditor(self.editing_image.copy())
        self.text_watermark = DraggableTextWatermark(self.editing_image.copy())
        self.crop_controller = CropController(self.editing_image.copy())

        # 重置
        self.is_cropping = False
        self.crop_start = None
        self.canvas.config(cursor="")
        self._reset_view()
        self._update_canvas()

    # --- 4. 文字水印 (可拖动) ---

    def _build_text_panel(self):
        # 水印类型选择
        ttk.Label(self.panel_content, text="水印类型:").pack(anchor=tk.W)
        self.watermark_type = tk.StringVar(value="text")
        type_frame = tk.Frame(self.panel_content, bg=COLORS["bg_panel"])
        type_frame.pack(fill=tk.X, pady=5)
        
        # 添加水印类型切换事件
        def on_watermark_type_change():
            # 始终显示文字输入框，不受水印类型影响
            self.txt_entry.pack(fill=tk.X, pady=5)
            # 更新预览
            self._update_text_preview()
        
        ttk.Radiobutton(type_frame, text="文字水印", variable=self.watermark_type, value="text", command=on_watermark_type_change).pack(side=tk.LEFT, padx=3)
        ttk.Radiobutton(type_frame, text="时间水印", variable=self.watermark_type, value="time", command=on_watermark_type_change).pack(side=tk.LEFT, padx=3)

        # 文字输入
        self.txt_entry = ttk.Entry(self.panel_content)
        self.txt_entry.pack(fill=tk.X, pady=5)
        self.txt_entry.insert(0, "")
        self.txt_entry.bind("<KeyRelease>", lambda e: self._update_text_preview())

        ttk.Label(self.panel_content, text="字号:").pack(anchor=tk.W)
        self.font_scale = ttk.Scale(self.panel_content, from_=10, to=200, value=50)
        self.font_scale.pack(fill=tk.X)
        self.font_scale.bind("<B1-Motion>", lambda e: self._update_text_preview())  # 实时更新预览

        ttk.Label(self.panel_content, text="透明度:").pack(anchor=tk.W)
        self.alpha_scale = ttk.Scale(self.panel_content, from_=0, to=255, value=180)
        self.alpha_scale.pack(fill=tk.X)
        self.alpha_scale.bind("<B1-Motion>", lambda e: self._update_text_preview())  # 实时更新预览

        ttk.Button(self.panel_content, text="选择颜色", command=self._pick_text_color).pack(fill=tk.X, pady=5)
        self.text_color = "#ffffff"

        # 添加更多水印样式选项
        ttk.Label(self.panel_content, text="描边宽度:").pack(anchor=tk.W, pady=(10, 0))
        self.stroke_width_scale = ttk.Scale(self.panel_content, from_=0, to=10, value=2)
        self.stroke_width_scale.pack(fill=tk.X)
        self.stroke_width_scale.bind("<B1-Motion>", lambda e: self._update_text_preview())

        ttk.Button(self.panel_content, text="选择描边颜色", command=self._pick_stroke_color).pack(fill=tk.X, pady=5)
        self.stroke_color = "#000000"

        ttk.Button(self.panel_content, text="✔ 添加到图片", command=self._apply_text_watermark).pack(pady=20, fill=tk.X)
        ttk.Label(self.panel_content, text="* 可直接拖动文字调整位置", foreground="#888888").pack()
        ttk.Label(self.panel_content, text="* 右键点击水印可删除", foreground="#888888").pack()

        # 初始化文字水印实例
        if self.editing_image:
            self.text_watermark = DraggableTextWatermark(self.editing_image.copy())
            self._update_text_preview()
            # 绑定事件
            self.canvas.bind("<ButtonPress-1>", self._text_drag_start)
            self.canvas.bind("<B1-Motion>", self._text_drag_move)
            self.canvas.bind("<ButtonRelease-1>", self._text_drag_end)
            # 绑定右键点击事件
            self.canvas.bind("<ButtonPress-3>", self._text_right_click)
            
        # 水印删除相关变量
        self.show_delete_button = False
        self.delete_button = None
        self.delete_button_rect = None

    def _pick_text_color(self):
        c = colorchooser.askcolor(color=self.text_color)[1]
        if c: 
            self.text_color = c
            self._update_text_preview()

    def _pick_stroke_color(self):
        """选择描边颜色"""
        c = colorchooser.askcolor(color=self.stroke_color)[1]
        if c: 
            self.stroke_color = c
            self._update_text_preview()

    def _update_text_preview(self):
        if not self.editing_image:
            return
        
        # 创建新的水印对象，基于当前编辑图像
        is_time_watermark = self.watermark_type.get() == "time"
        self.text_watermark = DraggableTextWatermark(self.editing_image.copy(), is_time_watermark)
        
        # 如果是文字水印，获取输入的文字
        if not is_time_watermark:
            text = self.txt_entry.get()
            # 空文字时不显示任何内容
            self.text_watermark.set_text(text)
        
        # 设置水印样式
        font_size = int(self.font_scale.get())
        alpha = int(self.alpha_scale.get())
        stroke_width = int(self.stroke_width_scale.get())
        
        # 将十六进制颜色转换为RGB
        r = int(self.text_color[1:3], 16)
        g = int(self.text_color[3:5], 16)
        b = int(self.text_color[5:7], 16)
        text_color_rgb = (r, g, b)
        
        # 将描边颜色转换为RGB
        sr = int(self.stroke_color[1:3], 16)
        sg = int(self.stroke_color[3:5], 16)
        sb = int(self.stroke_color[5:7], 16)
        stroke_color_rgb = (sr, sg, sb)
        
        # 设置完整样式
        self.text_watermark.set_style(text_color_rgb, font_size, alpha, stroke_color_rgb, stroke_width)
        
        # 绑定拖动事件，确保新创建的水印可以被拖动
        self.canvas.bind("<ButtonPress-1>", self._text_drag_start)
        self.canvas.bind("<B1-Motion>", self._text_drag_move)
        self.canvas.bind("<ButtonRelease-1>", self._text_drag_end)
        
        # 更新预览
        self._update_canvas()
        
        # 隐藏删除按钮
        if self.show_delete_button:
            self._hide_delete_button()
    # 替换你的水印拖动事件（这部分负责拖动逻辑，保证无跳动、不卡顿）
    def _text_drag_start(self, event):
        if not self.text_watermark:
            return

        # 记录鼠标与文字位置的偏移（为了防止跳动）
        px, py = self._screen_to_image(event.x, event.y)
        if px is None:
            return

        # 获取水印的边界框
        bbox = self.text_watermark.get_bbox()
        # 计算水印的实际宽度和高度
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        # 计算水印的实际边界
        x1 = self.text_watermark.x
        y1 = self.text_watermark.y
        x2 = x1 + w
        y2 = y1 + h
        
        # 判断鼠标是否在水印框内
        if not (x1 <= px <= x2 and y1 <= py <= y2):
            return
        
        self.is_dragging_text = True
        self.canvas.config(cursor="fleur")

        self.drag_offset_x = px - self.text_watermark.x
        self.drag_offset_y = py - self.text_watermark.y

    def _text_drag_move(self, event):
        if not self.is_dragging_text:
            return

        px, py = self._screen_to_image(event.x, event.y)
        if px is None:
            return

        # 实时移动
        self.text_watermark.move_to(px - self.drag_offset_x,
                                    py - self.drag_offset_y)

        # 只更新水印，不重绘整个图片
        self.preview_image = self.text_watermark.apply()
        self._update_canvas()

    def _text_drag_end(self, event):
        self.is_dragging_text = False
        self.canvas.config(cursor="")
        # 检查text_watermark是否存在
        if self.text_watermark:
            self.preview_image = self.text_watermark.apply()
            self._update_canvas()

    # 右键点击 → 显示 ❌ 删除按钮
    def _text_right_click(self, event):
        """右键点击水印：显示删除按钮 ❌"""
        if not self.text_watermark:
            return

        # 检查是否点中了水印区域
        px, py = self._screen_to_image(event.x, event.y)
        if px is None:
            return

        bbox = self.text_watermark.get_bbox()
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]

        # 判断点击是否落在文字内
        if not (self.text_watermark.x <= px <= self.text_watermark.x + w and
                self.text_watermark.y <= py <= self.text_watermark.y + h):
            return

        # 显示删除按钮
        self._show_delete_button()

    def _show_delete_button(self):
        """在水印右上角绘制 ❌ 按钮"""
        self._hide_delete_button()

        if not self.text_watermark:
            return

        bbox = self.text_watermark.get_bbox()
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]

        # 计算水印中心映射到画布位置
        sx, sy = self._image_to_screen(self.text_watermark.x + w,
                                       self.text_watermark.y)

        btn_size = 22

        # 画圆
        self.del_btn_circle = self.canvas.create_oval(
            sx, sy - btn_size,
                sx + btn_size, sy,
            fill="#ff4444", outline="white", width=2, tags="del_btn"
        )

        # 写 ❌
        self.del_btn_text = self.canvas.create_text(
            sx + btn_size // 2, sy - btn_size // 2,
            text="×", fill="white", font=("Arial", 15, "bold"), tags="del_btn"
        )

        self.canvas.tag_bind("del_btn", "<Button-1>", self._delete_watermark)
    # 隐藏删除按钮
    def _hide_delete_button(self):
        self.canvas.delete("del_btn")
    # 删除水印
    def _delete_watermark(self, event=None):
        """真正删除水印"""
        self.text_watermark = None
        self.preview_image = self.editing_image.copy()
        self._hide_delete_button()
        self._update_canvas()


    def _apply_text_watermark(self):
        if not self.editing_image or not self.text_watermark:
            return
        self._push_history()
        
        # 将水印应用到编辑图像
        self.editing_image = self.text_watermark.apply()
        
        # 更新预览图像为编辑图像的副本，此时已经包含了固定的水印
        self.preview_image = self.editing_image.copy()
        
        # 关键修复：清除text_watermark对象
        # 这样就不会在原位置拖动时出现复制水印的问题
        # 只有当用户开始编辑新水印时，才会重新创建text_watermark对象
        self.text_watermark = None
        
        # 确保当前工具仍然是text，但此时没有活跃的水印对象
        self.current_tool = "text"
        
        self._update_canvas()
        
        # 解绑拖动事件，避免在没有水印时触发
        self.canvas.unbind("<ButtonPress-1>")
        self.canvas.unbind("<B1-Motion>")
        self.canvas.unbind("<ButtonRelease-1>")

    # 添加两个坐标转换函数（非常重要，保证拖动、删除按钮准确）
    def _screen_to_image(self, sx, sy):
        """将屏幕坐标转换为图片像素坐标"""
        if not self.preview_image:
            return None, None

        cw = self.canvas.winfo_width() // 2 + self.pan_offset_x
        ch = self.canvas.winfo_height() // 2 + self.pan_offset_y

        iw = self.editing_image.width * self.zoom_scale
        ih = self.editing_image.height * self.zoom_scale

        lx = cw - iw / 2
        ly = ch - ih / 2

        if not (lx <= sx <= lx + iw and ly <= sy <= ly + ih):
            return None, None

        px = (sx - lx) / self.zoom_scale
        py = (sy - ly) / self.zoom_scale
        return px, py

    def _image_to_screen(self, px, py):
        """图片像素坐标 → 屏幕坐标"""
        cw = self.canvas.winfo_width() // 2 + self.pan_offset_x
        ch = self.canvas.winfo_height() // 2 + self.pan_offset_y

        sx = cw - (self.editing_image.width * self.zoom_scale) / 2 + px * self.zoom_scale
        sy = ch - (self.editing_image.height * self.zoom_scale) / 2 + py * self.zoom_scale
        return sx, sy

    # --- 5. 涂鸦/马赛克 (新实现) ---
    def _build_doodle_panel(self):
        # 笔刷大小
        ttk.Label(self.panel_content, text="笔刷大小:").pack(anchor=tk.W, pady=(10, 0))
        self.brush_size_scale = ttk.Scale(self.panel_content, from_=5, to=100, value=20)
        self.brush_size_scale.pack(fill=tk.X)

        # 画笔颜色
        ttk.Button(self.panel_content, text="选择颜色", command=self._pick_brush_color).pack(fill=tk.X, pady=5)
        self.brush_color = "#ff0000"

        ttk.Button(self.panel_content, text="✔ 结束绘制", command=lambda: self._finish_doodle()).pack(pady=20,
                                                                                                          fill=tk.X)
        ttk.Label(self.panel_content, text="* 绘制过程中可撤销", foreground="#888888").pack()

        # 初始化涂鸦编辑器（只在进入涂鸦模式时初始化一次）
        if self.editing_image:
            self.doodle_editor = DoodleEditor(self.editing_image.copy())
        else:
            # 如果没有打开图片，创建一个默认的编辑器实例
            self.doodle_editor = None
        
        # 激活绘制
        self.canvas.config(cursor="dot")
        self.canvas.bind("<ButtonPress-1>", self._doodle_start)
        self.canvas.bind("<B1-Motion>", self._doodle_draw)
        self.canvas.bind("<ButtonRelease-1>", self._doodle_end)
        self.last_draw_pos = None

    def _pick_brush_color(self):
        c = colorchooser.askcolor(color=self.brush_color)[1]
        if c: self.brush_color = c

    def _doodle_start(self, event):
        if not self.editing_image or not self.doodle_editor:
            return
        
        self.last_draw_pos = (event.x, event.y)
        # 初始化点列表，用于存储绘制路径点
        self.draw_points = []
        
        # 将第一个点转换为图片坐标并添加到点列表
        cx = self.canvas.winfo_width() // 2 + self.pan_offset_x
        cy = self.canvas.winfo_height() // 2 + self.pan_offset_y
        current_w = int(self.editing_image.width * self.zoom_scale)
        current_h = int(self.editing_image.height * self.zoom_scale)
        img_x1 = cx - current_w // 2
        img_y1 = cy - current_h // 2
        
        x = (event.x - img_x1) / self.zoom_scale
        y = (event.y - img_y1) / self.zoom_scale
        self.draw_points.append((x, y))

    def _doodle_draw(self, event):
        if not self.last_draw_pos or not self.editing_image or not self.doodle_editor:
            return

        # 第一次绘制时保存历史记录
        if len(self.draw_points) == 1:
            self._push_history()

        # 转换屏幕坐标到图片坐标
        cx = self.canvas.winfo_width() // 2 + self.pan_offset_x
        cy = self.canvas.winfo_height() // 2 + self.pan_offset_y
        current_w = int(self.editing_image.width * self.zoom_scale)
        current_h = int(self.editing_image.height * self.zoom_scale)
        img_x1 = cx - current_w // 2
        img_y1 = cy - current_h // 2

        # 计算实际图片坐标
        x = (event.x - img_x1) / self.zoom_scale
        y = (event.y - img_y1) / self.zoom_scale
        
        # 添加当前点到点列表
        self.draw_points.append((x, y))
        
        # 设置画笔属性
        brush_size = int(self.brush_size_scale.get())
        # 将十六进制颜色转换为RGBA
        r = int(self.brush_color[1:3], 16)
        g = int(self.brush_color[3:5], 16)
        b = int(self.brush_color[5:7], 16)
        color = (r, g, b, 255)
        
        self.doodle_editor.set_brush(brush_size, color)
        
        # 当有足够的点时，使用平滑算法绘制
        if len(self.draw_points) > 2:
            # 使用贝塞尔曲线平滑绘制
            self._draw_smooth_path()
        
        # 更新预览
        self.preview_image = self.doodle_editor.merge()
        self._update_canvas()

        self.last_draw_pos = (event.x, event.y)
    
    def _draw_smooth_path(self):
        """使用贝塞尔曲线绘制平滑路径"""
        if len(self.draw_points) < 3:
            return
        
        points = self.draw_points[-4:] if len(self.draw_points) >= 4 else self.draw_points
        
        # 获取画笔属性
        brush_size = int(self.brush_size_scale.get())
        r = int(self.brush_color[1:3], 16)
        g = int(self.brush_color[3:5], 16)
        b = int(self.brush_color[5:7], 16)
        color = (r, g, b, 255)
        
        # 使用Catmull-Rom样条曲线平滑
        for i in range(len(points) - 1):
            if i == 0 and len(points) > 2:
                # 第一个线段，使用前三个点计算控制点
                p0 = points[i]
                p1 = points[i+1]
                p2 = points[i+2]
                
                # 计算控制点
                cp1 = (p1[0] + (p2[0] - p0[0]) * 0.1, p1[1] + (p2[1] - p0[1]) * 0.1)
                cp2 = (p1[0] + (p2[0] - p0[0]) * 0.1, p1[1] + (p2[1] - p0[1]) * 0.1)
            elif i == len(points) - 2 and len(points) > 2:
                # 最后一个线段，使用最后三个点计算控制点
                p0 = points[i-1]
                p1 = points[i]
                p2 = points[i+1]
                
                # 计算控制点
                cp1 = (p1[0] + (p2[0] - p0[0]) * 0.1, p1[1] + (p2[1] - p0[1]) * 0.1)
                cp2 = (p1[0] + (p2[0] - p0[0]) * 0.1, p1[1] + (p2[1] - p0[1]) * 0.1)
            else:
                # 中间线段，使用前后两个点计算控制点
                p_prev = points[i-1] if i > 0 else points[i]
                p_current = points[i]
                p_next = points[i+1]
                p_next_next = points[i+2] if i+2 < len(points) else points[i+1]
                
                # 计算控制点，使用张力参数控制平滑程度
                tension = 0.5
                cp1 = (p_current[0] + (p_next[0] - p_prev[0]) * tension * 0.1,
                       p_current[1] + (p_next[1] - p_prev[1]) * tension * 0.1)
                cp2 = (p_next[0] - (p_next_next[0] - p_current[0]) * tension * 0.1,
                       p_next[1] - (p_next_next[1] - p_current[1]) * tension * 0.1)
            
            # 使用贝塞尔曲线绘制
            self._draw_bezier(points[i], cp1, cp2, points[i+1], color, brush_size)
    
    def _draw_bezier(self, p0, cp1, cp2, p3, color, width):
        """绘制贝塞尔曲线"""
        # 计算贝塞尔曲线上的点
        steps = 10  # 曲线分段数
        for t in range(steps):
            t0 = t / steps
            t1 = t0 + 1 / steps
            
            # 使用贝塞尔曲线公式计算点
            x0 = self._bezier_point(p0[0], cp1[0], cp2[0], p3[0], t0)
            y0 = self._bezier_point(p0[1], cp1[1], cp2[1], p3[1], t0)
            x1 = self._bezier_point(p0[0], cp1[0], cp2[0], p3[0], t1)
            y1 = self._bezier_point(p0[1], cp1[1], cp2[1], p3[1], t1)
            
            # 绘制小段直线
            self.doodle_editor.draw.line((x0, y0, x1, y1), fill=color, width=width)
    
    def _bezier_point(self, p0, cp1, cp2, p3, t):
        """计算贝塞尔曲线上的单个点"""
        return (1-t)**3 * p0 + 3*(1-t)**2 * t * cp1 + 3*(1-t)*t**2 * cp2 + t**3 * p3

    def _doodle_end(self, event):
        if not self.editing_image or not self.doodle_editor:
            return
        
        # 绘制结束，处理剩余的点
        if len(self.draw_points) > 1:
            # 使用贝塞尔曲线平滑绘制剩余路径
            self._draw_smooth_path()
        
        # 更新预览和编辑图像，使绘制痕迹永久保留
        self.preview_image = self.doodle_editor.merge()
        self.editing_image = self.preview_image.copy()
        self._update_canvas()
        # 涂鸦时隐藏删除按钮
        self._hide_delete_button()
        # 清空点列表
        self.draw_points = []

    def _build_mosaic_panel(self):
        # 马赛克类型选择
        ttk.Label(self.panel_content, text="马赛克类型:").pack(anchor=tk.W)
        self.mosaic_type = tk.StringVar(value="pixel")
        type_frame = tk.Frame(self.panel_content, bg=COLORS["bg_panel"])
        type_frame.pack(fill=tk.X, pady=5)
        
        # 添加不同类型的马赛克选项
        ttk.Radiobutton(type_frame, text="像素化", variable=self.mosaic_type, value="pixel").pack(anchor=tk.W, pady=2)
        ttk.Radiobutton(type_frame, text="模糊", variable=self.mosaic_type, value="blur").pack(anchor=tk.W, pady=2)
        ttk.Radiobutton(type_frame, text="三角形", variable=self.mosaic_type, value="triangle").pack(anchor=tk.W, pady=2)

        # 马赛克大小
        ttk.Label(self.panel_content, text="马赛克大小:").pack(anchor=tk.W, pady=(10, 0))
        self.mosaic_size_scale = ttk.Scale(self.panel_content, from_=10, to=200, value=50)
        self.mosaic_size_scale.pack(fill=tk.X)

        ttk.Button(self.panel_content, text="✔ 结束马赛克", command=lambda: self._finish_mosaic()).pack(pady=20,
                                                                                                          fill=tk.X)
        ttk.Label(self.panel_content, text="* 绘制过程中可撤销", foreground="#888888").pack()

        # 初始化马赛克编辑器
        if self.editing_image:
            self.mosaic_editor = MosaicEditor(self.editing_image.copy())
        else:
            self.mosaic_editor = None
        
        # 激活绘制
        self.canvas.config(cursor="dot")
        self.canvas.bind("<ButtonPress-1>", self._mosaic_start)
        self.canvas.bind("<B1-Motion>", self._mosaic_draw)
        self.canvas.bind("<ButtonRelease-1>", self._mosaic_end)
        self.last_mosaic_pos = None
    
    def _mosaic_start(self, event):
        if not self.editing_image or not self.mosaic_editor:
            return
        
        self.last_mosaic_pos = (event.x, event.y)
        # 保存当前状态到历史记录
        self._push_history()
    
    def _mosaic_draw(self, event):
        if not self.last_mosaic_pos or not self.editing_image or not self.mosaic_editor:
            return

        # 转换屏幕坐标到图片坐标
        cx = self.canvas.winfo_width() // 2 + self.pan_offset_x
        cy = self.canvas.winfo_height() // 2 + self.pan_offset_y
        current_w = int(self.editing_image.width * self.zoom_scale)
        current_h = int(self.editing_image.height * self.zoom_scale)
        img_x1 = cx - current_w // 2
        img_y1 = cy - current_h // 2

        # 计算实际图片坐标
        x = (event.x - img_x1) / self.zoom_scale
        y = (event.y - img_y1) / self.zoom_scale
        
        # 设置马赛克参数
        mosaic_size = int(self.mosaic_size_scale.get())
        mosaic_type = self.mosaic_type.get()
        self.mosaic_editor.set_mosaic_params(mosaic_size, mosaic_type)
        
        # 应用马赛克
        self.mosaic_editor.apply_mosaic_area(x, y)
        
        # 更新预览
        self.preview_image = self.mosaic_editor.merge()
        self._update_canvas()

        self.last_mosaic_pos = (event.x, event.y)
    
    def _mosaic_end(self, event):
        if not self.editing_image:
            return
        
        # 更新编辑图像，使马赛克痕迹永久保留
        self.editing_image = self.preview_image.copy()
        self._update_canvas()
        # 清空上次位置
        self.last_mosaic_pos = None
    
    def _finish_doodle(self):
        # 结束涂鸦绘制，切换到调整面板
        self._hide_delete_button()
        self.show_panel("adjust")
    
    def _finish_mosaic(self):
        # 结束马赛克绘制，切换到调整面板
        self._hide_delete_button()
        self.show_panel("adjust")


if __name__ == "__main__":
    # 高分屏适配
    try:
        from ctypes import windll

        windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass

    app = ModernEditor()

    app.mainloop()
