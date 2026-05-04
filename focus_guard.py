import cv2
import mediapipe as mp
# Modüllere doğrudan erişim sağlayarak hata riskini azaltıyoruz
from mediapipe.solutions import face_mesh as mp_face_mesh
from mediapipe.solutions import pose as mp_pose
from mediapipe.solutions import drawing_utils as mp_drawing
import time
import tkinter as tk
from tkinter import ttk, filedialog
from PIL import Image, ImageTk
import threading
import os
import ctypes
import json
import random

class FocusGuard:
    def __init__(self):
        # Taşınabilir Dosya Yolları
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.config_path = os.path.join(self.base_dir, "settings.json")
        self.music_path = os.path.join(self.base_dir, "recep-ivedik-muz-k.mp3")
        self.default_img = os.path.join(self.base_dir, "recep.png")
        
        self.load_config()
        
        # İlk kurulumda varsayılan resmi ekle
        if not self.image_list and os.path.exists(self.default_img):
            self.image_list.append(self.default_img)
            self.save_config()

        self.last_seen_time = time.time()
        self.is_looking_away = False
        self.running = True
        self.system_active = False
        self.current_frame = None
        
        # MediaPipe Modülleri (Güvenli Erişim)
        self.face_mesh = mp_face_mesh.FaceMesh(
            max_num_faces=1, refine_landmarks=True,
            min_detection_confidence=0.5, min_tracking_confidence=0.5
        )
        self.pose = mp_pose.Pose(
            min_detection_confidence=0.5, min_tracking_confidence=0.5
        )
        self.mp_pose = mp_pose # Landmark isimleri için referans
        
        self.root = None
        self.overlay = None
        
        self.thread = threading.Thread(target=self.detection_loop, daemon=True)
        self.thread.start()
        
        self.setup_gui()

    def load_config(self):
        self.timeout = 5
        self.head_sens = 0.12
        self.eye_sens = 0.15
        self.blink_sens = 0.15
        self.volume = 500
        self.opacity = 1.0
        self.image_list = []

        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r") as f:
                    data = json.load(f)
                    self.timeout = data.get("timeout", 5)
                    self.head_sens = data.get("head_sens", 0.12)
                    self.eye_sens = data.get("eye_sens", 0.15)
                    self.blink_sens = data.get("blink_sens", 0.15)
                    self.volume = data.get("volume", 500)
                    self.opacity = data.get("opacity", 1.0)
                    self.image_list = data.get("image_list", [])
            except: pass

    def save_config(self):
        data = {
            "timeout": self.timeout, "head_sens": self.head_sens, 
            "eye_sens": self.eye_sens, "blink_sens": self.blink_sens,
            "volume": self.volume, "opacity": self.opacity,
            "image_list": self.image_list
        }
        with open(self.config_path, "w") as f: json.dump(data, f)

    def setup_gui(self):
        self.root = tk.Tk()
        self.root.title("Focus Guard (Recep İvedik Version)")
        self.root.geometry("1300x850")
        self.root.configure(bg="#050505")
        
        # --- LEFT PANEL: CAMERA (80%) ---
        self.left_panel = tk.Frame(self.root, bg="#000", borderwidth=0, highlightthickness=0)
        self.left_panel.place(relx=0, rely=0, relwidth=0.8, relheight=1.0)

        self.cam_label = tk.Label(self.left_panel, bg="black", borderwidth=0, highlightthickness=0)
        self.cam_label.pack(fill="both", expand=True)

        status_info_f = tk.Frame(self.left_panel, bg="#000")
        status_info_f.pack(fill="x", side="bottom")
        
        self.status_bar = tk.Label(status_info_f, text="SYSTEM INACTIVE", font=("Arial", 14, "bold"), fg="#444", bg="#000", pady=5)
        self.status_bar.pack(side="left", padx=30)
        
        self.timer_label = tk.Label(status_info_f, text="Time: 0.0s", font=("Arial", 13, "bold"), fg="#ff4d4d", bg="#000", pady=5)
        self.timer_label.pack(side="right", padx=30)

        # --- RIGHT PANEL: SETTINGS (20%) ---
        right_panel_container = tk.Frame(self.root, bg="#0a0a0a", borderwidth=0, highlightthickness=0)
        right_panel_container.place(relx=0.8, rely=0, relwidth=0.2, relheight=1.0)

        canvas = tk.Canvas(right_panel_container, bg="#0a0a0a", highlightthickness=0)
        scrollbar = ttk.Scrollbar(right_panel_container, orient="vertical", command=canvas.yview)
        self.scrollable_frame = tk.Frame(canvas, bg="#0a0a0a", padx=15, pady=20)

        self.scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw", width=250)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def _on_mousewheel(event): canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        tk.Label(self.scrollable_frame, text="FOCUS GUARD", font=("Impact", 24), fg="#f0c32d", bg="#0a0a0a").pack(pady=5)
        tk.Label(self.scrollable_frame, text="Recep İvedik Edition", font=("Arial", 10, "italic"), fg="#666", bg="#0a0a0a").pack(pady=(0, 15))

        self.toggle_btn = tk.Button(self.scrollable_frame, text="START SYSTEM", bg="#f0c32d", font=("Arial", 12, "bold"), 
                                   command=self.toggle_system, relief="flat", pady=15, cursor="hand2")
        self.toggle_btn.pack(fill="x", pady=15)

        img_frame = tk.LabelFrame(self.scrollable_frame, text=" Gallery Management ", fg="#f0c32d", bg="#0a0a0a", padx=10, pady=10, font=("Arial", 11, "bold"))
        img_frame.pack(fill="x", pady=10)

        self.img_listbox = tk.Listbox(img_frame, height=3, bg="#111", fg="white", borderwidth=0, font=("Arial", 10))
        self.img_listbox.pack(fill="x", pady=5)
        for path in self.image_list: self.img_listbox.insert("end", os.path.basename(path))
        
        btn_f = tk.Frame(img_frame, bg="#0a0a0a")
        btn_f.pack(fill="x")
        tk.Button(btn_f, text="+ Add Image", command=self.add_image, bg="#222", fg="white", font=("Arial", 9, "bold")).pack(side="left", expand=True, fill="x", padx=2)
        tk.Button(btn_f, text="- Delete", command=self.remove_image, bg="#331111", fg="white", font=("Arial", 9, "bold")).pack(side="left", expand=True, fill="x", padx=2)

        ctrl_frame = tk.Frame(self.scrollable_frame, bg="#0a0a0a")
        ctrl_frame.pack(fill="x", pady=10)

        def create_s(lbl, minv, maxv, cur, cmd, is_sens=False):
            tk.Label(ctrl_frame, text=lbl, fg="#aaa", bg="#0a0a0a", font=("Arial", 10, "bold")).pack(anchor="w", pady=(10,0))
            s = tk.Scale(ctrl_frame, from_=minv, to=maxv, orient="horizontal", bg="#0a0a0a", fg="#f0c32d", 
                        highlightthickness=0, command=cmd, troughcolor="#1a1a1a", font=("Arial", 9))
            s.set(cur if not is_sens else cur*100)
            s.pack(fill="x")
            return s

        create_s("Head Sensitivity", 5, 35, self.head_sens, lambda v: self.update_sens("head", v), True)
        create_s("Eye Sensitivity", 5, 35, self.eye_sens, lambda v: self.update_sens("eye", v), True)
        create_s("Blink Sensitivity", 10, 35, self.blink_sens, lambda v: self.update_sens("blink", v), True)
        create_s("Alert Timeout (s)", 1, 20, self.timeout, self.set_timeout)
        create_s("Volume Control", 0, 1000, self.volume, self.set_volume)
        create_s("Overlay Opacity", 10, 100, self.opacity*100, self.set_opacity)

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.update_gui_frame()
        self.root.mainloop()

    def update_sens(self, type, v):
        val = int(v)/100
        if type == "head": self.head_sens = val
        elif type == "eye": self.eye_sens = val
        elif type == "blink": self.blink_sens = val
        self.save_config()

    def add_image(self):
        files = filedialog.askopenfilenames(filetypes=[("Images", "*.png *.jpg *.jpeg")])
        for f in files:
            if f not in self.image_list:
                self.image_list.append(f)
                self.img_listbox.insert("end", os.path.basename(f))
        self.save_config()

    def remove_image(self):
        sel = self.img_listbox.curselection()
        if sel:
            idx = sel[0]
            self.image_list.pop(idx)
            self.img_listbox.delete(idx)
            self.save_config()

    def set_volume(self, v): self.volume = int(v); self.save_config()
    def set_opacity(self, v): self.opacity = int(v)/100; self.save_config()
    def set_timeout(self, v): self.timeout = int(v); self.save_config()

    def toggle_system(self):
        self.system_active = not self.system_active
        if self.system_active:
            self.toggle_btn.config(text="STOP SYSTEM", bg="#ff4d4d", fg="white")
            self.status_bar.config(text="TRACKING ACTIVE...", fg="#4ade80")
            self.last_seen_time = time.time()
        else:
            self.toggle_btn.config(text="START SYSTEM", bg="#f0c32d", fg="black")
            self.status_bar.config(text="SYSTEM INACTIVE", fg="#444")
            self.timer_label.config(text="Time: 0.0s")
            self.cam_label.config(image="", text="")
            self.hide_overlay()

    def update_gui_frame(self):
        if self.current_frame is not None and self.system_active:
            label_w = self.cam_label.winfo_width()
            label_h = self.cam_label.winfo_height()
            if label_w > 1 and label_h > 1:
                h, w = self.current_frame.shape[:2]
                target_ratio = label_w / label_h
                current_ratio = w / h
                if current_ratio > target_ratio:
                    new_w = int(h * target_ratio)
                    start_x = (w - new_w) // 2
                    cropped = self.current_frame[:, start_x:start_x+new_w]
                else:
                    new_h = int(w / target_ratio)
                    start_y = (h - new_h) // 2
                    cropped = self.current_frame[start_y:start_y+new_h, :]
                img = Image.fromarray(cropped)
                img = img.resize((label_w, label_h), Image.Resampling.LANCZOS)
                tk_img = ImageTk.PhotoImage(img)
                self.cam_label.config(image=tk_img)
                self.cam_label.image = tk_img
        self.root.after(20, self.update_gui_frame)

    def play_music(self):
        try:
            path = self.music_path.replace("\\", "/")
            ctypes.windll.winmm.mciSendStringW(f'open "{path}" type mpegvideo alias my_mp3', None, 0, 0)
            ctypes.windll.winmm.mciSendStringW(f'setaudio my_mp3 volume to {self.volume}', None, 0, 0)
            ctypes.windll.winmm.mciSendStringW('play my_mp3 repeat', None, 0, 0)
        except: pass

    def stop_music(self):
        try:
            ctypes.windll.winmm.mciSendStringW('stop my_mp3', None, 0, 0)
            ctypes.windll.winmm.mciSendStringW(f'close my_mp3', None, 0, 0)
        except: pass

    def detection_loop(self):
        while self.running:
            if self.system_active:
                cap = cv2.VideoCapture(0)
                while self.system_active and self.running:
                    ret, frame = cap.read()
                    if not ret: break
                    frame = cv2.flip(frame, 1)
                    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    results_mesh = self.face_mesh.process(rgb_frame)
                    results_pose = self.pose.process(rgb_frame)
                    focus_ok = False
                    if results_mesh.multi_face_landmarks:
                        face = results_mesh.multi_face_landmarks[0]
                        nose = face.landmark[1]
                        l_b, r_b = face.landmark[234], face.landmark[454]
                        t_b, b_b = face.landmark[10], face.landmark[152]
                        rel_x = (nose.x - min(l_b.x, r_b.x)) / abs(r_b.x - l_b.x)
                        rel_y = (nose.y - min(t_b.y, b_b.y)) / abs(b_b.y - t_b.y)
                        l_iris = face.landmark[468]
                        l_e_l, l_e_r = face.landmark[33], face.landmark[133]
                        l_e_t, l_e_b = face.landmark[159], face.landmark[145]
                        iris_x = (l_iris.x - min(l_e_l.x, l_e_r.x)) / abs(l_e_r.x - l_e_l.x)
                        iris_y = (l_iris.y - min(l_e_t.y, l_e_b.y)) / abs(l_e_b.y - l_e_t.y)
                        eye_ratio = abs(l_e_b.y - l_e_t.y) / abs(l_e_r.x - l_e_l.x)
                        h_ok = (0.5 - self.head_sens) < rel_x < (0.5 + self.head_sens) and (0.55 - self.head_sens) < rel_y < (0.55 + self.head_sens)
                        e_ok = (0.5 - self.eye_sens) < iris_x < (0.5 + self.eye_sens) and iris_y < 0.65
                        o_ok = eye_ratio > self.blink_sens
                        focus_ok = h_ok and e_ok and o_ok
                    color = (0, 255, 0) if focus_ok else (255, 0, 0)
                    if results_pose.pose_landmarks:
                        landmarks = results_pose.pose_landmarks.landmark
                        h, w, _ = rgb_frame.shape
                        ls = landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER]
                        rs = landmarks[self.mp_pose.PoseLandmark.RIGHT_SHOULDER]
                        nose_p = landmarks[self.mp_pose.PoseLandmark.NOSE]
                        ls_xy = (int(ls.x * w), int(ls.y * h))
                        rs_xy = (int(rs.x * w), int(rs.y * h))
                        nose_xy = (int(nose_p.x * w), int(nose_p.y * h))
                        neck_xy = (int((ls_xy[0] + rs_xy[0]) / 2), int((ls_xy[1] + rs_xy[1]) / 2))
                        cv2.line(rgb_frame, nose_xy, neck_xy, color, 3)
                        cv2.line(rgb_frame, ls_xy, rs_xy, color, 3)
                        cv2.circle(rgb_frame, ls_xy, 5, color, -1)
                        cv2.circle(rgb_frame, rs_xy, 5, color, -1)
                        cv2.circle(rgb_frame, nose_xy, 5, color, -1)
                    if focus_ok:
                        self.root.after(0, lambda: [self.status_bar.config(text="FOCUSED ✅", fg="#4ade80"), self.timer_label.config(text="Time: 0.0s")])
                        self.last_seen_time = time.time()
                        if self.is_looking_away: self.hide_overlay()
                    else:
                        dur = time.time() - self.last_seen_time
                        self.root.after(0, lambda d=dur: [self.status_bar.config(text="NOT FOCUSED ❌", fg="#ff4d4d"), self.timer_label.config(text=f"Time: {d:.1f}s")])
                        if dur >= self.timeout and not self.is_looking_away and results_mesh.multi_face_landmarks:
                            self.show_overlay()
                    if not results_mesh.multi_face_landmarks:
                        self.last_seen_time = time.time()
                        self.root.after(0, lambda: [self.status_bar.config(text="NOBODY DETECTED 😴", fg="#888"), self.timer_label.config(text="Time: 0.0s")])
                        if self.is_looking_away: self.hide_overlay()
                    self.current_frame = rgb_frame
                    time.sleep(0.01)
                cap.release()
            else:
                time.sleep(0.5)

    def show_overlay(self):
        if not self.image_list: return
        self.is_looking_away = True
        self.play_music()
        img_path = random.choice(self.image_list)
        try:
            self.overlay = tk.Toplevel(self.root)
            self.overlay.attributes("-fullscreen", True, "-topmost", True, "-alpha", self.opacity)
            self.overlay.configure(bg="black")
            p_img = Image.open(img_path)
            sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
            p_img.thumbnail((sw, sh), Image.Resampling.LANCZOS)
            tk_img = ImageTk.PhotoImage(p_img)
            lbl = tk.Label(self.overlay, image=tk_img, bg="black")
            lbl.image = tk_img
            lbl.pack(expand=True)
            tk.Label(self.overlay, text="NEREYE BAKIYON?!", font=("Arial", 60, "bold"), fg="red", bg="black").pack(pady=20)
        except: pass

    def hide_overlay(self):
        self.is_looking_away = False
        self.stop_music()
        if self.overlay: 
            self.overlay.destroy()
            self.overlay = None

    def on_closing(self):
        self.running = False
        self.system_active = False
        self.save_config()
        self.root.destroy()

if __name__ == "__main__":
    FocusGuard()
