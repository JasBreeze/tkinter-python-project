from PIL import Image
from io import BytesIO


def parse_cube_file(cube_path):
    """
    解析.cube格式的3D LUT文件
    :param cube_path: .cube文件路径
    :return: lut_size, lut_data
    """
    with open(cube_path, 'r') as f:
        content = f.readlines()
    
    # 解析LUT尺寸
    lut_size = 32  # 默认尺寸
    for line in content:
        line = line.strip()
        if line.startswith('LUT_3D_SIZE'):
            lut_size = int(line.split()[-1])
            break
    
    # 提取LUT数据
    lut_data = []
    for line in content:
        line = line.strip()
        if line and not line.startswith('#') and not line.startswith('TITLE') and not line.startswith('LUT_3D_SIZE'):
            values = list(map(float, line.split()))
            if len(values) >= 3:
                # 将LUT值从[0,1]范围转换为[0,255]范围
                r = int(values[0] * 255)
                g = int(values[1] * 255)
                b = int(values[2] * 255)
                lut_data.append((r, g, b))
    
    return lut_size, lut_data


def apply_3d_lut(img, lut_size, lut_data):
    """
    应用3D LUT到图像
    :param img: 原始图像
    :param lut_size: LUT尺寸
    :param lut_data: LUT数据列表，每个元素是(r, g, b)元组
    :return: 应用LUT后的图像
    """
    # 转换为RGB模式
    img_rgb = img.convert('RGB')
    width, height = img_rgb.size
    
    # 创建新图像
    result = Image.new('RGB', (width, height))
    pixels = result.load()
    
    # 遍历每个像素，应用LUT
    for y in range(height):
        for x in range(width):
            # 获取原始像素值
            r, g, b = img_rgb.getpixel((x, y))
            
            # 将RGB值映射到LUT尺寸范围
            r_index = int((r / 255.0) * (lut_size - 1))
            g_index = int((g / 255.0) * (lut_size - 1))
            b_index = int((b / 255.0) * (lut_size - 1))
            
            # 计算LUT索引
            lut_index = r_index + g_index * lut_size + b_index * lut_size * lut_size
            
            # 获取LUT映射后的颜色
            if lut_index < len(lut_data):
                pixels[x, y] = lut_data[lut_index]
            else:
                # 如果索引超出范围，使用原始颜色
                pixels[x, y] = (r, g, b)
    
    return result


def apply_LUT(img, lut_img_or_path):
    """
    应用LUT效果
    :param img: 原始图像
    :param lut_img_or_path: LUT图像或LUT文件路径
    :return: 应用LUT后的图像
    """
    # 如果是路径，根据扩展名处理
    if isinstance(lut_img_or_path, str):
        if lut_img_or_path.lower().endswith('.cube'):
            # 解析.cube文件
            lut_size, lut_data = parse_cube_file(lut_img_or_path)
            # 应用3D LUT
            return apply_3d_lut(img, lut_size, lut_data)
        else:
            # 加载图片
            lut_img = Image.open(lut_img_or_path).convert("RGB")
            # 应用图片LUT
            lut = lut_img.resize(img.size)
            return Image.blend(img, lut, 0.6)
    else:
        # 应用图片LUT
        lut = lut_img_or_path.resize(img.size)
        return Image.blend(img, lut, 0.6)


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
