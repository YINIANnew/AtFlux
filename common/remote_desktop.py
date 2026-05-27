import threading
import time
import struct
import zlib

try:
    import win32api
    import win32con
    import win32gui
    import win32ui
    import win32com.client
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False

class ScreenCapture:
    def __init__(self, config):
        self.config = config
        self.capture_interval = config['remote_desktop']['screen_capture_interval']
        self.max_frame_size = config['remote_desktop']['max_frame_size']
        self.compression_level = config['remote_desktop']['compression_level']
        
        self.running = False
        self.thread = None
        self.last_frame = None
        self.callback = None
        
        self.hwnd = win32gui.GetDesktopWindow() if HAS_WIN32 else None
    
    def start(self, callback=None):
        self.callback = callback
        self.running = True
        self.thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.thread.start()
    
    def stop(self):
        self.running = False
    
    def _capture_loop(self):
        while self.running:
            frame = self.capture_screen()
            if frame and self.callback:
                self.callback(frame)
            time.sleep(self.capture_interval / 1000.0)
    
    def capture_screen(self):
        if not HAS_WIN32 or not self.hwnd:
            return None
        
        try:
            left, top, right, bottom = win32gui.GetWindowRect(self.hwnd)
            width = right - left
            height = bottom - top
            
            hdc = win32gui.GetDC(self.hwnd)
            mfc_dc = win32ui.CreateDCFromHandle(hdc)
            save_dc = mfc_dc.CreateCompatibleDC()
            
            bitmap = win32ui.CreateBitmap()
            bitmap.CreateCompatibleBitmap(mfc_dc, width, height)
            save_dc.SelectObject(bitmap)
            
            save_dc.BitBlt((0, 0), (width, height), mfc_dc, (0, 0), win32con.SRCCOPY)
            
            bmp_info = bitmap.GetInfo()
            bmp_str = bitmap.GetBitmapBits(True)
            
            mfc_dc.DeleteDC()
            save_dc.DeleteDC()
            win32gui.ReleaseDC(self.hwnd, hdc)
            win32gui.DeleteObject(bitmap.GetHandle())
            
            return {
                'width': width,
                'height': height,
                'bits_per_pixel': bmp_info['bmBitsPixel'],
                'data': bmp_str
            }
        
        except Exception as e:
            return None
    
    def compress_frame(self, frame):
        if not frame:
            return None
        
        try:
            raw_data = struct.pack('!IIII', 
                frame['width'], 
                frame['height'], 
                frame['bits_per_pixel'],
                len(frame['data'])
            ) + frame['data']
            
            compressed = zlib.compress(raw_data, self.compression_level)
            
            if len(compressed) > self.max_frame_size:
                compressed = compressed[:self.max_frame_size]
            
            return compressed
        
        except Exception as e:
            return None
    
    def decompress_frame(self, compressed_data):
        try:
            raw_data = zlib.decompress(compressed_data)
            
            header_size = 16
            width = struct.unpack('!I', raw_data[0:4])[0]
            height = struct.unpack('!I', raw_data[4:8])[0]
            bits_per_pixel = struct.unpack('!I', raw_data[8:12])[0]
            data_size = struct.unpack('!I', raw_data[12:16])[0]
            data = raw_data[header_size:header_size + data_size]
            
            return {
                'width': width,
                'height': height,
                'bits_per_pixel': bits_per_pixel,
                'data': data
            }
        
        except Exception as e:
            return None

class InputSimulator:
    def __init__(self):
        if HAS_WIN32:
            self.shell = win32com.client.Dispatch("WScript.Shell")
    
    def send_key(self, key_code, pressed=True):
        if not HAS_WIN32:
            return
        
        try:
            if pressed:
                win32api.keybd_event(key_code, 0, 0, 0)
            else:
                win32api.keybd_event(key_code, 0, win32con.KEYEVENTF_KEYUP, 0)
        except Exception as e:
            pass
    
    def send_mouse_move(self, x, y):
        if not HAS_WIN32:
            return
        
        try:
            win32api.SetCursorPos((x, y))
        except Exception as e:
            pass
    
    def send_mouse_click(self, button='left', pressed=True):
        if not HAS_WIN32:
            return
        
        try:
            if button == 'left':
                down_flag = win32con.MOUSEEVENTF_LEFTDOWN
                up_flag = win32con.MOUSEEVENTF_LEFTUP
            elif button == 'right':
                down_flag = win32con.MOUSEEVENTF_RIGHTDOWN
                up_flag = win32con.MOUSEEVENTF_RIGHTUP
            else:
                return
            
            if pressed:
                win32api.mouse_event(down_flag, 0, 0, 0, 0)
            else:
                win32api.mouse_event(up_flag, 0, 0, 0, 0)
        except Exception as e:
            pass
    
    def send_mouse_wheel(self, delta):
        if not HAS_WIN32:
            return
        
        try:
            win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, delta, 0)
        except Exception as e:
            pass

class RemoteDesktopProtocol:
    SCREEN_FRAME = 0x10
    MOUSE_MOVE = 0x11
    MOUSE_CLICK = 0x12
    MOUSE_WHEEL = 0x13
    KEY_EVENT = 0x14
    
    def __init__(self, session, crypto_manager):
        self.session = session
        self.crypto_manager = crypto_manager
    
    def send_frame(self, frame_data):
        header = struct.pack('!II', self.SCREEN_FRAME, len(frame_data))
        message = header + frame_data
        if self.crypto_manager:
            message = self.crypto_manager.encrypt_with_aes(message)
        self.session.send(message)
    
    def send_mouse_move(self, x, y):
        payload = struct.pack('!II', x, y)
        header = struct.pack('!II', self.MOUSE_MOVE, len(payload))
        message = header + payload
        if self.crypto_manager:
            message = self.crypto_manager.encrypt_with_aes(message)
        self.session.send(message)
    
    def send_mouse_click(self, button, pressed):
        button_code = 0 if button == 'left' else 1
        pressed_code = 1 if pressed else 0
        payload = struct.pack('!BB', button_code, pressed_code)
        header = struct.pack('!II', self.MOUSE_CLICK, len(payload))
        message = header + payload
        if self.crypto_manager:
            message = self.crypto_manager.encrypt_with_aes(message)
        self.session.send(message)
    
    def send_key_event(self, key_code, pressed):
        pressed_code = 1 if pressed else 0
        payload = struct.pack('!IB', key_code, pressed_code)
        header = struct.pack('!II', self.KEY_EVENT, len(payload))
        message = header + payload
        if self.crypto_manager:
            message = self.crypto_manager.encrypt_with_aes(message)
        self.session.send(message)
    
    def parse_message(self, data):
        if self.crypto_manager:
            data = self.crypto_manager.decrypt_with_aes(data)
        
        if len(data) < 8:
            return None, None
        
        msg_type = struct.unpack('!I', data[:4])[0]
        payload_length = struct.unpack('!I', data[4:8])[0]
        payload = data[8:8+payload_length]
        
        return msg_type, payload