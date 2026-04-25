# Drowsiness-Detector-On-Rasperry-Pi-5
Real-time driver drowsiness and yawn detection system optimized for Raspberry Pi 5. Built with Python, OpenCV &amp; dlib. It tracks facial landmarks to trigger a multithreaded GPIO or system audio alarm upon detecting fatigue, enhancing road safety.
Driver Drowsiness & Yawn Detection (Raspberry Pi 5)

Project Overview:
This is a driver drowsiness monitoring and warning system optimized specifically for embedded devices, particularly the Raspberry Pi (especially RPi 5). The project utilizes a Webcam combined with Computer Vision algorithms to track the driver's facial state in real-time. The system will immediately trigger an audible alarm if it detects the driver closing their eyes for too long or yawning continuously, helping to prevent traffic accidents caused by fatigue.

Key Features
Drowsiness Detection: Uses the Eye Aspect Ratio (EAR) metric. If the EAR falls below 0.25 for 15 consecutive frames, the system triggers an alarm.
Yawn Detection: Calculates the Mouth/Lip Distance (MAR - Mouth Aspect Ratio). The alarm activates if the driver opens their mouth wide (MAR > 25) continuously for more than 4.0 seconds.
Real-world Environment Optimization: Integrates a CLAHE filter to enhance image processing in low-light conditions (e.g., inside a car cabin at night).
Flexible Hardware Integration: * Supports a physical Buzzer via GPIO 17 pin on the Raspberry Pi (using the gpiozero library).
Automatic fallback to system audio if the GPIO circuit is not detected.
Multithreading: The alarm audio thread is isolated to ensure the image processing pipeline does not lag or drop frames when the buzzer sounds.

Hardware & Software Requirements:

Hardware
Raspberry Pi (Raspberry Pi 5 is highly recommended for optimal FPS).
Webcam (USB Web Camera or Pi Camera Module).
Active Buzzer - Optional, connected to GPIO 17.

Software & Dependencies
This project is written in Python 3. You need to install the following libraries:
1. opencv-python (cv2)
2. dlib (Requires the pre-trained shape_predictor_68_face_landmarks.dat model)
3. imutils
4. scipy
5. gpiozero (For controlling GPIO pins on the RPi)
6. sox (For Linux system audio if a physical buzzer is unavailable. Install via: sudo apt install sox)

Installation & Usage:
1. Prepare the AI Model
Download the shape_predictor_68_face_landmarks.dat file (dlib's pre-trained model) and place it in the same directory as the drowsiness_yawn.py script.

2. Run the Program
Open the Terminal in the project directory and execute the following command:

Bash
python drowsiness_yawn.py --webcam 0
(You can change the 0 to the corresponding camera index if you are using multiple cameras).

3. Visual Interface & Monitoring
In the Console, the system will print real-time metrics (FPS, Status, EAR, MAR, and Timer). The Camera window will display the facial landmark tracking and flash a red "WAKE UP!" warning when an incident is detected. To exit the program, simply press 'q' or 'ESC'.
