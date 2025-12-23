import socket
import json
import threading
from openai import OpenAI
from kokoro import KPipeline
import soundfile as sf
from playsound import playsound
import os
import uuid

# ====== CONFIG ======
DEEPSEEK_API_KEY = "sk-54257af5fc5f49b08fe00189aaa1bf92"
ROBOT_IP = "192.168.137.19" 
ROBOT_PORT = 50090

client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
pipeline = KPipeline(lang_code="a")

def speak(text):
    """Function to turn text to speech and play it."""
    if not text: return
    generator = pipeline(text, voice="af_heart")
    for _, (_, _, audio) in enumerate(generator):
        fname = f"speech_{uuid.uuid4().hex[:6]}.wav"
        sf.write(fname, audio, 24000)
        playsound(fname)
        os.remove(fname)

def classify_instruction(user_input):
    """LLM classifies input into exact command strings."""
    prompt = f"""
    Classify the user's request into EXACTLY one of these strings:
    "patrol", "stop patrol", "right uppercut", "left uppercut", "right kick", "left kick", "wingchun".
    
    User: {user_input}
    Output only the string.
    """
    resp = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )
    return resp.choices[0].message.content.strip().lower().replace('"', '')

def listen_to_robot(sock):
    """Continuously listens for 'SPEAK:' messages from the robot."""
    while True:
        try:
            data = sock.recv(1024).decode()
            if not data: break
            if "SPEAK:" in data:
                message = data.split("SPEAK:")[1].strip()
                print(f"Robot says: {message}")
                speak(message)
        except:
            break

def main():
    # Create a persistent connection
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect((ROBOT_IP, ROBOT_PORT))
        print("Connected to Robot.")
        
        # Start a thread to listen for the robot's "I am walking" updates
        threading.Thread(target=listen_to_robot, args=(s,), daemon=True).start()
        
        while True:
            user_text = input("\nCommand the Robot > ")
            if user_text.lower() in ['q', 'exit']: break
            
            cmd = classify_instruction(user_text)
            print(f"LLM Classified as: {cmd}")
            
            s.sendall(cmd.encode())
            
    except Exception as e:
        print(f"Connection Error: {e}")
    finally:
        s.close()

if __name__ == "__main__":
    main()
