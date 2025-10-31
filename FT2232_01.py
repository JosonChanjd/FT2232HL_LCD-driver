import os
import time
import struct
import msvcrt
from typing import List, Optional, Tuple, Union, Dict
from ctypes import (
    windll, c_ulong, c_uint, c_ushort, c_ubyte, c_char, c_void_p, 
    c_char_p, c_int, c_long, POINTER, byref, create_string_buffer
)

# 设置FTD2XX DLL路径
os.environ['FTD2XX_DLL_DIR'] = r'C:\Users\sesa696240\Desktop\PMDB'

# 尝试导入ftd2xx库，兼容ctypes模式
try:
    import ftd2xx
    FTDI_AVAILABLE = True
except ImportError:
    FTDI_AVAILABLE = False
    print("警告: 未安装ftd2xx库，将使用ctypes直接调用DLL")


class LCDFonts:
    """LCD字体数据类（原lcd_fonts.py完整内容）"""
    
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
        return [0] * 16
    
    @staticmethod
    def get_ascii_2412_font(char_code: int) -> List[int]:
        """获取12x24 ASCII字体数据"""
        return [0] * 24
    
    @staticmethod
    def get_ascii_3216_font(char_code: int) -> List[int]:
        """获取16x32 ASCII字体数据"""
        return [0] * 32
    
    @staticmethod
    def get_chinese_12x12_font(char_bytes: bytes) -> List[int]:
        """获取12x12中文字体数据"""
        return [0] * 24
    
    @staticmethod
    def get_chinese_16x16_font(char_bytes: bytes) -> List[int]:
        """获取16x16中文字体数据"""
        return [0] * 32
    
    @staticmethod
    def get_chinese_24x24_font(char_bytes: bytes) -> List[int]:
        """获取24x24中文字体数据"""
        return [0] * 72
    
    @staticmethod
    def get_chinese_32x32_font(char_bytes: bytes) -> List[int]:
        """获取32x32中文字体数据"""
        return [0] * 128


class FTD2XXSPIInterface:
    """基于FTD2XX.DLL的SPI接口实现（原ftdi_spi_interface.py完整内容）"""
    
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
        """初始化FTD2XX SPI接口"""
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
        """连接到FTDI设备"""
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
        """配置SPI参数"""
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
        """SPI写操作"""
        if not self.is_connected:
            raise Exception("设备未连接")
        
        if not data:
            return True
        
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
        
        if cpol == cpha: #模式0 or 模式3
            commands.extend([
                self.CMD_CLOCK_FALL_OUT_BYTES,
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
        
        # 发送命令
        self._write_data(commands)
        return True
    
    def spi_read(self, length: int) -> List[int]:
        """SPI读操作"""
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
            response = self._read_data(length)
            return list(response)
        except Exception as e:
            print(f"SPI读操作失败: {str(e)}")
            return []
    
    def spi_transfer(self, data: List[int]) -> List[int]:
        """SPI全双工传输"""
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
        """SPI写后读操作"""
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
        """设置GPIO引脚状态"""
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
        """设置GPIO引脚状态（高8位）"""
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
        """设置GPIO引脚方向"""
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
        """读取GPIO引脚状态"""
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
        """设置A0引脚状态"""
        return self.set_gpio_pin(self.PIN_A0, state)
    
    def set_reset(self, state: bool) -> bool:
        """设置RESET引脚状态"""
        return self.set_gpio_pin(self.PIN_RESET, state)
    
    def set_cs_main(self, state: bool) -> bool:
        """设置主CS引脚状态 (AD10)"""
        return self.set_gpio_pin(self.PIN_CS, state)
    
    def LCD_Reset(self) -> bool:
        """复位设备 (拉低RESET引脚)"""
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
        """发送LCD命令"""
        if not self.is_connected:
            raise Exception("设备未连接")
        self.set_a0(False)  # 设置A0为低（命令模式）
        self.gpio_high_output()  # 输出A0状态
        self.set_cs_main(False)  # 拉低CS选中设备
        self.gpio_high_output()  # 输出CS状态
        self.spi_write([command])
        self.set_cs_main(True)  # 拉高CS取消选中
        self.gpio_high_output()  # 输出CS状态
        return True
    
    def LCD_Data(self, data: int) -> bool:
        """发送LCD数据"""
        if not self.is_connected:
            raise Exception("设备未连接")
        self.set_a0(True)  # 设置A0为高（数据模式）
        self.gpio_high_output()  # 输出A0状态
        self.set_cs_main(False)  # 拉低CS选中设备
        self.gpio_high_output()  # 输出CS状态
        self.spi_write([data])
        self.set_cs_main(True)  # 拉高CS取消选中
        self.gpio_high_output()  # 输出CS状态
        return True
    
    def LCD_DataN(self, data_list: List[int]) -> bool:
        """发送LCD数据列表"""
        if not self.is_connected:
            raise Exception("设备未连接")
        self.set_a0(True)  # 设置A0为高（数据模式）
        self.gpio_high_output()  # 输出A0状态
        self.set_cs_main(False)  # 拉低CS选中设备
        self.gpio_high_output()  # 输出CS状态
        self.spi_write(data_list)
        self.set_cs_main(True)  # 拉高CS取消选中
        self.gpio_high_output()  # 输出CS状态
        return True
    
    def LCD_ReceiveData(self) -> int:
        """从LCD读取1字节数据"""
        if not self.is_connected:
            raise Exception("设备未连接")
        self.set_a0(True)
        self.gpio_high_output()  # 输出A0状态
        self.set_cs_main(True)
        self.gpio_high_output()  # 输出CS状态
        data = self.spi_read(1)
        self.set_cs_main(False)
        self.gpio_high_output()  # 输出CS状态
        return data[0] if data else 0
    
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
                        'type': device_type.value,
                        'device_id': device_id.value,
                        'serial_number': serial_number.value.decode('utf-8').strip('\x00'),
                        'description': description.value.decode('utf-8').strip('\x00'),
                        'interface': 'ctypes'
                    }
                else:
                    print(f"获取设备信息失败，状态码: {status}")
                    return {'error': f"获取设备信息失败，状态码: {status}"}
            
            else:
                # 使用ftd2xx库获取设备信息
                if hasattr(self.device_handle, 'getDeviceInfo'):
                    info = self.device_handle.getDeviceInfo()
                    return {
                        'type': info['type'],
                        'device_id': info.get('id', 0),
                        'serial_number': info.get('serial', ''),
                        'description': info.get('description', ''),
                        'interface': 'ftd2xx'
                    }
                else:
                    # 兼容旧版本ftd2xx库
                    try:
                        serial = self.device_handle.getSerialNumber()
                        desc = self.device_handle.getDescription()
                        return {
                            'serial_number': serial,
                            'description': desc,
                            'interface': 'ftd2xx'
                        }
                    except Exception as e:
                        print(f"获取设备信息失败: {str(e)}")
                        return {'error': str(e)}
                        
        except Exception as e:
            print(f"获取设备信息时出错: {str(e)}")
            return {'error': str(e)}


class PMDBLCD:
    """PMDB LCD显示屏控制类（原pmdb_lcd.py完整内容）"""
    
    def __init__(self, spi_interface: FTD2XXSPIInterface):
        """初始化LCD显示屏"""
        self.spi = spi_interface
        self.width = 128  # 默认宽度128像素
        self.height = 64  # 默认高度64像素
        self.fonts = LCDFonts()
        self.initialized = False
        
        # 初始化显示方向和镜像
        self.direction = 0  # 0: 正常, 1: 旋转90度, 2: 旋转180度, 3: 旋转270度
        self.mirror_x = False  # X轴镜像
        self.mirror_y = False  # Y轴镜像
        
        # 初始化显示缓冲区
        self.buffer_size = (self.width // 8) * self.height
        self.display_buffer = [0x00] * self.buffer_size
    
    def init(self) -> bool:
        """初始化LCD显示屏"""
        if not self.spi.is_connected:
            print("SPI接口未连接，无法初始化LCD")
            return False
        
        try:
            print("开始初始化LCD显示屏...")
            
            # 复位显示屏
            self.spi.LCD_Reset()
            time.sleep(0.1)  # 等待复位完成
            
            # 发送初始化命令序列（基于SSD1306/SSD1327控制器通用配置）
            init_commands = [
                0xAE,  # 关闭显示
                0xD5, 0x80,  # 设置显示时钟分频因子/振荡器频率
                0xA8, 0x3F,  # 设置多路复用率 (1/64)
                0xD3, 0x00,  # 设置显示偏移
                0x40,  # 设置显示起始行
                0x8D, 0x14,  # 启用电荷泵
                0x20, 0x00,  # 设置内存地址模式为水平寻址
                0xA1,  # 设置段重映射 (0xA0正常, 0xA1反转)
                0xC8,  # 设置COM输出扫描方向 (0xC0正常, 0xC8反转)
                0xDA, 0x12,  # 设置COM引脚硬件配置
                0x81, 0xCF,  # 设置对比度控制
                0xD9, 0xF1,  # 设置预充电周期
                0xDB, 0x40,  # 设置VCOMH取消选择级别
                0xA4,  # 全局显示开启 (恢复RAM内容显示)
                0xA6,  # 设置正常显示 (0xA6正常, 0xA7反显)
                0xAF   # 开启显示
            ]
            
            # 发送所有初始化命令
            for cmd in init_commands:
                self.spi.LCD_Command(cmd)
                time.sleep(0.001)
            
            self.clear()  # 清空显示
            self.initialized = True
            print("LCD显示屏初始化成功")
            return True
            
        except Exception as e:
            print(f"LCD初始化失败: {str(e)}")
            self.initialized = False
            return False
    
    def clear(self) -> bool:
        """清空显示缓冲区并刷新"""
        if not self.initialized:
            return False
            
        # 清空缓冲区
        self.display_buffer = [0x00] * self.buffer_size
        # 刷新显示
        return self.refresh()
    
    def refresh(self) -> bool:
        """将缓冲区内容刷新到显示屏"""
        if not self.initialized or not self.spi.is_connected:
            return False
        
        try:
            # 设置显示区域
            self.spi.LCD_Command(0x21)  # 设置列地址
            self.spi.LCD_Command(0x00)  # 起始列
            self.spi.LCD_Command(0x7F)  # 结束列
            
            self.spi.LCD_Command(0x22)  # 设置页地址
            self.spi.LCD_Command(0x00)  # 起始页
            self.spi.LCD_Command(0x07)  # 结束页 (64行/8=8页)
            
            # 发送整个缓冲区数据
            self.spi.LCD_DataN(self.display_buffer)
            return True
            
        except Exception as e:
            print(f"刷新显示失败: {str(e)}")
            return False
    
    def set_pixel(self, x: int, y: int, color: int = 1) -> bool:
        """设置指定位置像素点"""
        if not self.initialized:
            return False
            
        # 检查坐标是否在有效范围内
        if x < 0 or x >= self.width or y < 0 or y >= self.height:
            return False
            
        # 计算缓冲区索引和位位置
        page = y // 8
        page_byte = x + (page * self.width)
        bit_pos = y % 8
        
        if color:
            # 置位
            self.display_buffer[page_byte] |= (1 << bit_pos)
        else:
            # 清零
            self.display_buffer[page_byte] &= ~(1 << bit_pos)
            
        return True
    
    def draw_char(self, x: int, y: int, char: str, font_size: tuple = (6, 12)) -> int:
        """绘制单个ASCII字符"""
        if not self.initialized or len(char) != 1:
            return 0
            
        char_code = ord(char)
        font_width, font_height = font_size
        
        # 获取字符字体数据
        if font_size == (6, 12):
            font_data = self.fonts.get_ascii_1206_font(char_code)
        elif font_size == (8, 16):
            font_data = self.fonts.get_ascii_1608_font(char_code)
        elif font_size == (12, 24):
            font_data = self.fonts.get_ascii_2412_font(char_code)
        elif font_size == (16, 32):
            font_data = self.fonts.get_ascii_3216_font(char_code)
        else:
            print(f"不支持的字体大小: {font_size}")
            return 0
        
        # 绘制字符
        for row in range(font_height):
            row_data = font_data[row] if row < len(font_data) else 0
            for col in range(font_width):
                if (row_data >> (font_width - 1 - col)) & 0x01:
                    self.set_pixel(x + col, y + row, 1)
        
        return font_width  # 返回字符宽度
    
    def draw_string(self, x: int, y: int, text: str, font_size: tuple = (6, 12)) -> int:
        """绘制字符串"""
        if not self.initialized:
            return 0
            
        current_x = x
        font_width, font_height = font_size
        
        for char in text:
            # 绘制单个字符
            char_width = self.draw_char(current_x, y, char, font_size)
            current_x += char_width + 1  # 字符间距
            
            # 检查是否超出屏幕宽度
            if current_x >= self.width:
                break
                
        return current_x - x  # 返回总宽度
    
    def set_contrast(self, contrast: int) -> bool:
        """设置显示对比度 (0-255)"""
        if not self.initialized or contrast < 0 or contrast > 255:
            return False
            
        try:
            self.spi.LCD_Command(0x81)
            self.spi.LCD_Command(contrast)
            return True
        except Exception as e:
            print(f"设置对比度失败: {str(e)}")
            return False
    
    def set_display_on(self, on: bool = True) -> bool:
        """开启/关闭显示"""
        if not self.initialized:
            return False
            
        try:
            self.spi.LCD_Command(0xAF if on else 0xAE)
            return True
        except Exception as e:
            print(f"设置显示状态失败: {str(e)}")
            return False
    
    def invert_display(self, invert: bool = True) -> bool:
        """反显/正常显示切换"""
        if not self.initialized:
            return False
            
        try:
            self.spi.LCD_Command(0xA7 if invert else 0xA6)
            return True
        except Exception as e:
            print(f"设置反显状态失败: {str(e)}")
            return False


def main():
    """主函数：演示PMDB LCD显示屏控制"""
    print("PMDB LCD显示屏测试程序")
    print("----------------------")
    
    # 创建SPI接口
    spi = FTD2XXSPIInterface(device_index=0, use_ctypes=False)
    
    try:
        # 连接设备
        if not spi.connect():
            print("无法连接到FTDI设备，程序退出")
            return
            
        # 打印设备信息
        device_info = spi.get_device_info()
        print("\n设备信息:")
        for key, value in device_info.items():
            print(f"  {key}: {value}")
        
        # 创建LCD控制器
        lcd = PMDBLCD(spi)
        
        # 初始化LCD
        if not lcd.init():
            print("LCD初始化失败，程序退出")
            return
        
        # 显示测试内容
        print("\n显示测试内容...")
        lcd.draw_string(10, 10, "Hello, World!", (6, 12))
        lcd.draw_string(10, 30, "PMDB LCD Test", (6, 12))
        lcd.draw_string(10, 50, "1234567890", (6, 12))
        lcd.refresh()
        
        print("内容已显示，按任意键继续...")
        msvcrt.getch()  # 等待按键
        
        # 测试对比度调节
        print("调节对比度...")
        for contrast in [50, 100, 150, 200, 255, 200, 150, 100, 50]:
            lcd.set_contrast(contrast)
            time.sleep(0.2)
        
        print("按任意键反显屏幕...")
        msvcrt.getch()
        lcd.invert_display(True)
        time.sleep(2)
        
        print("按任意键恢复正常显示...")
        msvcrt.getch()
        lcd.invert_display(False)
        
        print("按任意键清除屏幕...")
        msvcrt.getch()
        lcd.clear()
        
        print("测试完成")
        
    except Exception as e:
        print(f"程序运行出错: {str(e)}")
        import traceback
        traceback.print_exc()
        
    finally:
        # 断开连接
        spi.disconnect()


if __name__ == "__main__":
    main()
