import sys
import subprocess
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QPushButton, QSpinBox, QComboBox, QMessageBox, QGroupBox)
from PyQt5.QtCore import Qt, QTimer


class UpdatePauser(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Windows 更新暂停工具")
        self.resize(500, 350)
        
        # 主界面布局
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        # 当前状态显示
        self.status_group = QGroupBox("当前更新状态")
        self.status_layout = QVBoxLayout()
        
        self.current_status_label = QLabel("正在检测当前状态...")
        self.next_update_label = QLabel()
        self.paused_until_label = QLabel()
        
        self.status_layout.addWidget(self.current_status_label)
        self.status_layout.addWidget(self.next_update_label)
        self.status_layout.addWidget(self.paused_until_label)
        self.status_group.setLayout(self.status_layout)
        
        # 暂停更新设置
        self.pause_group = QGroupBox("暂停更新设置")
        self.pause_layout = QVBoxLayout()
        
        self.duration_layout = QHBoxLayout()
        self.duration_spinbox = QSpinBox()
        self.duration_spinbox.setMinimum(1)
        self.duration_spinbox.setMaximum(99999)
        self.duration_spinbox.setValue(7)
        
        self.unit_combobox = QComboBox()
        self.unit_combobox.addItems(["天", "周", "月", "年", "百年", "千年", "万年", "永久"])
        
        self.duration_layout.addWidget(self.duration_spinbox)
        self.duration_layout.addWidget(self.unit_combobox)
        self.duration_layout.addStretch()
        
        self.pause_button = QPushButton("暂停更新")
        self.pause_button.clicked.connect(self.pause_updates)
        
        self.resume_button = QPushButton("恢复更新")
        self.resume_button.clicked.connect(self.resume_updates)
        
        self.pause_layout.addLayout(self.duration_layout)
        self.pause_layout.addWidget(self.pause_button)
        self.pause_layout.addWidget(self.resume_button)
        self.pause_group.setLayout(self.pause_layout)
        
        # 添加到主布局
        layout.addWidget(self.status_group)
        layout.addWidget(self.pause_group)
        
        # 状态检测定时器
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_update_status)
        self.timer.start(1000)
        
        # 初始状态检测
        self.check_update_status()
        
        # 设置样式
        self.setStyleSheet("""
            QGroupBox {
                font-size: 14px;
                font-weight: bold;
                margin-top: 10px;
                border: 1px solid gray;
                border-radius: 5px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px;
            }
            QLabel {
                font-size: 13px;
            }
            QPushButton {
                font-size: 14px;
                padding: 5px;
                min-height: 30px;
            }
            QSpinBox {
                font-size: 14px;
                padding: 5px;
            }
            QComboBox {
                font-size: 14px;
                padding: 5px;
            }
        """)
    
    def check_update_status(self):
        try:
            # 检查更新服务状态
            result = subprocess.run(
                ["sc", "query", "wuauserv"],
                capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            if "RUNNING" in result.stdout:
                self.current_status_label.setText("Windows Update 服务状态: <font color='green'>运行中</font>")
            else:
                self.current_status_label.setText("Windows Update 服务状态: <font color='red'>已停止</font>")
            
            # 检查暂停状态
            result = subprocess.run(
                ["reg", "query", "HKLM\\SOFTWARE\\Microsoft\\WindowsUpdate\\UX\\Settings", "/v", "FlightSettingsMaxPauseDays"],
                capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            if "FlightSettingsMaxPauseDays" in result.stdout:
                max_pause_days = int(result.stdout.split()[-1])
                self.paused_until_label.setText(f"最大可暂停天数: {max_pause_days} 天")
            else:
                self.paused_until_label.setText("最大可暂停天数: 未设置")
            
            # 检查下次更新时间
            result = subprocess.run(
                ["powershell", "-Command", "(Get-ItemProperty -Path 'HKLM:\\SOFTWARE\\Microsoft\\WindowsUpdate\\UX\\Settings').PausedFeatureUpdateEndTime"],
                capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            if result.stdout.strip():
                end_time = result.stdout.strip()
                try:
                    end_time = datetime.strptime(end_time.split(".")[0], "%Y-%m-%d %H:%M:%S")
                    now = datetime.now()
                    if end_time > now:
                        remaining = end_time - now
                        days = remaining.days
                        hours = remaining.seconds // 3600
                        self.next_update_label.setText(f"更新已暂停至: {end_time.strftime('%Y-%m-%d %H:%M')} (剩余 {days}天 {hours}小时)")
                    else:
                        self.next_update_label.setText("更新暂停已过期")
                except ValueError:
                    self.next_update_label.setText("下次更新时间: 未知")
            else:
                self.next_update_label.setText("更新未暂停")
                
        except Exception as e:
            self.current_status_label.setText(f"状态检测错误: {str(e)}")
    
    def pause_updates(self):
        duration = self.duration_spinbox.value()
        unit = self.unit_combobox.currentText()
        
        # 转换为天数
        if unit == "天":
            days = duration
        elif unit == "周":
            days = duration * 7
        elif unit == "月":
            days = duration * 30
        elif unit == "年":
            days = duration * 365
        elif unit == "百年":
            days = duration * 365 * 100
        elif unit == "千年":
            days = duration * 365 * 1000
        elif unit == "万年":
            days = duration * 365 * 10000
        else:  # 永久
            days = 365 * 10000  # 设置一个非常大的值
            
        try:
            # 设置最大暂停天数
            subprocess.run(
                ["reg", "add", "HKLM\\SOFTWARE\\Microsoft\\WindowsUpdate\\UX\\Settings", 
                 "/v", "FlightSettingsMaxPauseDays", "/t", "REG_DWORD", "/d", str(days), "/f"],
                check=True, creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            # 暂停更新
            subprocess.run(
                ["powershell", "-Command", "Suspend-WindowsUpdate", "-Confirm:$false"],
                check=True, creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            # 停止更新服务
            subprocess.run(
                ["net", "stop", "wuauserv"],
                check=True, creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            # 如果是永久暂停，额外设置一些注册表项
            if unit == "永久":
                # 禁用自动更新
                subprocess.run(
                    ["reg", "add", "HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows\\WindowsUpdate\\AU",
                     "/v", "NoAutoUpdate", "/t", "REG_DWORD", "/d", "1", "/f"],
                    check=True, creationflags=subprocess.CREATE_NO_WINDOW
                )
                # 禁用更新服务
                subprocess.run(
                    ["sc", "config", "wuauserv", "start=", "disabled"],
                    check=True, creationflags=subprocess.CREATE_NO_WINDOW
                )
            
            QMessageBox.information(self, "成功", f"已成功暂停 Windows 更新 {duration} {unit}")
            self.check_update_status()
            
        except subprocess.CalledProcessError as e:
            QMessageBox.critical(self, "错误", f"暂停更新失败: {str(e)}")
    
    def resume_updates(self):
        try:
            # 恢复更新
            subprocess.run(
                ["powershell", "-Command", "Resume-WindowsUpdate"],
                check=True, creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            # 启动更新服务
            subprocess.run(
                ["net", "start", "wuauserv"],
                check=True, creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            # 如果是永久暂停恢复的，需要重新启用自动更新
            subprocess.run(
                ["reg", "add", "HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows\\WindowsUpdate\\AU",
                 "/v", "NoAutoUpdate", "/t", "REG_DWORD", "/d", "0", "/f"],
                check=True, creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            # 设置服务为自动启动
            subprocess.run(
                ["sc", "config", "wuauserv", "start=", "auto"],
                check=True, creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            QMessageBox.information(self, "成功", "已恢复 Windows 更新")
            self.check_update_status()
            
        except subprocess.CalledProcessError as e:
            QMessageBox.critical(self, "错误", f"恢复更新失败: {str(e)}")


if __name__ == "__main__":
    # 适配高DPI屏幕
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
    
    app = QApplication(sys.argv)
    window = UpdatePauser()
    window.show()
    sys.exit(app.exec_())