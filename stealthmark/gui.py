import sys
sys.path.insert(0, 'D:\\work\\code\\stealthmark\\src')

import os
from pathlib import Path
from typing import List

from PyQt6 import QtWidgets, QtCore, QtGui
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QPushButton, QComboBox,
    QListWidget, QTableWidget, QTableWidgetItem, QProgressBar,
    QFileDialog, QMessageBox, QGroupBox, QCheckBox, QMenuBar, QMenu,
    QStyleFactory, QAbstractItemView,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QRunnable, QThreadPool
from PyQt6.QtGui import QAction

from src.core.manager import StealthMark
from src.core.base import WatermarkStatus


# ==================== Supported Extensions ====================
SUPPORTED_EXTENSIONS = {
    '.pdf', '.docx', '.pptx', '.xlsx', '.odt', '.odp', '.ods',
    '.epub', '.rtf', '.png', '.jpg', '.jpeg', '.bmp', '.tiff',
    '.tif', '.webp', '.gif', '.heic', '.heif', '.wav', '.mp3',
    '.flac', '.aac', '.m4a', '.mp4', '.avi', '.mkv', '.mov',
    '.webm', '.wmv',
}


# ==================== Worker Thread ====================

class WatermarkWorker(QThread):
    """Run watermarking operations in background thread."""
    progress = pyqtSignal(int, int, str)   # current, total, filename
    result_ready = pyqtSignal(dict)          # {filename, success, message, watermark, match}
    finished_all = pyqtSignal(int, int)      # success_count, failed_count

    def __init__(
        self,
        files: List[str],
        action: str,
        watermark: str,
        password: str,
        output_dir: str,
        filename_pattern: str,
        overwrite: bool,
    ):
        super().__init__()
        self.files = files
        self.action = action
        self.watermark = watermark
        self.password = password
        self.output_dir = output_dir
        self.filename_pattern = filename_pattern
        self.overwrite = overwrite
        self._sm = StealthMark(password=self.password or None)
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def _output_path(self, src_path: str) -> str:
        src = Path(src_path)
        if self.overwrite:
            return str(src)
        # Apply filename pattern
        out_name = self.filename_pattern.replace('{name}', src.stem).replace('{ext}', src.suffix)
        return os.path.join(self.output_dir, out_name)

    def run(self):
        success_count = 0
        failed_count = 0
        total = len(self.files)

        for idx, filepath in enumerate(self.files):
            if self._cancelled:
                break
            self.progress.emit(idx + 1, total, Path(filepath).name)
            try:
                if self.action == 'embed':
                    out = self._output_path(filepath)
                    r = self._sm.embed(filepath, self.watermark, out)
                    self.result_ready.emit({
                        'filename': Path(filepath).name,
                        'success': r.is_success,
                        'message': r.message,
                        'watermark': self.watermark,
                        'match': None,
                    })
                    if r.is_success:
                        success_count += 1
                    else:
                        failed_count += 1

                elif self.action == 'extract':
                    r = self._sm.extract(filepath)
                    content = r.watermark.content if r.watermark else None
                    self.result_ready.emit({
                        'filename': Path(filepath).name,
                        'success': r.is_success,
                        'message': r.message,
                        'watermark': content,
                        'match': None,
                    })
                    if r.is_success:
                        success_count += 1
                    else:
                        failed_count += 1

                else:  # verify
                    r = self._sm.verify(filepath, self.watermark)
                    self.result_ready.emit({
                        'filename': Path(filepath).name,
                        'success': r.is_success,
                        'message': r.message,
                        'watermark': r.details.get('extracted') if r.details else None,
                        'match': r.is_valid,
                    })
                    if r.is_success:
                        success_count += 1
                    else:
                        failed_count += 1

            except Exception as e:
                self.result_ready.emit({
                    'filename': Path(filepath).name,
                    'success': False,
                    'message': str(e),
                    'watermark': None,
                    'match': None,
                })
                failed_count += 1

        self.finished_all.emit(success_count, failed_count)


# ==================== Main Window ====================

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self._files: List[str] = []
        self._worker: WatermarkWorker = None
        self._pool = QThreadPool()
        self._pool.setMaxThreadCount(1)
        self._result_rows = {}  # filename -> row index

        self.setWindowTitle("StealthMark - 隐式水印工具")
        self.resize(950, 720)
        self.setMinimumSize(800, 600)

        self._setup_ui()
        self._connect_signals()
        self._load_styles()

    # ---- UI Setup ----

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 12)
        layout.setSpacing(6)

        # Menu bar
        self._setup_menu()

        # Top: File Selection
        self._setup_file_panel(layout)

        # Middle: Settings
        self._setup_settings_panel(layout)

        # Bottom: Action + Progress
        self._setup_action_panel(layout)

        # Results Table
        self._setup_results_panel(layout)

    def _setup_menu(self):
        menubar = QMenuBar(self)
        file_menu = menubar.addMenu("文件")
        exit_action = QAction("退出", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        help_menu = menubar.addMenu("帮助")
        about_action = QAction("关于", self)
        about_action.triggered.connect(self._about)
        help_menu.addAction(about_action)

        layout = QVBoxLayout()
        layout.setMenuBar(menubar)

    def _setup_file_panel(self, parent_layout):
        group = QGroupBox("文件选择")
        g = QVBoxLayout(group)

        btn_row = QHBoxLayout()
        self.btn_select_file = QPushButton("选择文件")
        self.btn_select_folder = QPushButton("选择文件夹")
        self.btn_clear = QPushButton("清空列表")
        btn_row.addWidget(self.btn_select_file)
        btn_row.addWidget(self.btn_select_folder)
        btn_row.addWidget(self.btn_clear)
        btn_row.addStretch()
        g.addLayout(btn_row)

        self.file_list = QListWidget()
        self.file_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.file_list.setAcceptDrops(True)
        self.file_list.setDragDropMode(QAbstractItemView.DragDropMode.DropOnly)
        self.file_list.setMinimumHeight(80)
        self.file_list.setTextElideMode(Qt.TextElideMode.ElideMiddle)
        g.addWidget(self.file_list)

        self.lbl_count = QLabel("共 0 个文件")
        g.addWidget(self.lbl_count)

        parent_layout.addWidget(group)

    def _setup_settings_panel(self, parent_layout):
        grid = QGridLayout()

        # Action mode
        lbl_mode = QLabel("操作模式:")
        self.cmb_mode = QComboBox()
        self.cmb_mode.addItems(["嵌入水印", "提取水印", "验证水印"])
        grid.addWidget(lbl_mode, 0, 0)
        grid.addWidget(self.cmb_mode, 0, 1, 1, 3)

        # Watermark text
        lbl_wm = QLabel("水印内容:")
        self.edit_watermark = QLineEdit()
        self.edit_watermark.setPlaceholderText("输入水印内容")
        grid.addWidget(lbl_wm, 1, 0)
        grid.addWidget(self.edit_watermark, 1, 1, 1, 3)

        # Password
        lbl_pwd = QLabel("密码(可选):")
        self.edit_password = QLineEdit()
        self.edit_password.setPlaceholderText("留空则不加密")
        self.edit_password.setEchoMode(QLineEdit.EchoMode.Password)
        grid.addWidget(lbl_pwd, 2, 0)
        grid.addWidget(self.edit_password, 2, 1, 1, 3)

        # Output directory
        lbl_out = QLabel("输出目录:")
        self.edit_output_dir = QLineEdit()
        self.edit_output_dir.setText(os.getcwd())
        self.btn_browse_out = QPushButton("浏览")
        grid.addWidget(lbl_out, 3, 0)
        grid.addWidget(self.edit_output_dir, 3, 1)
        grid.addWidget(self.btn_browse_out, 3, 2)
        self.chk_overwrite = QCheckBox("覆盖原文件")
        grid.addWidget(self.chk_overwrite, 3, 3)

        # Filename pattern
        lbl_pattern = QLabel("命名模式:")
        self.edit_pattern = QLineEdit()
        self.edit_pattern.setText("{name}_wm{ext}")
        self.edit_pattern.setToolTip("{name}=原文件名(不含后缀), {ext}=原扩展名\n嵌入时生效，覆盖原文件时忽略")
        lbl_pattern.setToolTip("{name}=原文件名, {ext}=扩展名")
        grid.addWidget(lbl_pattern, 4, 0)
        grid.addWidget(self.edit_pattern, 4, 1, 1, 3)

        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 1)
        grid.setColumnStretch(3, 1)

        group = QGroupBox("设置")
        group.setLayout(grid)
        parent_layout.addWidget(group)

    def _setup_action_panel(self, parent_layout):
        h = QHBoxLayout()

        self.btn_start = QPushButton("开始处理")
        self.btn_start.setMinimumHeight(42)
        font = self.btn_start.font()
        font.setPointSize(11)
        font.setBold(True)
        self.btn_start.setFont(font)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimumHeight(20)

        self.lbl_status = QLabel("就绪")
        self.lbl_status.setStyleSheet("color: #666;")
        self.lbl_status.setMinimumWidth(180)

        h.addWidget(self.btn_start)
        h.addWidget(self.progress_bar, 1)
        h.addWidget(self.lbl_status)

        parent_layout.addLayout(h)

    def _setup_results_panel(self, parent_layout):
        group = QGroupBox("处理结果")
        g = QVBoxLayout(group)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["文件", "状态", "水印内容", "详情"])
        self.table.setMinimumHeight(180)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        # Auto-resize last column
        header = self.table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeMode.Stretch)

        g.addWidget(self.table)
        parent_layout.addWidget(group, 1)  # stretch

    def _load_styles(self):
        self.setStyle(QStyleFactory.create("Fusion"))
        palette = self.palette()
        palette.setColor(QtGui.QPalette.ColorRole.Window, QtGui.QColor(240, 240, 245))
        palette.setColor(QtGui.QPalette.ColorRole.Base, QtGui.QColor(255, 255, 255))
        palette.setColor(QtGui.QPalette.ColorRole.Highlight, QtGui.QColor(42, 99, 177))
        self.setPalette(palette)

        green = "background-color: #4CAF50; color: white; font-weight: bold;"
        self.btn_start.setStyleSheet(
            "QPushButton { background-color: #2E7D32; color: white; "
            "font-weight: bold; border-radius: 6px; padding: 6px; }"
            "QPushButton:pressed { background-color: #1B5E20; }"
            "QPushButton:disabled { background-color: #A5D6A7; color: #ccc; }"
        )

    # ---- Signals ----

    def _connect_signals(self):
        self.btn_select_file.clicked.connect(self._on_select_file)
        self.btn_select_folder.clicked.connect(self._on_select_folder)
        self.btn_clear.clicked.connect(self._on_clear)
        self.btn_browse_out.clicked.connect(self._on_browse_output)
        self.btn_start.clicked.connect(self._on_start)
        self.file_list.model().rowsInserted.connect(self._update_count)
        self.file_list.model().rowsRemoved.connect(self._update_count)
        self.file_list.files_dropped = self._on_files_dropped
        self.file_list.dragEnterEvent = lambda e: e.acceptProposedAction()
        self.file_list.dragMoveEvent = lambda e: e.acceptProposedAction()
        self.file_list.dropEvent = self._on_drop

        self.cmb_mode.currentIndexChanged.connect(self._on_mode_changed)
        self._on_mode_changed(0)

    def _on_mode_changed(self, idx):
        labels = ["嵌入水印", "提取水印", "验证水印"]
        mode = labels[idx]
        self.edit_watermark.setEnabled(mode != "提取水印")
        self.edit_pattern.setEnabled(mode == "嵌入水印")

    # ---- File Handling ----

    def _add_files(self, paths: List[str]):
        for p in paths:
            if p in self._files:
                continue
            ext = Path(p).suffix.lower()
            if ext not in SUPPORTED_EXTENSIONS:
                continue
            self._files.append(p)
            self.file_list.addItem(p)
        self._update_count()

    def _on_select_file(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择文件", os.getcwd(),
            "所有支持的文件 (*)",
        )
        self._add_files(files)

    def _on_select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "选择文件夹", os.getcwd())
        if not folder:
            return
        files = []
        for root, _, fnames in os.walk(folder):
            for fname in fnames:
                if Path(fname).suffix.lower() in SUPPORTED_EXTENSIONS:
                    files.append(os.path.join(root, fname))
        self._add_files(files)

    def _on_clear(self):
        self._files.clear()
        self.file_list.clear()
        self._update_count()
        self.table.setRowCount(0)
        self._result_rows.clear()

    def _on_drop(self, event):
        paths = [u.toLocalFile() for u in event.mimeData().urls()]
        self._add_files(paths)

    def _update_count(self):
        n = len(self._files)
        self.lbl_count.setText(f"共 {n} 个文件")

    # ---- Output ----

    def _on_browse_output(self):
        folder = QFileDialog.getExistingDirectory(
            self, "选择输出目录", self.edit_output_dir.text(),
        )
        if folder:
            self.edit_output_dir.setText(folder)

    # ---- Processing ----

    def _on_start(self):
        if not self._files:
            QMessageBox.warning(self, "提示", "请先选择文件！")
            return

        action_map = {0: "embed", 1: "extract", 2: "verify"}
        action = action_map[self.cmb_mode.currentIndex()]

        if action in ("embed", "verify") and not self.edit_watermark.text().strip():
            QMessageBox.warning(self, "提示", "请输入水印内容！")
            self.edit_watermark.setFocus()
            return

        output_dir = self.edit_output_dir.text().strip()
        if not self.chk_overwrite.isChecked() and action == "embed":
            if not output_dir or not os.path.isdir(output_dir):
                QMessageBox.warning(self, "提示", "请选择有效的输出目录！")
                self.edit_output_dir.setFocus()
                return

        self._start_processing(action)

    def _start_processing(self, action: str):
        self.btn_start.setEnabled(False)
        self.table.setRowCount(0)
        self._result_rows.clear()
        self.progress_bar.setValue(0)
        self.lbl_status.setText("处理中...")

        self._worker = WatermarkWorker(
            files=self._files,
            action=action,
            watermark=self.edit_watermark.text().strip(),
            password=self.edit_password.text(),
            output_dir=self.edit_output_dir.text().strip(),
            filename_pattern=self.edit_pattern.text().strip(),
            overwrite=self.chk_overwrite.isChecked(),
        )
        self._worker.progress.connect(self._on_progress)
        self._worker.result_ready.connect(self._on_result)
        self._worker.finished_all.connect(self._on_finished)
        self._worker.start()

    def _on_progress(self, current: int, total: int, filename: str):
        pct = int(current / total * 100)
        self.progress_bar.setValue(pct)
        self.lbl_status.setText(f"[{current}/{total}] {filename}")

    def _on_result(self, data: dict):
        row = self.table.rowCount()
        self.table.insertRow(row)
        fn = data['filename']
        self._result_rows[fn] = row

        # Status icon + text
        ok = data['success']
        item_fn = QTableWidgetItem(fn)
        item_fn.setBackground(QtGui.QColor(220, 255, 220) if ok else QtGui.QColor(255, 220, 220))
        item_st = QTableWidgetItem("[OK]" if ok else "[FAIL]")
        item_st.setForeground(QtGui.QColor(0, 120, 0) if ok else QtGui.QColor(180, 0, 0))
        item_wm = QTableWidgetItem(data.get('watermark') or "")
        item_msg = QTableWidgetItem(data.get('message', ''))

        self.table.setItem(row, 0, item_fn)
        self.table.setItem(row, 1, item_st)
        self.table.setItem(row, 2, item_wm)
        self.table.setItem(row, 3, item_msg)

        if data.get('match') is not None:
            match_icon = "[OK]" if data['match'] else "[FAIL]"
            match_item = QTableWidgetItem(f"{match_icon} {data.get('message','')}")
            self.table.setItem(row, 3, match_item)

        self.table.resizeRowsToContents()

    def _on_finished(self, success: int, failed: int):
        self.btn_start.setEnabled(True)
        self.progress_bar.setValue(100)
        total = success + failed
        self.lbl_status.setText(f"完成：{success} 成功，{failed} 失败")
        self._worker = None

    # ---- About ----

    def _about(self):
        QMessageBox.about(
            self,
            "关于 StealthMark",
            "<b>StealthMark</b> v1.0.0<br>"
            "隐式水印工具 - 支持 30+ 格式<br><br>"
            "支持格式：PDF、DOCX、PPTX、XLSX、ODT、ODP、ODS、"
            "EPUB、RTF、PNG、JPG、BMP、TIFF、WebP、GIF、HEIC、"
            "WAV、MP3、FLAC、AAC、M4A、MP4、AVI、MKV、MOV、WebM、WMV<br><br>"
            "<a href='https://github.com/qqtou/stealthmark'>GitHub: qqtou/stealthmark</a>",
        )
