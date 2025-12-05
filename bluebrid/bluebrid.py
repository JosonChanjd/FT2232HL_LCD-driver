"""
P3PLUS LCD 驱动最终完整版
-------------------------------------------------------------------------
功能特性:
1. SPI 通信: 使用 MPSSE 指令打包
2. 图形库: 支持画点、线、矩形、圆、区域填充、字符显示。
3. 演示模式: 包含普通绘图、棋盘格、分屏显示的自动切换逻辑。

硬件环境:
- Controller: UC1638 (128x128 4-Level Grayscale, 本驱动配置为二值模式)
- Interface: FTDI FT232H/FT2232H (MPSSE Mode)
-------------------------------------------------------------------------
"""

import os
import time
import msvcrt
from typing import List, Union
from ctypes import (
    windll, c_ulong, c_ubyte, c_void_p, c_int, POINTER, byref
)

# 配置 DLL 路径
os.environ['FTD2XX_DLL_DIR'] = r'C:\Users\sesa696240\Desktop\PMDB'

try:
    import ftd2xx
    FTDI_AVAILABLE = True
except ImportError:
    FTDI_AVAILABLE = False

# ============================================================================
# 1. LCD 字体数据模块
# ============================================================================
class LCDFonts:
    """
    存储 ASCII 字符的点阵数据。
    取模方式: 纵向取模，字节倒序 (LSB在上)。
    尺寸: 6x12 (宽x高)，每个字符占用 12 字节。
    """
    @staticmethod
    def get_ascii_1206_font(char_code: int) -> List[int]:
        # 仅列出常用字符以节省空间，实际工程可扩展为完整 ASCII 表
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
            67: [0x00,0x00,0x1E,0x11,0x01,0x01,0x01,0x01,0x11,0x0E,0x00,0x00], # C
            68: [0x00,0x00,0x0F,0x12,0x12,0x12,0x12,0x12,0x12,0x0F,0x00,0x00], # D
            69: [0x00,0x00,0x1F,0x12,0x0A,0x0E,0x0A,0x02,0x12,0x1F,0x00,0x00], # E
            72: [0x00,0x00,0x33,0x12,0x12,0x1E,0x12,0x12,0x12,0x33,0x00,0x00], # H
            76: [0x00,0x00,0x07,0x02,0x02,0x02,0x02,0x02,0x22,0x3F,0x00,0x00], # L
            77: [0x00,0x00,0x3B,0x1B,0x1B,0x1B,0x15,0x15,0x15,0x35,0x00,0x00], # M
            80: [0x00,0x00,0x0F,0x12,0x12,0x0E,0x02,0x02,0x02,0x07,0x00,0x00], # P
            83: [0x00,0x00,0x0E,0x11,0x01,0x0E,0x10,0x11,0x11,0x0E,0x00,0x00], # S
            85: [0x00,0x00,0x11,0x11,0x11,0x11,0x11,0x11,0x11,0x0E,0x00,0x00], # U
            101: [0x00,0x00,0x00,0x00,0x00,0x0C,0x12,0x1E,0x02,0x1C,0x00,0x00], # e
            108: [0x00,0x07,0x04,0x04,0x04,0x04,0x04,0x04,0x04,0x1F,0x00,0x00], # l
            111: [0x00,0x00,0x00,0x00,0x00,0x0C,0x12,0x12,0x12,0x0C,0x00,0x00], # o
        }
        # 默认返回一个方块字符，避免 KeyError
        return ascii_1206.get(char_code, [0x00,0x1E,0x21,0x21,0x21,0x1E,0x00,0x00,0x00,0x00,0x00,0x00])

# ============================================================================
# 2. FTDI SPI 接口层
# ============================================================================
class FTD2XXSPIInterface:
    """
    封装 FTDI MPSSE 引擎的操作。
    核心逻辑: 将 GPIO 操作和 SPI 数据流合并为一个 USB 数据包发送，
    极大地减少了 USB 事务(Transaction)的数量，从而消除 1ms 的 USB 帧延迟累积。
    """
    
    # FTDI 状态码与模式定义
    FT_OK = 0
    FT_BITMODE_RESET = 0x00
    FT_BITMODE_MPSSE = 0x02
    
    # MPSSE 原始指令集 (OpCodes)
    CMD_SET_DATA_BITS_LOW  = 0x80 # 设置低8位字节 (ADBUS 0-7)
    CMD_SET_DATA_BITS_HIGH = 0x82 # 设置高8位字节 (ACBUS 0-7)
    # 0x11: Bytes Out on Falling Edge (SPI Mode 0: CPOL=0, CPHA=0)
    # 数据在下降沿输出，时钟空闲为低
    CMD_CLOCK_FALL_OUT_BYTES = 0x11 
    
    # 硬件引脚映射 (连接在 ACBUS 高8位端口)
    PIN_A0    = 0  # AC0: 命令/数据选择 (0=Cmd, 1=Data)
    PIN_RESET = 1  # AC1: 硬件复位
    PIN_CS    = 2  # AC2: 片选信号 (低有效)
    
    def __init__(self, device_index: int = 0, use_ctypes: bool = False):
        self.device_index = device_index
        self.use_ctypes = use_ctypes
        self.device_handle = None
        self.is_connected = False
        self.clock_speed = 2000000 # SPI 时钟 2MHz
        
        # GPIO 状态缓存 (MPSSE 需要每次发送完整的 8bit 状态)
        # Low Byte (ADBUS): SCLK(bit0), MOSI(bit1) 为输出; MISO(bit2) 为输入
        # 0xFB = 1111 1011
        self.gpio_low_dir = 0xFB 
        self.gpio_low_val = 0x00 # 初始时钟低电平
        
        # High Byte (ACBUS): A0, RESET, CS 全部为输出
        # 0x07 = 0000 0111
        self.gpio_high_dir = 0x07
        self.gpio_high_val = 0x07 # 初始状态: CS高(未选中), RESET高(运行)

        if use_ctypes: self._init_dll()
    
    def _init_dll(self):
        """加载 FTD2XX.DLL 并定义 ctypes 函数原型"""
        try:
            dll_paths = [r'C:\Users\sesa696240\Desktop\PMDB\FTD2XX.DLL', 'FTD2XX.DLL', 'ftd2xx.dll']
            self.ftd2xx_dll = None
            for path in dll_paths:
                try:
                    self.ftd2xx_dll = windll.LoadLibrary(path)
                    break
                except OSError: continue
            
            if not self.ftd2xx_dll: raise Exception("FTD2XX.DLL not found")
            
            # 定义使用到的函数
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
        """建立设备连接并配置 MPSSE 模式"""
        try:
            if self.use_ctypes:
                handle = c_void_p()
                if self.ftd2xx_dll.FT_Open(self.device_index, byref(handle)) != self.FT_OK: return False
                self.device_handle = handle
                # 设置 USB 缓冲区大小和延迟定时器
                self.ftd2xx_dll.FT_SetUSBParameters(handle, 65536, 65536)
                self.ftd2xx_dll.FT_SetLatencyTimer(handle, 1) # 关键: 设为 1ms 以获得最快响应
                
                # 切换 BitMode 序列: Reset -> MPSSE
                self.ftd2xx_dll.FT_SetBitMode(handle, 0, self.FT_BITMODE_RESET)
                time.sleep(0.01)
                self.ftd2xx_dll.FT_SetBitMode(handle, 0, self.FT_BITMODE_MPSSE)
                self.ftd2xx_dll.FT_Purge(handle, 3) # 清空 RX/TX FIFO
            else:
                # 兼容 pyftdi/ftd2xx 库模式
                if not FTDI_AVAILABLE: return False
                self.device_handle = ftd2xx.open(self.device_index)
                self.device_handle.setUSBParameters(65536, 65536)
                self.device_handle.setLatencyTimer(1)
                self.device_handle.setBitMode(0, self.FT_BITMODE_RESET)
                time.sleep(0.01)
                self.device_handle.setBitMode(0, self.FT_BITMODE_MPSSE)
                self.device_handle.purge(3)
            
            self._initialize_mpsse()
            self.is_connected = True
            return True
        except Exception: return False
    
    def disconnect(self):
        if self.device_handle:
            try:
                if self.use_ctypes: self.ftd2xx_dll.FT_Close(self.device_handle)
                else: self.device_handle.close()
            except: pass
        self.is_connected = False
    
    def _initialize_mpsse(self):
        """配置 MPSSE 基础参数: 时钟分频与引脚方向"""
        # 计算分频系数: Divisor = (12MHz / (2 * Clock)) - 1
        divisor = max(0, min(0xFFFF, int(12000000 / (2 * self.clock_speed)) - 1))
        
        cmds = [
            0x8A, # 禁用 5 分频 (使用 60MHz 主频)
            0x97, # 禁用自适应时钟
            0x8D, # 禁用三相数据时钟
            0x86, divisor & 0xFF, (divisor >> 8) & 0xFF, # 设置时钟指令 + 分频系数(低,高)
            0x85, # 禁用内部回环
            # 初始化 GPIO 状态
            self.CMD_SET_DATA_BITS_LOW, self.gpio_low_val, self.gpio_low_dir,
            self.CMD_SET_DATA_BITS_HIGH, self.gpio_high_val, self.gpio_high_dir
        ]
        self._write_raw(cmds)
    
    def _write_raw(self, data: List[int]):
        """通过 USB 发送原始字节流"""
        if not self.device_handle: return
        b_data = bytes(data)
        if self.use_ctypes:
            written = c_ulong()
            self.ftd2xx_dll.FT_Write(self.device_handle, b_data, len(b_data), byref(written))
        else: self.device_handle.write(b_data)

    def _send_packet(self, data: List[int], is_command: bool):
        """
        [Packetization 逻辑核心]
        构造包含完整 SPI 事务的指令包:
        1. 设定 ACBUS: 拉低 CS, 并根据 is_command 设置 A0 电平。
        2. 发送 SPI 数据块。
        3. 设定 ACBUS: 拉高 CS (结束事务)。
        4. 单次 USB Write 调用发送整个包。
        """
        cmds = []

        # 1. 计算 "开始传输" 时的 GPIO 状态
        val_active = self.gpio_high_val & ~(1 << self.PIN_CS) # CS 置 0 (有效)
        if is_command:
            val_active &= ~(1 << self.PIN_A0) # A0 置 0 (命令模式)
        else:
            val_active |= (1 << self.PIN_A0)  # A0 置 1 (数据模式)
        
        # 2. 计算 "结束传输" 时的 GPIO 状态
        val_idle = self.gpio_high_val | (1 << self.PIN_CS) # CS 置 1 (空闲)

        # 3. 添加 GPIO 设置指令
        cmds.extend([self.CMD_SET_DATA_BITS_HIGH, val_active, self.gpio_high_dir])
        
        # 4. 添加 SPI 数据发送指令
        length = len(data)
        if length > 0:
            # MPSSE 数据长度定义为 Length - 1
            len_lsb = (length - 1) & 0xFF
            len_msb = ((length - 1) >> 8) & 0xFF
            cmds.extend([self.CMD_CLOCK_FALL_OUT_BYTES, len_lsb, len_msb])
            cmds.extend(data)
        
        # 5. 添加 CS 恢复指令
        cmds.extend([self.CMD_SET_DATA_BITS_HIGH, val_idle, self.gpio_high_dir])
        
        # 6. 发送数据包
        self._write_raw(cmds)

    def LCD_Reset(self):
        """控制硬件复位引脚的时序"""
        # Reset 拉低
        val_reset = self.gpio_high_val & ~(1 << self.PIN_RESET)
        self._write_raw([self.CMD_SET_DATA_BITS_HIGH, val_reset, self.gpio_high_dir])
        time.sleep(0.02) # 保持复位 20ms
        # Reset 拉高
        self._write_raw([self.CMD_SET_DATA_BITS_HIGH, self.gpio_high_val, self.gpio_high_dir])
        time.sleep(0.02) # 等待芯片启动
        
    def LCD_Command(self, command: int): self._send_packet([command], is_command=True)
    def LCD_Data(self, data: int): self._send_packet([data], is_command=False)
    def LCD_DataN(self, data_list: List[int]): self._send_packet(list(data_list), is_command=False)

# ============================================================================
# 3. P3PLUS LCD 驱动层 (UC1638 逻辑)
# ============================================================================
class P3PLUSLCD:
    P3PLUS_PAGES_16 = 16 # 128行 / 8位 = 16页
    P3PLUS_COLS = 128
    P3PLUS_ROWS = 128
    
    def __init__(self, spi_interface: FTD2XXSPIInterface):
        self.spi = spi_interface
        # 显存缓冲区: 128列 * 16页 = 2048 Bytes
        self.display_buffer = [0] * (self.P3PLUS_PAGES_16 * self.P3PLUS_COLS)
        
    def P3PLUS_init(self) -> bool:
        """初始化 UC1638 控制器寄存器"""
        try:
            self.spi.LCD_Reset()
            # 为了代码紧凑，使用别名
            c, d = self.spi.LCD_Command, self.spi.LCD_Data
            
            c(0xe1); # System Reset: 软复位
            c(0xe2); time.sleep(0.002)
            
            # --- 显示控制 ---
            c(0xa4); # Set All Pixel ON -> OFF (禁用全亮测试模式)
            c(0xa6); # Set Inverse Display -> OFF (正常显示，1=黑，0=白)
            
            # --- 电源管理 ---
            c(0xb8); d(0x00); # LCD Control: 设置 MTP (Multi-Time Programmable) 选项
            c(0x2d); # Power Control: 启用内部电荷泵
            c(0x20); # Temp Comp: 设置温度补偿系数
            c(0xea); # Bias Setting: 设置偏压比
            
            # --- 对比度设置 ---
            c(0x81); d(170); # Set Vbias Potentiometer (对比度值 0-255，170为经验值)
            
            # --- 扫描控制 ---
            c(0xa3); # Set Line Rate: 设置帧刷新率
            c(0xc8); d(0x2f); # Set COM Scan Direction: 更改行扫描顺序 (上下翻转)
            
            # --- 地址映射 ---
            c(0x89); c(0x95); # RAM Address Control: 设置 AC 范围和模式
            c(0x84); # Set COM0: 设置起始行
            c(0xf1); d(127); # Set COM End: 设置结束行 (128 Multiplex)
            c(0xc4); # LCD Map Control: 镜像/旋转控制
            c(0x86); # COM Scan Function
            
            # --- 滚动与窗口 ---
            c(0x40); c(0x50); # Set Scroll Line: 滚动起始行设为 0
            c(0x04); d(55);   # [关键] Set Column Address Offset: 修正屏幕物理偏移量 55
            
            # 窗口地址范围设置 (Window Program)
            c(0xf4); d(55);  # Window Start Column
            c(0xf6); d(182); # Window End Column (55 + 128 - 1)
            c(0xf5); d(0);   # Window Start Page
            c(0xf7); d(15);  # Window End Page
            c(0xf9); # Window Enable
            
            c(0xc9); d(0xad); # Display Enable: 开启显示，允许休眠模式唤醒
            return True
        except Exception as e:
            print(f"P3PLUS初始化失败: {str(e)}")
            return False
    
    def lcd_flush(self) -> bool:
        """将本地显存缓冲区(Display Buffer)写入 GRAM"""
        try:
            buffer = self.display_buffer
            for page in range(self.P3PLUS_PAGES_16):
                # 1. 设置页地址 (Page Address Set: 0x60 + LSB, 0x70 + MSB)
                self.spi.LCD_Command(0x60 | (page & 0x0F))
                self.spi.LCD_Command(0x70 | (page >> 4))
                
                # 2. 重置列地址 (因为每次写入后指针会偏移，且需要加 55 的物理 Offset)
                self.spi.LCD_Command(0x04); self.spi.LCD_Data(55)
                
                # 3. 发送 "Write Data" 命令 (0x01)
                self.spi.LCD_Command(0x01)
                
                # 4. 批量发送一整页 (128 Bytes) 数据
                # 利用 FTD2XXSPIInterface 的 Packetization，这一步是一次 USB 传输
                page_data = buffer[page * self.P3PLUS_COLS:(page + 1) * self.P3PLUS_COLS]
                self.spi.LCD_DataN(page_data)
            return True
        except Exception: return False

    def clear_screen(self, color: int = 0) -> bool:
        """清空显存"""
        val = 0xFF if color else 0x00
        self.display_buffer = [val] * (self.P3PLUS_PAGES_16 * self.P3PLUS_COLS)
        return True

    def lcd_draw_point(self, x: int, y: int, color: int) -> bool:
        """画点逻辑: 计算 Page 和 Bit 偏移"""
        if x < 0 or x >= self.P3PLUS_COLS or y < 0 or y >= self.P3PLUS_ROWS: return False
        page = y >> 3   # y / 8
        row = y & 0x7   # y % 8
        idx = page * self.P3PLUS_COLS + x
        
        if color & 1:
            self.display_buffer[idx] |= (1 << row) # 置位
        else:
            self.display_buffer[idx] &= ~(1 << row) # 清位
        return True

    def lcd_fill(self, x1: int, y1: int, x2: int, y2: int, color: int) -> bool:
        """
        区域填充函数: 优化的位操作，用于快速绘制大面积矩形。
        避免逐点调用的开销，直接操作 Byte 的掩码。
        """
        # 边界限制
        if x1 > self.P3PLUS_COLS - 1: x1 = self.P3PLUS_COLS - 1
        if x2 > self.P3PLUS_COLS - 1: x2 = self.P3PLUS_COLS - 1
        if y1 > self.P3PLUS_ROWS - 1: y1 = self.P3PLUS_ROWS - 1
        if y2 > self.P3PLUS_ROWS - 1: y2 = self.P3PLUS_ROWS - 1
        
        color = color & 1
        page1 = y1 >> 3
        page2 = y2 >> 3
        row1 = y1 & 0x7
        row2 = y2 & 0x7
        
        for page in range(page1, page2 + 1):
            # 计算当前页中需要覆盖的行范围
            row_start = row1 if page == page1 else 0
            row_end = row2 if page == page2 else 7
            
            # 生成掩码 (例如 0000 0111)
            mask = 0
            for i in range(row_start, row_end + 1):
                mask |= (1 << i)
            
            # 批量应用掩码到列
            for col in range(x1, x2 + 1):
                idx = page * self.P3PLUS_COLS + col
                if color:
                    self.display_buffer[idx] |= mask
                else:
                    self.display_buffer[idx] &= ~mask
        return True

    def lcd_draw_line(self, x1, y1, x2, y2, color: int) -> bool:
        """Bresenham 直线算法"""
        delta_x = abs(x2 - x1)
        delta_y = abs(y2 - y1)
        sx = 1 if x1 < x2 else -1
        sy = 1 if y1 < y2 else -1
        err = delta_x - delta_y
        while True:
            self.lcd_draw_point(x1, y1, color)
            if x1 == x2 and y1 == y2: break
            e2 = 2 * err
            if e2 > -delta_y:
                err -= delta_y
                x1 += sx
            if e2 < delta_x:
                err += delta_x
                y1 += sy
        return True
    
    def lcd_draw_rectangle(self, x1, y1, x2, y2, color: int) -> bool:
        self.lcd_draw_line(x1, y1, x2, y1, color)
        self.lcd_draw_line(x1, y1, x1, y2, color)
        self.lcd_draw_line(x1, y2, x2, y2, color)
        self.lcd_draw_line(x2, y1, x2, y2, color)
        return True
    
    def draw_circle(self, x0: int, y0: int, r: int, color: int) -> bool:
        """中点画圆算法 (Bresenham Circle)"""
        a, b = 0, r
        while a <= b:
            # 利用圆的8对称性
            self.lcd_draw_point(x0 - b, y0 - a, color)
            self.lcd_draw_point(x0 + b, y0 - a, color)
            self.lcd_draw_point(x0 - a, y0 + b, color)
            self.lcd_draw_point(x0 - a, y0 - b, color)
            self.lcd_draw_point(x0 + b, y0 + a, color)
            self.lcd_draw_point(x0 + a, y0 - b, color)
            self.lcd_draw_point(x0 + a, y0 + b, color)
            self.lcd_draw_point(x0 - b, y0 + a, color)
            a += 1
            if (a*a + b*b) > (r*r): b -= 1
        return True
    
    def lcd_show_char(self, x: int, y: int, char: str, fc: int, bc: int, size: int, mode: int = 0) -> bool:
        if size != 12: return False
        font_data = LCDFonts.get_ascii_1206_font(ord(char))
        # 字体绘制逻辑: 逐列扫描
        for i in range(12): # 高度
            for j in range(6): # 宽度
                # 判断字模位是否有效
                if font_data[i] & (0x01 << j):
                    self.lcd_draw_point(x + j, y + i, fc)
                elif not mode: # 非叠加模式下绘制背景色
                    self.lcd_draw_point(x + j, y + i, bc)
        return True

    def lcd_show_string(self, x: int, y: int, text: str, fc: int, bc: int, size: int, mode: int = 0) -> bool:
        for char in text:
            self.lcd_show_char(x, y, char, fc, bc, size, mode)
            x += size // 2 # 移动光标
        return True

    def lcd_show_int_num(self, x: int, y: int, num: int, length: int, fc: int, bc: int, size: int) -> bool:
        size_x = size // 2
        enshow = 0
        for t in range(length):
            temp = (num // (10 ** (length - t - 1))) % 10
            # 消除前导零
            if enshow == 0 and t < (length - 1):
                if temp == 0:
                    self.lcd_show_char(x + t * size_x, y, ' ', fc, bc, size, 0)
                    continue
                else: enshow = 1
            self.lcd_show_char(x + t * size_x, y, chr(temp + 48), fc, bc, size, 0)
        return True

    # ----------------------------------------------------
    # 新增图案业务逻辑
    # ----------------------------------------------------
    def draw_checkerboard(self):
        """
        绘制 3x3 棋盘格 (5黑4白)
        逻辑: 将128x128 屏幕划分为 3行3列，索引和为偶数时填充黑色。
        """
        self.clear_screen(0) 
        cols = [(0, 42), (43, 85), (86, 127)]
        rows = [(0, 42), (43, 85), (86, 127)]
        
        for r_idx in range(3):
            for c_idx in range(3):
                if (r_idx + c_idx) % 2 == 0:
                    x1, x2 = cols[c_idx]
                    y1, y2 = rows[r_idx]
                    self.lcd_fill(x1, y1, x2, y2, 1)

    def draw_split_screen(self):
        """
        绘制分屏图案:
        上半部分 (Y=0~63) 为白色 (0)
        下半部分 (Y=64~127) 为黑色 (1)
        """
        self.clear_screen(0)
        self.lcd_fill(0, 64, 127, 127, 1)

# ============================================================================
# 4. 主程序入口
# ============================================================================
def main():
    print("P3PLUS LCD 图案切换演示程序")
    print("-----------------------------------")
    print("状态 1: 几何图形与文字演示")
    print("状态 2: 3x3 棋盘格 (5黑4白)")
    print("状态 3: 上下分屏 (上白下黑)")
    print("逻辑: 每 5 秒自动切换，按 ESC 键退出")
    print("-----------------------------------")
    
    spi = FTD2XXSPIInterface(device_index=0, use_ctypes=True)
    
    if not spi.connect():
        print("错误: 无法连接 FTDI 设备，请检查 USB 连接或驱动。")
        return
    
    try:
        lcd = P3PLUSLCD(spi)
        if not lcd.P3PLUS_init():
            print("错误: LCD 控制器初始化失败。")
            return
        
        print("初始化成功，演示开始...")
        
        # 状态常量定义
        STATE_DEMO = 0
        STATE_CHECKERBOARD = 1
        STATE_SPLIT = 2
        
        current_state = STATE_DEMO
        
        while True:
            # 记录本轮状态开始时间
            start_time = time.time()
            
            # --- 绘图逻辑 ---
            if current_state == STATE_DEMO:
                print(f"[{time.strftime('%H:%M:%S')}] 切换至: 几何图形演示")
                lcd.clear_screen(0)
                lcd.lcd_draw_rectangle(0, 0, 127, 127, 1)  # 边框
                lcd.draw_circle(80, 40, 20, 1)             # 圆
                lcd.lcd_draw_line(0, 0, 127, 127, 1)       # 对角线
                lcd.lcd_show_string(10, 60, "Hello", 1, 0, 12, 1)
                lcd.lcd_show_string(10, 80, "P3PLUS LCD", 1, 0, 12, 1)
                lcd.lcd_show_int_num(10, 100, 12345, 5, 1, 0, 12)
                lcd.lcd_flush()
                
            elif current_state == STATE_CHECKERBOARD:
                print(f"[{time.strftime('%H:%M:%S')}] 切换至: 棋盘格")
                lcd.draw_checkerboard()
                lcd.lcd_flush()
                
            elif current_state == STATE_SPLIT:
                print(f"[{time.strftime('%H:%M:%S')}] 切换至: 分屏显示")
                lcd.draw_split_screen()
                lcd.lcd_flush()
            
            # --- 延时循环 (5秒) ---
            # 使用 0.1s 短延时轮询，确保 ESC 键能被及时响应，而不是阻塞 sleep 5秒
            exit_flag = False
            while (time.time() - start_time) < 5.0:
                if msvcrt.kbhit():
                    if msvcrt.getch() == b'\x1b': # ESC ASCII Code
                        exit_flag = True
                        break
                time.sleep(0.1)
            
            if exit_flag:
                print("检测到 ESC 键，程序退出。")
                break
                
            # --- 状态切换 ---
            current_state = (current_state + 1) % 3
            
    except Exception as e:
        print(f"运行时发生异常: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        spi.disconnect()
        print("SPI 连接已安全断开。")

if __name__ == "__main__":
    main()
