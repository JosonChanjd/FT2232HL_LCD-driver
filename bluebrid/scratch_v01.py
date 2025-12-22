import tkinter as tk
from tkinter import ttk, messagebox
import mss
from PIL import Image
import time
import os
import threading
import pyautogui
from ctypes import *
import math

# ============================================================================
#  底层 FTDI 驱动 (带自动恢复与稳健读写)
# ============================================================================
try:
    os.environ['FTD2XX_DLL_DIR'] = r'C:\Users\sesa696240\Desktop\PMDB'
except:
    pass

class FTDI_Driver_Ultra:
    PIN_A0  = 0x01
    PIN_RST = 0x02
    PIN_CS  = 0x04 
    
    def __init__(self):
        try:
            self.dll = windll.LoadLibrary("FTD2XX.DLL")
        except:
            raise Exception("无法加载 FTD2XX.DLL")
        
        self.handle = c_void_p()
        self.connect()

    def connect(self):
        """ 连接并配置设备 """
        if self.handle:
            try: self.dll.FT_Close(self.handle)
            except: pass
            
        self.handle = c_void_p()
        if self.dll.FT_Open(0, byref(self.handle)) != 0:
            raise Exception("FTDI 设备未找到或被占用")
        
        # 优化 USB 参数：大缓冲 + 短延迟
        self.dll.FT_SetUSBParameters(self.handle, 65536, 65536)
        self.dll.FT_SetTimeouts(self.handle, 2000, 2000) # 2秒超时，防卡死
        self.dll.FT_SetLatencyTimer(self.handle, 2)
        
        # 重置 MPSSE 引擎
        self.dll.FT_SetBitMode(self.handle, 0, 0x00)
        time.sleep(0.05)
        self.dll.FT_SetBitMode(self.handle, 0, 0x02) 
        time.sleep(0.05)
        
        # 1. Purge
        self.dll.FT_Purge(self.handle, 3) 
        # 2. Config MPSSE
        self._setup_mpsse()
        # 3. HW Reset LCD
        self._hw_reset()
        # 4. SW Init LCD
        self._sw_init()

    def _setup_mpsse(self):
        # 10 MHz
        cmds = bytearray([
            0x8A, 0x97, 0x8D,
            0x86, 0x02, 0x00,  # Divisor=2 -> 10MHz
            0x85,
            0x80, 0x00, 0xFB,  # Mode 0 (SCLK Low)
            0x82, 0x07, 0x07   # GPIO Initial (CS=1)
        ])
        self._write_raw(cmds)

    def _write_raw(self, data):
        if isinstance(data, list): data = bytes(data)
        
        ptr = 0
        total = len(data)
        # 每次 USB 写包不超过 32KB
        chunk_limit = 32768 
        written_buf = c_ulong()
        
        while ptr < total:
            chunk = data[ptr : ptr + chunk_limit]
            ret = self.dll.FT_Write(self.handle, 
                                    (c_char * len(chunk)).from_buffer_copy(chunk), 
                                    len(chunk), 
                                    byref(written_buf))
            if ret != 0:
                raise Exception("USB 通信错误")
            actual = written_buf.value
            if actual == 0:
                raise Exception("设备无响应 (Timeout)")
            ptr += actual

    def _hw_reset(self):
        # 硬件复位引脚
        self._write_raw(b'\x82\x05\x07') # RST=0
        time.sleep(0.05)
        self._write_raw(b'\x82\x07\x07') # RST=1
        time.sleep(0.15)

    def _sw_init(self):
        # 基础初始化序列
        cmds = [
            (0x11, None),        # Sleep Out
            (0x36, [0x2A]),      # Landscape (MV=1)
            (0x3A, [0x05]),      # 16-bit RGB565
            (0x21, None),        # Inversion On
            (0x29, None)         # Display On
        ]
        
        # 特殊处理：Sleep Out 需要延时
        self.write_cmd(0x11)
        time.sleep(0.12)
        
        for c, d in cmds[1:]:
            self.write_cmd(c)
            if d: self.write_data_block(d)
        
        time.sleep(0.05)

    def write_cmd(self, cmd):
        # GPIO Low -> Write 1 Byte -> GPIO High
        self._write_raw(bytearray([0x82, 0x02, 0x07, 0x11, 0x00, 0x00, cmd, 0x82, 0x07, 0x07]))

    def write_data_block(self, data_bytes):
        # 一次性写入一个块
        if not isinstance(data_bytes, (bytes, bytearray)):
            data_bytes = bytearray(data_bytes)
        
        length = len(data_bytes) - 1
        # Header: CS=0, Cmd 0x11, Len L, Len H
        header = bytearray([0x82, 0x03, 0x07, 0x11, length & 0xFF, (length >> 8) & 0xFF])
        # Tail: CS=1
        tail = b'\x82\x07\x07'
        
        self._write_raw(header + data_bytes + tail)

    def close(self):
        try: self.dll.FT_Close(self.handle)
        except: pass

# ============================================================================
#  2. 高性能颜色处理引擎 (Look-Up Table)
# ============================================================================
class ColorEnhancer:
    def __init__(self):
        self.r_lut = [0] * 256
        self.g_lut = [0] * 256
        self.b_lut = [0] * 256
        
        # Gamma 1.3
        gamma = 1.3
        
        for i in range(256):
            # 1. 归一化并 Gamma 校正
            val = 255.0 * math.pow(i / 255.0, gamma)
            val = int(min(255, max(0, val)))
            
            # 2. 预计算位移
            # R (High 5 bits) -> move to High Byte [15:11]
            self.r_lut[i] = (val & 0xF8) << 8
            
            # G (6 bits) -> High 3 bits [10:8], Low 3 bits [7:5]
            self.g_lut[i] = (val & 0xFC) << 3
            
            # B (5 bits) -> Low Byte [4:0]
            self.b_lut[i] = (val >> 3)

# ============================================================================
#  3. 主程序 UI
# ============================================================================
class UltraApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ST7789 Pro (Auto-Recovery)")
        self.root.geometry("300x200")
        self.root.attributes('-topmost', 1) 
        
        self.driver = None
        self.streaming = False
        self.lut = ColorEnhancer()
        self.sct = mss.mss()
        self.screen_w, self.screen_h = pyautogui.size()
        
        self.W, self.H = 320, 240
        self.BLOCK_H = 10 
        
        # 预先分配内存
        self.full_buf = bytearray(self.W * self.H * 2)
        
        self._ui()
        
    def _ui(self):
        frame = tk.Frame(self.root, padx=10, pady=10)
        frame.pack(fill="both", expand=True)
        
        self.status = tk.StringVar(value="准备就绪")
        tk.Label(frame, textvariable=self.status, fg="blue", font=("Arial", 9)).pack()
        
        # [修改] 移除了不支持的 Emoji，改为普通字符
        self.btn_action = ttk.Button(frame, text=">>> 连接并开始 <<<", command=self.toggle)
        self.btn_action.pack(pady=10, fill="x")
        
        self.progress = ttk.Progressbar(frame, mode="determinate")
        self.progress.pack(fill="x", pady=5)
        
        self.lbl_fps = tk.Label(frame, text="FPS: 0.0")
        self.lbl_fps.pack()
        
    def log(self, msg, err=False):
        self.status.set(msg)
        print(f"[Sys] {msg}")

    def toggle(self):
        if not self.streaming:
            self.streaming = True
            # [修改] 移除了不支持的 Emoji
            self.btn_action.config(text="[ 停止传输 ]")
            threading.Thread(target=self._run_driver, daemon=True).start()
        else:
            self.streaming = False
            self.btn_action.config(text="正在停止...")

    def _run_driver(self):
        try:
            self.log("正在连接硬件...")
            if self.driver: self.driver.close()
            self.driver = FTDI_Driver_Ultra()
            
            # 进入传输循环
            self._transfer_loop()
            
        except Exception as e:
            self.log(f"硬件错误: {e}", True)
            self.streaming = False
            self.root.after(0, lambda: self.btn_action.config(text=">>> 重试连接 <<<"))
        finally:
            if self.driver: self.driver.close()

    def _transfer_loop(self):
        drv = self.driver
        
        col_cmd = bytearray([0x00, 0x00, 0x01, 0x3F]) # 0~319
        row_cmd = bytearray([0x00, 0x00, 0x00, 0xEF]) # 0~239
        
        r_map = self.lut.r_lut
        g_map = self.lut.g_lut
        b_map = self.lut.b_lut
        
        w, h = self.W, self.H
        bh = self.BLOCK_H
        
        last_t = time.time()
        frames = 0
        
        self.log("传输中 (Gamma+Resync)")
        
        while self.streaming:
            try:
                # 1. 鼠标位置
                mx, my = pyautogui.position()
                left = max(0, min(mx - 160, self.screen_w - 320))
                top = max(0, min(my - 120, self.screen_h - 240))
                
                # 2. 抓图
                sct_img = self.sct.grab({"top": int(top), "left": int(left), "width": w, "height": h, "mon": 1})
                
                # 3. 颜色转换
                img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
                
                r_ch = img.getchannel('R').getdata()
                g_ch = img.getchannel('G').getdata()
                b_ch = img.getchannel('B').getdata()
                
                # 4. 发送流程
                drv.write_cmd(0x2A); drv.write_data_block(col_cmd)
                drv.write_cmd(0x2B); drv.write_data_block(row_cmd)
                drv.write_cmd(0x2C)
                
                # 分块处理
                block_size_pixels = w * bh
                r_vals = list(r_ch)
                g_vals = list(g_ch)
                b_vals = list(b_ch)
                
                total_blocks = h // bh
                
                for i in range(total_blocks):
                    if not self.streaming: break
                    
                    start_idx = i * block_size_pixels
                    end_idx = start_idx + block_size_pixels
                    
                    block_data = bytearray(block_size_pixels * 2)
                    
                    rs = r_vals[start_idx:end_idx]
                    gs = g_vals[start_idx:end_idx]
                    bs = b_vals[start_idx:end_idx]
                    
                    idx = 0
                    for r, g, b in zip(rs, gs, bs):
                        val = r_map[r] | g_map[g] | b_map[b]
                        block_data[idx] = (val >> 8) & 0xFF
                        block_data[idx+1] = val & 0xFF
                        idx += 2
                        
                    drv.write_data_block(block_data)
                    
                    # 进度条
                    if i % 4 == 0:
                        self.root.after(0, lambda v=i: self.progress.config(value=v*4))

                # 计算 FPS
                frames += 1
                if time.time() - last_t >= 1.0:
                    fps = frames / (time.time() - last_t)
                    self.root.after(0, lambda f=fps: self.lbl_fps.config(text=f"FPS: {f:.1f}"))
                    frames = 0
                    last_t = time.time()
            
            except Exception as e:
                # 自动恢复
                self.log(f"通信中断: {e}", True)
                time.sleep(1)
                try:
                    drv.connect()
                    self.log("重连成功", False)
                except:
                    pass

        self.root.after(0, lambda: self.btn_action.config(text=">>> 连接并开始 <<<", state="normal"))

    def __del__(self):
        if self.driver: self.driver.close()

if __name__ == "__main__":
    root = tk.Tk()
    app = UltraApp(root)
    root.mainloop()
