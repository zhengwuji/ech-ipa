# 主程序入口
import sys
import os
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer
from ui.main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("网站监控工具")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()

