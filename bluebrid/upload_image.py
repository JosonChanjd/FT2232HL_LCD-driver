import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk
import time
import os
import threading
from ctypes import *

# ============================================================================
#  底层驱动 (10MHz High-Speed but Stable Protocol)
# ============================================================================
try:
    os.environ['FTD2XX_DLL_DIR'] = r'C:\Users\sesa696240\Desktop\PMDB'
except:
    pass

class FTDI_HighSpeed_Stable_Driver:
    PIN_A0  = 0x01 # AC0
    PIN_RST = 0x02 # AC1
    PIN_CS  = 0x04 # AC2
    
    def __init__(self):
        try:
            self.dll = windll.LoadLibrary("FTD2XX.DLL")
        except Exception as e:
            raise Exception(f"无法加载 FTD2XX.DLL: {str(e)}")
        
        self.handle = c_void_p()
        if self.dll.FT_Open(0, byref(self.handle)) != 0:
            raise Exception("无法打开 FTDI 设备")
        
        self.dll.FT_SetUSBParameters(self.handle, 65536, 65536)
        self.dll.FT_SetTimeouts(self.handle, 5000, 5000)
        self.dll.FT_SetLatencyTimer(self.handle, 2)
        
        self.dll.FT_SetBitMode(self.handle, 0, 0x00)
        time.sleep(0.05)
        self.dll.FT_SetBitMode(self.handle, 0, 0x02) # MPSSE
        time.sleep(0.05)
        self.dll.FT_Purge(self.handle, 3) 
        
        self._setup_mpsse()

    def _setup_mpsse(self):
        # -----------------------------------------------------------
        # 配置 SPI: 10 MHz
        # Formula: 60MHz / ((1 + Divisor) * 2)
        # Divisor = 2 -> 60 / 6 = 10 MHz (满足 >= 8MHz 要求)
        # -----------------------------------------------------------
        divisor = 2
        print(f"-> 配置 SPI: 10 MHz (Div={divisor}), Mode 0")
        
        cmds = bytearray([
            0x8A,             
            0x97,             
            0x8D,             
            0x86, divisor, 0x00,  # Divisor = 2 (0x0002) -> 10 MHz
            0x85,             
            0x80, 0x00, 0xFB,     # SCLK Low
            0x82, 0x07, 0x07      # CS High
        ])
        self._write_raw(cmds)

    def _write_raw(self, data):
        # 严格的循环写入，确保高速下数据不丢失
        if isinstance(data, list): data = bytes(data)
        
        total_len = len(data)
        bytes_written = 0
        written_buffer = c_ulong()
        
        while bytes_written < total_len:
            chunk = data[bytes_written:] 
            ret = self.dll.FT_Write(self.handle, 
                                    (c_char * len(chunk)).from_buffer_copy(chunk), 
                                    len(chunk), 
                                    byref(written_buffer))
            if ret != 0:
                raise Exception("FTDI Write Error")
            actual = written_buffer.value
            if actual == 0:
                raise Exception("FTDI Buffer Full/Stuck")
            bytes_written += actual

    def reset_lcd(self):
        self._write_raw(b'\x82\x05\x07') # RST=0
        time.sleep(0.1)
        self._write_raw(b'\x82\x07\x07') # RST=1
        time.sleep(0.15)

    def write_cmd(self, cmd):
        # CS Toggle: High -> Low -> Data -> High
        # 即使是命令也进行 CS 切换，保证同步
        b = bytearray([
            0x82, 0x02, 0x07,          # CS=0, A0=0
            0x11, 0x00, 0x00, cmd,     # Write 1 byte
            0x82, 0x07, 0x07           # CS=1
        ])
        self._write_raw(b)

    def write_data_chunk(self, data_chunk):
        """
        发送一行数据 (Atom Transaction)
        CS 拉低 -> 发送数据 -> CS 拉高
        这能有效消除“图片错位”，因为每一行 CS 都会强制复位 LCD 的 bit 计数器
        """
        if isinstance(data_chunk, list): data_chunk = bytearray(data_chunk)
        
        length = len(data_chunk) - 1
        
        cmds = bytearray()
        # 1. CS Low, A0 High (Data)
        cmds.extend(b'\x82\x03\x07') 
        
        # 2. SPI Write Bytes
        cmds.append(0x11)
        cmds.append(length & 0xFF)
        cmds.append((length >> 8) & 0xFF)
        cmds.extend(data_chunk)
        
        # 3. CS High (Idle)
        cmds.extend(b'\x82\x07\x07') 
        
        self._write_raw(cmds)
        
    def close(self):
        if self.handle:
            self.dll.FT_Close(self.handle)

# ============================================================================
#  UI 应用程序
# ============================================================================
class LCDApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ST7789 10MHz 稳定版 (Row-by-Row)")
        self.root.geometry("500x600")
        
        self.driver = None
        self.connected = False
        self.img_data_rgb565 = None 
        self.is_uploading = False
        
        self._create_widgets()
        
    def _create_widgets(self):
        frame_ctrl = tk.LabelFrame(self.root, text="控制台", padx=10, pady=10)
        frame_ctrl.pack(pady=10, padx=10, fill="x")
        
        tk.Button(frame_ctrl, text="1. 连接设备", command=self.on_connect, bg="#bbdefb").grid(row=0, column=0, padx=5)
        tk.Button(frame_ctrl, text="2. 选择图片", command=self.on_open_image).grid(row=0, column=1, padx=5)
        self.btn_upload = tk.Button(frame_ctrl, text="3. 开始上传", command=self.on_upload, bg="#c8e6c9", state=tk.DISABLED)
        self.btn_upload.grid(row=0, column=2, padx=5)

        self.lbl_status = tk.Label(frame_ctrl, text="状态: 等待连接 (10MHz)", fg="gray")
        self.lbl_status.grid(row=1, column=0, columnspan=3, pady=5)
        
        self.lbl_preview = tk.Label(self.root, text="图片预览区域", bg="#e0e0e0", width=46, height=15)
        self.lbl_preview.pack(pady=10)
        
        self.progress = ttk.Progressbar(self.root, orient=tk.HORIZONTAL, length=450, mode='determinate')
        self.progress.pack(pady=5)
        
        self.txt_log = tk.Text(self.root, height=12, width=65, font=("Consolas", 8))
        self.txt_log.pack(pady=5, padx=10)

    def log(self, msg):
        self.txt_log.insert(tk.END, f"[{time.strftime('%H:%M:%S')}] {msg}\n")
        self.txt_log.see(tk.END)

    def on_connect(self):
        try:
            if self.driver: self.driver.close()
            self.driver = FTDI_HighSpeed_Stable_Driver()
            self.log("MPSSE 10MHz 初始化完成")
            threading.Thread(target=self._init_lcd, daemon=True).start()
        except Exception as e:
            messagebox.showerror("连接错误", str(e))
            self.log(f"Err: {e}")

    def _init_lcd(self):
        self.log("正在执行复位和初始化...")
        drv = self.driver
        drv.reset_lcd()
        
        # 初始化序列
        init_seq = [
            (0x11, None, 0.120),  # Sleep Out
            (0x36, [0x2A], 0.01), # Landscape (MV=1)
            (0x3A, [0x05], 0.01), # Pixel Format 16bit
            (0x21, None, 0.01),   # Inversion ON (通常ST7789需要)
            (0x29, None, 0.05),   # Display On
        ]
        
        for cmd, data, wait in init_seq:
            drv.write_cmd(cmd)
            if data:
                drv.write_data_chunk(data)
            time.sleep(wait)
            
        self.connected = True
        self.lbl_status.config(text="已连接", fg="green")
        self.log("LCD 初始化就绪 (横屏模式 0x2A)")
        
        if self.img_data_rgb565:
            self.root.after(0, lambda: self.btn_upload.config(state=tk.NORMAL))

    def on_open_image(self):
        path = filedialog.askopenfilename(filetypes=[("Image", "*.jpg;*.png;*.bmp")])
        if not path: return
        
        try:
            img = Image.open(path).convert("RGB")
            # 强制缩放至 320x240 (ST7789横屏分辨率)
            img = img.resize((320, 240), Image.Resampling.LANCZOS)
            
            tk_img = ImageTk.PhotoImage(img)
            self.lbl_preview.config(image=tk_img, text="")
            self.lbl_preview.image = tk_img
            
            self.btn_upload.config(state=tk.DISABLED)
            threading.Thread(target=self._convert_image, args=(img,), daemon=True).start()
            
        except Exception as e:
            self.log(f"图片错误: {e}")

    def _convert_image(self, img):
        self.log("正在转换数据...")
        pixels = list(img.getdata())
        self.img_data_rgb565 = bytearray(len(pixels) * 2)
        
        idx = 0
        for r, g, b in pixels:
            # RGB565 conversion
            rgb = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
            # Big Endian
            self.img_data_rgb565[idx]   = (rgb >> 8) & 0xFF
            self.img_data_rgb565[idx+1] = rgb & 0xFF
            idx += 2
            
        self.log(f"转换完成 ({len(self.img_data_rgb565)} 字节)")
        if self.connected:
            self.root.after(0, lambda: self.btn_upload.config(state=tk.NORMAL))

    def on_upload(self):
        if not self.img_data_rgb565: return
        self.is_uploading = True
        self.btn_upload.config(state=tk.DISABLED)
        threading.Thread(target=self._start_transfer, daemon=True).start()

    def _start_transfer(self):
        drv = self.driver
        try:
            self.log("设定地址窗口 (320x240)...")
            
            # 设置列地址 0~319 (逻辑宽)
            drv.write_cmd(0x2A)
            drv.write_data_chunk([0, 0, 1, 63])
            
            # 设置行地址 0~239 (逻辑高)
            drv.write_cmd(0x2B)
            drv.write_data_chunk([0, 0, 0, 239])
            
            # 准备写入显存
            drv.write_cmd(0x2C)
            
            self.log(">>> 开始行级传输 <<<")
            
            width = 320
            height = 240
            bytes_per_line = width * 2 # 640字节
            
            start_time = time.time()
            
            # --- 核心：按行循环发送 ---
            for y in range(height):
                start = y * bytes_per_line
                end = start + bytes_per_line
                line_data = self.img_data_rgb565[start:end]
                
                # 发送一行
                drv.write_data_chunk(line_data)
                
                # --- 稳定性关键：行间延时 ---
                # 这保证了 LCD 有绝对足够的时间将数据从 FIFO 写入 GRAM
                # 同时 CS 的拉高拉低可以重置可能出现的位移
                # 0.002秒延时 * 240行 ≈ 0.5秒额外时间，对用户体验影响极小，但极大提升稳定性
                time.sleep(0.002)
                
                # 更新进度
                if y % 24 == 0: # 减少UI刷新频率
                    progress = (y / height) * 100
                    self.root.after(0, lambda p=progress: self.progress.config(value=p))
            
            duration = time.time() - start_time
            self.root.after(0, lambda: self.progress.config(value=100))
            self.log(f"传输完成! 耗时: {duration:.2f}秒")
            
        except Exception as e:
            self.log(f"传输异常: {e}")
        finally:
            self.is_uploading = False
            self.root.after(0, lambda: self.btn_upload.config(state=tk.NORMAL))

    def __del__(self):
        if self.driver:
            self.driver.close()

if __name__ == "__main__":
    root = tk.Tk()
    app = LCDApp(root)
    root.mainloop()
