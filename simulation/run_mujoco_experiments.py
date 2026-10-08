import argparse
import time
import os

try:
    import torch
    from transformers import AutoModelForImageTextToText, AutoProcessor
    from PIL import Image, ImageDraw, ImageFont
    import numpy as np
except ImportError as e:
    print(f"Warning: ML dependencies not found. Specific error: {e}")
    print("Please ensure requirements.txt is fully installed on the compute node.")

import mujoco
import imageio

class StretchMujocoEnv:
    def __init__(self, use_gui=False):
        self.use_gui = use_gui
        self.model = mujoco.MjModel.from_xml_path('simulation/custom_scene.xml')
        self.data = mujoco.MjData(self.model)
        self.renderer = mujoco.Renderer(self.model, height=480, width=640)
        
        # We will store frames here to save as a video later
        self.frames = []
        self.current_caption = ""
        print("[MuJoCo] Initialized real MuJoCo offscreen rendering environment.")
        
    def _record_frame(self):
        self.renderer.update_scene(self.data)
        pixels = self.renderer.render()
        if self.current_caption:
            img = Image.fromarray(pixels)
            draw = ImageDraw.Draw(img)
            # Burn text into the top left corner (could use custom font later)
            draw.text((20, 20), self.current_caption, fill=(255, 255, 0))
            pixels = np.array(img)
        self.frames.append(pixels)

    def get_camera_image(self):
        # Render a single frame for VLA
        self._record_frame()
        return Image.fromarray(self.frames[-1])

    def execute_action(self, action_vector):
        print(f"[MuJoCo] Executing action vector: {action_vector}")
        # Drive the robot forward
        self.data.actuator('forward').ctrl[0] = action_vector[0] * 5.0
        for _ in range(40):
            mujoco.mj_step(self.model, self.data)
            self._record_frame()
        self.data.actuator('forward').ctrl[0] = 0.0
        
    def gesture_lean_and_pause(self, target_location):
        print(f"[MuJoCo] GESTURE: Leaning arm toward {target_location} and pausing...")
        # Extend the arm and turn wrist slightly to point
        self.data.actuator('arm_extend').ctrl[0] = 0.25
        self.data.actuator('wrist_yaw').ctrl[0] = 1.0
        for _ in range(40):
            mujoco.mj_step(self.model, self.data)
            self._record_frame()
            
        # Pause for human
        for _ in range(50):
            mujoco.mj_step(self.model, self.data)
            self._record_frame()
            
        # Return to center
        self.data.actuator('arm_extend').ctrl[0] = 0.0
        self.data.actuator('wrist_yaw').ctrl[0] = 0.0
        for _ in range(40):
            mujoco.mj_step(self.model, self.data)
            self._record_frame()
        
    def speak(self, text):
        print(f"[Robot Audio] {text}")
        self.current_caption = f"Robot Audio: {text}"
        # Render a few frames with the text so it stays on screen
        for _ in range(60):
            mujoco.mj_step(self.model, self.data)
            self._record_frame()
        self.current_caption = ""
        
    def save_video(self, filename):
        if len(self.frames) > 0:
            writer = imageio.get_writer(filename, fps=30)
            for frame in self.frames:
                writer.append_data(frame)
            writer.close()
            print(f"[MuJoCo] Saved video to {filename}")
        self.frames = [] # Reset for next mode
        self.current_caption = ""
        mujoco.mj_resetData(self.model, self.data) # Reset simulation state

def load_vla_model(device="cuda"):
    print(f"Loading VLA model on {device}...")
    # This is standard for OpenVLA (openvla/openvla-7b)
    # Using a placeholder function since loading a 7B model requires actual weights
    # processor = AutoProcessor.from_pretrained("openvla/openvla-7b", trust_remote_code=True)
    # vla = AutoModelForVision2Seq.from_pretrained(
    #     "openvla/openvla-7b", 
    #     torch_dtype=torch.bfloat16, 
    #     trust_remote_code=True
    # ).to(device)
    # return vla, processor
    return None, None

def run_clarification_mode(mode, env, vla, processor, log_dir, instruction="bring me the cup"):
    print(f"\n--- Running Condition: {mode.upper()} ---")
    image = env.get_camera_image()
    
    # 1. Immediate Action
    if mode == "immediate":
        print("[Agent] Inferring best action without clarification.")
        # VLA predicts action directly
        env.execute_action([0.1, 0.0, -0.2, 0.0, 1.0])
        
    # 2. Asking for Clarification
    elif mode == "ask":
        print("[Agent] Detected ambiguity. Formulating clarification question.")
        env.speak("Did you mean the red cup on the left, or the blue cup on the right?")
        # Wait for user input (simulated)
        print("[Human] The blue one.")
        env.execute_action([0.5, 0.2, 0.0, 0.0, 1.0])
        
    # 3. Arm Gestures
    elif mode == "gesture":
        print("[Agent] Detected ambiguity. Using physical gesture.")
        env.gesture_lean_and_pause("hypothesized_target_1")
        print("[Human] *Nudges robot to confirm*")
        env.execute_action([0.5, 0.2, 0.0, 0.0, 1.0])
        
    # 4. Hybrid (Ask + Gesture)
    elif mode == "hybrid":
        print("[Agent] Detected ambiguity. Using multi-modal clarification.")
        env.speak("Did you mean this cup?")
        env.gesture_lean_and_pause("hypothesized_target_1")
        print("[Human] Yes, that one.")
        env.execute_action([0.5, 0.2, 0.0, 0.0, 1.0])

    # Save the recorded frames as an MP4 video
    env.save_video(f"{log_dir}/clarification_{mode}.mp4")

def main():
    parser = argparse.ArgumentParser(description='Run MuJoCo Simulation for HRI Project')
    parser.add_argument('--mode', type=str, default='all', choices=['immediate', 'ask', 'gesture', 'hybrid', 'all'])
    parser.add_argument('--log_dir', type=str, default='./data_analysis/pilot_logs')
    parser.add_argument('--use_gui', type=lambda x: (str(x).lower() == 'true'), default=False)
    args = parser.parse_args()

    os.makedirs(args.log_dir, exist_ok=True)
    print(f"Starting MuJoCo simulation for mode: {args.mode}")

    # Initialize Simulator
    env = StretchMujocoEnv(use_gui=args.use_gui)
    
    # Load VLA (assuming running on PACE-ICE with GPU)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    vla, processor = load_vla_model(device)
    
    modes_to_run = ['immediate', 'ask', 'gesture', 'hybrid'] if args.mode == 'all' else [args.mode]
    
    for m in modes_to_run:
        run_clarification_mode(m, env, vla, processor, args.log_dir)

if __name__ == '__main__':
    main()
