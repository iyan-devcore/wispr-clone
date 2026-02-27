import ctypes
import sys
import sounddevice as sd
import numpy as np
import librosa
from pynput import keyboard, mouse
import pyautogui
from faster_whisper import WhisperModel
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer, QThread, Signal
from bubble import RecordingBubble


# ==============================
# GLOBAL STATE
# ==============================
worker = None
ctrl_pressed = False
mouse4_pressed = False
recording = False
audio_buffer = []


# ==============================
# SILENCE DETECTION
# ==============================
def is_silence(audio, threshold=0.015):
    rms = np.sqrt(np.mean(audio ** 2))
    return rms < threshold


# ==============================
# TRANSCRIBE WORKER
# ==============================
class TranscribeWorker(QThread):
    finished = Signal(str)

    def __init__(self, audio, samplerate):
        super().__init__()
        self.audio = audio
        self.samplerate = samplerate

    def run(self):
        audio_resampled = librosa.resample(
            self.audio,
            orig_sr=self.samplerate,
            target_sr=16000
        )

        segments, _ = model.transcribe(
            audio_resampled,
            language="en",
            task="transcribe"
        )

        final_text = " ".join([s.text for s in segments]).strip()
        self.finished.emit(final_text)


# ==============================
# FIX DPI WARNING
# ==============================
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except:
    pass


# ==============================
# LOAD WHISPER
# ==============================
print("Loading Whisper model...")
model = WhisperModel("large-v3", device="cuda", compute_type="float16")
print("Model loaded.")


# ==============================
# AUDIO DEVICE
# ==============================
DEVICE_INDEX = 21
device_info = sd.query_devices(DEVICE_INDEX, 'input')
samplerate = int(device_info['default_samplerate'])


# ==============================
# QT APP
# ==============================
app = QApplication(sys.argv)
bubble = RecordingBubble()

print("Hold CTRL + Mouse4 to speak. ESC to quit.")


# ==============================
# AUDIO CALLBACK
# ==============================
def audio_callback(indata, frames, time, status):
    global recording, audio_buffer
    if recording:
        audio_buffer.append(indata.copy())
        bubble.update_level(indata.flatten())


stream = sd.InputStream(
    device=DEVICE_INDEX,
    samplerate=samplerate,
    channels=1,
    dtype="float32",
    callback=audio_callback,
)
stream.start()


# ==============================
# GLOBAL HOTKEY LISTENERS
# ==============================
def on_key_press(key):
    global ctrl_pressed
    if key in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
        ctrl_pressed = True

    if key == keyboard.Key.esc:
        print("Exiting...")
        stream.stop()
        stream.close()
        app.quit()


def on_key_release(key):
    global ctrl_pressed
    if key in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
        ctrl_pressed = False


def on_click(x, y, button, pressed):
    global mouse4_pressed
    if button == mouse.Button.x1:  # Mouse 4
        mouse4_pressed = pressed


keyboard_listener = keyboard.Listener(
    on_press=on_key_press,
    on_release=on_key_release
)
keyboard_listener.start()

mouse_listener = mouse.Listener(
    on_click=on_click
)
mouse_listener.start()


# ==============================
# MAIN LOOP
# ==============================
def update_loop():
    global recording, audio_buffer, worker

    # START RECORDING
    if ctrl_pressed and mouse4_pressed and not recording:
        recording = True
        audio_buffer = []
        print("\nRecording...")
        bubble.set_recording()
        return

    # STOP RECORDING
    if (not ctrl_pressed or not mouse4_pressed) and recording:
        recording = False
        print("Transcribing...")
        bubble.set_processing()

        if not audio_buffer:
            bubble.set_idle()
            return

        audio = np.concatenate(audio_buffer, axis=0).flatten()

        if len(audio) == 0:
            bubble.set_idle()
            return

        if is_silence(audio):
            print("Silence detected. Ignoring.")
            bubble.set_idle()
            return

        if worker is not None:
            return

        worker = TranscribeWorker(audio, samplerate)

        def on_finished(text):
            global worker
            print("\n--- FINAL TEXT ---")
            print(text)

            if text:
                pyautogui.write(text + " ")

            bubble.set_idle()

            worker.quit()
            worker.wait()
            worker = None

        worker.finished.connect(on_finished)
        worker.start()
        return


# ==============================
# TIMER
# ==============================
timer = QTimer()
timer.timeout.connect(update_loop)
timer.start(30)


sys.exit(app.exec())