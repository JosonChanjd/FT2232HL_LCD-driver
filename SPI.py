import ctypes
from ctypes import c_uint8, c_uint16, c_uint32, POINTER, Structure, WinDLL, byref

# -------------------------- 1. 映射文档定义的数据类型与结构体（🔶1-186至🔶1-219） --------------------------
# 文档3.4.2节Typedef定义（确保与库API类型匹配）
uint8 = c_uint8
uint16 = c_uint16
uint32 = c_uint32
FT_STATUS = c_uint32  # 所有SPI API返回值类型（🔶1-42）
FT_HANDLE = POINTER(c_uint8)  # 设备通道句柄（🔶1-73）

# 文档3.4.1节：ChannelConfig结构体（SPI通道配置参数，含时钟频率）
class ChannelConfig(Structure):
    _fields_ = [
        ("ClockRate", uint32),       # SPI时钟频率（Hz，0-30MHz，🔶1-189至🔶1-190）
        ("LatencyTimer", uint8),     # 延迟定时器（ms，高速设备1-255，🔶1-191至🔶1-196）
        ("configOptions", uint32),   # SPI模式、片选线配置（🔶1-197至🔶1-203）
        ("Pins", uint32),            # 引脚方向与电平（🔶1-210至🔶1-217）
        ("reserved", uint16)         # 保留字段（🔶1-218至🔶1-219）
    ]

# 文档3.1.2节：FT_DEVICE_LIST_INFO_NODE结构体（获取通道信息用）
class FT_DEVICE_LIST_INFO_NODE(Structure):
    _fields_ = [
        ("Flags", uint32),
        ("Type", uint32),
        ("ID", uint32),
        ("LocId", uint32),
        ("SerialNumber", ctypes.c_char * 16),  # 设备串口号（🔶1-58）
        ("Description", ctypes.c_char * 64),   # 设备描述（如FT2232H MiniModule，🔶1-58）
        ("ftHandle", FT_HANDLE)                 # 未打开时为0（🔶1-58）
    ]

# -------------------------- 2. 加载LibMPSSE-SPI库（Windows版，按用户路径配置） --------------------------
try:
    # 加载用户指定路径的库文件（注意：文档标准文件名为libMPSSE_spi.dll，若加载失败需核对文件名，🔶1-26至🔶1-29）
    lib = WinDLL("C:\\Users\\sesa696240\\Desktop\\2232\\libmpsse.dll")
except OSError as e:
    raise Exception(f"库加载失败：请确认路径正确，且文件为文档指定的LibMPSSE-SPI库（🔶1-26至🔶1-29），错误：{str(e)}")

# -------------------------- 3. 绑定文档定义的SPI发送相关API函数（🔶1-41至🔶1-145） --------------------------
# 3.3.1节：Init_libMPSSE（库初始化，前置操作，🔶1-172至🔶1-178）
lib.Init_libMPSSE.argtypes = []
lib.Init_libMPSSE.restype = None

# 3.3.2节：Cleanup_libMPSSE（库资源清理，后置操作，🔶1-179至🔶1-185）
lib.Cleanup_libMPSSE.argtypes = []
lib.Cleanup_libMPSSE.restype = None

# 3.1.1节：SPI_GetNumChannels（获取可用通道数，🔶1-44至🔶1-55）
lib.SPI_GetNumChannels.argtypes = [POINTER(uint32)]
lib.SPI_GetNumChannels.restype = FT_STATUS

# 3.1.2节：SPI_GetChannelInfo（获取通道信息，🔶1-56至🔶1-71）
lib.SPI_GetChannelInfo.argtypes = [uint32, POINTER(FT_DEVICE_LIST_INFO_NODE)]
lib.SPI_GetChannelInfo.restype = FT_STATUS

# 3.1.3节：SPI_OpenChannel（打开通道，🔶1-72至🔶1-81）
lib.SPI_OpenChannel.argtypes = [uint32, POINTER(FT_HANDLE)]
lib.SPI_OpenChannel.restype = FT_STATUS

# 3.1.4节：SPI_InitChannel（初始化通道，含时钟频率配置，🔶1-81至🔶1-95）
lib.SPI_InitChannel.argtypes = [FT_HANDLE, POINTER(ChannelConfig)]
lib.SPI_InitChannel.restype = FT_STATUS

# 3.1.5节：SPI_CloseChannel（关闭通道，🔶1-95至🔶1-101）
lib.SPI_CloseChannel.argtypes = [FT_HANDLE]
lib.SPI_CloseChannel.restype = FT_STATUS

# 3.1.7节：SPI_Write（SPI数据发送核心函数，阻塞式，🔶1-115至🔶1-130）
lib.SPI_Write.argtypes = [FT_HANDLE, POINTER(uint8), uint32, POINTER(uint32), uint32]
lib.SPI_Write.restype = FT_STATUS

# -------------------------- 4. 仅发送数据的SPI功能实现（参考文档4节写入逻辑，🔶1-232至🔶1-253） --------------------------
def spi_only_send_example(send_data, target_clock_hz=5000):
    """
    SPI仅发送数据函数
    参数：
        send_data: 待发送数据（列表，如[0xA0, 0x00, 0x01]）
        target_clock_hz: 设计的SPI时钟频率（Hz，默认5000Hz，需在0-30MHz范围内，🔶1-190）
    """
    ft_handle = FT_HANDLE()  # 通道句柄
    channel_count = uint32(0)  # 可用通道数

    try:
        # 步骤1：初始化LibMPSSE库（文档要求的前置操作，🔶1-168）
        lib.Init_libMPSSE()
        print("✅ LibMPSSE库初始化完成")

        # 步骤2：获取可用SPI通道数（确认设备连接，🔶1-44）
        status = lib.SPI_GetNumChannels(byref(channel_count))
        if status != 0:
            raise Exception(f"SPI_GetNumChannels失败，状态码：0x{status:x}（参考文档D2XX状态码说明）")
        if channel_count.value == 0:
            raise Exception("❌ 无可用SPI通道（需确认FTDI设备已连接且D2XX驱动已安装，🔶1-18、🔶1-237）")
        print(f"✅ 可用SPI通道数：{channel_count.value}")

        # 步骤3：获取第0号通道信息（确认设备型号，🔶1-56）
        dev_info = FT_DEVICE_LIST_INFO_NODE()
        status = lib.SPI_GetChannelInfo(0, byref(dev_info))
        if status != 0:
            raise Exception(f"SPI_GetChannelInfo失败，状态码：0x{status:x}")
        print(f"\n📌 通道0设备信息：")
        print(f"  设备描述：{dev_info.Description.decode('ascii')}")
        print(f"  串口号：{dev_info.SerialNumber.decode('ascii')}")

        # 步骤4：打开第0号通道（🔶1-72）
        status = lib.SPI_OpenChannel(0, byref(ft_handle))
        if status != 0:
            raise Exception(f"❌ SPI_OpenChannel失败，状态码：0x{status:x}（通道可能被其他程序占用，🔶1-80）")
        print(f"✅ 通道0打开成功，句柄：0x{ctypes.addressof(ft_handle.contents):x}")

        # 步骤5：配置SPI通道（核心：设置目标时钟频率，🔶1-81至🔶1-95）
        spi_config = ChannelConfig()
        spi_config.ClockRate = target_clock_hz  # 配置为目标时钟频率（设计值）
        spi_config.LatencyTimer = 255          # 延迟定时器（高速设备推荐值，🔶1-196）
        # configOptions：MODE0（0x00）+ 片选DBUS3（0x00）+ 片选低电平有效（0x20），符合文档示例（🔶1-203）
        spi_config.configOptions = 0x00 | 0x00 | 0x20
        spi_config.Pins = 0x00000000           # 引脚默认配置（文档4节示例，🔶1-242）
        spi_config.reserved = 0                # 保留字段置0（🔶1-219）

        # 初始化通道（将时钟频率等配置写入硬件）
        status = lib.SPI_InitChannel(ft_handle, byref(spi_config))
        if status != 0:
            raise Exception(f"❌ SPI_InitChannel失败，状态码：0x{status:x}")
        # 打印时钟频率配置信息（用于确认设计值）
        print(f"\n✅ SPI通道配置完成：")
        print(f"  设计时钟频率：{spi_config.ClockRate} Hz（{spi_config.ClockRate/1000:.1f} kHz）")
        print(f"  SPI模式：MODE0 | 片选：DBUS3（低电平有效）")

        # 步骤6：SPI数据发送（核心功能，参考文档4节EEPROM写入逻辑，🔶1-242至🔶1-249）
        if not send_data:
            raise Exception("❌ 待发送数据为空，请传入非空列表")
        
        # 转换发送数据为库要求的uint8数组
        send_len = len(send_data)
        send_buf = (uint8 * send_len)(*send_data)
        size_sent = uint32(0)  # 实际发送字节数（输出参数）
        
        # 传输选项：字节传输（0x00）+ 传输前片选使能（0x02）+ 传输后片选释放（0x04）（🔶1-106、🔶1-119）
        transfer_opt = 0x00 | 0x02 | 0x04

        # 调用SPI_Write发送数据（阻塞函数，直至发送完成或出错，🔶1-122）
        status = lib.SPI_Write(
            ft_handle, 
            send_buf, 
            send_len, 
            byref(size_sent), 
            transfer_opt
        )
        if status != 0:
            raise Exception(f"❌ SPI_Write失败，状态码：0x{status:x}")
        
        # 打印发送结果
        print(f"\n✅ SPI数据发送完成：")
        print(f"  待发送数据（十六进制）：{[f'0x{byte:02x}' for byte in send_data]}")
        print(f"  待发送字节数：{send_len}")
        print(f"  实际发送字节数：{size_sent.value}")
        if size_sent.value == send_len:
            print("  ✅ 发送字节数匹配，数据发送正常")

    except Exception as e:
        print(f"\n❌ 程序异常：{str(e)}")
    finally:
        # 步骤7：释放资源（文档要求的后置操作，避免资源泄漏，🔶1-95、🔶1-179）
        if ft_handle:
            lib.SPI_CloseChannel(ft_handle)
            print("\n✅ SPI通道已关闭")
        lib.Cleanup_libMPSSE()
        print("✅ LibMPSSE库资源已清理")

# -------------------------- 5. 程序入口（定义待发送数据并运行） --------------------------
if __name__ == "__main__":
    # 1. 定义待发送的SPI数据（可根据需求修改，示例为文档4节EEPROM写命令+地址+数据）
    # 格式：[命令字节, 地址字节, 数据字节1, 数据字节2, ...]
    spi_send_data = [0xA0, 0x00, 0x12, 0x34]  # 示例：0xA0=写命令，0x00=地址，0x1234=数据
    
    # 2. 定义设计的SPI时钟频率（单位：Hz，需在0-30MHz范围内，🔶1-190）
    design_clock_hz = 1000000  # 设计为5000Hz（5kHz），可修改为目标频率（如1000000=1MHz）
    
    # 3. 运行SPI仅发送功能
    spi_only_send_example(send_data=spi_send_data, target_clock_hz=design_clock_hz)
