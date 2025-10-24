import ctypes
import time
from ctypes import c_uint8, c_uint16, c_uint32, POINTER, Structure, WinDLL, byref

# -------------------------- 1. 数据类型定义（严格遵循AN_178 3.4节） --------------------------
uint8 = c_uint8
uint16 = c_uint16
uint32 = c_uint32
FT_STATUS = c_uint32
FT_HANDLE = ctypes.c_void_p  # AN_178定义的FT_HANDLE为void*

# AN_178 3.4.1节：ChannelConfig结构体（SPI通道配置核心）
class ChannelConfig(Structure):
    _fields_ = [
        ("ClockRate", uint32),    # SPI时钟频率（Hz）
        ("LatencyTimer", uint8),  # 延迟定时器（ms，Hi-speed设备1-255，AN_178 3.4.1）
        ("configOptions", uint32),# SPI模式+CS配置（AN_178 3.4.1 bit0-5）
        ("Pins", uint32),         # ADBUS引脚方向+电平（关键：配置DC/RST为输出）
        ("reserved", uint16)      # 保留字段，必须设为0
    ]

# AN_178 3.1.2节：FT_DEVICE_LIST_INFO_NODE（通道信息结构体）
class FT_DEVICE_LIST_INFO_NODE(Structure):
    _fields_ = [
        ("Flags", uint32),
        ("Type", uint32),
        ("ID", uint32),
        ("LocId", uint32),
        ("SerialNumber", ctypes.c_char * 16),
        ("Description", ctypes.c_char * 64),
        ("ftHandle", FT_HANDLE)
    ]

# -------------------------- 2. 引脚配置（AN_178 3.4.1 + UC1638c手册6.1节） --------------------------
# 硬件连接：SCLK→ADBUS0, MOSI→ADBUS1, CS→ADBUS3, DC→ADBUS4, RST→ADBUS5
DC_PIN_MASK = 0x10  # ADBUS4（UC1638c CD引脚，命令=低/数据=高）
RST_PIN_MASK = 0x20 # ADBUS5（UC1638c RST引脚，复位=低）
CS_ACTIVE_LOW = 0x20# AN_178 3.4.1：bit5=1，CS低有效
SPI_MODE0 = 0x00    # AN_178 3.4.1：SPI MODE0（CPOL=0, CPHA=0）

# AN_178 3.4.1节：Pins字段32位配置（ADBUS引脚初始化/关闭时的方向+电平）
# bit0~7（初始化后方向）：DC(0x10)、RST(0x20)设为输出（1）
INIT_DIR = DC_PIN_MASK | RST_PIN_MASK  # 0x30
# bit8~15（初始化后电平）：RST初始高（0x20），DC初始低（0x00）
INIT_VAL = RST_PIN_MASK
# bit16~23（关闭后方向）、bit24~31（关闭后电平）：同初始化
CLOSE_DIR = INIT_DIR
CLOSE_VAL = INIT_VAL
# 最终Pins配置（AN_178要求的32位格式）
TOTAL_PIN_CONFIG = INIT_DIR | (INIT_VAL << 8) | (CLOSE_DIR << 16) | (CLOSE_VAL << 24)

# AN_178 3.1.7节：SPI_Write的transferOptions（CS自动控制）
# bit1=CS使能（拉低），bit2=CS禁用（拉高），确保传输前后CS电平正确
SPI_CS_OPTIONS = 0x06

# -------------------------- 3. 绑定libMPSSE标准API（仅AN_178 3节列出的函数） --------------------------
try:
    lib = WinDLL("C:\\Users\\sesa696240\\Desktop\\2232\\libmpsse.dll")
except OSError as e:
    raise Exception(f"libmpsse.dll加载失败: {str(e)}（AN_178 4节：检查路径）")

# AN_178 3.3节：库初始化/清理
lib.Init_libMPSSE.argtypes = []
lib.Init_libMPSSE.restype = None
lib.Cleanup_libMPSSE.argtypes = []
lib.Cleanup_libMPSSE.restype = None

# AN_178 3.1节：SPI核心函数
lib.SPI_GetNumChannels.argtypes = [POINTER(uint32)]
lib.SPI_GetNumChannels.restype = FT_STATUS
lib.SPI_GetChannelInfo.argtypes = [uint32, POINTER(FT_DEVICE_LIST_INFO_NODE)]
lib.SPI_GetChannelInfo.restype = FT_STATUS
lib.SPI_OpenChannel.argtypes = [uint32, POINTER(FT_HANDLE)]
lib.SPI_OpenChannel.restype = FT_STATUS
lib.SPI_InitChannel.argtypes = [FT_HANDLE, POINTER(ChannelConfig)]
lib.SPI_InitChannel.restype = FT_STATUS
lib.SPI_CloseChannel.argtypes = [FT_HANDLE]
lib.SPI_CloseChannel.restype = FT_STATUS
lib.SPI_Write.argtypes = [FT_HANDLE, POINTER(uint8), uint32, POINTER(uint32), uint32]
lib.SPI_Write.restype = FT_STATUS

# AN_178 3.2节：GPIO函数（仅FT_WriteGPIO，无FT_SetBitMode）
lib.FT_WriteGPIO.argtypes = [FT_HANDLE, uint8, uint8]  # AN_178 3.2.1：uint8参数
lib.FT_WriteGPIO.restype = FT_STATUS

# AN_178 3.1.9节：显式配置CS（解决版本兼容问题）
lib.SPI_ChangeCS.argtypes = [FT_HANDLE, uint32]
lib.SPI_ChangeCS.restype = FT_STATUS

# -------------------------- 4. 基础控制函数（AN_178+UC1638c手册规范） --------------------------
def set_rst(handle, level):
    """UC1638c手册44节：RST复位时序（拉低≥5ms，拉高≥150ms）"""
    # AN_178 3.2.1：FT_WriteGPIO(handle, 方向, 电平)
    # 方向：DC/RST设为输出（0x30）；电平：RST=level时置1
    status = lib.FT_WriteGPIO(handle, 0x30, RST_PIN_MASK if level else 0x00)
    if status != 0:
        raise Exception(f"RST设置失败（level={level}），状态码0x{status:x}（AN_178 3.2.1）")
    # 满足UC1638c复位时序
    if level == 0:
        time.sleep(0.01)  # 拉低10ms（≥5ms）
    else:
        time.sleep(0.2)   # 拉高200ms（≥150ms）

def set_dc(handle, level):
    """UC1638c手册6.1节：DC引脚控制（0=命令，1=数据）"""
    # 方向：DC/RST设为输出（0x30）；电平：DC=level时置1
    status = lib.FT_WriteGPIO(handle, 0x30, DC_PIN_MASK if level else 0x00)
    if status != 0:
        raise Exception(f"DC设置失败（level={level}），状态码0x{status:x}（AN_178 3.2.1）")

def init_cs(handle):
    """AN_178 3.1.9节：显式配置CS为ADBUS3（低有效，MODE0）"""
    cs_config = SPI_MODE0 | CS_ACTIVE_LOW  # bit0-1=MODE0，bit5=CS低有效
    status = lib.SPI_ChangeCS(handle, cs_config)
    if status != 0:
        raise Exception(f"CS配置失败，状态码0x{status:x}（AN_178 3.1.9）")

# -------------------------- 5. LCD控制函数（UC1638c手册13-25节命令） --------------------------
def lcd_send_command(handle, cmd):
    """UC1638c手册13节：发送命令（DC=低，CS自动控制）"""
    set_dc(handle, 0)  # 命令模式
    send_buf = (uint8 * 1)(cmd)
    size_sent = uint32(0)
    # AN_178 3.1.7：SPI_Write带CS自动拉低/拉高（SPI_CS_OPTIONS=0x06）
    status = lib.SPI_Write(handle, send_buf, 1, byref(size_sent), SPI_CS_OPTIONS)
    if status != 0 or size_sent.value != 1:
        raise Exception(f"命令0x{cmd:02x}发送失败，已发{size_sent.value}/1字节")

def lcd_send_data(handle, data):
    """UC1638c手册13节：发送数据（DC=高，CS自动控制）"""
    set_dc(handle, 1)  # 数据模式
    send_buf = (uint8 * 1)(data)
    size_sent = uint32(0)
    status = lib.SPI_Write(handle, send_buf, 1, byref(size_sent), SPI_CS_OPTIONS)
    if status != 0 or size_sent.value != 1:
        raise Exception(f"数据0x{data:02x}发送失败，已发{size_sent.value}/1字节")

def lcd_init(handle):
    """UC1638c手册13-25节：LCD初始化流程"""
    pm = 0x30  # VLCD电压配置（UC1638c手册26节）
    
    # 1. 硬件复位（UC1638c手册44节）
    set_rst(handle, 1)
    time.sleep(0.1)
    set_rst(handle, 0)  # 拉低复位
    set_rst(handle, 1)  # 拉高恢复
    
    # 2. 按UC1638c手册命令初始化
    lcd_send_command(handle, 0xE1)  # 系统复位（双字节）
    lcd_send_data(handle, 0xE2)
    time.sleep(0.002)
    lcd_send_command(handle, 0xA4)  # 仅激活窗口像素
    lcd_send_command(handle, 0xA6)  # 正常显示
    lcd_send_command(handle, 0xB8)  # MTP控制（0x00）
    lcd_send_data(handle, 0x00)
    lcd_send_command(handle, 0x2D)  # 内部VLCD泵使能
    lcd_send_command(handle, 0x26)  # 温度补偿（-0.05%/℃）
    lcd_send_command(handle, 0xEA)  # 设置偏置比
    lcd_send_command(handle, 0x81)  # 设置VLCD（PM值）
    lcd_send_data(handle, pm)
    lcd_send_command(handle, 0xA3)  # 行速率15.6KLPS
    lcd_send_command(handle, 0xC8)  # 关闭N-LINE反转
    lcd_send_data(handle, 0x00)
    lcd_send_command(handle, 0x89)  # RAM地址自动+1
    lcd_send_command(handle, 0x95)  # 1Bit/像素
    lcd_send_command(handle, 0x84)  # 从COM1扫描
    lcd_send_command(handle, 0xF1)  # COM结束=127
    lcd_send_data(handle, 127)
    lcd_send_command(handle, 0xC0 | (1 << 2) | (0 << 1))  # MY=1（行镜像）
    lcd_send_command(handle, 0x86)  # 隔行扫描
    lcd_send_command(handle, 0x40)  # 无滚动
    lcd_send_command(handle, 0x50)  # 滚动偏移0
    lcd_send_command(handle, 0x04)  # 列起始=55
    lcd_send_data(handle, 55)
    lcd_send_command(handle, 0xF4)  # 窗口起始列=55
    lcd_send_data(handle, 55)
    lcd_send_command(handle, 0xF6)  # 窗口结束列=182
    lcd_send_data(handle, 182)
    lcd_send_command(handle, 0xF5)  # 窗口起始页=0
    lcd_send_data(handle, 0)
    lcd_send_command(handle, 0xF7)  # 窗口结束页=15
    lcd_send_data(handle, 15)
    lcd_send_command(handle, 0xF9)  # 保留命令
    lcd_send_command(handle, 0xC9)  # 显示模式
    lcd_send_data(handle, 0xAD)
    lcd_send_command(handle, 0xAF)  # 开启显示（关键）
    time.sleep(0.1)
    print("LCD初始化完成（UC1638c手册命令规范）")

# -------------------------- 6. 显示填充函数（UC1638c手册40节DDRAM） --------------------------
def lcd_fill_black_upper_white_lower(handle):
    """上半区（0-7页）黑，下半区（8-15页）白"""
    # 上半区黑色
    lcd_send_command(handle, 0x60 | 0)  # 页LSB=0
    lcd_send_command(handle, 0x70)      # 页MSB=0
    lcd_send_command(handle, 0x00)      # 写数据模式
    black_buf = (uint8 * 1024)(0x00)
    remaining = 128 * 8
    while remaining > 0:
        send_len = min(1024, remaining)
        size_sent = uint32(0)
        status = lib.SPI_Write(handle, black_buf, send_len, byref(size_sent), SPI_CS_OPTIONS)
        if status != 0 or size_sent.value != send_len:
            raise Exception(f"上半区黑填充失败，已发{size_sent.value}/{send_len}字节")
        remaining -= send_len
    print("上半区（0-7页）黑色填充完成")

    # 下半区白色
    lcd_send_command(handle, 0x60 | 8)  # 页LSB=8
    lcd_send_command(handle, 0x70)      # 页MSB=0
    lcd_send_command(handle, 0x00)      # 写数据模式
    white_buf = (uint8 * 1024)(0xFF)
    remaining = 128 * 8
    while remaining > 0:
        send_len = min(1024, remaining)
        size_sent = uint32(0)
        status = lib.SPI_Write(handle, white_buf, send_len, byref(size_sent), SPI_CS_OPTIONS)
        if status != 0 or size_sent.value != send_len:
            raise Exception(f"下半区白填充失败，已发{size_sent.value}/{send_len}字节")
        remaining -= send_len
    print("下半区（8-15页）白色填充完成")

def lcd_fill_white_upper_black_lower(handle):
    """上半区（0-7页）白，下半区（8-15页）黑"""
    # 上半区白色
    lcd_send_command(handle, 0x60 | 0)
    lcd_send_command(handle, 0x70)
    lcd_send_command(handle, 0x00)
    white_buf = (uint8 * 1024)(0xFF)
    remaining = 128 * 8
    while remaining > 0:
        send_len = min(1024, remaining)
        size_sent = uint32(0)
        status = lib.SPI_Write(handle, white_buf, send_len, byref(size_sent), SPI_CS_OPTIONS)
        if status != 0 or size_sent.value != send_len:
            raise Exception(f"上半区白填充失败，已发{size_sent.value}/{send_len}字节")
        remaining -= send_len
    print("上半区（0-7页）白色填充完成")

    # 下半区黑色
    lcd_send_command(handle, 0x60 | 8)
    lcd_send_command(handle, 0x70)
    lcd_send_command(handle, 0x00)
    black_buf = (uint8 * 1024)(0x00)
    remaining = 128 * 8
    while remaining > 0:
        send_len = min(1024, remaining)
        size_sent = uint32(0)
        status = lib.SPI_Write(handle, black_buf, send_len, byref(size_sent), SPI_CS_OPTIONS)
        if status != 0 or size_sent.value != send_len:
            raise Exception(f"下半区黑填充失败，已发{size_sent.value}/{send_len}字节")
        remaining -= send_len
    print("下半区（8-15页）黑色填充完成")

# -------------------------- 7. 主函数（AN_178 4节Usage Example流程） --------------------------
def spi_lcd_control(target_clock_hz=1000000):
    ft_handle = FT_HANDLE()
    channel_count = uint32(0)

    try:
        # 1. 初始化库（AN_178 3.3.1）
        lib.Init_libMPSSE()
        print("libMPSSE库初始化完成")

        # 2. 检查SPI通道（AN_178 3.1.1）
        status = lib.SPI_GetNumChannels(byref(channel_count))
        if status != 0:
            raise Exception(f"SPI_GetNumChannels失败，状态码0x{status:x}")
        if channel_count.value == 0:
            raise Exception("无可用SPI通道（检查FTDI设备+D2XX驱动，AN_178 4节）")
        print(f"发现{channel_count.value}个SPI通道")

        # 3. 打开并配置SPI通道（AN_178 3.1.3+3.1.4）
        status = lib.SPI_OpenChannel(0, byref(ft_handle))
        if status != 0:
            raise Exception(f"打开通道0失败，状态码0x{status:x}")
        print(f"通道0打开成功，句柄：0x{ft_handle.value:x}")

        # AN_178 3.1.4：配置SPI参数（含ADBUS引脚方向）
        spi_config = ChannelConfig()
        spi_config.ClockRate = target_clock_hz  # 1MHz（稳定优先）
        spi_config.LatencyTimer = 1            # Hi-speed设备推荐值
        spi_config.configOptions = SPI_MODE0 | CS_ACTIVE_LOW  # MODE0+CS低有效
        spi_config.Pins = TOTAL_PIN_CONFIG     # 关键：ADBUS4/5设为输出
        spi_config.reserved = 0

        status = lib.SPI_InitChannel(ft_handle, byref(spi_config))
        if status != 0:
            raise Exception(f"SPI_InitChannel失败，状态码0x{status:x}（AN_178 3.1.4）")
        print("SPI通道初始化完成（ADBUS4/5已设为输出）")

        # 4. 初始化CS+LCD
        init_cs(ft_handle)
        print("CS引脚（ADBUS3）配置完成（低有效）")
        lcd_init(ft_handle)

        # 5. 循环切换显示
        print("\n循环切换黑白色块（按Ctrl+C退出）...")
        is_upper_black = True
        while True:
            if is_upper_black:
                print("\n=== 上黑下白 ===")
                lcd_fill_black_upper_white_lower(ft_handle)
            else:
                print("\n=== 上白下黑 ===")
                lcd_fill_white_upper_black_lower(ft_handle)
            is_upper_black = not is_upper_black
            time.sleep(2)

    except Exception as e:
        print(f"\n错误: {str(e)}")
    finally:
        # 6. 释放资源（AN_178 3.1.5+3.3.2）
        if ft_handle.value:
            lib.SPI_CloseChannel(ft_handle)
            print("\nSPI通道已关闭")
        lib.Cleanup_libMPSSE()
        print("libMPSSE库已清理")

if __name__ == "__main__":
    spi_lcd_control(target_clock_hz=1000000)  # 1MHz SPI时钟（UC1638c稳定支持）
