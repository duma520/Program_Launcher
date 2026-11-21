import os
import sys
import time
import threading
import json
from concurrent.futures import ThreadPoolExecutor, as_completed


# 更鲁棒的 win32 模块导入处理
def setup_win32_imports():
    """设置 win32 模块的导入路径"""
    if getattr(sys, 'frozen', False):
        # 打包后的环境
        base_path = sys._MEIPASS if hasattr(sys, '_MEIPASS') else os.path.dirname(sys.executable)
        
        # 添加所有可能的路径
        possible_paths = [
            base_path,
            os.path.join(base_path, 'win32'),
            os.path.join(base_path, 'win32com'),
            os.path.join(base_path, 'win32ctypes'),
            os.path.join(base_path, 'pywin32-ctypes'),
            os.path.join(base_path, 'pywin32_system32'),
            os.path.join(base_path, 'win32ctypes', 'pywin32'),
            os.path.join(base_path, 'win32ctypes', 'win32api'),
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                sys.path.insert(0, path)
        
        # 设置环境变量
        os.environ['PATH'] = base_path + os.pathsep + os.environ.get('PATH', '')
        
        # 尝试设置 PYTHONPATH
        python_paths = [p for p in possible_paths if os.path.exists(p)]
        if python_paths:
            os.environ['PYTHONPATH'] = os.pathsep.join(python_paths) + os.pathsep + os.environ.get('PYTHONPATH', '')

# 调用设置
setup_win32_imports()

# 现在尝试导入 win32 模块，使用更灵活的方式
win32_modules_available = False
try:
    # 尝试各种导入方式
    try:
        import win32api
        import win32con
        import win32gui
        import win32process
        win32_modules_available = True
    except ImportError:
        try:
            # 尝试从 win32ctypes 导入
            import win32ctypes.pywin32.win32api as win32api
            import win32ctypes.pywin32.win32con as win32con
            import win32ctypes.pywin32.win32gui as win32gui
            import win32ctypes.pywin32.win32process as win32process
            win32_modules_available = True
        except ImportError:
            # 最后尝试
            import ctypes
            # 创建简单的包装器
            class Win32Wrapper:
                @staticmethod
                def MessageBox(hWnd, text, caption, type):
                    return ctypes.windll.user32.MessageBoxW(hWnd, text, caption, type)
            
            win32api = Win32Wrapper()
except Exception as e:
    print(f"Warning: Failed to import win32 modules: {e}")

# 如果某些模块不可用，创建占位符
if not win32_modules_available:
    # 创建简单的替代实现
    class Win32Fallback:
        def __getattr__(self, name):
            return lambda *args, **kwargs: None
    
    win32api = Win32Fallback()
    win32con = Win32Fallback()
    win32gui = Win32Fallback()
    win32process = Win32Fallback()

# 禁用 PyInstaller 时间戳设置
def disable_pyinstaller_timestamp():
    """禁用 PyInstaller 的时间戳设置"""
    try:
        import PyInstaller.utils.win32.versioninfo
        PyInstaller.utils.win32.versioninfo.SetVersion = lambda *args, **kwargs: None
    except ImportError:
        pass

def disable_timestamp_check():
    if getattr(sys, 'frozen', False):
        try:
            import PyInstaller.utils.win32.versioninfo
            PyInstaller.utils.win32.versioninfo.SetVersion = lambda *args, **kwargs: None
        except ImportError:
            pass

# 在程序开始处调用
disable_pyinstaller_timestamp()
disable_timestamp_check()
    



import shutil
import glob
import datetime
import pinyin
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QLineEdit, QTabWidget, QMessageBox,
                             QFileDialog, QGroupBox, QScrollArea, QSizePolicy, QSpacerItem,
                             QMenu, QTableWidget, QTableWidgetItem, QDialog, QLayout,
                             QCheckBox, QComboBox, QInputDialog, QToolButton,
                             QSpinBox, QListWidget, QListWidgetItem, QTextEdit) 
from PySide6.QtCore import Qt, QSize, QSettings, QTimer, QRect, QPoint, Signal, QThread, QObject
from PySide6.QtGui import QIcon, QColor, QTextCursor, QTextCharFormat, QFont, QPixmap, QKeySequence, QPalette, QAction, QCursor
from PIL import Image, ImageDraw, ImageFont
import sqlite3
import win32api
import win32con
import win32process
import win32gui
from typing import Optional, List, Tuple, Dict, Any

# 程序基目录：打包后为 exe 所在目录，源码运行为本文件所在目录（资源/缓存统一用此定位，Nuitka 打包后 __file__ 不可靠）
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class ProjectInfo:
    """项目信息元数据（集中管理所有项目相关信息）"""
    VERSION = "3.17"
    BUILD_DATE = "2026-08-19"
    AUTHOR = "杜玛"
    LICENSE = "MIT"
    COPYRIGHT = "© 永久 杜玛"
    URL = "https://github.com/duma520"
    MAINTAINER_EMAIL = "不提供"
    NAME = "程序启动器"
    DESCRIPTION = "程序启动器，基于PySide6的桌面应用程序"
    HELP_TEXT = """
使用说明:
1. 搜索功能: 在顶部搜索框中输入关键词可以快速查找分组或按钮
2. 批量操作: 右键按钮可以选择批量操作
3. 启动参数: 编辑按钮时可以设置启动参数和工作目录
4. 管理员权限: 可以设置以管理员权限运行程序
5. 图标支持: 自动提取exe图标或自定义图标
6. 收藏功能: 可以将常用程序置顶
"""

    @classmethod
    def get_metadata(cls) -> dict:
        """获取主要元数据字典"""
        return {
            'version': cls.VERSION,
            'author': cls.AUTHOR,
            'license': cls.LICENSE,
            'url': cls.URL
        }

    @classmethod
    def get_header(cls) -> str:
        """生成标准化的项目头信息"""
        return f"{cls.NAME} {cls.VERSION} | {cls.LICENSE} License | {cls.URL}"

# 马卡龙色系定义
class MacaronColors:
    # 粉色系
    SAKURA_PINK = QColor(255, 183, 206)  # 樱花粉
    ROSE_PINK = QColor(255, 154, 162)    # 玫瑰粉
    
    # 蓝色系
    SKY_BLUE = QColor(162, 225, 246)    # 天空蓝
    LILAC_MIST = QColor(230, 230, 250)   # 淡丁香
    
    # 绿色系
    MINT_GREEN = QColor(181, 234, 215)   # 薄荷绿
    APPLE_GREEN = QColor(212, 241, 199)  # 苹果绿
    
    # 黄色/橙色系
    LEMON_YELLOW = QColor(255, 234, 165) # 柠檬黄
    BUTTER_CREAM = QColor(255, 248, 184) # 奶油黄
    PEACH_ORANGE = QColor(255, 218, 193) # 蜜桃橙
    
    # 紫色系
    LAVENDER = QColor(199, 206, 234)     # 薰衣草紫
    TARO_PURPLE = QColor(216, 191, 216)  # 香芋紫
    
    # 中性色
    CARAMEL_CREAM = QColor(240, 230, 221) # 焦糖奶霜

class FlowLayout(QLayout):
    """自定义流式布局，实现从左到右、自动换行的布局效果"""
    def __init__(self, parent=None, margin=10, spacing=10):
        super().__init__(parent)
        self._items = []
        self._margin = margin
        self._spacing = spacing

    def addItem(self, item):
        self._items.append(item)

    def count(self):
        return len(self._items)

    def itemAt(self, index):
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def expandingDirections(self):
        return Qt.Orientations(Qt.Orientation(0))

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._doLayout(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._doLayout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        margin = self._margin
        return QSize(size.width() + 2 * margin, size.height() + 2 * margin)

    def _doLayout(self, rect, test_only):
        margin = self._margin
        spacing = self._spacing
        x = rect.x() + margin
        y = rect.y() + margin
        line_height = 0
        
        for item in self._items:
            wid = item.widget()
            space_x = spacing
            space_y = spacing
            next_x = x + item.sizeHint().width() + space_x
            if next_x - space_x > rect.right() and line_height > 0:
                x = rect.x() + margin
                y = y + line_height + space_y
                next_x = x + item.sizeHint().width() + space_x
                line_height = 0
            
            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))
            
            x = next_x
            line_height = max(line_height, item.sizeHint().height())
        
        return y + line_height - rect.y()


# ===================== 图标方案配置（设置，实时自动保存 + 持久保存） =====================
_ICON_SCHEME = 1  # 当前采用的图标方案（1=方案1；2=方案2 自定义顺序；100+=用户另存的自定义方案）
_CUSTOM_SCHEME_START = 100  # 用户另存的自定义方案 id 起始

# 可调整顺序的步骤（方案2 / 自定义方案可重新排列 ①~⑤；⑥⑦为固定兜底/保险）
ICON_STEPS = {
    1: "① exe/dll 等可执行文件自带图标      → extract_exe_icon",
    2: "② 程序所在目录下自带的图标文件      → find_icon_in_directory",
    3: "③ 图标库 resource\\icons 精确匹配     → find_icon_in_library",
    4: "④ 调用 Windows 系统图标              → extract_system_icon_os",
    5: "⑤ 从 Windows 图标资源文件中提取      → extract_icon_resource",
}
# 固定兜底/保险（不可调整顺序）
ICON_TAIL = (
    "（以下两步为兜底 / 保险，顺序固定，不可调整）\n"
    "⑥ 兜底：默认图标（blank.svg）         → find_default_icon_in_library\n"
    "⑦ 最终保险：按类型生成默认图标      → generate_default_icon"
)

# 内置方案定义（order 为可调整步骤①~⑤的执行顺序）
ICON_SCHEMES = {
    1: {
        "name": "方案1：默认方案（固定顺序，推荐）",
        "order": [1, 2, 3, 4, 5],
        "editable": False,
    },
    2: {
        "name": "方案2：自定义逻辑顺序",
        "order": [1, 2, 3, 4, 5],  # 用户可在设置中调整并实时保存
        "editable": True,
    },
}


def _step_text(order: list) -> str:
    """把步骤顺序渲染为多行说明文本"""
    lines = []
    for i, s in enumerate(order, 1):
        lines.append(f"第{i}步：{ICON_STEPS.get(s, f'步骤{s}')}")
    return "\n".join(lines)


def get_icon_scheme() -> int:
    """获取当前图标方案编号"""
    return _ICON_SCHEME


def set_icon_scheme(scheme: int) -> None:
    """设置当前图标方案（实时自动保存，持久化）"""
    global _ICON_SCHEME
    if scheme in ICON_SCHEMES:
        _ICON_SCHEME = scheme
        save_icon_scheme()


def get_scheme_order(scheme: int) -> list:
    """获取方案的步骤执行顺序（①~⑤）"""
    info = ICON_SCHEMES.get(scheme)
    if info and info.get("order"):
        return list(info["order"])
    return [1, 2, 3, 4, 5]


def get_scheme_desc(scheme: int) -> str:
    """获取图标方案说明文本（名称 + 先后顺序逻辑 + 固定兜底）"""
    info = ICON_SCHEMES.get(scheme)
    if not info:
        return "（未知方案）"
    order = info.get("order", [1, 2, 3, 4, 5])
    return f"{info['name']}\n\n【采用先后顺序逻辑】\n{_step_text(order)}\n\n{ICON_TAIL}"


def set_scheme2_order(order: list) -> None:
    """更新方案2 的可调整顺序（实时自动保存，持久化）"""
    ICON_SCHEMES[2]["order"] = [s for s in order if s in ICON_STEPS]
    try:
        s = QSettings("ProgramLauncher", "Settings")
        s.setValue("scheme2_order", json.dumps(ICON_SCHEMES[2]["order"]))
    except Exception:
        pass


def add_custom_scheme(name: str, order: list) -> int:
    """把自定义后的方案另存为新方案（持久化），返回新方案 id"""
    sid = _CUSTOM_SCHEME_START
    while sid in ICON_SCHEMES:
        sid += 1
    ICON_SCHEMES[sid] = {
        "name": name,
        "order": [s for s in order if s in ICON_STEPS],
        "editable": True,
        "custom": True,
    }
    _save_custom_schemes()
    return sid


def update_custom_scheme(scheme: int, name: str = None, order: list = None) -> None:
    """更新已另存的自定义方案（顺序或名称，实时自动保存）"""
    info = ICON_SCHEMES.get(scheme)
    if not info or not info.get("custom"):
        return
    if name:
        info["name"] = name
    if order:
        info["order"] = [s for s in order if s in ICON_STEPS]
    _save_custom_schemes()


def _save_custom_schemes() -> None:
    """持久化所有用户另存的自定义方案"""
    try:
        customs = [
            {"name": info["name"], "order": info.get("order", [1, 2, 3, 4, 5])}
            for sid, info in ICON_SCHEMES.items() if sid >= _CUSTOM_SCHEME_START
        ]
        s = QSettings("ProgramLauncher", "Settings")
        s.setValue("custom_schemes", json.dumps(customs, ensure_ascii=False))
    except Exception:
        pass


def load_icon_scheme() -> None:
    """启动时加载图标方案设置（QSettings 持久化）"""
    global _ICON_SCHEME
    try:
        s = QSettings("ProgramLauncher", "Settings")
        # 方案2 的自定义顺序
        try:
            o = json.loads(s.value("scheme2_order", "[1,2,3,4,5]"))
            if isinstance(o, list) and o:
                ICON_SCHEMES[2]["order"] = [x for x in o if x in ICON_STEPS]
        except Exception:
            pass
        # 用户另存的自定义方案
        try:
            customs = json.loads(s.value("custom_schemes", "[]"))
            if isinstance(customs, list):
                for i, c in enumerate(customs):
                    sid = _CUSTOM_SCHEME_START + i
                    ICON_SCHEMES[sid] = {
                        "name": str(c.get("name", f"自定义方案{i + 1}")),
                        "order": [x for x in c.get("order", [1, 2, 3, 4, 5]) if x in ICON_STEPS],
                        "editable": True,
                        "custom": True,
                    }
        except Exception:
            pass
        # 当前选中的方案
        val = int(s.value("icon_scheme", 1))
        _ICON_SCHEME = val if val in ICON_SCHEMES else 1
    except Exception:
        _ICON_SCHEME = 1


def save_icon_scheme() -> None:
    """保存当前选中的图标方案（QSettings 持久化）"""
    try:
        s = QSettings("ProgramLauncher", "Settings")
        s.setValue("icon_scheme", _ICON_SCHEME)
    except Exception:
        pass


class DynamicIconGenerator:
    @staticmethod
    def generate_icon(text: str = "APP", size: Tuple[int, int] = (64, 64)) -> str:
        """动态生成ICO图标文件"""
        # 创建图像
        img = Image.new('RGB', size, (70, 130, 180))  # 蓝色背景
        draw = ImageDraw.Draw(img)
        
        try:
            # 尝试使用系统字体
            font = ImageFont.truetype("arial.ttf", 20)
        except:
            # 回退到默认字体
            font = ImageFont.load_default()
        
        # 计算文本位置 (兼容新旧Pillow版本)
        try:
            # 新版本Pillow使用textbbox
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
        except AttributeError:
            # 旧版本Pillow使用textsize
            text_width, text_height = draw.textsize(text, font)
        
        position = ((size[0] - text_width) // 2, (size[1] - text_height) // 2)
        
        # 绘制文本
        draw.text(position, text, fill=(255, 255, 255), font=font)
        
        # 保存为ICO文件
        ico_path = "icon.ico"
        img.save(ico_path, sizes=[size])
        return ico_path

    @staticmethod
    def extract_exe_icon(exe_path: str, output_path: str = None) -> Optional[str]:
        """从exe文件中提取图标（改进版）"""
        try:
            import win32ui

            if not os.path.exists(exe_path):
                return None

            if not output_path:
                # 使用绝对路径
                output_dir = os.path.abspath(os.path.join(BASE_DIR, "temp_icons"))
                if not os.path.exists(output_dir):
                    os.makedirs(output_dir)
                output_path = os.path.abspath(os.path.join(output_dir, f"{os.path.basename(exe_path)}_{hash(exe_path)}.ico"))
            
            # 方法1: 使用win32gui.ExtractIconEx
            try:
                large, small = win32gui.ExtractIconEx(exe_path, 0)
                
                if large:
                    icon = large[0]
                    hdc = win32ui.CreateDCFromHandle(win32gui.GetDC(0))
                    hbmp = win32ui.CreateBitmap()
                    hbmp.CreateCompatibleBitmap(hdc, 32, 32)
                    hdc = hdc.CreateCompatibleDC()
                    hdc.SelectObject(hbmp)
                    hdc.DrawIcon((0, 0), icon)
                    hbmp.SaveBitmapFile(hdc, output_path)
                    win32gui.DestroyIcon(icon)
                    return output_path
            except Exception:
                pass
            
            # 方法2: 使用Pillow提取
            try:
                from PIL import Image
                ico_x = win32gui.ExtractIcon(exe_path, 0)
                
                if ico_x:
                    hdc = win32ui.CreateDCFromHandle(win32gui.GetDC(0))
                    hbmp = win32ui.CreateBitmap()
                    hbmp.CreateCompatibleBitmap(hdc, 32, 32)
                    hdc = hdc.CreateCompatibleDC()
                    hdc.SelectObject(hbmp)
                    hdc.DrawIcon((0, 0), ico_x)
                    bmpinfo = hbmp.GetInfo()
                    bmpstr = hbmp.GetBitmapBits(True)
                    img = Image.frombuffer(
                        'RGB',
                        (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
                        bmpstr, 'raw', 'BGRX', 0, 1
                    )
                    img.save(output_path)
                    win32gui.DestroyIcon(ico_x)
                    return output_path
            except Exception:
                pass
            
            # 方法3: 使用Shell API
            try:
                import ctypes
                from ctypes import wintypes
                SHGFI_ICON = 0x000000100
                SHGFI_LARGEICON = 0x000000000
                SHGFI_SMALLICON = 0x000000001
                
                class SHFILEINFO(ctypes.Structure):
                    _fields_ = [
                        ('hIcon', ctypes.c_void_p),
                        ('iIcon', ctypes.c_int),
                        ('dwAttributes', ctypes.c_uint),
                        ('szDisplayName', ctypes.c_wchar * 260),
                        ('szTypeName', ctypes.c_wchar * 80)
                    ]
                
                shell32 = ctypes.windll.shell32
                info = SHFILEINFO()
                res = shell32.SHGetFileInfoW(
                    exe_path, 0, ctypes.byref(info), 
                    ctypes.sizeof(info), 
                    SHGFI_ICON | SHGFI_LARGEICON
                )
                
                if info.hIcon:
                    import win32ui
                    hdc = win32ui.CreateDCFromHandle(win32gui.GetDC(0))
                    hbmp = win32ui.CreateBitmap()
                    hbmp.CreateCompatibleBitmap(hdc, 32, 32)
                    hdc = hdc.CreateCompatibleDC()
                    hdc.SelectObject(hbmp)
                    hdc.DrawIcon((0, 0), info.hIcon)
                    hbmp.SaveBitmapFile(hdc, output_path)
                    win32gui.DestroyIcon(info.hIcon)
                    return output_path
            except Exception:
                pass
            
            # 方法4: 使用系统默认图标
            try:
                from win32com.shell import shell, shellcon
                from win32com.shell.shell import SHGetFileInfo
                flags = shellcon.SHGFI_ICON | shellcon.SHGFI_LARGEICON
                info = SHGetFileInfo(exe_path, 0, flags)
                
                if info[0]:
                    icon = info[0]
                    hdc = win32ui.CreateDCFromHandle(win32gui.GetDC(0))
                    hbmp = win32ui.CreateBitmap()
                    hbmp.CreateCompatibleBitmap(hdc, 32, 32)
                    hdc = hdc.CreateCompatibleDC()
                    hdc.SelectObject(hbmp)
                    hdc.DrawIcon((0, 0), icon)
                    hbmp.SaveBitmapFile(hdc, output_path)
                    win32gui.DestroyIcon(icon)
                    return output_path
            except Exception:
                pass
            
            return None
        
        except Exception:
            return None



    @staticmethod
    def find_icon_in_directory(directory: str) -> Optional[str]:
        """在指定目录下查找图标文件"""
        if not os.path.isdir(directory):
            return None
        
        # 查找常见的图标文件
        icon_patterns = ["icon.*", "*.ico"]
        for pattern in icon_patterns:
            files = glob.glob(os.path.join(directory, pattern))
            if files:
                # 优先返回.ico文件
                ico_files = [f for f in files if f.lower().endswith('.ico')]
                if ico_files:
                    return ico_files[0]
                return files[0]  # 返回找到的第一个匹配文件
        
        return None

    @staticmethod
    def find_icon_in_library(path: str) -> Optional[str]:
        """方案2（精确匹配）：从现成图标库 resource/icons 中按类型查找图标

        图标库位于程序当前目录的子目录 resource\icons（只读，不写入）：
        - classic\ : 按扩展名命名的图标库（如 exe.svg / pdf.svg / folder.svg / default.svg / blank.svg）
        - extra\   : 文件夹系列图标（folder-*.svg，更丰富）

        仅做**精确匹配**：目录 → extra\folder.svg（回退 classic\folder.svg）；
        文件 → classic\<扩展名>.svg；无精确匹配一律返回 None。
        （注意：不要在这里回退 default/blank，否则链路中后续的"Windows 系统图标"步骤永远不会执行；
        默认图标兜底由 find_default_icon_in_library 负责）
        """
        base = os.path.join(BASE_DIR, "resource", "icons")
        classic_dir = os.path.join(base, "classic")
        extra_dir = os.path.join(base, "extra")

        # 目录：优先 extra 文件夹图标，回退 classic
        if os.path.isdir(path):
            for d in (extra_dir, classic_dir):
                candidate = os.path.join(d, "folder.svg")
                if os.path.exists(candidate):
                    return candidate
            return None

        # 文件：按扩展名精确匹配 classic 图标库
        ext = os.path.splitext(path)[1].lower().lstrip('.')
        if ext:
            candidate = os.path.join(classic_dir, f"{ext}.svg")
            if os.path.exists(candidate):
                return candidate
        return None

    @staticmethod
    def find_default_icon_in_library(path: str) -> Optional[str]:
        """兜底：无图标时的默认图标（直接用图标库默认图标，不做"最相似"归并）

        - 目录 → extra\folder.svg（回退 classic\folder.svg）
        - 文件 → ① 先精确匹配 classic\<扩展名>.svg（有专属图标用专属）
                ② 无专属图标 → classic\blank.svg（再退 default.svg）
        仍无 → 返回 None
        """
        base = os.path.join(BASE_DIR, "resource", "icons")
        classic_dir = os.path.join(base, "classic")
        extra_dir = os.path.join(base, "extra")

        # 目录：文件夹图标
        if os.path.isdir(path):
            for d in (extra_dir, classic_dir):
                candidate = os.path.join(d, "folder.svg")
                if os.path.exists(candidate):
                    return candidate

        # 文件：优先专属图标，其次默认图标
        ext = os.path.splitext(path)[1].lower().lstrip('.')
        if ext:
            candidate = os.path.join(classic_dir, f"{ext}.svg")
            if os.path.exists(candidate):
                return candidate

        # 默认图标：blank.svg 优先，default.svg 备用
        for name in ("blank.svg", "default.svg"):
            candidate = os.path.join(classic_dir, name)
            if os.path.exists(candidate):
                return candidate
        return None

    @staticmethod
    def find_icon_auto(path: str, name: str = "") -> Optional[str]:
        """按用户选择的图标方案自动获取图标（设置中可选）

        方案1：固定顺序；方案2 / 用户另存的自定义方案：自定义①~⑤顺序（⑥⑦固定兜底）。
        """
        order = get_scheme_order(get_icon_scheme())
        return DynamicIconGenerator._find_icon_by_order(path, name, order)

    @staticmethod
    def _find_icon_by_order(path: str, name: str, order: list) -> Optional[str]:
        """按指定步骤顺序执行①~⑤；⑥兜底 / ⑦保险固定在后"""
        for step in order:
            icon = DynamicIconGenerator._exec_icon_step(path, step)
            if icon:
                return icon
        # ⑥ 兜底：默认图标（固定，blank.svg/default.svg）
        icon = DynamicIconGenerator.find_default_icon_in_library(path)
        if icon:
            return icon
        # ⑦ 最终保险：按类型生成默认图标（固定）
        return DynamicIconGenerator.generate_default_icon(path, name)

    @staticmethod
    def _exec_icon_step(path: str, step: int) -> Optional[str]:
        """执行单个图标步骤（①~⑤），失败返回 None"""
        try:
            if step == 1:
                # ① 仅对含内嵌图标资源的文件（exe/dll 等）；.bat/.cmd 是文本无图标资源，交由 ③ 图标库 bat.svg/cmd.svg
                ext = os.path.splitext(path)[1].lower() if not os.path.isdir(path) else ""
                if ext in ('.exe', '.dll', '.com', '.msi', '.ocx', '.sys', '.scr', '.pif', '.app'):
                    return DynamicIconGenerator.extract_exe_icon(path)
            elif step == 2:
                if not os.path.isdir(path):
                    d = os.path.dirname(path)
                    if d:
                        return DynamicIconGenerator.find_icon_in_directory(d)
            elif step == 3:
                return DynamicIconGenerator.find_icon_in_library(path)
            elif step == 4:
                return DynamicIconGenerator.extract_system_icon_os(path)
            elif step == 5:
                return DynamicIconGenerator.extract_icon_resource(path)
        except Exception:
            pass
        return None

    @staticmethod
    def _resolve_lnk_path(lnk_path: str) -> str:
        """解析.lnk快捷方式的目标路径（兼容Nuitka打包环境）"""
        # 先尝试 pythoncom 方式（非 frozen 环境）
        if not getattr(sys, 'frozen', False):
            try:
                import pythoncom
                from win32com.shell import shell
                pythoncom.CoInitialize()
                shortcut = pythoncom.CoCreateInstance(
                    shell.CLSID_ShellLink, None,
                    pythoncom.CLSCTX_INPROC_SERVER, shell.IID_IShellLink)
                shortcut.QueryInterface(pythoncom.IID_IPersistFile).Load(lnk_path)
                target = shortcut.GetPath(shell.SLGP_UNCPRIORITY)[0]
                if target and os.path.exists(target):
                    return target
            except Exception:
                pass
        
        # ctypes 回退方案（Nuitka frozen 环境兼容）
        try:
            import ctypes
            from ctypes import wintypes
            
            # COM GUIDs
            CLSID_ShellLink = bytes([
                0x01,0x14,0x02,0x00,0x00,0x00,0x00,0x00,
                0xC0,0x00,0x00,0x00,0x00,0x00,0x00,0x46])
            IID_IShellLinkW = bytes([
                0xF9,0x14,0x02,0x00,0x00,0x00,0x00,0x00,
                0xC0,0x00,0x00,0x00,0x00,0x00,0x00,0x46])
            IID_IPersistFile = bytes([
                0x0b,0x01,0x00,0x00,0x00,0x00,0x00,0x00,
                0xC0,0x00,0x00,0x00,0x00,0x00,0x00,0x46])
            
            ole32 = ctypes.windll.ole32
            
            # IShellLinkW vtable 函数指针
            # IUnknown: QueryInterface(0), AddRef(1), Release(2)
            # IShellLinkW: GetPath(3), GetIDList(4), SetIDList(5), ...
            
            pSl = ctypes.c_void_p()
            hr = ole32.CoCreateInstance(
                ctypes.create_string_buffer(CLSID_ShellLink, 16), None, 1,  # CLSCTX_INPROC_SERVER
                ctypes.create_string_buffer(IID_IShellLinkW, 16),
                ctypes.byref(pSl))
            
            if hr != 0 or not pSl:
                return lnk_path
            
            # QueryInterface for IPersistFile (通过 IShellLinkW 的 vtable)
            vtable = ctypes.cast(pSl, ctypes.POINTER(ctypes.c_void_p)).contents
            vtable = ctypes.cast(vtable, ctypes.POINTER(ctypes.c_void_p))
            
            # IUnknown::QueryInterface
            pPf = ctypes.c_void_p()
            QueryInterface = ctypes.cast(vtable[0], ctypes.CFUNCTYPE(
                ctypes.c_long, ctypes.c_void_p,
                ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)))
            hr = QueryInterface(pSl, ctypes.create_string_buffer(IID_IPersistFile, 16), ctypes.byref(pPf))
            
            if hr != 0 or not pPf:
                vtable2 = ctypes.cast(pSl, ctypes.POINTER(ctypes.c_void_p)).contents
                vtable2 = ctypes.cast(vtable2, ctypes.POINTER(ctypes.c_void_p))
                Release = ctypes.cast(vtable2[2], ctypes.CFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p))
                Release(pSl)
                return lnk_path
            
            # IPersistFile::Load
            pf_vtable = ctypes.cast(pPf, ctypes.POINTER(ctypes.c_void_p)).contents
            pf_vtable = ctypes.cast(pf_vtable, ctypes.POINTER(ctypes.c_void_p))
            Load = ctypes.cast(pf_vtable[5], ctypes.CFUNCTYPE(
                ctypes.c_long, ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_uint))
            hr = Load(pPf, lnk_path, 0)
            
            if hr != 0:
                return lnk_path
            
            # IShellLinkW::GetPath
            GetPath = ctypes.cast(vtable[3], ctypes.CFUNCTYPE(
                ctypes.c_long, ctypes.c_void_p, ctypes.c_wchar_p,
                ctypes.c_int, ctypes.c_void_p, ctypes.c_uint))
            
            buf = ctypes.create_unicode_buffer(260)
            hr = GetPath(pSl, buf, 260, None, 0)  # SLGP_UNCPRIORITY = 0
            
            # Release interfaces
            pf_vtable2 = ctypes.cast(pPf, ctypes.POINTER(ctypes.c_void_p)).contents
            pf_vtable2 = ctypes.cast(pf_vtable2, ctypes.POINTER(ctypes.c_void_p))
            Release2 = ctypes.cast(pf_vtable2[2], ctypes.CFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p))
            Release2(pPf)
            
            vtable3 = ctypes.cast(pSl, ctypes.POINTER(ctypes.c_void_p)).contents
            vtable3 = ctypes.cast(vtable3, ctypes.POINTER(ctypes.c_void_p))
            Release3 = ctypes.cast(vtable3[2], ctypes.CFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p))
            Release3(pSl)
            
            if hr == 0 and buf.value and os.path.exists(buf.value):
                return buf.value
                
        except Exception:
            pass
        
        return lnk_path  # 解析失败返回原路径
    
    @staticmethod
    def extract_icon_resource(path: str, output_path: str = None) -> Optional[str]:
        """步骤⑤：从 Windows 图标资源文件中提取（win32gui.ExtractIconEx，适用于 .exe/.dll 等含内嵌图标的文件）"""
        if not os.path.exists(path):
            return None
        if output_path is None:
            output_dir = os.path.abspath(os.path.join(BASE_DIR, "temp_icons"))
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            output_path = os.path.abspath(os.path.join(
                output_dir, f"sysicon_{hash(path)}_{os.path.basename(path)}.ico"))
        if os.path.exists(output_path):
            return output_path
        actual_path = path
        if path.lower().endswith('.lnk'):
            try:
                actual_path = DynamicIconGenerator._resolve_lnk_path(path)
            except Exception:
                pass
        try:
            import win32ui
            large, small = win32gui.ExtractIconEx(actual_path, 0)
            if large:
                icon = large[0]
                hdc = win32ui.CreateDCFromHandle(win32gui.GetDC(0))
                hbmp = win32ui.CreateBitmap()
                hbmp.CreateCompatibleBitmap(hdc, 32, 32)
                hdc = hdc.CreateCompatibleDC()
                hdc.SelectObject(hbmp)
                hdc.DrawIcon((0, 0), icon)
                hbmp.SaveBitmapFile(hdc, output_path)
                for ic in large:
                    win32gui.DestroyIcon(ic)
                for ic in small:
                    win32gui.DestroyIcon(ic)
                return output_path
        except Exception:
            pass
        return None

    @staticmethod
    def extract_system_icon_os(path: str, output_path: str = None) -> Optional[str]:
        """步骤④：调用 Windows 系统图标（SHGetFileInfo，适用于任意文件类型）"""
        if not os.path.exists(path):
            return None
        if output_path is None:
            output_dir = os.path.abspath(os.path.join(BASE_DIR, "temp_icons"))
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            output_path = os.path.abspath(os.path.join(
                output_dir, f"sysicon_{hash(path)}_{os.path.basename(path)}.ico"))
        if os.path.exists(output_path):
            return output_path
        actual_path = path
        if path.lower().endswith('.lnk'):
            try:
                actual_path = DynamicIconGenerator._resolve_lnk_path(path)
            except Exception:
                pass
        # win32com.shell.SHGetFileInfo
        try:
            import pythoncom
            from win32com.shell import shell, shellcon
            flags = shellcon.SHGFI_ICON | shellcon.SHGFI_LARGEICON
            ret, info = shell.SHGetFileInfo(actual_path, 0, flags)
            if ret and len(info) > 0 and info[0]:
                import win32ui
                icon = info[0]
                hdc = win32ui.CreateDCFromHandle(win32gui.GetDC(0))
                hbmp = win32ui.CreateBitmap()
                hbmp.CreateCompatibleBitmap(hdc, 32, 32)
                hdc = hdc.CreateCompatibleDC()
                hdc.SelectObject(hbmp)
                hdc.DrawIcon((0, 0), icon)
                hbmp.SaveBitmapFile(hdc, output_path)
                win32gui.DestroyIcon(icon)
                return output_path
        except Exception:
            pass
        # ctypes SHGetFileInfoW（兼容性最好）
        try:
            import ctypes
            from ctypes import wintypes
            SHGFI_ICON = 0x100
            SHGFI_LARGEICON = 0
            class SHFILEINFO(ctypes.Structure):
                _fields_ = [
                    ('hIcon', wintypes.HICON),
                    ('iIcon', ctypes.c_int),
                    ('dwAttributes', ctypes.c_uint),
                    ('szDisplayName', ctypes.c_wchar * 260),
                    ('szTypeName', ctypes.c_wchar * 80)
                ]
            shell32 = ctypes.windll.shell32
            info = SHFILEINFO()
            result = shell32.SHGetFileInfoW(
                actual_path, 0, ctypes.byref(info),
                ctypes.sizeof(info), SHGFI_ICON | SHGFI_LARGEICON
            )
            if result and info.hIcon:
                import win32ui
                hdc = win32ui.CreateDCFromHandle(win32gui.GetDC(0))
                hbmp = win32ui.CreateBitmap()
                hbmp.CreateCompatibleBitmap(hdc, 32, 32)
                hdc = hdc.CreateCompatibleDC()
                hdc.SelectObject(hbmp)
                hdc.DrawIcon((0, 0), info.hIcon)
                hbmp.SaveBitmapFile(hdc, output_path)
                win32gui.DestroyIcon(info.hIcon)
                return output_path
        except Exception:
            pass
        return None

    @staticmethod
    def extract_system_icon(path: str, output_path: str = None) -> Optional[str]:
        """合并获取（兼容）：⑤资源提取 → ④系统图标（原 extract_system_icon 行为）"""
        r = DynamicIconGenerator.extract_icon_resource(path, output_path)
        if r:
            return r
        return DynamicIconGenerator.extract_system_icon_os(path, output_path)

    @staticmethod
    def generate_default_icon(path: str, name: str = "", output_dir: str = None) -> str:
        """根据路径类型自动生成默认图标
        
        - 目录: 黄色文件夹图标
        - *.exe/*.com: 蓝色程序图标
        - 其他文件: 根据扩展名生成不同颜色图标
        """
        if output_dir is None:
            output_dir = os.path.join(BASE_DIR, "icons", "auto")
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # 生成唯一文件名
        icon_name = f"auto_{hash(path)}_{os.path.basename(path)}.ico"
        output_path = os.path.join(output_dir, icon_name)
        
        # 如果已经生成过，直接返回
        if os.path.exists(output_path):
            return output_path
        
        size = (64, 64)
        ext = os.path.splitext(path)[1].lower() if not os.path.isdir(path) else ""
        
        # 根据文件类型选择颜色和标签
        if os.path.isdir(path):
            bg_color = (255, 200, 50)    # 金黄色 - 文件夹
            label = "DIR"
            icon_symbol = "📁"
        elif ext in ('.exe', '.com', '.bat', '.cmd', '.msi'):
            bg_color = (52, 120, 220)    # 蓝色 - 可执行程序
            label = ext.upper().lstrip('.')[:3]
            icon_symbol = "▶"
        elif ext in ('.txt', '.md', '.doc', '.docx', '.pdf', '.xls', '.xlsx', '.ppt', '.pptx', '.csv', '.log'):
            bg_color = (80, 80, 80)      # 深灰色 - 文档
            label = "DOC"
            icon_symbol = "📄"
        elif ext in ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.ico', '.webp', '.tiff'):
            bg_color = (200, 80, 160)    # 紫红色 - 图片
            label = "IMG"
            icon_symbol = "🖼"
        elif ext in ('.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma', '.m4a'):
            bg_color = (80, 180, 80)     # 绿色 - 音频
            label = "AUD"
            icon_symbol = "🎵"
        elif ext in ('.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm'):
            bg_color = (220, 120, 40)    # 橙色 - 视频
            label = "VID"
            icon_symbol = "🎬"
        elif ext in ('.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz', '.cab'):
            bg_color = (180, 140, 80)    # 棕色 - 压缩包
            label = "ZIP"
            icon_symbol = "📦"
        elif ext in ('.py', '.pyw', '.pyc'):
            bg_color = (48, 105, 152)    # Python蓝
            label = "PY"
            icon_symbol = "🐍"
        elif ext in ('.js', '.ts', '.jsx', '.tsx', '.vue'):
            bg_color = (240, 220, 50)    # 黄色 - JavaScript
            label = "JS"
            icon_symbol = "{ }"
        elif ext in ('.html', '.htm', '.css', '.scss', '.less'):
            bg_color = (228, 77, 38)     # 橙红 - Web
            label = "WEB"
            icon_symbol = "🌐"
        elif ext in ('.cpp', '.c', '.h', '.hpp', '.cs', '.java', '.go', '.rs'):
            bg_color = (100, 100, 180)   # 蓝紫 - 代码
            label = ext.upper().lstrip('.')[:3]
            icon_symbol = "< >"
        elif ext in ('.lnk', '.url'):
            bg_color = (60, 160, 200)    # 浅蓝 - 快捷方式
            label = "LNK"
            icon_symbol = "🔗"
        elif ext in ('.dll', '.sys', '.ocx'):
            bg_color = (140, 140, 160)   # 灰蓝 - 系统文件
            label = "SYS"
            icon_symbol = "⚙"
        else:
            bg_color = (100, 160, 200)   # 默认淡蓝
            label = ext.lstrip('.')[:3].upper() if ext else "FILE"
            icon_symbol = "📎"
        
        try:
            img = Image.new('RGB', size, bg_color)
            draw = ImageDraw.Draw(img)
            
            # 绘制圆角效果（简化：用稍浅颜色画内边框）
            inner_color = tuple(min(c + 30, 255) for c in bg_color)
            draw.rectangle([4, 4, 60, 60], fill=inner_color, outline=bg_color, width=2)
            
            # 尝试绘制类型标签
            try:
                font_label = ImageFont.truetype("segoeui.ttf", 16)
                font_ext = ImageFont.truetype("segoeui.ttf", 11)
            except:
                try:
                    font_label = ImageFont.truetype("arial.ttf", 16)
                    font_ext = ImageFont.truetype("arial.ttf", 11)
                except:
                    font_label = ImageFont.load_default()
                    font_ext = ImageFont.load_default()
            
            # 绘制图标符号（如果字体支持）
            if icon_symbol:
                try:
                    # 计算文本位置
                    bbox = draw.textbbox((0, 0), icon_symbol, font=font_label)
                    sw = bbox[2] - bbox[0]
                    sh = bbox[3] - bbox[1]
                    draw.text(((size[0] - sw) // 2, (size[1] - sh) // 2 - 8),
                             icon_symbol, fill=(255, 255, 255), font=font_label)
                except:
                    # 如果符号不显示，用标签替代
                    bbox = draw.textbbox((0, 0), label, font=font_label)
                    tw = bbox[2] - bbox[0]
                    th = bbox[3] - bbox[1]
                    draw.text(((size[0] - tw) // 2, (size[1] - th) // 2 - 6),
                             label, fill=(255, 255, 255), font=font_label)
            
            # 在底部绘制扩展名
            if ext and len(ext) <= 6:
                ext_text = ext.lstrip('.')[:4]
                bbox = draw.textbbox((0, 0), ext_text, font=font_ext)
                ew = bbox[2] - bbox[0]
                draw.text(((size[0] - ew) // 2, size[1] - 18),
                         ext_text, fill=(255, 255, 255), font=font_ext)
            
            img.save(output_path, sizes=[size])
            return output_path
            
        except Exception as e:
            print(f"[WARNING] 生成默认图标失败: {e}")
            return ""

class BackupRestoreDialog(QDialog):
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.parent = parent
        self.setWindowTitle("数据库备份与恢复")
        self.resize(800, 600)

        self.init_ui()
        self.load_backups()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 操作按钮区域
        btn_layout = QHBoxLayout()
        
        self.backup_btn = QPushButton("创建手动备份")
        self.backup_btn.clicked.connect(self.create_manual_backup)
        btn_layout.addWidget(self.backup_btn)
        
        self.restore_btn = QPushButton("恢复选中备份")
        self.restore_btn.clicked.connect(self.restore_backup)
        btn_layout.addWidget(self.restore_btn)
        
        btn_layout.addStretch()
        
        # 备份数量设置
        self.count_label = QLabel("保留备份数量:")
        btn_layout.addWidget(self.count_label)
        
        self.count_spin = QSpinBox()
        self.count_spin.setRange(1, 100)
        self.count_spin.setValue(self.db_manager.backup_count)
        self.count_spin.valueChanged.connect(self.update_backup_count)
        btn_layout.addWidget(self.count_spin)
        
        layout.addLayout(btn_layout)
        
        # 备份列表表格
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["选择", "备份时间", "类型", "大小", "数据库版本"])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSortingEnabled(True)
        
        # 设置列宽
        self.table.setColumnWidth(0, 50)
        self.table.setColumnWidth(1, 150)
        self.table.setColumnWidth(2, 80)
        self.table.setColumnWidth(3, 100)
        
        layout.addWidget(self.table)
        
        # 筛选区域
        filter_layout = QHBoxLayout()
        
        self.type_filter = QComboBox()
        self.type_filter.addItem("所有类型", "")
        self.type_filter.addItem("自动备份", "auto")
        self.type_filter.addItem("手动备份", "manual")
        self.type_filter.addItem("恢复前", "restore_pre")
        self.type_filter.currentIndexChanged.connect(self.load_backups)
        filter_layout.addWidget(self.type_filter)
        
        self.date_filter = QComboBox()
        self.date_filter.addItem("所有时间", "")
        self.date_filter.addItem("今天", "today")
        self.date_filter.addItem("最近7天", "week")
        self.date_filter.addItem("最近30天", "month")
        self.date_filter.currentIndexChanged.connect(self.load_backups)
        filter_layout.addWidget(self.date_filter)
        
        filter_layout.addStretch()
        layout.addLayout(filter_layout)
        
        self.setLayout(layout)
    
    def load_backups(self):
        """加载备份列表"""
        try:
            self.table.setRowCount(0)
            backups = self.db_manager.get_backup_files()
            
            if not backups:
                QMessageBox.information(self, "信息", "没有找到备份文件")
                return
                
            # 应用筛选
            filter_type = self.type_filter.currentData()
            filter_date = self.date_filter.currentData()
            today = datetime.datetime.now().date()
            
            valid_backups = 0
            
            for backup in backups:
                if not os.path.exists(backup):
                    continue
                    
                info = self.db_manager.get_backup_info(backup)
                if not info:
                    continue
                    
                # 类型筛选
                if filter_type and filter_type not in info["type"]:
                    continue
                    
                # 日期筛选
                if filter_date:
                    backup_date = info["time"].date()
                    
                    if filter_date == "today" and backup_date != today:
                        continue
                    elif filter_date == "week" and (today - backup_date).days > 7:
                        continue
                    elif filter_date == "month" and (today - backup_date).days > 30:
                        continue
                        
                self.add_backup_row(info)
                valid_backups += 1
                
            self.table.sortByColumn(1, Qt.DescendingOrder)
            
            if valid_backups == 0:
                QMessageBox.information(self, "信息", "没有匹配筛选条件的备份文件")
                
        except Exception as e:
            print(f"[ERROR] Failed to load backups: {str(e)}")
            QMessageBox.warning(self, "错误", f"加载备份失败: {str(e)}")


    
    def add_backup_row(self, info):
        """添加备份行到表格"""
        try:
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            # 选择框
            check = QCheckBox()
            check.setChecked(False)
            cell = QWidget()
            layout = QHBoxLayout(cell)
            layout.addWidget(check)
            layout.setAlignment(Qt.AlignCenter)
            layout.setContentsMargins(0, 0, 0, 0)
            self.table.setCellWidget(row, 0, cell)
            
            # 备份时间
            time_item = QTableWidgetItem(info["time"].strftime("%Y-%m-%d %H:%M:%S"))
            time_item.setData(Qt.UserRole, info["path"])  # 存储完整路径
            self.table.setItem(row, 1, time_item)
            
            # 备份类型
            type_text = {
                "auto": "自动",
                "manual": "手动",
                "restore_pre": "恢复前",
            }.get(info["type"], info["type"])
            self.table.setItem(row, 2, QTableWidgetItem(type_text))
            
            # 文件大小
            size_str = ""
            try:
                if info['size'] < 1024:
                    size_str = f"{info['size']} B"
                elif info['size'] < 1024*1024:
                    size_str = f"{info['size']/1024:.1f} KB"
                else:
                    size_str = f"{info['size']/1024/1024:.1f} MB"
            except:
                size_str = "N/A"
            self.table.setItem(row, 3, QTableWidgetItem(size_str))
            
            # 数据库版本
            version_item = QTableWidgetItem(info["version"])
            version_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 4, version_item)
            
        except Exception as e:
            print(f"[ERROR] Failed to add backup row: {str(e)}")

    
    def create_manual_backup(self):
        """创建手动备份"""
        backup_path = self.db_manager.create_backup(backup_type="manual")
        if backup_path:
            QMessageBox.information(self, "成功", f"已创建手动备份:\n{backup_path}")
            self.load_backups()
        else:
            QMessageBox.warning(self, "失败", "创建备份失败")
    
    def restore_backup(self):
        """恢复选中的备份"""
        selected = []
        for row in range(self.table.rowCount()):
            check = self.table.cellWidget(row, 0).findChild(QCheckBox)
            if check and check.isChecked():
                path = self.table.item(row, 1).data(Qt.UserRole)
                selected.append(path)
        
        if not selected:
            QMessageBox.warning(self, "警告", "请先选择要恢复的备份")
            return
            
        if len(selected) > 1:
            QMessageBox.warning(self, "警告", "一次只能恢复一个备份")
            return
            
        backup_path = selected[0]
        reply = QMessageBox.question(
            self, "确认恢复", 
            f"确定要恢复此备份吗?\n\n{backup_path}", 
            QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            if self.db_manager.restore_database(backup_path):
                QMessageBox.information(self, "成功", "恢复完成，程序将重新加载数据")
                self.parent.load_data()
                self.close()
            else:
                QMessageBox.warning(self, "失败", "恢复备份失败")
    
    def update_backup_count(self, count):
        """更新保留备份数量"""
        self.db_manager.backup_count = count



class DatabaseManager:
    def __init__(self):
        self.db_path = "launcher.db"
        self.backup_count = 30  # 默认保留30个备份
        self._init_db()
        self._init_backup_dir()
        self._init_icon_dir()
        self.conn = None
        self.last_check_time = 0

    def check_connection(self):
        """检查并确保数据库连接正常"""
        current_time = time.time()
        if current_time - self.last_check_time < 60:  # 每分钟最多检查一次
            
            return True
            
        try:
            # 尝试执行一个简单的查询来测试连接
            temp_conn = sqlite3.connect(self.db_path)
            cursor = temp_conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            temp_conn.close()
            self.last_check_time = current_time
            return True
        except sqlite3.Error as e:
            print(f"数据库连接检查失败: {str(e)}")
            return False

    def _init_backup_dir(self):
        """初始化备份目录"""
        if not os.path.exists("backups"):
            os.makedirs("backups")
    
    def backup_database(self):
        """备份数据库到backups目录（带频率限制检查）"""
        try:
            # 检查上次备份时间，避免过于频繁备份（调整为4.5分钟）
            current_time = time.time()
            if hasattr(self, 'last_backup_time') and current_time - self.last_backup_time < 270:
                # 如果距离上次备份不到4.5分钟（270秒），跳过本次备份
                return False
                
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = os.path.join("backups", f"launcher_backup_{timestamp}.db")
            shutil.copy2(self.db_path, backup_path)
            
            # 更新最后备份时间
            self.last_backup_time = current_time
            
            # 保留最多24个备份文件（因为现在是每5分钟备份，24个=2小时）
            backups = sorted(glob.glob(os.path.join("backups", "launcher_backup_*.db")))
            if len(backups) > 24:
                for old_backup in backups[:-24]:
                    try:
                        os.remove(old_backup)
                    except Exception as e:
                        print(f"删除旧备份失败: {str(e)}")
            return True
        except Exception as e:
            print(f"备份失败: {str(e)}")
            return False


            
    def _init_db(self):
        """初始化数据库"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # 创建分组表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS groups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    position INTEGER DEFAULT 0,
                    is_favorite INTEGER DEFAULT 0
                )
            """)
            # 创建按钮表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS buttons (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    group_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    path TEXT NOT NULL,
                    arguments TEXT DEFAULT '',
                    working_dir TEXT DEFAULT '',
                    run_as_admin INTEGER DEFAULT 0,
                    icon_path TEXT DEFAULT '',
                    position INTEGER DEFAULT 0,
                    is_favorite INTEGER DEFAULT 0,
                    FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE
                )
            """)
            
            # 检查并添加可能缺失的列（兼容性处理）
            columns_to_add = [
                ('groups', 'is_favorite', 'INTEGER DEFAULT 0'),
                ('buttons', 'arguments', 'TEXT DEFAULT \'\''),
                ('buttons', 'working_dir', 'TEXT DEFAULT \'\''),
                ('buttons', 'run_as_admin', 'INTEGER DEFAULT 0'),
                ('buttons', 'icon_path', 'TEXT DEFAULT \'\''),
                ('buttons', 'is_favorite', 'INTEGER DEFAULT 0')
            ]
            
            for table, column, col_type in columns_to_add:
                try:
                    cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
                except sqlite3.OperationalError:
                    pass  # 列已存在
                
            conn.commit()


    
    def add_group(self, name: str, is_favorite: bool = False) -> int:
        """添加新分组"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # 获取当前最大position值
            cursor.execute("SELECT MAX(position) FROM groups")
            max_pos = cursor.fetchone()[0] or 0
            
            cursor.execute(
                "INSERT INTO groups (name, position, is_favorite) VALUES (?, ?, ?)",
                (name, max_pos + 1, 1 if is_favorite else 0)
            )
            conn.commit()
            return cursor.lastrowid
    
    def get_groups(self) -> List[Tuple[int, str, int, int]]:
        """获取所有分组（带连接检查和重试）"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                if not self.check_connection():
                    if attempt == max_retries - 1:
                        return []  # 最后一次尝试失败返回空列表
                    time.sleep(0.5)  # 短暂等待后重试
                    continue
                    
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT id, name, position, is_favorite FROM groups ORDER BY is_favorite DESC, position")
                    return cursor.fetchall()
                    
            except sqlite3.Error as e:
                print(f"获取分组失败(尝试 {attempt + 1}/{max_retries}): {str(e)}")
                if attempt == max_retries - 1:
                    return []  # 最后一次尝试失败返回空列表
                time.sleep(0.5)  # 短暂等待后重试

    
    def update_group_name(self, group_id: int, new_name: str):
        """更新分组名称"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE groups SET name = ? WHERE id = ?",
                (new_name, group_id)
            )
            conn.commit()
    
    def toggle_group_favorite(self, group_id: int, is_favorite: bool):
        """切换分组收藏状态"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE groups SET is_favorite = ? WHERE id = ?",
                (1 if is_favorite else 0, group_id)
            )
            conn.commit()
    
    def delete_group(self, group_id: int):
        """删除分组及其所有按钮"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM groups WHERE id = ?", (group_id,))
            conn.commit()
    
    def add_button(self, group_id: int, name: str, path: str, 
                  arguments: str = '', working_dir: str = '', 
                  run_as_admin: bool = False, icon_path: str = '',
                  is_favorite: bool = False) -> int:
        """添加新按钮"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # 获取当前最大position值
            cursor.execute("SELECT MAX(position) FROM buttons WHERE group_id = ?", (group_id,))
            max_pos = cursor.fetchone()[0] or 0
            
            cursor.execute(
                """INSERT INTO buttons 
                (group_id, name, path, arguments, working_dir, 
                 run_as_admin, icon_path, position, is_favorite) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (group_id, name, path, arguments, working_dir, 
                 1 if run_as_admin else 0, icon_path, max_pos + 1, 
                 1 if is_favorite else 0)
            )
            conn.commit()
            return cursor.lastrowid
    
    def get_buttons(self, group_id: int) -> List[Tuple[int, str, str, str, str, int, str, int, int]]:
        """获取指定分组的所有按钮"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT id, name, path, arguments, working_dir, 
                run_as_admin, icon_path, position, is_favorite 
                FROM buttons WHERE group_id = ? 
                ORDER BY is_favorite DESC, position""",
                (group_id,)
            )
            return cursor.fetchall()
    
    def get_all_buttons(self) -> List[Tuple[int, int, str, str, str, str, int, str, int, int]]:
        """获取所有按钮"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT id, group_id, name, path, arguments, 
                working_dir, run_as_admin, icon_path, position, is_favorite 
                FROM buttons 
                ORDER BY is_favorite DESC, position"""
            )
            return cursor.fetchall()
    
    def update_button(self, button_id: int, name: str, path: str, 
                    arguments: str = '', working_dir: str = '', 
                    run_as_admin: bool = False, icon_path: str = ''):
        """更新按钮信息"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """UPDATE buttons SET 
                name = ?, path = ?, arguments = ?, 
                working_dir = ?, run_as_admin = ?, icon_path = ? 
                WHERE id = ?""",
                (name, path, arguments, working_dir, 
                 1 if run_as_admin else 0, icon_path, button_id)
            )
            conn.commit()
    
    def toggle_button_favorite(self, button_id: int, is_favorite: bool):
        """切换按钮收藏状态"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE buttons SET is_favorite = ? WHERE id = ?",
                (1 if is_favorite else 0, button_id)
            )
            conn.commit()
    
    def delete_button(self, button_id: int):
        """删除按钮"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM buttons WHERE id = ?", (button_id,))
            conn.commit()
    
    def move_buttons_to_group(self, button_ids: List[int], target_group_id: int):
        """将按钮移动到另一个分组"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # 获取目标组中当前最大的position值
            cursor.execute("SELECT MAX(position) FROM buttons WHERE group_id = ?", (target_group_id,))
            max_pos = cursor.fetchone()[0] or 0
            
            # 更新每个按钮的group_id和position
            for i, button_id in enumerate(button_ids, 1):
                cursor.execute(
                    "UPDATE buttons SET group_id = ?, position = ? WHERE id = ?",
                    (target_group_id, max_pos + i, button_id)
                )
            conn.commit()
    
    def reorder_groups(self, group_order: List[int]):
        """重新排序分组"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            for position, group_id in enumerate(group_order, 1):
                cursor.execute(
                    "UPDATE groups SET position = ? WHERE id = ?",
                    (position, group_id)
                )
            conn.commit()
    
    def reorder_buttons(self, button_order: List[int]):
        """重新排序按钮"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            for position, button_id in enumerate(button_order, 1):
                cursor.execute(
                    "UPDATE buttons SET position = ? WHERE id = ?",
                    (position, button_id)
                )
            conn.commit()
    
    def get_button_position_info(self, button_id: int) -> Optional[Tuple[int, int, int]]:
        """获取按钮的位置信息 (group_id, position, total_in_group)"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT group_id, position FROM buttons WHERE id = ?", (button_id,)
            )
            row = cursor.fetchone()
            if not row:
                return None
            group_id, position = row
            cursor.execute(
                "SELECT COUNT(*) FROM buttons WHERE group_id = ?", (group_id,)
            )
            total = cursor.fetchone()[0]
            return (group_id, position, total)
    
    def move_button_forward(self, button_id: int) -> bool:
        """将按钮在同组内向前移动一位（position值减小，显示位置更靠前）"""
        info = self.get_button_position_info(button_id)
        if not info:
            return False
        group_id, position, total = info
        if position <= 1:
            return False  # 已经是最前面
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # 找到前一个按钮（position比当前小，且最接近的）
            cursor.execute(
                """SELECT id, position FROM buttons 
                WHERE group_id = ? AND position < ? 
                ORDER BY position DESC LIMIT 1""",
                (group_id, position)
            )
            prev_button = cursor.fetchone()
            if not prev_button:
                return False
            
            prev_id, prev_position = prev_button
            # 交换两个按钮的position
            cursor.execute(
                "UPDATE buttons SET position = ? WHERE id = ?",
                (prev_position, button_id)
            )
            cursor.execute(
                "UPDATE buttons SET position = ? WHERE id = ?",
                (position, prev_id)
            )
            conn.commit()
            return True
    
    def move_button_backward(self, button_id: int) -> bool:
        """将按钮在同组内向后移动一位（position值增大，显示位置更靠后）"""
        info = self.get_button_position_info(button_id)
        if not info:
            return False
        group_id, position, total = info
        if position >= total:
            return False  # 已经是最后面
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # 找到后一个按钮（position比当前大，且最接近的）
            cursor.execute(
                """SELECT id, position FROM buttons 
                WHERE group_id = ? AND position > ? 
                ORDER BY position ASC LIMIT 1""",
                (group_id, position)
            )
            next_button = cursor.fetchone()
            if not next_button:
                return False
            
            next_id, next_position = next_button
            # 交换两个按钮的position
            cursor.execute(
                "UPDATE buttons SET position = ? WHERE id = ?",
                (next_position, button_id)
            )
            cursor.execute(
                "UPDATE buttons SET position = ? WHERE id = ?",
                (position, next_id)
            )
            conn.commit()
            return True


    def _init_icon_dir(self):
        """初始化图标目录"""
        self.icon_dir = os.path.join(os.path.dirname(self.db_path), "icons")
        if not os.path.exists(self.icon_dir):
            os.makedirs(self.icon_dir)

    def get_icon_path(self, original_path: str) -> str:
        """获取图标保存路径"""
        if not original_path:
            return ""
        
        self._init_icon_dir()
        filename = os.path.basename(original_path)
        # 生成唯一文件名避免冲突
        unique_name = f"{hash(original_path)}_{filename}"
        return os.path.join(self.icon_dir, unique_name)

    def copy_icon_to_storage(self, icon_path: str) -> str:
        """将图标复制到持久化存储"""
        if not icon_path or not os.path.exists(icon_path):
            return ""
        
        target_path = self.get_icon_path(icon_path)
        try:
            shutil.copy2(icon_path, target_path)
            return target_path
        except Exception as e:
            print(f"无法复制图标文件: {e}")
            return icon_path  # 返回原始路径作为回退


    def get_backup_files(self):
        """获取所有备份文件，按时间排序"""
        backup_dir = "backups"
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
            return []
        
        # 使用更宽松的匹配模式
        backup_patterns = [
            os.path.join(backup_dir, "launcher_*.db"),
            os.path.join(backup_dir, "*.bak"),
            os.path.join(backup_dir, "*.db")
        ]
        
        backups = []
        for pattern in backup_patterns:
            backups.extend(glob.glob(pattern))
        
        # 去重并排序
        backups = list(set(backups))
        backups.sort(key=os.path.getmtime, reverse=True)
        return backups

    
    def create_backup(self, backup_type="auto"):
        """创建数据库备份"""
        try:
            # 确保备份目录存在
            backup_dir = "backups"
            if not os.path.exists(backup_dir):
                os.makedirs(backup_dir)
                
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"launcher_{backup_type}_backup_{timestamp}.db"
            backup_path = os.path.abspath(os.path.join(backup_dir, backup_name))
            
            # 使用WAL模式备份确保一致性
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 开始备份
            cursor.execute("BEGIN IMMEDIATE")
            shutil.copy2(self.db_path, backup_path)
            conn.commit()
            conn.close()
            
            # 验证备份是否创建成功
            if not os.path.exists(backup_path):
                print("[ERROR] Backup file was not created")
                return None
                
            # 清理旧备份
            backups = self.get_backup_files()
            if len(backups) > self.backup_count:
                for old_backup in backups[self.backup_count:]:
                    try:
                        os.remove(old_backup)
                    except Exception as e:
                        print(f"[ERROR] Failed to remove old backup: {str(e)}")
            
            return backup_path
        except Exception as e:
            print(f"[ERROR] Backup failed: {str(e)}")
            return None

        
    def restore_database(self, backup_path):
        """从备份恢复数据库"""
        try:
            # 先创建恢复前的备份
            self.create_backup(backup_type="restore_pre")
            
            # 执行恢复
            shutil.copy2(backup_path, self.db_path)
            
            # 重新初始化连接
            if self.conn:
                self.conn.close()
                self.conn = None
                
            return True
        except Exception as e:
            print(f"恢复失败: {str(e)}")
            return False
        
    def get_backup_info(self, backup_path):
        """获取备份文件信息"""
        try:
            if not os.path.exists(backup_path):
                return None
                
            stat = os.stat(backup_path)
            size = stat.st_size
            mtime = datetime.datetime.fromtimestamp(stat.st_mtime)
            
            # 从文件名获取备份类型
            filename = os.path.basename(backup_path)
            if "auto_backup" in filename:
                btype = "auto"
            elif "manual_backup" in filename:
                btype = "manual"
            elif "restore_pre" in filename:
                btype = "restore_pre"
            else:
                btype = "unknown"
                
            # 尝试获取数据库版本信息
            version = "unknown"
            try:
                conn = sqlite3.connect(f"file:{backup_path}?mode=ro", uri=True)
                cursor = conn.cursor()
                
                # 检查是否有特定表来判断是否是有效的备份
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='groups'")
                if not cursor.fetchone():
                    return None
                    
                # 获取版本信息
                cursor.execute("PRAGMA user_version")
                version = str(cursor.fetchone()[0])
                conn.close()
            except sqlite3.Error as e:
                print(f"[WARNING] Failed to read backup version: {str(e)}")
                
            return {
                "path": backup_path,
                "size": size,
                "time": mtime,
                "type": btype,
                "version": version
            }
        except Exception as e:
            print(f"[ERROR] Failed to get backup info: {str(e)}")
            return None


    def validate_backup_file(self, backup_path):
        """验证备份文件是否有效"""
        if not os.path.exists(backup_path):
            return False
            
        try:
            # 尝试打开备份文件验证有效性
            conn = sqlite3.connect(f"file:{backup_path}?mode=ro", uri=True)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            conn.close()
            return bool(tables)  # 如果有表则认为是有效备份
        except:
            return False


class HighlightTextEdit(QLineEdit):
    """支持高亮显示搜索关键字的文本框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.highlight_format = QTextCharFormat()
        self.highlight_format.setBackground(QColor(255, 255, 0))  # 黄色背景高亮
    
    def highlight_text(self, text: str):
        """高亮显示匹配的文本"""
        if not text:
            return
        
        # 获取当前文本
        current_text = self.text()
        if not current_text:
            return
        
        # 创建高亮格式
        palette = self.palette()
        palette.setColor(QPalette.Highlight, QColor(255, 255, 0))
        palette.setColor(QPalette.HighlightedText, Qt.black)
        self.setPalette(palette)
        
        # 查找所有匹配位置
        start_pos = 0
        while True:
            pos = current_text.lower().find(text.lower(), start_pos)
            if pos == -1:
                break
            self.setSelection(pos, len(text))
            start_pos = pos + len(text)

class ButtonEditor(QDialog):
    def __init__(self, button_id: Optional[int] = None, group_id: Optional[int] = None, 
                 name: str = "", path: str = "", arguments: str = "", 
                 working_dir: str = "", run_as_admin: bool = False, 
                 icon_path: str = "", is_favorite: bool = False, parent=None):
        super().__init__(parent)
        self.button_id = button_id
        self.group_id = group_id
        self.parent = parent
        self.icon_path = icon_path
        
        self.setWindowTitle("编辑按钮" if button_id else "添加按钮")
        self.setWindowModality(Qt.ApplicationModal)
        self.resize(500, 300)
        
        layout = QVBoxLayout()
        
        # 按钮名称
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("按钮名称:"))
        self.name_edit = QLineEdit(name)
        name_layout.addWidget(self.name_edit)
        
        # 收藏复选框
        self.favorite_check = QCheckBox("收藏")
        self.favorite_check.setChecked(is_favorite)
        name_layout.addWidget(self.favorite_check)
        
        layout.addLayout(name_layout)
        
        # 程序路径
        path_layout = QHBoxLayout()
        path_layout.addWidget(QLabel("程序路径:"))
        self.path_edit = QLineEdit(path)
        path_layout.addWidget(self.path_edit)
        
        self.browse_btn = QPushButton("浏览...")
        self.browse_btn.clicked.connect(self.browse_path)
        path_layout.addWidget(self.browse_btn)
        layout.addLayout(path_layout)
        
        # 启动参数
        args_layout = QHBoxLayout()
        args_layout.addWidget(QLabel("启动参数:"))
        self.args_edit = QLineEdit(arguments)
        args_layout.addWidget(self.args_edit)
        layout.addLayout(args_layout)
        
        # 工作目录
        dir_layout = QHBoxLayout()
        dir_layout.addWidget(QLabel("工作目录:"))
        self.dir_edit = QLineEdit(working_dir)
        dir_layout.addWidget(self.dir_edit)
        
        self.browse_dir_btn = QPushButton("浏览...")
        self.browse_dir_btn.clicked.connect(self.browse_working_dir)
        dir_layout.addWidget(self.browse_dir_btn)
        layout.addLayout(dir_layout)
        
        # 管理员权限和图标设置
        options_layout = QHBoxLayout()
        
        # 管理员权限
        self.admin_check = QCheckBox("以管理员权限运行")
        self.admin_check.setChecked(run_as_admin)
        options_layout.addWidget(self.admin_check)
        
        # 图标设置
        icon_btn_layout = QHBoxLayout()
        icon_btn_layout.addWidget(QLabel("图标:"))
        
        self.icon_btn = QPushButton()
        self.update_icon_btn()
        self.icon_btn.clicked.connect(self.change_icon)
        icon_btn_layout.addWidget(self.icon_btn)
        
        self.clear_icon_btn = QPushButton("清除")
        self.clear_icon_btn.clicked.connect(self.clear_icon)
        icon_btn_layout.addWidget(self.clear_icon_btn)
        
        options_layout.addLayout(icon_btn_layout)
        layout.addLayout(options_layout)
        
        # 按钮区域
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("保存")
        self.save_btn.clicked.connect(self.save_button)
        btn_layout.addWidget(self.save_btn)
        
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.close)
        btn_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(btn_layout)
        self.setLayout(layout)
    
    def update_icon_btn(self):
        """更新图标按钮的显示"""
        if self.icon_path and os.path.exists(self.icon_path):
            self.icon_btn.setIcon(QIcon(self.icon_path))
            self.icon_btn.setText("更改图标")
        else:
            self.icon_btn.setIcon(QIcon())
            self.icon_btn.setText("设置图标")
    
    def browse_path(self):
        """浏览文件系统选择程序或目录"""
        # 先检查剪贴板是否有文件或目录
        clipboard = QApplication.clipboard()
        if clipboard.mimeData().hasUrls():
            urls = clipboard.mimeData().urls()
            if urls and urls[0].isLocalFile():
                path = urls[0].toLocalFile()
                if os.path.exists(path):  # 检查路径是否存在
                    reply = QMessageBox.question(
                        self, "使用剪贴板路径", 
                        f"检测到剪贴板中有路径:\n{path}\n\n是否使用此路径?",
                        QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
                    if reply == QMessageBox.Yes:
                        self.path_edit.setText(path)
                        # 如果没有选择图标，尝试获取图标
                        if not self.icon_path:
                            self.set_icon_from_path(path)
                        return
        
        # 显示文件/目录选择对话框
        dialog = QFileDialog(self)
        dialog.setFileMode(QFileDialog.ExistingFile)
        dialog.setOption(QFileDialog.DontUseNativeDialog, True)
        
        # 添加"选择文件夹"按钮
        dir_btn = QPushButton("选择文件夹")
        dir_btn.clicked.connect(lambda: dialog.setFileMode(QFileDialog.Directory))
        dialog.layout().addWidget(dir_btn)
        
        # 添加"选择文件"按钮
        file_btn = QPushButton("选择文件")
        file_btn.clicked.connect(lambda: dialog.setFileMode(QFileDialog.ExistingFile))
        dialog.layout().addWidget(file_btn)
        
        if dialog.exec():
            paths = dialog.selectedFiles()
            if paths:
                path = paths[0]
                self.path_edit.setText(path)
                # 如果没有选择图标，尝试获取图标
                if not self.icon_path:
                    self.set_icon_from_path(path)


    def set_icon_from_path(self, path):
        """根据路径自动设置图标（统一优先次序 find_icon_auto）"""
        icon_path = DynamicIconGenerator.find_icon_auto(path)
        if icon_path:
            self.icon_path = icon_path
            self.update_icon_btn()



    
    def browse_working_dir(self):
        """浏览工作目录"""
        dir_path = QFileDialog.getExistingDirectory(self, "选择工作目录")
        if dir_path:
            self.dir_edit.setText(dir_path)
    
    def change_icon(self):
        """更改图标"""
        icon_path, _ = QFileDialog.getOpenFileName(
            self, "选择图标文件", "", "图标文件 (*.ico *.png *.jpg);;所有文件 (*.*)")
        if icon_path:
            self.icon_path = icon_path
            self.update_icon_btn()
    
    def clear_icon(self):
        """清除图标"""
        self.icon_path = ""
        self.update_icon_btn()
    
    def save_button(self):
        """保存按钮信息"""
        name = self.name_edit.text().strip()
        path = self.path_edit.text().strip()
        args = self.args_edit.text().strip()
        working_dir = self.dir_edit.text().strip()
        run_as_admin = self.admin_check.isChecked()
        is_favorite = self.favorite_check.isChecked()
        
        if not name:
            QMessageBox.warning(self, "警告", "按钮名称不能为空!")
            return
        
        if not path:
            QMessageBox.warning(self, "警告", "程序路径不能为空!")
            return
        
        # 预处理路径
        path = path.replace('/', '\\').strip('"\'')
        if working_dir:
            working_dir = working_dir.replace('/', '\\').strip('"\'')
        
        # 验证路径
        if not os.path.exists(path):
            if not (path.startswith('\\\\') or ':/' in path or ':\\' in path):
                QMessageBox.warning(self, "警告", "指定的路径不存在!")
                return
        
        db = DatabaseManager()
        
        # 处理图标路径
        icon_path = self.icon_path
        if icon_path:  # 如果有图标，确保它被保存到持久化存储
            icon_path = db.copy_icon_to_storage(icon_path)
        
        # 如果没有选择图标，按统一优先次序自动获取图标（find_icon_auto）
        if not icon_path:
            auto_icon = DynamicIconGenerator.find_icon_auto(path, name)
            if auto_icon:
                icon_path = db.copy_icon_to_storage(auto_icon)
                try:
                    # 若产物来自临时目录 temp_icons（exe 图标/系统图标提取），复制后删除原临时文件
                    temp_dir = os.path.abspath(os.path.join(BASE_DIR, "temp_icons"))
                    if os.path.abspath(os.path.dirname(auto_icon)) == temp_dir:
                        os.remove(auto_icon)
                except:
                    pass

        if self.button_id is not None:
            # 更新现有按钮
            db.update_button(
                self.button_id, name, path, args, 
                working_dir, run_as_admin, icon_path
            )
            db.toggle_button_favorite(self.button_id, is_favorite)
        else:
            # 添加新按钮
            if self.group_id is None:
                QMessageBox.warning(self, "错误", "未指定分组!")
                return
            db.add_button(
                self.group_id, name, path, args, 
                working_dir, run_as_admin, icon_path, is_favorite
            )
        
        self.parent.load_data()  # 刷新主界面
        self.close()



class GroupEditor(QDialog):
    def __init__(self, group_id: Optional[int] = None, name: str = "", 
                 is_favorite: bool = False, parent=None):
        super().__init__(parent)
        self.group_id = group_id
        self.parent = parent
        
        self.setWindowTitle("编辑分组" if group_id else "添加分组")
        self.setWindowModality(Qt.ApplicationModal)
        self.resize(300, 150)
        
        layout = QVBoxLayout()
        
        # 分组名称
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("分组名称:"))
        self.name_edit = QLineEdit(name)
        name_layout.addWidget(self.name_edit)
        layout.addLayout(name_layout)
        
        # 收藏复选框
        self.favorite_check = QCheckBox("收藏分组")
        self.favorite_check.setChecked(is_favorite)
        layout.addWidget(self.favorite_check)
        
        # 按钮区域
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("保存")
        self.save_btn.clicked.connect(self.save_group)
        btn_layout.addWidget(self.save_btn)
        
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.close)
        btn_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(btn_layout)
        self.setLayout(layout)
    
    def save_group(self):
        """保存分组信息"""
        name = self.name_edit.text().strip()
        is_favorite = self.favorite_check.isChecked()
        
        if not name:
            QMessageBox.warning(self, "警告", "分组名称不能为空!")
            return
        
        db = DatabaseManager()
        if self.group_id is not None:
            # 更新现有分组
            db.update_group_name(self.group_id, name)
            db.toggle_group_favorite(self.group_id, is_favorite)
        else:
            # 添加新分组
            db.add_group(name, is_favorite)
        
        self.parent.load_data()  # 刷新主界面
        self.close()

class ButtonReorderDialog(QDialog):
    """按钮全部重新排序对话框"""
    def __init__(self, group_id: int, group_name: str, parent=None):
        super().__init__(parent)
        self.group_id = group_id
        self.group_name = group_name
        self.parent = parent
        
        self.setWindowTitle(f"重新排序 - {group_name}")
        self.setWindowModality(Qt.ApplicationModal)
        self.resize(500, 500)
        
        layout = QVBoxLayout()
        
        # 说明标签
        tip_label = QLabel("使用右侧按钮调整按键排列顺序，或直接拖拽列表项排序：")
        tip_label.setWordWrap(True)
        layout.addWidget(tip_label)
        
        # 主区域：列表 + 按钮
        main_layout = QHBoxLayout()
        
        # 按钮列表
        self.list_widget = QListWidget()
        self.list_widget.setDragDropMode(QListWidget.InternalMove)
        self.list_widget.setSelectionMode(QListWidget.SingleSelection)
        self.list_widget.setAlternatingRowColors(True)
        main_layout.addWidget(self.list_widget)
        
        # 移动按钮区域
        move_btn_layout = QVBoxLayout()
        move_btn_layout.setAlignment(Qt.AlignTop)
        
        self.top_btn = QPushButton("移至最前 ↑↑")
        self.top_btn.clicked.connect(self.move_to_top)
        move_btn_layout.addWidget(self.top_btn)
        
        self.up_btn = QPushButton("上移 ↑")
        self.up_btn.clicked.connect(self.move_up)
        move_btn_layout.addWidget(self.up_btn)
        
        self.down_btn = QPushButton("下移 ↓")
        self.down_btn.clicked.connect(self.move_down)
        move_btn_layout.addWidget(self.down_btn)
        
        self.bottom_btn = QPushButton("移至最后 ↓↓")
        self.bottom_btn.clicked.connect(self.move_to_bottom)
        move_btn_layout.addWidget(self.bottom_btn)
        
        main_layout.addLayout(move_btn_layout)
        layout.addLayout(main_layout)
        
        # 自动排序区域
        sort_group = QGroupBox("自动排序（按文件属性排列）")
        sort_layout = QHBoxLayout(sort_group)
        sort_layout.addWidget(QLabel("排序方式:"))
        self.sort_combo = QComboBox()
        self.sort_combo.addItem("名称", "name")
        self.sort_combo.addItem("类型（扩展名）", "type")
        self.sort_combo.addItem("修改日期", "date")
        self.sort_combo.addItem("大小", "size")
        sort_layout.addWidget(self.sort_combo)
        sort_layout.addWidget(QLabel("方向:"))
        self.order_combo = QComboBox()
        self.order_combo.addItem("升序", False)
        self.order_combo.addItem("降序", True)
        sort_layout.addWidget(self.order_combo)
        self.apply_sort_btn = QPushButton("应用排序")
        self.apply_sort_btn.clicked.connect(self.apply_auto_sort)
        sort_layout.addWidget(self.apply_sort_btn)
        layout.addWidget(sort_group)
        
        sort_tip = QLabel("提示：自动排序会重排列表，点『保存排序』后写入生效。")
        sort_tip.setWordWrap(True)
        layout.addWidget(sort_tip)
        
        # 按钮区域
        btn_layout = QHBoxLayout()
        
        self.reset_btn = QPushButton("恢复原顺序")
        self.reset_btn.clicked.connect(self.reset_order)
        btn_layout.addWidget(self.reset_btn)
        
        btn_layout.addItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        
        self.save_btn = QPushButton("保存排序")
        self.save_btn.clicked.connect(self.save_order)
        self.save_btn.setDefault(True)
        btn_layout.addWidget(self.save_btn)
        
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.close)
        btn_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(btn_layout)
        self.setLayout(layout)
        
        # 加载按钮数据
        self.original_order = []  # 保存原始顺序用于恢复
        self.load_buttons()
    
    def _make_item(self, button_id, name, path, is_favorite=False, run_as_admin=False) -> QListWidgetItem:
        """创建列表项并保存排序所需数据（button_id/path/收藏/管理员）"""
        item = QListWidgetItem(name)
        item.setData(Qt.UserRole, button_id)
        item.setData(Qt.UserRole + 1, path)
        item.setData(Qt.UserRole + 2, 1 if is_favorite else 0)
        item.setData(Qt.UserRole + 3, 1 if run_as_admin else 0)
        item.setToolTip(f"路径: {path}")
        if is_favorite:
            item.setForeground(QColor(255, 102, 0))
        if run_as_admin:
            font = item.font()
            font.setBold(True)
            item.setFont(font)
        return item
    
    def load_buttons(self):
        """加载分组内所有按钮到列表"""
        db = DatabaseManager()
        buttons = db.get_buttons(self.group_id)
        self.list_widget.clear()
        self.original_order = []
        
        for btn_data in buttons:
            (button_id, name, path, args, working_dir,
             run_as_admin, icon_path, _, is_favorite) = btn_data
            self.list_widget.addItem(
                self._make_item(button_id, name, path, is_favorite, run_as_admin))
            self.original_order.append(button_id)
    
    def move_up(self):
        """上移选中项"""
        row = self.list_widget.currentRow()
        if row > 0:
            item = self.list_widget.takeItem(row)
            self.list_widget.insertItem(row - 1, item)
            self.list_widget.setCurrentRow(row - 1)
    
    def move_down(self):
        """下移选中项"""
        row = self.list_widget.currentRow()
        if row >= 0 and row < self.list_widget.count() - 1:
            item = self.list_widget.takeItem(row)
            self.list_widget.insertItem(row + 1, item)
            self.list_widget.setCurrentRow(row + 1)
    
    def move_to_top(self):
        """移至最前"""
        row = self.list_widget.currentRow()
        if row > 0:
            item = self.list_widget.takeItem(row)
            self.list_widget.insertItem(0, item)
            self.list_widget.setCurrentRow(0)
    
    def move_to_bottom(self):
        """移至最后"""
        row = self.list_widget.currentRow()
        count = self.list_widget.count()
        if row >= 0 and row < count - 1:
            item = self.list_widget.takeItem(row)
            self.list_widget.insertItem(count - 1, item)
            self.list_widget.setCurrentRow(count - 1)
    
    def reset_order(self):
        """恢复原始顺序"""
        self.list_widget.clear()
        db = DatabaseManager()
        buttons = db.get_buttons(self.group_id)
        for button_id in self.original_order:
            for btn_data in buttons:
                if btn_data[0] == button_id:
                    (bid, name, path, _a, _w, run_as_admin, _i, _p, is_favorite) = btn_data
                    self.list_widget.addItem(
                        self._make_item(bid, name, path, is_favorite, run_as_admin))
                    break
    
    def apply_auto_sort(self):
        """按选择的排序方式自动排列按钮顺序（应用后点『保存排序』写入生效）

        排序方式：名称 / 类型（扩展名） / 修改日期 / 大小；可升序 / 降序。
        """
        mode = self.sort_combo.currentData()
        reverse = bool(self.order_combo.currentData())
        
        # 收集当前列表项数据
        rows = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            rows.append((
                item.data(Qt.UserRole),            # button_id
                item.text(),                       # name
                item.data(Qt.UserRole + 1),        # path
                bool(item.data(Qt.UserRole + 2)),  # is_favorite
                bool(item.data(Qt.UserRole + 3)),  # run_as_admin
            ))
        
        def sort_key(r):
            _bid, name, path, _fav, _admin = r
            if mode == "name":
                return (name.lower(),)
            if mode == "type":
                ext = os.path.splitext(path or '')[1].lower()
                isdir = bool(path and os.path.isdir(path))
                return (0 if isdir else 1, ext, name.lower())
            if mode == "date":
                try:
                    t = os.path.getmtime(path) if path and os.path.exists(path) else 0.0
                except Exception:
                    t = 0.0
                return (t, name.lower())
            if mode == "size":
                try:
                    s = os.path.getsize(path) if path and os.path.isfile(path) else 0
                except Exception:
                    s = 0
                return (s, name.lower())
            return (0,)
        
        rows.sort(key=sort_key, reverse=reverse)
        self.list_widget.clear()
        for bid, name, path, fav, admin in rows:
            self.list_widget.addItem(self._make_item(bid, name, path, fav, admin))
        self.list_widget.setCurrentRow(0)
    
    def save_order(self):
        """保存新的排序"""
        new_order = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            button_id = item.data(Qt.UserRole)
            new_order.append(button_id)
        
        db = DatabaseManager()
        db.reorder_buttons(new_order)
        self.parent.load_data()
        self.close()

class IconLoadWorker(QThread):
    """后台加载图标的线程工作类"""
    icon_loaded = Signal(int, str)  # button_id, icon_path
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._tasks = []  # List of (button_id, path, name)
        self._lock = threading.Lock()
        self._cancelled = False
    
    def add_task(self, button_id: int, path: str, name: str = ""):
        """添加图标加载任务"""
        with self._lock:
            self._tasks.append((button_id, path, name))
    
    def cancel(self):
        """取消所有任务"""
        with self._lock:
            self._cancelled = True
            self._tasks.clear()
    
    def run(self):
        """在后台线程中加载图标"""
        while True:
            with self._lock:
                if self._cancelled or not self._tasks:
                    break
                button_id, path, name = self._tasks.pop(0)
            
            # 按统一优先次序自动获取图标（find_icon_auto）
            icon_path = DynamicIconGenerator.find_icon_auto(path, name)
            
            if icon_path and not self._cancelled:
                self.icon_loaded.emit(button_id, icon_path)


class DataLoadWorker(QThread):
    """后台加载数据的工作线程"""
    data_ready = Signal(list)  # groups data
    progress = Signal(str)    # 进度信息
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._cancelled = False
    
    def cancel(self):
        self._cancelled = True
    
    def run(self):
        """在后台线程中加载数据"""
        try:
            self.progress.emit("正在加载数据...")
            db = DatabaseManager()
            groups = db.get_groups()
            
            if not groups:
                try:
                    db.add_group("默认分组")
                    groups = db.get_groups()
                except Exception as e:
                    groups = [(1, "默认分组", 0, 0)]
            
            if not self._cancelled:
                self.data_ready.emit(groups)
        except Exception as e:
            if not self._cancelled:
                self.progress.emit(f"加载数据失败: {str(e)}")


class BackupWorker(QThread):
    """后台备份数据库的工作线程"""
    backup_complete = Signal(bool, str)  # success, message
    
    def __init__(self, parent=None):
        super().__init__(parent)
    
    def run(self):
        """在后台线程中执行备份"""
        try:
            db = DatabaseManager()
            backup_path = db.create_backup()
            if backup_path:
                self.backup_complete.emit(True, f"自动备份成功: {backup_path}")
            else:
                self.backup_complete.emit(False, "自动备份失败")
        except Exception as e:
            self.backup_complete.emit(False, f"备份异常: {str(e)}")


class SearchResultDialog(QDialog):
    """搜索结果对话框"""
    def __init__(self, results: List[Tuple[str, str, str]], parent=None):
        super().__init__(parent)
        self.setWindowTitle("搜索结果")
        self.setWindowModality(Qt.NonModal)
        self.resize(600, 400)
        
        layout = QVBoxLayout()
        
        # 结果表格
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["类型", "名称", "路径/分组"])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        
        # 填充数据
        self.table.setRowCount(len(results))
        for row, (result_type, name, path) in enumerate(results):
            self.table.setItem(row, 0, QTableWidgetItem(result_type))
            self.table.setItem(row, 1, QTableWidgetItem(name))
            self.table.setItem(row, 2, QTableWidgetItem(path))
        
        self.table.resizeColumnsToContents()
        layout.addWidget(self.table)
        
        # 关闭按钮
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)
        
        self.setLayout(layout)

class SettingsDialog(QDialog):
    """设置对话框（使用分页标签方式管理和布局）"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.setWindowModality(Qt.ApplicationModal)
        self.resize(640, 560)
        
        layout = QVBoxLayout()
        
        # 分页标签
        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_icon_scheme_tab(), "图标方案")
        # 后续标签（其它设置）在此追加
        layout.addWidget(self.tabs)
        
        # 底部按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.close)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
    
    # ---------- 图标方案页 ----------
    def _build_icon_scheme_tab(self) -> QWidget:
        """图标方案设置页：选择方案；方案2/自定义方案可调整①~⑤顺序并另存为新方案"""
        page = QWidget()
        v = QVBoxLayout(page)
        
        # 方案选择行
        scheme_row = QHBoxLayout()
        scheme_row.addWidget(QLabel("图标方案:"))
        self.scheme_combo = QComboBox()
        self._reload_scheme_combo()
        self.scheme_combo.currentIndexChanged.connect(self._on_scheme_changed)
        scheme_row.addWidget(self.scheme_combo, 1)
        v.addLayout(scheme_row)
        
        # 方案说明（当前方案的先后顺序逻辑，只读）
        self.scheme_desc = QTextEdit()
        self.scheme_desc.setReadOnly(True)
        self.scheme_desc.setPlainText(get_scheme_desc(get_icon_scheme()))
        v.addWidget(self.scheme_desc, 1)
        
        # 可调整顺序区（仅方案2 / 自定义方案显示）
        self.sort_box = QGroupBox("可调整顺序（①~⑤；⑥兜底 / ⑦保险固定在后）")
        sv = QVBoxLayout(self.sort_box)
        self.step_list = QListWidget()
        sv.addWidget(self.step_list)
        btn_row = QHBoxLayout()
        self.move_up_btn = QPushButton("上移 ↑")
        self.move_up_btn.clicked.connect(self._move_step_up)
        btn_row.addWidget(self.move_up_btn)
        self.move_down_btn = QPushButton("下移 ↓")
        self.move_down_btn.clicked.connect(self._move_step_down)
        btn_row.addWidget(self.move_down_btn)
        btn_row.addStretch()
        self.save_as_btn = QPushButton("另存为新方案...")
        self.save_as_btn.clicked.connect(self._save_as_new_scheme)
        btn_row.addWidget(self.save_as_btn)
        sv.addLayout(btn_row)
        self.sort_box.setVisible(False)
        v.addWidget(self.sort_box)
        
        return page
    
    def _reload_scheme_combo(self) -> None:
        """重建方案下拉（含内置方案与用户另存的自定义方案）"""
        self.scheme_combo.blockSignals(True)
        self.scheme_combo.clear()
        for sid, info in ICON_SCHEMES.items():
            self.scheme_combo.addItem(info["name"], sid)
        idx = self.scheme_combo.findData(get_icon_scheme())
        self.scheme_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self.scheme_combo.blockSignals(False)
    
    def _on_scheme_changed(self, index: int):
        """切换图标方案 -> 实时自动保存（持久化），并刷新说明/排序区"""
        sid = self.scheme_combo.itemData(index)
        set_icon_scheme(sid)
        self.scheme_desc.setPlainText(get_scheme_desc(sid))
        info = ICON_SCHEMES.get(sid, {})
        editable = bool(info.get("editable"))
        self.sort_box.setVisible(editable)
        if editable:
            self._load_steps_to_list(get_scheme_order(sid))
        else:
            self.step_list.clear()
    
    def _load_steps_to_list(self, order: list) -> None:
        """把①~⑤顺序加载到可排序列表"""
        self.step_list.clear()
        for s in order:
            item = QListWidgetItem(ICON_STEPS.get(s, f"步骤{s}"))
            item.setData(Qt.UserRole, s)
            self.step_list.addItem(item)
    
    def _current_order(self) -> list:
        """读取当前排序列表中的①~⑤顺序"""
        return [self.step_list.item(i).data(Qt.UserRole) for i in range(self.step_list.count())]
    
    def _save_current_order(self) -> None:
        """保存当前顺序（方案2 存 scheme2_order；自定义方案存 custom_schemes）并刷新说明"""
        order = self._current_order()
        sid = self.scheme_combo.currentData()
        info = ICON_SCHEMES.get(sid, {})
        if sid == 2:
            set_scheme2_order(order)
        elif info.get("custom"):
            update_custom_scheme(sid, order=order)
        self.scheme_desc.setPlainText(get_scheme_desc(sid))
    
    def _move_step_up(self):
        """上移当前步骤"""
        row = self.step_list.currentRow()
        if row > 0:
            item = self.step_list.takeItem(row)
            self.step_list.insertItem(row - 1, item)
            self.step_list.setCurrentRow(row - 1)
            self._save_current_order()
    
    def _move_step_down(self):
        """下移当前步骤"""
        row = self.step_list.currentRow()
        if row >= 0 and row < self.step_list.count() - 1:
            item = self.step_list.takeItem(row)
            self.step_list.insertItem(row + 1, item)
            self.step_list.setCurrentRow(row + 1)
            self._save_current_order()
    
    def _save_as_new_scheme(self):
        """把当前自定义顺序另存为新方案（名称可自定义），方便以后选择"""
        order = self._current_order()
        count = len([k for k in ICON_SCHEMES if k >= _CUSTOM_SCHEME_START])
        name, ok = QInputDialog.getText(
            self, "另存为新方案", "方案名称:", text=f"我的方案{count + 1}")
        if not ok or not name.strip():
            return
        sid = add_custom_scheme(name.strip(), order)
        set_icon_scheme(sid)
        self._reload_scheme_combo()
        self.scheme_combo.setCurrentIndex(self.scheme_combo.findData(sid))
        self._on_scheme_changed(self.scheme_combo.currentIndex())

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # 设置窗口标题和图标
        self.setWindowTitle(f"{ProjectInfo.NAME} {ProjectInfo.VERSION} (Build: {ProjectInfo.BUILD_DATE})")
        self.set_application_icon()
        
        # 加载图标方案设置（持久化，实时自动保存）
        load_icon_scheme()
        
        # 主窗口设置
        self.resize(800, 600)
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # 主布局
        self.main_layout = QVBoxLayout(self.central_widget)
        
        # 创建搜索框
        self.create_search_box()
        
        # 创建标签页
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.West)
        self.tab_widget.setMovable(True)
        self.tab_widget.tabBar().setUsesScrollButtons(True)
        self.tab_widget.tabBar().setElideMode(Qt.ElideRight)
        self.main_layout.addWidget(self.tab_widget)
        
        # 添加控制按钮
        self.create_control_buttons()

        # 修改备份定时器为更智能的方式
        self.backup_timer = QTimer(self)
        self.backup_timer.timeout.connect(self.smart_backup)
        self.backup_timer.start(30000)  # 每30秒检查一次
        
        # 初始化批量选择模式
        self.batch_mode = False
        self.selected_buttons = set()
        
        # 初始化多线程相关
        self._thread_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="launcher")
        self._icon_workers = []      # 图标加载线程列表
        self._data_worker = None     # 数据加载线程
        self._backup_worker = None   # 备份线程
        
        # 加载数据
        self.load_data()
        
        # 加载窗口设置
        self.load_window_settings()

        # 添加剪贴板监控
        self.clipboard = QApplication.clipboard()
        self.clipboard.dataChanged.connect(self.check_clipboard_for_executable)
        self.last_clipboard_path = None
        
        # 添加快捷键
        self.paste_action = QAction(self)
        self.paste_action.setShortcut(QKeySequence("Ctrl+V"))
        self.paste_action.triggered.connect(self.handle_paste_shortcut)
        self.addAction(self.paste_action)

    def check_clipboard_for_executable(self):
        """检查剪贴板中是否有可执行文件或目录"""
        if self.clipboard.mimeData().hasUrls():
            urls = self.clipboard.mimeData().urls()
            if urls and urls[0].isLocalFile():
                path = urls[0].toLocalFile()
                if os.path.exists(path):  # 检查路径是否存在
                    self.last_clipboard_path = path
                    return path
        elif self.clipboard.mimeData().hasText():
            text = self.clipboard.text().strip()
            if os.path.exists(text):  # 检查路径是否存在
                self.last_clipboard_path = text
                return text
        self.last_clipboard_path = None
        return None


    def show_add_button_dialog_from_clipboard(self, path):
        """从剪贴板路径显示添加按钮对话框"""
        current_index = self.tab_widget.currentIndex()
        if current_index == -1:
            QMessageBox.warning(self, "警告", "请先选择一个分组!")
            return
        
        # 获取当前分组ID
        db = DatabaseManager()
        groups = db.get_groups()
        if not groups:
            QMessageBox.warning(self, "错误", "没有可用的分组!")
            return
        
        group_id = groups[current_index][0]
        name = os.path.splitext(os.path.basename(path))[0]

        # 自动设置图标（统一优先次序 find_icon_auto）
        icon_path = DynamicIconGenerator.find_icon_auto(path)
        
        dialog = ButtonEditor(
            group_id=group_id,
            name=name,
            path=path,
            icon_path=icon_path,
            parent=self
        )
        dialog.setWindowFlags(dialog.windowFlags() | Qt.WindowStaysOnTopHint)
        dialog.exec()



    def handle_paste_shortcut(self):
        """处理Ctrl+V快捷键"""
        path = self.check_clipboard_for_executable()

        if path:
            self.show_add_button_dialog_from_clipboard(path)
        else:
            QMessageBox.information(self, "提示", "剪贴板中没有找到可执行文件")


    def create_search_box(self):
        """创建搜索框"""
        search_layout = QHBoxLayout()
        
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("搜索分组或按钮...")
        self.search_edit.textChanged.connect(self.on_search_text_changed)
        search_layout.addWidget(self.search_edit)
        
        self.search_btn = QPushButton("搜索")
        self.search_btn.clicked.connect(self.perform_search)
        search_layout.addWidget(self.search_btn)
        
        # 右上角"设置"按钮（搜索右边）
        self.settings_btn = QPushButton("设置")
        self.settings_btn.clicked.connect(self.show_settings_dialog)
        search_layout.addWidget(self.settings_btn)
        
        self.main_layout.addLayout(search_layout)
    
    def on_search_text_changed(self, text):
        """搜索文本变化时的处理"""
        if not text.strip():
            # 如果搜索框为空，恢复原始视图
            self.load_data()
    
    def perform_search(self):
        """执行搜索"""
        search_text = self.search_edit.text().strip()
        if not search_text:
            return
        
        db = DatabaseManager()
        results = []
        
        # 搜索分组
        groups = db.get_groups()
        for group_id, group_name, _, _ in groups:
            # 匹配分组名称或拼音首字母
            if (search_text.lower() in group_name.lower() or 
                search_text.lower() in pinyin.get_initial(group_name).lower()):
                results.append(("分组", group_name, ""))
        
        # 搜索按钮
        buttons = db.get_all_buttons()
        for button_id, group_id, name, path, _, _, _, _, _, _ in buttons:
            # 获取分组名称
            group_name = next((g[1] for g in groups if g[0] == group_id), "未知分组")
            
            # 匹配按钮名称、路径或拼音首字母
            if (search_text.lower() in name.lower() or 
                search_text.lower() in path.lower() or 
                search_text.lower() in pinyin.get_initial(name).lower()):
                results.append(("按钮", name, f"{group_name} | {path}"))
        
        if results:
            # 显示搜索结果对话框
            dialog = SearchResultDialog(results, self)
            dialog.show()
        else:
            QMessageBox.information(self, "搜索结果", "没有找到匹配的项目")

    def smart_backup(self):
        """智能备份策略（检查是否需要备份后异步执行）"""
        now = datetime.datetime.now()
        
        # 只在工作时间备份(8:00-20:00)
        if 8 <= now.hour < 20:
            # 每小时备份一次
            if now.minute == 0:
                self.perform_backup()

    def perform_backup(self):
        """执行数据库备份（后台线程执行，避免UI卡顿）"""
        # 如果已有备份线程在运行，跳过
        if self._backup_worker and self._backup_worker.isRunning():
            return
        
        # 清理旧的已完成线程引用
        if self._backup_worker:
            try:
                self._backup_worker.backup_complete.disconnect()
            except (RuntimeError, TypeError):
                pass
            self._backup_worker = None
        
        self._backup_worker = BackupWorker(self)
        self._backup_worker.backup_complete.connect(self._on_backup_complete)
        self._backup_worker.finished.connect(self._on_backup_worker_finished)
        self._backup_worker.start()
    
    def _on_backup_worker_finished(self):
        """备份线程结束后清理引用"""
        if self._backup_worker:
            try:
                self._backup_worker.backup_complete.disconnect()
                self._backup_worker.finished.disconnect()
            except (RuntimeError, TypeError):
                pass
            self._backup_worker.deleteLater()
            self._backup_worker = None
    
    def _on_backup_complete(self, success: bool, message: str):
        """备份完成的回调"""
        self._backup_worker = None


    def set_application_icon(self):
        """设置应用程序图标"""
        icon_path = "icon.ico"
        
        if not os.path.exists(icon_path):
            # 动态生成图标
            icon_path = DynamicIconGenerator.generate_icon("启动器")
        
        self.setWindowIcon(QIcon(icon_path))
    
    def create_control_buttons(self):
        """创建控制按钮"""
        control_layout = QHBoxLayout()
        
        # 添加分组按钮
        self.add_group_btn = QPushButton("添加分组")
        self.add_group_btn.clicked.connect(self.show_add_group_dialog)
        control_layout.addWidget(self.add_group_btn)
        
        # 添加按钮
        self.add_button_btn = QPushButton("添加按钮")
        self.add_button_btn.clicked.connect(self.show_add_button_dialog)
        control_layout.addWidget(self.add_button_btn)
        
        # 批量操作按钮
        self.batch_btn = QPushButton("批量操作")
        self.batch_btn.setCheckable(True)
        self.batch_btn.clicked.connect(self.toggle_batch_mode)
        control_layout.addWidget(self.batch_btn)
        
        # 添加弹簧
        control_layout.addItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        
        # 刷新按钮
        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.clicked.connect(self.load_data)
        control_layout.addWidget(self.refresh_btn)
        
        # 添加备份按钮
        self.backup_btn = QPushButton("数据库备份")
        self.backup_btn.clicked.connect(self.show_backup_dialog)
        control_layout.addWidget(self.backup_btn)
            

        self.main_layout.addLayout(control_layout)

    def show_backup_dialog(self):
        """显示备份恢复对话框"""
        db = DatabaseManager()
        dialog = BackupRestoreDialog(db, self)
        dialog.exec()

    def show_settings_dialog(self):
        """显示设置对话框（分页标签）"""
        dialog = SettingsDialog(self)
        dialog.setWindowFlags(dialog.windowFlags() | Qt.WindowStaysOnTopHint)
        dialog.exec()

    def toggle_batch_mode(self, checked):
        """切换批量操作模式"""
        self.batch_mode = checked
        self.batch_btn.setStyleSheet("background-color: #FF9999" if checked else "")
        self.selected_buttons.clear()
        
        # 更新所有按钮的样式
        for i in range(self.tab_widget.count()):
            tab = self.tab_widget.widget(i)
            scroll = tab.findChild(QScrollArea)
            if scroll:
                scroll_content = scroll.widget()
                buttons_group = scroll_content.findChild(QGroupBox)
                if buttons_group:
                    for btn in buttons_group.findChildren(QToolButton):
                        btn.setStyleSheet("")
    
    def load_data(self):
        """加载分组和按钮数据（多线程优化版本）"""
        try:
            # 取消之前的图标加载线程
            self._cancel_icon_workers()
            
            # 清除现有标签页前先备份当前选中索引
            current_index = self.tab_widget.currentIndex()
            
            # 清除现有标签页
            while self.tab_widget.count() > 0:
                widget = self.tab_widget.widget(0)
                self.tab_widget.removeTab(0)
                if widget:
                    widget.deleteLater()
            
            db = DatabaseManager()
            groups = db.get_groups()
            
            if not groups:
                try:
                    default_group_id = db.add_group("默认分组")
                    groups = db.get_groups()
                    if not groups:
                        raise Exception("无法创建默认分组")
                except Exception as e:
                    print(f"[ERROR] 创建默认分组失败: {str(e)}")
                    groups = [(1, "默认分组", 0, 0)]
            
            # 收集所有按钮的图标加载任务
            icon_tasks = []
            
            # 按顺序添加分组标签页
            for group_id, group_name, _, is_favorite in groups:
                try:
                    tasks = self.add_group_tab(group_id, group_name, is_favorite)
                    icon_tasks.extend(tasks)
                except Exception as e:
                    print(f"[ERROR] 添加分组标签页失败: {group_name}, 错误: {str(e)}")
                    import traceback
                    traceback.print_exc()
            
            # 恢复之前选中的标签页
            if current_index >= 0 and current_index < self.tab_widget.count():
                self.tab_widget.setCurrentIndex(current_index)
            
            # 后台异步加载图标
            if icon_tasks:
                icon_worker = IconLoadWorker(self)
                icon_worker.icon_loaded.connect(self._on_icon_loaded)
                icon_worker.finished.connect(lambda w=icon_worker: self._on_icon_worker_finished(w))
                for button_id, path, name in icon_tasks:
                    icon_worker.add_task(button_id, path, name)
                self._icon_workers.append(icon_worker)
                icon_worker.start()
            
        except Exception as e:
            print(f"[CRITICAL] 加载数据时发生严重错误: {str(e)}")
            import traceback
            traceback.print_exc()
            QMessageBox.warning(self, "错误", "加载数据时发生错误，正在尝试恢复...")
            self.tab_widget.clear()
            self.add_group_tab(1, "默认分组", False)
    
    def _cancel_icon_workers(self):
        """取消所有正在运行的图标加载线程"""
        for worker in self._icon_workers:
            if worker.isRunning():
                worker.cancel()
                # 先断开信号连接，防止悬空信号
                try:
                    worker.icon_loaded.disconnect()
                except (RuntimeError, TypeError):
                    pass
                # 等待线程结束（最多5秒）
                if not worker.wait(5000):
                    # 超时则强制终止
                    worker.terminate()
                    worker.wait(2000)
        self._icon_workers.clear()
    
    def _on_icon_loaded(self, button_id: int, icon_path: str):
        """图标加载完成后的回调（在主线程中执行）"""
        if not icon_path or not os.path.exists(icon_path):
            return
        
        # 在所有标签页中查找对应的按钮并更新图标
        for i in range(self.tab_widget.count()):
            tab = self.tab_widget.widget(i)
            scroll = tab.findChild(QScrollArea)
            if scroll:
                scroll_content = scroll.widget()
                buttons_group = scroll_content.findChild(QGroupBox)
                if buttons_group:
                    for btn in buttons_group.findChildren(QToolButton):
                        bid = btn.property("button_id")
                        if bid is not None and bid == button_id:
                            btn.setIcon(QIcon(icon_path))
                            btn.setIconSize(QSize(32, 32))
                            return
    
    def _on_icon_worker_finished(self, worker: IconLoadWorker):
        """图标加载线程完成后的清理"""
        try:
            if worker in self._icon_workers:
                self._icon_workers.remove(worker)
            worker.deleteLater()
        except Exception:
            pass


    
    def add_group_tab(self, group_id: int, group_name: str, is_favorite: bool) -> list:
        """添加分组标签页（多线程优化版本），返回图标加载任务列表"""
        icon_tasks = []
        try:
            tab = QWidget()
            tab_layout = QVBoxLayout(tab)
            
            # 创建滚动区域
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll_content = QWidget()
            scroll_layout = QVBoxLayout(scroll_content)
            
            # 添加分组标题和编辑按钮
            try:
                header_layout = QHBoxLayout()
                
                # 收藏星标
                favorite_icon = QLabel()
                if is_favorite:
                    try:
                        favorite_icon.setPixmap(QIcon(":star.png").pixmap(16, 16))
                    except:
                        favorite_icon.setText("★")
                header_layout.addWidget(favorite_icon)
                
                group_label = QLabel(f"<h2>{group_name}</h2>")
                header_layout.addWidget(group_label)
                
                # 编辑分组按钮
                edit_group_btn = QPushButton("编辑")
                edit_group_btn.clicked.connect(lambda _, gid=group_id, name=group_name, fav=is_favorite: 
                                            self.show_edit_group_dialog(gid, name, fav))
                header_layout.addWidget(edit_group_btn)
                
                # 删除分组按钮
                delete_group_btn = QPushButton("删除")
                delete_group_btn.clicked.connect(lambda _, gid=group_id: self.delete_group(gid))
                header_layout.addWidget(delete_group_btn)
                
                # 重新排序按钮
                reorder_btn = QPushButton("重新排序")
                reorder_btn.clicked.connect(lambda _, gid=group_id, gname=group_name: 
                                          self.show_button_reorder_dialog(gid, gname))
                header_layout.addWidget(reorder_btn)
                
                header_layout.addItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
                scroll_layout.addLayout(header_layout)
            except Exception as e:
                print(f"[ERROR] 创建分组标题失败: {str(e)}")
                scroll_layout.addWidget(QLabel(f"<h2>{group_name}</h2>"))
            
            # 添加按钮区域
            try:
                buttons_group = QGroupBox()
                buttons_layout = FlowLayout()
                buttons_group.setLayout(buttons_layout)
                
                db = DatabaseManager()
                buttons = db.get_buttons(group_id)
                
                if not buttons:
                    no_buttons_label = QLabel('此分组没有按钮，点击右上角的"添加按钮"来添加。')
                    no_buttons_label.setAlignment(Qt.AlignCenter)
                    buttons_layout.addWidget(no_buttons_label)
                else:
                    for button_data in buttons:
                        try:
                            (button_id, name, path, args, working_dir, 
                            run_as_admin, icon_path, _, is_favorite) = button_data
                            
                            btn = QToolButton()
                            btn.setText(name)
                            btn.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
                            btn.setToolTip(f"路径: {path}\n参数: {args}\n工作目录: {working_dir}")
                            btn.setFixedSize(120, 60)
                            btn.setProperty("button_id", button_id)
                            
                            # 优先使用已保存的图标路径（数据库中的）
                            icon_loaded = False
                            if icon_path and os.path.exists(icon_path):
                                try:
                                    btn.setIcon(QIcon(icon_path))
                                    btn.setIconSize(QSize(32, 32))
                                    icon_loaded = True
                                except:
                                    pass
                            
                            # 如果没有已保存的有效图标，添加到后台加载任务
                            if not icon_loaded:
                                icon_tasks.append((button_id, path, name))
                            
                            # 如果是收藏的按钮，添加星标
                            if is_favorite:
                                btn.setStyleSheet("font-weight: bold; color: #FF6600;")
                            
                            # 如果是管理员权限运行，添加特殊样式
                            if run_as_admin:
                                btn.setStyleSheet(btn.styleSheet() + "border: 1px solid red;")
                            
                            # 按钮点击事件
                            if not self.batch_mode:
                                btn.clicked.connect(lambda _, p=path, a=args, wd=working_dir, ra=run_as_admin: 
                                                self.launch_program(p, a, wd, ra))
                            else:
                                btn.clicked.connect(lambda _, bid=button_id, b=btn: 
                                                self.toggle_button_selection(bid, b))
                            
                            # 按钮上下文菜单
                            btn.setContextMenuPolicy(Qt.CustomContextMenu)
                            btn.customContextMenuRequested.connect(
                                lambda pos, bid=button_id, gid=group_id, n=name, p=path, 
                                    a=args, wd=working_dir, ra=run_as_admin, ip=icon_path, fav=is_favorite: 
                                self.show_button_context_menu(pos, bid, gid, n, p, a, wd, ra, ip, fav))
                            
                            buttons_layout.addWidget(btn)
                        except Exception as e:
                            print(f"[ERROR] 创建按钮失败: {name}, 错误: {str(e)}")
                            continue
                    
                scroll_layout.addWidget(buttons_group)
                scroll_layout.addItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))
                
                scroll.setWidget(scroll_content)
                tab_layout.addWidget(scroll)
                
                # 添加标签页
                self.tab_widget.addTab(tab, group_name)
                if is_favorite:
                    self.tab_widget.tabBar().setTabTextColor(self.tab_widget.count()-1, QColor(255, 102, 0))
                
            except Exception as e:
                print(f"[ERROR] 创建按钮区域失败: {str(e)}")
                error_label = QLabel(f"无法加载按钮: {str(e)}")
                error_label.setAlignment(Qt.AlignCenter)
                tab_layout.addWidget(error_label)
                self.tab_widget.addTab(tab, group_name)
                
        except Exception as e:
            print(f"[CRITICAL] 添加分组标签页时发生严重错误: {str(e)}")
            import traceback
            traceback.print_exc()
        
        return icon_tasks

    
    def toggle_button_selection(self, button_id: int, button: QToolButton):
        """切换按钮的选择状态"""
        if button_id in self.selected_buttons:
            self.selected_buttons.remove(button_id)
            button.setStyleSheet("")
        else:
            self.selected_buttons.add(button_id)
            button.setStyleSheet("background-color: #99CCFF")
    
    def show_add_group_dialog(self):
        """显示添加分组对话框"""
        dialog = GroupEditor(parent=self)
        dialog.setWindowFlags(dialog.windowFlags() | Qt.WindowStaysOnTopHint)
        dialog.exec()
    
    def show_edit_group_dialog(self, group_id: int, name: str, is_favorite: bool):
        """显示编辑分组对话框"""
        dialog = GroupEditor(group_id=group_id, name=name, is_favorite=is_favorite, parent=self)
        dialog.setWindowFlags(dialog.windowFlags() | Qt.WindowStaysOnTopHint)
        dialog.exec()
    
    def delete_group(self, group_id: int):
        """删除分组"""
        reply = QMessageBox.question(
            self, "确认删除", 
            "确定要删除这个分组及其所有按钮吗?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            db = DatabaseManager()
            db.delete_group(group_id)
            self.load_data()
    
    def show_button_reorder_dialog(self, group_id: int, group_name: str):
        """显示按钮全部重新排序对话框"""
        dialog = ButtonReorderDialog(group_id, group_name, parent=self)
        dialog.setWindowFlags(dialog.windowFlags() | Qt.WindowStaysOnTopHint)
        dialog.exec()
    
    def show_add_button_dialog(self):
        """显示添加按钮对话框"""
        current_index = self.tab_widget.currentIndex()
        if current_index == -1:
            QMessageBox.warning(self, "警告", "请先选择一个分组!")
            return
        
        # 获取当前分组ID
        db = DatabaseManager()
        groups = db.get_groups()
        if not groups:
            QMessageBox.warning(self, "错误", "没有可用的分组!")
            return
        
        group_id = groups[current_index][0]
        dialog = ButtonEditor(group_id=group_id, parent=self)
        dialog.setWindowFlags(dialog.windowFlags() | Qt.WindowStaysOnTopHint)
        if dialog.exec() == QDialog.Accepted:
            # 添加短暂延迟确保数据库写入完成
            QTimer.singleShot(100, self.load_data)

        
    
    def show_edit_button_dialog(self, button_id: int, name: str, path: str, 
                              arguments: str, working_dir: str, 
                              run_as_admin: bool, icon_path: str, is_favorite: bool):
        """显示编辑按钮对话框"""
        dialog = ButtonEditor(
            button_id=button_id, name=name, path=path, 
            arguments=arguments, working_dir=working_dir, 
            run_as_admin=run_as_admin, icon_path=icon_path, 
            is_favorite=is_favorite, parent=self
        )
        dialog.setWindowFlags(dialog.windowFlags() | Qt.WindowStaysOnTopHint)
        dialog.exec()
    
    def delete_button(self, button_id: int):
        """删除按钮"""
        reply = QMessageBox.question(
            self, "确认删除", 
            "确定要删除这个按钮吗?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            db = DatabaseManager()
            db.delete_button(button_id)
            self.load_data()
    
    def show_button_context_menu(self, pos, button_id: int, group_id: int, 
                               name: str, path: str, arguments: str, 
                               working_dir: str, run_as_admin: bool, 
                               icon_path: str, is_favorite: bool):
        """显示按钮的上下文菜单"""
        # 创建菜单
        menu = QMenu(self)
        
        # 编辑动作
        edit_action = menu.addAction("编辑")
        edit_action.triggered.connect(
            lambda: self.show_edit_button_dialog(
                button_id, name, path, arguments, 
                working_dir, run_as_admin, icon_path, is_favorite))
        
        # 收藏/取消收藏动作
        favorite_text = "取消收藏" if is_favorite else "收藏"
        favorite_action = menu.addAction(favorite_text)
        favorite_action.triggered.connect(
            lambda: self.toggle_button_favorite(button_id, not is_favorite))
        
        # 移动动作
        move_menu = menu.addMenu("移动到")
        
        db = DatabaseManager()
        groups = db.get_groups()
        for gid, gname, _, _ in groups:
            if gid != group_id:  # 不显示当前分组
                action = move_menu.addAction(gname)
                action.triggered.connect(
                    lambda _, bid=button_id, tgid=gid: self.move_button_to_group(bid, tgid))
        
        # 批量操作菜单
        if self.batch_mode:
            batch_menu = menu.addMenu("批量操作")
            
            # 批量移动
            batch_move_menu = batch_menu.addMenu("批量移动")
            for gid, gname, _, _ in groups:
                if gid != group_id:  # 不显示当前分组
                    action = batch_move_menu.addAction(gname)
                    action.triggered.connect(
                        lambda _, tgid=gid: self.batch_move_buttons(tgid))
            
            # 批量删除
            batch_delete_action = batch_menu.addAction("批量删除")
            batch_delete_action.triggered.connect(self.batch_delete_buttons)
        
        # 位置调整菜单
        position_menu = menu.addMenu("调整位置")
        
        move_forward_action = position_menu.addAction("前移 ↑")
        move_forward_action.triggered.connect(
            lambda: self.move_button_position_forward(button_id))
        
        move_backward_action = position_menu.addAction("后移 ↓")
        move_backward_action.triggered.connect(
            lambda: self.move_button_position_backward(button_id))
        
        # 分隔线
        menu.addSeparator()
        
        # 删除动作
        delete_action = menu.addAction("删除")
        delete_action.triggered.connect(
            lambda: self.delete_button(button_id))
        
        # 获取发送信号的按钮并显示菜单
        button = self.sender()
        if button:
            menu.exec(button.mapToGlobal(pos))
        else:
            # 如果无法获取按钮，直接使用鼠标的全局位置
            menu.exec(QCursor.pos())
    
    def toggle_button_favorite(self, button_id: int, is_favorite: bool):
        """切换按钮收藏状态"""
        db = DatabaseManager()
        db.toggle_button_favorite(button_id, is_favorite)
        self.load_data()
    
    def move_button_to_group(self, button_id: int, target_group_id: int):
        """移动按钮到另一个分组"""
        db = DatabaseManager()
        db.move_buttons_to_group([button_id], target_group_id)
        self.load_data()
    
    def move_button_position_forward(self, button_id: int):
        """将按钮在同组内向前移动一位"""
        db = DatabaseManager()
        if db.move_button_forward(button_id):
            self.load_data()
    
    def move_button_position_backward(self, button_id: int):
        """将按钮在同组内向后移动一位"""
        db = DatabaseManager()
        if db.move_button_backward(button_id):
            self.load_data()
    
    def batch_move_buttons(self, target_group_id: int):
        """批量移动按钮到另一个分组"""
        if not self.selected_buttons:
            QMessageBox.warning(self, "警告", "请先选择要移动的按钮!")
            return
        
        reply = QMessageBox.question(
            self, "确认移动", 
            f"确定要将选中的 {len(self.selected_buttons)} 个按钮移动到目标分组吗?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            db = DatabaseManager()
            db.move_buttons_to_group(list(self.selected_buttons), target_group_id)
            self.toggle_batch_mode(False)  # 退出批量模式
            self.load_data()
    
    def batch_delete_buttons(self):
        """批量删除按钮"""
        if not self.selected_buttons:
            QMessageBox.warning(self, "警告", "请先选择要删除的按钮!")
            return
        
        reply = QMessageBox.question(
            self, "确认删除", 
            f"确定要删除选中的 {len(self.selected_buttons)} 个按钮吗?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            db = DatabaseManager()
            for button_id in self.selected_buttons:
                db.delete_button(button_id)
            self.toggle_batch_mode(False)  # 退出批量模式
            self.load_data()
    
    def launch_program(self, path: str, arguments: str = "", working_dir: str = "", run_as_admin: bool = False):
        """启动指定程序或打开目录（异步执行，避免UI卡顿）"""
        def _launch():
            try:
                # 预处理路径 - 替换正斜杠为反斜杠，并去除多余的引号
                _path = path.replace('/', '\\').strip('"\'')
                
                # 预处理工作目录
                _working_dir = working_dir
                if _working_dir:
                    _working_dir = _working_dir.replace('/', '\\').strip('"\'')
                
                # 检查路径是否存在
                if not os.path.exists(_path):
                    if ':/' in _path or ':\\' in _path:
                        # 映射驱动器路径，使用信号在主线程显示警告
                        QTimer.singleShot(0, lambda: QMessageBox.warning(
                            self, "警告", f"路径 {_path} 不可访问，请检查网络连接或驱动器映射"))
                        return
                    else:
                        QTimer.singleShot(0, lambda: QMessageBox.warning(
                            self, "警告", f"路径 {_path} 不存在"))
                        return

                if os.path.isdir(_path):
                    os.startfile(_path)
                    return

                if sys.platform == "win32":
                    if run_as_admin:
                        from win32com.shell import shell
                        from win32com.shell.shell import ShellExecuteEx
                        from win32com.shell import shellcon
                        
                        params = arguments if arguments else ""
                        _working_dir = _working_dir if _working_dir else os.path.dirname(_path)
                        
                        if _working_dir and not os.path.exists(_working_dir):
                            _working_dir = None
                        
                        ShellExecuteEx(
                            nShow=win32con.SW_SHOWNORMAL,
                            fMask=shellcon.SEE_MASK_NOCLOSEPROCESS,
                            lpVerb='runas',
                            lpFile=_path,
                            lpParameters=params,
                            lpDirectory=_working_dir
                        )
                    else:
                        params = arguments if arguments else ""
                        _working_dir = _working_dir if _working_dir else os.path.dirname(_path)
                        
                        if _working_dir and not os.path.exists(_working_dir):
                            _working_dir = None
                        
                        import subprocess
                        try:
                            subprocess.Popen([_path] + params.split(), cwd=_working_dir)
                        except Exception as e:
                            os.startfile(_path)
                else:
                    cmd = f'xdg-open "{_path}"'
                    if arguments:
                        cmd += f' {arguments}'
                    os.system(cmd)
            except Exception as e:
                print(f"无法启动程序: {e}")
                QTimer.singleShot(0, lambda: QMessageBox.critical(
                    self, "错误", f"无法启动程序:\n{str(e)}"))
        
        # 使用线程池异步执行启动操作
        self._thread_pool.submit(_launch)


    
    def closeEvent(self, event):
        """窗口关闭事件"""
        # 取消所有后台图标加载线程
        self._cancel_icon_workers()
        
        # 关闭线程池
        self._thread_pool.shutdown(wait=False)
        
        # 退出时执行备份（后台）
        self.perform_backup()
        
        # 等待备份线程完成（最多3秒）
        if self._backup_worker and self._backup_worker.isRunning():
            self._backup_worker.wait(3000)
        
        self.save_window_settings()
        event.accept()
    
    def save_window_settings(self):
        """保存窗口设置"""
        settings = QSettings("ProgramLauncher", "MainWindow")
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("windowState", self.saveState())
        
        # 保存标签页顺序
        tab_order = []
        for i in range(self.tab_widget.count()):
            tab_text = self.tab_widget.tabText(i)
            tab_order.append(tab_text)
        settings.setValue("tabOrder", tab_order)
    
    def load_window_settings(self):
        """加载窗口设置"""
        settings = QSettings("ProgramLauncher", "MainWindow")
        geometry = settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        
        window_state = settings.value("windowState")
        if window_state:
            self.restoreState(window_state)
        
        # 加载标签页顺序
        tab_order = settings.value("tabOrder")
        if tab_order and isinstance(tab_order, list):
            # 我们需要重新排序标签页
            db = DatabaseManager()
            groups = {name: (gid, pos) for gid, name, pos, _ in db.get_groups()}
            
            # 创建一个从组名到位置的映射
            name_to_pos = {name: pos for pos, name in enumerate(tab_order)}
            
            # 获取所有分组并按保存的顺序排序
            all_groups = db.get_groups()
            sorted_groups = sorted(
                all_groups, 
                key=lambda x: name_to_pos.get(x[1], len(tab_order)))
            
            # 更新数据库中的顺序
            db.reorder_groups([g[0] for g in sorted_groups])
            
            # 重新加载数据
            self.load_data()

def fix_pyinstaller_permission_issue():
    """解决PyInstaller权限问题"""
    import sys
    import os
    if getattr(sys, 'frozen', False) and os.name == 'nt':
        # 如果是打包后的程序在Windows上运行
        import win32api
        import win32con
        import win32security
        
        # 获取当前可执行文件路径
        exe_path = sys.executable
        
        try:
            # 获取文件安全描述符
            sd = win32security.GetFileSecurity(
                exe_path, 
                win32security.DACL_SECURITY_INFORMATION
            )
            
            # 获取当前用户SID
            user_sid = win32security.GetTokenInformation(
                win32security.OpenProcessToken(
                    win32api.GetCurrentProcess(),
                    win32con.TOKEN_QUERY
                ),
                win32security.TokenUser
            )[0]
            
            # 添加完全控制权限
            dacl = sd.GetSecurityDescriptorDacl()
            dacl.AddAccessAllowedAce(
                win32security.ACL_REVISION,
                win32con.FILE_ALL_ACCESS,
                user_sid
            )
            
            # 应用新的安全描述符
            sd.SetSecurityDescriptorDacl(1, dacl, 0)
            win32security.SetFileSecurity(
                exe_path,
                win32security.DACL_SECURITY_INFORMATION,
                sd
            )
        except Exception as e:
            print(f"无法修复权限问题: {e}")

# 在程序启动时调用
fix_pyinstaller_permission_issue()


if __name__ == "__main__":
    # 启动异常日志捕获（适用于 Nuitka 打包后控制台隐藏的情况）
    import traceback
    import io
    
    def _setup_crash_log():
        """设置崩溃日志，将未捕获的异常写入文件"""
        log_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        log_path = os.path.join(log_dir, "crash_log.txt")
        
        def _excepthook(exc_type, exc_value, exc_tb):
            tb_lines = traceback.format_exception(exc_type, exc_value, exc_tb)
            tb_text = "".join(tb_lines)
            try:
                with open(log_path, "w", encoding="utf-8") as f:
                    f.write(f"Crash Time: {datetime.datetime.now()}\n")
                    f.write(f"Python: {sys.version}\n")
                    f.write(f"Frozen: {getattr(sys, 'frozen', False)}\n")
                    f.write(f"Executable: {sys.executable}\n\n")
                    f.write(tb_text)
            except:
                pass
            # 也输出到 stderr（如果控制台可用）
            sys.stderr.write(tb_text)
            sys.stderr.flush()
        
        sys.excepthook = _excepthook
    
    _setup_crash_log()
    
    fix_pyinstaller_permission_issue()
    app = QApplication(sys.argv)
    
    # 设置应用程序信息 - 使用 ProjectInfo 中的元数据
    app.setApplicationName(ProjectInfo.NAME)
    app.setApplicationDisplayName(ProjectInfo.NAME)
    app.setApplicationVersion(ProjectInfo.VERSION)
    
    # 设置组织信息（可选）
    app.setOrganizationName(ProjectInfo.AUTHOR)
    app.setOrganizationDomain(ProjectInfo.URL)
    
    # 创建并显示主窗口
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())