from PIL import Image, ImageDraw, ImageFilter, ImageFont

class DoodleEditor:
    def __init__(self, base_img: Image.Image):
        self.base = base_img
        self.layer = Image.new("RGBA", base_img.size, (0, 0, 0, 0))  # 透明图层
        self.draw = ImageDraw.Draw(self.layer)
        self.size = 20
        self.color = (255, 0, 0, 255)
        self.mode = "brush"  # "brush" or "eraser"

    def set_brush(self, size, color):
        self.size = size
        self.color = color

    def set_mode(self, mode):
        self.mode = mode

    def draw_line(self, x1, y1, x2, y2):
        """绘制平滑的线条或橡皮擦"""
        if self.mode == "eraser":
            # 橡皮擦模式：创建遮罩并清除图层对应区域
            mask = Image.new("L", self.layer.size, 0)
            ImageDraw.Draw(mask).line((x1, y1, x2, y2), fill=255, width=self.size)
            self.layer.paste((0, 0, 0, 0), (0, 0), mask)
        else:
            # 画笔模式：正常绘制彩色线条
            self.draw.line((x1, y1, x2, y2), fill=self.color, width=self.size)

    def merge(self):
        return Image.alpha_composite(self.base.convert("RGBA"), self.layer).convert("RGB")

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
        """应用马赛克效果到指定区域"""
        r = self.size // 2
        # 将坐标转换为整数，修复TypeError
        box = tuple(int(coord) for coord in (x - r, y - r, x + r, y + r))
        # 边界检查
        box = (max(0, box[0]), max(0, box[1]), min(self.base.width, box[2]), min(self.base.height, box[3]))
        if box[0] >= box[2] or box[1] >= box[3]:
            return
        
        region = self.base_copy.crop(box)
        
        if self.type == "pixel":
            # 像素化马赛克
            pixel_size = max(2, min(20, self.size // 12))
            small = region.resize((pixel_size, pixel_size), Image.NEAREST)
            mosaic = small.resize(region.size, Image.NEAREST)
        elif self.type == "blur":
            # 模糊马赛克
            blur_radius = max(5, min(30, self.size // 6))
            mosaic = region.filter(ImageFilter.GaussianBlur(radius=blur_radius))
        elif self.type == "triangle":
            # 三角形马赛克效果
            small_size = max(4, min(16, self.size // 15))
            small = region.resize((small_size, small_size), Image.NEAREST)
            mosaic = small.resize(region.size, Image.Resampling.NEAREST)
            mosaic = mosaic.filter(ImageFilter.EDGE_ENHANCE_MORE)
            mosaic = mosaic.filter(ImageFilter.SHARPEN)
            mosaic = mosaic.filter(ImageFilter.SHARPEN)
        elif self.type == "hexagon":
            # 六边形马赛克效果
            small_size = max(6, min(20, self.size // 12))
            small = region.resize((small_size, small_size), Image.NEAREST)
            mosaic = small.resize(region.size, Image.Resampling.LANCZOS)
            mosaic = mosaic.filter(ImageFilter.EDGE_ENHANCE_MORE)
            mosaic = mosaic.filter(ImageFilter.SHARPEN)
        elif self.type == "circle":
            # 圆形马赛克效果
            small_size = max(4, min(18, self.size // 11))
            small = region.resize((small_size, small_size), Image.BICUBIC)
            mosaic = small.resize(region.size, Image.Resampling.BICUBIC)
            mosaic = mosaic.filter(ImageFilter.GaussianBlur(radius=1))
            mosaic = mosaic.filter(ImageFilter.EDGE_ENHANCE_MORE)
        else:
            # 默认像素化
            pixel_size = max(2, min(20, self.size // 12))
            small = region.resize((pixel_size, pixel_size), Image.NEAREST)
            mosaic = small.resize(region.size, Image.NEAREST)
        
        self.layer.paste(mosaic, box)

    def merge(self):
        return Image.alpha_composite(self.base.convert("RGBA"), self.layer).convert("RGB")

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
        self.x = int(x)
        self.y = int(y)

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

class DraggableSticker:
    """可拖动 + 可删除 + 支持大小调整 + 支持旋转的贴纸"""

    def __init__(self, base_img, sticker_path):
        self.base = base_img
        self.sticker_path = sticker_path
        self.original_sticker = Image.open(sticker_path).convert("RGBA")
        self.sticker = self.original_sticker.copy()
        
        # 默认大小为原始贴纸的50%，但不超过图片的1/3
        max_size = min(base_img.width, base_img.height) // 3
        original_width, original_height = self.sticker.size
        scale_factor = min(0.5, max_size / max(original_width, original_height))
        
        self.original_width = int(original_width * scale_factor)
        self.original_height = int(original_height * scale_factor)
        self.sticker = self.sticker.resize((self.original_width, self.original_height), Image.LANCZOS)
        
        # 默认放在中心
        self.x = base_img.width // 2
        self.y = base_img.height // 2
        
        # 旋转角度
        self.rotation = 0
        
        # 缩放比例
        self.scale = 1.0
        
        # 更新宽高（旋转前的宽高）
        self.width = self.original_width
        self.height = self.original_height
        
    def set_style(self, scale, rotation):
        """设置贴纸样式：缩放比例和旋转角度"""
        self.scale = scale
        self.rotation = rotation
        
        # 应用缩放和旋转
        original_width, original_height = self.original_sticker.size
        new_width = int(original_width * self.scale)
        new_height = int(original_height * self.scale)
        
        # 保存旋转前的宽高（用于白框）
        self.original_width = new_width
        self.original_height = new_height
        
        # 先缩放
        scaled_sticker = self.original_sticker.resize((new_width, new_height), Image.LANCZOS)
        
        # 再旋转
        self.sticker = scaled_sticker.rotate(self.rotation, expand=True, resample=Image.BICUBIC)
        
        # 更新宽高（旋转后的宽高）
        self.width, self.height = self.sticker.size
    
    def get_original_bbox(self):
        """获取旋转前的边界框（用于绘制白框）"""
        # 计算旋转前的边界框
        x1 = self.x - self.original_width // 2
        y1 = self.y - self.original_height // 2
        x2 = x1 + self.original_width
        y2 = y1 + self.original_height
        return (x1, y1, x2, y2)
    
    def move_to(self, x, y):
        """绝对移动（用于拖动）"""
        self.x = int(x)
        self.y = int(y)
    
    def get_bbox(self):
        """获取贴纸的像素边界框"""
        # 计算贴纸在图片上的位置
        x1 = self.x - self.width // 2
        y1 = self.y - self.height // 2
        x2 = x1 + self.width
        y2 = y1 + self.height
        
        return (x1, y1, x2, y2)
    
    def apply(self):
        """真正绘制到新图层，用于预览和最终应用"""
        img = self.base.convert("RGBA")
        layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
        
        # 计算贴纸在图层上的位置
        x = self.x - self.width // 2
        y = self.y - self.height // 2
        
        # 确保贴纸不会超出图片边界
        x = max(0, min(x, img.width - self.width))
        y = max(0, min(y, img.height - self.height))
        
        # 绘制贴纸 - 确保坐标为整数
        layer.paste(self.sticker, (int(x), int(y)), self.sticker)
        
        return Image.alpha_composite(img, layer).convert("RGB")

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

        # 确保x1 < x2, y1 < y2
        start_x = min(x1, x2)
        start_y = min(y1, y2)
        end_x = max(x1, x2)
        end_y = max(y1, y2)
        
        # 计算当前裁剪框的宽度和高度
        current_w = end_x - start_x
        current_h = end_y - start_y
        
        # 获取目标宽高比
        rw, rh = self.ratio
        target_ratio = rw / rh
        
        # 计算新的宽度和高度
        if current_w / current_h > target_ratio:
            # 当前宽度过大，根据高度计算新宽度
            new_w = current_h * target_ratio
            new_h = current_h
        else:
            # 当前高度过大，根据宽度计算新高度
            new_h = current_w / target_ratio
            new_w = current_w
        
        # 计算新的结束坐标，保持起始点不变
        new_end_x = start_x + new_w
        new_end_y = start_y + new_h
        
        # 恢复原始方向
        if x1 > x2:
            start_x, new_end_x = new_end_x, start_x
        if y1 > y2:
            start_y, new_end_y = new_end_y, start_y
        
        return start_x, start_y, new_end_x, new_end_y

    def crop(self, box):
        return self.img.crop(box)
