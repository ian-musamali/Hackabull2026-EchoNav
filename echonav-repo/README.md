# EchoNav 🦯

> Wearable AI navigation assistant for the visually impaired.  
> D455 depth camera + ROS2 + Vision AI + Bluetooth audio.

---

## Hardware

| Part | Notes |
|---|---|
| Intel RealSense D455 | Chest-mounted, 15° downward tilt |
| Raspberry Pi 3B v1.2 | USB relay node |
| Laptop (backpack) | Main compute — ROS2 master |
| AirPods | Bluetooth audio output |
| LiPo pack | Powers all nodes |
| 3D-printed chest mount | PLA, 15° tilt, strap clips |

---

## System overview

```
D455 ──USB2──▶ Pi 3B ──WiFi──▶ Laptop
                                  │
                    ┌─────────────┴─────────────┐
                    │                           │
               FAST LOOP (~5 Hz)          SLOW LOOP (~0.3 Hz)
               Depth → zone detector      RGB → Vision AI API
               L/C/R distances            Natural language scene
                    │                           │
                    └─────────────┬─────────────┘
                                  │
                           TTS queue (pyttsx3)
                                  │
                           AirPods (Bluetooth)
```

---

## Installation

### 1. Laptop (main compute)

```bash
# Prerequisites: ROS2 Humble/Iron, Python 3.10+
pip install pyttsx3 opencv-python numpy

# Clone into your ROS2 workspace
cd ~/ros2_ws/src
git clone <this-repo> echonav
cd ~/ros2_ws
colcon build --packages-select echonav
source install/setup.bash
```

### 2. Raspberry Pi 3B

Install ROS2 on the Pi (use the official arm64 packages or build from source).
Then install the RealSense ROS2 driver:

```bash
sudo apt install ros-humble-realsense2-camera
```

Configure the Pi as a ROS2 node that bridges to the laptop:

```bash
# On Pi – set the ROS2 domain to match the laptop
export ROS_DOMAIN_ID=42

# Launch the camera node (streams depth + RGB topics)
ros2 launch realsense2_camera rs_launch.py \
  depth_module.profile:=424x240x15 \
  rgb_camera.profile:=424x240x15 \
  align_depth.enable:=false \
  enable_color:=true \
  enable_depth:=true
```

> **Bandwidth tip:** At 424×240×15fps, USB 2.0 handles both depth and RGB
> comfortably. The laptop subscribes over the local network.

### 3. Bluetooth audio

```bash
# Pair AirPods
bluetoothctl
> scan on
> pair <MAC>
> connect <MAC>
> trust <MAC>

# Set as default PulseAudio sink
pactl set-default-sink bluez_sink.<MAC_underscores>.a2dp_sink

# Verify
paplay /usr/share/sounds/alsa/Front_Center.wav
```

---

## Running EchoNav

### Step 1: Start the Pi camera node (on Pi)
```bash
export ROS_DOMAIN_ID=42
ros2 launch realsense2_camera rs_launch.py \
  depth_module.profile:=424x240x15 \
  rgb_camera.profile:=424x240x15
```

### Step 2: Set your API key (on laptop)
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
# or:
export OPENAI_API_KEY="sk-..."
export ECHONAV_BACKEND="openai"
```

### Step 3: Launch EchoNav (on laptop)
```bash
export ROS_DOMAIN_ID=42
source ~/ros2_ws/install/setup.bash
ros2 launch echonav echonav.launch.py
```

### Optional overrides
```bash
ros2 launch echonav echonav.launch.py \
  danger_m:=0.6 \
  warning_m:=1.2 \
  scene_interval_s:=5.0 \
  rate_wpm:=180
```

---

## ROS2 topics

| Topic | Type | Publisher | Subscriber |
|---|---|---|---|
| `/camera/depth/image_rect_raw` | `sensor_msgs/Image` | Pi (realsense2_camera) | obstacle_detector |
| `/camera/color/image_raw` | `sensor_msgs/Image` | Pi (realsense2_camera) | scene_describer |
| `/echonav/obstacle_alert` | `std_msgs/String` | obstacle_detector | tts_queue |
| `/echonav/scene_description` | `std_msgs/String` | scene_describer | tts_queue |

---

## Tuning guide

| Parameter | Default | Lower → | Higher → |
|---|---|---|---|
| `danger_m` | 0.8 m | Fewer alerts (tight spaces OK) | Earlier warning |
| `warning_m` | 1.5 m | Less chatty | More cautious |
| `fps` | 5 Hz | Less CPU on laptop | Faster reaction |
| `scene_interval_s` | 3.0 s | More frequent descriptions | Quieter |
| `rate_wpm` | 160 | Easier to understand | More information/sec |
| `jpeg_quality` | 70 | Less bandwidth / weaker API image | Better AI accuracy |

---

## Demo checklist

- [ ] D455 chest-mounted, cable routed to Pi in jacket pocket
- [ ] Pi bridging depth + RGB topics over WiFi to laptop
- [ ] Laptop running in backpack, AC or LiPo power
- [ ] AirPods paired and set as default PulseAudio sink
- [ ] `ANTHROPIC_API_KEY` exported
- [ ] `echonav.launch.py` running, all 3 nodes GREEN in `ros2 node list`
- [ ] Test with: `ros2 topic echo /echonav/obstacle_alert`
- [ ] Walk through room with obstacles — audio guidance confirms

---

## 3D print: chest mount

**File:** `cad/d455_chest_mount.stl` (add your design here)

- Material: PLA
- Tilt: 15° forward-downward so the D455 FOV covers 0.5–4m in front on the floor
- Attachment: two 25mm MOLLE-style strap slots for a chest harness
- Camera lock: M4 bolt into D455 tripod thread (1/4"-20 with M4 adapter)

Suggested print settings: 0.2mm layer height, 30% infill, 3 perimeters.

---

## Pitch

> *"A wearable depth camera + AI that talks blind users through any space in
> real time. Obstacle detection, scene description, Bluetooth audio. Built with
> ROS2 and RealSense."*

---

## License

MIT — build freely, hack loudly.
