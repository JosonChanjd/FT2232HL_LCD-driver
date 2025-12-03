"""
PMDB LCD 驱动完整版 (Merged)
包含: 
1. LCD_FONTS (字库)
2. FTDI_SPI_INTERFACE (底层通信)
3. PMDB_LCD (屏幕驱动与主逻辑)

注意: 请确保 C:\\Users\\sesa696240\\Desktop\\PMDB 路径下存在 FTD2XX.DLL
"""

import os
import time
import struct
import msvcrt
from typing import List, Optional, Tuple, Dict, Union
from ctypes import (
    windll, c_ulong, c_uint, c_ushort, c_ubyte, c_char, c_void_p, 
    c_char_p, c_int, c_long, POINTER, byref, create_string_buffer
)

# 设置FTD2XX DLL路径 (保持原路径)
os.environ['FTD2XX_DLL_DIR'] = r'C:\Users\sesa696240\Desktop\PMDB'

# 尝试导入 ftd2xx 库，如果没有则标记为不可用
try:
    import ftd2xx
    FTDI_AVAILABLE = True
except ImportError:
    FTDI_AVAILABLE = False
    # print("警告: 未安装ftd2xx库，将使用ctypes直接调用DLL")

# ==========================================
# 第一部分: LCD 字体数据 (LCD_FONTS)
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
            26: [0x00,0x00,0x00,0x00,0x04,0x00,0x00,0x00,0x00,0x04,0x00,0x00],  # :
            27: [0x00,0x00,0x00,0x00,0x00,0x04,0x00,0x00,0x00,0x04,0x04,0x00],  # ;
            28: [0x00,0x00,0x10,0x08,0x04,0x02,0x02,0x04,0x08,0x10,0x00,0x00],  # <
            29: [0x00,0x00,0x00,0x00,0x3F,0x00,0x3F,0x00,0x00,0x00,0x00,0x00],  # =
            30: [0x00,0x00,0x02,0x04,0x08,0x10,0x10,0x08,0x04,0x02,0x00,0x00],  # >
            31: [0x00,0x00,0x0E,0x11,0x11,0x08,0x04,0x04,0x00,0x04,0x00,0x00],  # ?
            32: [0x00,0x00,0x1C,0x22,0x29,0x2D,0x2D,0x1D,0x22,0x1C,0x00,0x00],  # @
            33: [0x00,0x00,0x04,0x04,0x0C,0x0A,0x0A,0x1E,0x12,0x33,0x00,0x00],  # A
            34: [0x00,0x00,0x0F,0x12,0x12,0x0E,0x12,0x12,0x12,0x0F,0x00,0x00],  # B
            35: [0x00,0x00,0x1E,0x11,0x01,0x01,0x01,0x01,0x11,0x0E,0x00,0x00],  # C
            36: [0x00,0x00,0x0F,0x12,0x12,0x12,0x12,0x12,0x12,0x0F,0x00,0x00],  # D
            37: [0x00,0x00,0x1F,0x12,0x0A,0x0E,0x0A,0x02,0x12,0x1F,0x00,0x00],  # E
            38: [0x00,0x00,0x1F,0x12,0x0A,0x0E,0x0A,0x02,0x02,0x07,0x00,0x00],  # F
            39: [0x00,0x00,0x1C,0x12,0x01,0x01,0x39,0x11,0x12,0x0C,0x00,0x00],  # G
            40: [0x00,0x00,0x33,0x12,0x12,0x1E,0x12,0x12,0x12,0x33,0x00,0x00],  # H
            41: [0x00,0x00,0x1F,0x04,0x04,0x04,0x04,0x04,0x04,0x1F,0x00,0x00],  # I
            42: [0x00,0x00,0x3E,0x08,0x08,0x08,0x08,0x08,0x08,0x08,0x09,0x07],  # J
            43: [0x00,0x00,0x37,0x12,0x0A,0x06,0x0A,0x12,0x12,0x37,0x00,0x00],  # K
            44: [0x00,0x00,0x07,0x02,0x02,0x02,0x02,0x02,0x22,0x3F,0x00,0x00],  # L
            45: [0x00,0x00,0x3B,0x1B,0x1B,0x1B,0x15,0x15,0x15,0x35,0x00,0x00],  # M
            46: [0x00,0x00,0x3B,0x12,0x16,0x16,0x1A,0x1A,0x12,0x17,0x00,0x00],  # N
            47: [0x00,0x00,0x0E,0x11,0x11,0x11,0x11,0x11,0x11,0x0E,0x00,0x00],  # O
            48: [0x00,0x00,0x0F,0x12,0x12,0x0E,0x02,0x02,0x02,0x07,0x00,0x00],  # P
            49: [0x00,0x00,0x0E,0x11,0x11,0x11,0x11,0x17,0x19,0x0E,0x18,0x00],  # Q
            50: [0x00,0x00,0x0F,0x12,0x12,0x0E,0x0A,0x12,0x12,0x37,0x00,0x00],  # R
            51: [0x00,0x00,0x1E,0x11,0x01,0x06,0x08,0x10,0x11,0x0F,0x00,0x00],  # S
            52: [0x00,0x00,0x1F,0x15,0x04,0x04,0x04,0x04,0x04,0x0E,0x00,0x00],  # T
            53: [0x00,0x00,0x33,0x12,0x12,0x12,0x12,0x12,0x12,0x0C,0x00,0x00],  # U
            54: [0x00,0x00,0x33,0x12,0x12,0x0A,0x0A,0x0C,0x04,0x04,0x00,0x00],  # V
            55: [0x00,0x00,0x15,0x15,0x15,0x15,0x0E,0x0A,0x0A,0x0A,0x00,0x00],  # W
            56: [0x00,0x00,0x1B,0x0A,0x0A,0x04,0x04,0x0A,0x0A,0x1B,0x00,0x00],  # X
            57: [0x00,0x00,0x1B,0x0A,0x0A,0x0A,0x04,0x04,0x04,0x0E,0x00,0x00],  # Y
            58: [0x00,0x00,0x1F,0x09,0x08,0x04,0x04,0x02,0x12,0x1F,0x00,0x00],  # Z
            59: [0x1C,0x04,0x04,0x04,0x04,0x04,0x04,0x04,0x04,0x04,0x1C,0x00],  # [
            60: [0x00,0x02,0x02,0x04,0x04,0x04,0x08,0x08,0x08,0x10,0x10,0x00],  # \
            61: [0x0E,0x08,0x08,0x08,0x08,0x08,0x08,0x08,0x08,0x08,0x0E,0x00],  # ]
            62: [0x04,0x0A,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00],  # ^
            63: [0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x3F],  # _
            64: [0x02,0x04,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00],  # `
            65: [0x00,0x00,0x00,0x00,0x00,0x0C,0x12,0x1C,0x12,0x3C,0x00,0x00],  # a
            66: [0x00,0x03,0x02,0x02,0x02,0x0E,0x12,0x12,0x12,0x0E,0x00,0x00],  # b
            67: [0x00,0x00,0x00,0x00,0x00,0x1C,0x12,0x02,0x12,0x0C,0x00,0x00],  # c
            68: [0x00,0x18,0x10,0x10,0x10,0x1C,0x12,0x12,0x12,0x3C,0x00,0x00],  # d
            69: [0x00,0x00,0x00,0x00,0x00,0x0C,0x12,0x1E,0x02,0x1C,0x00,0x00],  # e
            70: [0x00,0x18,0x24,0x04,0x04,0x1E,0x04,0x04,0x04,0x1E,0x00,0x00],  # f
            71: [0x00,0x00,0x00,0x00,0x00,0x3C,0x12,0x0C,0x02,0x1C,0x22,0x1C],  # g
            72: [0x00,0x03,0x02,0x02,0x02,0x0E,0x12,0x12,0x12,0x37,0x00,0x00],  # h
            73: [0x00,0x04,0x04,0x00,0x00,0x06,0x04,0x04,0x04,0x0E,0x00,0x00],  # i
            74: [0x00,0x08,0x08,0x00,0x00,0x0C,0x08,0x08,0x08,0x08,0x08,0x07],  # j
            75: [0x00,0x03,0x02,0x02,0x02,0x1A,0x0A,0x06,0x0A,0x13,0x00,0x00],  # k
            76: [0x00,0x07,0x04,0x04,0x04,0x04,0x04,0x04,0x04,0x1F,0x00,0x00],  # l
            77: [0x00,0x00,0x00,0x00,0x00,0x0F,0x15,0x15,0x15,0x15,0x00,0x00],  # m
            78: [0x00,0x00,0x00,0x00,0x00,0x0F,0x12,0x12,0x12,0x37,0x00,0x00],  # n
            79: [0x00,0x00,0x00,0x00,0x00,0x0C,0x12,0x12,0x12,0x0C,0x00,0x00],  # o
            80: [0x00,0x00,0x00,0x00,0x00,0x0F,0x12,0x12,0x12,0x0E,0x02,0x07],  # p
            81: [0x00,0x00,0x00,0x00,0x00,0x1C,0x12,0x12,0x12,0x1C,0x10,0x38],  # q
            82: [0x00,0x00,0x00,0x00,0x00,0x1B,0x06,0x02,0x02,0x07,0x00,0x00],  # r
            83: [0x00,0x00,0x00,0x00,0x00,0x1E,0x02,0x0C,0x10,0x1E,0x00,0x00],  # s
            84: [0x00,0x00,0x00,0x04,0x04,0x1E,0x04,0x04,0x04,0x1C,0x00,0x00],  # t
            85: [0x00,0x00,0x00,0x00,0x00,0x1B,0x12,0x12,0x12,0x3C,0x00,0x00],  # u
            86: [0x00,0x00,0x00,0x00,0x00,0x1B,0x0A,0x0A,0x04,0x04,0x00,0x00],  # v
            87: [0x00,0x00,0x00,0x00,0x00,0x15,0x15,0x0E,0x0A,0x0A,0x00,0x00],  # w
            88: [0x00,0x00,0x00,0x00,0x00,0x1B,0x0A,0x04,0x0A,0x1B,0x00,0x00],  # x
            89: [0x00,0x00,0x00,0x00,0x00,0x33,0x12,0x12,0x0C,0x08,0x04,0x03],  # y
            90: [0x00,0x00,0x00,0x00,0x00,0x1E,0x08,0x04,0x04,0x1E,0x00,0x00],  # z
            91: [0x18,0x08,0x08,0x08,0x08,0x0C,0x08,0x08,0x08,0x08,0x18,0x00],  # {
            92: [0x08,0x08,0x08,0x08,0x08,0x08,0x08,0x08,0x08,0x08,0x08,0x08],  # |
            93: [0x06,0x04,0x04,0x04,0x04,0x08,0x04,0x04,0x04,0x04,0x06,0x00],  # }
            94: [0x16,0x09,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00],  # ~
        }
        return ascii_1206.get(char_code, [0] * 12)
    
    @staticmethod
    def get_ascii_1608_font(char_code: int) -> List[int]:
        """获取8x16 ASCII字体数据"""
        # 这里应该包含完整的字体数据，暂时返回空数据
        return [0] * 16
    
    @staticmethod
    def get_ascii_2412_font(char_code: int) -> List[int]:
        """获取12x24 ASCII字体数据"""
        # 这里应该包含完整的字体数据，暂时返回空数据
        return [0] * 24
    
    @staticmethod
    def get_ascii_3216_font(char_code: int) -> List[int]:
        """获取16x32 ASCII字体数据"""
        # 这里应该包含完整的字体数据，暂时返回空数据
        return [0] * 32
    
    @staticmethod
    def get_chinese_12x12_font(char_bytes: bytes) -> List[int]:
        """获取12x12中文字体数据"""
        # 这里应该包含中文字体数据，暂时返回空数据
        return [0] * 24
    
    @staticmethod
    def get_chinese_16x16_font(char_bytes: bytes) -> List[int]:
        """获取16x16中文字体数据"""
        # 这里应该包含中文字体数据，暂时返回空数据
        return [0] * 32
    
    @staticmethod
    def get_chinese_24x24_font(char_bytes: bytes) -> List[int]:
        """获取24x24中文字体数据"""
        # 这里应该包含中文字体数据，暂时返回空数据
        return [0] * 72
    
    @staticmethod
    def get_chinese_32x32_font(char_bytes: bytes) -> List[int]:
        """获取32x32中文字体数据"""
        # 这里应该包含中文字体数据，暂时返回空数据
        return [0] * 128


# ==========================================
# 第二部分: FTDI SPI 接口 (FTDI_SPI_INTERFACE)
# ==========================================

class FTD2XXSPIInterface:
    """基于FTD2XX.DLL的SPI接口实现"""
    
    # FT_STATUS 错误代码
    FT_OK = 0
    FT_INVALID_HANDLE = 1
    FT_DEVICE_NOT_FOUND = 2
    FT_DEVICE_NOT_OPENED = 3
    FT_IO_ERROR = 4
    FT_INSUFFICIENT_RESOURCES = 5
    FT_INVALID_PARAMETER = 6
    FT_INVALID_BAUD_RATE = 7
    FT_DEVICE_NOT_OPENED_FOR_ERASE = 8
    FT_DEVICE_NOT_OPENED_FOR_WRITE = 9
    FT_FAILED_TO_WRITE_DEVICE = 10
    FT_EEPROM_READ_FAILED = 11
    FT_EEPROM_WRITE_FAILED = 12
    FT_EEPROM_ERASE_FAILED = 13
    FT_EEPROM_NOT_PRESENT = 14
    FT_EEPROM_NOT_PROGRAMMED = 15
    FT_INVALID_ARGS = 16
    FT_NOT_SUPPORTED = 17
    FT_OTHER_ERROR = 18
    FT_DEVICE_LIST_NOT_READY = 19
    
    # 设备类型
    FT_DEVICE_2232H = 6
    
    # 位模式
    FT_BITMODE_RESET = 0x00
    FT_BITMODE_ASYNC_BITBANG = 0x01
    FT_BITMODE_MPSSE = 0x02
    FT_BITMODE_SYNC_BITBANG = 0x04
    FT_BITMODE_MCU_HOST = 0x08
    FT_BITMODE_FAST_SERIAL = 0x10
    FT_BITMODE_CBUS_BITBANG = 0x20
    FT_BITMODE_SYNC_FIFO = 0x40
    
    # MPSSE命令定义
    CMD_SET_DATA_BITS_LOW = 0x80
    CMD_SET_DATA_BITS_HIGH = 0x82
    CMD_READ_DATA_BITS_LOW = 0x81
    CMD_READ_DATA_BITS_HIGH = 0x83
    CMD_SET_CLOCK_DIVISOR = 0x86
    CMD_SET_LOOPBACK = 0x84
    CMD_DISABLE_LOOPBACK = 0x85
    CMD_SEND_IMMEDIATE = 0x87
    CMD_WAIT_ON_HIGH = 0x88
    CMD_WAIT_ON_LOW = 0x89
    CMD_CLOCK_RISE_OUT_BYTES = 0x10
    CMD_CLOCK_FALL_OUT_BYTES = 0x11
    CMD_CLOCK_RISE_IN_BYTES = 0x20
    CMD_CLOCK_FALL_IN_BYTES = 0x24
    CMD_CLOCK_FALL_OUT_RISE_IN_BYTES = 0x31
    CMD_CLOCK_RISE_OUT_FALL_IN_BYTES = 0x34
    CMD_CLOCK_RISE_OUT_BITS = 0x12
    CMD_CLOCK_FALL_OUT_BITS = 0x13
    CMD_CLOCK_RISE_IN_BITS = 0x22
    CMD_CLOCK_FALL_IN_BITS = 0x26
    CMD_CLOCK_FALL_OUT_RISE_IN_BITS = 0x33
    CMD_CLOCK_RISE_OUT_FALL_IN_BITS = 0x36
    
    # SPI模式定义
    SPI_MODE_0 = 0  # CPOL=0, CPHA=0
    SPI_MODE_1 = 1  # CPOL=0, CPHA=1
    SPI_MODE_2 = 2  # CPOL=1, CPHA=0
    SPI_MODE_3 = 3  # CPOL=1, CPHA=1
    
    def __init__(self, device_index: int = 0, use_ctypes: bool = False):
        """
        初始化FTD2XX SPI接口
        
        Args:
            device_index: 设备索引
            use_ctypes: 是否使用ctypes直接调用DLL（默认使用ftd2xx库）
        """
        self.device_index = device_index
        self.use_ctypes = use_ctypes
        self.device_handle = None
        self.is_connected = False
        
        # SPI配置
        self.spi_mode = self.SPI_MODE_0
        self.clock_speed = 1000000  # 1MHz
        self.clock_divisor = 0
        
        # 引脚定义
        self.PIN_SCLK = 0   # AD0
        self.PIN_MOSI = 1   # AD1
        self.PIN_MISO = 2   # AD2
        self.PIN_CS0 = 3    # AD3
        self.PIN_CS1 = 4    # AD4
        self.PIN_CS2 = 5    # AD5
        self.PIN_CS3 = 6    # AD6
        self.PIN_CS4 = 7    # AD7
        
        # GPIO引脚定义 (高8位)
        self.PIN_A0 = 8     # AD8
        self.PIN_RESET = 9  # AD9
        self.PIN_CS = 10    # AD10
        
        # GPIO状态 (低8位和高8位)
        self.gpio_direction_low = 0x00
        self.gpio_value_low = 0x00
        self.gpio_direction_high = 0x00
        self.gpio_value_high = 0x00
        
        # 初始化DLL
        if use_ctypes:
            self._init_dll()
    
    def _init_dll(self):
        """初始化FTD2XX DLL"""
        try:
            # 尝试加载DLL
            dll_paths = [
                r'C:\Users\sesa696240\Desktop\PMDB\FTD2XX.DLL',
                'FTD2XX.DLL',
                'ftd2xx.dll'
            ]
            
            self.ftd2xx_dll = None
            for dll_path in dll_paths:
                try:
                    self.ftd2xx_dll = windll.LoadLibrary(dll_path)
                    print(f"成功加载DLL: {dll_path}")
                    break
                except OSError:
                    continue
            
            if not self.ftd2xx_dll:
                raise Exception("无法加载FTD2XX.DLL")
            
            # 设置函数原型
            self._setup_dll_functions()
            
        except Exception as e:
            raise Exception(f"初始化DLL失败: {str(e)}")
    
    def _setup_dll_functions(self):
        """设置DLL函数原型"""
        # FT_Open
        self.ftd2xx_dll.FT_Open.argtypes = [c_int, POINTER(c_void_p)]
        self.ftd2xx_dll.FT_Open.restype = c_ulong
        
        # FT_Close
        self.ftd2xx_dll.FT_Close.argtypes = [c_void_p]
        self.ftd2xx_dll.FT_Close.restype = c_ulong
        
        # FT_Write
        self.ftd2xx_dll.FT_Write.argtypes = [c_void_p, c_void_p, c_ulong, POINTER(c_ulong)]
        self.ftd2xx_dll.FT_Write.restype = c_ulong
        
        # FT_Read
        self.ftd2xx_dll.FT_Read.argtypes = [c_void_p, c_void_p, c_ulong, POINTER(c_ulong)]
        self.ftd2xx_dll.FT_Read.restype = c_ulong
        
        # FT_SetBitMode
        self.ftd2xx_dll.FT_SetBitMode.argtypes = [c_void_p, c_ubyte, c_ubyte]
        self.ftd2xx_dll.FT_SetBitMode.restype = c_ulong
        
        # FT_SetUSBParameters
        self.ftd2xx_dll.FT_SetUSBParameters.argtypes = [c_void_p, c_ulong, c_ulong]
        self.ftd2xx_dll.FT_SetUSBParameters.restype = c_ulong
        
        # FT_SetLatencyTimer
        self.ftd2xx_dll.FT_SetLatencyTimer.argtypes = [c_void_p, c_ubyte]
        self.ftd2xx_dll.FT_SetLatencyTimer.restype = c_ulong
        
        # FT_Purge
        self.ftd2xx_dll.FT_Purge.argtypes = [c_void_p, c_ulong]
        self.ftd2xx_dll.FT_Purge.restype = c_ulong
        
        # FT_GetDeviceInfo
        self.ftd2xx_dll.FT_GetDeviceInfo.argtypes = [c_void_p, POINTER(c_ulong), c_char_p, c_char_p, c_void_p]
        self.ftd2xx_dll.FT_GetDeviceInfo.restype = c_ulong
        
        # FT_GetQueueStatus
        self.ftd2xx_dll.FT_GetQueueStatus.argtypes = [c_void_p, POINTER(c_ulong)]
        self.ftd2xx_dll.FT_GetQueueStatus.restype = c_ulong
        
        # FT_ResetDevice
        self.ftd2xx_dll.FT_ResetDevice.argtypes = [c_void_p]
        self.ftd2xx_dll.FT_ResetDevice.restype = c_ulong
    
    def _clear_input_buffer(self):
        """清空输入缓冲区（基于官方C代码）"""
        try:
            if self.use_ctypes:
                # 使用ctypes检查队列状态
                queue_status = c_ulong()
                status = self.ftd2xx_dll.FT_GetQueueStatus(self.device_handle, byref(queue_status))
                
                if status == self.FT_OK and queue_status.value > 0:
                    print(f"  发现缓冲区中有 {queue_status.value} 字节残留数据，正在清理...")
                    
                    # 读取并清空缓冲区
                    buffer_size = min(queue_status.value, 1024)  # 限制读取大小
                    buffer = create_string_buffer(buffer_size)
                    bytes_read = c_ulong()
                    
                    read_status = self.ftd2xx_dll.FT_Read(
                        self.device_handle,
                        buffer,
                        c_ulong(buffer_size),
                        byref(bytes_read)
                    )
                    
                    if read_status == self.FT_OK:
                        print(f"  ✓ 成功清理 {bytes_read.value} 字节残留数据")
                    else:
                        print(f"  ⚠ 清理残留数据失败，状态码: {read_status}")
                else:
                    print("  ✓ 缓冲区已清空")
            else:
                # 使用ftd2xx库
                if hasattr(self.device_handle, 'getQueueStatus'):
                    queue_status = self.device_handle.getQueueStatus()
                    if queue_status > 0:
                        print(f"  发现缓冲区中有 {queue_status} 字节残留数据，正在清理...")
                        # 读取并清空缓冲区
                        buffer_size = min(queue_status, 1024)
                        self.device_handle.read(buffer_size)
                        print(f"  ✓ 成功清理 {buffer_size} 字节残留数据")
                    else:
                        print("  ✓ 缓冲区已清空")
                else:
                    print("  ✓ 跳过缓冲区检查（ftd2xx库版本不支持）")
                    
        except Exception as e:
            print(f"  ⚠ 缓冲区清理过程中出错: {str(e)}")
    
    def connect(self) -> bool:
        """
        连接到FTDI设备
        
        Returns:
            bool: 连接是否成功
        """
        try:
            if self.use_ctypes:
                return self._connect_ctypes()
            else:
                return self._connect_ftd2xx()
        except Exception as e:
            print(f"连接失败: {str(e)}")
            return False
    
    def _connect_ctypes(self) -> bool:
        """使用ctypes连接设备"""
        if not self.ftd2xx_dll:
            raise Exception("DLL未初始化")
        
        # 打开设备
        handle = c_void_p()
        status = self.ftd2xx_dll.FT_Open(c_int(self.device_index), byref(handle))
        
        if status != self.FT_OK:
            raise Exception(f"打开设备失败，状态码: {status}")
        
        self.device_handle = handle
        
        # 设置USB参数
        self.ftd2xx_dll.FT_SetUSBParameters(self.device_handle, c_ulong(65536), c_ulong(65536))
        self.ftd2xx_dll.FT_SetLatencyTimer(self.device_handle, c_ubyte(1))
        
        # 复位位模式
        self.ftd2xx_dll.FT_SetBitMode(self.device_handle, c_ubyte(0x00), c_ubyte(self.FT_BITMODE_RESET))
        time.sleep(0.01)
        
        # 设置为MPSSE模式
        self.ftd2xx_dll.FT_SetBitMode(self.device_handle, c_ubyte(0x00), c_ubyte(self.FT_BITMODE_MPSSE))
        time.sleep(0.01)
        
        # 清空缓冲区 - 先检查并读取残留数据
        self._clear_input_buffer()
        
        # 然后执行标准清空操作
        self.ftd2xx_dll.FT_Purge(self.device_handle, c_ulong(0x01 | 0x02))  # PURGE_RX | PURGE_TX
        
        # 初始化MPSSE
        self._initialize_mpsse()
        
        self.is_connected = True
        print(f"FTDI设备连接成功 (ctypes)，索引: {self.device_index}")
        return True
    
    def _connect_ftd2xx(self) -> bool:
        """使用ftd2xx库连接设备"""
        if not FTDI_AVAILABLE:
            raise Exception("ftd2xx库未安装")
        
        try:
            # 打开设备
            print(f"正在打开设备 {self.device_index}...")
            self.device_handle = ftd2xx.open(self.device_index)
            print("设备打开成功")
            
            # 设置USB参数
            print("设置USB参数...")
            self.device_handle.setUSBParameters(65536, 65536)
            self.device_handle.setLatencyTimer(1)
            print("USB参数设置成功")
            
            # 复位位模式
            print("复位位模式...")
            self.device_handle.setBitMode(0x00, 0x00)  # 复位
            time.sleep(0.01)
            print("位模式复位成功")
            
            # 设置为MPSSE模式
            print("设置为MPSSE模式...")
            self.device_handle.setBitMode(0x00, 0x02)  # MPSSE模式
            time.sleep(0.01)
            print("MPSSE模式设置成功")
            
            # 清空缓冲区
            print("清空缓冲区...")
            self._clear_input_buffer()
            self.device_handle.purge(ftd2xx.defines.PURGE_RX | ftd2xx.defines.PURGE_TX)
            print("缓冲区清空成功")
            
            # 初始化MPSSE
            print("初始化MPSSE...")
            self._initialize_mpsse()
            print("MPSSE初始化成功")
            
            self.is_connected = True
            print(f"FTDI设备连接成功 (ftd2xx)，索引: {self.device_index}")
            return True
            
        except Exception as e:
            print(f"连接过程中出错: {str(e)}")
            import traceback
            traceback.print_exc()
            if self.device_handle:
                try:
                    self.device_handle.close()
                except:
                    pass
                self.device_handle = None
            raise e
    
    def disconnect(self):
        """断开连接"""
        try:
            if self.device_handle:
                if self.use_ctypes:
                    self.ftd2xx_dll.FT_Close(self.device_handle)
                else:
                    self.device_handle.close()
                self.device_handle = None
            self.is_connected = False
            print("FTDI设备已断开连接")
        except Exception as e:
            print(f"断开连接时出错: {str(e)}")
    
    def _initialize_mpsse(self):
        """初始化MPSSE"""
        try:
            # 发送同步序列
            print("  发送第一个同步序列...")
            sync_commands = [0xAA, 0x00]
            self._write_data(sync_commands)
            time.sleep(0.01)
            print("  ✓ 第一个同步序列发送成功")
            
            # 再次发送同步序列确保设备进入MPSSE模式
            print("  发送第二个同步序列...")
            sync_commands = [0xAB, 0x00]
            self._write_data(sync_commands)
            time.sleep(0.01)
            print("  ✓ 第二个同步序列发送成功")
            
            # 额外的MPSSE配置（基于官方代码）
            print("  配置MPSSE参数...")
            mpsse_config = [
                0x8A,  # 确保禁用时钟分频5 (60MHz主时钟)
                0x97,  # 确保关闭自适应时钟
                0x8D,  # 禁用3相数据时钟
            ]
            self._write_data(mpsse_config)
            time.sleep(0.02)  # 20ms延时
            print("  ✓ MPSSE参数配置完成")
            
            # 计算时钟分频器
            self.clock_divisor = int(12000000 / (2 * self.clock_speed)) - 1
            self.clock_divisor = max(0, min(0xFFFF, self.clock_divisor))
            print(f"  时钟分频器: {self.clock_divisor} (目标频率: {self.clock_speed}Hz)")
            
            # 设置引脚方向
            cpol, cpha = self._get_spi_config()
            
            # 根据CPOL设置初始时钟状态
            if cpol == 0:
                low_value = 0x00  # 时钟AD0空闲时为低电平
            else:
                low_value = 0x01  # 时钟AD0空闲时为高电平 
            
            # 设置引脚方向：SCLK(AD0)=输出, MOSI(AD1)=输出, MISO(AD2)=输入
            # 根据官方代码，使用0x0b (bit0=SK输出, bit1=DO输出, bit3=GPIOL0输出)
            low_direction = 0x0b  # bit 0(SCLK)和bit 1(MOSI)为输出，bit 3为输出，bit 2(MISO)为输入
            
            # 设置高8位GPIO方向：A0(AD8)=输出, RESET(AD9)=输出, CS(AD10)=输出
            high_direction = 0x07  # bit 0(A0), bit 1(RESET), bit 2(CS)为输出
            high_value = 0x07  # 初始值都为低电平
            
            init_commands = [
                # 设置时钟分频器
                self.CMD_SET_CLOCK_DIVISOR,
                self.clock_divisor & 0xFF,
                (self.clock_divisor >> 8) & 0xFF,
                
                # 禁用环回
                self.CMD_DISABLE_LOOPBACK,
                
                 # 设置GPIO方向 (低8位)
                self.CMD_SET_DATA_BITS_LOW,
                low_value,
                low_direction,
                
                 # 设置GPIO方向 (高8位)
                self.CMD_SET_DATA_BITS_HIGH,
                high_value,
                high_direction,

               
            ]
            
            print(f"  发送MPSSE初始化命令: {[hex(x) for x in init_commands]}")
            self._write_data(init_commands)
            time.sleep(0.01)
            print("  ✓ 初始化命令发送成功")
            
            # 更新GPIO状态
            self.gpio_direction_low = low_direction
            self.gpio_value_low = low_value
            self.gpio_direction_high = high_direction
            self.gpio_value_high = high_value
            
        except Exception as e:
            print(f"  ✗ MPSSE初始化失败: {str(e)}")
            raise e
    
             
    def _write_data(self, data: List[int]):
        """写入数据到设备"""
        if not self.device_handle:
            raise Exception("设备句柄无效")
        
        data_bytes = bytes(data)
        
        if self.use_ctypes:
            bytes_written = c_ulong()
            status = self.ftd2xx_dll.FT_Write(
                self.device_handle, 
                data_bytes, 
                c_ulong(len(data_bytes)), 
                byref(bytes_written)
            )
            if status != self.FT_OK:
                raise Exception(f"写入失败，状态码: {status}")
        else:
            self.device_handle.write(data_bytes)
    
    def _read_data(self, length: int) -> bytes:
        """从设备读取数据"""
        if not self.device_handle:
            raise Exception("设备句柄无效")
        
        if self.use_ctypes:
            buffer = create_string_buffer(length)
            bytes_read = c_ulong()
            status = self.ftd2xx_dll.FT_Read(
                self.device_handle,
                buffer,
                c_ulong(length),
                byref(bytes_read)
            )
            if status != self.FT_OK:
                raise Exception(f"读取失败，状态码: {status}")
            return buffer.raw[:bytes_read.value]
        else:
            return self.device_handle.read(length)
    
    def configure_spi(self, mode: int, clock_speed: int) -> bool:
        """
        配置SPI参数
        
        Args:
            mode: SPI模式 (0-3)
            clock_speed: 时钟频率 (Hz)
            
        Returns:
            bool: 配置是否成功
        """
        if not self.is_connected:
            raise Exception("设备未连接")
        
        if mode not in [0, 1, 2, 3]:
            raise ValueError(f"不支持的SPI模式: {mode}")
        
        self.spi_mode = mode
        self.clock_speed = clock_speed
        
        # 重新初始化MPSSE
        self._initialize_mpsse()
        
        print(f"SPI配置: 模式={mode}, 频率={clock_speed}Hz")
        return True
    
    def _get_spi_config(self) -> Tuple[int, int]:
        """获取SPI配置参数"""
        mode_configs = {
            0: (0, 0),  # CPOL=0, CPHA=0
            1: (0, 1),  # CPOL=0, CPHA=1
            2: (1, 0),  # CPOL=1, CPHA=0
            3: (1, 1),  # CPOL=1, CPHA=1
        }
        return mode_configs[self.spi_mode]
    
    def spi_write(self, data: List[int]) -> bool:
        """
        SPI写操作
        
        Args:
            data: 要发送的数据列表
            
        Returns:
            bool: 操作是否成功
        """
        if not self.is_connected:
            raise Exception("设备未连接")
        
        if not data:
            return True
        
        cpol, cpha = self._get_spi_config()
        #print(f"cpol, cpha=: {cpol,cpha}")
        # 构造SPI传输命令
        commands = []
        
        # 设置引脚方向
        low_direction = 0x0b  # SCLK和MOSI为输出，MISO为输入，bit3为输出
        low_value_start = 0x00 if cpol == cpha else 0x01  # 根据CPOL设置初始时钟AD0状态
        low_value_end = 0x00 if cpol == 0 else 0x01  # 根据CPOL设置初始时钟AD0状态
        
        commands.extend([
            self.CMD_SET_DATA_BITS_LOW,
            low_value_start,
            low_direction,
        ])
        
        # 添加数据长度和SPI命令
        data_len = len(data) - 1
        
        if cpol == cpha: #模式0 or 模式3
            commands.extend([
                self.CMD_CLOCK_FALL_OUT_BYTES, #CMD_CLOCK_RISE_OUT_BYTES,
                data_len & 0xFF,
                (data_len >> 8) & 0xFF,
            ])
        
        else:  # 模式1 or 模式2
            commands.extend([
                self.CMD_CLOCK_RISE_OUT_BYTES,
                data_len & 0xFF,
                (data_len >> 8) & 0xFF,
            ])
        
        # 添加数据
        commands.extend(data)
        
        # Resume Clock State
        #commands.extend([
        #   self.CMD_SET_DATA_BITS_LOW,
        #   low_value_end,
        #   low_direction,
        #   ])
        # 发送命令
        self._write_data(commands)
        return True
    
    def spi_read(self, length: int) -> List[int]:
        """
        SPI读操作
        
        Args:
            length: 要读取的字节数
            
        Returns:
            List[int]: 读取到的数据
        """
        if not self.is_connected:
            raise Exception("设备未连接")
        
        if length <= 0:
            return []
        
        self._clear_input_buffer() # clear input buffer befoe reading
        
        cpol, cpha = self._get_spi_config()
        
        # 构造SPI读取命令
        commands = []
        
        # 设置引脚方向
        low_direction = 0x0b  # SCLK和MOSI为输出，MISO为输入，bit3为输出
        low_value_start = 0x00 if cpol == cpha else 0x01  # 根据CPOL设置初始时钟AD0状态
        low_value_end = 0x00 if cpol == 0 else 0x01  # 根据CPOL设置初始时钟AD0状态
        
        commands.extend([
            self.CMD_SET_DATA_BITS_LOW,
            low_value_start,
            low_direction,
        ])
        
        # 添加读取长度和SPI命令
        data_len = length - 1
        
        if cpol == 0 and cpha == 0:  # 模式0
            commands.extend([
                self.CMD_CLOCK_RISE_IN_BYTES,
                data_len & 0xFF,
                (data_len >> 8) & 0xFF,
            ])
        elif cpol == 0 and cpha == 1:  # 模式1
            commands.extend([
                self.CMD_CLOCK_FALL_IN_BYTES,
                data_len & 0xFF,
                (data_len >> 8) & 0xFF,
            ])
        elif cpol == 1 and cpha == 0:  # 模式2
            commands.extend([
                self.CMD_CLOCK_FALL_IN_BYTES,
                data_len & 0xFF,
                (data_len >> 8) & 0xFF,
            ])
        else:  # 模式3
            commands.extend([
                self.CMD_CLOCK_RISE_IN_BYTES,
                data_len & 0xFF,
                (data_len >> 8) & 0xFF,
            ])
        #resume SCLK to initial state
        commands.extend([
            self.CMD_SET_DATA_BITS_LOW,
            low_value_end,
            low_direction,
        ])
        # 发送命令
        self._write_data(commands)
        
        # 读取响应数据
        try:
            response = self._read_data(length)
            
            return list(response)
        except Exception as e:
            print(f"SPI读操作失败: {str(e)}")
            
            return []
    
    def spi_transfer(self, data: List[int]) -> List[int]:
        """
        SPI全双工传输
        
        Args:
            data: 要发送的数据列表
            
        Returns:
            List[int]: 接收到的数据列表
        """
        if not self.is_connected:
            raise Exception("设备未连接")
        
        if not data:
            return []
        
        self._clear_input_buffer() # clear input buffer befoe transfer
        
        cpol, cpha = self._get_spi_config()
        
        # 构造SPI传输命令
        commands = []
        
        # 设置引脚方向
        low_direction = 0x0b  # SCLK和MOSI为输出，MISO为输入，bit3为输出
        low_value_start = 0x00 if cpol == cpha else 0x01  # 根据CPOL设置初始时钟AD0状态
        low_value_end = 0x00 if cpol == 0 else 0x01  # 根据CPOL设置初始时钟AD0状态
        
        commands.extend([
            self.CMD_SET_DATA_BITS_LOW,
            low_value_start,
            low_direction,
        ])
        
        # 添加数据长度和SPI命令
        data_len = len(data) - 1
        
        if cpol == 0 and cpha == 0:  # 模式0
            commands.extend([
                self.CMD_CLOCK_FALL_OUT_RISE_IN_BYTES,
                data_len & 0xFF,
                (data_len >> 8) & 0xFF,
            ])
        elif cpol == 0 and cpha == 1:  # 模式1
            commands.extend([
                self.CMD_CLOCK_RISE_OUT_FALL_IN_BYTES,
                data_len & 0xFF,
                (data_len >> 8) & 0xFF,
            ])
        elif cpol == 1 and cpha == 0:  # 模式2
            commands.extend([
                self.CMD_CLOCK_RISE_OUT_FALL_IN_BYTES,
                data_len & 0xFF,
                (data_len >> 8) & 0xFF,
            ])
        else:  # 模式3
            commands.extend([
                self.CMD_CLOCK_FALL_OUT_RISE_IN_BYTES,
                data_len & 0xFF,
                (data_len >> 8) & 0xFF,
            ])
        
        # 添加数据
        commands.extend(data)
        # resume SCLK to initial state
        commands.extend([
            self.CMD_SET_DATA_BITS_LOW,
            low_value_end,
            low_direction,
        ])
        # 发送命令
        self._write_data(commands)
        
        # 读取响应数据
        try:
            response = self._read_data(len(data))
            
            return list(response)
        except Exception as e:
            print(f"SPI传输失败: {str(e)}")
            
            return []
    
    def spi_write_read(self, write_data: List[int], read_length: int) -> List[int]:
        """
        SPI写后读操作
        
        Args:
            write_data: 要发送的数据
            read_length: 要读取的字节数
            
        Returns:
            List[int]: 读取到的数据
        """
        # 先发送数据
        if write_data:
            self.spi_write(write_data)
        
        # 再读取数据
        return self.spi_read(read_length)
    
    
    def set_gpio_pin(self, pin: int, state: bool) -> bool:
        if pin < 0 or pin > 15:
            raise ValueError(f"GPIO引脚超出范围: {pin}")
        # 更新GPIO状态
        if pin <= 7:  # 低8位
            if state:
                self.gpio_value_low |= (1 << pin)
            else:
                self.gpio_value_low &= ~(1 << pin)
            self.gpio_direction_low |= (1 << pin)  # 设置为输出
        else:  # 高8位
            pin_bit = pin - 8
            if state:
                self.gpio_value_high |= (1 << pin_bit)
            else:
                self.gpio_value_high &= ~(1 << pin_bit)
            self.gpio_direction_high |= (1 << pin_bit)  # 设置为输出

        return True
    def gpio_output(self) -> bool:
        """
        设置GPIO引脚状态
        
        Args:
            pin: GPIO引脚 (0-15)
            state: 状态 (True=高电平, False=低电平)
            
        Returns:
            bool: 操作是否成功
        """
        if not self.is_connected:
            raise Exception("设备未连接")
        # 发送命令
        commands = [
            self.CMD_SET_DATA_BITS_LOW,
            self.gpio_value_low,
            self.gpio_direction_low,
            self.CMD_SET_DATA_BITS_HIGH,
            self.gpio_value_high,
            self.gpio_direction_high,
        ]
        
        self._write_data(commands)
        return True
        
    def gpio_high_output(self) -> bool:
        """
        设置GPIO引脚状态
        
        Args:
            pin: GPIO引脚 (0-15)
            state: 状态 (True=高电平, False=低电平)
            
        Returns:
            bool: 操作是否成功
        """
        if not self.is_connected:
            raise Exception("设备未连接")
        # 发送命令
        commands = [
            self.CMD_SET_DATA_BITS_LOW,
            self.gpio_value_low,
            self.gpio_direction_low,
            self.CMD_SET_DATA_BITS_HIGH,
            self.gpio_value_high,
            self.gpio_direction_high,
        ]
        
        self._write_data(commands)
        return True
    def set_gpio_direction(self, pin: int, direction: int) -> bool:
        """
        设置GPIO引脚方向
        
        Args:
            pin: GPIO引脚 (0-15)
            direction: 方向 (0=输入, 1=输出)
            
        Returns:
            bool: 操作是否成功
        """
        if not self.is_connected:
            raise Exception("设备未连接")
        
        if pin < 0 or pin > 15:
            raise ValueError(f"GPIO引脚超出范围: {pin}")
        
        # 更新GPIO方向
        if pin <= 7:  # 低8位
            if direction:
                self.gpio_direction_low |= (1 << pin)
            else:
                self.gpio_direction_low &= ~(1 << pin)
        else:  # 高8位
            pin_bit = pin - 8
            if direction:
                self.gpio_direction_high |= (1 << pin_bit)
            else:
                self.gpio_direction_high &= ~(1 << pin_bit)
        
        self.gpio_output() 
        
        return True
    
    def read_gpio_pin(self, pin: int) -> Optional[bool]:
        """
        读取GPIO引脚状态
        
        Args:
            pin: GPIO引脚 (0-15)
            
        Returns:
            Optional[bool]: GPIO状态，None表示读取失败
        """
        if not self.is_connected:
            raise Exception("设备未连接")
        
        if pin < 0 or pin > 15:
            raise ValueError(f"GPIO引脚超出范围: {pin}")
        
        try:
            # 发送读取命令
            commands = [
                self.CMD_READ_DATA_BITS_LOW,
                self.CMD_READ_DATA_BITS_HIGH,
                self.CMD_SEND_IMMEDIATE,
            ]
            self._write_data(commands)
            
            # 读取响应 (2字节：低8位和高8位)
            response = self._read_data(2)
            if len(response) >= 2:
                low_byte = response[0]
                high_byte = response[1]
                
                if pin <= 7:  # 低8位
                    return bool(low_byte & (1 << pin))
                else:  # 高8位
                    pin_bit = pin - 8
                    return bool(high_byte & (1 << pin_bit))
            return None
        except Exception as e:
            print(f"读取GPIO{pin}失败: {str(e)}")
            return None
    
    def set_a0(self, state: bool) -> bool:
        """
        设置A0引脚状态
        
        Args:
            state: 状态 (True=高电平, False=低电平)
            
        Returns:
            bool: 操作是否成功
        """
        return self.set_gpio_pin(self.PIN_A0, state)
    
    def set_reset(self, state: bool) -> bool:
        """
        设置RESET引脚状态
        
        Args:
            state: 状态 (True=高电平, False=低电平)
            
        Returns:
            bool: 操作是否成功
        """
        return self.set_gpio_pin(self.PIN_RESET, state)
    
    def set_cs_main(self, state: bool) -> bool:
        """
        设置主CS引脚状态 (AD10)
        
        Args:
            state: 状态 (True=低电平选中, False=高电平未选中)
            
        Returns:
            bool: 操作是否成功
        """
        return self.set_gpio_pin(self.PIN_CS, state)
    
    def LCD_Reset(self) -> bool:
        """
        复位设备 (拉低RESET引脚)
        
        Returns:
            bool: 操作是否成功
        """
        try:
            # 拉低RESET
            self.set_reset(False)
            self.gpio_high_output()
            time.sleep(0.02)  # 保持10ms
            # 拉高RESET
            self.set_reset(True)
            self.gpio_high_output()
            time.sleep(0.02)  # 等待设备稳定
            return True
        except Exception as e:
            print(f"设备复位失败: {str(e)}")
            return False
        
    def LCD_Command(self, command: int) -> bool:
        """
        发送LCD命令
        
        Args:
            command: LCD命令
        """
        if not self.is_connected:
            raise Exception("设备未连接")
        self.set_a0(False)  # in order to save time, only change the flag
        self.gpio_high_output() # output a0 and cs in the same MPSSE group
        self.set_cs_main(False) # in order to save time, only change the flag
        self.gpio_high_output() # output a0 and cs in the same MPSSE group
        self.spi_write([command])
        self.set_cs_main(True) # output a0 and cs in the same MPSSE group
        self.gpio_high_output()
        return True
    
    def LCD_Data(self, data: int) -> bool:
        """
        发送LCD数据
        
        Args:
            data: LCD数据
        """
        if not self.is_connected:
            raise Exception("设备未连接")
        self.set_a0(True) # in order to save time, only change the flag
        self.gpio_high_output() # output a0 and cs in the same MPSSE group
        self.set_cs_main(False) # in order to save time, only change the flag
        self.gpio_high_output() # output a0 and cs in the same MPSSE group
        self.spi_write([data])
        self.set_cs_main(True)
        self.gpio_high_output() # output a0 and cs in the same MPSSE group
        return True
    
    def LCD_DataN(self, data_list: List[int]) -> bool:
        """
        发送LCD数据
        
        Args:
            data_list: LCD数据列表
        """
        if not self.is_connected:
            raise Exception("设备未连接")
        self.set_a0(True) # in order to save time, only change the flag
        self.gpio_high_output() # output a0 and cs in the same MPSSE group
        self.set_cs_main(False) # in order to save time, only change the flag
        self.gpio_high_output()  # output a0 and cs in the same MPSSE group
        self.spi_write(data_list)
        self.set_cs_main(True)  
        self.gpio_high_output()  # output a0 and cs in the same MPSSE group
        return True
    
    def LCD_ReceiveData(self) -> int:
        """
        从LCD读取1字节数据
        """
        if not self.is_connected:
            raise Exception("设备未连接")
        self.set_a0(True)
        self.gpio_high_output() # output a0 and cs in the same MPSSE group
        self.set_cs_main(True)
        self.gpio_high_output() # output a0 and cs in the same MPSSE group
        data = self.spi_read(1)
        self.set_cs_main(False)
        self.gpio_high_output() # output a0 and cs in the same MPSSE group
        return data[0]
    
    def get_device_info(self) -> dict:
        """获取设备信息"""
        if not self.is_connected:
            return {}
        
        try:
            if self.use_ctypes:
                # 使用ctypes获取设备信息
                device_type = c_ulong()
                device_id = c_ulong()
                serial_number = create_string_buffer(16)
                description = create_string_buffer(64)
                
                status = self.ftd2xx_dll.FT_GetDeviceInfo(
                    self.device_handle,
                    byref(device_type),
                    serial_number,
                    description,
                    byref(device_id)
                )
                
                if status == self.FT_OK:
                    return {
                        "device_index": self.device_index,
                        "device_type": device_type.value,
                        "device_id": device_id.value,
                        "serial_number": serial_number.value.decode('utf-8', errors='ignore'),
                        "description": description.value.decode('utf-8', errors='ignore'),
                        "spi_mode": self.spi_mode,
                        "clock_speed": self.clock_speed,
                    }
            else:
                # 使用ftd2xx库获取设备信息
                info = self.device_handle.getDeviceInfo()
                return {
                    "device_index": self.device_index,
                    "description": info[0],
                    "serial_number": info[1],
                    "device_id": info[2],
                    "spi_mode": self.spi_mode,
                    "clock_speed": self.clock_speed,
                }
        except Exception as e:
            print(f"获取设备信息失败: {str(e)}")
            return {}


# ==========================================
# 第三部分: PMDB LCD 驱动 (PMDB_LCD)
# ==========================================

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

# ==========================================
# 主程序入口 (Main)
# ==========================================

def main():
    """主函数 - 演示LCD驱动使用"""
    print("PMDB LCD驱动演示 (合并版)")
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
        iloop=0
        
        # 注意：此处原逻辑为 while False, 已修改为 while True 以保证程序运行
        while True:
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
