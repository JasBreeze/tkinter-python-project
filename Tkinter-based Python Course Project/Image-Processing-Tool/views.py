
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
        
        # 垂直滚动条样式，使其更加明显
        style.configure("Vertical.TScrollbar", 
                       background=COLORS["bg_panel"],
                       troughcolor=COLORS["bg_main"],
                       arrowcolor=COLORS["accent"],
                       bordercolor=COLORS["bg_main"])
        style.map("Vertical.TScrollbar",
                 background=[("active", COLORS["bg_tool"])],
                 troughcolor=[("active", COLORS["bg_main"])])
    
    def _init_layout(self):
        """初始化应用程序布局，采用三栏设计：
        - 左侧工具栏：包含各种编辑工具入口
        - 中间画布：显示和编辑图片的主要区域
        - 右侧属性面板：根据所选工具动态显示属性和参数
        """

        # 1. 顶部菜单栏 (Header)
        header = tk.Frame(self, bg=COLORS["bg_tool"], height=40)
        header.pack(side=tk.TOP, fill=tk.X)
        self._create_header_btn(header, "📂 打开图片", self.controller.open_image)
        self._create_header_btn(header, "💾 保存", self._save_image)
        self._create_header_btn(header, "🔄 重命名", self._rename_image)
        self._create_header_btn(header, "↩ 撤销 (Ctrl+Z)", self._undo)
        self._create_header_btn(header, "↪ 重做 (Ctrl+Y)", self._redo)
        self._create_header_btn(header, "✨ 自动优化", self._auto_enhance)

        # 2. 主容器
        main_container = ttk.Frame(self, style="Main.TFrame")
        main_container.pack(fill=tk.BOTH, expand=True)

        # 2.1 左侧工具栏 (Sidebar)
        self.sidebar = tk.Frame(main_container, bg=COLORS["bg_tool"], width=80)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar.pack_propagate(False)

        # 工具按钮 - 按功能分组排列
        sidebar_tools = [
            ("基础\n调节", "adjust", "调整图片亮度、对比度等基础参数"),
            ("滤镜\n特效", "filter", "应用内置滤镜和LUT滤镜"),
            ("裁剪\n旋转", "crop", "裁剪、旋转和翻转图片"),
            ("添加\n水印", "text", "添加文字或时间水印"),
            ("涂鸦\n笔刷", "doodle", "自由手绘涂鸦"),
            ("马赛克", "mosaic", "添加马赛克效果"),
            ("添加\n贴纸", "sticker", "添加装饰性贴纸"),
            ("批量\n处理", "batch", "批量转换格式和添加水印")
        ]
        
        for text, tool_id, tooltip in sidebar_tools:
            self._add_sidebar_tool(text, tool_id, lambda id=tool_id: self.show_panel(id))

        # 2.2 右侧属性面板 (Properties)
        self.prop_panel = tk.Frame(main_container, bg=COLORS["bg_panel"], width=300)
        self.prop_panel.pack(side=tk.RIGHT, fill=tk.Y)
        self.prop_panel.pack_propagate(False)

        # 属性面板标题
        self.panel_title = ttk.Label(self.prop_panel, text="工具属性", style="Header.TLabel")
        self.panel_title.pack(pady=5, padx=5)

        # 创建可滚动的内容容器
        scroll_container = tk.Frame(self.prop_panel, bg=COLORS["bg_panel"])
        scroll_container.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5)

        # 画布作为滚动区域
        self.scroll_canvas = tk.Canvas(scroll_container, bg=COLORS["bg_panel"], highlightthickness=0)
        self.scroll_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 垂直滚动条，应用自定义样式使其更加明显
        # 注意：必须先创建canvas，然后再创建scrollbar并关联
        self.scrollbar = ttk.Scrollbar(scroll_container, orient=tk.VERTICAL, command=self.scroll_canvas.yview, style="Vertical.TScrollbar")
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 将画布与滚动条关联
        self.scroll_canvas.configure(yscrollcommand=self.scrollbar.set)
        
        # 确保滚动条始终可见，设置滚动增量
        self.scroll_canvas.configure(yscrollincrement=1)

        # 内容容器，实际的面板内容将放在这里
        self.panel_content = tk.Frame(self.scroll_canvas, bg=COLORS["bg_panel"])
        self.content_window = self.scroll_canvas.create_window((0, 0), window=self.panel_content, anchor=tk.NW, width=290)

        # 绑定鼠标滚轮事件，实现平滑滚动
        def _on_mousewheel(event):
            self.scroll_canvas.yview_scroll(int(-1*(event.delta/120)), "units")

        # 确保内容容器大小变化时更新滚动区域
        def update_scrollregion(event):
            # 设置滚动区域，确保内容可以滚动
            self.scroll_canvas.configure(scrollregion=self.scroll_canvas.bbox("all"))
            if event.widget == self.panel_content:
                self.scroll_canvas.itemconfig(self.content_window, width=event.width)
            # 强制更新滚动条状态
            self.scrollbar.update()
            self.scroll_canvas.update()

        self.panel_content.bind("<Configure>", update_scrollregion)
        self.scroll_canvas.bind("<MouseWheel>", _on_mousewheel)
        self.panel_content.bind("<MouseWheel>", _on_mousewheel)
        
        # 创建底部固定控制区域
        self.bottom_control_frame = ttk.Frame(self.prop_panel, style="TFrame")
        self.bottom_control_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=(5, 20))

        # 2.3 中间画布 (Canvas) - 图片编辑的主要区域
        canvas_frame = tk.Frame(main_container, bg=COLORS["bg_main"])
        canvas_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(canvas_frame, bg=COLORS["bg_main"], highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # 初始状态提示
        self.status_label = tk.Label(self.canvas, text="请打开一张图片开始编辑",
                                     bg=COLORS["bg_main"], fg="#666666", font=("Arial", 14))
        self.status_label.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        
        # 底部状态条，用于显示操作反馈
        self.bottom_status = tk.Label(self, text="就绪", bg=COLORS["bg_tool"], fg=COLORS["fg_text"], 
                                     font=("Segoe UI", 9), height=2, bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.bottom_status.pack(side=tk.BOTTOM, fill=tk.X)
    
    def update_status(self, message, duration=2000):
        """更新底部状态栏消息"""
        self.bottom_status.config(text=message)
        # 2秒后恢复默认状态
        self.after(duration, lambda: self.bottom_status.config(text="就绪"))
    
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

        # 清空面板和底部控制区域
        for widget in self.panel_content.winfo_children():
            widget.destroy()
        for widget in self.bottom_control_frame.winfo_children():
            widget.destroy()

        # 根据工具构建 UI
        titles = {
            "adjust": "光效调节", "filter": "滤镜库",
            "crop": "裁剪构图", "text": "添加水印", "doodle": "画笔涂鸦", "mosaic": "马赛克工具",
            "sticker": "贴纸", "batch": "批量处理",
            "batch_convert": "批量转换格式", "batch_watermark": "批量添加水印"
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
        elif tool_name == "batch":
            self._build_batch_panel()
        elif tool_name == "batch_convert":
            self._build_batch_convert_panel()
        elif tool_name == "batch_watermark":
            self._build_batch_watermark_panel()
    
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
        
        # 确保 selected_ratio 已初始化
        if not hasattr(self.controller, 'selected_ratio'):
            self.controller._init_tk_variables()
        
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
        
        # 设置两行两列的网格布局
        ttk.Button(rotate_frame, text="左旋转90°", command=self.controller._rotate_left).grid(row=0, column=0, padx=3, pady=2, sticky=tk.NSEW)
        ttk.Button(rotate_frame, text="右旋转90°", command=self.controller._rotate_right).grid(row=0, column=1, padx=3, pady=2, sticky=tk.NSEW)
        ttk.Button(rotate_frame, text="左右翻转", command=self.controller._flip_horizontal).grid(row=1, column=0, padx=3, pady=2, sticky=tk.NSEW)
        ttk.Button(rotate_frame, text="上下翻转", command=self.controller._flip_vertical).grid(row=1, column=1, padx=3, pady=2, sticky=tk.NSEW)
        
        # 设置网格列权重，确保按钮大小一致
        rotate_frame.grid_columnconfigure(0, weight=1)
        rotate_frame.grid_columnconfigure(1, weight=1)
        
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
    
    # 辅助函数：创建标签和滑块的组合
    def _create_labeled_scale(self, label, var, from_, to, command=None, orient=tk.HORIZONTAL, pack=True, **kwargs):
        """创建带有标签的滑块控件"""
        # 创建标签
        ttk.Label(self.panel_content, text=label).pack(anchor=tk.W, pady=kwargs.get('pady', (0, 2)))
        # 创建滑块
        scale = ttk.Scale(self.panel_content, from_=from_, to=to, variable=var, orient=orient, command=command)
        if pack:
            scale.pack(fill=tk.X, pady=kwargs.get('pady', 5))
        return scale
    
    # 辅助函数：创建标签和单选按钮组
    def _create_radio_group(self, label, options, var, command=None):
        """创建带有标签的单选按钮组"""
        # 创建标签
        ttk.Label(self.panel_content, text=label).pack(anchor=tk.W, pady=(0, 5))
        # 创建单选按钮组框架
        frame = tk.Frame(self.panel_content, bg=COLORS["bg_panel"])
        frame.pack(fill=tk.X, pady=5)
        # 添加单选按钮
        for option in options:
            ttk.Radiobutton(frame, text=option[0], variable=var, value=option[1], command=command).pack(side=tk.LEFT, padx=3)
        return frame
    
    # 辅助函数：创建带标签的输入框
    def _create_labeled_entry(self, label, var=None, default_value="", command=None):
        """创建带有标签的输入框"""
        # 创建标签
        ttk.Label(self.panel_content, text=label).pack(anchor=tk.W, pady=(0, 2))
        # 创建输入框
        entry = ttk.Entry(self.panel_content, textvariable=var)
        entry.pack(fill=tk.X, pady=5)
        # 插入默认值
        if default_value:
            entry.insert(0, default_value)
        # 绑定命令
        if command:
            entry.bind("<KeyRelease>", command)
        return entry
    
    def _build_text_panel(self):
        """构建文字水印面板"""
        # 水印类型选择
        self.controller.watermark_type = tk.StringVar(value="text")
        
        # 添加水印类型切换事件
        def on_watermark_type_change():
            # 始终显示文字输入框，不受水印类型影响
            self.controller._update_text_preview()
        
        # 使用辅助函数创建单选按钮组
        self._create_radio_group("水印类型:", [
            ("文字水印", "text"),
            ("时间水印", "time")
        ], self.controller.watermark_type, on_watermark_type_change)

        # 文字输入
        text_entry = self._create_labeled_entry("文字:", var=self.controller.watermark_text_var, command=lambda e: self.controller._update_text_preview())
        # 保存Entry引用，供控制器访问
        self.controller.watermark_entry = text_entry
        
        # 字体大小
        self.controller.watermark_size_var = tk.IntVar(value=50)
        size_scale = self._create_labeled_scale("字号:", self.controller.watermark_size_var, 10, 200, 
                                               command=lambda v: self.controller._update_text_preview())
        # 绑定拖动事件，实时更新预览
        size_scale.bind("<B1-Motion>", lambda e: self.controller._update_text_preview())
        
        # 透明度
        self.controller.watermark_alpha_var = tk.IntVar(value=180)
        alpha_scale = self._create_labeled_scale("透明度:", self.controller.watermark_alpha_var, 0, 255, 
                                               command=lambda v: self.controller._update_text_preview())
        # 绑定拖动事件，实时更新预览
        alpha_scale.bind("<B1-Motion>", lambda e: self.controller._update_text_preview())
        
        # 颜色选择
        ttk.Button(self.panel_content, text="选择颜色", command=self.controller._choose_watermark_color).pack(fill=tk.X, pady=5)
        self.controller.watermark_color = (255, 255, 255)
        
        # 描边宽度
        self.controller.watermark_stroke_width_var = tk.IntVar(value=2)
        stroke_width_scale = self._create_labeled_scale("描边宽度:", self.controller.watermark_stroke_width_var, 0, 10, 
                                                       command=lambda v: self.controller._update_text_preview(),
                                                       pady=(10, 5))
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
        # 确保变量已经初始化
        if not hasattr(self.controller, 'doodle_size_var'):
            self.controller._init_tk_variables()
        
        # 绘制模式 - 使用辅助函数创建单选按钮组
        self._create_radio_group("绘制模式:", [
            ("笔刷", "brush"),
            ("橡皮擦", "eraser")
        ], self.controller.doodle_mode, self.controller._on_doodle_mode_change)
        
        # 大小滑块 - 使用辅助函数创建标签和滑块组合
        self._create_labeled_scale("大小:", self.controller.doodle_size_var, 1, 100, 
                                 command=lambda v: self.controller._on_doodle_size_change(float(v)))
        
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
    
    def _add_doodle_size_slider(self):
        """添加或更新涂鸦大小滑块 - 使用新的辅助函数"""
        # 移除旧的滑块
        for widget in self.panel_content.winfo_children():
            if isinstance(widget, ttk.Scale):
                widget.pack_forget()
        
        # 使用辅助函数创建标签和滑块组合
        self._create_labeled_scale("大小:", self.controller.doodle_size_var, 1, 100, 
                                 command=lambda v: self.controller._on_doodle_size_change(float(v)))
    
    def _build_mosaic_panel(self):
        """构建马赛克面板"""
        # 确保变量已经初始化
        if not hasattr(self.controller, 'mosaic_type_var'):
            self.controller._init_tk_variables()
        
        # 马赛克类型选择 - 使用辅助函数创建单选按钮组
        self._create_radio_group("马赛克类型:", [
            ("像素化", "pixel"),
            ("模糊", "blur")
        ], self.controller.mosaic_type_var, self.controller._on_mosaic_type_change)

        # 马赛克大小 - 使用辅助函数创建标签和滑块组合
        self._create_labeled_scale("马赛克大小:", self.controller.mosaic_size_var, 10, 200, 
                                 command=lambda v: self.controller._on_mosaic_size_change(float(v)))

        # 结束马赛克按钮
        ttk.Button(self.panel_content, text="✔ 结束马赛克", command=self.controller._apply_mosaic).pack(pady=20, fill=tk.X)
        ttk.Label(self.panel_content, text="* 绘制过程中可撤销", foreground="#888888").pack()

        # 初始化马赛克工具
        if self.controller.editing_image:
            self.controller._init_mosaic_tool()
    
    def _add_label(self, text, pady=5):
        """添加标签的辅助方法 - 兼容旧代码"""
        ttk.Label(self.panel_content, text=text).pack(anchor=tk.W, pady=pady)
    
    def _add_note(self, text):
        """添加注释文本的辅助方法 - 兼容旧代码"""
        ttk.Label(self.panel_content, text=text, foreground="#888888").pack()
    
    def _build_sticker_panel(self):
        """构建贴纸面板"""
        # 加载贴纸文件
        sticker_dir = os.path.join(os.path.dirname(__file__), "resources", "stickers")
        self.controller.sticker_files = [os.path.join(sticker_dir, f) for f in os.listdir(sticker_dir) 
                             if f.endswith((".png", ".jpg", ".jpeg", ".bmp"))]
        
        # 创建固定大小的滚动容器，添加垂直滚动条
        sticker_container = ttk.Frame(self.panel_content, style="TFrame")
        sticker_container.pack(fill=tk.X, pady=5)
        
        # 创建垂直滚动条，应用自定义样式使其更加明显
        sticker_scrollbar = ttk.Scrollbar(sticker_container, orient=tk.VERTICAL, style="Vertical.TScrollbar")
        sticker_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 创建Canvas作为滚动区域，设置固定高度
        sticker_canvas = tk.Canvas(sticker_container, 
                                  bg=COLORS["bg_panel"],
                                  yscrollcommand=sticker_scrollbar.set,
                                  highlightthickness=0,
                                  height=350)  # 固定高度，确保面积不变
        sticker_canvas.pack(side=tk.LEFT, fill=tk.X)
        
        # 配置滚动条
        sticker_scrollbar.config(command=sticker_canvas.yview)
        
        # 贴纸内容框架
        sticker_grid = ttk.Frame(sticker_canvas, style="TFrame")
        # 保存窗口ID
        sticker_window_id = sticker_canvas.create_window((0, 0), window=sticker_grid, anchor=tk.NW, width=sticker_canvas.winfo_reqwidth())
        
        # 更新滚动区域
        def update_sticker_scrollregion(event):
            sticker_canvas.config(scrollregion=sticker_canvas.bbox("all"))
            # 确保内容宽度与画布一致
            sticker_canvas.itemconfig(sticker_window_id, width=sticker_canvas.winfo_width())
        
        sticker_grid.bind("<Configure>", update_sticker_scrollregion)
        sticker_canvas.bind("<Configure>", update_sticker_scrollregion)
        
        # 绑定鼠标滚轮事件
        def on_sticker_mousewheel(event):
            sticker_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        sticker_canvas.bind("<MouseWheel>", on_sticker_mousewheel)
        sticker_grid.bind("<MouseWheel>", on_sticker_mousewheel)
        
        # 每行显示3个贴纸
        row = 0
        col = 0
        thumb_size = (70, 70)  # 调整贴纸大小，优化显示效果
        
        # 优化贴纸加载和显示
        for i, sticker_path in enumerate(self.controller.sticker_files):
            try:
                # 跳过损坏的文件，减少错误处理开销
                sticker_img = Image.open(sticker_path)
                
                # 计算缩放比例，保持原始比例
                original_width, original_height = sticker_img.size
                scale = min(thumb_size[0] / original_width, thumb_size[1] / original_height)
                new_width = int(original_width * scale)
                new_height = int(original_height * scale)
                
                # 高质量缩放
                resized_sticker = sticker_img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                # 处理透明背景
                display_sticker = Image.new('RGBA', thumb_size, (255, 255, 255, 0))
                x = (thumb_size[0] - new_width) // 2
                y = (thumb_size[1] - new_height) // 2
                
                if resized_sticker.mode == 'RGBA':
                    display_sticker.paste(resized_sticker, (x, y), resized_sticker)
                else:
                    rgba_sticker = resized_sticker.convert('RGBA')
                    display_sticker.paste(rgba_sticker, (x, y), rgba_sticker)
                
                sticker_tk = ImageTk.PhotoImage(display_sticker)
                
                # 创建贴纸按钮
                sticker_btn = tk.Button(sticker_grid, image=sticker_tk, 
                                      bg=COLORS["bg_tool"], 
                                      bd=1, 
                                      relief="raised",
                                      highlightthickness=1,
                                      highlightbackground=COLORS["accent"],
                                      width=thumb_size[0],
                                      height=thumb_size[1],
                                      command=lambda path=sticker_path: self.controller._select_sticker(path))
                sticker_btn.image = sticker_tk  # 保存引用
                
                # 网格布局，每行3个
                sticker_btn.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
                
                # 递增行列计数
                col += 1
                if col >= 3:
                    col = 0
                    row += 1
            except Exception as e:
                # 忽略无法加载的文件
                print(f"无法加载贴纸文件 {sticker_path}: {e}")
                continue
        
        # 提示文本
        ttk.Label(self.panel_content, text="* 点击贴纸添加到图片，添加后可拖动调整位置", foreground="#888888").pack(pady=10)
        
        # 添加一个占位框架，确保贴纸区域有足够的高度，让主滚动条可以滚动更多内容
        # 这会让更多贴纸显示出来
        spacer = tk.Frame(self.panel_content, bg=COLORS["bg_panel"], height=200)
        spacer.pack(fill=tk.X, pady=10)
        
        # 添加贴纸缩放控件到底部固定区域
        scale_frame = ttk.Frame(self.bottom_control_frame)
        scale_frame.pack(fill=tk.X, pady=5)
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
        
        # 添加贴纸旋转控件到底部固定区域
        rotate_frame = ttk.Frame(self.bottom_control_frame)
        rotate_frame.pack(fill=tk.X, pady=5)
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
        
        # 确认添加贴纸按钮到底部固定区域
        confirm_frame = ttk.Frame(self.bottom_control_frame)
        confirm_frame.pack(fill=tk.X, pady=10)
        ttk.Button(confirm_frame, text="✔ 确认添加贴纸", command=self.controller._confirm_sticker).pack(fill=tk.X)
        
        # 绑定输入框事件
        self.sticker_scale_entry.bind("<Return>", lambda e: self.controller._update_sticker_style(self.sticker_scale_var.get(), self.controller.sticker_rotation))
        self.sticker_scale_entry.bind("<FocusOut>", lambda e: self.controller._update_sticker_style(self.sticker_scale_var.get(), self.controller.sticker_rotation))
        self.sticker_rotation_entry.bind("<Return>", lambda e: self.controller._update_sticker_style(self.controller.sticker_scale, self.sticker_rotation_var.get()))
        self.sticker_rotation_entry.bind("<FocusOut>", lambda e: self.controller._update_sticker_style(self.controller.sticker_scale, self.sticker_rotation_var.get()))
        
        # 绑定画布事件
        if self.controller.editing_image:
            self.canvas.bind("<ButtonPress-1>", self.controller._on_sticker_press)
            self.canvas.bind("<B1-Motion>", self.controller._on_sticker_drag)
            self.canvas.bind("<ButtonRelease-1>", self.controller._on_sticker_release)
            self.canvas.bind("<ButtonPress-3>", self.controller._on_sticker_right_click)
    
    def _build_batch_panel(self):
        """构建批量处理主面板"""
        # 批量处理选项说明
        ttk.Label(self.panel_content, text="选择要执行的批量操作：", style="Header.TLabel").pack(pady=10)
        
        # 批量转换格式按钮
        tk.Button(self.panel_content, text="🔄 批量转换格式", 
                command=lambda: self.show_panel("batch_convert"), 
                bg=COLORS["bg_tool"], 
                fg=COLORS["fg_text"],
                bd=0, 
                activebackground=COLORS["accent"], 
                height=3, 
                font=("Segoe UI", 11)).pack(fill=tk.X, pady=5, padx=10)
        
        # 批量添加水印按钮
        tk.Button(self.panel_content, text="🔖 批量添加水印", 
                command=lambda: self.show_panel("batch_watermark"), 
                bg=COLORS["bg_tool"], 
                fg=COLORS["fg_text"],
                bd=0, 
                activebackground=COLORS["accent"], 
                height=3, 
                font=("Segoe UI", 11)).pack(fill=tk.X, pady=5, padx=10)
        
        # 说明文本
        ttk.Label(self.panel_content, text="* 选择一个批量操作开始处理", foreground="#888888").pack(pady=20)
        ttk.Label(self.panel_content, text="* 支持批量处理多个文件或整个文件夹", foreground="#888888").pack()
        ttk.Label(self.panel_content, text="* 可自定义输出格式、质量和其他参数", foreground="#888888").pack()
    
    def _build_batch_convert_panel(self):
        """构建批量转换格式面板"""
        # 初始化批量转换格式所需的变量
        if not hasattr(self.controller, 'batch_convert_vars'):
            self.controller._init_batch_convert_vars()
        
        # 创建固定大小的滚动容器，添加垂直滚动条
        batch_container = ttk.Frame(self.panel_content, style="TFrame")
        batch_container.pack(fill=tk.X, pady=5)
        
        # 创建垂直滚动条，应用自定义样式使其更加明显
        batch_scrollbar = ttk.Scrollbar(batch_container, orient=tk.VERTICAL, style="Vertical.TScrollbar")
        batch_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 创建Canvas作为滚动区域，设置固定高度
        batch_canvas = tk.Canvas(batch_container, 
                                bg=COLORS["bg_panel"],
                                yscrollcommand=batch_scrollbar.set,
                                highlightthickness=0,
                                height=600)  # 增加高度，确保执行按钮可见
        batch_canvas.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # 配置滚动条
        batch_scrollbar.config(command=batch_canvas.yview)
        
        # 内容框架
        content_frame = ttk.Frame(batch_canvas, style="TFrame")
        # 保存窗口ID
        content_window_id = batch_canvas.create_window((0, 0), window=content_frame, anchor=tk.NW, width=batch_canvas.winfo_reqwidth())
        
        # 更新滚动区域
        def update_batch_scrollregion(event):
            batch_canvas.config(scrollregion=batch_canvas.bbox("all"))
            # 确保内容宽度与画布一致
            batch_canvas.itemconfig(content_window_id, width=batch_canvas.winfo_width())
        
        content_frame.bind("<Configure>", update_batch_scrollregion)
        batch_canvas.bind("<Configure>", update_batch_scrollregion)
        
        # 绑定鼠标滚轮事件
        def on_batch_mousewheel(event):
            batch_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        batch_canvas.bind("<MouseWheel>", on_batch_mousewheel)
        content_frame.bind("<MouseWheel>", on_batch_mousewheel)
        
        # 1. 基本设置
        ttk.Label(content_frame, text="📋 批量转换设置", style="Header.TLabel").pack(pady=3, anchor=tk.W)
        ttk.Separator(content_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=3)
        
        # 选择模式
        ttk.Label(content_frame, text="处理模式:").pack(anchor=tk.W, pady=1, padx=3)
        mode_container = ttk.Frame(content_frame)
        mode_container.pack(fill=tk.X, pady=1, padx=3)
        ttk.Radiobutton(mode_container, text="文件夹", variable=self.controller.batch_convert_vars['mode_var'], value="folder").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(mode_container, text="文件", variable=self.controller.batch_convert_vars['mode_var'], value="file").pack(side=tk.LEFT, padx=15)
        
        # 包含子文件夹选项
        filter_container = ttk.Frame(content_frame)
        filter_container.pack(fill=tk.X, pady=1, padx=3)
        ttk.Checkbutton(filter_container, text="包含子文件夹", variable=self.controller.batch_convert_vars['recursive_var']).pack(side=tk.LEFT, padx=5)
        
        # 2. 输入输出设置
        ttk.Label(content_frame, text="📁 输入输出", style="Header.TLabel").pack(pady=3, anchor=tk.W, padx=3)
        ttk.Separator(content_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=3)
        
        # 输入选择
        input_container = ttk.Frame(content_frame)
        input_container.pack(fill=tk.X, pady=1, padx=3)
        input_btn = ttk.Button(input_container, text="选择输入", command=self.controller._batch_select_input, width=7)
        input_btn.pack(side=tk.RIGHT, padx=3)
        self.input_label = ttk.Label(input_container, textvariable=self.controller.batch_convert_vars['input_label_var'], 
                                    anchor=tk.W, font=('Segoe UI', 8), wraplength=220)
        self.input_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=3)
        
        # 文件数量
        file_count_label = ttk.Label(content_frame, textvariable=self.controller.batch_convert_vars['file_count_label_var'], 
                                    anchor=tk.W, font=('Segoe UI', 8), foreground="#888888")
        file_count_label.pack(fill=tk.X, pady=1, padx=3)
        
        # 输出选择
        output_container = ttk.Frame(content_frame)
        output_container.pack(fill=tk.X, pady=1, padx=3)
        output_btn = ttk.Button(output_container, text="选择输出", command=self.controller._batch_select_output, width=7)
        output_btn.pack(side=tk.RIGHT, padx=3)
        self.output_label = ttk.Label(output_container, textvariable=self.controller.batch_convert_vars['output_label_var'], 
                                     anchor=tk.W, font=('Segoe UI', 8), wraplength=220)
        self.output_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=3)
        
        # 3. 文件列表预览
        ttk.Label(content_frame, text="📋 文件预览", style="Header.TLabel").pack(pady=3, anchor=tk.W, padx=3)
        ttk.Separator(content_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=3)
        
        # 文件列表文本框
        text_frame = ttk.Frame(content_frame)
        text_frame.pack(fill=tk.X, pady=1, padx=3)
        self.controller.batch_convert_vars['file_list_text'] = tk.Text(text_frame, height=3, wrap=tk.WORD, font=('Segoe UI', 8), bg="#2a2a2a", fg="#ffffff")
        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=self.controller.batch_convert_vars['file_list_text'].yview, style="Vertical.TScrollbar")
        self.controller.batch_convert_vars['file_list_text'].configure(yscrollcommand=scrollbar.set)
        self.controller.batch_convert_vars['file_list_text'].pack(side=tk.LEFT, fill=tk.X, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.controller.batch_convert_vars['file_list_text'].config(state="disabled")
        
        # 移除不存在的update_status方法调用
        
        # 4. 转换设置
        ttk.Label(content_frame, text="⚙️ 转换设置", style="Header.TLabel").pack(pady=3, anchor=tk.W, padx=3)
        ttk.Separator(content_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=3)
        
        # 目标格式
        ttk.Label(content_frame, text="目标格式:").pack(anchor=tk.W, pady=1, padx=3)
        
        # 格式选项使用网格布局，更紧凑
        format_container = ttk.Frame(content_frame)
        format_container.pack(fill=tk.X, pady=1, padx=3)
        
        supported_formats = ["JPG", "PNG", "BMP", "WEBP", "TIFF", "ICO"]
        for i, fmt in enumerate(supported_formats):
            radio_btn = ttk.Radiobutton(format_container, text=fmt, variable=self.controller.batch_convert_vars['target_format_var'], 
                          value=fmt)
            radio_btn.grid(row=i//3, column=i%3, sticky=tk.W, padx=5, pady=1)
            # 添加工具提示
            # 移除不存在的update_status方法调用
        
        # 质量设置
        quality_frame = ttk.Frame(content_frame)
        quality_frame.pack(fill=tk.X, pady=1, padx=3)
        ttk.Label(quality_frame, text="质量:").pack(anchor=tk.W, pady=1, padx=3, side=tk.LEFT)
        quality_container = ttk.Frame(quality_frame)
        quality_container.pack(fill=tk.X, pady=1, padx=3, side=tk.LEFT, expand=True)
        quality_scale = ttk.Scale(quality_container, from_=1, to=100, variable=self.controller.batch_convert_vars['quality_var'], 
                 orient=tk.HORIZONTAL)
        quality_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        ttk.Label(quality_container, textvariable=self.controller.batch_convert_vars['quality_var'], width=3).pack(side=tk.LEFT, padx=3)
        
        # 添加快速质量设置按钮
        quick_quality_frame = ttk.Frame(content_frame)
        quick_quality_frame.pack(fill=tk.X, pady=1, padx=3)
        ttk.Button(quick_quality_frame, text="高质量", command=lambda: self.controller.batch_convert_vars['quality_var'].set(90)).pack(side=tk.LEFT, padx=2)
        ttk.Button(quick_quality_frame, text="中质量", command=lambda: self.controller.batch_convert_vars['quality_var'].set(70)).pack(side=tk.LEFT, padx=2)
        ttk.Button(quick_quality_frame, text="低质量", command=lambda: self.controller.batch_convert_vars['quality_var'].set(50)).pack(side=tk.LEFT, padx=2)
        
        # 5. 重命名选项
        ttk.Label(content_frame, text="✏️ 重命名", style="Header.TLabel").pack(pady=3, anchor=tk.W, padx=3)
        ttk.Separator(content_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=3)
        
        # 启用重命名
        rename_container = ttk.Frame(content_frame)
        rename_container.pack(fill=tk.X, pady=1, padx=3)
        rename_check = ttk.Checkbutton(rename_container, text="启用重命名", variable=self.controller.batch_convert_vars['rename_var'])
        rename_check.pack(side=tk.LEFT, padx=3)
        # 移除不存在的update_status方法调用
        
        # 前缀后缀输入
        rename_details = ttk.Frame(content_frame)
        rename_details.pack(fill=tk.X, pady=1, padx=10)
        
        ttk.Label(rename_details, text="前缀:").pack(side=tk.LEFT, padx=3)
        prefix_entry = ttk.Entry(rename_details, textvariable=self.controller.batch_convert_vars['prefix_var'], width=10)
        prefix_entry.pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
        # 移除不存在的update_status方法调用
        
        ttk.Label(rename_details, text="后缀:").pack(side=tk.LEFT, padx=8)
        suffix_entry = ttk.Entry(rename_details, textvariable=self.controller.batch_convert_vars['suffix_var'], width=10)
        suffix_entry.pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
        # 移除不存在的update_status方法调用
        
        # 6. 进度显示
        ttk.Label(content_frame, text="📊 进度", style="Header.TLabel").pack(pady=3, anchor=tk.W, padx=3)
        ttk.Separator(content_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=3)
        
        # 当前文件
        current_file_label = ttk.Label(content_frame, textvariable=self.controller.batch_convert_vars['current_file_var'], 
                                      font=('Segoe UI', 8), wraplength=240)
        current_file_label.pack(fill=tk.X, pady=1, padx=3)
        
        # 进度条
        progress_bar = ttk.Progressbar(content_frame, variable=self.controller.batch_convert_vars['progress_var'], 
                                      maximum=100, mode="determinate")
        progress_bar.pack(fill=tk.X, pady=1, padx=3)
        
        # 进度标签
        progress_label = ttk.Label(content_frame, textvariable=self.controller.batch_convert_vars['progress_label_var'], 
                                  font=('Segoe UI', 8))
        progress_label.pack(fill=tk.X, pady=1, padx=3)
        
        # 7. 操作按钮 - 移到滚动区域内部
        btn_frame = ttk.Frame(content_frame)
        btn_frame.pack(fill=tk.X, pady=20, padx=3)
        
        # 优化按钮布局
        btn_frame.grid_columnconfigure(0, weight=1)
        btn_frame.grid_columnconfigure(1, weight=1)
        btn_frame.grid_columnconfigure(2, weight=1)
        
        back_btn = ttk.Button(btn_frame, text="返回", command=lambda: self.show_panel("batch"))
        back_btn.grid(row=0, column=0, padx=3, sticky="nsew")
        # 移除不存在的update_status方法调用
        
        cancel_btn = ttk.Button(btn_frame, text="取消", command=lambda: self.show_panel("batch"))
        cancel_btn.grid(row=0, column=1, padx=3, sticky="nsew")
        # 移除不存在的update_status方法调用
        
        start_btn = ttk.Button(btn_frame, text="执行转换", command=self.controller._batch_start_conversion)
        start_btn.grid(row=0, column=2, padx=3, sticky="nsew")
        # 移除不存在的update_status方法调用
        
        # 添加状态提示标签
        status_tip = ttk.Label(content_frame, text="提示: 选择输入和输出目录后点击执行转换", foreground="#888888", font=('Segoe UI', 8))
        status_tip.pack(fill=tk.X, pady=5, padx=3)
        
        # 确保滚动区域更新
        self.after(100, lambda: self.scroll_canvas.configure(scrollregion=self.scroll_canvas.bbox("all")))
    
    def _build_batch_watermark_panel(self):
        """构建批量添加水印面板"""
        # 初始化批量添加水印所需的变量
        if not hasattr(self.controller, 'batch_watermark_vars'):
            self.controller._init_batch_watermark_vars()
        
        # 创建固定大小的滚动容器，添加垂直滚动条
        batch_container = ttk.Frame(self.panel_content, style="TFrame")
        batch_container.pack(fill=tk.X, pady=5)
        
        # 创建垂直滚动条，应用自定义样式使其更加明显
        batch_scrollbar = ttk.Scrollbar(batch_container, orient=tk.VERTICAL, style="Vertical.TScrollbar")
        batch_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 创建Canvas作为滚动区域，设置固定高度
        batch_canvas = tk.Canvas(batch_container, 
                                bg=COLORS["bg_panel"],
                                yscrollcommand=batch_scrollbar.set,
                                highlightthickness=0,
                                height=600)  # 增加高度，确保执行按钮可见
        batch_canvas.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # 配置滚动条
        batch_scrollbar.config(command=batch_canvas.yview)
        
        # 内容框架
        content_frame = ttk.Frame(batch_canvas, style="TFrame")
        # 保存窗口ID
        content_window_id = batch_canvas.create_window((0, 0), window=content_frame, anchor=tk.NW, width=batch_canvas.winfo_reqwidth())
        
        # 更新滚动区域
        def update_batch_scrollregion(event):
            batch_canvas.config(scrollregion=batch_canvas.bbox("all"))
            # 确保内容宽度与画布一致
            batch_canvas.itemconfig(content_window_id, width=batch_canvas.winfo_width())
        
        content_frame.bind("<Configure>", update_batch_scrollregion)
        batch_canvas.bind("<Configure>", update_batch_scrollregion)
        
        # 绑定鼠标滚轮事件
        def on_batch_mousewheel(event):
            batch_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        batch_canvas.bind("<MouseWheel>", on_batch_mousewheel)
        content_frame.bind("<MouseWheel>", on_batch_mousewheel)
        
        # 1. 基本设置
        ttk.Label(content_frame, text="📋 批量水印设置", style="Header.TLabel").pack(pady=3, anchor=tk.W)
        ttk.Separator(content_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=3)
        
        # 选择模式
        ttk.Label(content_frame, text="处理模式:").pack(anchor=tk.W, pady=1, padx=3)
        mode_container = ttk.Frame(content_frame)
        mode_container.pack(fill=tk.X, pady=1, padx=3)
        ttk.Radiobutton(mode_container, text="文件夹", variable=self.controller.batch_watermark_vars['mode_var'], value="folder").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(mode_container, text="文件", variable=self.controller.batch_watermark_vars['mode_var'], value="file").pack(side=tk.LEFT, padx=15)
        
        # 水印类型
        ttk.Label(content_frame, text="水印类型:").pack(anchor=tk.W, pady=1, padx=3)
        type_container = ttk.Frame(content_frame)
        type_container.pack(fill=tk.X, pady=1, padx=3)
        ttk.Radiobutton(type_container, text="文字水印", variable=self.controller.batch_watermark_vars['watermark_type_var'], value="text").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(type_container, text="图片水印", variable=self.controller.batch_watermark_vars['watermark_type_var'], value="image").pack(side=tk.LEFT, padx=15)
        
        # 2. 输入输出设置
        ttk.Label(content_frame, text="📁 输入输出", style="Header.TLabel").pack(pady=3, anchor=tk.W)
        ttk.Separator(content_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=3)
        
        # 输入选择
        input_container = ttk.Frame(content_frame)
        input_container.pack(fill=tk.X, pady=1, padx=3)
        input_btn = ttk.Button(input_container, text="选择输入", command=self.controller._batch_watermark_select_input, width=7)
        input_btn.pack(side=tk.RIGHT, padx=3)
        self.input_label = ttk.Label(input_container, textvariable=self.controller.batch_watermark_vars['input_label_var'], 
                                    anchor=tk.W, font=('Segoe UI', 8), wraplength=220)
        self.input_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=3)
        
        # 文件数量
        file_count_label = ttk.Label(content_frame, textvariable=self.controller.batch_watermark_vars['file_count_label_var'], 
                                    anchor=tk.W, font=('Segoe UI', 8), foreground="#888888")
        file_count_label.pack(fill=tk.X, pady=1, padx=3)
        
        # 输出选择
        output_container = ttk.Frame(content_frame)
        output_container.pack(fill=tk.X, pady=1, padx=3)
        output_btn = ttk.Button(output_container, text="选择输出", command=self.controller._batch_watermark_select_output, width=7)
        output_btn.pack(side=tk.RIGHT, padx=3)
        self.output_label = ttk.Label(output_container, textvariable=self.controller.batch_watermark_vars['output_label_var'], 
                                     anchor=tk.W, font=('Segoe UI', 8), wraplength=220)
        self.output_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=3)
        
        # 3. 文字水印设置
        ttk.Label(content_frame, text="✏️ 水印内容", style="Header.TLabel").pack(pady=3, anchor=tk.W)
        ttk.Separator(content_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=3)
        
        # 水印文字
        text_container = ttk.Frame(content_frame)
        text_container.pack(fill=tk.X, pady=1, padx=3)
        ttk.Label(text_container, text="文字:").pack(side=tk.LEFT, padx=3, anchor=tk.CENTER)
        ttk.Entry(text_container, textvariable=self.controller.batch_watermark_vars['text_var']).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=3)
        
        # 字体大小
        size_frame = ttk.Frame(content_frame)
        size_frame.pack(fill=tk.X, pady=5, padx=3)
        ttk.Label(size_frame, text="大小:").pack(side=tk.LEFT, padx=2, anchor=tk.CENTER)
        ttk.Scale(size_frame, from_=10, to=200, variable=self.controller.batch_watermark_vars['font_size_var'], 
                 orient=tk.HORIZONTAL).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        ttk.Label(size_frame, textvariable=self.controller.batch_watermark_vars['font_size_var'], width=3).pack(side=tk.LEFT, padx=3)
        
        # 透明度
        opacity_frame = ttk.Frame(content_frame)
        opacity_frame.pack(fill=tk.X, pady=5, padx=3)
        ttk.Label(opacity_frame, text="透明度:").pack(side=tk.LEFT, padx=2, anchor=tk.CENTER)
        ttk.Scale(opacity_frame, from_=0, to=255, variable=self.controller.batch_watermark_vars['opacity_var'], 
                 orient=tk.HORIZONTAL).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        ttk.Label(opacity_frame, textvariable=self.controller.batch_watermark_vars['opacity_var'], width=3).pack(side=tk.LEFT, padx=3)
        
        # 4. 颜色设置
        ttk.Label(content_frame, text="🎨 颜色设置", style="Header.TLabel").pack(pady=3, anchor=tk.W)
        ttk.Separator(content_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=3)
        
        # 文字颜色
        text_color_container = ttk.Frame(content_frame)
        text_color_container.pack(fill=tk.X, pady=1, padx=3)
        ttk.Label(text_color_container, text="文字色:").pack(side=tk.LEFT, padx=3, anchor=tk.CENTER)
        ttk.Entry(text_color_container, textvariable=self.controller.batch_watermark_vars['text_color_var']).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        ttk.Button(text_color_container, text="选择", command=lambda: self.controller._batch_watermark_select_color("text_color_var"), width=4).pack(side=tk.LEFT, padx=3)
        
        # 描边颜色
        stroke_container = ttk.Frame(content_frame)
        stroke_container.pack(fill=tk.X, pady=1, padx=3)
        ttk.Label(stroke_container, text="描边色:").pack(side=tk.LEFT, padx=3, anchor=tk.CENTER)
        ttk.Entry(stroke_container, textvariable=self.controller.batch_watermark_vars['stroke_color_var']).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        ttk.Button(stroke_container, text="选择", command=lambda: self.controller._batch_watermark_select_color("stroke_color_var"), width=4).pack(side=tk.LEFT, padx=3)
        
        # 描边宽度
        stroke_width_container = ttk.Frame(content_frame)
        stroke_width_container.pack(fill=tk.X, pady=1, padx=3)
        ttk.Label(stroke_width_container, text="描边宽:").pack(side=tk.LEFT, padx=3, anchor=tk.CENTER)
        ttk.Scale(stroke_width_container, from_=0, to=10, variable=self.controller.batch_watermark_vars['stroke_width_var'], 
                 orient=tk.HORIZONTAL).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        ttk.Label(stroke_width_container, textvariable=self.controller.batch_watermark_vars['stroke_width_var'], width=3).pack(side=tk.LEFT, padx=3)
        
        # 4. 图片水印设置
        ttk.Label(content_frame, text="🖼️ 图片水印", style="Header.TLabel").pack(pady=3, anchor=tk.W)
        ttk.Separator(content_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=3)
        
        # 图片选择
        image_container = ttk.Frame(content_frame)
        image_container.pack(fill=tk.X, pady=1, padx=3)
        ttk.Label(image_container, text="图片:").pack(side=tk.LEFT, padx=3, anchor=tk.CENTER)
        ttk.Button(image_container, text="选择图片", command=lambda: self.controller._batch_watermark_select_image()).pack(side=tk.RIGHT, padx=3)
        ttk.Entry(image_container, textvariable=self.controller.batch_watermark_vars['image_watermark_path']).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=3)
        
        # 图片缩放
        scale_frame = ttk.Frame(content_frame)
        scale_frame.pack(fill=tk.X, pady=5, padx=3)
        ttk.Label(scale_frame, text="缩放:").pack(side=tk.LEFT, padx=2, anchor=tk.CENTER)
        ttk.Scale(scale_frame, from_=10, to=200, variable=self.controller.batch_watermark_vars['image_watermark_scale'], 
                 orient=tk.HORIZONTAL).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        ttk.Label(scale_frame, textvariable=self.controller.batch_watermark_vars['image_watermark_scale'], width=3).pack(side=tk.LEFT, padx=3)
        ttk.Label(scale_frame, text="%").pack(side=tk.LEFT, padx=1)
        
        # 图片透明度
        image_opacity_frame = ttk.Frame(content_frame)
        image_opacity_frame.pack(fill=tk.X, pady=5, padx=3)
        ttk.Label(image_opacity_frame, text="透明度:").pack(side=tk.LEFT, padx=2, anchor=tk.CENTER)
        ttk.Scale(image_opacity_frame, from_=0, to=255, variable=self.controller.batch_watermark_vars['image_watermark_opacity'], 
                 orient=tk.HORIZONTAL).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        ttk.Label(image_opacity_frame, textvariable=self.controller.batch_watermark_vars['image_watermark_opacity'], width=3).pack(side=tk.LEFT, padx=3)
        
        # 5. 位置设置
        ttk.Label(content_frame, text="📍 位置设置", style="Header.TLabel").pack(pady=3, anchor=tk.W)
        ttk.Separator(content_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=3)
        
        # 位置选择
        position_container = ttk.Frame(content_frame)
        position_container.pack(fill=tk.X, pady=1, padx=3)
        ttk.Label(position_container, text="位置:", width=5).pack(side=tk.LEFT, padx=3, anchor=tk.CENTER)
        
        positions = ["左上角", "右上角", "左下角", "右下角", "上居中", "下居中", "左居中", "右居中", "居中"]
        position_combo = ttk.Combobox(position_container, textvariable=self.controller.batch_watermark_vars['position_var'], 
                                     values=positions, state="readonly")
        position_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=3)
        
        # 偏移设置
        offset_container = ttk.Frame(content_frame)
        offset_container.pack(fill=tk.X, pady=1, padx=3)
        
        # 水平偏移
        offset_x_frame = ttk.Frame(offset_container)
        offset_x_frame.pack(fill=tk.X, pady=5)
        ttk.Label(offset_x_frame, text="水平:").pack(side=tk.LEFT, padx=2, anchor=tk.CENTER)
        ttk.Scale(offset_x_frame, from_=-100, to=100, variable=self.controller.batch_watermark_vars['offset_x_var'], 
                 orient=tk.HORIZONTAL).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        ttk.Label(offset_x_frame, textvariable=self.controller.batch_watermark_vars['offset_x_var'], width=3).pack(side=tk.LEFT, padx=2)
        
        # 垂直偏移
        offset_y_frame = ttk.Frame(offset_container)
        offset_y_frame.pack(fill=tk.X, pady=5)
        ttk.Label(offset_y_frame, text="垂直:").pack(side=tk.LEFT, padx=2, anchor=tk.CENTER)
        ttk.Scale(offset_y_frame, from_=-100, to=100, variable=self.controller.batch_watermark_vars['offset_y_var'], 
                 orient=tk.HORIZONTAL).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        ttk.Label(offset_y_frame, textvariable=self.controller.batch_watermark_vars['offset_y_var'], width=3).pack(side=tk.LEFT, padx=2)
        
        # 6. 进度显示
        ttk.Label(content_frame, text="📊 进度", style="Header.TLabel").pack(pady=3, anchor=tk.W)
        ttk.Separator(content_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=3)
        
        # 当前文件
        self.current_file_label = ttk.Label(content_frame, textvariable=self.controller.batch_watermark_vars['current_file_var'], 
                                          font=('Segoe UI', 8), wraplength=240)
        self.current_file_label.pack(fill=tk.X, pady=1, padx=3)
        
        # 进度条
        progress_bar = ttk.Progressbar(content_frame, variable=self.controller.batch_watermark_vars['progress_var'], 
                                      maximum=100, mode="determinate")
        progress_bar.pack(fill=tk.X, pady=1, padx=3)
        
        # 进度标签
        progress_label = ttk.Label(content_frame, textvariable=self.controller.batch_watermark_vars['progress_label_var'], 
                                  font=('Segoe UI', 8))
        progress_label.pack(fill=tk.X, pady=1, padx=3)
        
        # 7. 操作按钮 - 移到滚动区域内部
        btn_frame = ttk.Frame(content_frame)
        btn_frame.pack(fill=tk.X, pady=20, padx=3)
        
        # 优化按钮布局
        btn_frame.grid_columnconfigure(0, weight=1)
        btn_frame.grid_columnconfigure(1, weight=1)
        btn_frame.grid_columnconfigure(2, weight=1)
        
        back_btn = ttk.Button(btn_frame, text="返回", command=lambda: self.show_panel("batch"))
        back_btn.grid(row=0, column=0, padx=3, sticky="nsew")
        
        cancel_btn = ttk.Button(btn_frame, text="取消", command=lambda: self.show_panel("batch"))
        cancel_btn.grid(row=0, column=1, padx=3, sticky="nsew")
        
        start_btn = ttk.Button(btn_frame, text="执行水印", command=self.controller._batch_start_add_watermark)
        start_btn.grid(row=0, column=2, padx=3, sticky="nsew")
        
        # 添加状态提示标签
        status_tip = ttk.Label(content_frame, text="提示: 选择输入和输出目录后点击执行水印", foreground="#888888", font=('Segoe UI', 8))
        status_tip.pack(fill=tk.X, pady=5, padx=3)
        
        # 确保滚动区域更新
        self.after(100, lambda: self.scroll_canvas.configure(scrollregion=self.scroll_canvas.bbox("all")))
        

    
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


    def _rename_image(self):
        """重命名图片"""
        self.controller.rename_image