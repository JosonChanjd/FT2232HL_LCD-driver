"""
PPDB035_SPI LCD 驱动完整版 (适配 ST7272A/ST7789 协议)
-------------------------------------------------------------------------
功能特性:
1. SPI 通信: 使用 FTDI MPSSE (SPI Mode 3: CPOL=1, CPHA=1)
2. 硬件环境: 
   - LCD: PPDB035 (320x240 RGB565, Driver: ST7272A)
   - Interface: FTDI FT232H/FT2232H
3. 修改点: 适配 RGB565 颜色格式、分辨率及初始化序列
-------------------------------------------------------------------------
"""

import os
import time
import msvcrt
import struct
from typing import List
from ctypes import (
    windll, c_ulong, c_ubyte, c_void_p, c_int, POINTER, byref
)

# 配置 DLL 路径 (请根据实际情况修改)
os.environ['FTD2XX_DLL_DIR'] = r'C:\Users\sesa696240\Desktop\PMDB'

try:
    import ftd2xx
    FTDI_AVAILABLE = True
except ImportError:
    FTDI_AVAILABLE = False

# ============================================================================
# 1. 辅助颜色工具
# ============================================================================
def color565(r, g, b):
    """将 RGB888 转换为 RGB565 整数"""
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)

# 常用颜色定义
BLACK   = 0x0000
WHITE   = 0xFFFF
RED     = 0xF800
GREEN   = 0x07E0
BLUE    = 0x001F
YELLOW  = 0xFFE0
CYAN    = 0x07FF
MAGENTA = 0xF81F

# ============================================================================
# 2. LCD 字体数据模块 (保持 ASCII 12x6)
# ============================================================================
class LCDFonts:
    """
    简单 ASCII 字库
    """
    @staticmethod
    def get_ascii_1206_font(char_code: int) -> List[int]:
        ascii_1206 = {
             0: [0x00]*12, 32: [0x00]*12,
            33: [0x00,0x00,0x04,0x04,0x04,0x04,0x04,0x00,0x00,0x04,0x00,0x00], # !
            48: [0x00,0x00,0x0E,0x11,0x11,0x11,0x11,0x11,0x11,0x0E,0x00,0x00], # 0
            49: [0x00,0x00,0x04,0x06,0x04,0x04,0x04,0x04,0x04,0x0E,0x00,0x00], # 1
            50: [0x00,0x00,0x0E,0x11,0x11,0x08,0x04,0x02,0x01,0x1F,0x00,0x00], # 2
            51: [0x00,0x00,0x0E,0x11,0x10,0x0C,0x10,0x10,0x11,0x0E,0x00,0x00], # 3
            52: [0x00,0x00,0x08,0x0C,0x0C,0x0A,0x09,0x1F,0x08,0x1C,0x00,0x00], # 4
            53: [0x00,0x00,0x1F,0x01,0x01,0x0F,0x11,0x10,0x11,0x0E,0x00,0x00], # 5
            54: [0x00,0x00,0x0C,0x12,0x01,0x0D,0x13,0x11,0x11,0x0E,0x00,0x00], # 6
            55: [0x00,0x00,0x1E,0x10,0x08,0x08,0x04,0x04,0x04,0x04,0x00,0x00], # 7
            56: [0x00,0x00,0x0E,0x11,0x11,0x0E,0x11,0x11,0x11,0x0E,0x00,0x00], # 8
            57: [0x00,0x00,0x0E,0x11,0x11,0x19,0x16,0x10,0x09,0x06,0x00,0x00], # 9
            65: [0x00,0x00,0x04,0x04,0x0C,0x0A,0x0A,0x1E,0x12,0x33,0x00,0x00], # A
            66: [0x00,0x00,0x0F,0x12,0x12,0x0E,0x12,0x12,0x12,0x0F,0x00,0x00], # B
            72: [0x00,0x00,0x33,0x12,0x12,0x1E,0x12,0x12,0x12,0x33,0x00,0x00], # H
            76: [0x00,0x00,0x07,0x02,0x02,0x02,0x02,0x02,0x22,0x3F,0x00,0x00], # L
            80: [0x00,0x00,0x0F,0x12,0x12,0x0E,0x02,0x02,0x02,0x07,0x00,0x00], # P
            83: [0x00,0x00,0x0E,0x11,0x01,0x0E,0x10,0x11,0x11,0x0E,0x00,0x00], # S
            101: [0x00,0x00,0x00,0x00,0x00,0x0C,0x12,0x1E,0x02,0x1C,0x00,0x00], # e
            108: [0x00,0x07,0x04,0x04,0x04,0x04,0x04,0x04,0x04,0x1F,0x00,0x00], # l
            111: [0x00,0x00,0x00,0x00,0x00,0x0C,0x12,0x12,0x12,0x0C,0x00,0x00], # o
        }
        return ascii_1206.get(char_code, [0xFF]*12)

# ============================================================================
# 3. FTDI SPI 接口层 (针对 PPDB035 调整 SPI 模式)
# ============================================================================
class FTD2XXSPIInterface:
    FT_OK = 0
    FT_BITMODE_RESET = 0x00
    FT_BITMODE_MPSSE = 0x02
    
    # MPSSE OpCodes
    CMD_SET_DATA_BITS_LOW  = 0x80
    CMD_SET_DATA_BITS_HIGH = 0x82
    # PDF Page 15: "idle state high (CPOL=1), data latching at clock second edge (rising edge, CPHA=1)"
    # MPSSE 0x11: Bytes Out on Falling Edge.
    # 若 SCLK Idle High，初始为1。下降沿(Leading)输出数据，上升沿(Trailing)设备采样。
    # 这符合 Mode 3 (CPOL=1, CPHA=1) 的行为。
    CMD_CLOCK_FALL_OUT_BYTES = 0x11 
    
    # 硬件引脚映射 (ACBUS)
    PIN_A0    = 0  # AC0: 0=Cmd, 1=Data
    PIN_RESET = 1  # AC1: Reset
    PIN_CS    = 2  # AC2: CS (Active Low)
    
    def __init__(self, device_index: int = 0, use_ctypes: bool = False):
        self.device_index = device_index
        self.use_ctypes = use_ctypes
        self.device_handle = None
        self.clock_speed = 15000000 # 15MHz (PDF建议 8-16MHz)
        
        # SCLK (bit0) 初始必须为 High (CPOL=1)
        # MOSI (bit1) 输出
        # MISO (bit2) 输入
        # 0xFB = 1111 1011
        self.gpio_low_dir = 0xFB 
        self.gpio_low_val = 0x01 # SCLK Idle High
        
        # ACBUS: A0, RESET, CS 全部为输出
        self.gpio_high_dir = 0x07
        self.gpio_high_val = 0x07 # CS High, Reset High

        if use_ctypes: self._init_dll()
    
    def _init_dll(self):
        try:
            dll_paths = [r'C:\Users\sesa696240\Desktop\PMDB\FTD2XX.DLL', 'FTD2XX.DLL', 'ftd2xx.dll']
            self.ftd2xx_dll = None
            for path in dll_paths:
                try:
                    self.ftd2xx_dll = windll.LoadLibrary(path)
                    break
                except OSError: continue
            
            if not self.ftd2xx_dll: raise Exception("FTD2XX.DLL not found")
            
            self.ftd2xx_dll.FT_Open.argtypes = [c_int, POINTER(c_void_p)]
            self.ftd2xx_dll.FT_Open.restype = c_ulong
            self.ftd2xx_dll.FT_Close.argtypes = [c_void_p]
            self.ftd2xx_dll.FT_Write.argtypes = [c_void_p, c_void_p, c_ulong, POINTER(c_ulong)]
            self.ftd2xx_dll.FT_Write.restype = c_ulong
            self.ftd2xx_dll.FT_SetBitMode.argtypes = [c_void_p, c_ubyte, c_ubyte]
            self.ftd2xx_dll.FT_SetUSBParameters.argtypes = [c_void_p, c_ulong, c_ulong]
            self.ftd2xx_dll.FT_SetLatencyTimer.argtypes = [c_void_p, c_ubyte]
            self.ftd2xx_dll.FT_Purge.argtypes = [c_void_p, c_ulong]
        except Exception as e: raise Exception(f"DLL Init Failed: {str(e)}")
    
    def connect(self) -> bool:
        try:
            if self.use_ctypes:
                handle = c_void_p()
                if self.ftd2xx_dll.FT_Open(self.device_index, byref(handle)) != self.FT_OK: return False
                self.device_handle = handle
                self.ftd2xx_dll.FT_SetUSBParameters(handle, 65536, 65536)
                self.ftd2xx_dll.FT_SetLatencyTimer(handle, 1)
                self.ftd2xx_dll.FT_SetBitMode(handle, 0, self.FT_BITMODE_RESET)
                time.sleep(0.01)
                self.ftd2xx_dll.FT_SetBitMode(handle, 0, self.FT_BITMODE_MPSSE)
                self.ftd2xx_dll.FT_Purge(handle, 3)
            else:
                if not FTDI_AVAILABLE: return False
                self.device_handle = ftd2xx.open(self.device_index)
                self.device_handle.setUSBParameters(65536, 65536)
                self.device_handle.setLatencyTimer(1)
                self.device_handle.setBitMode(0, self.FT_BITMODE_RESET)
                time.sleep(0.01)
                self.device_handle.setBitMode(0, self.FT_BITMODE_MPSSE)
                self.device_handle.purge(3)
            
            self._initialize_mpsse()
            return True
        except Exception: return False
    
    def disconnect(self):
        if self.device_handle:
            try:
                if self.use_ctypes: self.ftd2xx_dll.FT_Close(self.device_handle)
                else: self.device_handle.close()
            except: pass
    
    def _initialize_mpsse(self):
        divisor = max(0, min(0xFFFF, int(12000000 / (2 * self.clock_speed)) - 1))
        cmds = [
            0x8A, 0x97, 0x8D, # Disable /5, Disable Adaptive, Disable 3-Phase
            0x86, divisor & 0xFF, (divisor >> 8) & 0xFF,
            0x85, # Disable Loopback
            self.CMD_SET_DATA_BITS_LOW, self.gpio_low_val, self.gpio_low_dir,
            self.CMD_SET_DATA_BITS_HIGH, self.gpio_high_val, self.gpio_high_dir
        ]
        self._write_raw(cmds)
    
    def _write_raw(self, data: List[int]):
        if not self.device_handle: return
        b_data = bytes(data)
        if self.use_ctypes:
            written = c_ulong()
            self.ftd2xx_dll.FT_Write(self.device_handle, b_data, len(b_data), byref(written))
        else: self.device_handle.write(b_data)

    def _send_packet(self, data: List[int], is_command: bool):
        cmds = []
        val_active = self.gpio_high_val & ~(1 << self.PIN_CS) # CS Low
        if is_command:
            val_active &= ~(1 << self.PIN_A0) # A0 Low (Cmd)
        else:
            val_active |= (1 << self.PIN_A0)  # A0 High (Data)
        
        val_idle = self.gpio_high_val | (1 << self.PIN_CS) # CS High

        cmds.extend([self.CMD_SET_DATA_BITS_HIGH, val_active, self.gpio_high_dir])
        
        length = len(data)
        if length > 0:
            if length > 65536: # MPSSE Max chunk 64KB
                chunks = [data[i:i + 65535] for i in range(0, length, 65535)]
                for chunk in chunks:
                    l = len(chunk)
                    cmds.extend([self.CMD_CLOCK_FALL_OUT_BYTES, (l-1)&0xFF, ((l-1)>>8)&0xFF])
                    cmds.extend(chunk)
            else:
                cmds.extend([self.CMD_CLOCK_FALL_OUT_BYTES, (length-1)&0xFF, ((length-1)>>8)&0xFF])
                cmds.extend(data)
        
        cmds.extend([self.CMD_SET_DATA_BITS_HIGH, val_idle, self.gpio_high_dir])
        self._write_raw(cmds)

    def LCD_Reset(self):
        val_reset = self.gpio_high_val & ~(1 << self.PIN_RESET)
        self._write_raw([self.CMD_SET_DATA_BITS_HIGH, val_reset, self.gpio_high_dir])
        time.sleep(0.1) # 100ms
        self._write_raw([self.CMD_SET_DATA_BITS_HIGH, self.gpio_high_val, self.gpio_high_dir])
        time.sleep(0.15) # 150ms after reset
        
    def LCD_Command(self, command: int): self._send_packet([command], True)
    def LCD_Data(self, data: int): self._send_packet([data], False)
    def LCD_DataN(self, data_list: List[int]): self._send_packet(list(data_list), False)

# ============================================================================
# 4. PPDB035 LCD 驱动层 (ST7272A/ST7789)
# ============================================================================
class PPDB035LCD:
    WIDTH = 320
    HEIGHT = 240
    
    def __init__(self, spi_interface: FTD2XXSPIInterface):
        self.spi = spi_interface
        # 显存缓冲区: 320x240x2 bytes (RGB565)
        # 初始化为黑色
        self.buffer_size = self.WIDTH * self.HEIGHT * 2
        self.display_buffer = bytearray([0x00] * self.buffer_size)
        
    def init(self) -> bool:
        """根据 PDF 文档及 ST7272A 标准初始化"""
        try:
            self.spi.LCD_Reset()
            c, d = self.spi.LCD_Command, self.spi.LCD_Data
            
            c(0x11) # Sleep Out
            time.sleep(0.12)
            
            # PDF Page 20 init code: 
            # SpiTFT_Command(0x36); 
            # SpiTFT_Data(0xB4); // Portrait mode, LCD driver on right
            c(0x36); d(0xB4) 
            
            # Pixel Format Set (RGB565)
            c(0x3A); d(0x05) 
            
            # Display ON
            c(0x29)
            time.sleep(0.05)
            
            return True
        except Exception as e:
            print(f"LCD Init Failed: {str(e)}")
            return False
    
    def set_window(self, x1, y1, x2, y2):
        """设置绘图窗口 (ST7789/ST7272A 标准指令)"""
        c, d = self.spi.LCD_Command, self.spi.LCD_Data
        c(0x2A) # Column Address Set
        d(x1 >> 8); d(x1 & 0xFF)
        d(x2 >> 8); d(x2 & 0xFF)
        
        c(0x2B) # Row Address Set
        d(y1 >> 8); d(y1 & 0xFF)
        d(y2 >> 8); d(y2 & 0xFF)
        
        c(0x2C) # Memory Write

    def lcd_flush(self) -> bool:
        """全屏刷新"""
        try:
            self.set_window(0, 0, self.WIDTH - 1, self.HEIGHT - 1)
            # 发送整个缓冲区
            self.spi.LCD_DataN(self.display_buffer)
            return True
        except Exception: return False

    def clear_screen(self, color: int):
        """清屏 (color 为 16位 RGB565)"""
        hi = color >> 8
        lo = color & 0xFF
        # 快速填充 bytearray
        self.display_buffer[:] = bytes([hi, lo] * (self.WIDTH * self.HEIGHT))

    def lcd_draw_point(self, x: int, y: int, color: int):
        if 0 <= x < self.WIDTH and 0 <= y < self.HEIGHT:
            idx = (y * self.WIDTH + x) * 2
            self.display_buffer[idx] = color >> 8
            self.display_buffer[idx + 1] = color & 0xFF

    def lcd_fill(self, x1, y1, x2, y2, color: int):
        if x1 < 0: x1 = 0
        if y1 < 0: y1 = 0
        if x2 >= self.WIDTH: x2 = self.WIDTH - 1
        if y2 >= self.HEIGHT: y2 = self.HEIGHT - 1
        
        hi = color >> 8
        lo = color & 0xFF
        line_data = bytes([hi, lo] * (x2 - x1 + 1))
        
        for y in range(y1, y2 + 1):
            start_idx = (y * self.WIDTH + x1) * 2
            end_idx = start_idx + len(line_data)
            self.display_buffer[start_idx:end_idx] = line_data

    def lcd_draw_line(self, x1, y1, x2, y2, color: int):
        # Bresenham
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        sx = 1 if x1 < x2 else -1
        sy = 1 if y1 < y2 else -1
        err = dx - dy
        while True:
            self.lcd_draw_point(x1, y1, color)
            if x1 == x2 and y1 == y2: break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x1 += sx
            if e2 < dx:
                err += dx
                y1 += sy

    def lcd_draw_rectangle(self, x1, y1, x2, y2, color: int):
        self.lcd_draw_line(x1, y1, x2, y1, color)
        self.lcd_draw_line(x1, y1, x1, y2, color)
        self.lcd_draw_line(x1, y2, x2, y2, color)
        self.lcd_draw_line(x2, y1, x2, y2, color)

    def draw_circle(self, x0, y0, r, color):
        f = 1 - r
        ddF_x = 1
        ddF_y = -2 * r
        x = 0
        y = r
        self.lcd_draw_point(x0, y0 + r, color)
        self.lcd_draw_point(x0, y0 - r, color)
        self.lcd_draw_point(x0 + r, y0, color)
        self.lcd_draw_point(x0 - r, y0, color)
        while x < y:
            if f >= 0:
                y -= 1
                ddF_y += 2
                f += ddF_y
            x += 1
            ddF_x += 2
            f += ddF_x
            self.lcd_draw_point(x0 + x, y0 + y, color)
            self.lcd_draw_point(x0 - x, y0 + y, color)
            self.lcd_draw_point(x0 + x, y0 - y, color)
            self.lcd_draw_point(x0 - x, y0 - y, color)
            self.lcd_draw_point(x0 + y, y0 + x, color)
            self.lcd_draw_point(x0 - y, y0 + x, color)
            self.lcd_draw_point(x0 + y, y0 - x, color)
            self.lcd_draw_point(x0 - y, y0 - x, color)

    def lcd_show_char(self, x, y, char, fc, bc, size=12):
        if size != 12: return
        font = LCDFonts.get_ascii_1206_font(ord(char))
        for i in range(12):
            line = font[i]
            for j in range(6):
                if (line >> j) & 0x01:
                    self.lcd_draw_point(x + j, y + i, fc)
                else:
                    self.lcd_draw_point(x + j, y + i, bc)

    def lcd_show_string(self, x, y, text, fc, bc, size=12):
        for char in text:
            self.lcd_show_char(x, y, char, fc, bc, size)
            x += size // 2

    # 业务绘图逻辑
    def draw_checkerboard(self):
        self.clear_screen(WHITE)
        block_w = self.WIDTH // 3
        block_h = self.HEIGHT // 3
        for r in range(3):
            for c in range(3):
                if (r + c) % 2 == 0:
                    self.lcd_fill(c*block_w, r*block_h, (c+1)*block_w, (r+1)*block_h, BLACK)

    def draw_split_screen(self):
        self.clear_screen(WHITE)
        # 下半部分为黑色
        self.lcd_fill(0, self.HEIGHT//2, self.WIDTH, self.HEIGHT, BLACK)

# ============================================================================
# 5. 主程序
# ============================================================================
def main():
    print("PPDB035 LCD (ST7272A) 驱动程序")
    print("-----------------------------------")
    
    spi = FTD2XXSPIInterface(device_index=0, use_ctypes=True)
    
    if not spi.connect():
        print("错误: 无法连接 FTDI 设备。")
        return
    
    try:
        lcd = PPDB035LCD(spi)
        if not lcd.init():
            print("错误: LCD 初始化失败。")
            return
        
        print("初始化成功。演示开始 (按 ESC 退出)...")
        
        STATE_DEMO = 0
        STATE_CHECKERBOARD = 1
        STATE_SPLIT = 2
        current_state = STATE_DEMO
        
        while True:
            start_time = time.time()
            
            if current_state == STATE_DEMO:
                print("演示: 几何图形")
                lcd.clear_screen(BLACK)
                lcd.lcd_draw_rectangle(10, 10, 310, 230, RED)
                lcd.draw_circle(160, 120, 50, GREEN)
                lcd.lcd_draw_line(0, 0, 319, 239, BLUE)
                lcd.lcd_show_string(100, 115, "PPDB035 SPI", WHITE, BLACK, 12)
                lcd.lcd_show_string(100, 130, "320x240 RGB", YELLOW, BLACK, 12)
                lcd.lcd_flush()
                
            elif current_state == STATE_CHECKERBOARD:
                print("演示: 棋盘格")
                lcd.draw_checkerboard()
                lcd.lcd_flush()
                
            elif current_state == STATE_SPLIT:
                print("演示: 分屏")
                lcd.draw_split_screen()
                lcd.lcd_flush()
            
            # 延时检测退出
            while (time.time() - start_time) < 3.0:
                if msvcrt.kbhit():
                    if msvcrt.getch() == b'\x1b':
                        return
                time.sleep(0.1)
            
            current_state = (current_state + 1) % 3
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        spi.disconnect()

if __name__ == "__main__":
    main()
