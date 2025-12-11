from typing import Callable, Dict, Optional
from PyQt5 import QtCore, QtGui, QtWidgets


class RegionSelector(QtWidgets.QWidget):
    finished: Callable[[Optional[Dict[str, float]]], None]

    def __init__(self, image_path: str, on_finish: Callable[[Optional[Dict[str, float]]], None]):
        super().__init__()
        self.image_path = image_path
        self.on_finish = on_finish
        self.setWindowTitle("选择监控区域")
        self.setWindowModality(QtCore.Qt.ApplicationModal)
        self.pixmap = QtGui.QPixmap(image_path)
        self.label = QtWidgets.QLabel()
        self.label.setPixmap(self.pixmap)
        self.label.setAlignment(QtCore.Qt.AlignCenter)
        self.selection = None
        self.dragging = False
        self.start_pos = QtCore.QPoint()
        self.end_pos = QtCore.QPoint()

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.label)

        btn_row = QtWidgets.QHBoxLayout()
        ok_btn = QtWidgets.QPushButton("确定")
        cancel_btn = QtWidgets.QPushButton("取消")
        ok_btn.clicked.connect(self._accept)
        cancel_btn.clicked.connect(self._cancel)
        btn_row.addStretch()
        btn_row.addWidget(ok_btn)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)
        self.setLayout(layout)
        self.resize(self.pixmap.width(), self.pixmap.height())

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.dragging = True
            self.start_pos = event.pos()
            self.end_pos = event.pos()
            self.update()

    def mouseMoveEvent(self, event):
        if self.dragging:
            self.end_pos = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton and self.dragging:
            self.dragging = False
            self.end_pos = event.pos()
            self._store_selection()
            self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.start_pos and self.end_pos:
            painter = QtGui.QPainter(self)
            painter.setPen(QtGui.QPen(QtGui.QColor(255, 0, 0), 2, QtCore.Qt.DashLine))
            rect = QtCore.QRect(self.start_pos, self.end_pos).normalized()
            painter.drawRect(rect)

    def _store_selection(self):
        rect = QtCore.QRect(self.start_pos, self.end_pos).normalized()
        if rect.width() < 5 or rect.height() < 5:
            self.selection = None
            return
        x_ratio = rect.x() / self.pixmap.width()
        y_ratio = rect.y() / self.pixmap.height()
        w_ratio = rect.width() / self.pixmap.width()
        h_ratio = rect.height() / self.pixmap.height()
        self.selection = {
            "x_ratio": x_ratio,
            "y_ratio": y_ratio,
            "w_ratio": w_ratio,
            "h_ratio": h_ratio,
            "ref_width": self.pixmap.width(),
            "ref_height": self.pixmap.height(),
        }

    def _accept(self):
        self.on_finish(self.selection)
        self.close()

    def _cancel(self):
        self.on_finish(None)
        self.close()

