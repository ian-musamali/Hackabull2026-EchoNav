"""
EchoNav – ROS2 Launch File
Launches the full pipeline on the backpack laptop.

Usage:
    ros2 launch echonav echonav.launch.py
    ros2 launch echonav echonav.launch.py backend:=openai danger_m:=0.6

The realsense2_camera node is launched separately on the Raspberry Pi.
See README for Pi setup instructions.
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription(
        [
            # ── Launch arguments ─────────────────────────────────────
            DeclareLaunchArgument(
                "backend",
                default_value="anthropic",
                description="Vision AI backend: 'anthropic' or 'openai'",
            ),
            DeclareLaunchArgument(
                "danger_m",
                default_value="0.8",
                description="Danger zone threshold in metres",
            ),
            DeclareLaunchArgument(
                "warning_m",
                default_value="1.5",
                description="Warning zone threshold in metres",
            ),
            DeclareLaunchArgument(
                "scene_interval_s",
                default_value="8.0",
                description="Seconds between scene descriptions",
            ),
            DeclareLaunchArgument(
                "rate_wpm",
                default_value="160",
                description="TTS speech rate in words per minute",
            ),

            # ── Obstacle Detector (fast loop) ─────────────────────────
            Node(
                package="echonav",
                executable="obstacle_detector",
                name="obstacle_detector",
                output="screen",
                parameters=[
                    {
                        "danger_m":  LaunchConfiguration("danger_m"),
                        "warning_m": LaunchConfiguration("warning_m"),
                        "fps":       5.0,
                    }
                ],
            ),

            # ── Scene Describer (slow loop) ───────────────────────────
            Node(
                package="echonav",
                executable="scene_describer",
                name="scene_describer",
                output="screen",
                parameters=[
                    {
                        "backend":    LaunchConfiguration("backend"),
                        "interval_s": LaunchConfiguration("scene_interval_s"),
                        "jpeg_quality": 70,
                        "resize_width": 640,
                    }
                ],
            ),

            # ── TTS Queue (audio output) ──────────────────────────────
            Node(
                package="echonav",
                executable="tts_queue",
                name="tts_queue",
                output="screen",
                parameters=[
                    {
                        "rate_wpm":            LaunchConfiguration("rate_wpm"),
                        "volume":              0.9,
                        "obstacle_cooldown_s": 2.0,
                        "scene_cooldown_s":    4.0,
                    }
                ],
            ),
        ]
    )
