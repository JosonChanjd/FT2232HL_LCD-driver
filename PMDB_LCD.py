"""
PMDB LCD驱动 - Python版本
基于UC1638控制器的128x128像素LCD驱动
从C语言PMDB_lcd.c转换而来
"""

import time
from typing import List, Optional, Tuple
from ftdi_spi_interface import FTD2XXSPIInterface
from lcd_fonts import LCDFonts

class PMDBLCD:
    """PMDB LCD驱动类"""
    
    # 显示参数
    PMDB_PAGES_16 = 16
    PMDB_COLS = 128
    PMDB_ROWS = 128  # 16页 * 8行 = 128行
    
    def __init__(self, spi_interface: FTD2XXSPIInterface):
        """
        初始化LCD驱动
        
        Args:
            spi_interface: FTDI SPI接口实例
        """
        self.spi = spi_interface
        self.contrast = 170
        self.display_buffer = [0] * (self.PMDB_PAGES_16 * self.PMDB_COLS)
        
    
    
    def init_controller_pmdb_uc1638(self) -> bool:
        """
        初始化UC1638控制器
        
        Returns:
            bool: 操作是否成功
        """
        try:
            # 系统复位
            self.spi.LCD_Command(0xe1)
            self.spi.LCD_Data(0xe2)
            time.sleep(0.002)
            
            # 设置显示模式
            self.spi.LCD_Command(0xa4)  # 设置所有像素开启
            self.spi.LCD_Command(0xa6)  # 正常显示模式
            
            # MTP控制
            self.spi.LCD_Command(0xb8)
            self.spi.LCD_Data(0x00)
            
            # 内部VLCD设置
            self.spi.LCD_Command(0x2d)  # 设置泵控制
            self.spi.LCD_Command(0x20)  # 设置温度补偿
            self.spi.LCD_Command(0xea)  # 设置偏置
            
            # 设置对比度
            self.spi.LCD_Command(0x81)  # 设置PM
            self.spi.LCD_Data(self.contrast)  # 对比度值
            
            # 设置帧率
            self.spi.LCD_Command(0xa3)  # 设置帧率
            
            # N_LINE反转
            self.spi.LCD_Command(0xc8)
            self.spi.LCD_Data(0x2F)
            
            # 设置RAM地址控制
            self.spi.LCD_Command(0x89)  # CA/PA地址控制
            self.spi.LCD_Command(0x95)  # 设置显示模式
            
            # 设置COM1
            self.spi.LCD_Command(0x84)
            
            # 设置COM结束
            self.spi.LCD_Command(0xf1)
            self.spi.LCD_Data(127)  # COM结束地址
            
            # LCD映射控制
            self.spi.LCD_Command(0xC4)  # My=0, Mx=1
            
            # 设置COM扫描功能
            self.spi.LCD_Command(0x86)  # 隔行扫描
            
            # 滚动行设置
            self.spi.LCD_Command(0x40)  # 无滚动
            self.spi.LCD_Command(0x50)
            
            # 设置列地址
            self.spi.LCD_Command(0x04)
            self.spi.LCD_Data(55)  # 起始列地址
            
            # 设置页地址
            self.spi.LCD_Command(0x60 | 0)  # 页地址LSB
            self.spi.LCD_Command(0x70)      # 页地址MSB
            
            # 设置窗口程序
            self.spi.LCD_Command(0xf4)  # 窗口起始列
            self.spi.LCD_Data(55)
            self.spi.LCD_Command(0xf6)  # 窗口结束列
            self.spi.LCD_Data(182)
            self.spi.LCD_Command(0xf5)  # 窗口起始页
            self.spi.LCD_Data(0)
            self.spi.LCD_Command(0xf7)  # 窗口结束页
            self.spi.LCD_Data(15)
            self.spi.LCD_Command(0xf9)  # 窗口程序使能
            
            # 设置显示模式
            self.spi.LCD_Command(0xc9)
            self.spi.LCD_Data(0xad)  # 黑白模式
            
            return True
            
        except Exception as e:
            print(f"UC1638初始化失败: {str(e)}")
            return False
    
    def pmdb_init(self) -> bool:
        """
        初始化PMDB LCD
        
        Returns:
            bool: 初始化是否成功
        """
        try:
            # LCD复位
            #self.lcd_reset()
            self.spi.LCD_Reset()
            # 初始化控制器
            return self.init_controller_pmdb_uc1638()
            
        except Exception as e:
            print(f"PMDB初始化失败: {str(e)}")
            return False
    
    def lcd_flush(self) -> bool:
        """
        刷新显示缓冲区到LCD
        
        Returns:
            bool: 操作是否成功
        """
        try:
            buffer = self.display_buffer
            
            for page in range(self.PMDB_PAGES_16):
                # 设置页地址
                self.spi.LCD_Command(0x60 | (page & 0x0F))  # 页地址LSB
                self.spi.LCD_Command(0x70 | (page >> 4))    # 页地址MSB
                
                # 设置列地址
                self.spi.LCD_Command(0x04)
                self.spi.LCD_Data(55)  # 起始列地址
                
                # 发送数据
                self.spi.LCD_Command(0x01)
                page_data = buffer[page * self.PMDB_COLS:(page + 1) * self.PMDB_COLS]
                self.spi.LCD_DataN(page_data)
            
            return True
            
        except Exception as e:
            print(f"LCD刷新失败: {str(e)}")
            return False
    
    def lcd_fill(self, x1: int, y1: int, x2: int, y2: int, color: int) -> bool:
        """
        填充指定区域
        
        Args:
            x1, y1: 起始坐标
            x2, y2: 结束坐标
            color: 颜色 (0或1)
            
        Returns:
            bool: 操作是否成功
        """
        try:
            # 边界检查
            if x1 > self.PMDB_COLS - 1:
                x1 = self.PMDB_COLS - 1
            if x2 > self.PMDB_COLS - 1:
                x2 = self.PMDB_COLS - 1
            if y1 > (self.PMDB_PAGES_16 << 3) - 1:
                y1 = (self.PMDB_PAGES_16 << 3) - 1
            if y2 > (self.PMDB_PAGES_16 << 3) - 1:
                y2 = (self.PMDB_PAGES_16 << 3) - 1
            
            color = color & 1
            
            page1 = y1 >> 3
            page2 = y2 >> 3
            row1 = y1 & 0x7
            row2 = y2 & 0x7
            
            for page in range(page1, page2 + 1):
                row_start = 0
                row_end = 7
                
                if page == page1:
                    row_start = row1
                if page == page2:
                    row_end = row2
                
                for col in range(x1, x2 + 1):
                    data = self.display_buffer[page * self.PMDB_COLS + col]
                    for row in range(row_start, row_end + 1):
                        color_mask = 0x1 << row
                        data = (data & ~color_mask) | (color << row)
                    self.display_buffer[page * self.PMDB_COLS + col] = data
            
            return True
            
        except Exception as e:
            print(f"填充区域失败: {str(e)}")
            return False
    
    def lcd_draw_point(self, x: int, y: int, color: int) -> bool:
        """
        画点
        
        Args:
            x, y: 坐标
            color: 颜色 (0或1)
            
        Returns:
            bool: 操作是否成功
        """
        try:
            # 边界检查
            if x > self.PMDB_COLS - 1:
                x = self.PMDB_COLS - 1
            if y > self.PMDB_ROWS - 1:
                y = self.PMDB_ROWS - 1
            
            color = color & 1
            
            page = y >> 3
            row = y & 0x7
            
            data = self.display_buffer[page * self.PMDB_COLS + x]
            color_mask = 0x1 << row
            data = (data & ~color_mask) | (color << row)
            self.display_buffer[page * self.PMDB_COLS + x] = data
            
            return True
            
        except Exception as e:
            print(f"画点失败: {str(e)}")
            return False
    
    def lcd_draw_line(self, x1: int, y1: int, x2: int, y2: int, color: int) -> bool:
        """
        画线
        
        Args:
            x1, y1: 起始坐标
            x2, y2: 结束坐标
            color: 颜色 (0或1)
            
        Returns:
            bool: 操作是否成功
        """
        try:
            delta_x = x2 - x1
            delta_y = y2 - y1
            u_row = x1
            u_col = y1
            
            # 确定增量方向
            if delta_x > 0:
                incx = 1
            elif delta_x == 0:
                incx = 0
            else:
                incx = -1
                delta_x = -delta_x
            
            if delta_y > 0:
                incy = 1
            elif delta_y == 0:
                incy = 0
            else:
                incy = -1
                delta_y = -delta_y
            
            # 选择最大距离
            if delta_x > delta_y:
                distance = delta_x
            else:
                distance = delta_y
            
            xerr = 0
            yerr = 0
            
            for t in range(distance + 1):
                self.lcd_draw_point(u_row, u_col, color)
                xerr += delta_x
                yerr += delta_y
                
                if xerr > distance:
                    xerr -= distance
                    u_row += incx
                
                if yerr > distance:
                    yerr -= distance
                    u_col += incy
            
            return True
            
        except Exception as e:
            print(f"画线失败: {str(e)}")
            return False
    
    def lcd_draw_rectangle(self, x1: int, y1: int, x2: int, y2: int, color: int) -> bool:
        """
        画矩形
        
        Args:
            x1, y1: 起始坐标
            x2, y2: 结束坐标
            color: 颜色 (0或1)
            
        Returns:
            bool: 操作是否成功
        """
        try:
            # 画四条边
            self.lcd_draw_line(x1, y1, x2, y1, color)  # 上边
            self.lcd_draw_line(x1, y1, x1, y2, color)  # 左边
            self.lcd_draw_line(x1, y2, x2, y2, color)  # 下边
            self.lcd_draw_line(x2, y1, x2, y2, color)  # 右边
            
            return True
            
        except Exception as e:
            print(f"画矩形失败: {str(e)}")
            return False
    
    def draw_circle(self, x0: int, y0: int, r: int, color: int) -> bool:
        """
        画圆
        
        Args:
            x0, y0: 圆心坐标
            r: 半径
            color: 颜色 (0或1)
            
        Returns:
            bool: 操作是否成功
        """
        try:
            a = 0
            b = r
            
            while a <= b:
                # 画8个对称点
                self.lcd_draw_point(x0 - b, y0 - a, color)
                self.lcd_draw_point(x0 + b, y0 - a, color)
                self.lcd_draw_point(x0 - a, y0 + b, color)
                self.lcd_draw_point(x0 - a, y0 - b, color)
                self.lcd_draw_point(x0 + b, y0 + a, color)
                self.lcd_draw_point(x0 + a, y0 - b, color)
                self.lcd_draw_point(x0 + a, y0 + b, color)
                self.lcd_draw_point(x0 - b, y0 + a, color)
                
                a += 1
                if (a * a + b * b) > (r * r):
                    b -= 1
            
            return True
            
        except Exception as e:
            print(f"画圆失败: {str(e)}")
            return False
    
    def lcd_show_char(self, x: int, y: int, char: str, fc: int, bc: int, size: int, mode: int = 0) -> bool:
        """
        显示字符
        
        Args:
            x, y: 显示位置
            char: 要显示的字符
            fc: 前景色
            bc: 背景色
            size: 字体大小
            mode: 显示模式 (0=叠加模式, 1=覆盖模式)
            
        Returns:
            bool: 操作是否成功
        """
        try:
            char_code = ord(char) - ord(' ')
            size_x = size // 2
            
            # 根据字体大小选择对应的字体数据
            if size == 12:
                # 6x12字体
                font_data = LCDFonts.get_ascii_1206_font(char_code)
                font_width = 6
                font_height = 12
            elif size == 16:
                # 8x16字体
                font_data = LCDFonts.get_ascii_1608_font(char_code)
                font_width = 8
                font_height = 16
            elif size == 24:
                # 12x24字体
                font_data = LCDFonts.get_ascii_2412_font(char_code)
                font_width = 12
                font_height = 24
            elif size == 32:
                # 16x32字体
                font_data = LCDFonts.get_ascii_3216_font(char_code)
                font_width = 16
                font_height = 32
            else:
                print(f"不支持的字体大小: {size}")
                return False
            
            # 绘制字符
            for i in range(font_height):
                if i < len(font_data):
                    for j in range(font_width):
                        if font_data[i] & (0x01 << j):
                            self.lcd_draw_point(x + j, y + i, fc)
                        elif not mode:  # 叠加模式
                            self.lcd_draw_point(x + j, y + i, bc)
            
            return True
            
        except Exception as e:
            print(f"显示字符失败: {str(e)}")
            return False
    
    def lcd_show_string(self, x: int, y: int, text: str, fc: int, bc: int, size: int, mode: int = 0) -> bool:
        """
        显示字符串
        
        Args:
            x, y: 显示位置
            text: 要显示的字符串
            fc: 前景色
            bc: 背景色
            size: 字体大小
            mode: 显示模式
            
        Returns:
            bool: 操作是否成功
        """
        try:
            for char in text:
                self.lcd_show_char(x, y, char, fc, bc, size, mode)
                x += size // 2
            
            return True
            
        except Exception as e:
            print(f"显示字符串失败: {str(e)}")
            return False
    
    def lcd_show_int_num(self, x: int, y: int, num: int, length: int, fc: int, bc: int, size: int) -> bool:
        """
        显示整数
        
        Args:
            x, y: 显示位置
            num: 要显示的数字
            length: 显示位数
            fc: 前景色
            bc: 背景色
            size: 字体大小
            
        Returns:
            bool: 操作是否成功
        """
        try:
            size_x = size // 2
            enshow = 0
            
            for t in range(length):
                temp = (num // (10 ** (length - t - 1))) % 10
                
                if enshow == 0 and t < (length - 1):
                    if temp == 0:
                        self.lcd_show_char(x + t * size_x, y, ' ', fc, bc, size, 0)
                        continue
                    else:
                        enshow = 1
                
                self.lcd_show_char(x + t * size_x, y, chr(temp + 48), fc, bc, size, 0)
            
            return True
            
        except Exception as e:
            print(f"显示整数失败: {str(e)}")
            return False
    
    def lcd_show_float_num(self, x: int, y: int, num: float, length: int, fc: int, bc: int, size: int) -> bool:
        """
        显示浮点数
        
        Args:
            x, y: 显示位置
            num: 要显示的数字
            length: 显示位数
            fc: 前景色
            bc: 背景色
            size: 字体大小
            
        Returns:
            bool: 操作是否成功
        """
        try:
            size_x = size // 2
            num *= 10
            num_int = int(num)
            
            for t in range(length):
                temp = (num_int // (10 ** (length - t - 1))) % 10
                
                if t == (length - 1):
                    self.lcd_show_char(x + (length - 1) * size_x, y, '.', fc, bc, size, 0)
                    t += 1
                    length += 1
                
                self.lcd_show_char(x + t * size_x, y, chr(temp + 48), fc, bc, size, 0)
            
            return True
            
        except Exception as e:
            print(f"显示浮点数失败: {str(e)}")
            return False
    
    def clear_screen(self, color: int = 0) -> bool:
        """
        清屏
        
        Args:
            color: 清屏颜色 (0=黑色, 1=白色)
            
        Returns:
            bool: 操作是否成功
        """
        try:
            self.lcd_fill(0, 0, self.PMDB_COLS - 1, self.PMDB_ROWS - 1, color)
            return True
        except Exception as e:
            print(f"清屏失败: {str(e)}")
            return False
    
    def set_contrast(self, contrast: int) -> bool:
        """
        设置对比度
        
        Args:
            contrast: 对比度值 (0-255)
            
        Returns:
            bool: 操作是否成功
        """
        try:
            self.contrast = max(0, min(255, contrast))
            self.spi.LCD_Command(0x81)
            self.spi.LCD_Data(self.contrast)
            return True
        except Exception as e:
            print(f"设置对比度失败: {str(e)}")
            return False
    
    
    def lcd_show_chinese(self, x: int, y: int, text: str, fc: int, bc: int, size: int, mode: int = 0) -> bool:
        """
        显示中文字符
        
        Args:
            x, y: 显示位置
            text: 要显示的中文字符串
            fc: 前景色
            bc: 背景色
            size: 字体大小
            mode: 显示模式 (0=叠加模式, 1=覆盖模式)
            
        Returns:
            bool: 操作是否成功
        """
        try:
            # 中文字符显示需要特殊处理
            # 这里暂时用简单实现
            for i, char in enumerate(text):
                if ord(char) > 127:  # 中文字符
                    self.lcd_show_chinese_char(x + i * size, y, char, fc, bc, size, mode)
                else:  # ASCII字符
                    self.lcd_show_char(x + i * (size // 2), y, char, fc, bc, size, mode)
            
            return True
            
        except Exception as e:
            print(f"显示中文字符失败: {str(e)}")
            return False
    
    def lcd_show_chinese_char(self, x: int, y: int, char: str, fc: int, bc: int, size: int, mode: int = 0) -> bool:
        """
        显示单个中文字符
        
        Args:
            x, y: 显示位置
            char: 要显示的中文字符
            fc: 前景色
            bc: 背景色
            size: 字体大小
            mode: 显示模式
            
        Returns:
            bool: 操作是否成功
        """
        try:
            # 获取中文字符的字节数据
            char_bytes = char.encode('utf-8')
            
            # 根据字体大小选择对应的字体数据
            if size == 12:
                # 12x12中文字体
                font_data = LCDFonts.get_chinese_12x12_font(char_bytes)
                font_width = 12
                font_height = 12
            elif size == 16:
                # 16x16中文字体
                font_data = LCDFonts.get_chinese_16x16_font(char_bytes)
                font_width = 16
                font_height = 16
            elif size == 24:
                # 24x24中文字体
                font_data = LCDFonts.get_chinese_24x24_font(char_bytes)
                font_width = 24
                font_height = 24
            elif size == 32:
                # 32x32中文字体
                font_data = LCDFonts.get_chinese_32x32_font(char_bytes)
                font_width = 32
                font_height = 32
            else:
                print(f"不支持的中文字体大小: {size}")
                return False
            
            # 绘制中文字符
            for i in range(font_height):
                if i < len(font_data):
                    for j in range(font_width):
                        if font_data[i] & (0x01 << j):
                            self.lcd_draw_point(x + j, y + i, fc)
                        elif not mode:  # 叠加模式
                            self.lcd_draw_point(x + j, y + i, bc)
            
            return True
            
        except Exception as e:
            print(f"显示中文字符失败: {str(e)}")
            return False


def main():
    """主函数 - 演示LCD驱动使用"""
    print("PMDB LCD驱动演示")
    print("=" * 50)
    
    # 创建SPI接口
    spi = FTD2XXSPIInterface(device_index=0, use_ctypes=True)
    
    try:
        # 连接设备
        if not spi.connect():
            print("设备连接失败")
            return
        
        spi.configure_spi(0, 500000)
        # 创建LCD驱动实例
        lcd = PMDBLCD(spi)
        
        # 初始化LCD
        if not lcd.pmdb_init():
            print("LCD初始化失败")
            return
        
        print("LCD初始化成功")
        
        #return
        # 清屏
        lcd.clear_screen(0)
        
        # 画一些图形
        lcd.lcd_draw_rectangle(0, 0, 127, 127, 1) 
        #lcd.lcd_draw_rectangle(10, 10, 50, 50, 1)  # 画矩形
        lcd.draw_circle(80, 40, 20, 1)             # 画圆
        lcd.lcd_draw_line(0, 0, 127, 127, 1)       # 画对角线
        
        # 显示文字
        lcd.lcd_show_string(10, 60, "Hello", 1, 0, 12, 1)
        lcd.lcd_show_string(10, 80, "PMDB LCD", 1, 0, 12, 1)
        lcd.lcd_show_int_num(10, 100, 12345, 5, 1, 0, 12)
        #lcd.lcd_show_float_num(10, 120, 3.14159, 6, 1, 0, 16)
        
        # 显示中文字符（简化版）
        #lcd.lcd_show_chinese(60, 60, "测试", 1, 0, 16, 0)
        
        # 刷新显示
        
        lcd.lcd_flush()
        
                
        spi.LCD_Command(0xc9)
        spi.LCD_Data(0xad)  
        
        print("\n按ESC键退出程序...")
        
        # 等待用户按ESC键退出
        import msvcrt
        iloop=0
        while False:

            if iloop==0:
                lcd.lcd_show_string(10, 80, "PMDB LCD", 1, 0, 12, 1)
                iloop=1
            else:
                lcd.lcd_show_string(10, 80, "PMDB LCD", 0, 1, 12, 1)
                iloop=0
            lcd.lcd_flush()
            
            if msvcrt.kbhit():
                key = msvcrt.getch()
                if key == b'\x1b':  # ESC键
                    print("\n用户按了ESC键退出")
                    break
            time.sleep(0.5)
        print("LCD显示测试完成")
    except Exception as e:
        print(f"测试过程中出错: {str(e)}")
    
    finally:
        # 断开连接
        spi.disconnect()
        print("设备已断开连接")


if __name__ == "__main__":
    main()
