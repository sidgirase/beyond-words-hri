import argparse

def main():
    parser = argparse.ArgumentParser(description='Run MuJoCo Simulation for HRI Project')
    parser.add_argument('--mode', type=str, default='all', help='Clarification mode: immediate, ask, gesture, hybrid, or all')
    parser.add_argument('--log_dir', type=str, default='./logs', help='Directory to save logs')
    parser.add_argument('--use_gui', type=bool, default=True, help='Enable MuJoCo GUI')
    args = parser.parse_args()

    print(f"Starting MuJoCo simulation for mode: {args.mode}")
    # TODO: P1 - Implement VLA deployment and 4 modes here

if __name__ == '__main__':
    main()
