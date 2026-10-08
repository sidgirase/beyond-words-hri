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

    def point_at(self, target):
        yaw_val = 1.0 if target == "red" else -1.0 # Red is +y left relative to robot, but wait, stretch wrist yaw: let's just use 1.0 and -1.0
        print(f"[MuJoCo] GESTURE: Pointing at {target} cup...")
        self.data.actuator('arm_extend').ctrl[0] = 0.15
        self.data.actuator('wrist_yaw').ctrl[0] = yaw_val
        for _ in range(30):
            mujoco.mj_step(self.model, self.data)
            self._record_frame()
            
    def retract(self):
        self.data.actuator('wrist_yaw').ctrl[0] = 0.0
        self.data.actuator('arm_extend').ctrl[0] = 0.0
        for _ in range(30):
            mujoco.mj_step(self.model, self.data)
            self._record_frame()

    def touch(self, target):
        yaw_val = 1.0 if target == "red" else -1.0
        print(f"[MuJoCo] ACTION: Touching {target} cup...")
        self.data.actuator('wrist_yaw').ctrl[0] = yaw_val
        self.data.actuator('arm_extend').ctrl[0] = 0.35
        for _ in range(40):
            mujoco.mj_step(self.model, self.data)
            self._record_frame()
        self.retract()
        
    def speak(self, text, duration=60):
        print(f"[Audio] {text}")
        self.current_caption = text
        # Render frames with the text so it stays on screen
        for _ in range(duration):
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

def run_scenario(scenario, env, vla, processor, log_dir):
    print(f"\n--- Running Scenario: {scenario.upper()} ---")
    
    # 1. Assume Mode
    if scenario == "assume":
        env.speak("Robot: Assuming red cup.", duration=30)
        env.touch("red")
        
    # 2. Audio Yes
    elif scenario == "audio_yes":
        env.speak("Robot: Did you mean the red cup?", duration=50)
        env.speak("Human: Yes.", duration=40)
        env.touch("red")
        
    # 3. Audio No
    elif scenario == "audio_no":
        env.speak("Robot: Did you mean the red cup?", duration=50)
        env.speak("Human: No, the blue one.", duration=50)
        env.speak("Robot: Understood.", duration=30)
        env.touch("blue")
        
    # 4. Gesture Yes
    elif scenario == "gesture_yes":
        env.point_at("red")
        env.speak("Human: Yes.", duration=40)
        env.touch("red")
        
    # 5. Gesture No
    elif scenario == "gesture_no":
        env.point_at("red")
        env.speak("Human: No.", duration=40)
        env.retract()
        env.point_at("blue")
        env.speak("Human: Yes.", duration=40)
        env.touch("blue")
        
    # 6. Hybrid Yes
    elif scenario == "hybrid_yes":
        env.point_at("red")
        env.speak("Robot: Did you mean this cup?", duration=50)
        env.speak("Human: Yes.", duration=40)
        env.touch("red")
        
    # 7. Hybrid No
    elif scenario == "hybrid_no":
        env.point_at("red")
        env.speak("Robot: Did you mean this cup?", duration=50)
        env.speak("Human: No, the other one.", duration=50)
        env.retract()
        env.point_at("blue")
        env.speak("Robot: This one?", duration=40)
        env.speak("Human: Yes.", duration=40)
        env.touch("blue")

    # Save the recorded frames as an MP4 video
    env.save_video(f"{log_dir}/scenario_{scenario}.mp4")

def main():
    parser = argparse.ArgumentParser(description='Run MuJoCo Simulation for HRI Project')
    parser.add_argument('--scenario', type=str, default='all', 
                        choices=['assume', 'audio_yes', 'audio_no', 'gesture_yes', 'gesture_no', 'hybrid_yes', 'hybrid_no', 'all'])
    parser.add_argument('--log_dir', type=str, default='./data_analysis/pilot_logs')
    parser.add_argument('--use_gui', type=lambda x: (str(x).lower() == 'true'), default=False)
    args = parser.parse_args()

    # Create timestamped run directory
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    run_dir = os.path.join(args.log_dir, f"run_{timestamp}")
    os.makedirs(run_dir, exist_ok=True)
    print(f"Starting MuJoCo simulation for scenario: {args.scenario}")
    print(f"Saving outputs to: {run_dir}")

    # Initialize Simulator
    env = StretchMujocoEnv(use_gui=args.use_gui)
    
    # Load VLA (assuming running on PACE-ICE with GPU)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    vla, processor = load_vla_model(device)
    
    all_scenarios = ['assume', 'audio_yes', 'audio_no', 'gesture_yes', 'gesture_no', 'hybrid_yes', 'hybrid_no']
    scenarios_to_run = all_scenarios if args.scenario == 'all' else [args.scenario]
    
    for s in scenarios_to_run:
        run_scenario(s, env, vla, processor, run_dir)

if __name__ == '__main__':
    main()
