"""
ST7789 LCD Driver (MPSSE/SPI Mode 0)
------------------------------------------------------
Frequency : 10 MHz (Divisor = 2)
Logic Res : 320 x 240 (Landscape)
Color     : GREEN (0x07E0)
------------------------------------------------------
"""
import time
import os
from ctypes import *

# 确保 DLL 路径正确
try:
    os.environ['FTD2XX_DLL_DIR'] = r'C:\Users\sesa696240\Desktop\PMDB'
except:
    pass

class FTDI_PDF_Driver:
    PIN_A0  = 0x01 # AC0
    PIN_RST = 0x02 # AC1
    PIN_CS  = 0x04 # AC2
    
    def __init__(self):
        try:
            self.dll = windll.LoadLibrary("FTD2XX.DLL")
        except:
            raise Exception("无法加载 FTD2XX.DLL")
        
        self.handle = c_void_p()
        if self.dll.FT_Open(0, byref(self.handle)) != 0:
            raise Exception("无法打开 FTDI 设备")
        
        self.dll.FT_SetUSBParameters(self.handle, 65536, 65536)
        self.dll.FT_SetLatencyTimer(self.handle, 2)
        
        self.dll.FT_SetBitMode(self.handle, 0, 0x00)
        time.sleep(0.05)
        self.dll.FT_SetBitMode(self.handle, 0, 0x02) # MPSSE
        time.sleep(0.05)
        self.dll.FT_Purge(self.handle, 3)
        
        self._setup_mpsse()

    def _setup_mpsse(self):
        # 10 MHz, Mode 0
        cmds = [
            0x8A, 0x97, 0x8D,
            0x86, 0x02, 0x00,     # Div=2 -> 10MHz
            0x85,
            0x80, 0x00, 0xFB,     # SCLK Low Idle (Mode 0)
            0x82, 0x07, 0x07
        ]
        self._write_raw(cmds)

    def _write_raw(self, data):
        b_data = bytes(data)
        written = c_ulong()
        self.dll.FT_Write(self.handle, b_data, len(b_data), byref(written))

    def drive_reset_procedure(self):
        print("-> Hardware Reset...")
        self._write_raw([0x82, 0x05, 0x07]) # RST=0
        time.sleep(0.05) 
        self._write_raw([0x82, 0x07, 0x07]) # RST=1
        time.sleep(0.12)

    def write_cmd_a0(self, cmd):
        # Mode 0 Write: 0x11 (Bytes, MSB, Falling edge setup)
        self._write_raw([0x82, 0x02, 0x07, 
                         0x11, 0x00, 0x00, cmd,
                         0x82, 0x07, 0x07])

    def write_data_a1(self, data):
        if isinstance(data, int):
            data = [data]
        cmds = [0x82, 0x03, 0x07]
        limit = 65530
        for i in range(0, len(data), limit):
            chunk = data[i:i+limit]
            l = len(chunk) - 1
            cmds += [0x11, l & 0xFF, (l >> 8) & 0xFF]
            cmds += chunk
        cmds += [0x82, 0x07, 0x07]
        self._write_raw(cmds)
        
    def close(self):
        self.dll.FT_Close(self.handle)

def main():
    spi = FTDI_PDF_Driver()
    
    try:
        # 1. 硬件复位
        spi.drive_reset_procedure()
        
        # 2. 基础配置
        print("-> 0x11: Sleep Out")
        spi.write_cmd_a0(0x11)
        time.sleep(0.12)
        
        print("-> 0x3A: Pixel Format RGB565 (16-bit)")
        spi.write_cmd_a0(0x3A)
        spi.write_data_a1(0x05)

        # 3. 设置横屏
        # 0x2A = MV=1
        print("-> 0x36: MADCTL = 0x2A")
        spi.write_cmd_a0(0x36)
        spi.write_data_a1(0x2A)

        # 4. 列地址 (逻辑宽 320)
        print("-> 0x2A: Column 0~319")
        spi.write_cmd_a0(0x2A)
        spi.write_data_a1([0x00, 0x00, 0x01, 0x3F])

        # 5. 行地址 (逻辑高 240)
        print("-> 0x2B: Row 0~239")
        spi.write_cmd_a0(0x2B)
        spi.write_data_a1([0x00, 0x00, 0x00, 0xEF])
        
        print("-> 0x29: Display On")
        spi.write_cmd_a0(0x29)

        # 6. 写显存 - 绿色
        print("-> 0x2C: RAM Write (Filling GREEN 0x07E0)...")
        spi.write_cmd_a0(0x2C)
        
        width_logic = 320
        height_logic = 240
        
        # ---------------- 修改处：颜色改为绿色 ----------------
        # RGB565 绿色 = 0x07E0
        # High Byte = 0x07, Low Byte = 0xE0
        pixel_green = [0x07, 0xE0]
        
        # 构建一整行的数据
        line_buffer = pixel_green * width_logic 
        # ----------------------------------------------------
        
        for _ in range(height_logic):
            spi.write_data_a1(line_buffer)
            
        print("Done. Check LCD (Should be Green).")

    except Exception as e:
        print(f"\nError: {e}")
    finally:
        spi.close()

if __name__ == "__main__":
    main()
