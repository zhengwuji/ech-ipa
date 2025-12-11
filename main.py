# 主程序入口
import sys
import os
import traceback
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import QTimer

def main():
    try:
        app = QApplication(sys.argv)
        app.setApplicationName("网站监控工具")
        
        from ui.main_window import MainWindow
        window = MainWindow()
        window.show()
        
        sys.exit(app.exec_())
    except Exception as e:
        error_msg = f"程序启动失败:\n{str(e)}\n\n详细信息:\n{traceback.format_exc()}"
        print(error_msg)
        try:
            QMessageBox.critical(None, "严重错误", error_msg)
        except:
            pass
        sys.exit(1)

if __name__ == '__main__':
    main()

