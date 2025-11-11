import time
from typing import List, Optional, Tuple

from ftdi_spi_interface import FTD2XXSPIInterface


class TFTLCD:
    """TFT LCD驱动类（适配FTDI SPI接口，修正参数错误）"""
    
    # 显示方向枚举
    LANDSCAPE_IC_UP = 0
    LANDSCAPE_IC_DOWN = 1
    PORTRAIT_IC_UP = 2
    PORTRAIT_IC_DOWN = 3
    
    # 颜色模式
    COLOR_MODE_RGB444 = 0
    COLOR_MODE_RGB565 = 1
    
    # 屏幕尺寸常量
    LCD_LAST_COLUMN = 319  # 320-1
    LCD_LAST_ROW = 239     # 240-1

    def __init__(self, spi_interface: FTD2XXSPIInterface):
        """初始化TFT LCD驱动"""
        self.spi = spi_interface
        
        # 初始化缓冲区及状态变量
        self.spi_buffer = [0] * 320  # 用于存储像素数据的缓冲区
        self.display_orientation = self.LANDSCAPE_IC_UP  # 默认显示方向
        self.host_width = 0          # 显示宽度
        self.host_height = 0         # 显示高度
        self.x1 = 0                  # 矩形起始X
        self.x2 = 0                  # 矩形结束X
        self.y1 = 0                  # 矩形起始Y
        self.y2 = 0                  # 矩形结束Y
        self.y = 1                   # 当前绘制行
        self.color = 0               # 当前绘制颜色
        self.vhost_step = 0          # 状态机步骤
        self.delay_counter = 0       # 延迟计数器

    def lcd_reset(self):
        """屏幕复位操作（使用SPI接口提供的复位方法）"""
        self.spi.LCD_Reset()
        time.sleep(0.1)  # 复位后稳定延迟

    def init(self):
        """初始化LCD（对应原C代码中的LCD_Init）"""
        self.lcd_reset()  # 执行复位
        
        # 设置初始显示方向（竖屏模式，LCD驱动在右侧）
        self.send_command(0x36)
        self.send_data(0xB4)
        
        # 初始化VHost相关参数
        self.init_vhost()
        return True  # 增加返回值，便于判断初始化成功

    def init_vhost(self):
        """初始化VHost控制参数"""
        self.y = 1
        self.y1 = 0
        self.y2 = 0
        self.vhost_step = 0
        self.display_orientation = self.LANDSCAPE_IC_UP
        
        # 配置显示方向命令
        self.send_command(0x36)
        self.send_data(0xA0)
        
        # 设置初始显示尺寸
        self.set_display_size(320, 240)

    def send_command(self, cmd: int):
        """发送命令到LCD控制器"""
        self.spi.LCD_Command(cmd)

    def send_data(self, data: int):
        """发送单字节数据到LCD控制器"""
        self.spi.LCD_Data(data)

    def send_data_n(self, data: List[int], num: int):
        """发送多字节数据到LCD控制器"""
        self.spi.LCD_DataN(data[:num])

    def set_display_size(self, width: int, height: int):
        """设置显示区域尺寸"""
        self.host_width = width
        self.host_height = height

    def vhost_task(self):
        """VHost主任务状态机"""
        self.vhost_rgb565()

    def vhost_rgb565(self):
        """RGB565模式下的显示逻辑"""
        if self.vhost_step == 0:
            # 步骤0：填充全屏背景（白色）
            if self.display_orientation in (self.LANDSCAPE_IC_DOWN, self.LANDSCAPE_IC_UP):
                self.set_display_size(320, 240)
                self.vhost_step += self.fill_rect(0, 0, 319, 239, 0xFFFF)
            else:
                self.set_display_size(240, 320)
                self.vhost_step += self.fill_rect(0, 0, 239, 319, 0xFFFF)

        elif self.vhost_step == 1:
            # 步骤1：填充内部黑色矩形
            if self.display_orientation in (self.LANDSCAPE_IC_DOWN, self.LANDSCAPE_IC_UP):
                self.set_display_size(320, 240)
                self.vhost_step += self.fill_rect(1, 1, 318, 238, 0)
            else:
                self.set_display_size(240, 320)
                self.vhost_step += self.fill_rect(1, 1, 238, 318, 0)

        elif self.vhost_step == 2:
            # 步骤2：填充红色矩形
            self.vhost_step += self.fill_rect(10, 10, 50, 50, 0xF800)

        elif self.vhost_step == 3:
            # 步骤3：填充绿色矩形
            self.vhost_step += self.fill_rect(11, 51, 80, 90, 0x07E0)

        elif self.vhost_step == 4:
            # 步骤4：填充蓝色矩形
            self.vhost_step += self.fill_rect(12, 91, 120, 130, 0x001F)

        elif self.vhost_step == 5:
            # 步骤5：填充白色矩形并重置延迟计数器
            self.vhost_step += self.fill_rect(13, 131, 160, 170, 0xFFFF)
            self.delay_counter = 0

        elif self.vhost_step == 6:
            # 步骤6：延迟后切换显示方向
            self.delay_counter += 1
            if self.delay_counter > 0xFF000:
                self.send_command(0x36)
                if self.display_orientation == self.LANDSCAPE_IC_UP:
                    self.send_data(0x20)
                    self.display_orientation = self.LANDSCAPE_IC_DOWN
                elif self.display_orientation == self.LANDSCAPE_IC_DOWN:
                    self.send_data(0xC0)
                    self.display_orientation = self.PORTRAIT_IC_UP
                elif self.display_orientation == self.PORTRAIT_IC_UP:
                    self.send_data(0x00)
                    self.display_orientation = self.PORTRAIT_IC_DOWN
                elif self.display_orientation == self.PORTRAIT_IC_DOWN:
                    self.send_data(0xA0)
                    self.display_orientation = self.LANDSCAPE_IC_UP
                self.delay_counter = 0
                self.vhost_step = 0

    def fill_rect(self, x1: int, y1: int, x2: int, y2: int, color: int) -> int:
        """填充矩形区域"""
        if self.y > self.y2:
            # 处理坐标反转和边界检查
            self.x1, self.x2 = (x2, x1) if x2 < x1 else (x1, x2)
            self.y1, self.y2 = (y2, y1) if y2 < y1 else (y1, y2)

            # 限制坐标在屏幕范围内
            self.y2 = min(self.y2, self.host_height - 1)
            self.x2 = min(self.x2, self.host_width - 1)
            self.x1 = min(self.x1, self.host_width - 1)
            self.y1 = min(self.y1, self.host_height - 1)

            # 设置列地址
            self.send_command(0x2A)
            self.send_data((self.x1 >> 8) & 0xFF)
            self.send_data(self.x1 & 0xFF)
            self.send_data((self.x2 >> 8) & 0xFF)
            self.send_data(self.x2 & 0xFF)

            # 设置行地址
            self.send_command(0x2B)
            self.send_data((self.y1 >> 8) & 0xFF)
            self.send_data(self.y1 & 0xFF)
            self.send_data((self.y2 >> 8) & 0xFF)
            self.send_data(self.y2 & 0xFF)

            # 准备写入像素数据
            self.send_command(0x2C)
            self.y = self.y1
            self.color = color
            return 0
        else:
            return self.vhost_task_rgb565()

    def vhost_task_rgb565(self) -> int:
        """处理RGB565格式的像素数据发送"""
        if self.y <= self.y2:
            pixel_count = self.x2 - self.x1 + 1
            for x in range(pixel_count):
                self.spi_buffer[x] = self.color
            
            # 转换为字节列表
            data_bytes = []
            for color in self.spi_buffer[:pixel_count]:
                data_bytes.append(color & 0xFF)
                data_bytes.append((color >> 8) & 0xFF)
            
            self.send_data_n(data_bytes, len(data_bytes))
            self.y += 1

        if self.y > self.y2:
            self.y = 0xFFF
            return 1
        else:
            return 0


def main():
    """TFT LCD驱动测试主函数"""
    print("TFT LCD驱动测试程序")
    print("=" * 50)
    
    # 创建SPI接口实例
    spi = FTD2XXSPIInterface(device_index=0, use_ctypes=True)
    
    try:
        # 连接SPI设备
        if not spi.connect():
            print("无法连接到SPI设备，请检查硬件连接")
            return
        
        # 修正：使用位置参数配置SPI（模式0，速率10MHz）
        # 参考最初代码中的调用方式：spi.configure_spi(0, 500000)
        spi.configure_spi(0, 10000000)  # 第一个参数：模式；第二个参数：速率（Hz）
        
        # 创建LCD驱动实例并初始化
        lcd = TFTLCD(spi)
        if not lcd.init():
            print("LCD初始化失败")
            return
        
        print("LCD初始化成功，开始显示测试...")
        print("按Ctrl+C退出程序")
        
        # 循环执行显示任务
        while True:
            lcd.vhost_task()
            time.sleep(0.001)
            
    except KeyboardInterrupt:
        print("\n用户中断程序")
    except Exception as e:
        print(f"程序运行出错: {str(e)}")
    finally:
        spi.disconnect()
        print("SPI设备已断开连接")


if __name__ == "__main__":
    main()
