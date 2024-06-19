import os
import sys
import csv
import requests
import subprocess
from PyQt5.QtCore import QThread, pyqtSignal, Qt, QTimer, QMutex, QMutexLocker
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QTextEdit, QPushButton, QCheckBox, QHBoxLayout, QMessageBox

class DownloadThread(QThread):
    finished = pyqtSignal(str)

    def __init__(self, app_name, app_url, extension):
        super().__init__()
        self.app_name = app_name
        self.app_url = app_url
        self.extension = extension

    def run(self):
        try:
            response = requests.get(self.app_url)
            response.raise_for_status()
            file_path = os.path.join("Repository", f"{self.app_name}{self.extension}")
            with open(file_path, "wb") as f:
                f.write(response.content)
            result_message = f"Download do instalador {self.app_name} concluído."
        except requests.exceptions.RequestException as e:
            result_message = f"Falha ao baixar {self.app_name}: {str(e)}"
        except Exception as e:
            result_message = f"Erro ao baixar {self.app_name}: {str(e)}"
        self.finished.emit(result_message)

class InstallationApp(QWidget):
    def __init__(self):
        super().__init__()
        self.checkboxes = []
        self.threads = []
        self.mutex = QMutex()
        self.initUI()
        self.create_repository_folder()  # Adicionando criação de pasta no inicializador
        self.load_apps_from_csv()

    def initUI(self):
        self.setWindowTitle('QuickBuild')
        self.setGeometry(100, 100, 800, 400)

        self.status_label = QLabel('Logs:', self)
        self.installation_log = QTextEdit(self)
        self.installation_log.setReadOnly(True)

        self.install_button = QPushButton('Baixar Selecionados', self)
        self.install_button.clicked.connect(self.download_selected_installers)

        self.open_folder_button = QPushButton('Onde estão meus instaladores?', self)
        self.open_folder_button.clicked.connect(self.open_repository_folder)

        select_all_layout = QHBoxLayout()
        self.select_all_checkbox = QCheckBox('Selecionar Tudo', self)
        self.select_all_checkbox.stateChanged.connect(self.select_all_checkboxes)
        select_all_layout.addWidget(self.select_all_checkbox)
        select_all_layout.addStretch(1)

        self.checkbox_layout = QHBoxLayout()

        vbox = QVBoxLayout(self)
        vbox.addWidget(self.status_label)
        vbox.addWidget(self.installation_log)
        vbox.addWidget(self.install_button)
        vbox.addWidget(self.open_folder_button)
        vbox.addLayout(select_all_layout)
        vbox.addLayout(self.checkbox_layout)

        self.setLayout(vbox)

    def load_apps_from_csv(self):
        try:
            with open("apps.csv", mode='r', newline='') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    checkbox = QCheckBox(row['name'], self)
                    checkbox.setChecked(False)
                    self.checkboxes.append({
                        "checkbox": checkbox,
                        "name": row['name'],
                        "url": row['url'],
                        "extension": row.get('extension', '')
                    })
                    self.checkbox_layout.addWidget(checkbox)
        except FileNotFoundError:
            self.log_message("Arquivo apps.csv não encontrado.")

    def create_repository_folder(self):
        folder_path = os.path.join(os.getcwd(), "Repository")
        try:
            os.makedirs(folder_path, exist_ok=True)
        except Exception as e:
            self.log_message(f"Erro ao criar a pasta Repository: {str(e)}")

    def download_selected_installers(self):
        if all(not checkbox["checkbox"].isChecked() for checkbox in self.checkboxes):
            self.log_message("Erro: Nenhum aplicativo selecionado para baixar.")
            return

        self.install_button.setEnabled(False)

        for checkbox_data in self.checkboxes:
            checkbox = checkbox_data["checkbox"]
            if checkbox.isChecked():
                app_name = checkbox_data["name"]
                app_url = checkbox_data["url"]
                extension = checkbox_data["extension"] or (".exe" if app_url.lower().endswith(".exe") else ".msi")
                
                thread = DownloadThread(app_name, app_url, extension)
                thread.finished.connect(self.thread_finished)
                with QMutexLocker(self.mutex):
                    self.threads.append(thread)
                thread.start()

        self.start_thread_check_timer()

    def thread_finished(self, result_message):
        self.log_message(result_message)
        with QMutexLocker(self.mutex):
            self.threads = [thread for thread in self.threads if thread.isRunning()]

    def start_thread_check_timer(self):
        self.thread_check_timer = QTimer(self)
        self.thread_check_timer.timeout.connect(self.check_active_threads)
        self.thread_check_timer.start(1000)

    def stop_thread_check_timer(self):
        if hasattr(self, 'thread_check_timer'):
            self.thread_check_timer.stop()

    def check_active_threads(self):
        with QMutexLocker(self.mutex):
            if not any(thread.isRunning() for thread in self.threads):
                self.stop_thread_check_timer()
                self.install_button.setEnabled(True)
                self.show_success_message()

    def show_success_message(self):
        QMessageBox.information(self, 'Downloads Concluídos', 'Todos os downloads foram concluídos com sucesso.')

    def log_message(self, message):
        self.installation_log.append(message)

    def open_repository_folder(self):
        folder_path = os.path.join(os.getcwd(), "Repository")
        if not os.path.exists(folder_path):
         self.create_repository_folder()

        try:
            subprocess.Popen(['explorer', folder_path])
        except Exception as e:
            self.log_message(f"Erro ao abrir a pasta Repository: {str(e)}")

    def select_all_checkboxes(self, state):
        for checkbox_data in self.checkboxes:
            checkbox = checkbox_data["checkbox"]
            checkbox.setChecked(state == Qt.Checked)

    def closeEvent(self, event):
        self.stop_thread_check_timer()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    installation_app = InstallationApp()
    installation_app.show()
    sys.exit(app.exec_())