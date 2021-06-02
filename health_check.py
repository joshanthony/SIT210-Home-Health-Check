from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from picamera import PiCamera
import RPi.GPIO as GPIO
import sys
import time
import serial
import requests

LED_PIN = 36
GPIO.setmode(GPIO.BOARD)
GPIO.setup(LED_PIN, GPIO.OUT)

camera = PiCamera()
camera.rotation = 270
IMG_DIR = "/home/pi/Capture/"
serial_in = serial.Serial('/dev/ttyACM0', 9600)

HTTP_URL = "https://healthcheck.joshanthony.io/sync"
USER_EMAIL = "josh@example.com"

class Signal(QObject):
    # Signals for emitting events during the lifecycle of a thread
    finished = pyqtSignal()
    progress = pyqtSignal(int)

class Thread(QRunnable):
    # Run a function as a separate thread using PyQT
    def __init__(self, func, *args, **kwargs):
        super(Thread, self).__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.signal = Signal()
        self.kwargs['thread_callback'] = self.signal.progress

    @pyqtSlot()
    def run(self):
        # Try block allows us to send a signal when the thread is finished
        try:
            self.func(*self.args, **self.kwargs)
        except:
            print("Error running function")
        finally:
            self.signal.finished.emit()

class HealthCheck(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.photo = None
        self.heart_rate = None
        self.thread_pool = QThreadPool()

    def getHeartRate(self, thread_callback):
        # Collect 5 heart rate samples
        samples = []
        checking = True
        try:
            while checking:
                data = serial_in.readline()
                heart_rate = data.decode('utf-8').strip()
                if heart_rate:
                    samples.append(int(heart_rate))
                if len(samples) >= 5:
                    checking = False
        except:
            return 0 # return on error
        # return the average heart rate to improve accuracy
        avg_hr = sum(samples) / len(samples)
        self.heart_rate = avg_hr
        return avg_hr

    def flashLED(self, seconds):
        GPIO.output(LED_PIN, GPIO.HIGH)        
        time.sleep(seconds)
        GPIO.output(LED_PIN, GPIO.LOW)

    def takePhoto(self, thread_callback):
        # Update the confirmation and progress text
        thread_callback.emit(0)
        self.confirmation.setText("Taking photo...")
        # Flash the LED
        self.flashLED(2)
        thread_callback.emit(50)
        # Take a photo and save the photo location
        img_path = self.capturePhoto()
        thread_callback.emit(100)
        self.photo = img_path        
        return img_path

    def capturePhoto(self):
        # Capture and save a photo using PiCamera
        img_name = 'img_%s.jpg' % time.time()
        img_path = IMG_DIR + img_name
        camera.start_preview()
        time.sleep(0.1)
        camera.capture(img_path)
        time.sleep(3)
        camera.stop_preview()
        return img_path

    def updateProgress(self, value):
        self.progress.setText(f"{value}% complete")

    def requestSync(self):
        # Check if we have the data we need to sync before syncing the data
        if self.heart_rate is not None and self.photo is not None:
            self.confirmation.setText("Saving data...")
            self.syncData()
        elif self.photo is not None:
            self.confirmation.setText("Waiting for HR data...")

    def syncData(self):
        # Send the data to our web app via HTTP POST request
        headers = {"api_key":"cbb55f1ebc328401c04941968b597b0b"}
        file = {'file': open(self.photo, 'rb')}
        body = {'hr': self.heart_rate, 'user': USER_EMAIL}
        r = requests.post(HTTP_URL, files=file, data=body, headers=headers)
        self.confirmation.setText("Health Check Complete")

    def initUI(self):
        # Create GUI elements and styles
        self.btn = QPushButton('Start Health Check', self)
        self.btn.setFont(QFont('Arial font', 30))
        self.confirmation = QLabel("")
        self.confirmation.setFont(QFont('Arial font', 26))
        self.progress = QLabel("")
        self.progress.setFont(QFont('Arial font', 26))

        # Connect button to function onClick
        self.btn.clicked.connect(self.onClick)        

        # Position the GUI layout
        grid = QGridLayout(self)
        self.setWindowTitle('Health Check')
        grid.addWidget(self.btn, 1, 0)
        grid.addWidget(self.confirmation, 2, 0)
        grid.addWidget(self.progress, 3, 0)
        self.show()

    @pyqtSlot()
    def onClick(self):
        # Reset values to collect new data
        self.photo = None
        self.heart_rate = None

        # 1. Take a photo (multithreaded), update GUI progress and sync data
        photo_thread = Thread(self.takePhoto)
        photo_thread.signal.progress.connect(self.updateProgress)
        photo_thread.signal.finished.connect(self.requestSync)
        self.thread_pool.start(photo_thread)

        # 2. Get heart rate (multithreaded) and sync data
        hr_thread = Thread(self.getHeartRate) 
        hr_thread.signal.finished.connect(self.requestSync)
        self.thread_pool.start(hr_thread)

if __name__ == '__main__':
    if not QApplication.instance():
        app = QApplication(sys.argv)
    else:
        app = QApplication.instance()
    ex = HealthCheck()
    sys.exit(app.exec_())