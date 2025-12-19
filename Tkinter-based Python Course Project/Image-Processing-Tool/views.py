import tkinter as tk
from tkinter import ttk
from config import COLORS
from PIL import Image, ImageTk
import os

class ModernEditorView(tk.Tk):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.title("ProEditor")
        self.geometry("1280x800")
        self.configure(bg=COLORS["bg_main"])
        
        # Canvas用的ImageTk对象
        self.tk_image = None
        
        # UI 初始化
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
        self._create_header_btn(header, "📂 打开图片", self.controller.open_image)
        self._create_header_btn(header, "💾 保存", self._save_image)
        self._create_header_btn(header, "🔄 重命名", self._rename_image)
        self._create_header_btn(header, "↩ 撤销 (Ctrl+Z)", self._undo)
        self._create_header_btn(header, "↪ 重做 (Ctrl+Y)", self._redo)
        self._create_header_btn(header, "✨ 自动优化", self._auto_enhance)
        self._create_header_btn(header, "🔄 批量转换格式", self._batch_convert_format)
        self._create_header_btn(header, "🔖 批量添加水印", self._batch_add_watermark)

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
        self._add_sidebar_tool("添加\n贴纸", "sticker", lambda: self.show_panel("sticker"))

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
                        bd=0, activebackground=COLORS["accent"], height=3, font= ("Segoe UI", 11, "bold"))
        btn.pack(fill=tk.X, pady=1)
    
    def _bind_events(self):
        # 窗口改变大小
        self.canvas.bind("<Configure>", lambda e: self.controller._update_canvas())
        # 鼠标滚轮缩放
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind("<Button-4>", self._on_mousewheel)
        self.canvas.bind("<Button-5>", self._on_mousewheel)
        # 右键拖拽画布
        self.canvas.bind("<ButtonPress-3>", self._on_pan_start)
        self.canvas.bind("<B3-Motion>", self._on_pan_move)
        # 快捷键
        self.bind("<Control-z>", lambda e: self._undo())
        self.bind("<Control-y>", lambda e: self._redo())
        self.bind("<Control-s>", lambda e: self._save_image())
    
    def show_panel(self, tool_name):
        """切换右侧面板内容"""
        # 如果从其他工具切换过来，先应用更改
        self.controller._apply_pending_changes()

        self.controller.current_tool = tool_name
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
            "crop": "裁剪构图", "text": "添加水印", "doodle": "画笔涂鸦", "mosaic": "马赛克工具",
            "sticker": "贴纸"
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
        elif tool_name == "sticker":
            self._build_sticker_panel()
    
    # 面板构建方法
    def _build_adjust_panel(self):
        """构建调节滑块"""
        self._create_slider("亮度", "brightness", 0.5, 1.5)
        self._create_slider("对比度", "contrast", 0.5, 1.5)
        self._create_slider("饱和度", "saturation", 0.0, 2.0)
        self._create_slider("锐化", "sharpness", 0.0, 2.0)

        ttk.Button(self.panel_content, text="应用调节", command=self.controller._apply_adjust).pack(pady=20, fill=tk.X)
        ttk.Label(self.panel_content, text="* 拖动滑块实时预览", foreground="#888888").pack()

    def _create_slider(self, label, param_key, min_v, max_v):
        frame = tk.Frame(self.panel_content, bg=COLORS["bg_panel"])
        frame.pack(fill=tk.X, pady=5)

        ttk.Label(frame, text=label).pack(anchor=tk.W)
        scale = ttk.Scale(frame, from_=min_v, to=max_v, value=self.controller.temp_adjustments[param_key],
                          command=lambda v: self.controller._on_adjust_change(param_key, float(v)))
        scale.pack(fill=tk.X)
    
    def _build_filter_panel(self):
        """构建滤镜面板"""
        # 内置滤镜
        ttk.Label(self.panel_content, text="内置滤镜:").pack(anchor=tk.W, pady=5)
        filters = ["原始", "黑白", "怀旧", "模糊", "浮雕", "轮廓"]
        for f in filters:
            btn = tk.Button(self.panel_content, text=f, bg=COLORS["bg_tool"], fg="white",
                            command=lambda mode=f: self.controller._apply_filter_preview(mode))
            btn.pack(fill=tk.X, pady=2)
        
        # LUT滤镜
        ttk.Separator(self.panel_content, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
        ttk.Label(self.panel_content, text="LUT滤镜:").pack(anchor=tk.W, pady=5)
        ttk.Button(self.panel_content, text="选择LUT文件", command=self.controller._load_lut_file).pack(fill=tk.X, pady=5)
        ttk.Label(self.panel_content, text="* 支持 .cube 或 .png 格式", foreground="#888888").pack()

        ttk.Button(self.panel_content, text="✔ 确认应用", command=self.controller._confirm_filter).pack(pady=20, fill=tk.X)
        ttk.Label(self.panel_content, text="* 实时预览效果", foreground="#888888").pack()
    
    def _build_crop_panel(self):
        """构建裁剪面板"""
        ttk.Label(self.panel_content, text="裁剪比例:").pack(anchor=tk.W)
        
        # 裁剪比例按钮组
        ratio_frame = tk.Frame(self.panel_content, bg=COLORS["bg_panel"])
        ratio_frame.pack(fill=tk.X, pady=5)
        
        # 比例选项列表
        ratios = ["自由", "1:1", "4:3", "3:4", "16:9", "9:16"]
        self.controller.selected_ratio = tk.StringVar(value="自由")
        
        # 使用更灵活的布局，允许选项自动换行
        for i, ratio in enumerate(ratios):
            btn = ttk.Radiobutton(ratio_frame, text=ratio, variable=self.controller.selected_ratio, value=ratio, 
                                 command=self.controller._update_crop_ratio)
            btn.grid(row=i//3, column=i%3, padx=5, pady=2, sticky=tk.W)
        
        # 确保框架能够根据内容调整大小
        ratio_frame.grid_columnconfigure(0, weight=1)
        ratio_frame.grid_columnconfigure(1, weight=1)
        ratio_frame.grid_columnconfigure(2, weight=1)
        
        # 添加旋转和翻转按钮组
        ttk.Label(self.panel_content, text="旋转/翻转:").pack(anchor=tk.W, pady=(10, 0))
        rotate_frame = tk.Frame(self.panel_content, bg=COLORS["bg_panel"])
        rotate_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(rotate_frame, text="左旋转90°", command=self.controller._rotate_left).pack(side=tk.LEFT, padx=3, fill=tk.X, expand=True)
        ttk.Button(rotate_frame, text="右旋转90°", command=self.controller._rotate_right).pack(side=tk.LEFT, padx=3, fill=tk.X, expand=True)
        ttk.Button(rotate_frame, text="左右翻转", command=self.controller._flip_horizontal).pack(side=tk.LEFT, padx=3, fill=tk.X, expand=True)
        ttk.Button(rotate_frame, text="上下翻转", command=self.controller._flip_vertical).pack(side=tk.LEFT, padx=3, fill=tk.X, expand=True)
        
        # 添加自定义旋转角度控制
        ttk.Label(self.panel_content, text="旋转角度:").pack(anchor=tk.W, pady=(10, 0))
        rotate_angle_frame = tk.Frame(self.panel_content, bg=COLORS["bg_panel"])
        rotate_angle_frame.pack(fill=tk.X, pady=5)
        
        self.controller.rotate_angle_var = tk.IntVar(value=0)
        
        # 旋转角度滑块
        angle_scale = ttk.Scale(rotate_angle_frame, from_=0, to=360, variable=self.controller.rotate_angle_var, 
                               command=lambda v: self.controller._on_rotate_angle_change())
        angle_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=3)
        
        # 旋转角度输入框
        angle_entry = ttk.Entry(rotate_angle_frame, textvariable=self.controller.rotate_angle_var, width=5)
        angle_entry.pack(side=tk.LEFT, padx=3)
        
        # 旋转角度应用按钮
        ttk.Button(rotate_angle_frame, text="旋转", command=self.controller._rotate_by_angle).pack(side=tk.LEFT, padx=3)
        
        ttk.Button(self.panel_content, text="开始/重置裁剪框", command=self.controller._init_crop_tool).pack(fill=tk.X, pady=5)
        ttk.Button(self.panel_content, text="恢复原始图像", command=self.controller._restore_original).pack(fill=tk.X, pady=5)
        ttk.Button(self.panel_content, text="✔ 确认裁剪", command=self.controller._do_crop).pack(fill=tk.X, pady=20)
    
    def _build_text_panel(self):
        """构建文字水印面板"""
        # 水印类型选择
        ttk.Label(self.panel_content, text="水印类型:").pack(anchor=tk.W)
        self.controller.watermark_type = tk.StringVar(value="text")
        type_frame = tk.Frame(self.panel_content, bg=COLORS["bg_panel"])
        type_frame.pack(fill=tk.X, pady=5)
        
        # 添加水印类型切换事件
        def on_watermark_type_change():
            # 始终显示文字输入框，不受水印类型影响
            self.controller._update_text_preview()
        
        ttk.Radiobutton(type_frame, text="文字水印", variable=self.controller.watermark_type, value="text", command=on_watermark_type_change).pack(side=tk.LEFT, padx=3)
        ttk.Radiobutton(type_frame, text="时间水印", variable=self.controller.watermark_type, value="time", command=on_watermark_type_change).pack(side=tk.LEFT, padx=3)

        # 文字输入
        text_entry = ttk.Entry(self.panel_content)
        text_entry.pack(fill=tk.X, pady=5)
        text_entry.insert(0, "")
        # 保存引用，供控制器访问
        self.controller.watermark_text_var = text_entry
        # 绑定键盘事件，实时更新预览
        text_entry.bind("<KeyRelease>", lambda e: self.controller._update_text_preview())
        
        # 字体大小
        ttk.Label(self.panel_content, text="字号:").pack(anchor=tk.W)
        self.controller.watermark_size_var = tk.IntVar(value=50)
        size_scale = ttk.Scale(self.panel_content, from_=10, to=200, variable=self.controller.watermark_size_var, orient=tk.HORIZONTAL)
        size_scale.pack(fill=tk.X)
        # 绑定拖动事件，实时更新预览
        size_scale.bind("<B1-Motion>", lambda e: self.controller._update_text_preview())
        
        # 透明度
        ttk.Label(self.panel_content, text="透明度:").pack(anchor=tk.W)
        self.controller.watermark_alpha_var = tk.IntVar(value=180)
        alpha_scale = ttk.Scale(self.panel_content, from_=0, to=255, variable=self.controller.watermark_alpha_var, orient=tk.HORIZONTAL)
        alpha_scale.pack(fill=tk.X)
        # 绑定拖动事件，实时更新预览
        alpha_scale.bind("<B1-Motion>", lambda e: self.controller._update_text_preview())
        
        # 颜色选择
        ttk.Button(self.panel_content, text="选择颜色", command=self.controller._choose_watermark_color).pack(fill=tk.X, pady=5)
        self.controller.watermark_color = (255, 255, 255)
        
        # 描边宽度
        ttk.Label(self.panel_content, text="描边宽度:").pack(anchor=tk.W, pady=(10, 0))
        self.controller.watermark_stroke_width_var = tk.IntVar(value=2)
        stroke_width_scale = ttk.Scale(self.panel_content, from_=0, to=10, variable=self.controller.watermark_stroke_width_var, orient=tk.HORIZONTAL)
        stroke_width_scale.pack(fill=tk.X)
        # 绑定拖动事件，实时更新预览
        stroke_width_scale.bind("<B1-Motion>", lambda e: self.controller._update_text_preview())
        
        # 描边颜色选择
        ttk.Button(self.panel_content, text="选择描边颜色", command=self.controller._choose_stroke_color).pack(fill=tk.X, pady=5)
        self.controller.watermark_stroke_color = (0, 0, 0)
        
        # 添加水印按钮
        ttk.Button(self.panel_content, text="✔ 添加到图片", command=self.controller._add_text_watermark).pack(pady=20, fill=tk.X)
        ttk.Label(self.panel_content, text="* 可直接拖动文字调整位置", foreground="#888888").pack()
        ttk.Label(self.panel_content, text="* 右键点击水印可删除", foreground="#888888").pack()
        
        # 初始化文字水印实例并绑定事件
        if self.controller.editing_image:
            self.controller._update_text_preview()
            # 绑定事件
            self.canvas.bind("<ButtonPress-1>", self.controller._on_text_watermark_press)
            self.canvas.bind("<B1-Motion>", self.controller._on_text_watermark_drag)
            self.canvas.bind("<ButtonRelease-1>", self.controller._on_text_watermark_release)
            # 绑定右键点击事件
            self.canvas.bind("<ButtonPress-3>", self.controller._on_text_watermark_right_click)
    
    def _build_doodle_panel(self):
        """构建涂鸦面板"""
        # 大小
        ttk.Label(self.panel_content, text="大小:").pack(anchor=tk.W, pady=5)
        self.controller.doodle_size_var = tk.IntVar(value=20)
        size_scale = ttk.Scale(self.panel_content, from_=1, to=100, variable=self.controller.doodle_size_var, orient=tk.HORIZONTAL, 
                              command=lambda v: self.controller._on_doodle_size_change(float(v)))
        size_scale.pack(fill=tk.X, pady=5)
        
        # 绘制模式
        ttk.Label(self.panel_content, text="绘制模式:").pack(anchor=tk.W, pady=5)
        self.controller.doodle_mode = tk.StringVar(value="brush")
        mode_frame = tk.Frame(self.panel_content, bg=COLORS["bg_panel"])
        mode_frame.pack(fill=tk.X, pady=5)
        brush_radio = ttk.Radiobutton(mode_frame, text="笔刷", variable=self.controller.doodle_mode, value="brush", command=self.controller._on_doodle_mode_change)
        brush_radio.pack(side=tk.LEFT, padx=5)
        eraser_radio = ttk.Radiobutton(mode_frame, text="橡皮擦", variable=self.controller.doodle_mode, value="eraser", command=self.controller._on_doodle_mode_change)
        eraser_radio.pack(side=tk.LEFT, padx=5)
        
        # 选择颜色按钮
        tk.Button(self.panel_content, text="选择颜色", bg=COLORS["bg_tool"], fg="white", 
                 command=self.controller._choose_doodle_color).pack(fill=tk.X, pady=10)
        self.controller.doodle_color = (255, 0, 0)
        
        # 结束绘制按钮
        tk.Button(self.panel_content, text="✔ 结束绘制", bg=COLORS["accent"], fg="white", 
                 command=self.controller._apply_doodle).pack(fill=tk.X, pady=20)
        ttk.Label(self.panel_content, text="* 绘制过程中可撤销", foreground="#888888").pack()
        
        # 初始化涂鸦工具
        if self.controller.editing_image:
            self.controller._init_doodle_tool()
    
    def _build_mosaic_panel(self):
        """构建马赛克面板"""
        # 马赛克类型选择
        ttk.Label(self.panel_content, text="马赛克类型:").pack(anchor=tk.W)
        self.controller.mosaic_type_var = tk.StringVar(value="pixel")
        type_frame = tk.Frame(self.panel_content, bg=COLORS["bg_panel"])
        type_frame.pack(fill=tk.X, pady=5)
        
        # 只保留像素化和模糊两种类型
        ttk.Radiobutton(type_frame, text="像素化", variable=self.controller.mosaic_type_var, value="pixel", command=self.controller._on_mosaic_type_change).pack(anchor=tk.W, pady=2)
        ttk.Radiobutton(type_frame, text="模糊", variable=self.controller.mosaic_type_var, value="blur", command=self.controller._on_mosaic_type_change).pack(anchor=tk.W, pady=2)

        # 马赛克大小
        ttk.Label(self.panel_content, text="马赛克大小:").pack(anchor=tk.W, pady=(10, 0))
        self.controller.mosaic_size_var = tk.IntVar(value=50)
        size_scale = ttk.Scale(self.panel_content, from_=10, to=200, variable=self.controller.mosaic_size_var, orient=tk.HORIZONTAL, 
                              command=lambda v: self.controller._on_mosaic_size_change(float(v)))
        size_scale.pack(fill=tk.X)

        # 结束马赛克按钮
        ttk.Button(self.panel_content, text="✔ 结束马赛克", command=self.controller._apply_mosaic).pack(pady=20, fill=tk.X)
        ttk.Label(self.panel_content, text="* 绘制过程中可撤销", foreground="#888888").pack()

        # 初始化马赛克工具
        if self.controller.editing_image:
            self.controller._init_mosaic_tool()
    
    def _build_sticker_panel(self):
        """构建贴纸面板"""
        # 加载贴纸文件
        sticker_dir = os.path.join(os.path.dirname(__file__), "resources", "stickers")
        self.controller.sticker_files = [os.path.join(sticker_dir, f) for f in os.listdir(sticker_dir) 
                             if f.endswith((".png", ".jpg", ".jpeg", ".bmp"))]
        
        # 创建滚动条
        scroll_frame = ttk.Frame(self.panel_content)
        scroll_frame.pack(fill=tk.BOTH, expand=True)
        
        canvas = tk.Canvas(scroll_frame, bg=COLORS["bg_panel"])
        scrollbar = ttk.Scrollbar(scroll_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # 显示贴纸网格
        sticker_frame = ttk.Frame(scrollable_frame)
        sticker_frame.pack(pady=10)
        
        # 每行显示3个贴纸
        row = 0
        col = 0
        # 贴纸缩略图大小，确保完全在边界内
        thumb_size = (70, 70)
        
        for sticker_path in self.controller.sticker_files:
            try:
                # 加载贴纸图像，保持原始格式
                sticker_img = Image.open(sticker_path)
                
                # 保持贴纸原始尺寸比例，不进行过度缩放
                # 先计算合适的缩放比例，确保贴纸在保持清晰度的同时适应显示区域
                original_width, original_height = sticker_img.size
                
                # 计算缩放比例，确保贴纸不会被过度压缩
                scale = min(thumb_size[0] / original_width, thumb_size[1] / original_height)
                
                # 计算新尺寸，确保是整数
                new_width = int(original_width * scale)
                new_height = int(original_height * scale)
                
                # 使用高质量缩放算法，保持清晰度
                resized_sticker = sticker_img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                # 创建一个透明背景的新图像，用于居中显示贴纸
                new_img = Image.new('RGBA', thumb_size, (255, 255, 255, 0))
                
                # 计算居中位置
                x = (thumb_size[0] - new_width) // 2
                y = (thumb_size[1] - new_height) // 2
                
                # 将贴纸粘贴到居中位置，确保透明通道正确处理
                if resized_sticker.mode == 'RGBA':
                    new_img.paste(resized_sticker, (x, y), resized_sticker)
                else:
                    # 对于非透明图像，转换为RGBA模式
                    rgba_sticker = resized_sticker.convert('RGBA')
                    new_img.paste(rgba_sticker, (x, y), rgba_sticker)
                
                # 使用高质量渲染，提高显示清晰度
                sticker_tk = ImageTk.PhotoImage(new_img)
                
                # 创建贴纸按钮，增大按钮大小，添加边框效果
                sticker_btn = tk.Button(sticker_frame, image=sticker_tk, 
                                      bg=COLORS["bg_tool"], 
                                      bd=1, 
                                      relief="raised",
                                      highlightthickness=1,
                                      highlightbackground=COLORS["accent"],
                                      command=lambda path=sticker_path: self.controller._select_sticker(path))
                sticker_btn.image = sticker_tk  # 保存引用，防止被垃圾回收
                
                # 调整按钮大小和间距
                sticker_btn.grid(row=row, column=col, padx=3, pady=3, sticky="nsew")
                
                # 设置单元格大小，确保按钮大小一致
                sticker_frame.grid_columnconfigure(col, minsize=thumb_size[0]+10, uniform="sticker")
                sticker_frame.grid_rowconfigure(row, minsize=thumb_size[1]+10, uniform="sticker")
                
                col += 1
                if col >= 3:
                    col = 0
                    row += 1
            except Exception as e:
                # 忽略无法打开的贴纸文件
                print(f"无法加载贴纸文件 {sticker_path}: {e}")
                continue
        
        # 放置画布和滚动条
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        ttk.Label(self.panel_content, text="* 点击贴纸添加到图片，添加后可拖动调整位置", foreground="#888888").pack(pady=10)
        
        # 添加贴纸缩放控件
        scale_frame = ttk.Frame(self.panel_content)
        scale_frame.pack(fill=tk.X, pady=10)
        ttk.Label(scale_frame, text="贴纸大小：").pack(side=tk.LEFT, padx=5)
        self.sticker_scale_var = tk.DoubleVar(value=1.0)
        self.sticker_scale_slider = ttk.Scale(
            scale_frame,
            from_=0.1,
            to=3.0,
            orient=tk.HORIZONTAL,
            variable=self.sticker_scale_var,
            command=lambda val: self.controller._update_sticker_style(float(val), self.controller.sticker_rotation)
        )
        self.sticker_scale_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.sticker_scale_entry = ttk.Entry(scale_frame, width=6, textvariable=self.sticker_scale_var, justify=tk.CENTER)
        self.sticker_scale_entry.pack(side=tk.LEFT, padx=5)
        
        # 添加贴纸旋转控件
        rotate_frame = ttk.Frame(self.panel_content)
        rotate_frame.pack(fill=tk.X, pady=10)
        ttk.Label(rotate_frame, text="旋转角度：").pack(side=tk.LEFT, padx=5)
        self.sticker_rotation_var = tk.DoubleVar(value=0.0)
        self.sticker_rotation_slider = ttk.Scale(
            rotate_frame,
            from_=0,
            to=360,
            orient=tk.HORIZONTAL,
            variable=self.sticker_rotation_var,
            command=lambda val: self.controller._update_sticker_style(self.controller.sticker_scale, float(val))
        )
        self.sticker_rotation_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.sticker_rotation_entry = ttk.Entry(rotate_frame, width=6, textvariable=self.sticker_rotation_var, justify=tk.CENTER)
        self.sticker_rotation_entry.pack(side=tk.LEFT, padx=5)
        ttk.Label(rotate_frame, text="°").pack(side=tk.LEFT, padx=2)
        self.sticker_scale_entry.bind("<Return>", lambda e: self.controller._update_sticker_style(self.sticker_scale_var.get(), self.controller.sticker_rotation))
        self.sticker_scale_entry.bind("<FocusOut>", lambda e: self.controller._update_sticker_style(self.sticker_scale_var.get(), self.controller.sticker_rotation))
        self.sticker_rotation_entry.bind("<Return>", lambda e: self.controller._update_sticker_style(self.controller.sticker_scale, self.sticker_rotation_var.get()))
        self.sticker_rotation_entry.bind("<FocusOut>", lambda e: self.controller._update_sticker_style(self.controller.sticker_scale, self.sticker_rotation_var.get()))
        
        ttk.Button(self.panel_content, text="✔ 确认添加贴纸", command=self.controller._confirm_sticker).pack(fill=tk.X, pady=5)
        
        # 绑定画布事件，用于贴纸拖动和删除
        if self.controller.editing_image:
            self.canvas.bind("<ButtonPress-1>", self.controller._on_sticker_press)
            self.canvas.bind("<B1-Motion>", self.controller._on_sticker_drag)
            self.canvas.bind("<ButtonRelease-1>", self.controller._on_sticker_release)
            self.canvas.bind("<ButtonPress-3>", self.controller._on_sticker_right_click)
    
    # 事件处理方法
    def _on_mousewheel(self, event):
        if not self.controller.editing_image: return
        # Windows: event.delta, Linux: 4/5 buttons
        if event.num == 5 or event.delta < 0:
            self.controller.zoom_scale *= 0.9
        else:
            self.controller.zoom_scale *= 1.1
        self.controller._update_canvas()
    
    def _on_pan_start(self, event):
        self.controller.last_mouse_pos = (event.x, event.y)
        self.canvas.config(cursor="fleur")
    
    def _on_pan_move(self, event):
        dx = event.x - self.controller.last_mouse_pos[0]
        dy = event.y - self.controller.last_mouse_pos[1]
        self.controller.pan_offset_x += dx
        self.controller.pan_offset_y += dy
        self.controller.last_mouse_pos = (event.x, event.y)
        self.controller._update_canvas()
    
    # 其他视图相关方法
    def _save_image(self):
        """保存图片"""
        self.controller.save_image()
    
    def _undo(self):
        """撤销操作"""
        self.controller.undo()
    
    def _redo(self):
        """重做操作"""
        self.controller.redo()
    
    def _auto_enhance(self):
        """自动增强图片"""
        self.controller.auto_enhance()
    
    def _batch_convert_format(self):
        """批量转换格式"""
        self.controller.batch_convert_format()
    
    def _batch_add_watermark(self):
        """批量添加水印"""
        self.controller.batch_add_watermark()
    
    def _rename_image(self):
        """重命名图片"""
        self.controller.rename_image()
