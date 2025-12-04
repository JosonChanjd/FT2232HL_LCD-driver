"""
P3Plus LCD
"""

import os
import time
import msvcrt
from typing import List, Optional, Tuple, Union
from ctypes import (
    windll, c_ulong, c_ubyte, c_char_p, c_void_p, c_int, POINTER, byref, create_string_buffer
)

# 路径配置
os.environ['FTD2XX_DLL_DIR'] = r'C:\Users\sesa696240\Desktop\PMDB'

try:
    import ftd2xx
    FTDI_AVAILABLE = True
except ImportError:
    FTDI_AVAILABLE = False

# ==========================================
# 1. LCD 字体数据 
# ==========================================
class LCDFonts:
    """LCD字体数据类"""
    @staticmethod
    def get_ascii_1206_font(char_code: int) -> List[int]:
        """获取6x12 ASCII字体数据"""
        ascii_1206 = {
            0: [0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00],  # 空格
            1: [0x00,0x00,0x04,0x04,0x04,0x04,0x04,0x00,0x00,0x04,0x00,0x00],  # !
            2: [0x14,0x14,0x0A,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00],  # "
            3: [0x00,0x00,0x0A,0x0A,0x1F,0x0A,0x0A,0x1F,0x0A,0x0A,0x00,0x00],  # #
            4: [0x00,0x04,0x0E,0x15,0x05,0x06,0x0C,0x14,0x15,0x0E,0x04,0x00],  # $
            5: [0x00,0x00,0x12,0x15,0x0D,0x15,0x2E,0x2C,0x2A,0x12,0x00,0x00],  # %
            6: [0x00,0x00,0x04,0x0A,0x0A,0x36,0x15,0x15,0x29,0x16,0x00,0x00],  # &
            7: [0x02,0x02,0x01,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00],  # '
            8: [0x10,0x08,0x08,0x04,0x04,0x04,0x04,0x04,0x08,0x08,0x10,0x00],  # (
            9: [0x02,0x04,0x04,0x08,0x08,0x08,0x08,0x08,0x04,0x04,0x02,0x00],  # )
            10: [0x00,0x00,0x00,0x04,0x15,0x0E,0x0E,0x15,0x04,0x00,0x00,0x00],  # *
            11: [0x00,0x00,0x00,0x08,0x08,0x3E,0x08,0x08,0x00,0x00,0x00,0x00],  # +
            12: [0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x02,0x02,0x01,0x00],  # ,
            13: [0x00,0x00,0x00,0x00,0x00,0x3F,0x00,0x00,0x00,0x00,0x00,0x00],  # -
            14: [0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x02,0x00,0x00],  # .
            15: [0x00,0x20,0x10,0x10,0x08,0x08,0x04,0x04,0x02,0x02,0x01,0x00],  # /
            16: [0x00,0x00,0x0E,0x11,0x11,0x11,0x11,0x11,0x11,0x0E,0x00,0x00],  # 0
            17: [0x00,0x00,0x04,0x06,0x04,0x04,0x04,0x04,0x04,0x0E,0x00,0x00],  # 1
            18: [0x00,0x00,0x0E,0x11,0x11,0x08,0x04,0x02,0x01,0x1F,0x00,0x00],  # 2
            19: [0x00,0x00,0x0E,0x11,0x10,0x0C,0x10,0x10,0x11,0x0E,0x00,0x00],  # 3
            20: [0x00,0x00,0x08,0x0C,0x0C,0x0A,0x09,0x1F,0x08,0x1C,0x00,0x00],  # 4
            21: [0x00,0x00,0x1F,0x01,0x01,0x0F,0x11,0x10,0x11,0x0E,0x00,0x00],  # 5
            22: [0x00,0x00,0x0C,0x12,0x01,0x0D,0x13,0x11,0x11,0x0E,0x00,0x00],  # 6
            23: [0x00,0x00,0x1E,0x10,0x08,0x08,0x04,0x04,0x04,0x04,0x00,0x00],  # 7
            24: [0x00,0x00,0x0E,0x11,0x11,0x0E,0x11,0x11,0x11,0x0E,0x00,0x00],  # 8
            25: [0x00,0x00,0x0E,0x11,0x11,0x19,0x16,0x10,0x09,0x06,0x00,0x00],  # 9
            32: [0x00,0x00,0x1C,0x22,0x29,0x2D,0x2D,0x1D,0x22,0x1C,0x00,0x00],  # @
            65: [0x00,0x00,0x04,0x04,0x0C,0x0A,0x0A,0x1E,0x12,0x33,0x00,0x00],  # A
            66: [0x00,0x00,0x0F,0x12,0x12,0x0E,0x12,0x12,0x12,0x0F,0x00,0x00],  # B
            79: [0x00,0x00,0x0E,0x11,0x11,0x11,0x11,0x11,0x11,0x0E,0x00,0x00],  # O
            80: [0x00,0x00,0x0F,0x12,0x12,0x0E,0x02,0x02,0x02,0x07,0x00,0x00],  # P
            83: [0x00,0x00,0x1E,0x02,0x0C,0x10,0x1E,0x00,0x00,0x00,0x00,0x00],  # S
            97: [0x00,0x00,0x00,0x00,0x00,0x0C,0x12,0x1C,0x12,0x3C,0x00,0x00],  # a
            111: [0x00,0x00,0x00,0x00,0x00,0x0C,0x12,0x12,0x12,0x0C,0x00,0x00], # o
            112: [0x00,0x00,0x00,0x00,0x00,0x0F,0x12,0x12,0x12,0x0E,0x02,0x07], # p
            115: [0x00,0x00,0x00,0x00,0x00,0x1E,0x02,0x0C,0x10,0x1E,0x00,0x00], # s
        }
        return ascii_1206.get(char_code, [0] * 12)

# ==========================================
# 2. FTDI SPI 接口
# ==========================================
class FTD2XXSPIInterface:
    """基于FTD2XX.DLL的SPI接口实现"""
    # FTDI常量
    FT_OK = 0
    FT_BITMODE_RESET = 0x00
    FT_BITMODE_MPSSE = 0x02
    
    # MPSSE命令
    CMD_SET_DATA_BITS_LOW = 0x80
    CMD_SET_DATA_BITS_HIGH = 0x82
    CMD_SEND_IMMEDIATE = 0x87
    CMD_CLOCK_FALL_OUT_BYTES = 0x11
    CMD_CLOCK_RISE_OUT_BYTES = 0x10
    
    # GPIO引脚定义 (FT232H High Byte: A0=bit0, A1=bit1, A2=bit2)
    PIN_A0 = 0       # 对应硬件Pin8
    PIN_RESET = 1    # 对应硬件Pin9
    PIN_CS = 2       # 对应硬件Pin10

    def __init__(self, device_index: int = 0, use_ctypes: bool = False):
        self.device_index = device_index
        self.use_ctypes = use_ctypes
        self.device_handle = None
        self.is_connected = False
        
        # SPI默认配置
        self.spi_mode = 0
        self.clock_speed = 1000000
        
        # GPIO状态缓存
        self.gpio_low = {'val': 0x00, 'dir': 0x00}  # Low byte: SCLK(0), MOSI(1), MISO(2), CS0-4(3-7)
        self.gpio_high = {'val': 0x07, 'dir': 0x07} # High byte: A0/A1/A2输出，默认高电平
        
        if use_ctypes:
            self._init_dll()
    
    def _init_dll(self):
        """初始化DLL"""
        dll_names = [
            r'C:\Users\sesa696240\Desktop\PMDB\FTD2XX.DLL',
            'FTD2XX.DLL',
            'ftd2xx.dll'
        ]
        self.ftd2xx_dll = None
        for name in dll_names:
            try:
                self.ftd2xx_dll = windll.LoadLibrary(name)
                break
            except OSError:
                continue
        
        if not self.ftd2xx_dll:
            raise Exception("无法加载FTD2XX.DLL")
        
        # 设置函数原型
        funcs = [
            ('FT_Open', [c_int, POINTER(c_void_p)], c_ulong),
            ('FT_Close', [c_void_p], c_ulong),
            ('FT_Write', [c_void_p, c_void_p, c_ulong, POINTER(c_ulong)], c_ulong),
            ('FT_Read', [c_void_p, c_void_p, c_ulong, POINTER(c_ulong)], c_ulong),
            ('FT_SetBitMode', [c_void_p, c_ubyte, c_ubyte], c_ulong),
            ('FT_SetUSBParameters', [c_void_p, c_ulong, c_ulong], c_ulong),
            ('FT_SetLatencyTimer', [c_void_p, c_ubyte], c_ulong),
            ('FT_Purge', [c_void_p, c_ulong], c_ulong),
            ('FT_GetQueueStatus', [c_void_p, POINTER(c_ulong)], c_ulong),
        ]
        for name, args, res in funcs:
            f = getattr(self.ftd2xx_dll, name)
            f.argtypes = args
            f.restype = res

    def _clear_input_buffer(self):
        """清理输入缓冲区"""
        """1(PURGE_TXABORT):中止所有待发送的输出操作"""
        """2(PURGE_RXABORT):中止所有待接收的输出操作"""
        if not self.use_ctypes: 
            if hasattr(self.device_handle, 'purge'):
                self.device_handle.purge(3)
            return

        q_status = c_ulong()
        self.ftd2xx_dll.FT_GetQueueStatus(self.device_handle, byref(q_status))
        if q_status.value > 0:
            self.ftd2xx_dll.FT_Read(
                self.device_handle, 
                create_string_buffer(q_status.value), 
                q_status.value, 
                byref(c_ulong())
            )

    def _mpsse_sync(self):
        """MPSSE同步（确保MPSSE模式正常）"""
        # 标准MPSSE同步流程：发送0xAA，读取响应0xBB
        self._write_data([0xAA])
        time.sleep(0.001)
        resp = self._read_data(1)
        if resp != b'\xBB':
            # 重试同步
            self._write_data([0xAB, 0xAB])
            time.sleep(0.001)
            self._clear_input_buffer()

    def connect(self) -> bool:
        """连接FTDI设备"""
        try:
            if self.use_ctypes:
                handle = c_void_p()
                if self.ftd2xx_dll.FT_Open(self.device_index, byref(handle)) != self.FT_OK:
                    return False
                self.device_handle = handle
                # 配置USB参数
                self.ftd2xx_dll.FT_SetUSBParameters(handle, 65536, 65536)
                self.ftd2xx_dll.FT_SetLatencyTimer(handle, 1)
                # 重置模式并切换到MPSSE
                self.ftd2xx_dll.FT_SetBitMode(handle, 0, self.FT_BITMODE_RESET)
                time.sleep(0.01)
                self.ftd2xx_dll.FT_SetBitMode(handle, 0, self.FT_BITMODE_MPSSE)
                self.ftd2xx_dll.FT_Purge(handle, 3)  # 清空RX/TX缓冲区
            else:
                if not FTDI_AVAILABLE:
                    return False
                self.device_handle = ftd2xx.open(self.device_index)
                self.device_handle.setUSBParameters(65536, 65536)
                self.device_handle.setLatencyTimer(1)
                self.device_handle.setBitMode(0, self.FT_BITMODE_RESET)
                time.sleep(0.01)
                self.device_handle.setBitMode(0, self.FT_BITMODE_MPSSE)
                self.device_handle.purge(3)

            # MPSSE同步
            self._mpsse_sync()
            self._initialize_mpsse()
            self.is_connected = True
            return True
        except Exception as e:
            print(f"连接错误: {e}")
            return False

    def disconnect(self):
        """断开设备连接"""
        if self.device_handle:
            try:
                if self.use_ctypes:
                    self.ftd2xx_dll.FT_Close(self.device_handle)
                else:
                    self.device_handle.close()
            except Exception as e:
                print(f"断开连接错误: {e}")
        self.is_connected = False

    def _initialize_mpsse(self):
        """初始化MPSSE模式"""
        # 计算分频系数 (FT232H时钟12MHz)
        divisor = max(0, min(0xFFFF, int(12000000 / (2 * self.clock_speed)) - 1))
        
        # GPIO配置: 
        # Low byte - SCLK(0)=输出, MOSI(1)=输出, MISO(2)=输入, 其他=输出
        self.gpio_low['dir'] = 0xFB  # 11111011 (MISO输入)
        self.gpio_low['val'] = 0x00 if self.spi_mode <= 1 else 0x01  # CPOL
        
        # High byte - A0/A1/A2=输出 (默认高电平)
        self.gpio_high['dir'] = 0x07  # 00000111
        self.gpio_high['val'] = 0x07  # 默认高电平

        # 发送初始化命令
        cmds = [
            0x8A,                   # 禁用5分频
            0x97,                   # 禁用自适应时钟
            0x8D,                   # 禁用3相时钟
            0x86, divisor & 0xFF, (divisor >> 8) & 0xFF,  # 设置时钟分频
            0x85,                   # 禁用环回模式
            self.CMD_SET_DATA_BITS_LOW, self.gpio_low['val'], self.gpio_low['dir'],
            self.CMD_SET_DATA_BITS_HIGH, self.gpio_high['val'], self.gpio_high['dir']
        ]
        self._write_data(cmds)
        time.sleep(0.001)

    def _write_data(self, data: Union[List[int], bytes, bytearray]):
        """底层数据发送"""
        if not self.device_handle or not data:
            return
        
        b_data = bytes(data) if not isinstance(data, (bytes, bytearray)) else data
        if self.use_ctypes:
            written = c_ulong()
            self.ftd2xx_dll.FT_Write(self.device_handle, b_data, len(b_data), byref(written))
        else:
            self.device_handle.write(b_data)
        time.sleep(0.0001)  # 轻微延时确保数据发送完成

    def _read_data(self, length: int) -> bytes:
        """底层数据读取"""
        if not self.device_handle or length <= 0:
            return b''
        
        if self.use_ctypes:
            buf = create_string_buffer(length)
            read = c_ulong()
            self.ftd2xx_dll.FT_Read(self.device_handle, buf, length, byref(read))
            return buf.raw[:read.value]
        return self.device_handle.read(length)

    def configure_spi(self, mode: int, speed: int):
        """配置SPI模式和速度"""
        self.spi_mode = max(0, min(3, mode))
        self.clock_speed = max(100000, min(6000000, speed))  # 限制速度范围
        if self.is_connected:
            self._initialize_mpsse()

    def _make_spi_prefix(self) -> List[int]:
        """生成SPI操作前缀指令"""
        cpol = 1 if self.spi_mode >= 2 else 0
        val = self.gpio_low['val'] & ~0x01 | cpol
        return [self.CMD_SET_DATA_BITS_LOW, val, self.gpio_low['dir']]

    def spi_write(self, data: Union[List[int], bytes]) -> bool:
        """SPI数据发送"""
        if not self.is_connected or not data:
            return False
        
        cmds = self._make_spi_prefix()
        cpol, cpha = (self.spi_mode >= 2), (self.spi_mode % 2)
        cmd_byte = self.CMD_CLOCK_FALL_OUT_BYTES if (cpol == cpha) else self.CMD_CLOCK_RISE_OUT_BYTES
        
        data_len = len(data)
        if data_len == 0:
            return True
        
        # MPSSE长度格式: 长度-1 (LSB, MSB)
        len_lsb = (data_len - 1) & 0xFF
        len_msb = ((data_len - 1) >> 8) & 0xFF
        
        cmds.extend([cmd_byte, len_lsb, len_msb])
        cmds.extend(data)
        self._write_data(cmds)
        return True

    def _update_gpio(self, high_byte: bool, pin_idx: int, val: bool):
        """更新GPIO状态"""
        target = self.gpio_high if high_byte else self.gpio_low
        mask = 1 << pin_idx
        if val:
            target['val'] |= mask
        else:
            target['val'] &= ~mask
        target['dir'] |= mask  # 设置为输出
        
        # 发送GPIO更新指令
        cmd = self.CMD_SET_DATA_BITS_HIGH if high_byte else self.CMD_SET_DATA_BITS_LOW
        self._write_data([cmd, target['val'], target['dir']])
        time.sleep(0.0005)

    # GPIO控制方法
    def set_a0(self, state: bool):
        """设置A0引脚状态"""
        self._update_gpio(True, self.PIN_A0, state)

    def set_reset(self, state: bool):
        """设置RESET引脚状态"""
        self._update_gpio(True, self.PIN_RESET, state)

    def set_cs_main(self, state: bool):
        """设置CS引脚状态"""
        self._update_gpio(True, self.PIN_CS, state)

    def LCD_Reset(self):
        """LCD硬件复位"""
        self.set_reset(False)  # 拉低复位
        time.sleep(0.01)       # 保持复位
        self.set_reset(True)   # 释放复位
        time.sleep(0.01)

    def LCD_Command(self, cmd: int):
        """发送LCD命令"""
        self.set_a0(False)
        self.set_cs_main(False)
        self.spi_write([cmd & 0xFF])
        self.set_cs_main(True)
        time.sleep(0.0005)

    def LCD_Data(self, val: int):
        """发送单个LCD数据"""
        self.set_a0(True)
        self.set_cs_main(False)
        self.spi_write([val & 0xFF])
        self.set_cs_main(True)
        time.sleep(0.0005)

    def LCD_DataN(self, data: Union[List[int], bytearray]):
        """发送多个LCD数据"""
        self.set_a0(True)
        self.set_cs_main(False)
        self.spi_write(data)
        self.set_cs_main(True)
        time.sleep(0.0005)

# ==========================================
# 3. PMDB LCD 驱动
# ==========================================
class PMDBLCD:
    def __init__(self, spi: FTD2XXSPIInterface):
        self.spi = spi
        self.width = 128
        self.height = 128
        self.buffer = bytearray(self.width * (self.height // 8))  # 128x128 = 16页x128列

    def init_controller(self):
        """初始化LCD控制器"""
        try:
            # 硬件复位
            self.spi.LCD_Reset()
            time.sleep(0.01)

            # 初始化命令序列（修正命令/数据分类）
            init_cmds = [
                # 基础配置
                (True, 0xE1),    # 软复位命令
                (True, 0xA4),    # 正常显示（非全亮）
                (True, 0xA6),    # 正常显示（非反显）
                (True, 0xB8),    # MTP模式
                (False, 0x00),   # MTP参数
                (True, 0x81),    # 对比度设置
                (False, 170),    # 对比度值
                (True, 0xA3),    # 帧率设置
                (True, 0xC8),    # 扫描方向
                (False, 0x2F),   # 扫描参数
                (True, 0x89),    # RAM控制
                (True, 0x95),    # RAM参数
                (True, 0x84),    # COM配置
                (True, 0xF1),    # COM参数1
                (False, 127),    # COM参数2
                (True, 0xC4),    # 映射配置
                (True, 0x86),    # 扫描线配置
                (True, 0x40),    # 滚动配置
                (True, 0x50),    # 滚动参数
                # 窗口配置
                (True, 0x04),    # 列地址低4位
                (False, 55),     # 列地址值
                (True, 0x60),    # 页地址
                (True, 0x70),    # 页地址扩展
                (True, 0xF4),    # 窗口1
                (False, 55),     # 窗口1参数
                (True, 0xF6),    # 窗口2
                (False, 182),    # 窗口2参数
                (True, 0xF5),    # 窗口3
                (False, 0),      # 窗口3参数
                (True, 0xF7),    # 窗口4
                (False, 15),     # 窗口4参数
                (True, 0xF9),    # 窗口5
                (False, 0),      # 窗口5参数（补充缺失的参数）
                (True, 0xC9),    # 使能配置
                (False, 0xAD),   # 使能参数
            ]

            # 执行初始化命令
            for is_cmd, val in init_cmds:
                if is_cmd:
                    self.spi.LCD_Command(val)
                else:
                    self.spi.LCD_Data(val)
            
            time.sleep(0.05)  # 初始化完成延时
            return True
        except Exception as e:
            print(f"LCD初始化错误: {e}")
            return False

    def flush(self):
        """刷新缓冲区到屏幕"""
        for page in range(self.height // 8):
            # 设置页地址 (0xB0 + page)
            self.spi.LCD_Command(0xB0 + page)
            # 设置列地址低4位
            self.spi.LCD_Command(0x00)
            # 设置列地址高4位
            self.spi.LCD_Command(0x10)
            # 发送当前页数据
            start = page * self.width
            self.spi.LCD_DataN(self.buffer[start:start + self.width])

    def clear(self, color: int = 0):
        """清空屏幕缓冲区"""
        val = 0xFF if color else 0x00
        self.buffer = bytearray([val] * len(self.buffer))

    def draw_point(self, x: int, y: int, color: int):
        """绘制单个像素"""
        if not (0 <= x < self.width and 0 <= y < self.height):
            return
        
        page = y // 8
        bit = y % 8
        idx = page * self.width + x
        
        if color:
            self.buffer[idx] |= (1 << bit)
        else:
            self.buffer[idx] &= ~(1 << bit)

    def draw_line(self, x1, y1, x2, y2, color):
        """绘制直线（Bresenham算法）"""
        dx = abs(x2 - x1)
        sx = 1 if x1 < x2 else -1
        dy = -abs(y2 - y1)
        sy = 1 if y1 < y2 else -1
        err = dx + dy

        while True:
            self.draw_point(x1, y1, color)
            if x1 == x2 and y1 == y2:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x1 += sx
            if e2 <= dx:
                err += dx
                y1 += sy

    def draw_rect(self, x1, y1, x2, y2, color):
        """绘制矩形"""
        self.draw_line(x1, y1, x2, y1, color)
        self.draw_line(x1, y2, x2, y2, color)
        self.draw_line(x1, y1, x1, y2, color)
        self.draw_line(x2, y1, x2, y2, color)

    def draw_circle(self, x0, y0, r, color):
        """绘制圆形"""
        f = 1 - r
        ddF_x = 1
        ddF_y = -2 * r
        x = 0
        y = r

        self.draw_point(x0, y0 + r, color)
        self.draw_point(x0, y0 - r, color)
        self.draw_point(x0 + r, y0, color)
        self.draw_point(x0 - r, y0, color)

        while x < y:
            if f >= 0:
                y -= 1
                ddF_y += 2
                f += ddF_y
            x += 1
            ddF_x += 2
            f += ddF_x

            # 8对称点绘制
            points = [
                (x0+x, y0+y), (x0-x, y0+y),
                (x0+x, y0-y), (x0-x, y0-y),
                (x0+y, y0+x), (x0-y, y0+x),
                (x0+y, y0-x), (x0-y, y0-x)
            ]
            for px, py in points:
                self.draw_point(px, py, color)

    def show_string(self, x, y, text, size=12, color=1):
        """显示字符串"""
        if size != 12:
            return
        
        for char in text:
            if x + 6 > self.width:
                break
            
            code = ord(char)
            font = LCDFonts.get_ascii_1206_font(code) if code < 128 else [0]*12

            # 绘制6x12字符
            for r in range(12):
                row_data = font[r] if r < len(font) else 0
                for c in range(6):
                    if row_data & (1 << (5 - c)):
                        self.draw_point(x + c, y + r, color)
                    else:
                        self.draw_point(x + c, y + r, 0)
            
            x += 6  # 字符间距（6列宽度）

# ==========================================
# 主程序
# ==========================================
def main():
    print("LCD Driver Demo (Fixed & Optimized)")
    spi = None
    try:
        # 初始化SPI接口
        spi = FTD2XXSPIInterface(device_index=0, use_ctypes=True)
        if not spi.connect():
            print("无法连接FTDI设备")
            return
        
        # 配置SPI
        spi.configure_spi(0, 500000)  # SPI Mode 0, 500kHz
        lcd = PMDBLCD(spi)

        # 初始化LCD
        if not lcd.init_controller():
            print("LCD初始化失败")
            return

        print("LCD初始化完成，按ESC退出...")
        
        # 绘制初始界面
        lcd.clear(0)
        lcd.draw_rect(0, 0, 127, 127, 1)
        lcd.draw_line(0, 0, 127, 127, 1)
        lcd.draw_circle(64, 64, 30, 1)
        lcd.show_string(10, 10, "Fixed & Optimized!", 12)
        lcd.flush()

        # 主循环
        blink_flag = False
        while True:
            # 清除原位置字符
            lcd.show_string(10, 30, "Blinking...", 12, 0)
            # 绘制新状态字符
            lcd.show_string(10, 30, "Blinking...", 12, 1 if blink_flag else 0)
            lcd.flush()
            
            blink_flag = not blink_flag

            # 检测ESC按键退出
            if msvcrt.kbhit():
                key = msvcrt.getch()
                if key == b'\x1b':  # ESC键
                    print("退出程序...")
                    break
            
            time.sleep(0.5)

    except Exception as e:
        print(f"程序运行错误: {e}")
    finally:
        # 确保设备断开连接
        if spi and spi.is_connected:
            spi.disconnect()

if __name__ == "__main__":
    main()
