# Focus Guard (Recep İvedik Version) 🚀🕺

Focus Guard is a professional AI-powered desktop application designed to keep you focused while working. If you lose focus, it triggers a humorous alert featuring Recep İvedik images and music!

## ✨ Features
- **AI Attention Tracking:** Uses MediaPipe Face Mesh and Pose to monitor head orientation, eye gaze, and blinks.
- **Dynamic Neck Skeleton:** Minimalist skeleton that turns **GREEN** when focused and **RED** when not.
- **Custom Gallery:** Add your own alert images (default is `recep.png`).
- **Interactive Studio UI:** Large camera preview, scrollable settings, volume, and opacity controls.
- **Smart Pause:** Automatically pauses the timer when you leave your desk.

## 🚀 Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/FocusGuard-Recep-Ivedik.git
   cd FocusGuard-Recep-Ivedik
   ```

2. **Create a Virtual Environment:**
   ```bash
   python -m venv .venv
   ```

3. **Install Dependencies:**
   ```bash
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```

4. **Run the App:**
   Just double-click **`FocusGuard_Baslat.bat`** or run:
   ```bash
   python focus_guard.py
   ```

## 📂 Project Structure
- `focus_guard.py`: Main application logic.
- `recep.png`: Default alert image.
- `recep-ivedik-muz-k.mp3`: Alert sound.
- `FocusGuard_Baslat.bat`: Easy launcher for Windows.
- `settings.json`: Your saved sensitivity settings.

## ⚖️ License
This project is for educational and entertainment purposes. Enjoy!
