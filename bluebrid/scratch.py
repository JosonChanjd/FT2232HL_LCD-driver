import tkinter as tk
from tkinter import ttk, messagebox
import mss
from PIL import Image  # <--- 补回了这一行
import time
import os
import threading
import pyautogui
from ctypes import *
import math

# ============================================================================
#  1. 底层 FTDI 驱动 (10MHz)
# ============================================================================
try:
    os.environ['FTD2XX_DLL_DIR'] = r'C:\Users\sesa696240\Desktop\PMDB'
except:
    pass

class FTDI_Driver_Pro:
    PIN_A0  = 0x01
    PIN_RST = 0x02
    PIN_CS  = 0x04 
    
    def __init__(self):
        try:
            self.dll = windll.LoadLibrary("FTD2XX.DLL")
        except:
            raise Exception("FTD2XX.DLL 加载失败")
        
        self.handle = c_void_p()
        if self.dll.FT_Open(0, byref(self.handle)) != 0:
            raise Exception("无法打开 FTDI 设备")
        
        self.dll.FT_SetUSBParameters(self.handle, 65536, 65536)
        self.dll.FT_SetTimeouts(self.handle, 5000, 5000)
        self.dll.FT_SetLatencyTimer(self.handle, 2)
        
        self.dll.FT_SetBitMode(self.handle, 0, 0x00)
        time.sleep(0.05)
        self.dll.FT_SetBitMode(self.handle, 0, 0x02) 
        time.sleep(0.05)
        self.dll.FT_Purge(self.handle, 3) 
        
        self._setup_mpsse()

    def _setup_mpsse(self):
        # 10 MHz
        cmds = bytearray([
            0x8A, 0x97, 0x8D,
            0x86, 0x02, 0x00,  # Div=2
            0x85,
            0x80, 0x00, 0xFB,  
            0x82, 0x07, 0x07   
        ])
        self._write_raw(cmds)

    def _write_raw(self, data):
        if isinstance(data, list): data = bytes(data)
        total_len = len(data)
        bytes_written = 0
        written_buf = c_ulong()
        
        while bytes_written < total_len:
            chunk = data[bytes_written:]
            ret = self.dll.FT_Write(self.handle, 
                                    (c_char * len(chunk)).from_buffer_copy(chunk), 
                                    len(chunk), 
                                    byref(written_buf))
            if ret != 0 or written_buf.value == 0:
                raise Exception("USB 写入失败")
            bytes_written += written_buf.value

    def reset_and_init(self):
        self._write_raw(b'\x82\x05\x07') 
        time.sleep(0.1)
        self._write_raw(b'\x82\x07\x07') 
        time.sleep(0.15)
        
        # Init: 0x36=2A (Landscape), 0x3A=05 (16bit)
        seq = [
            (0x11, None, 0.12),
            (0x36, [0x2A], 0.01),
            (0x3A, [0x05], 0.01),
            (0x21, None, 0.01),
            (0x29, None, 0.05)
        ]
        for cmd, data, wait in seq:
            self.write_cmd(cmd)
            if data: self.write_data_block(data)
            time.sleep(wait)

    def write_cmd(self, cmd):
        self._write_raw(bytearray([0x82, 0x02, 0x07, 0x11, 0x00, 0x00, cmd, 0x82, 0x07, 0x07]))

    def write_data_block(self, data_input):
        if isinstance(data_input, list):
            data_bytes = bytearray(data_input)
        else:
            data_bytes = data_input 

        length = len(data_bytes) - 1
        header = bytearray([0x82, 0x03, 0x07, 0x11, length & 0xFF, (length >> 8) & 0xFF])
        tail = b'\x82\x07\x07'
        self._write_raw(header + data_bytes + tail)

    def close(self):
        if self.handle: self.dll.FT_Close(self.handle)

# ============================================================================
#  2. UI 程序
# ============================================================================
class ScreenMirrorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ST7789 Pro (10MHz)")
        self.root.geometry("300x180")
        self.root.attributes('-topmost', 1) 
        
        self.driver = None
        self.connected = False
        self.streaming = False
        
        self.sct = mss.mss()
        self.screen_w, self.screen_h = pyautogui.size()
        
        self.W, self.H = 320, 240
        self.BLOCK_HEIGHT = 40 
        
        self._setup_ui()
        
    def _setup_ui(self):
        frame = tk.Frame(self.root, padx=10, pady=10)
        frame.pack(fill="both", expand=True)
        
        self.status_var = tk.StringVar(value="等待连接...")
        self.fps_var = tk.StringVar(value="FPS: --")
        
        tk.Label(frame, text="ST7789 实时传输终端", font=("Microsoft YaHei", 10, "bold")).pack()
        tk.Label(frame, textvariable=self.status_var, fg="gray", font=("Arial", 8)).pack(pady=2)
        
        btn_frame = tk.Frame(frame)
        btn_frame.pack(pady=10)
        
        self.btn_conn = ttk.Button(btn_frame, text="⚡ 连接", command=self.on_connect, width=10)
        self.btn_conn.pack(side="left", padx=5)
        
        self.btn_run = ttk.Button(btn_frame, text="▶ 开始", command=self.on_toggle, width=10, state="disabled")
        self.btn_run.pack(side="left", padx=5)
        
        self.progress = ttk.Progressbar(frame, mode='determinate')
        self.progress.pack(fill='x', pady=5)
        
        tk.Label(frame, textvariable=self.fps_var, font=("Consolas", 9)).pack()

    def log(self, msg, color="black"):
        self.status_var.set(msg)

    def on_connect(self):
        if self.driver: 
            self.driver.close()
        
        try:
            self.driver = FTDI_Driver_Pro()
            threading.Thread(target=self._init_task, daemon=True).start()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _init_task(self):
        self.log("初始化设备...")
        try:
            self.driver.reset_and_init()
            self.connected = True
            self.root.after(0, lambda: self.log("设备就绪 (10MHz)", "green"))
            self.root.after(0, lambda: self.btn_run.config(state="normal"))
        except Exception as e:
            self.root.after(0, lambda: self.log(str(e), "red"))

    def on_toggle(self):
        if not self.streaming:
            self.streaming = True
            self.btn_run.config(text="⏹ 停止")
            self.btn_conn.config(state="disabled")
            threading.Thread(target=self._stream_loop, daemon=True).start()
        else:
            self.streaming = False
            self.btn_run.config(text="停止中...")

    def _stream_loop(self):
        drv = self.driver
        
        col_set = bytearray([0x00, 0x00, 0x01, 0x3F])
        row_set = bytearray([0x00, 0x00, 0x00, 0xEF])
        
        frame_cnt = 0
        last_t = time.time()
        
        while self.streaming:
            try:
                # 1. 坐标
                mx, my = pyautogui.position()
                left = mx - 160
                top = my - 120
                if left < 0: left = 0
                if top < 0: top = 0
                if left + 320 > self.screen_w: left = self.screen_w - 320
                if top + 240 > self.screen_h: top = self.screen_h - 240
                
                # 2. 抓屏
                sct_img = self.sct.grab({"top": int(top), "left": int(left), "width": 320, "height": 240, "mon": 1})
                
                # 3. 转换
                img_pil = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
                
                # 分离通道，加速处理
                r_ch = list(img_pil.getchannel('R').getdata())
                g_ch = list(img_pil.getchannel('G').getdata())
                b_ch = list(img_pil.getchannel('B').getdata())
                
                # 4. 传输 (分块)
                drv.write_cmd(0x2A); drv.write_data_block(col_set)
                drv.write_cmd(0x2B); drv.write_data_block(row_set)
                drv.write_cmd(0x2C)
                
                block_h = self.BLOCK_HEIGHT
                
                for start_y in range(0, 240, block_h):
                    if not self.streaming: break
                    
                    end_y = min(start_y + block_h, 240)
                    count = 320 * (end_y - start_y)
                    p_start = start_y * 320
                    p_end = p_start + count
                    
                    # 列表切片
                    rs = r_ch[p_start:p_end]
                    gs = g_ch[p_start:p_end]
                    bs = b_ch[p_start:p_end]
                    
                    # 极速打包 RGB565
                    int_vals = [ ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3) 
                                 for r, g, b in zip(rs, gs, bs) ]
                    
                    block_data = bytearray(count * 2)
                    block_data[0::2] = [v >> 8 for v in int_vals]
                    block_data[1::2] = [v & 0xFF for v in int_vals]
                    
                    drv.write_data_block(block_data)
                    time.sleep(0.002) # 微小延时
                    
                    # 进度条
                    prog = (end_y / 240) * 100
                    self.root.after(0, lambda p=prog: self.progress.config(value=p))

                frame_cnt += 1
                if time.time() - last_t >= 1.0:
                    fps = frame_cnt / (time.time() - last_t)
                    self.root.after(0, lambda f=fps: self.fps_var.set(f"FPS: {f:.1f}"))
                    frame_cnt = 0
                    last_t = time.time()
                
            except Exception as e:
                print(f"Loop Err: {e}")
                break
        
        self.root.after(0, self._ui_stop)

    def _ui_stop(self):
        self.streaming = False
        self.btn_run.config(text="▶ 开始")
        self.btn_conn.config(state="normal")
        self.progress.config(value=0)

    def __del__(self):
        if self.driver: self.driver.close()

if __name__ == "__main__":
    root = tk.Tk()
    app = ScreenMirrorApp(root)
    root.mainloop()
