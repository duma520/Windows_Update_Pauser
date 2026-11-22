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
                # 修改这里：处理十六进制值
                value_str = result.stdout.split()[-1].strip()
                try:
                    if value_str.startswith('0x'):
                        max_pause_days = int(value_str, 16)  # 如果是十六进制，按16进制解析
                    else:
                        max_pause_days = int(value_str)  # 否则按十进制解析
                    self.paused_until_label.setText(f"最大可暂停天数: {max_pause_days} 天")
                except ValueError:
                    self.paused_until_label.setText(f"最大可暂停天数: 无效值 '{value_str}'")
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
            print(f"[DEBUG] 状态检测错误: {str(e)}")
            self.current_status_label.setText(f"状态检测错误: {str(e)}")
    
    def pause_updates(self):
        duration = self.duration_spinbox.value()
        unit = self.unit_combobox.currentText()
        
        # 转换为天数
        unit_days = {
            "天": 1,
            "周": 7,
            "月": 30,
            "年": 365,
            "百年": 365*100,
            "千年": 365*1000,
            "万年": 365*10000,
            "永久": 365*10000
        }
        days = duration * unit_days.get(unit, 1)
        
        # Windows 10 最大暂停天数限制为35天
        win10_max_pause = 35
        effective_days = min(days, win10_max_pause) if unit != "永久" else win10_max_pause

        try:
            # 设置最大暂停天数 (Win10/Win11通用)
            subprocess.run(
                ["reg", "add", r"HKLM\SOFTWARE\Microsoft\WindowsUpdate\UX\Settings", 
                "/v", "FlightSettingsMaxPauseDays", "/t", "REG_DWORD", "/d", str(effective_days), "/f"],
                check=True, creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            # 计算暂停结束时间
            end_time = datetime.now() + timedelta(days=effective_days)
            end_time_str = end_time.strftime("%Y-%m-%d %H:%M:%S")
            
            # Windows 10 专用设置 (让设置界面显示暂停状态)
            subprocess.run(
                ["reg", "add", r"HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\WindowsUpdate\Services\Default",
                "/v", "Paused", "/t", "REG_DWORD", "/d", "1", "/f"],
                check=True, creationflags=subprocess.CREATE_NO_WINDOW
            )
            subprocess.run(
                ["reg", "add", r"HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\WindowsUpdate\Services\Default",
                "/v", "PausedUntil", "/t", "REG_SZ", "/d", end_time_str, "/f"],
                check=True, creationflags=subprocess.CREATE_NO_WINDOW
            )

            # 新增以下注册表项来确保Windows 10设置界面显示暂停状态
            subprocess.run(
                ["reg", "add", r"HKLM\SOFTWARE\Microsoft\WindowsUpdate\UX\Settings",
                "/v", "PauseFeatureUpdatesEndTime", "/t", "REG_SZ", "/d", end_time_str, "/f"],
                check=True, creationflags=subprocess.CREATE_NO_WINDOW
            )
            subprocess.run(
                ["reg", "add", r"HKLM\SOFTWARE\Microsoft\WindowsUpdate\UX\Settings",
                "/v", "PauseQualityUpdatesEndTime", "/t", "REG_SZ", "/d", end_time_str, "/f"],
                check=True, creationflags=subprocess.CREATE_NO_WINDOW
            )
            subprocess.run(
                ["reg", "add", r"HKLM\SOFTWARE\Microsoft\WindowsUpdate\UX\Settings",
                "/v", "PauseUpdatesStartTime", "/t", "REG_SZ", "/d", datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "/f"],
                check=True, creationflags=subprocess.CREATE_NO_WINDOW
            )

            # Windows 11 专用设置
            subprocess.run(
                ["reg", "add", r"HKLM\SOFTWARE\Microsoft\WindowsUpdate\UX\Settings",
                "/v", "PausedFeatureUpdateEndTime", "/t", "REG_SZ", "/d", end_time_str, "/f"],
                check=True, creationflags=subprocess.CREATE_NO_WINDOW
            )
            subprocess.run(
                ["reg", "add", r"HKLM\SOFTWARE\Microsoft\WindowsUpdate\UX\Settings",
                "/v", "PauseUpdatesExpiryTime", "/t", "REG_SZ", "/d", end_time_str, "/f"],
                check=True, creationflags=subprocess.CREATE_NO_WINDOW
            )

            # 停止更新服务
            stop_service_failed = False
            try:
                result = subprocess.run(
                    ["sc", "query", "wuauserv"],
                    capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW
                )
                if "RUNNING" in result.stdout:
                    subprocess.run(
                        ["net", "stop", "wuauserv"],
                        check=True, creationflags=subprocess.CREATE_NO_WINDOW
                    )
            except subprocess.CalledProcessError:
                stop_service_failed = True

            # 构建结果消息
            success_msg = [
                f"✅ 已成功暂停 Windows 更新 {duration} {unit}",
                "",
                "操作详情:",
                f"• 实际生效天数: {effective_days} 天 (Windows 10 最大限制35天)" if effective_days != days else "",
                "• 已设置 Windows 10 和 Windows 11 兼容的暂停状态",
                f"• 暂停结束时间: {end_time_str}",
                "",
                "⚠ 注意: Windows 10 最多只能暂停35天更新",
                "多次暂停会从当前时间重新计算35天"
            ]
            
            # 添加刷新操作
            refresh_msg = self.refresh_system()
            if refresh_msg:
                success_msg.extend(["", "系统刷新操作:", refresh_msg])

            QMessageBox.information(self, "成功", "\n".join([line for line in success_msg if line]))
            self.check_update_status()
            
        except Exception as e:
            QMessageBox.critical(
                self, "错误",
                "暂停更新失败:\n\n"
                f"{str(e)}\n\n"
                "请尝试:\n"
                "1. 以管理员身份运行\n"
                "2. 检查防病毒软件设置\n"
                "3. 确认系统版本支持"
            )



    
    def resume_updates(self):
        try:
            # 清除新增的Windows 10暂停设置
            subprocess.run(
                ["reg", "delete", r"HKLM\SOFTWARE\Microsoft\WindowsUpdate\UX\Settings",
                "/v", "PauseFeatureUpdatesEndTime", "/f"],
                check=True, creationflags=subprocess.CREATE_NO_WINDOW
            )
            subprocess.run(
                ["reg", "delete", r"HKLM\SOFTWARE\Microsoft\WindowsUpdate\UX\Settings",
                "/v", "PauseQualityUpdatesEndTime", "/f"],
                check=True, creationflags=subprocess.CREATE_NO_WINDOW
            )
            subprocess.run(
                ["reg", "delete", r"HKLM\SOFTWARE\Microsoft\WindowsUpdate\UX\Settings",
                "/v", "PauseUpdatesStartTime", "/f"],
                check=True, creationflags=subprocess.CREATE_NO_WINDOW
            )

            
            # 清除 Windows 11 暂停设置
            subprocess.run(
                ["reg", "delete", r"HKLM\SOFTWARE\Microsoft\WindowsUpdate\UX\Settings",
                "/v", "PausedFeatureUpdateEndTime", "/f"],
                check=True, creationflags=subprocess.CREATE_NO_WINDOW
            )
            subprocess.run(
                ["reg", "delete", r"HKLM\SOFTWARE\Microsoft\WindowsUpdate\UX\Settings",
                "/v", "PauseUpdatesExpiryTime", "/f"],
                check=True, creationflags=subprocess.CREATE_NO_WINDOW
            )

            # 启动更新服务
            try:
                subprocess.run(
                    ["net", "start", "wuauserv"],
                    check=True, creationflags=subprocess.CREATE_NO_WINDOW
                )
            except subprocess.CalledProcessError:
                pass
                
            success_msg = [
                "✅ 已恢复 Windows 更新",
                "",
                "操作详情:",
                "• 已清除所有暂停设置",
                "• 服务状态: 已启动"
            ]
            # 添加刷新操作
            refresh_msg = self.refresh_system()
            if refresh_msg:
                success_msg.extend(["", "系统刷新操作:", refresh_msg])
            QMessageBox.information(self, "成功", "\n".join(success_msg))
            self.check_update_status()
            
        except Exception as e:
            QMessageBox.critical(
                self, "错误",
                "恢复更新失败:\n\n"
                f"{str(e)}\n\n"
                "请尝试以管理员身份运行此程序"
            )

    def refresh_system(self):
        """执行系统刷新操作"""
        refresh_actions = []
        
        try:
            # 1. 重启Windows Update服务
            subprocess.run(
                ["net", "stop", "wuauserv"],
                check=True, creationflags=subprocess.CREATE_NO_WINDOW
            )
            subprocess.run(
                ["net", "start", "wuauserv"],
                check=True, creationflags=subprocess.CREATE_NO_WINDOW
            )
            refresh_actions.append("• Windows Update服务已重启")
        except Exception as e:
            refresh_actions.append(f"• Windows Update服务重启失败: {str(e)}")
        
        try:
            # 2. 重启资源管理器
            subprocess.run(
                ["taskkill", "/f", "/im", "explorer.exe"],
                check=True, creationflags=subprocess.CREATE_NO_WINDOW
            )
            subprocess.run(
                ["start", "explorer.exe"],
                shell=True, check=True, creationflags=subprocess.CREATE_NO_WINDOW
            )
            refresh_actions.append("• 资源管理器已重启")
        except Exception as e:
            refresh_actions.append(f"• 资源管理器重启失败: {str(e)}")
        
        try:
            # 3. 强制刷新组策略
            subprocess.run(
                ["gpupdate", "/force"],
                check=True, creationflags=subprocess.CREATE_NO_WINDOW
            )
            refresh_actions.append("• 组策略已强制刷新")
        except Exception as e:
            refresh_actions.append(f"• 组策略刷新失败: {str(e)}")
        
        return "\n".join(refresh_actions)



if __name__ == "__main__":
    # 适配高DPI屏幕
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
    
    app = QApplication(sys.argv)
    window = UpdatePauser()
    window.show()
    sys.exit(app.exec_())