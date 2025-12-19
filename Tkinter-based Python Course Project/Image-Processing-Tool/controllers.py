import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk, colorchooser
from PIL import Image, ImageTk, ImageFilter, ImageEnhance, ImageOps
import os
from config import COLORS
from models import DraggableTextWatermark, DoodleEditor, MosaicEditor, CropController

class EditorController:
    def __init__(self, view):
        self.view = view
        self.filepath = None
        self.original_image = None  # 磁盘读取的原始图（作为撤销基准）
        self.editing_image = None  # 当前已应用修改的图片（作为图层基底）
        self.preview_image = None  # 用于显示的图片（叠加了未应用的滤镜/调节）
        self.history = []  # 撤销栈
        self.redo_history = []  # 重做栈
        
        # 画布视图状态
        self.zoom_scale = 1.0
        self.pan_offset_x = 0
        self.pan_offset_y = 0
        self.last_mouse_pos = (0, 0)
        
        # 当前工具状态
        self.current_tool = None
        self.temp_adjustments = {  # 暂存调节参数
            "brightness": 1.0,
            "contrast": 1.0,
            "saturation": 1.0,
            "sharpness": 1.0
        }
        
        # 新功能实例
        self.doodle_editor = None  # 涂鸦编辑器实例
        self.mosaic_editor = None  # 马赛克编辑器实例
        self.text_watermark = None  # 文字水印实例
        self.crop_controller = None  # 裁剪控制器实例
        
        # 裁剪相关变量
        self.is_cropping = False
        self.crop_start = None
        self.crop_end = None
        self.resize_mode = None  # 调整模式：None, 'n', 'ne', 'e', 'se', 's', 'sw', 'w', 'nw'
        self.resize_corner = None
        self.move_offset = (0, 0)  # 裁剪框移动偏移量
        self.selected_ratio = None
        self.rotate_angle_var = None
        
        # 初始化其他状态变量
        self.is_dragging_text = False  # 是否正在拖动文字
        self.text_drag_offset = (0, 0)  # 文字拖动偏移量
        self.show_delete_button = False
        self.delete_button = None
        self.delete_button_rect = None
        
        # 局部放大视图相关变量
        self.show_magnifier = False  # 是否显示放大镜
        self.magnifier_size = 80  # 减小放大镜大小
        self.magnifier_scale = 1.5  # 调整放大倍数
        self.magnifier_x = 0  # 放大镜位置
        self.magnifier_y = 0
        
        # 贴纸相关变量
        self.sticker_files = []  # 贴纸文件列表
        self.selected_sticker = None  # 当前选中的贴纸
        self.sticker_obj = None  # 当前贴纸的DraggableSticker对象
        self.sticker_image = None  # 当前贴纸的Image对象
        self.sticker_tk = None  # 当前贴纸的ImageTk对象
        self.sticker_pos = (0, 0)  # 贴纸在图片上的位置
        self.is_dragging_sticker = False  # 是否正在拖动贴纸
        self.sticker_drag_offset_x = 0  # 贴纸拖动偏移量X
        self.sticker_drag_offset_y = 0  # 贴纸拖动偏移量Y
        self.is_sticker_applied = False  # 贴纸是否已应用到图片
        self.show_sticker_delete_button = False  # 是否显示贴纸删除按钮
        self.sticker_scale = 1.0  # 贴纸缩放比例
        self.sticker_rotation = 0  # 贴纸旋转角度
        
        # 裁剪相关变量
        self.is_cropping = False  # 是否正在裁剪
        self.crop_start = None  # 裁剪起始位置
        self.crop_end = None  # 裁剪结束位置
        self.resize_mode = None  # 调整模式
        self.resize_corner = None  # 调整角点
        
        # 保存非tkinter变量
        self.doodle_color = (255, 0, 0)  # 画笔颜色
        self.watermark_color = (255, 255, 255)  # 水印颜色
        self.watermark_stroke_color = (0, 0, 0)  # 描边颜色
        
    def _init_tk_variables(self):
        """初始化tkinter变量，在根窗口创建后调用"""
        # 涂鸦相关变量
        self.doodle_size_var = tk.IntVar(value=20)  # 画笔大小
        self.doodle_mode = tk.StringVar(value="brush")  # 画笔模式
        self.eraser_size_var = tk.IntVar(value=20)  # 橡皮擦大小
        
        # 水印相关变量
        self.watermark_text_var = tk.StringVar(value="")  # 水印文字
        self.watermark_size_var = tk.IntVar(value=42)  # 水印字体大小
        self.watermark_alpha_var = tk.IntVar(value=200)  # 水印透明度
        self.watermark_stroke_var = tk.BooleanVar(value=True)  # 是否添加描边
        self.watermark_stroke_width_var = tk.IntVar(value=3)  # 描边宽度
        
        # 马赛克相关变量
        self.mosaic_size_var = tk.IntVar(value=20)  # 马赛克大小
        self.mosaic_type_var = tk.StringVar(value="pixel")  # 马赛克类型
        
        # 裁剪相关变量
        self.selected_ratio = tk.StringVar(value="自由")  # 裁剪比例
        self.rotate_angle_var = tk.IntVar(value=0)  # 旋转角度
    
    # 核心图片处理方法
    def open_image(self):
        """打开图片文件"""
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
                from models import DoodleEditor, DraggableTextWatermark, CropController, MosaicEditor
                self.doodle_editor = DoodleEditor(self.editing_image.copy())
                self.mosaic_editor = MosaicEditor(self.editing_image.copy())
                self.text_watermark = DraggableTextWatermark(self.editing_image.copy())
                self.crop_controller = CropController(self.editing_image.copy())

                self.history.clear()
                self._reset_view()
                
                # 检查status_label是否存在再销毁
                if hasattr(self.view, 'status_label') and self.view.status_label.winfo_exists():
                    self.view.status_label.destroy()
                
                self.view.show_panel("adjust")  # 默认打开调节面板
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
            cw = self.view.canvas.winfo_width()
            ch = self.view.canvas.winfo_height()
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
        try:
            display_img = None
            
            # 如果正在拖动水印，或者当前正在编辑水印，显示临时水印
            if (self.is_dragging_text or self.current_tool == "text") and self.text_watermark:
                # 生成带临时水印的预览图
                temp_img = self.text_watermark.apply()
                display_img = temp_img.resize((new_w, new_h),
                                            Image.Resampling.NEAREST if self.zoom_scale > 2 else Image.Resampling.LANCZOS)
            # 如果当前正在编辑涂鸦，显示临时涂鸦
            elif self.current_tool == "doodle" and self.doodle_editor:
                # 生成带临时涂鸦的预览图
                temp_img = self.doodle_editor.merge()
                display_img = temp_img.resize((new_w, new_h),
                                            Image.Resampling.NEAREST if self.zoom_scale > 2 else Image.Resampling.LANCZOS)
            # 如果当前正在编辑马赛克，显示临时马赛克
            elif self.current_tool == "mosaic" and self.mosaic_editor:
                # 生成带临时马赛克的预览图
                temp_img = self.mosaic_editor.merge()
                display_img = temp_img.resize((new_w, new_h),
                                            Image.Resampling.NEAREST if self.zoom_scale > 2 else Image.Resampling.LANCZOS)
            else:
                # 正常渲染，只显示已应用的水印
                display_img = self.preview_image.resize((new_w, new_h),
                                            Image.Resampling.NEAREST if self.zoom_scale > 2 else Image.Resampling.LANCZOS)
            
            self.view.tk_image = ImageTk.PhotoImage(display_img)

            # 3. 计算居中坐标 + 偏移量
            cx = self.view.canvas.winfo_width() // 2 + self.pan_offset_x
            cy = self.view.canvas.winfo_height() // 2 + self.pan_offset_y

            # 保存删除按钮状态
            show_delete = self.show_delete_button or self.show_sticker_delete_button
            self._hide_delete_button()

            self.view.canvas.delete("all")
            self.view.canvas.create_image(cx, cy, anchor=tk.CENTER, image=self.view.tk_image, tags="img")

            # 如果有裁剪框等覆盖层，需重新绘制
            if self.current_tool == "crop":
                self._draw_crop_rect(cx, cy, new_w, new_h)
        
            # 如果之前显示了删除按钮，重新绘制
            if show_delete:
                if self.text_watermark:
                    self.show_delete_button = True
                    self._show_delete_button()
                elif self.sticker_image:
                    self.show_sticker_delete_button = True
                    self._show_sticker_delete_button()
            
            # 绘制放大镜（只有在橡皮擦模式且正在擦除时才显示）
            if self.show_magnifier and self.preview_image:
                self._draw_magnifier(cx, cy, new_w, new_h)

        except Exception as e:
            error_msg = f"渲染错误: {str(e)}"
            print(error_msg)
            # 在画布上显示错误信息
            self.view.canvas.delete("all")
            self.view.canvas.create_text(
                self.view.canvas.winfo_width() // 2,
                self.view.canvas.winfo_height() // 2,
                text=error_msg,
                fill="red",
                font=("Arial", 12),
                tags="error"
            )
    
    def _apply_pending_changes(self):
        """应用当前面板的临时修改"""
        if self.current_tool == "adjust":
            # 调节是实时的，不需要特殊应用，因为 preview 已经是 adjust 后的结果
            # 但我们需要把 preview 固化到 editing_image
            if self.preview_image != self.editing_image:
                self._push_history()
                self.editing_image = self.preview_image.copy()
                self._reset_adjust_params()

        elif self.current_tool == "filter":
            # 切换工具时，应用当前滤镜效果
            if self.preview_image != self.editing_image:
                self._push_history()
                self.editing_image = self.preview_image.copy()

        elif self.current_tool == "crop":
            # 裁剪需要显式确认，切换工具时自动取消裁剪框
            self.is_cropping = False
            self.crop_start = None
            self.crop_end = None
            self.view.canvas.delete("overlay")
            self.view.canvas.config(cursor="")
        
        # 切换工具时隐藏删除按钮
        if self.show_delete_button or self.show_sticker_delete_button:
            self._hide_delete_button()
        
        # 切换工具时重置贴纸状态
        if self.sticker_image:
            # 如果有未确认的贴纸，重置状态
            self.sticker_image = None
            self.selected_sticker = None
            self.sticker_obj = None
            self.preview_image = self.editing_image.copy()
            self._update_canvas()
        
        # 切换工具时重置水印状态
        if self.text_watermark:
            # 如果有未确认的水印，重置状态
            self.text_watermark = None
            self.preview_image = self.editing_image.copy()
            self._update_canvas()
        
        # 切换工具时重置涂鸦和马赛克状态
        if self.current_tool in ["doodle", "mosaic"]:
            # 确保涂鸦和马赛克的未确认更改被丢弃
            self.doodle_editor = DoodleEditor(self.editing_image.copy())
            self.mosaic_editor = MosaicEditor(self.editing_image.copy())
            self.preview_image = self.editing_image.copy()
            self._update_canvas()
        
        # 重置所有拖动状态
        self.is_dragging_text = False
        self.is_dragging_sticker = False
        self.show_magnifier = False
    
    def _reset_adjust_params(self):
        """重置调节参数"""
        self.temp_adjustments = {k: 1.0 for k in self.temp_adjustments}

    def _on_adjust_change(self, key, value):
        self.temp_adjustments[key] = value
        # 实时处理 (Pipeline)
        if not self.editing_image:
            return

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
        self.view.show_panel("adjust")  # 重置滑块

    def _apply_filter_preview(self, mode):
        if not self.editing_image:
            return
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
        if not self.editing_image:
            return
        
        # 打开文件选择对话框，支持 .cube 和 .png 文件
        path = filedialog.askopenfilename(filetypes=[("LUT Files", "*.cube *.png"), ("All Files", "*.*")])
        if not path:
            return
        
        try:
            # 保存当前状态到撤销栈，以便用户可以撤销添加LUT的操作
            self._push_history()
            
            # 应用LUT效果
            from utils import apply_LUT
            self.preview_image = apply_LUT(self.editing_image, path)
            self._update_canvas()
            messagebox.showinfo("提示", "LUT滤镜已加载")
        except Exception as e:
            messagebox.showerror("错误", f"无法加载LUT文件: {str(e)}")

    def _confirm_filter(self):
        self._push_history()
        self.editing_image = self.preview_image.copy()
        # 更新其他功能实例
        from models import DoodleEditor, DraggableTextWatermark
        self.doodle_editor = DoodleEditor(self.editing_image.copy())
        self.text_watermark = DraggableTextWatermark(self.editing_image.copy())
        self._update_canvas()
        messagebox.showinfo("提示", "滤镜已应用")

    def _update_crop_ratio(self):
        if self.crop_controller:
            self.crop_controller.set_ratio(self.selected_ratio.get())
            # 如果已经有裁剪框，重新绘制
            if hasattr(self, 'crop_start') and hasattr(self, 'crop_end') and self.crop_start and self.crop_end:
                self._update_canvas()

    def _rotate_left(self):
        """左旋转90°"""
        if not self.editing_image: return
        
        self._push_history()
        # 左旋转90°（PIL的rotate方法，逆时针旋转）
        self.editing_image = self.editing_image.rotate(90, expand=True)
        self.preview_image = self.editing_image.copy()
        
        # 更新其他功能实例
        from models import DoodleEditor, DraggableTextWatermark, CropController
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
        from models import DoodleEditor, DraggableTextWatermark, CropController
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
        from models import DoodleEditor, DraggableTextWatermark, CropController
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
        from models import DoodleEditor, DraggableTextWatermark, CropController
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
        from models import DoodleEditor, DraggableTextWatermark, CropController
        self.doodle_editor = DoodleEditor(self.editing_image.copy())
        self.text_watermark = DraggableTextWatermark(self.editing_image.copy())
        self.crop_controller = CropController(self.editing_image.copy())
        
        # 重置旋转角度滑块
        self.rotate_angle_var.set(0)
        
        self._reset_view()
        self._update_canvas()

    def _init_crop_tool(self):
        self.is_cropping = True
        self.current_tool = "crop"  # 确保当前工具为裁剪
        self.view.canvas.config(cursor="cross")
        self.crop_start = None
        self.resize_mode = None  # 调整模式：None, 'n', 'ne', 'e', 'se', 's', 'sw', 'w', 'nw'
        self.resize_corner = None
        self.view.canvas.bind("<ButtonPress-1>", self._on_crop_press)
        self.view.canvas.bind("<B1-Motion>", self._on_crop_drag)
        self.view.canvas.bind("<ButtonRelease-1>", self._on_crop_release)
        self.view.canvas.bind("<Motion>", self._on_crop_motion)

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
                self.view.canvas.config(cursor="fleur")
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
                self.view.canvas.config(cursor="size_nw_se")
            elif (is_top and is_right) or (is_bottom and is_left):
                self.view.canvas.config(cursor="size_ne_sw")
            elif is_left or is_right:
                self.view.canvas.config(cursor="size_we")
            elif is_top or is_bottom:
                self.view.canvas.config(cursor="size_ns")
        elif is_inside:
            self.view.canvas.config(cursor="fleur")
        else:
            self.view.canvas.config(cursor="cross")

    def _do_crop(self):
        if not self.is_cropping or not self.crop_start or not self.crop_end:
            return
        
        # 确保x1 < x2, y1 < y2
        crop_x1 = min(self.crop_start[0], self.crop_end[0])
        crop_y1 = min(self.crop_start[1], self.crop_end[1])
        crop_x2 = max(self.crop_start[0], self.crop_end[0])
        crop_y2 = max(self.crop_start[1], self.crop_end[1])
        
        # 转换为图片坐标
        img_crop_start = self._screen_to_image(crop_x1, crop_y1)
        img_crop_end = self._screen_to_image(crop_x2, crop_y2)
        
        if img_crop_start and img_crop_end:
            self._push_history()
            # 确保坐标为整数
            crop_box = (int(img_crop_start[0]), int(img_crop_start[1]), int(img_crop_end[0]), int(img_crop_end[1]))
            # 执行裁剪
            self.editing_image = self.editing_image.crop(crop_box)
            self.preview_image = self.editing_image.copy()
            
            # 重新初始化所有功能实例
            from models import DoodleEditor, DraggableTextWatermark, CropController
            self.doodle_editor = DoodleEditor(self.editing_image.copy())
            self.text_watermark = DraggableTextWatermark(self.editing_image.copy())
            self.crop_controller = CropController(self.editing_image.copy())
            
            # 重置裁剪状态
            self.is_cropping = False
            self.crop_start = None
            self.crop_end = None
            self.view.canvas.config(cursor="")
            
            # 重置视图
            self._reset_view()
            
            # 更新画布
            self._update_canvas()

    def _restore_original(self):
        """恢复原始图像"""
        if self.original_image:
            self._push_history()
            self.editing_image = self.original_image.copy()
            self.preview_image = self.original_image.copy()
            self._reset_adjust_params()
            # 重新初始化所有功能实例
            from models import DoodleEditor, DraggableTextWatermark, CropController, MosaicEditor
            self.doodle_editor = DoodleEditor(self.editing_image.copy())
            self.mosaic_editor = MosaicEditor(self.editing_image.copy())
            self.text_watermark = DraggableTextWatermark(self.editing_image.copy())
            self.crop_controller = CropController(self.editing_image.copy())
            # 重置裁剪状态
            self.is_cropping = False
            self.crop_start = None
            self.crop_end = None
            self.view.canvas.config(cursor="")
            # 重置视图
            self._reset_view()
            # 更新画布
            self._update_canvas()

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
            canvas_w = self.view.canvas.winfo_width()
            canvas_h = self.view.canvas.winfo_height()
            
            # 确保x1 < x2, y1 < y2
            crop_x1 = min(x1, x2)
            crop_y1 = min(y1, y2)
            crop_x2 = max(x1, x2)
            crop_y2 = max(y1, y2)
            
            # 绘制半透明遮罩
            # 左侧遮罩
            self.view.canvas.create_rectangle(0, 0, crop_x1, canvas_h,
                                        fill="#000000", stipple="gray50", tags="overlay")
            # 右侧遮罩
            self.view.canvas.create_rectangle(crop_x2, 0, canvas_w, canvas_h,
                                        fill="#000000", stipple="gray50", tags="overlay")
            # 上侧遮罩
            self.view.canvas.create_rectangle(crop_x1, 0, crop_x2, crop_y1,
                                        fill="#000000", stipple="gray50", tags="overlay")
            # 下侧遮罩
            self.view.canvas.create_rectangle(crop_x1, crop_y2, crop_x2, canvas_h,
                                        fill="#000000", stipple="gray50", tags="overlay")
            
            # 画裁剪矩形
            self.view.canvas.create_rectangle(crop_x1, crop_y1, crop_x2, crop_y2,
                                     outline=COLORS["accent"], width=2, dash=(5, 2), tags="overlay")
            # 绘制裁剪框角点
            corner_size = 8
            corners = [
                (crop_x1 - corner_size, crop_y1 - corner_size, crop_x1 + corner_size, crop_y1 + corner_size),  # 左上
                (crop_x2 - corner_size, crop_y1 - corner_size, crop_x2 + corner_size, crop_y1 + corner_size),  # 右上
                (crop_x1 - corner_size, crop_y2 - corner_size, crop_x1 + corner_size, crop_y2 + corner_size),  # 左下
                (crop_x2 - corner_size, crop_y2 - corner_size, crop_x2 + corner_size, crop_y2 + corner_size)   # 右下
            ]
            for corner in corners:
                self.view.canvas.create_rectangle(*corner, fill=COLORS["accent"], outline="white", width=1, tags="overlay")

    def _choose_watermark_color(self):
        """选择水印文字颜色"""
        color = colorchooser.askcolor(initialcolor=f"#{self.watermark_color[0]:02x}{self.watermark_color[1]:02x}{self.watermark_color[2]:02x}")
        if color[1]:  # 使用十六进制颜色值
            # 转换为RGB元组
            rgb = tuple(int(color[1][i:i+2], 16) for i in (1, 3, 5))
            self.watermark_color = rgb
            # 更新预览
            self._update_text_preview()

    def _choose_stroke_color(self):
        """选择描边颜色"""
        color = colorchooser.askcolor(initialcolor=f"#{self.watermark_stroke_color[0]:02x}{self.watermark_stroke_color[1]:02x}{self.watermark_stroke_color[2]:02x}")
        if color[1]:  # 使用十六进制颜色值
            # 转换为RGB元组
            rgb = tuple(int(color[1][i:i+2], 16) for i in (1, 3, 5))
            self.watermark_stroke_color = rgb
            # 更新预览
            self._update_text_preview()

    def _update_text_preview(self):
        """更新文字水印预览"""
        if not self.editing_image:
            return
        
        # 创建新的水印对象，基于当前编辑图像
        is_time_watermark = self.watermark_type.get() == "time"
        self.text_watermark = DraggableTextWatermark(self.editing_image.copy(), is_time_watermark)
        
        # 如果是文字水印，获取输入的文字
        if not is_time_watermark:
            text = self.watermark_text_var.get()
            # 空文字时不显示任何内容
            self.text_watermark.set_text(text)
        
        # 设置水印样式
        size = self.watermark_size_var.get()
        alpha = self.watermark_alpha_var.get()
        stroke_width = self.watermark_stroke_width_var.get()
        
        # 设置水印样式
        self.text_watermark.set_style(
            self.watermark_color,
            size,
            alpha,
            self.watermark_stroke_color,
            stroke_width
        )
        
        # 更新画布
        self._update_canvas()
    
    def _add_text_watermark(self):
        """添加文字水印"""
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
        self.view.show_panel("text")
        
        # 隐藏删除按钮
        self._hide_delete_button()
        
        # 更新画布
        self._update_canvas()
        messagebox.showinfo("提示", "水印已添加到图片")

    def _on_text_watermark_press(self, event):
        """水印按下事件"""
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

        # 判断点击是否落在水印内
        if x1 <= px <= x2 and y1 <= py <= y2:
            # 进入拖动模式
            self.is_dragging_text = True
            # 计算偏移量：屏幕坐标 - 水印在屏幕上的坐标
            # 先将水印的图像坐标转换为屏幕坐标
            sx, sy = self._image_to_screen(self.text_watermark.x, self.text_watermark.y)
            self.text_drag_offset = (event.x - sx, event.y - sy)
            self.view.canvas.config(cursor="fleur")

    def _on_text_watermark_drag(self, event):
        """水印拖动事件"""
        if not self.is_dragging_text or not self.text_watermark:
            return
        
        # 计算新的水印屏幕位置
        new_sx = event.x - self.text_drag_offset[0]
        new_sy = event.y - self.text_drag_offset[1]
        
        # 转换为图像坐标
        new_px, new_py = self._screen_to_image(new_sx, new_sy)
        if new_px is None:
            return
        
        # 更新水印位置
        self.text_watermark.move_to(new_px, new_py)
        
        # 更新删除按钮位置
        self._hide_delete_button()
        self._show_delete_button()
        
        # 更新画布
        self._update_canvas()

    def _on_text_watermark_release(self, event):
        """水印释放事件"""
        self.is_dragging_text = False
        self.view.canvas.config(cursor="")

    def _on_text_watermark_right_click(self, event):
        """右键点击水印：显示删除按钮 ❌"""
        if not self.text_watermark:
            return

        # 检查是否点中了水印区域
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

        # 判断点击是否落在水印内
        if x1 <= px <= x2 and y1 <= py <= y2:
            # 显示删除按钮
            self._show_delete_button()
            self.show_delete_button = True

    def _choose_doodle_color(self):
        """选择画笔颜色"""
        color = colorchooser.askcolor(initialcolor=f"#{self.doodle_color[0]:02x}{self.doodle_color[1]:02x}{self.doodle_color[2]:02x}")
        if color[0]:
            self.doodle_color = tuple(map(int, color[0]))
            # 更新按钮颜色
            for widget in self.view.panel_content.winfo_children():
                if isinstance(widget, tk.Frame):
                    for child in widget.winfo_children():
                        if isinstance(child, tk.Button) and child.cget("width") == 2:
                            # 找到颜色选择按钮并更新
                            if hasattr(child, "command") and child.cget("command") == self._choose_doodle_color:
                                child.config(bg=f"#{self.doodle_color[0]:02x}{self.doodle_color[1]:02x}{self.doodle_color[2]:02x}")
                            break

    def _on_doodle_mode_change(self):
        """切换画笔/橡皮擦模式"""
        if self.doodle_editor:
            self.doodle_editor.set_mode(self.doodle_mode.get())
            # 更新笔刷大小，确保大小一致
            self.doodle_editor.set_brush(self.doodle_size_var.get(), self.doodle_color)
            # 初始时隐藏放大镜，只有在擦除时才显示
            self.show_magnifier = False
            self._update_canvas()

    def _on_doodle_size_change(self, value):
        """笔刷/橡皮擦大小变化事件"""
        size = int(value)
        if self.doodle_editor:
            self.doodle_editor.set_brush(size, self.doodle_color)

    def _on_doodle_mouse_move(self, event):
        """处理鼠标移动事件，更新放大镜位置"""
        # 只有在擦除状态下才显示放大镜
        if self.show_magnifier:
            # 更新放大镜位置
            self.magnifier_x, self.magnifier_y = event.x, event.y
            # 放大镜会在_update_canvas中自动绘制，这里只更新位置

    def _doodle_start(self, event):
        """涂鸦开始事件"""
        if not self.doodle_editor:
            return
        
        # 开始绘制/擦除时，如果是橡皮擦模式，显示放大镜
        current_mode = self.doodle_mode.get()
        if current_mode == "eraser":
            self.show_magnifier = True
            # 初始化放大镜位置
            self.magnifier_x, self.magnifier_y = event.x, event.y
        
        # 记录开始位置
        self.last_draw_pos = (event.x, event.y)
        
        # 初始化点列表，用于存储绘制路径点
        self.draw_points = []
        
        # 将第一个点转换为图片坐标并添加到点列表
        px, py = self._screen_to_image(event.x, event.y)
        if px is not None and py is not None:
            self.draw_points.append((px, py))
            # 绘制第一个点
            self.doodle_editor.draw_line(px, py, px, py)
            self._update_canvas()

    def _doodle_draw(self, event):
        """涂鸦绘制事件"""
        if not self.doodle_editor or not hasattr(self, "last_draw_pos") or not hasattr(self, "draw_points"):
            return
        
        # 转换为图片坐标
        px, py = self._screen_to_image(event.x, event.y)
        if px is None or py is None:
            return
        
        # 更新放大镜位置
        if self.show_magnifier:
            self.magnifier_x, self.magnifier_y = event.x, event.y
        
        # 绘制线条 - 使用图片坐标
        last_px, last_py = self.draw_points[-1]
        self.doodle_editor.draw_line(last_px, last_py, px, py)
        
        # 将点添加到点列表
        self.draw_points.append((px, py))
        
        # 更新画布
        self._update_canvas()

    def _doodle_end(self, event):
        """涂鸦结束事件"""
        if not self.doodle_editor:
            return
        
        # 绘制结束，隐藏放大镜
        self.show_magnifier = False
        
        # 清理临时属性
        if hasattr(self, "last_draw_pos"):
            delattr(self, "last_draw_pos")
        
        if hasattr(self, "draw_points"):
            delattr(self, "draw_points")
        
        self._update_canvas()

    def _apply_doodle(self):
        """应用涂鸦"""
        if not self.doodle_editor:
            return
        
        self._push_history()
        # 合并涂鸦到编辑图像
        self.editing_image = self.doodle_editor.merge()
        self.preview_image = self.editing_image.copy()
        
        # 重新初始化涂鸦编辑器
        self.doodle_editor = DoodleEditor(self.editing_image.copy())
        
        # 更新画布
        self._update_canvas()
        messagebox.showinfo("提示", "涂鸦已应用")

    def _choose_doodle_color(self):
        """选择画笔颜色"""
        # 打开颜色选择器
        color_code = colorchooser.askcolor(title="选择画笔颜色")
        if color_code and color_code[1]:
            self.brush_color = color_code[1]
            # 将十六进制颜色转换为RGBA
            r = int(self.brush_color[1:3], 16)
            g = int(self.brush_color[3:5], 16)
            b = int(self.brush_color[5:7], 16)
            self.doodle_color = (r, g, b, 255)
            if self.doodle_editor:
                self.doodle_editor.set_brush(self.doodle_size_var.get(), self.doodle_color)

    def _init_doodle_tool(self):
        """初始化涂鸦工具"""
        if not self.doodle_editor:
            self.doodle_editor = DoodleEditor(self.editing_image.copy())
        
        # 设置初始模式和大小
        self.doodle_editor.set_mode(self.doodle_mode.get())
        self.doodle_editor.set_brush(self.doodle_size_var.get(), self.doodle_color)
        
        # 绑定鼠标事件
        self.view.canvas.bind("<ButtonPress-1>", self._doodle_start)
        self.view.canvas.bind("<B1-Motion>", self._doodle_draw)
        self.view.canvas.bind("<ButtonRelease-1>", self._doodle_end)
        self.view.canvas.bind("<Motion>", self._on_doodle_mouse_move)
        
        # 设置光标
        self.view.canvas.config(cursor="dot")
        
        # 初始时隐藏放大镜
        self.show_magnifier = False
        self._update_canvas()

    def _on_mosaic_type_change(self):
        """马赛克类型变化事件"""
        if self.mosaic_editor:
            self.mosaic_editor.set_mosaic_params(self.mosaic_size_var.get(), self.mosaic_type_var.get())

    def _on_mosaic_size_change(self, value):
        """马赛克大小变化事件"""
        size = int(value)
        if self.mosaic_editor:
            self.mosaic_editor.set_mosaic_params(size, self.mosaic_type_var.get())

    def _set_mosaic_type(self, mosaic_type):
        """设置马赛克类型"""
        self.mosaic_type_var.set(mosaic_type)
        if self.mosaic_editor:
            self.mosaic_editor.set_mosaic_params(self.mosaic_size_var.get(), mosaic_type)

    def _init_mosaic_tool(self):
        """初始化马赛克工具"""
        if not self.mosaic_editor:
            self.mosaic_editor = MosaicEditor(self.editing_image.copy())
        
        # 设置初始参数
        self.mosaic_editor.set_mosaic_params(self.mosaic_size_var.get(), self.mosaic_type_var.get())
        
        # 绑定鼠标事件
        self.view.canvas.bind("<ButtonPress-1>", self._on_mosaic_press)
        self.view.canvas.bind("<B1-Motion>", self._on_mosaic_drag)
        self.view.canvas.bind("<ButtonRelease-1>", self._on_mosaic_release)
        
        # 设置光标
        self.view.canvas.config(cursor="cross")

    def _on_mosaic_press(self, event):
        """马赛克按下事件"""
        if not self.mosaic_editor:
            return
        
        # 转换为图片坐标
        px, py = self._screen_to_image(event.x, event.y)
        if px is None or py is None:
            return
        
        # 应用马赛克
        self.mosaic_editor.apply_mosaic_area(px, py)
        # 合并并更新预览
        self.preview_image = self.mosaic_editor.merge()
        self._update_canvas()

    def _on_mosaic_drag(self, event):
        """马赛克拖动事件"""
        if not self.mosaic_editor:
            return
        
        # 转换为图片坐标
        px, py = self._screen_to_image(event.x, event.y)
        if px is None or py is None:
            return
        
        # 应用马赛克
        self.mosaic_editor.apply_mosaic_area(px, py)
        # 合并并更新预览
        self.preview_image = self.mosaic_editor.merge()
        self._update_canvas()

    def _on_mosaic_release(self, event):
        """马赛克释放事件"""
        pass

    def _apply_mosaic(self):
        """应用马赛克"""
        if not self.mosaic_editor:
            return
        
        self._push_history()
        # 合并马赛克到编辑图像
        self.editing_image = self.mosaic_editor.merge()
        self.preview_image = self.editing_image.copy()
        
        # 重新初始化马赛克编辑器
        self.mosaic_editor = MosaicEditor(self.editing_image.copy())
        
        # 更新画布
        self._update_canvas()
        messagebox.showinfo("提示", "马赛克已应用")

    def _select_sticker(self, sticker_path):
        """选择贴纸"""
        try:
            self.selected_sticker = sticker_path
            # 使用DraggableSticker类创建贴纸对象
            if self.editing_image:
                from models import DraggableSticker
                self.sticker_obj = DraggableSticker(self.editing_image, sticker_path)
                self.sticker_image = self.sticker_obj.sticker
                self.sticker_pos = (self.editing_image.width // 2, self.editing_image.height // 2)
                self.sticker_scale = 1.0
                self.sticker_rotation = 0
                # 更新预览
                self._update_sticker_preview()
        except Exception as e:
            # 忽略无法打开的贴纸文件
            print(f"无法加载贴纸文件 {sticker_path}: {e}")
            messagebox.showerror("错误", f"无法加载贴纸文件: {e}")
            # 重置贴纸状态
            self.selected_sticker = None
            self.sticker_image = None
            self.sticker_obj = None

    def _update_sticker_preview(self):
        """更新贴纸预览"""
        if not self.editing_image or not self.sticker_obj:
            return
        
        # 使用DraggableSticker对象的apply方法更新预览
        self.preview_image = self.sticker_obj.apply()
        self._update_canvas()

    def _on_sticker_press(self, event):
        """贴纸拖动开始"""
        if not self.sticker_obj or not self.editing_image:
            return
        
        # 转换屏幕坐标到图片坐标
        px, py = self._screen_to_image(event.x, event.y)
        if px is None:
            return
        
        # 获取贴纸的边界框
        bbox = self.sticker_obj.get_bbox()
        # 计算贴纸的实际边界
        x1 = bbox[0]
        y1 = bbox[1]
        x2 = bbox[2]
        y2 = bbox[3]
        
        # 判断点击是否落在贴纸内
        if x1 <= px <= x2 and y1 <= py <= y2:
            # 进入拖动模式
            self.is_dragging_sticker = True
            # 计算偏移量：屏幕坐标 - 贴纸在屏幕上的坐标
            # 先将贴纸的图像坐标转换为屏幕坐标
            sx, sy = self._image_to_screen(self.sticker_obj.x, self.sticker_obj.y)
            self.sticker_drag_offset_x = event.x - sx
            self.sticker_drag_offset_y = event.y - sy
            self.view.canvas.config(cursor="fleur")

    def _on_sticker_drag(self, event):
        """贴纸拖动中"""
        if not self.is_dragging_sticker or not self.sticker_obj:
            return
        
        # 计算新的贴纸屏幕位置
        new_sx = event.x - self.sticker_drag_offset_x
        new_sy = event.y - self.sticker_drag_offset_y
        
        # 转换为图像坐标
        new_px, new_py = self._screen_to_image(new_sx, new_sy)
        if new_px is None:
            return
        
        # 更新贴纸位置
        self.sticker_obj.move_to(new_px, new_py)
        
        # 更新删除按钮位置
        if self.show_sticker_delete_button:
            self._hide_delete_button()
            self._show_sticker_delete_button()
        
        # 更新预览
        self._update_sticker_preview()

    def _on_sticker_release(self, event):
        """贴纸拖动结束"""
        if self.is_dragging_sticker:
            self.is_dragging_sticker = False
            self.view.canvas.config(cursor="")
            # 更新预览
            self._update_sticker_preview()

    def _on_sticker_right_click(self, event):
        """右键点击贴纸：显示删除按钮 ❌"""
        if not self.sticker_obj:
            return

        # 检查是否点中了贴纸区域
        px, py = self._screen_to_image(event.x, event.y)
        if px is None:
            return

        # 获取贴纸的边界框
        bbox = self.sticker_obj.get_bbox()
        # 计算贴纸的实际边界
        x1 = bbox[0]
        y1 = bbox[1]
        x2 = bbox[2]
        y2 = bbox[3]

        # 判断点击是否落在贴纸内
        if x1 <= px <= x2 and y1 <= py <= y2:
            # 显示删除按钮
            self._show_sticker_delete_button()
            self.show_sticker_delete_button = True

    def _confirm_sticker(self):
        """确认添加贴纸"""
        if not self.editing_image or not self.sticker_obj:
            messagebox.showinfo("提示", "请先选择一个贴纸")
            return
        
        self._push_history()
        
        # 将贴纸应用到编辑图像
        self.editing_image = self.preview_image.copy()
        
        # 更新预览图像为编辑图像的副本，此时已经包含了固定的贴纸
        self.preview_image = self.editing_image.copy()
        
        # 关键修复：清除贴纸对象
        # 这样就不会在原位置拖动时出现复制贴纸的问题
        # 只有当用户开始编辑新贴纸时，才会重新创建贴纸对象
        self.sticker_image = None
        self.selected_sticker = None
        self.sticker_obj = None
        self.sticker_scale = 1.0
        self.sticker_rotation = 0
        
        # 确保当前工具仍然是sticker，但此时没有活跃的贴纸对象
        self.view.show_panel("sticker")
        
        # 更新其他功能实例
        from models import DoodleEditor, DraggableTextWatermark, CropController
        self.doodle_editor = DoodleEditor(self.editing_image.copy())
        self.text_watermark = DraggableTextWatermark(self.editing_image.copy())
        self.crop_controller = CropController(self.editing_image.copy())
        
        self._hide_delete_button()
        self._update_canvas()
        messagebox.showinfo("提示", "贴纸已添加")

    def _delete_sticker(self, event=None):
        """删除当前贴纸"""
        if self.sticker_obj:
            self.sticker_image = None
            self.selected_sticker = None
            self.sticker_obj = None
            self.sticker_scale = 1.0
            self.sticker_rotation = 0
            self.preview_image = self.editing_image.copy()
            self._hide_delete_button()
            self._update_canvas()
    
    def _push_history(self):
        """保存当前 editing_image 到历史栈"""
        if self.editing_image:
            self.history.append(self.editing_image.copy())
            # 新操作时清空重做栈
            self.redo_history.clear()
            if len(self.history) > 15: self.history.pop(0)
    
    def undo(self):
        """撤销操作"""
        if self.history:
            # 先应用当前工具的未确认更改
            self._apply_pending_changes()
            
            # 将当前状态保存到重做栈
            self.redo_history.append(self.editing_image.copy())
            # 从撤销栈获取上一个状态
            self.editing_image = self.history.pop()
            self.preview_image = self.editing_image.copy()
            self._reset_adjust_params()
            
            # 重置所有工具状态
            self.current_tool = None
            self.is_cropping = False
            self.crop_start = None
            self.crop_end = None
            self.sticker_image = None
            self.selected_sticker = None
            self.sticker_obj = None
            self.text_watermark = None
            self.show_delete_button = False
            self.show_sticker_delete_button = False
            self.is_dragging_text = False
            self.is_dragging_sticker = False
            self.show_magnifier = False
            
            # 重新初始化所有功能实例，确保它们基于撤销后的图像
            from models import DoodleEditor, DraggableTextWatermark, CropController, MosaicEditor
            self.doodle_editor = DoodleEditor(self.editing_image.copy())
            self.mosaic_editor = MosaicEditor(self.editing_image.copy())
            self.text_watermark = DraggableTextWatermark(self.editing_image.copy())
            self.crop_controller = CropController(self.editing_image.copy())
            
            # 清空画布上的所有覆盖元素
            self.view.canvas.delete("overlay")
            self.view.canvas.delete("del_btn")
            self.view.canvas.delete("magnifier")
            
            # 重置光标
            self.view.canvas.config(cursor="")
            
            # 更新画布
            self._update_canvas()
            
            # 更新视图面板，确保显示正确的工具面板
            if hasattr(self.view, 'show_panel'):
                self.view.show_panel("adjust")
    
    def redo(self):
        """重做操作"""
        if self.redo_history:
            # 先应用当前工具的未确认更改
            self._apply_pending_changes()
            
            # 将当前状态保存到撤销栈
            self.history.append(self.editing_image.copy())
            # 从重做栈获取下一个状态
            self.editing_image = self.redo_history.pop()
            self.preview_image = self.editing_image.copy()
            self._reset_adjust_params()
            
            # 重置所有工具状态
            self.current_tool = None
            self.is_cropping = False
            self.crop_start = None
            self.crop_end = None
            self.sticker_image = None
            self.selected_sticker = None
            self.sticker_obj = None
            self.text_watermark = None
            self.show_delete_button = False
            self.show_sticker_delete_button = False
            self.is_dragging_text = False
            self.is_dragging_sticker = False
            self.show_magnifier = False
            
            # 重新初始化所有功能实例，确保它们基于重做后的图像
            from models import DoodleEditor, DraggableTextWatermark, CropController, MosaicEditor
            self.doodle_editor = DoodleEditor(self.editing_image.copy())
            self.mosaic_editor = MosaicEditor(self.editing_image.copy())
            self.text_watermark = DraggableTextWatermark(self.editing_image.copy())
            self.crop_controller = CropController(self.editing_image.copy())
            
            # 清空画布上的所有覆盖元素
            self.view.canvas.delete("overlay")
            self.view.canvas.delete("del_btn")
            self.view.canvas.delete("magnifier")
            
            # 重置光标
            self.view.canvas.config(cursor="")
            
            # 更新画布
            self._update_canvas()
            
            # 更新视图面板，确保显示正确的工具面板
            if hasattr(self.view, 'show_panel'):
                self.view.show_panel("adjust")
    
    def auto_enhance(self):
        """自动增强图片"""
        if not self.editing_image: return
        self._push_history()
        from PIL import ImageOps
        self.editing_image = ImageOps.autocontrast(self.editing_image)
        self.preview_image = self.editing_image.copy()
        self._update_canvas()
    
    def batch_convert_format(self):
        """批量转换格式功能"""
        pass
    
    def batch_add_watermark(self):
        """批量添加水印功能"""
        pass
    
    def rename_image(self):
        """重命名当前图片文件"""
        if not self.editing_image or not self.filepath:
            messagebox.showinfo("提示", "请先打开一张图片")
            return
        
        # 获取当前文件名和目录
        import os
        dir_path, old_name = os.path.split(self.filepath)
        old_name_no_ext, ext = os.path.splitext(old_name)
        
        # 弹出对话框让用户输入新文件名
        new_name = simpledialog.askstring("重命名", f"当前文件名: {old_name}\n请输入新文件名:", initialvalue=old_name_no_ext)
        
        if new_name:
            # 验证新文件名的有效性
            if not new_name.strip():
                messagebox.showerror("错误", "文件名不能为空")
                return
            
            # 检查文件名中是否包含非法字符
            invalid_chars = '<>:"/\\|?*'
            if any(char in invalid_chars for char in new_name):
                messagebox.showerror("错误", "文件名包含非法字符")
                return
            
            # 构建新的文件路径
            new_filepath = os.path.join(dir_path, new_name + ext)
            
            # 检查新文件名是否已存在
            if os.path.exists(new_filepath):
                messagebox.showerror("错误", "文件名已存在")
                return
            
            try:
                # 重命名文件
                os.rename(self.filepath, new_filepath)
                # 更新filepath属性
                self.filepath = new_filepath
                messagebox.showinfo("成功", "图片重命名成功")
            except Exception as e:
                messagebox.showerror("错误", f"重命名失败: {str(e)}")
    
    def save_image(self):
        """保存图片"""
        if not self.editing_image: return
        
        # 询问是否需要压缩
        response = messagebox.askyesno("压缩选项", "是否需要压缩图片？")
        
        if response:
            # 显示压缩设置对话框
            target_kb = simpledialog.askinteger("压缩设置", "目标大小 (KB):", minvalue=50, maxvalue=2048, initialvalue=800)
            if target_kb is None:
                return  # 用户取消
            
            # 执行压缩
            from utils import auto_compress
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
    
    def _hide_delete_button(self):
        """隐藏删除按钮"""
        if hasattr(self.view, 'canvas'):
            self.view.canvas.delete("del_btn")
        self.show_delete_button = False
        self.show_sticker_delete_button = False

    def _update_sticker_style(self, scale, rotation):
        """更新贴纸样式：缩放比例和旋转角度"""
        if not self.sticker_obj:
            return
        
        # 更新贴纸样式
        self.sticker_obj.set_style(scale, rotation)
        # 更新预览
        self._update_sticker_preview()
        # 更新删除按钮位置
        if self.show_sticker_delete_button:
            self._hide_delete_button()
            self._show_sticker_delete_button()

    def _show_delete_button(self):
        """在水印左上角绘制删除按钮"""
        self._hide_delete_button()
        
        if not self.text_watermark:
            return
        
        # 获取水印的边界框
        bbox = self.text_watermark.get_bbox()
        # 计算水印的实际宽度和高度
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        
        # 计算水印左上角映射到画布位置
        sx, sy = self._image_to_screen(self.text_watermark.x, self.text_watermark.y)
        
        btn_size = 22
        
        # 画圆 - 左上角位置
        self.view.canvas.create_oval(
            sx, sy - btn_size,
            sx + btn_size, sy,
            fill="#ff4444", outline="white", width=2, tags="del_btn"
        )
        
        # 写 ×
        self.view.canvas.create_text(
            sx + btn_size // 2, sy - btn_size // 2,
            text="×", fill="white", font=("Arial", 15, "bold"), tags="del_btn"
        )
        
        self.view.canvas.tag_bind("del_btn", "<Button-1>", self._delete_watermark)
    
    def _show_sticker_delete_button(self):
        """在贴纸左上角绘制删除按钮"""
        self._hide_delete_button()
        
        if not self.sticker_obj:
            return
        
        # 获取贴纸的边界框
        bbox = self.sticker_obj.get_bbox()
        # 计算贴纸的实际宽度和高度
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        
        # 计算贴纸左上角映射到画布位置
        sx, sy = self._image_to_screen(bbox[0], bbox[1])
        
        btn_size = 22
        
        # 画圆 - 左上角位置
        self.view.canvas.create_oval(
            sx, sy - btn_size,
            sx + btn_size, sy,
            fill="#ff4444", outline="white", width=2, tags="del_btn"
        )
        
        # 写 ×
        self.view.canvas.create_text(
            sx + btn_size // 2, sy - btn_size // 2,
            text="×", fill="white", font=("Arial", 15, "bold"), tags="del_btn"
        )
        
        self.view.canvas.tag_bind("del_btn", "<Button-1>", self._delete_sticker)
    
    def _delete_watermark(self, event=None):
        """删除水印"""
        self.text_watermark = None
        self.preview_image = self.editing_image.copy()
        self._hide_delete_button()
        self._update_canvas()
    
    def _delete_sticker(self, event=None):
        """删除贴纸"""
        self.sticker_image = None
        self.selected_sticker = None
        self.sticker_obj = None
        self.sticker_scale = 1.0
        self.sticker_rotation = 0
        self.preview_image = self.editing_image.copy()
        self._hide_delete_button()
        self._update_canvas()
    
    def _image_to_screen(self, px, py):
        """将图片坐标转换为屏幕坐标"""
        if not self.preview_image:
            return None, None
        
        # 获取画布中心
        cx = self.view.canvas.winfo_width() // 2 + self.pan_offset_x
        cy = self.view.canvas.winfo_height() // 2 + self.pan_offset_y
        
        # 获取图片显示尺寸
        img_w = int(self.preview_image.width * self.zoom_scale)
        img_h = int(self.preview_image.height * self.zoom_scale)
        
        # 计算图片在画布上的显示区域
        left = cx - img_w // 2
        top = cy - img_h // 2
        
        # 转换为屏幕坐标
        sx = left + px * self.zoom_scale
        sy = top + py * self.zoom_scale
        
        return sx, sy
    
    def _screen_to_image(self, sx, sy):
        """将屏幕坐标转换为图片坐标"""
        if not self.preview_image:
            return None, None
        
        # 获取画布中心
        cx = self.view.canvas.winfo_width() // 2 + self.pan_offset_x
        cy = self.view.canvas.winfo_height() // 2 + self.pan_offset_y
        
        # 获取图片显示尺寸
        img_w = int(self.preview_image.width * self.zoom_scale)
        img_h = int(self.preview_image.height * self.zoom_scale)
        
        # 计算图片在画布上的显示区域
        left = cx - img_w // 2
        top = cy - img_h // 2
        right = left + img_w
        bottom = top + img_h
        
        # 检查点击是否在图片区域内
        if not (left <= sx <= right and top <= sy <= bottom):
            return None, None
        
        # 转换为图片坐标
        px = (sx - left) / self.zoom_scale
        py = (sy - top) / self.zoom_scale
        
        return px, py
    
    def _draw_magnifier(self, cx, cy, new_w, new_h):
        """绘制放大镜视图"""
        # 计算放大镜显示的区域
        # 首先获取鼠标位置对应的图片坐标
        mouse_x, mouse_y = self.magnifier_x, self.magnifier_y
        
        # 转换为图片上的实际坐标
        img_x = (mouse_x - cx + new_w // 2) / self.zoom_scale
        img_y = (mouse_y - cy + new_h // 2) / self.zoom_scale
        
        # 计算放大区域的大小
        magnifier_radius = self.magnifier_size // 2
        img_radius = int(magnifier_radius / self.magnifier_scale / self.zoom_scale)
        
        # 边界检查
        x1 = max(0, int(img_x - img_radius))
        y1 = max(0, int(img_y - img_radius))
        x2 = min(self.preview_image.width, int(img_x + img_radius))
        y2 = min(self.preview_image.height, int(img_y + img_radius))
        
        if x1 >= x2 or y1 >= y2:
            return
        
        # 裁剪放大区域
        magnified_region = self.preview_image.crop((x1, y1, x2, y2))
        
        # 放大区域
        scaled_w = int((x2 - x1) * self.magnifier_scale)
        scaled_h = int((y2 - y1) * self.magnifier_scale)
        from PIL import Image
        magnified_region = magnified_region.resize((scaled_w, scaled_h), Image.Resampling.LANCZOS)
        
        # 转换为Tkinter可用的图像
        from PIL import ImageTk
        magnified_tk = ImageTk.PhotoImage(magnified_region)
        
        # 计算放大镜在画布上的位置
        # 将放大镜固定显示在左上角，参考示例图
        mag_x = 20  # 固定在左上角
        mag_y = 20  # 固定在左上角
        
        # 1. 绘制放大镜阴影，增强立体感
        shadow_offset = 3
        self.view.canvas.create_oval(
            mag_x + shadow_offset, mag_y + shadow_offset,
            mag_x + self.magnifier_size + shadow_offset, mag_y + self.magnifier_size + shadow_offset,
            fill="#000000", outline="", width=0, tags="magnifier", stipple="gray50"
        )
        
        # 2. 绘制放大镜边框
        self.view.canvas.create_oval(
            mag_x, mag_y,
            mag_x + self.magnifier_size, mag_y + self.magnifier_size,
            fill="white", outline="#333333", width=2, tags="magnifier"
        )
        
        # 3. 绘制放大后的图像
        self.view.canvas.create_image(
            mag_x + magnifier_radius,
            mag_y + magnifier_radius,
            image=magnified_tk, tags="magnifier"
        )
        
        # 4. 绘制放大镜内边框
        self.view.canvas.create_oval(
            mag_x + 2, mag_y + 2,
            mag_x + self.magnifier_size - 2, mag_y + self.magnifier_size - 2,
            fill="", outline="#666666", width=1, tags="magnifier"
        )
        
        # 5. 计算放大镜中心位置
        center_x = mag_x + magnifier_radius
        center_y = mag_y + magnifier_radius
        
        # 6. 绘制当前橡皮擦位置的圆（在原图上），使用实际笔刷大小
        brush_size = 20  # 默认笔刷大小
        self.view.canvas.create_oval(
            mouse_x - int(brush_size * self.zoom_scale / 2),
            mouse_y - int(brush_size * self.zoom_scale / 2),
            mouse_x + int(brush_size * self.zoom_scale / 2),
            mouse_y + int(brush_size * self.zoom_scale / 2),
            outline="white", width=2, tags="magnifier"
        )
        
        # 7. 在放大镜中心绘制圆形指示器
        mag_brush_size = int(brush_size * self.magnifier_scale)
        self.view.canvas.create_oval(
            center_x - mag_brush_size / 2,
            center_y - mag_brush_size / 2,
            center_x + mag_brush_size / 2,
            center_y + mag_brush_size / 2,
            outline="white", width=2, tags="magnifier"
        )
        
        # 8. 在放大镜中心绘制十字交叉线，叠加在圆形指示器上
        cross_size = 8
        self.view.canvas.create_line(
            center_x - cross_size, center_y,
            center_x + cross_size, center_y,
            fill="white", width=1, tags="magnifier"
        )
        self.view.canvas.create_line(
            center_x, center_y - cross_size,
            center_x, center_y + cross_size,
            fill="white", width=1, tags="magnifier"
        )
        
        # 9. 在圆形指示器中心绘制十字交叉点，增强定位效果
        dot_size = 2
        self.view.canvas.create_rectangle(
            center_x - dot_size, center_y - dot_size,
            center_x + dot_size, center_y + dot_size,
            fill="white", outline="", tags="magnifier"
        )
        
        # 10. 绘制指示线，连接鼠标和放大镜
        self.view.canvas.create_line(
            mouse_x, mouse_y,
            center_x, center_y,
            fill="#333333", width=1, dash=(4, 2), tags="magnifier"
        )
        
        # 保存图像引用，防止被垃圾回收
        self.magnified_tk = magnified_tk
    

