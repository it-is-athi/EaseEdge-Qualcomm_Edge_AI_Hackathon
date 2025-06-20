import cv2
import mediapipe as mp
import pyttsx3
import simpleaudio as sa
from datetime import datetime
import time
from twilio.rest import Client
import onnxruntime as ort
import numpy as np

# === TTS Setup ===
tts = pyttsx3.init()
tts.setProperty('rate', 150)

# === Face Mesh Setup ===
# type: ignore[attr-defined]
mp_face = mp.solutions.face_mesh
face_mesh = mp_face.FaceMesh(max_num_faces=1, min_detection_confidence=0.5)

# === Twilio Config ===
TWILIO_SID = "AC5f3826ccf1abf39e25ce7cf9f15ae87e"
TWILIO_AUTH = "2092c07220e7fa7b124bc93922c60972"
TWILIO_FROM = "+15705535015"  # your Twilio number
CARETAKER_PHONE = "+918883389966" 
# === Thresholds ===
BLINK_THRESHOLD = 0.02
NOD_MOVEMENT_THRESHOLD = 0.04
TWITCH_THRESHOLD = 0.015
EYE_CLOSED_SOS_TIME = 5
alert_cooldown = 15  # seconds

blink_counter = 0
closed_start = None
nod_history = []
last_alert_time = 0

GENDERS = ["Male", "Female"]
EMOTIONS = ["Neutral", "Happy", "Sad", "Surprise", "Anger"]

# === Load ONNX Model ===
session = ort.InferenceSession("face_attrib_net-facial-attribute-detection-float.onnx")


def speak(text):
    tts.say(text)
    tts.runAndWait()

def play_alarm():
    try:
        sa.WaveObject.from_wave_file("alarm.wav").play()
    except Exception as e:
        print("❌ Alarm failed:", e)

def log_event(event):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open("care_log.txt", "a") as f:
        f.write(f"[{timestamp}] {event}\n")

def send_sms_alert(message):
    try:
        client = Client(TWILIO_SID, TWILIO_AUTH)
        client.messages.create(body=message, from_=TWILIO_FROM, to=CARETAKER_PHONE)
        print("📱 SMS sent to caretaker.")
    except Exception as e:
        print("❌ SMS sending failed:", e)

def alert(event):
    global last_alert_time
    now = time.time()
    if now - last_alert_time > alert_cooldown:
        print("🚨 ALERT:", event)
        speak(event)
        play_alarm()
        send_sms_alert(f"RA Patient Alert: {event}")
        log_event("ALERT: " + event)
        last_alert_time = now

def detect_attributes(face_crop):
    try:
        resized = cv2.resize(face_crop, (128, 128))
        # Convert to BGR just in case (OpenCV usually gives BGR already)
        bgr = cv2.cvtColor(resized, cv2.COLOR_RGB2BGR) if resized.shape[2] == 3 else resized
        # Normalize and transpose
        input_blob = bgr.astype('float32') / 255.0
        input_blob = np.transpose(input_blob, (2, 0, 1))  # From HWC to CHW
        input_blob = np.expand_dims(input_blob, axis=0)   # Add batch dimension

        # Run model
        outputs = session.run(None, {"image": input_blob})

        # Ensure outputs[0] and outputs[1] are numpy arrays before using argmax
        gender_logits = np.array(outputs[0])
        emotion_logits = np.array(outputs[1])

        gender_idx = int(np.argmax(gender_logits))
        emotion_idx = int(np.argmax(emotion_logits))

        gender = GENDERS[gender_idx] if gender_idx < len(GENDERS) else "Unknown"
        emotion = EMOTIONS[emotion_idx] if emotion_idx < len(EMOTIONS) else "Unknown"
        return gender, emotion

    except Exception as e:
        print("⚠️ Attribute detection error:", e)
        return "Unknown", "Unknown"


# === Start Webcam ===
cap = cv2.VideoCapture(0)
print("\U0001f9e0 RA Edge AI Assistant running... (press Q to quit)")

while cap.isOpened():
    success, frame = cap.read()
    if not success:
        break

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    result = face_mesh.process(rgb)

    if result.multi_face_landmarks:
        for face in result.multi_face_landmarks:
            landmarks = face.landmark

            h, w, _ = frame.shape
            x_min = int(min(l.x for l in landmarks) * w)
            y_min = int(min(l.y for l in landmarks) * h)
            x_max = int(max(l.x for l in landmarks) * w)
            y_max = int(max(l.y for l in landmarks) * h)

            pad = 20
            x_min = max(0, x_min - pad)
            y_min = max(0, y_min - pad)
            x_max = min(w, x_max + pad)
            y_max = min(h, y_max + pad)

            face_crop = frame[y_min:y_max, x_min:x_max]
            gender, emotion = detect_attributes(face_crop)

            # Blink Detection
            left_eye = [landmarks[i] for i in [159, 145]]
            eye_dist = abs(left_eye[0].y - left_eye[1].y)

            if eye_dist < BLINK_THRESHOLD:
                if not closed_start:
                    closed_start = time.time()
                elif time.time() - closed_start >= EYE_CLOSED_SOS_TIME:
                    alert("Eyes closed too long. Possible fatigue or emergency.")
                    closed_start = None
            else:
                closed_start = None

            # Nod Detection
            nose_y = landmarks[1].y
            nod_history.append(nose_y)
            if len(nod_history) == 10:
                avg_nod = sum(nod_history) / 10
                if abs(avg_nod - nose_y) > NOD_MOVEMENT_THRESHOLD:
                    alert("Unusual nodding pattern detected.")
                nod_history.pop(0)

            # Twitch Detection
            brow_diff = abs(landmarks[65].y - landmarks[55].y)
            mouth_diff = abs(landmarks[13].y - landmarks[14].y)
            if brow_diff > TWITCH_THRESHOLD or mouth_diff > (TWITCH_THRESHOLD + 0.01):
                alert("Possible facial twitch detected.")

            # Emotion Discomfort
            if emotion in ["Sad", "Anger"]:
                alert("Emotion suggests discomfort.")

            cv2.putText(frame, f"Gender: {gender}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,0), 2)
            cv2.putText(frame, f"Emotion: {emotion}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,0), 2)

    cv2.imshow("RA Gesture + Emotion Monitor", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
