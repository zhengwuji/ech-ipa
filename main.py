import sys
from PyQt5 import QtWidgets

from ui.main_window import MainWindow
import version


def main():
    print(f"启动版本：{version.current_version()}")
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

