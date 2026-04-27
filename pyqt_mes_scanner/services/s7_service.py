# -*- coding: utf-8 -*-
"""西门子 S7 通讯服务 (基于 snap7)"""
import struct
import os
import concurrent.futures

try:
    import snap7
    from snap7.type import Areas
    from snap7.util import (
        get_bool, set_bool,
        get_int, set_int,
        get_dint, set_dint,
        get_real, set_real,
        get_string, set_string,
        get_sint, set_sint,
    )
    SNAP7_AVAILABLE = True
except ImportError:
    SNAP7_AVAILABLE = False


def _get_snap7_lib_path():
    """获取项目目录下的 snap7.dll 路径"""
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dll_path = os.path.join(project_dir, "snap7.dll")
    if os.path.exists(dll_path):
        return dll_path
    return None


class S7Service:
    """影子线程 + 零延迟缓存机制，保障 PyQt 主线程绝对流畅"""

    def __init__(self):
        self.client = None
        self.connected = False
        self._ip = ""
        self._rack = 0
        self._slot = 0
        self._cache = {} # 内存高速缓存
        import concurrent.futures
        import threading
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)
        self._lock = threading.Lock()

    def is_available(self):
        return SNAP7_AVAILABLE

    def connect(self, ip, rack=0, slot=1):
        if not SNAP7_AVAILABLE:
            return False, "snap7 库未安装"
        
        self._ip = ip
        self._rack = rack
        self._slot = slot

        # 如果当前未连接，发起子线程后台连接
        if not self.connected:
            self.executor.submit(self._connect_sync, ip, rack, slot)
            return False, "正在后台发起连接..."
            
        return True, "连接成功"

    def _connect_sync(self, ip, rack, slot):
        with self._lock:
            try:
                if self.client is not None:
                    try:
                        self.client.disconnect()
                        self.client.destroy()
                    except Exception:
                        pass
                lib_path = _get_snap7_lib_path()
                if lib_path:
                    self.client = snap7.client.Client(lib_location=lib_path)
                else:
                    self.client = snap7.client.Client()
                self.client.connect(ip, rack, slot)
                self.connected = True
                return True, "连接成功"
            except Exception:
                self.connected = False
                return False, "连接失败"

    def disconnect(self):
        with self._lock:
            if self.client is not None:
                try:
                    self.client.disconnect()
                    self.client.destroy()
                except Exception:
                    pass
                finally:
                    self.client = None
            self.connected = False

    def _reconnect_silently(self):
        """静默自动重连，防止网络闪断造成的永久死线"""
        with self._lock:
            try:
                if not getattr(self, "_ip", ""):
                    return
                if self.client is not None:
                    try:
                        self.client.disconnect()
                        self.client.destroy()
                    except Exception:
                        pass
                lib_path = _get_snap7_lib_path()
                if lib_path:
                    self.client = snap7.client.Client(lib_location=lib_path)
                else:
                    self.client = snap7.client.Client()
                self.client.connect(self._ip, self._rack, self._slot)
                self.connected = True
            except Exception:
                self.connected = False
            finally:
                self._is_reconnecting = False

    def read_area(self, area, db, offset, size):
        key = f"{area}:{db}:{offset}:{size}"
        if self.connected and self.client is not None:
            with self._lock:
                try:
                    val = self.client.read_area(area, db, offset, size)
                    if val is not None:
                        self._cache[key] = val
                        return val
                except Exception:
                    self.connected = False
                    
        if getattr(self, "_ip", ""):
            if not getattr(self, "_is_reconnecting", False):
                self._is_reconnecting = True
                self.executor.submit(self._reconnect_silently)
                
        return self._cache.get(key, bytearray(size))

    def _read_area_sync_and_cache_redundant(self, area, db, offset, size, key):
        # 始终为缓存请求准备一个键
        key = f"{area}:{db}:{offset}:{size}"
        
        # 立即秒回当前内存缓存里的值（避免任何等待）
        # 默认赋予一个占位大小的 bytearray 保证切片可用
        cached_val = self._cache.get(key, bytearray(size))
        
        # 如果未连接，直接返回缓存，并唤醒后台重连
        if not self.connected or self.client is None:
            if getattr(self, "_ip", ""):
                if not getattr(self, "_is_reconnecting", False):
                    self._is_reconnecting = True
                    self.executor.submit(self._reconnect_silently)
            return cached_val

        # 后台交由影子线程静默更新寄存器
        self.executor.submit(self._read_area_sync_and_cache, area, db, offset, size, key)
        return cached_val

    def _read_area_sync_and_cache(self, area, db, offset, size, key):
        try:
            if not self.connected or self.client is None:
                return
            with self._lock:
                val = self.client.read_area(area, db, offset, size)
            if val is not None:
                self._cache[key] = val
        except Exception as e:
            # 避免因为某些配置的监控地址不存在（如 Area not found）导致全局服务熔断
            err_msg = str(e).lower()
            if "area not found" in err_msg or "address out of range" in err_msg:
                pass
            else:
                self.connected = False

    def write_area(self, area, db, offset, data):
        if not self.connected or self.client is None:
            if getattr(self, "_ip", ""):
                if not getattr(self, "_is_reconnecting", False):
                    self._is_reconnecting = True
                    self.executor.submit(self._reconnect_silently)
            return False
        
        # 写入也异步执行，防止卡住写过程
        self.executor.submit(self._write_area_sync, area, db, offset, data)
        return True

    def _write_area_sync(self, area, db, offset, data):
        try:
            if not self.connected or self.client is None:
                return False
            with self._lock:
                self.client.write_area(area, db, offset, data)
            return True
        except Exception:
            self.connected = False
            return False

    # ---------- Bool ----------
    def read_bool(self, db, offset, bit):
        buf = self.read_area(Areas.DB, db, offset, 1)
        if buf is None or len(buf) == 0:
            return False
        return get_bool(buf, 0, bit)

    def write_bool(self, db, offset, bit, value):
        buf = self.read_area(Areas.DB, db, offset, 1)
        if buf is None or len(buf) == 0:
            buf = bytearray(1)
        set_bool(buf, 0, bit, value)
        return self.write_area(Areas.DB, db, offset, buf)

    # ---------- Int (2 bytes) ----------
    def read_int(self, db, offset):
        buf = self.read_area(Areas.DB, db, offset, 2)
        if buf is None or len(buf) < 2:
            return 0
        return get_int(buf, 0)

    def write_int(self, db, offset, value):
        buf = bytearray(2)
        set_int(buf, 0, value)
        return self.write_area(Areas.DB, db, offset, buf)

    # ---------- SInt (1 byte) ----------
    def read_sint(self, db, offset):
        buf = self.read_area(Areas.DB, db, offset, 1)
        if buf is None or len(buf) == 0:
            return 0
        return get_sint(buf, 0)

    def write_sint(self, db, offset, value):
        buf = bytearray(1)
        set_sint(buf, 0, value)
        return self.write_area(Areas.DB, db, offset, buf)

    # ---------- DInt (4 bytes) ----------
    def read_dint(self, db, offset):
        buf = self.read_area(Areas.DB, db, offset, 4)
        if buf is None or len(buf) < 4:
            return 0
        return get_dint(buf, 0)

    def write_dint(self, db, offset, value):
        buf = bytearray(4)
        set_dint(buf, 0, value)
        return self.write_area(Areas.DB, db, offset, buf)

    # ---------- Real (4 bytes) ----------
    def read_real(self, db, offset):
        buf = self.read_area(Areas.DB, db, offset, 4)
        if buf is None or len(buf) < 4:
            return 0.0
        return get_real(buf, 0)

    def write_real(self, db, offset, value):
        buf = bytearray(4)
        set_real(buf, 0, value)
        return self.write_area(Areas.DB, db, offset, buf)

    # ---------- String (S7 String, max 254 chars) ----------
    def read_string(self, db, offset, max_len=254):
        buf = self.read_area(Areas.DB, db, offset, max_len + 2)
        if buf is None or len(buf) < 2:
            return ""
        # 如果字节数组全是零，说明影子线程还没有拉回 PLC 真实数据
        if buf.count(0) == len(buf):
            return ""
        try:
            return get_string(buf, 0)
        except Exception:
            return ""

    def write_string(self, db, offset, value, max_len=254):
        buf = bytearray(max_len + 2)
        set_string(buf, 0, value, max_len)
        return self.write_area(Areas.DB, db, offset, buf)

    # ---------- 通用写入（根据类型自动选择） ----------
    def write_value(self, db, offset, data_type, value, bit=0, str_len=254):
        data_type = data_type.lower()
        if data_type == "bool":
            return self.write_bool(db, offset, bit, value)
        elif data_type == "int":
            return self.write_int(db, offset, value)
        elif data_type == "sint":
            return self.write_sint(db, offset, value)
        elif data_type == "dint":
            return self.write_dint(db, offset, value)
        elif data_type == "real":
            return self.write_real(db, offset, value)
        elif data_type == "string":
            return self.write_string(db, offset, value, str_len)
        else:
            return False

    def read_value(self, db, offset, data_type, bit=0, str_len=254):
        data_type = data_type.lower()
        if data_type == "bool":
            return self.read_bool(db, offset, bit)
        elif data_type == "int":
            return self.read_int(db, offset)
        elif data_type == "sint":
            return self.read_sint(db, offset)
        elif data_type == "dint":
            return self.read_dint(db, offset)
        elif data_type == "real":
            return self.read_real(db, offset)
        elif data_type == "string":
            return self.read_string(db, offset, str_len)
        else:
            return None

    # ---------- Bool ----------
    def read_bool(self, db, offset, bit):
        buf = self.read_area(Areas.DB, db, offset, 1)
        if buf is None:
            return None
        return get_bool(buf, 0, bit)

    def write_bool(self, db, offset, bit, value):
        buf = self.read_area(Areas.DB, db, offset, 1)
        if buf is None:
            return False
        set_bool(buf, 0, bit, value)
        return self.write_area(Areas.DB, db, offset, buf)

    # ---------- Int (2 bytes) ----------
    def read_int(self, db, offset):
        buf = self.read_area(Areas.DB, db, offset, 2)
        if buf is None:
            return None
        return get_int(buf, 0)

    def write_int(self, db, offset, value):
        buf = bytearray(2)
        set_int(buf, 0, value)
        return self.write_area(Areas.DB, db, offset, buf)

    # ---------- SInt (1 byte) ----------
    def read_sint(self, db, offset):
        buf = self.read_area(Areas.DB, db, offset, 1)
        if buf is None:
            return None
        return get_sint(buf, 0)

    def write_sint(self, db, offset, value):
        buf = bytearray(1)
        set_sint(buf, 0, value)
        return self.write_area(Areas.DB, db, offset, buf)

    # ---------- DInt (4 bytes) ----------
    def read_dint(self, db, offset):
        buf = self.read_area(Areas.DB, db, offset, 4)
        if buf is None:
            return None
        return get_dint(buf, 0)

    def write_dint(self, db, offset, value):
        buf = bytearray(4)
        set_dint(buf, 0, value)
        return self.write_area(Areas.DB, db, offset, buf)

    # ---------- Real (4 bytes) ----------
    def read_real(self, db, offset):
        buf = self.read_area(Areas.DB, db, offset, 4)
        if buf is None:
            return None
        return get_real(buf, 0)

    def write_real(self, db, offset, value):
        buf = bytearray(4)
        set_real(buf, 0, value)
        return self.write_area(Areas.DB, db, offset, buf)

    # ---------- String (S7 String, max 254 chars) ----------
    def read_string(self, db, offset, max_len=254):
        buf = self.read_area(Areas.DB, db, offset, max_len + 2)
        if buf is None or len(buf) < 2:
            return ""
        # 如果字节数组全是零，说明影子线程还没有拉回 PLC 真实数据
        if buf.count(0) == len(buf):
            return ""
        try:
            return get_string(buf, 0)
        except Exception:
            return ""

    def write_string(self, db, offset, value, max_len=254):
        buf = bytearray(max_len + 2)
        set_string(buf, 0, value, max_len)
        return self.write_area(Areas.DB, db, offset, buf)

    # ---------- 通用写入（根据类型自动选择） ----------
    def write_value(self, db, offset, data_type, value, bit=0, str_len=254):
        data_type = data_type.lower()
        if data_type == "bool":
            return self.write_bool(db, offset, bit, value)
        elif data_type == "int":
            return self.write_int(db, offset, value)
        elif data_type == "sint":
            return self.write_sint(db, offset, value)
        elif data_type == "dint":
            return self.write_dint(db, offset, value)
        elif data_type == "real":
            return self.write_real(db, offset, value)
        elif data_type == "string":
            return self.write_string(db, offset, value, str_len)
        else:
            return False

    def read_value(self, db, offset, data_type, bit=0, str_len=254):
        data_type = data_type.lower()
        if data_type == "bool":
            return self.read_bool(db, offset, bit)
        elif data_type == "int":
            return self.read_int(db, offset)
        elif data_type == "sint":
            return self.read_sint(db, offset)
        elif data_type == "dint":
            return self.read_dint(db, offset)
        elif data_type == "real":
            return self.read_real(db, offset)
        elif data_type == "string":
            return self.read_string(db, offset, str_len)
        else:
            return None
