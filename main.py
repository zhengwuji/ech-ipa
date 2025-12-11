# 主程序入口
import sys
import os
import traceback

# 添加当前目录到Python路径，确保打包后能正确导入模块
if getattr(sys, 'frozen', False):
    # 如果是打包后的exe，使用exe所在目录
    application_path = os.path.dirname(sys.executable)
else:
    # 如果是开发模式，使用脚本所在目录
    application_path = os.path.dirname(os.path.abspath(__file__))

if application_path not in sys.path:
    sys.path.insert(0, application_path)

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

