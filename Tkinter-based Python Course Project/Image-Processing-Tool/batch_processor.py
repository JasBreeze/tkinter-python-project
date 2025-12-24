from PIL import Image
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import time

class BatchProcessor:
    """批量处理工具类，提供批量转换格式和批量添加水印功能"""
    
    # 支持的输入格式
    SUPPORTED_INPUT_FORMATS = [".JPG", ".PNG", ".BMP", ".JPEG", ".WEBP", ".GIF", ".TIFF", ".TIF", ".ICO", ".PPM"]
    
    # 支持的输出格式
    SUPPORTED_OUTPUT_FORMATS = ["JPG", "PNG", "BMP", "WEBP", "TIFF", "ICO"]
    
    def __init__(self, parent=None):
        self.parent = parent
        self.is_processing = False
        self.current_thread = None
    
    def select_files(self, title="选择文件"):
        """选择多个图片文件"""
        filetypes = [
            ("图片文件", "*.jpg *.png *.bmp *.jpeg *.webp *.gif *.tiff *.tif *.ico *.ppm"),
            ("所有文件", "*.*")
        ]
        files = filedialog.askopenfilenames(title=title, filetypes=filetypes)
        return list(files)
    
    def select_directory(self, title="选择文件夹"):
        """选择文件夹"""
        directory = filedialog.askdirectory(title=title)
        return directory
    
    def get_files_from_directory(self, directory, recursive=False, include_subfolders=False):
        """获取文件夹中的所有图片文件"""
        image_files = []
        
        def scan_folder(folder):
            for filename in os.listdir(folder):
                file_path = os.path.join(folder, filename)
                if os.path.isfile(file_path):
                    ext = os.path.splitext(filename)[1].upper()
                    if ext in self.SUPPORTED_INPUT_FORMATS:
                        image_files.append(file_path)
                elif os.path.isdir(file_path) and (recursive or include_subfolders):
                    scan_folder(file_path)
        
        scan_folder(directory)
        return image_files
    
    def batch_convert_format(self):
        """批量转换图片格式 - 优化版本"""
        # 创建转换对话框
        dialog = tk.Toplevel(self.parent)
        dialog.title("批量转换格式 - 优化版")
        dialog.geometry("650x700")  # 增加高度，确保按钮可见
        dialog.resizable(True, True)
        
        # 居中显示
        if self.parent:
            dialog.transient(self.parent)
            dialog.grab_set()
        
        # 创建主框架并添加滚动条
        main_container = ttk.Frame(dialog)
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
        # 选择模式：文件或文件夹
        mode_var = tk.StringVar(value="folder")
        
        # 选择的文件
        selected_files = []
        input_dir = ""
        output_dir = ""
        
        # 目标格式
        target_format_var = tk.StringVar(value="PNG")
        
        # 转换质量
        quality_var = tk.IntVar(value=95)
        
        # 重命名选项
        rename_var = tk.BooleanVar(value=False)
        prefix_var = tk.StringVar(value="")
        suffix_var = tk.StringVar(value="")
        
        # 文件过滤选项
        recursive_var = tk.BooleanVar(value=False)
        
        # 进度条
        progress_var = tk.DoubleVar(value=0)
        
        # 当前处理文件
        current_file_var = tk.StringVar(value="")
        
        def select_input():
            """选择输入文件或文件夹"""
            nonlocal selected_files, input_dir
            if mode_var.get() == "folder":
                dir_path = self.select_directory("选择要转换的图片文件夹")
                if dir_path:
                    input_dir = dir_path
                    input_label.config(text=f"输入文件夹: {dir_path}")
                    # 预览文件数量
                    files = self.get_files_from_directory(dir_path, recursive=recursive_var.get())
                    file_count_label.config(text=f"找到图片: {len(files)} 张")
                    if files:
                        file_list_text.config(state="normal")
                        file_list_text.delete(1.0, tk.END)
                        for file in files[:20]:  # 显示前20个文件
                            file_list_text.insert(tk.END, f"• {os.path.basename(file)}\n")
                        if len(files) > 20:
                            file_list_text.insert(tk.END, f"... 还有 {len(files) - 20} 个文件\n")
                        file_list_text.config(state="disabled")
            else:
                files = self.select_files("选择要转换的图片文件")
                if files:
                    selected_files = files
                    input_label.config(text=f"选择文件: {len(files)} 个")
                    file_count_label.config(text=f"选择图片: {len(files)} 张")
                    file_list_text.config(state="normal")
                    file_list_text.delete(1.0, tk.END)
                    for file in files[:20]:
                        file_list_text.insert(tk.END, f"• {os.path.basename(file)}\n")
                    if len(files) > 20:
                        file_list_text.insert(tk.END, f"... 还有 {len(files) - 20} 个文件\n")
                    file_list_text.config(state="disabled")
        
        def select_output():
            """选择输出文件夹"""
            nonlocal output_dir
            dir_path = self.select_directory("选择输出文件夹")
            if dir_path:
                output_dir = dir_path
                output_label.config(text=f"输出文件夹: {dir_path}")
        
        def update_recursive():
            """更新递归选项"""
            if mode_var.get() == "folder" and input_dir:
                files = self.get_files_from_directory(input_dir, recursive=recursive_var.get())
                file_count_label.config(text=f"找到图片: {len(files)} 张")
                file_list_text.config(state="normal")
                file_list_text.delete(1.0, tk.END)
                for file in files[:20]:
                    file_list_text.insert(tk.END, f"• {os.path.basename(file)}\n")
                if len(files) > 20:
                    file_list_text.insert(tk.END, f"... 还有 {len(files) - 20} 个文件\n")
                file_list_text.config(state="disabled")
        
        def start_conversion_thread():
            """在后台线程中执行转换"""
            if self.is_processing:
                return
            
            self.is_processing = True
            self.current_thread = threading.Thread(target=start_conversion)
            self.current_thread.daemon = True
            self.current_thread.start()
        
        def start_conversion():
            """开始转换"""
            nonlocal selected_files
            
            # 验证输入
            if mode_var.get() == "folder":
                if not input_dir:
                    messagebox.showerror("错误", "请选择输入文件夹")
                    return
                selected_files = self.get_files_from_directory(input_dir, recursive=recursive_var.get())
            else:
                if not selected_files:
                    messagebox.showerror("错误", "请选择要转换的文件")
                    return
            
            if not output_dir:
                messagebox.showerror("错误", "请选择输出文件夹")
                return
            
            if not selected_files:
                messagebox.showerror("错误", "没有找到可转换的图片文件")
                return
            
            target_format = target_format_var.get().upper()
            quality = quality_var.get()
            
            # 禁用控件
            input_btn.config(state="disabled")
            output_btn.config(state="disabled")
            start_btn.config(state="disabled")
            mode_frame.config(state="disabled")
            format_frame.config(state="disabled")
            quality_frame.config(state="disabled")
            rename_frame.config(state="disabled")
            filter_frame.config(state="disabled")
            
            # 重置进度条
            progress_var.set(0)
            progress_bar.update()
            
            # 转换统计
            success_count = 0
            failed_count = 0
            skipped_count = 0
            failed_files = []
            
            # 执行转换
            total_files = len(selected_files)
            for i, file_path in enumerate(selected_files):
                try:
                    current_file_var.set(f"正在处理: {os.path.basename(file_path)}")
                    
                    # 检查文件是否存在
                    if not os.path.exists(file_path):
                        skipped_count += 1
                        continue
                    
                    # 打开图片
                    img = Image.open(file_path)
                    
                    # 转换为RGB模式（如果是RGBA或P模式）
                    if img.mode not in ["RGB", "L"]:
                        img = img.convert("RGB")
                    
                    # 生成输出文件名
                    filename = os.path.basename(file_path)
                    name_without_ext = os.path.splitext(filename)[0]
                    
                    # 应用重命名规则
                    if rename_var.get():
                        prefix = prefix_var.get().strip()
                        suffix = suffix_var.get().strip()
                        new_name = f"{prefix}{name_without_ext}{suffix}"
                    else:
                        new_name = name_without_ext
                    
                    output_filename = f"{new_name}.{target_format.lower()}"
                    output_path = os.path.join(output_dir, output_filename)
                    
                    # 检查输出文件是否已存在
                    if os.path.exists(output_path):
                        # 自动重命名
                        counter = 1
                        while os.path.exists(output_path):
                            output_filename = f"{new_name}_{counter}.{target_format.lower()}"
                            output_path = os.path.join(output_dir, output_filename)
                            counter += 1
                    
                    # 保存图片
                    save_options = {}
                    if target_format == "JPG":
                        save_options = {"quality": quality, "optimize": True}
                    elif target_format == "WEBP":
                        save_options = {"quality": quality, "method": 6}
                    elif target_format == "TIFF":
                        save_options = {"compression": "tiff_lzw"}
                    
                    img.save(output_path, **save_options)
                    success_count += 1
                    
                except Exception as e:
                    failed_count += 1
                    failed_files.append(f"{os.path.basename(file_path)}: {str(e)}")
                
                # 更新进度
                progress = (i + 1) / total_files * 100
                progress_var.set(progress)
                progress_label.config(text=f"转换进度: {int(progress)}% ({i+1}/{total_files})")
                progress_bar.update()
                dialog.update_idletasks()
                
                # 小延迟，让UI有机会更新
                time.sleep(0.01)
            
            # 启用控件
            input_btn.config(state="normal")
            output_btn.config(state="normal")
            start_btn.config(state="normal")
            mode_frame.config(state="normal")
            format_frame.config(state="normal")
            quality_frame.config(state="normal")
            rename_frame.config(state="normal")
            filter_frame.config(state="normal")
            
            current_file_var.set("")
            self.is_processing = False
            
            # 显示转换结果
            result_msg = f"批量转换完成！\n成功转换: {success_count} 张\n转换失败: {failed_count} 张"
            if skipped_count > 0:
                result_msg += f"\n跳过文件: {skipped_count} 张"
            
            if failed_count > 0:
                result_msg += f"\n\n失败列表:\n" + "\n".join(failed_files[:10])
                if len(failed_files) > 10:
                    result_msg += f"\n... 还有 {len(failed_files) - 10} 个文件转换失败"
            
            messagebox.showinfo("转换完成", result_msg)
        
        # 创建可滚动的主框架
        canvas = tk.Canvas(main_container)
        scrollbar = ttk.Scrollbar(main_container, orient="vertical", command=canvas.yview)
        main_frame = ttk.Frame(canvas, padding="20")
        
        main_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=main_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill=tk.BOTH, expand=True)
        scrollbar.pack(side="right", fill=tk.Y)
        
        # 选择模式
        mode_frame = ttk.LabelFrame(main_frame, text="选择模式", padding="10")
        mode_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Radiobutton(mode_frame, text="文件夹", variable=mode_var, value="folder", 
                       command=update_recursive).pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(mode_frame, text="文件", variable=mode_var, value="file",
                       command=update_recursive).pack(side=tk.LEFT, padx=10)
        
        # 文件过滤选项
        filter_frame = ttk.LabelFrame(main_frame, text="文件过滤", padding="10")
        filter_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Checkbutton(filter_frame, text="包含子文件夹", variable=recursive_var,
                       command=update_recursive).pack(side=tk.LEFT, padx=10)
        
        # 输入选择
        input_frame = ttk.LabelFrame(main_frame, text="输入", padding="10")
        input_frame.pack(fill=tk.X, pady=(0, 10))
        
        input_btn = ttk.Button(input_frame, text="选择输入", command=select_input)
        input_btn.pack(side=tk.RIGHT, padx=5)
        
        input_label = ttk.Label(input_frame, text="未选择输入", anchor=tk.W)
        input_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        file_count_label = ttk.Label(input_frame, text="找到图片: 0 张", anchor=tk.W)
        file_count_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # 文件列表预览
        file_list_frame = ttk.LabelFrame(main_frame, text="文件预览", padding="10")
        file_list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        file_list_text = tk.Text(file_list_frame, height=6, wrap=tk.WORD)
        scrollbar = ttk.Scrollbar(file_list_frame, orient=tk.VERTICAL, command=file_list_text.yview)
        file_list_text.configure(yscrollcommand=scrollbar.set)
        file_list_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        file_list_text.config(state="disabled")
        
        # 输出选择
        output_frame = ttk.LabelFrame(main_frame, text="输出", padding="10")
        output_frame.pack(fill=tk.X, pady=(0, 10))
        
        output_btn = ttk.Button(output_frame, text="选择输出文件夹", command=select_output)
        output_btn.pack(side=tk.RIGHT, padx=5)
        
        output_label = ttk.Label(output_frame, text="未选择输出文件夹", anchor=tk.W)
        output_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # 格式选择
        format_frame = ttk.LabelFrame(main_frame, text="目标格式", padding="10")
        format_frame.pack(fill=tk.X, pady=(0, 10))
        
        for fmt in self.SUPPORTED_OUTPUT_FORMATS:
            ttk.Radiobutton(format_frame, text=fmt, variable=target_format_var, value=fmt).pack(side=tk.LEFT, padx=10)
        
        # 质量设置
        quality_frame = ttk.LabelFrame(main_frame, text="转换质量", padding="10")
        quality_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(quality_frame, text="质量: ").pack(side=tk.LEFT, padx=5)
        ttk.Scale(quality_frame, from_=1, to=100, variable=quality_var, orient=tk.HORIZONTAL).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Label(quality_frame, textvariable=quality_var, width=5).pack(side=tk.LEFT, padx=5)
        
        # 重命名选项
        rename_frame = ttk.LabelFrame(main_frame, text="重命名选项", padding="10")
        rename_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Checkbutton(rename_frame, text="启用重命名", variable=rename_var).pack(side=tk.LEFT, padx=5)
        
        ttk.Label(rename_frame, text="前缀:").pack(side=tk.LEFT, padx=5)
        ttk.Entry(rename_frame, textvariable=prefix_var, width=10).pack(side=tk.LEFT, padx=5)
        
        ttk.Label(rename_frame, text="后缀:").pack(side=tk.LEFT, padx=5)
        ttk.Entry(rename_frame, textvariable=suffix_var, width=10).pack(side=tk.LEFT, padx=5)
        
        # 进度条
        progress_frame = ttk.LabelFrame(main_frame, text="转换进度", padding="10")
        progress_frame.pack(fill=tk.X, pady=(0, 10))
        
        current_file_label = ttk.Label(progress_frame, textvariable=current_file_var)
        current_file_label.pack(fill=tk.X, pady=5)
        
        progress_bar = ttk.Progressbar(progress_frame, variable=progress_var, maximum=100, mode="determinate")
        progress_bar.pack(fill=tk.X, pady=5)
        
        progress_label = ttk.Label(progress_frame, text="转换进度: 0%")
        progress_label.pack(fill=tk.X, pady=5)
        
        # 按钮
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=10)
        
        start_btn = ttk.Button(btn_frame, text="确认并执行转换", command=start_conversion_thread)
        start_btn.pack(side=tk.RIGHT, padx=5)
        
        ttk.Button(btn_frame, text="取消", command=dialog.destroy).pack(side=tk.RIGHT, padx=5)
        
        # 运行对话框
        if self.parent:
            self.parent.wait_window(dialog)
        else:
            dialog.mainloop()

    def batch_add_watermark(self):
        """批量添加水印"""
        # 创建水印对话框
        dialog = tk.Toplevel(self.parent)
        dialog.title("批量添加水印")
        dialog.geometry("650x700")  # 增加高度，确保按钮可见
        dialog.resizable(True, True)
        
        # 居中显示
        if self.parent:
            dialog.transient(self.parent)
            dialog.grab_set()
        
        # 创建主框架并添加滚动条
        main_container = ttk.Frame(dialog)
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 选择模式：文件或文件夹
        mode_var = tk.StringVar(value="folder")
        
        # 选择的文件
        selected_files = []
        input_dir = ""
        output_dir = ""
        
        # 水印类型
        watermark_type_var = tk.StringVar(value="text")
        
        # 文字水印设置
        text_var = tk.StringVar(value="水印")
        font_size_var = tk.IntVar(value=42)
        opacity_var = tk.IntVar(value=180)
        
        # 颜色设置
        text_color_var = tk.StringVar(value="#FFFFFF")
        stroke_color_var = tk.StringVar(value="#000000")
        stroke_width_var = tk.IntVar(value=2)
        
        # 水印位置
        position_var = tk.StringVar(value="右下角")
        offset_x_var = tk.IntVar(value=50)
        offset_y_var = tk.IntVar(value=50)
        
        # 进度条
        progress_var = tk.DoubleVar(value=0)
        
        def select_input():
            """选择输入文件或文件夹"""
            nonlocal selected_files, input_dir
            if mode_var.get() == "folder":
                dir_path = self.select_directory("选择要添加水印的图片文件夹")
                if dir_path:
                    input_dir = dir_path
                    input_label.config(text=f"输入文件夹: {dir_path}")
                    # 预览文件数量
                    files = self.get_files_from_directory(dir_path)
                    file_count_label.config(text=f"找到图片: {len(files)} 张")
            else:
                files = self.select_files("选择要添加水印的图片文件")
                if files:
                    selected_files = files
                    input_label.config(text=f"选择文件: {len(files)} 个")
                    file_count_label.config(text=f"选择图片: {len(files)} 张")
        
        def select_output():
            """选择输出文件夹"""
            nonlocal output_dir
            dir_path = self.select_directory("选择输出文件夹")
            if dir_path:
                output_dir = dir_path
                output_label.config(text=f"输出文件夹: {dir_path}")
        
        def select_color(var):
            """选择颜色"""
            color = tk.colorchooser.askcolor(parent=dialog, initialcolor=var.get())
            if color[1]:
                var.set(color[1])
        
        def start_add_watermark():
            """开始添加水印"""
            nonlocal selected_files
            
            # 验证输入
            if mode_var.get() == "folder":
                if not input_dir:
                    messagebox.showerror("错误", "请选择输入文件夹")
                    return
                selected_files = self.get_files_from_directory(input_dir)
            else:
                if not selected_files:
                    messagebox.showerror("错误", "请选择要添加水印的文件")
                    return
            
            if not output_dir:
                messagebox.showerror("错误", "请选择输出文件夹")
                return
            
            if watermark_type_var.get() == "text" and not text_var.get().strip():
                messagebox.showerror("错误", "水印文字不能为空")
                return
            
            # 禁用控件
            input_btn.config(state="disabled")
            output_btn.config(state="disabled")
            start_btn.config(state="disabled")
            mode_frame.config(state="disabled")
            type_frame.config(state="disabled")
            text_frame.config(state="disabled")
            position_frame.config(state="disabled")
            color_frame.config(state="disabled")
            
            # 重置进度条
            progress_var.set(0)
            progress_bar.update()
            
            # 添加水印统计
            success_count = 0
            failed_count = 0
            failed_files = []
            
            # 执行添加水印
            total_files = len(selected_files)
            for i, file_path in enumerate(selected_files):
                try:
                    # 打开图片
                    img = Image.open(file_path).convert("RGB")
                    img_width, img_height = img.size
                    
                    # 创建水印
                    from models import DraggableTextWatermark
                    watermark = DraggableTextWatermark(img)
                    
                    # 设置水印文字和样式
                    watermark.set_text(text_var.get())
                    
                    # 转换颜色
                    text_color = tuple(int(text_color_var.get()[i:i+2], 16) for i in (1, 3, 5))
                    stroke_color = tuple(int(stroke_color_var.get()[i:i+2], 16) for i in (1, 3, 5))
                    
                    watermark.set_style(
                        text_color,
                        font_size_var.get(),
                        opacity_var.get(),
                        stroke_color,
                        stroke_width_var.get()
                    )
                    
                    # 获取水印文字的边界框
                    bbox = watermark.get_bbox()
                    text_width = bbox[2] - bbox[0]
                    text_height = bbox[3] - bbox[1]
                    
                    # 计算水印位置
                    position = position_var.get()
                    offset_x = offset_x_var.get()
                    offset_y = offset_y_var.get()
                    
                    if position == "左上角":
                        x = offset_x
                        y = offset_y
                    elif position == "右上角":
                        x = img_width - text_width - offset_x
                        y = offset_y
                    elif position == "左下角":
                        x = offset_x
                        y = img_height - text_height - offset_y
                    elif position == "右下角":
                        x = img_width - text_width - offset_x
                        y = img_height - text_height - offset_y
                    elif position == "上居中":
                        x = (img_width - text_width) // 2 + offset_x
                        y = offset_y
                    elif position == "下居中":
                        x = (img_width - text_width) // 2 + offset_x
                        y = img_height - text_height - offset_y
                    elif position == "左居中":
                        x = offset_x
                        y = (img_height - text_height) // 2 + offset_y
                    elif position == "右居中":
                        x = img_width - text_width - offset_x
                        y = (img_height - text_height) // 2 + offset_y
                    elif position == "居中":
                        x = (img_width - text_width) // 2 + offset_x
                        y = (img_height - text_height) // 2 + offset_y
                    else:
                        x = img_width - text_width - offset_x
                        y = img_height - text_height - offset_y
                    
                    # 设置水印位置
                    watermark.move_to(x, y)
                    
                    # 应用水印
                    img_with_watermark = watermark.apply()
                    
                    # 保存图片
                    filename = os.path.basename(file_path)
                    output_path = os.path.join(output_dir, filename)
                    img_with_watermark.save(output_path, quality=95)
                    
                    success_count += 1
                except Exception as e:
                    failed_count += 1
                    failed_files.append(f"{os.path.basename(file_path)}: {str(e)}")
                
                # 更新进度
                progress = (i + 1) / total_files * 100
                progress_var.set(progress)
                progress_label.config(text=f"添加进度: {int(progress)}%")
                progress_bar.update()
                dialog.update_idletasks()
            
            # 启用控件
            input_btn.config(state="normal")
            output_btn.config(state="normal")
            start_btn.config(state="normal")
            mode_frame.config(state="normal")
            type_frame.config(state="normal")
            text_frame.config(state="normal")
            position_frame.config(state="normal")
            color_frame.config(state="normal")
            
            # 显示添加结果
            result_msg = f"批量添加水印完成！\n成功添加: {success_count} 张\n添加失败: {failed_count} 张"
            if failed_count > 0:
                result_msg += f"\n\n失败列表:\n" + "\n".join(failed_files[:10])
                if len(failed_files) > 10:
                    result_msg += f"\n... 还有 {len(failed_files) - 10} 个文件添加失败"
            
            messagebox.showinfo("添加完成", result_msg)
        
        # 创建可滚动的主框架
        canvas = tk.Canvas(main_container)
        scrollbar = ttk.Scrollbar(main_container, orient="vertical", command=canvas.yview)
        main_frame = ttk.Frame(canvas, padding="20")
        
        main_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=main_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill=tk.BOTH, expand=True)
        scrollbar.pack(side="right", fill=tk.Y)
        
        # 选择模式
        mode_frame = ttk.LabelFrame(main_frame, text="选择模式", padding="10")
        mode_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Radiobutton(mode_frame, text="文件夹", variable=mode_var, value="folder").pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(mode_frame, text="文件", variable=mode_var, value="file").pack(side=tk.LEFT, padx=10)
        
        # 输入选择
        input_frame = ttk.LabelFrame(main_frame, text="输入", padding="10")
        input_frame.pack(fill=tk.X, pady=(0, 10))
        
        input_btn = ttk.Button(input_frame, text="选择输入", command=select_input)
        input_btn.pack(side=tk.RIGHT, padx=5)
        
        input_label = ttk.Label(input_frame, text="未选择输入", anchor=tk.W)
        input_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        file_count_label = ttk.Label(input_frame, text="找到图片: 0 张", anchor=tk.W)
        file_count_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # 输出选择
        output_frame = ttk.LabelFrame(main_frame, text="输出", padding="10")
        output_frame.pack(fill=tk.X, pady=(0, 10))
        
        output_btn = ttk.Button(output_frame, text="选择输出文件夹", command=select_output)
        output_btn.pack(side=tk.RIGHT, padx=5)
        
        output_label = ttk.Label(output_frame, text="未选择输出文件夹", anchor=tk.W)
        output_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # 水印类型
        type_frame = ttk.LabelFrame(main_frame, text="水印类型", padding="10")
        type_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Radiobutton(type_frame, text="文字水印", variable=watermark_type_var, value="text").pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(type_frame, text="图片水印", variable=watermark_type_var, value="image").pack(side=tk.LEFT, padx=10)
        
        # 文字水印设置
        text_frame = ttk.LabelFrame(main_frame, text="文字水印设置", padding="10")
        text_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 文字输入
        ttk.Label(text_frame, text="水印文字: ").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Entry(text_frame, textvariable=text_var).grid(row=0, column=1, columnspan=3, padx=5, pady=5, sticky=tk.EW)
        
        # 字体大小
        ttk.Label(text_frame, text="字体大小: ").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Scale(text_frame, from_=10, to=200, variable=font_size_var, orient=tk.HORIZONTAL).grid(row=1, column=1, columnspan=2, padx=5, pady=5, sticky=tk.EW)
        ttk.Label(text_frame, textvariable=font_size_var).grid(row=1, column=3, padx=5, pady=5, width=5)
        
        # 透明度
        ttk.Label(text_frame, text="透明度: ").grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Scale(text_frame, from_=0, to=255, variable=opacity_var, orient=tk.HORIZONTAL).grid(row=2, column=1, columnspan=2, padx=5, pady=5, sticky=tk.EW)
        ttk.Label(text_frame, textvariable=opacity_var).grid(row=2, column=3, padx=5, pady=5, width=5)
        
        # 颜色设置
        color_frame = ttk.LabelFrame(main_frame, text="颜色设置", padding="10")
        color_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 文字颜色
        ttk.Label(color_frame, text="文字颜色: ").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Entry(color_frame, textvariable=text_color_var).grid(row=0, column=1, padx=5, pady=5, sticky=tk.EW)
        ttk.Button(color_frame, text="选择", command=lambda: select_color(text_color_var)).grid(row=0, column=2, padx=5, pady=5)
        
        # 描边颜色
        ttk.Label(color_frame, text="描边颜色: ").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Entry(color_frame, textvariable=stroke_color_var).grid(row=1, column=1, padx=5, pady=5, sticky=tk.EW)
        ttk.Button(color_frame, text="选择", command=lambda: select_color(stroke_color_var)).grid(row=1, column=2, padx=5, pady=5)
        
        # 描边宽度
        ttk.Label(color_frame, text="描边宽度: ").grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Scale(color_frame, from_=0, to=10, variable=stroke_width_var, orient=tk.HORIZONTAL).grid(row=2, column=1, columnspan=2, padx=5, pady=5, sticky=tk.EW)
        ttk.Label(color_frame, textvariable=stroke_width_var).grid(row=2, column=3, padx=5, pady=5, width=5)
        
        # 位置设置
        position_frame = ttk.LabelFrame(main_frame, text="位置设置", padding="10")
        position_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 位置选择
        positions = ["左上角", "右上角", "左下角", "右下角", "上居中", "下居中", "左居中", "右居中", "居中"]
        position_combo = ttk.Combobox(position_frame, textvariable=position_var, values=positions, state="readonly")
        position_combo.pack(side=tk.LEFT, padx=5, pady=5)
        
        # 偏移设置
        offset_frame = ttk.Frame(position_frame)
        offset_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)
        
        ttk.Label(offset_frame, text="水平偏移: ").grid(row=0, column=0, padx=5, pady=2, sticky=tk.W)
        ttk.Scale(offset_frame, from_=-200, to=200, variable=offset_x_var, orient=tk.HORIZONTAL).grid(row=0, column=1, padx=5, pady=2, sticky=tk.EW)
        ttk.Label(offset_frame, textvariable=offset_x_var).grid(row=0, column=2, padx=5, pady=2, width=5)
        
        ttk.Label(offset_frame, text="垂直偏移: ").grid(row=1, column=0, padx=5, pady=2, sticky=tk.W)
        ttk.Scale(offset_frame, from_=-200, to=200, variable=offset_y_var, orient=tk.HORIZONTAL).grid(row=1, column=1, padx=5, pady=2, sticky=tk.EW)
        ttk.Label(offset_frame, textvariable=offset_y_var).grid(row=1, column=2, padx=5, pady=2, width=5)
        
        # 进度条
        progress_frame = ttk.LabelFrame(main_frame, text="添加进度", padding="10")
        progress_frame.pack(fill=tk.X, pady=(0, 10))
        
        progress_bar = ttk.Progressbar(progress_frame, variable=progress_var, maximum=100, mode="determinate")
        progress_bar.pack(fill=tk.X, pady=5)
        
        progress_label = ttk.Label(progress_frame, text="添加进度: 0%")
        progress_label.pack(fill=tk.X, pady=5)
        
        # 按钮
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=20)
        
        start_btn = ttk.Button(btn_frame, text="确认并执行添加水印", command=start_add_watermark)
        start_btn.pack(side=tk.RIGHT, padx=5)
        
        ttk.Button(btn_frame, text="取消", command=dialog.destroy).pack(side=tk.RIGHT, padx=5)
        
        # 运行对话框
        if self.parent:
            self.parent.wait_window(dialog)
        else:
            dialog.mainloop()