from PIL import Image, ImageDraw
import os

def create_simple_frame():
    """創建簡約風格相框"""
    img = Image.new('RGBA', (1080, 1080), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # 繪製白色邊框，帶有陰影效果
    border_width = 20
    shadow_offset = 5
    
    # 繪製陰影
    draw.rectangle(
        (shadow_offset, shadow_offset, 1080-shadow_offset, 1080-shadow_offset),
        fill=(0, 0, 0, 50)
    )
    
    # 繪製白色邊框
    draw.rectangle(
        (0, 0, 1080, 1080),
        outline=(255, 255, 255, 255),
        width=border_width
    )
    
    return img

def create_cute_frame():
    """創建可愛風格相框"""
    img = Image.new('RGBA', (1080, 1080), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # 繪製粉色圓角邊框
    border_width = 25
    corner_radius = 50
    
    # 繪製四個圓角
    draw.ellipse((0, 0, corner_radius*2, corner_radius*2), fill=(255, 192, 203, 255))
    draw.ellipse((1080-corner_radius*2, 0, 1080, corner_radius*2), fill=(255, 192, 203, 255))
    draw.ellipse((0, 1080-corner_radius*2, corner_radius*2, 1080), fill=(255, 192, 203, 255))
    draw.ellipse((1080-corner_radius*2, 1080-corner_radius*2, 1080, 1080), fill=(255, 192, 203, 255))
    
    # 繪製連接線
    draw.rectangle((corner_radius, 0, 1080-corner_radius, border_width), fill=(255, 192, 203, 255))
    draw.rectangle((corner_radius, 1080-border_width, 1080-corner_radius, 1080), fill=(255, 192, 203, 255))
    draw.rectangle((0, corner_radius, border_width, 1080-corner_radius), fill=(255, 192, 203, 255))
    draw.rectangle((1080-border_width, corner_radius, 1080, 1080-corner_radius), fill=(255, 192, 203, 255))
    
    return img

def create_vintage_frame():
    """創建復古風格相框"""
    img = Image.new('RGBA', (1080, 1080), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # 使用復古棕色
    vintage_color = (139, 69, 19, 255)
    border_width = 30
    
    # 繪製雙層邊框
    draw.rectangle((0, 0, 1080, 1080), outline=vintage_color, width=border_width)
    draw.rectangle((border_width+10, border_width+10, 
                   1080-border_width-10, 1080-border_width-10), 
                   outline=vintage_color, width=2)
    
    return img

def create_holiday_frame():
    """創建節日風格相框"""
    img = Image.new('RGBA', (1080, 1080), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # 使用紅色
    holiday_color = (255, 0, 0, 255)
    border_width = 25
    
    # 繪製基本邊框
    draw.rectangle((0, 0, 1080, 1080), outline=holiday_color, width=border_width)
    
    # 在四角添加裝飾
    corner_size = 100
    for x, y in [(0, 0), (1080-corner_size, 0), 
                 (0, 1080-corner_size), (1080-corner_size, 1080-corner_size)]:
        # 繪製角落裝飾
        draw.line((x, y, x+corner_size, y), fill=holiday_color, width=border_width)
        draw.line((x, y, x, y+corner_size), fill=holiday_color, width=border_width)
    
    return img

def main():
    # 確保輸出目錄存在
    os.makedirs('static/frames', exist_ok=True)
    
    # 生成並保存所有相框
    frames = {
        'simple.png': create_simple_frame(),
        'cute.png': create_cute_frame(),
        'vintage.png': create_vintage_frame(),
        'holiday.png': create_holiday_frame()
    }
    
    for filename, frame in frames.items():
        output_path = os.path.join('static/frames', filename)
        frame.save(output_path, 'PNG')
        print(f'已生成相框：{filename}')

if __name__ == '__main__':
    main()
