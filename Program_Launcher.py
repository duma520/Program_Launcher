import os
import sys
import shutil
import glob
import datetime
import pinyin
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QLineEdit, QTabWidget, QMessageBox,
                             QFileDialog, QGroupBox, QScrollArea, QSizePolicy, QSpacerItem,
                             QMenu, QTableWidget, QTableWidgetItem, QDialog, QLayout,
                             QCheckBox, QAction, QComboBox, QInputDialog)
from PyQt5.QtCore import Qt, QSize, QSettings, QTimer, QRect, QPoint, pyqtSignal
from PyQt5.QtGui import QIcon, QColor, QTextCursor, QTextCharFormat, QFont, QPixmap
from PIL import Image, ImageDraw, ImageFont
import sqlite3
import win32api
import win32con
import win32process
import win32gui
from typing import Optional, List, Tuple, Dict, Any

class ProjectInfo:
    """项目信息元数据（集中管理所有项目相关信息）"""
    VERSION = "1.6.0"
    BUILD_DATE = "2025-05-24"
    AUTHOR = "杜玛"
    LICENSE = "MIT"
    COPYRIGHT = "© 永久 杜玛"
    URL = "https://github.com/duma520"
    MAINTAINER_EMAIL = "不提供"
    NAME = "程序启动器"
    DESCRIPTION = "程序启动器，基于PyQt5的桌面应用程序"
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
        """从exe文件中提取图标"""
        try:
            if not output_path:
                output_path = os.path.join("icons", os.path.basename(exe_path) + ".ico")
            
            if not os.path.exists("icons"):
                os.makedirs("icons")
            
            # 使用win32api提取图标
            large, small = win32gui.ExtractIconEx(exe_path, 0)
            if large:
                win32gui.DestroyIcon(large[0])
                # 保存图标
                icon = win32gui.LoadImage(0, exe_path, win32con.IMAGE_ICON, 0, 0, win32con.LR_LOADFROMFILE | win32con.LR_DEFAULTSIZE)
                win32gui.SaveImage(icon, output_path, win32con.IMAGE_ICON)
                return output_path
        except Exception as e:
            print(f"提取图标失败: {str(e)}")
            return None

class DatabaseManager:
    def __init__(self):
        self.db_path = "launcher.db"
        self._init_db()
        self._init_backup_dir()  # 新增初始化备份目录方法

    def _init_backup_dir(self):
        """初始化备份目录"""
        if not os.path.exists("backups"):
            os.makedirs("backups")
    
    def backup_database(self):
        """备份数据库到backups目录"""
        try:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = os.path.join("backups", f"launcher_backup_{timestamp}.db")
            shutil.copy2(self.db_path, backup_path)
            
            # 保留最多5个备份文件
            backups = sorted(glob.glob(os.path.join("backups", "launcher_backup_*.db")))
            if len(backups) > 5:
                for old_backup in backups[:-5]:
                    os.remove(old_backup)
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
        """获取所有分组"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, position, is_favorite FROM groups ORDER BY is_favorite DESC, position")
            return cursor.fetchall()
    
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
        """浏览文件系统选择程序"""
        path, _ = QFileDialog.getOpenFileName(
            self, "选择程序", "", "可执行文件 (*.exe *.bat *.cmd);;所有文件 (*.*)")
        if path:
            self.path_edit.setText(path)
            # 如果没有选择图标且是EXE文件，自动提取图标
            if not self.icon_path and path.lower().endswith('.exe'):
                icon_path = DynamicIconGenerator.extract_exe_icon(path)
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
        
        # 如果没有选择图标且路径是EXE文件，尝试自动提取图标
        icon_path = self.icon_path
        if not icon_path and path.lower().endswith('.exe'):
            icon_path = DynamicIconGenerator.extract_exe_icon(path)
    
        db = DatabaseManager()
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

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # 设置窗口标题和图标
        self.setWindowTitle(f"{ProjectInfo.NAME} {ProjectInfo.VERSION} (Build: {ProjectInfo.BUILD_DATE})")
        self.set_application_icon()
        
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

        # 添加定时备份
        self.backup_timer = QTimer(self)
        self.backup_timer.timeout.connect(self.perform_backup)
        self.backup_timer.start(3600000)  # 每小时备份一次 (3600000毫秒)
        
        # 初始化批量选择模式
        self.batch_mode = False
        self.selected_buttons = set()
        
        # 加载数据
        self.load_data()
        
        # 加载窗口设置
        self.load_window_settings()

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
    
    def perform_backup(self):
        """执行数据库备份"""
        db = DatabaseManager()
        if db.backup_database():
            print(f"数据库已自动备份于 {datetime.datetime.now()}")
        else:
            print("数据库自动备份失败")

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
        
        self.main_layout.addLayout(control_layout)
    
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
                    for btn in buttons_group.findChildren(QPushButton):
                        btn.setStyleSheet("")
    
    def load_data(self):
        """加载分组和按钮数据"""
        # 清除现有标签页
        while self.tab_widget.count() > 0:
            self.tab_widget.removeTab(0)
        
        db = DatabaseManager()
        groups = db.get_groups()
        
        if not groups:
            # 如果没有分组，添加一个默认分组
            default_group_id = db.add_group("默认分组")
            groups = db.get_groups()
        
        for group_id, group_name, _, is_favorite in groups:
            self.add_group_tab(group_id, group_name, is_favorite)
    
    def add_group_tab(self, group_id: int, group_name: str, is_favorite: bool):
        """添加分组标签页"""
        tab = QWidget()
        tab_layout = QVBoxLayout(tab)
        
        # 创建滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        
        # 添加分组标题和编辑按钮
        header_layout = QHBoxLayout()
        
        # 收藏星标
        favorite_icon = QLabel()
        favorite_icon.setPixmap(QIcon(":star.png").pixmap(16, 16)) if is_favorite else favorite_icon.clear()
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
        
        header_layout.addItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        scroll_layout.addLayout(header_layout)
        
        # 添加按钮区域 - 修改为流式布局
        buttons_group = QGroupBox()
        buttons_layout = FlowLayout()  # 使用自定义的流式布局
        buttons_group.setLayout(buttons_layout)
        
        db = DatabaseManager()
        buttons = db.get_buttons(group_id)
        
        if not buttons:
            # 如果没有按钮，显示提示信息
            no_buttons_label = QLabel('此分组没有按钮，点击右上角的"添加按钮"来添加。')
            no_buttons_label.setAlignment(Qt.AlignCenter)
            buttons_layout.addWidget(no_buttons_label)
        else:
            # 添加所有按钮
            for button_id, name, path, args, working_dir, run_as_admin, icon_path, _, is_favorite in buttons:
                btn = QPushButton(name)
                btn.setToolTip(f"路径: {path}\n参数: {args}\n工作目录: {working_dir}")
                
                # 设置按钮固定大小
                btn.setFixedSize(120, 60)
                
                # 设置按钮图标
                if icon_path and os.path.exists(icon_path):
                    btn.setIcon(QIcon(icon_path))
                    btn.setIconSize(QSize(32, 32))
                
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
        
        scroll_layout.addWidget(buttons_group)
        scroll_layout.addItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))
        
        scroll.setWidget(scroll_content)
        tab_layout.addWidget(scroll)
        
        # 添加标签页
        self.tab_widget.addTab(tab, group_name)
        if is_favorite:
            self.tab_widget.tabBar().setTabTextColor(self.tab_widget.count()-1, QColor(255, 102, 0))
    
    def toggle_button_selection(self, button_id: int, button: QPushButton):
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
        dialog.exec_()
    
    def show_edit_group_dialog(self, group_id: int, name: str, is_favorite: bool):
        """显示编辑分组对话框"""
        dialog = GroupEditor(group_id=group_id, name=name, is_favorite=is_favorite, parent=self)
        dialog.setWindowFlags(dialog.windowFlags() | Qt.WindowStaysOnTopHint)
        dialog.exec_()
    
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
        dialog.exec_()
    
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
        dialog.exec_()
    
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
        
        # 删除动作
        delete_action = menu.addAction("删除")
        delete_action.triggered.connect(
            lambda: self.delete_button(button_id))
        
        # 显示菜单
        menu.exec_(self.sender().mapToGlobal(pos))
    
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
        """启动指定程序"""
        try:
            if sys.platform == "win32":
                if run_as_admin:
                    # 以管理员权限运行
                    from win32com.shell import shell
                    from win32com.shell.shell import ShellExecuteEx
                    from win32com.shell import shellcon
                    
                    params = f'"{path}" {arguments}' if arguments else f'"{path}"'
                    working_dir = working_dir if working_dir else os.path.dirname(path)
                    
                    ShellExecuteEx(
                        nShow=win32con.SW_SHOWNORMAL,
                        fMask=shellcon.SEE_MASK_NOCLOSEPROCESS,
                        lpVerb='runas',
                        lpFile=path,
                        lpParameters=arguments,
                        lpDirectory=working_dir
                    )
                else:
                    # 普通方式运行
                    params = f'"{path}" {arguments}' if arguments else f'"{path}"'
                    working_dir = working_dir if working_dir else os.path.dirname(path)
                    os.chdir(working_dir)
                    os.startfile(params)
            else:
                # 非Windows系统
                cmd = f'xdg-open "{path}"'
                if arguments:
                    cmd += f' {arguments}'
                os.system(cmd)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法启动程序:\n{str(e)}")
    
    def closeEvent(self, event):
        """窗口关闭事件"""
        # 退出时执行备份
        self.perform_backup()
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

if __name__ == "__main__":
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
    
    sys.exit(app.exec_())