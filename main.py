import threading
from gesture_detector import GestureDetector
from recognizer import SpeechRecognitionEngine
import time

# Placeholder for the Vosk model path
VOSK_MODEL_PATH = 'model'  # Change this to your actual Vosk model directory

# --- Gesture Detection Thread ---
def run_gesture_detection():
    detector = GestureDetector()
    import cv2
    cap = cv2.VideoCapture(0)
    print("Gesture detection started.")
    print("Controls:")
    print("- Press 'p' to pause/resume detection")
    print("- Press 'q' to quit")
    print("\nEmergency System:")
    print(f"- {detector.emergency_blink_count} consecutive blinks will trigger emergency call")
    print(f"- Emergency contact: {detector.emergency_number}")
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        processed_frame = detector.process_frame(frame)
        cv2.imshow('Gesture Detection', processed_frame)
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('p'):
            detector.is_paused = not detector.is_paused
            print("Paused" if detector.is_paused else "Resumed")
    cap.release()
    cv2.destroyAllWindows()

# --- Speech Recognition Thread ---
def speech_callback(text):
    print(f"[Speech Recognition] Detected: {text}")

def run_speech_recognition():
    engine = SpeechRecognitionEngine(VOSK_MODEL_PATH)
    engine.start(speech_callback)
    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        engine.stop()

if __name__ == "__main__":
    gesture_thread = threading.Thread(target=run_gesture_detection, daemon=True)
    speech_thread = threading.Thread(target=run_speech_recognition, daemon=True)

    gesture_thread.start()
    speech_thread.start()

    gesture_thread.join()
    # When gesture detection window is closed, stop speech recognition
    print("Stopping speech recognition...")
    # No direct stop signal, but the thread will exit on KeyboardInterrupt or process exit. 