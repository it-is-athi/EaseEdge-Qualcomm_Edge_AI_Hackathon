# EaseEdge - Gesture Detection System

A real-time gesture-based emergency support system designed for individuals with limited mobility. EaseEdge uses computer vision and telephony integration to detect facial gestures (like blinks) and trigger emergency calls automatically. Built for the Qualcomm Edge AI Hackathon by Sudharshan J, Deebika N, and Divya Nandini R.

## Key Features
- **Real-time Gesture Detection:** Uses your webcam and advanced facial landmark detection to recognize blinks and nods, enabling hands-free emergency signaling.
- **Emergency Call Trigger:** Automatically places a call to a pre-set emergency contact if 4 consecutive blinks are detected, ensuring rapid response in critical situations.
- **Twilio Integration:** Seamlessly connects with Twilio to automate phone calls without manual intervention.
- **Simple Setup:** Easy installation and configuration with a virtual environment and a single `.env` file for credentials.

## Tech Stack
- **Python 3.11**
- **OpenCV** (for video capture and image processing)
- **MediaPipe** (for facial landmark detection)
- **Twilio** (for automated phone calls)
- **python-dotenv** (for environment variable management)
- **NumPy, SciPy** (for numerical and distance calculations)

## Quick Start
1. **Clone the repository**
   ```sh
   git clone <repo-url>
   cd <repo-folder>
   ```
2. **Create and activate the virtual environment**
   ```sh
   python -m venv venv
   .\venv\Scripts\activate   # PowerShell
   ```
   For more details, see `activate_venv_instructions.txt`.
3. **Install dependencies**
   ```sh
   pip install -r requirements.txt
   ```
4. **Environment variables are already set up in the .env file.**
5. **Run the application UI**
   ```sh
   python ui.py
   ```

## Notes
- Ensure your `.env` is set up before running.
- The system uses your webcam for detection. 
