import socket
import time
import cv2
import threading
import hiwonder.ActionGroupControl as AGC

HOST = "0.0.0.0"
PORT = 50090
U_TURN_STEPS = 16 

class RobotPatrol:
    def __init__(self, camera_capture):
        self.is_patrolling = False
        self.stop_event = threading.Event()
        self.conn = None
        self.cap = camera_capture
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        
        self.detected_faces = []
        self.intruder_visual_timer = 0 
        self.mode = "IDLE"  # <--- New variable to track robot status

    def send_speak(self, text):
        if self.conn:
            try:
                self.conn.sendall(f"SPEAK:{text}\n".encode())
            except: pass

    def run_action(self, action, speak_text=None):
        # Update mode to the current action
        previous_mode = self.mode
        self.mode = action.upper().replace("_", " ")
        
        if speak_text: self.send_speak(speak_text)
        print(f"Action: {action}")
        AGC.runActionGroup(action)
        time.sleep(0.05)
        
        # Reset mode to IDLE if we weren't patrolling
        if not self.is_patrolling:
            self.mode = "IDLE"

    def intruder_alert_sequence(self):
        self.mode = "DEFENDING" # Visual indicator for intruder logic
        self.send_speak("Intruder detected! Wing Chun activated.")
        self.intruder_visual_timer = 30 
        for i in range(3):
            if self.stop_event.is_set(): break
            self.run_action("wing_chun")
        self.send_speak("Area secured.")
        self.mode = "PATROLLING"

    def patrol_logic(self):
        self.is_patrolling = True
        self.mode = "PATROLLING"
        self.stop_event.clear()
        self.send_speak("Patrol started.")
        
        while not self.stop_event.is_set():
            for i in range(1, 11):
                if self.stop_event.is_set(): break
                self.run_action("go_forward", f"Step {i}")
                # Keep mode as PATROLLING after the step
                self.mode = "PATROLLING" 
                
                if len(self.detected_faces) > 0:
                    self.intruder_alert_sequence()

            if self.stop_event.is_set(): break
            self.mode = "TURNING"
            self.send_speak("Turning.")
            for _ in range(U_TURN_STEPS):
                if self.stop_event.is_set(): break
                self.run_action("turn_right")
            self.mode = "PATROLLING"
        
        self.is_patrolling = False
        self.mode = "IDLE"

    def network_listener(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((HOST, PORT))
        server.listen(1)
        while True:
            conn, addr = server.accept()
            self.conn = conn
            try:
                while True:
                    data = conn.recv(1024).decode().strip()
                    if not data: break
                    if data == "patrol":
                        if not self.is_patrolling:
                            threading.Thread(target=self.patrol_logic, daemon=True).start()
                    elif data == "stop patrol":
                        self.stop_event.set()
                        AGC.stopActionGroup()
                        self.run_action("stand", "Standing down.")
                        self.mode = "IDLE"
                    elif data in ["right uppercut", "left uppercut", "right kick", "left kick", "wingchun"]:
                        self.run_action(data.replace(" ", "_"), data.title())
            except: pass
            finally: conn.close(); self.conn = None

def main():
    cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
    if not cap.isOpened():
        cap = cv2.VideoCapture(0)
    
    robot = RobotPatrol(cap)
    threading.Thread(target=robot.network_listener, daemon=True).start()

    print("Robot GUI Online. Press 'q' to quit.")

    while True:
        ret, frame = cap.read()
        if not ret: break

        h, w, _ = frame.shape

        # 1. Face Detection
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = robot.face_cascade.detectMultiScale(gray, 1.2, 5, minSize=(80, 80))
        robot.detected_faces = faces 

        # 2. Draw Boxes around faces
        for (x, y, w_face, h_face) in faces:
            cv2.rectangle(frame, (x, y), (x+w_face, y+h_face), (0, 255, 0), 2)

        # 3. DRAW STATUS BAR (Bottom Overlay)
        # Create a darkened rectangle at the bottom for readability
        cv2.rectangle(frame, (0, h - 40), (w, h), (0, 0, 0), -1) 
        
        status_text = f"MODE: {robot.mode}"
        cv2.putText(frame, status_text, (15, h - 12), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        # 4. Intruder Alert UI (Top)
        if robot.intruder_visual_timer > 0 or len(faces) > 0:
            cv2.putText(frame, "INTRUDER ALERT", (w//2 - 120, 50), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3)
            if len(faces) == 0: robot.intruder_visual_timer -= 1

        cv2.imshow("Robot View", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
