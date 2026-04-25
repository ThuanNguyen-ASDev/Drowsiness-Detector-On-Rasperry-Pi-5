import cv2
import time
import threading
import sys
import os
import glob # [MỚI] Thư viện tìm kiếm file
import numpy as np
import dlib
from scipy.spatial import distance as dist
from imutils import face_utils
from datetime import datetime

# --- [MỚI] IMPORT THƯ VIỆN GIAO DIỆN VÀ ÂM THANH ---
import tkinter as tk
from tkinter import messagebox
try:
    import pygame
except ImportError:
    print("❌ Lỗi: Chưa cài đặt pygame. Hãy chạy: pip install pygame")
    sys.exit()

# --- KIỂM TRA THƯ VIỆN PI 5 ---
try:
    from picamera2 import Picamera2
except ImportError:
    print("❌ Lỗi: Chưa cài đặt Picamera2.")
    sys.exit()

# --- CẤU HÌNH ---
HW_RES = (1280, 720)
PROCESS_RES = (640, 480)
EYE_AR_THRESH = 0.25      
EYE_AR_CONSEC_FRAMES = 15 
YAWN_THRESH = 25          
YAWN_MIN_DURATION = 1.5   
MODEL_PATH = "shape_predictor_68_face_landmarks.dat"
SOUND_DIR = "sounds" # [MỚI] Thư mục chứa file nhạc

# --- BIẾN TOÀN CỤC ---
COUNTER_EYE = 0
YAWN_START_TIME = None
ALARM_ON = False
ALARM_TYPE = "None"
STOP_THREAD = False
SELECTED_MP3 = None # [MỚI] Biến lưu đường dẫn file nhạc được chọn

# --- [THAY ĐỔI] HÀM XỬ LÝ ÂM THANH (DÙNG PYGAME) ---
def sound_alarm_loop():
    global ALARM_ON, STOP_THREAD, SELECTED_MP3
    
    # Khởi tạo mixer của pygame
    pygame.mixer.init()
    
    # Load nhạc nếu người dùng đã chọn
    music_loaded = False
    if SELECTED_MP3 and os.path.exists(SELECTED_MP3):
        try:
            pygame.mixer.music.load(SELECTED_MP3)
            music_loaded = True
            print(f"🎵 Đã tải nhạc: {os.path.basename(SELECTED_MP3)}")
        except Exception as e:
            print(f"❌ Lỗi tải file nhạc: {e}")

    while not STOP_THREAD:
        if ALARM_ON:
            if music_loaded:
                # Nếu nhạc chưa chơi thì bắt đầu chơi (lặp vô tận = -1)
                if not pygame.mixer.music.get_busy():
                    pygame.mixer.music.play(-1)
            else:
                # Fallback: Nếu không chọn nhạc hoặc lỗi, dùng tiếng beep cũ
                os.system('play -n synth 0.5 sin 2500 >/dev/null 2>&1')
                time.sleep(0.1) 
        else:
            # [QUAN TRỌNG] Tắt nhạc ngay khi hết báo động
            if music_loaded and pygame.mixer.music.get_busy():
                pygame.mixer.music.stop()
            time.sleep(0.1)

# --- [MỚI] GIAO DIỆN CHỌN NHẠC (Tkinter) ---
def show_music_selector():
    global SELECTED_MP3
    
    # Tạo thư mục nếu chưa có
    if not os.path.exists(SOUND_DIR):
        os.makedirs(SOUND_DIR)
        print(f"⚠️ Đã tạo thư mục '{SOUND_DIR}'. Hãy bỏ file .mp3 vào đó!")

    # Tìm file mp3
    mp3_files = glob.glob(os.path.join(SOUND_DIR, "*.mp3"))
    
    # Nếu không có file nào, bỏ qua giao diện
    if not mp3_files:
        print("⚠️ Không tìm thấy file MP3 nào trong thư mục 'sounds'. Sử dụng âm thanh mặc định.")
        return

    # Cửa sổ giao diện
    root = tk.Tk()
    root.title("Cấu hình Báo Động")
    root.geometry("400x300")
    
    lbl = tk.Label(root, text="CHỌN NHẠC CẢNH BÁO:", font=("Arial", 12, "bold"))
    lbl.pack(pady=10)

    # Danh sách file
    listbox = tk.Listbox(root, font=("Arial", 10), selectmode=tk.SINGLE)
    for f in mp3_files:
        listbox.insert(tk.END, os.path.basename(f)) # Chỉ hiện tên file
    listbox.pack(expand=True, fill="both", padx=20)

    # Nút xác nhận
    def on_confirm():
        global SELECTED_MP3
        selection = listbox.curselection()
        if selection:
            index = selection[0]
            filename = listbox.get(index)
            SELECTED_MP3 = os.path.join(SOUND_DIR, filename)
            root.destroy() # Đóng cửa sổ để chạy tiếp chương trình
        else:
            messagebox.showwarning("Chú ý", "Vui lòng chọn một bài hát!")

    btn = tk.Button(root, text="BẮT ĐẦU GIÁM SÁT", command=on_confirm, bg="green", fg="white", font=("Arial", 10, "bold"))
    btn.pack(pady=20)

    # Mặc định chọn bài đầu tiên
    listbox.selection_set(0)
    
    print("🖥️ Đang hiển thị giao diện chọn nhạc...")
    root.mainloop()

# --- CÁC HÀM TÍNH TOÁN ---
def start_alarm(reason):
    global ALARM_ON, ALARM_TYPE
    if not ALARM_ON:
        ALARM_ON = True
        ALARM_TYPE = reason
        current_time = datetime.now().strftime("%H:%M:%S")
        print(f"\n[LOG {current_time}] 🚨 PHÁT HIỆN: {reason}! ĐANG BÁO ĐỘNG...")

def stop_alarm():
    global ALARM_ON, ALARM_TYPE
    if ALARM_ON:
        ALARM_ON = False
        ALARM_TYPE = "None"
        print(f"\n[LOG] ✅ Đã tỉnh táo. Tắt báo động.")

def eye_aspect_ratio(eye):
    A = dist.euclidean(eye[1], eye[5])
    B = dist.euclidean(eye[2], eye[4])
    C = dist.euclidean(eye[0], eye[3])
    return (A + B) / (2.0 * C)

def lip_distance(shape):
    top_lip = shape[50:53]
    top_lip = np.concatenate((top_lip, shape[61:64]))
    low_lip = shape[56:59]
    low_lip = np.concatenate((low_lip, shape[65:68]))
    top_mean = np.mean(top_lip, axis=0)
    low_mean = np.mean(low_lip, axis=0)
    return abs(top_mean[1] - low_mean[1])

# --- CLASS CAMERA ---
class CameraStream:
    def __init__(self):
        self.picam2 = Picamera2()
        config = self.picam2.create_video_configuration(
            main={"size": HW_RES, "format": "RGB888"}
        )
        self.picam2.configure(config)
        try:
            self.picam2.set_controls({"AfMode": 2, "AfRange": 0})
        except: pass
        self.picam2.start()
        
        self.frame = None
        self.running = False
        self.lock = threading.Lock()

    def start(self):
        self.running = True
        t = threading.Thread(target=self._update, args=())
        t.daemon = True
        t.start()
        return self

    def _update(self):
        while self.running:
            try:
                img = self.picam2.capture_array()
                img_small = cv2.resize(img, PROCESS_RES)
                img_small = cv2.flip(img_small, 0)
                with self.lock:
                    self.frame = img_small
            except: pass

    def read(self):
        with self.lock:
            return self.frame.copy() if self.frame is not None else None

    def stop(self):
        self.running = False
        self.picam2.stop()

# --- MAIN PROGRAM ---
if not os.path.exists(MODEL_PATH):
    print(f"❌ Không tìm thấy file model: {MODEL_PATH}")
    sys.exit()

# [MỚI] GỌI GIAO DIỆN CHỌN NHẠC TRƯỚC KHI KHỞI ĐỘNG HỆ THỐNG
show_music_selector()

print("⏳ Đang tải thư viện Dlib...")
detector = dlib.get_frontal_face_detector()
predictor = dlib.shape_predictor(MODEL_PATH)

(lStart, lEnd) = face_utils.FACIAL_LANDMARKS_IDXS["left_eye"]
(rStart, rEnd) = face_utils.FACIAL_LANDMARKS_IDXS["right_eye"]

print("📷 Đang khởi động Camera Pi 5...")
stream = CameraStream().start()

# Khởi chạy luồng âm thanh
alarm_thread = threading.Thread(target=sound_alarm_loop)
alarm_thread.daemon = True
alarm_thread.start()

time.sleep(2.0)
print("🚀 Bắt đầu theo dõi... (Nhấn 'q' để thoát)")

prev_frame_time = 0

try:
    while True:
        frame = stream.read()
        if frame is None:
            time.sleep(0.01)
            continue

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        rects = detector(gray, 0)

        frame_status = "NORMAL"
        status_color = (0, 255, 0)
        
        # Tinh FPS
        new_frame_time = time.time()
        fps = 1/(new_frame_time-prev_frame_time) if (new_frame_time-prev_frame_time) > 0 else 0
        prev_frame_time = new_frame_time
        
        if len(rects) > 0:
            rect = max(rects, key=lambda r: r.width() * r.height())
            shape = predictor(gray, rect)
            shape = face_utils.shape_to_np(shape)

            # 1. XỬ LÝ MẮT
            leftEye = shape[lStart:lEnd]
            rightEye = shape[rStart:rEnd]
            ear = (eye_aspect_ratio(leftEye) + eye_aspect_ratio(rightEye)) / 2.0
            ear_val=ear

            # 2. XỬ LÝ MIỆNG
            distance = lip_distance(shape)
            mar_val=distance
            
            # Vẽ viền
            leftEyeHull = cv2.convexHull(leftEye)
            rightEyeHull = cv2.convexHull(rightEye)
            lip = shape[48:60]
            cv2.drawContours(frame, [leftEyeHull], -1, (0, 0, 0), 1)
            cv2.drawContours(frame, [rightEyeHull], -1, (0, 0, 0), 1)
            cv2.drawContours(frame, [lip], -1, (100, 200, 255), 1)

            # === LOGIC KIỂM TRA BUỒN NGỦ ===
            if ear < EYE_AR_THRESH:
                COUNTER_EYE += 1
                if COUNTER_EYE >= EYE_AR_CONSEC_FRAMES:
                    start_alarm("BUỒN NGỦ")
                    frame_status = "DROWSY!"
                    status_color = (0, 0, 255)
            else:
                COUNTER_EYE = 0

            # === LOGIC KIỂM TRA NGÁP ===
            if distance > YAWN_THRESH:
                if YAWN_START_TIME is None:
                    YAWN_START_TIME = time.time()
                
                elapsed_yawn = time.time() - YAWN_START_TIME
                
                # Hiển thị thời gian ngáp
                cv2.putText(frame, f"Yawn: {elapsed_yawn:.1f}s", (10, PROCESS_RES[1] - 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 2)

                if elapsed_yawn >= YAWN_MIN_DURATION:
                    start_alarm(f"NGÁP ({elapsed_yawn:.1f}s)")
                    frame_status = "YAWNING!"
                    status_color = (0, 165, 255)
            else:
                YAWN_START_TIME = None

            # Tắt báo động nếu mọi chỉ số ok
            if ALARM_ON:
                if ear > EYE_AR_THRESH and distance < YAWN_THRESH:
                    stop_alarm()
                    
            curr_time = datetime.now().strftime("%H:%M:%S")
            sys.stdout.write(f"\r[{curr_time}] FPS:{int(fps):2d} | St:{frame_status:^8} | EAR:{ear_val:.2f} | MAR:{mar_val:.1f} ")
            sys.stdout.flush()

            # Hiển thị thông số
            cv2.putText(frame, f"EAR: {ear:.2f}", (PROCESS_RES[0] - 120, 30), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
            cv2.putText(frame, f"MAR: {distance:.1f}", (PROCESS_RES[0] - 120, 55), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
            cv2.putText(frame, f"FPS: {int(fps):2d}", (PROCESS_RES[0] - 120, 80),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

        else:
            frame_status = "NO FACE"
            status_color = (100, 100, 100)
            if ALARM_ON: stop_alarm()

        # Cảnh báo màn hình đỏ chót
        if ALARM_ON:
            cv2.rectangle(frame, (0, 0), PROCESS_RES, (0, 0, 255), 10)
            cv2.putText(frame, "WAKE UP!", (PROCESS_RES[0]//2 - 80, PROCESS_RES[1]//2), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3)

        cv2.putText(frame, f"Status: {frame_status}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, status_color, 2)

        cv2.imshow("Pi 5 - Driver Monitor", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break

except KeyboardInterrupt:
    pass

finally:
    print("\n[INFO] Đang dừng chương trình...")
    STOP_THREAD = True
    ALARM_ON = False
    stream.stop()
    # [MỚI] Thoát mixer nếu đã khởi tạo
    if 'pygame' in sys.modules:
        pygame.mixer.quit()
    cv2.destroyAllWindows()
    print("[INFO] Hoàn tất.")