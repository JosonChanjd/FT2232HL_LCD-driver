"""
FTDI FTD2XX SPI接口实现
基于FTD2XX.H头文件中的函数，使用FDT2xx.DLL实现SPI读写功能
支持所有四种SPI模式和完整的MPSSE命令集
"""

import os
import time
import struct
from typing import List, Optional, Tuple, Union
from ctypes import (
    windll, c_ulong, c_uint, c_ushort, c_ubyte, c_char, c_void_p, 
    c_char_p, c_int, c_long, POINTER, byref, create_string_buffer
)

# 设置FTD2XX DLL路径
os.environ['FTD2XX_DLL_DIR'] = r'C:\Users\sesa696240\Desktop\PMDB'

try:
    import ftd2xx
    FTDI_AVAILABLE = True
except ImportError:
    FTDI_AVAILABLE = False
    print("警告: 未安装ftd2xx库，将使用ctypes直接调用DLL")

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


def main():
    """主函数 - 演示SPI接口使用"""
    print("FTDI FTD2XX SPI接口演示")
    print("=" * 50)
    
    # 创建SPI接口实例
    spi = FTD2XXSPIInterface(device_index=0, use_ctypes=True)  # 使用ftd2xx库
    
    try:
        # 连接设备
        print("连接设备...")
        if not spi.connect():
            print("设备连接失败")
            return
        print("设备连接成功")
        
        # 显示设备信息
        info = spi.get_device_info()
        print(f"设备信息: {info}")
        
        # 配置SPI模式0，1MHz
        print("配置SPI模式0，1MHz...")
        spi.configure_spi(0, 1000000)
        
        
        # 测试设备复位
        print("\n测试设备复位...")
        spi.LCD_Reset()
        print("设备复位完成")
        
        # 测试数据
        test_data = [0x55, 0xAA, 0x33, 0xCC,0x01,0x02,0x03,0x04,0x05,0x06]
        
        
        #print(f"\n测试SPI写操作:")
        #print(f"发送数据: {[hex(x) for x in test_data]}")
        #spi.spi_write(test_data)
        #while(True):
            #print(f"\n测试SPI读操作:")
            #read_data = spi.spi_read(len(test_data))
            #print(f"读取数据: {[hex(x) for x in read_data]}")
            #time.sleep(0.01)
        for loop in range(4):
            
            print(f"\n测试SPI全双工传输:")
            transfer_data = spi.spi_transfer(test_data)
            print(f"发送: {[hex(x) for x in test_data]}")
            print(f"接收: {[hex(x) for x in transfer_data]}")
            
        print(f"\n测试SPI写后读:")
        write_read_data = spi.spi_read(len(test_data)) #spi.spi_write_read(test_data, len(test_data))
        #print(f"发送: {[hex(x) for x in test_data]}")
        print(f"接收: {[hex(x) for x in write_read_data]}")
        write_read_data = spi.spi_read(len(test_data)) #spi.spi_write_read(test_data, len(test_data))
        #print(f"发送: {[hex(x) for x in test_data]}")
        print(f"接收: {[hex(x) for x in write_read_data]}")
        write_read_data = spi.spi_read(len(test_data)) #spi.spi_write_read(test_data, len(test_data))
        #print(f"发送: {[hex(x) for x in test_data]}")
        print(f"接收: {[hex(x) for x in write_read_data]}")
        
        print(f"\n测试SPI全双工传输:")
        transfer_data = spi.spi_transfer(test_data)
        print(f"发送: {[hex(x) for x in test_data]}")
        print(f"接收: {[hex(x) for x in transfer_data]}")
        print(f"\n测试SPI全双工传输:")
        test_data=[0x11,0x23,0x34,0x56,0x78,0x9A,0xAB]
        transfer_data = spi.spi_transfer(test_data)
        print(f"发送: {[hex(x) for x in test_data]}")
        print(f"接收: {[hex(x) for x in transfer_data]}")
        
       
        
        print("\nSPI接口和GPIO测试完成！")
        
    except Exception as e:
        print(f"测试过程中出错: {str(e)}")
    
    finally:
        # 断开连接
        spi.disconnect()


if __name__ == "__main__":
    main()
