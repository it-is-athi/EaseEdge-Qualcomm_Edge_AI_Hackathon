# EaseEdge: Smart Monitoring & Emergency Support System

EaseEdge is a comprehensive real-time monitoring and emergency support application especially designed for individuals with Rheumatoid Arthritis (RA) and bedridden patients. The system provides a seamless, user-friendly dashboard that integrates gesture detection, speech recognition, reminders, and emergency support—all in one place. Its intuitive interface ensures accessibility and ease of use for both patients and caregivers, helping those with limited mobility communicate and receive timely assistance.

## Key Features
- **Gesture Detection:**
  - Uses your webcam and advanced computer vision (OpenCV + MediaPipe) to detect subtle facial gestures such as blinks, nods, and twitches.
  - Enables hands-free interaction and can help monitor user alertness or request assistance—ideal for users with severe mobility limitations.
- **Speech Recognition:**
  - Employs the Vosk offline speech-to-text engine to recognize spoken commands and emergency keywords without needing an internet connection.
  - Allows users to trigger emergency support or interact with reminders using their voice.
- **Reminders:**
  - Lets users or caregivers schedule important reminders (e.g., medication times, hydration, appointments).
  - Reminders are delivered both visually and through text-to-speech (pyttsx3), ensuring they are not missed.
- **Emergency Support:**
  - Provides a one-tap or voice-activated emergency call feature for immediate assistance.
  - Designed for quick access in urgent situations, especially for those who cannot move easily.
- **Modern UI:**
  - Features a clean, material-inspired dashboard with sidebar navigation for easy access to all functions.
  - Optimized for clarity, accessibility, and ease of use.

## How It Works
- The app uses your webcam to continuously monitor for facial gestures and listens for specific voice commands.
- When a gesture or emergency keyword is detected, the system can trigger alerts, reminders, or emergency support actions.
- All features are accessible from a single, integrated dashboard, making it especially useful for RA and bedridden patients who need reliable, accessible support.

## Libraries & Models Used
- **OpenCV:** For real-time video capture and image processing.
- **MediaPipe:** For accurate facial landmark detection and gesture analysis.
- **Vosk:** For offline speech recognition (requires the Vosk English model).
- **pyttsx3:** For text-to-speech reminders and alerts.
- **Tkinter & customtkinter:** For building the modern, interactive user interface.

### Model Files Required
- The Vosk model folder (e.g., `vosk-model-small-en-us-0.15`) must be present in the project directory for speech recognition to work offline.

## Getting Started
1. **Activate the virtual environment.**
   - See `activate_venv_instructions.txt` for step-by-step commands.
2. **Install dependencies (first time only):**
   ```sh
   pip install -r requirements.txt
   ```
3. **Start the app:**
   ```sh
   python ui.py
   ```

## Tips for Best Results
- Always activate your virtual environment before running scripts.
- Use your webcam in a well-lit environment for optimal gesture detection.
- Keep your face within the camera frame for accurate monitoring.
- Ensure the Vosk model folder is present for speech recognition features.

## License
Open source and available for anyone to use and modify. 