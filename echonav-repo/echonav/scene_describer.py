"""
EchoNav – Scene Describer Node (Slow Loop)
"""

import os
import base64
import threading
import time

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import String
from cv_bridge import CvBridge
import cv2
import numpy as np


ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
OPENAI_API_URL    = "https://api.openai.com/v1/chat/completions"

SCENE_PROMPT = (
    "You are a navigation assistant guiding a visually impaired person out of a building. "
    "In 1-2 short spoken sentences, tell them which direction to move to get closer to an exit. "
    "Look for: exit signs, doors, corridors, stairwells, daylight, or open spaces leading outside. "
    "Be direct and actionable, like 'Turn left, there is a door ahead' or 'Continue straight, exit sign visible ahead'. "
    "Do NOT describe the room. Only give directional guidance toward the nearest exit."
)


class SceneDescriber(Node):
    def __init__(self):
        super().__init__("scene_describer")

        self.declare_parameter("interval_s", 11.0)
        self.declare_parameter("backend", os.getenv("ECHONAV_BACKEND", "anthropic"))
        self.declare_parameter("jpeg_quality", 70)
        self.declare_parameter("resize_width", 640)

        self.interval_s    = self.get_parameter("interval_s").value
        self.backend       = self.get_parameter("backend").value
        self.jpeg_quality  = self.get_parameter("jpeg_quality").value
        self.resize_width  = self.get_parameter("resize_width").value

        self._api_key = (
            os.getenv("ANTHROPIC_API_KEY") if self.backend == "anthropic"
            else os.getenv("OPENAI_API_KEY")
        )

        self.bridge = CvBridge()
        self._latest_frame = None
        self._frame_lock = threading.Lock()
        self._calling_api = False
        self._last_description = ""
        self._last_call_time = 0.0

        self.sub = self.create_subscription(
            Image,
            "/camera/camera/color/image_raw",
            self._rgb_callback,
            1,
        )
        self.pub = self.create_publisher(String, "/echonav/scene_description", 10)

        # Use a wall-clock timer thread instead of ROS timer
        threading.Thread(target=self._timer_loop, daemon=True).start()

        self.get_logger().info(
            f"SceneDescriber ready — backend={self.backend} interval={self.interval_s}s"
        )

    def _rgb_callback(self, msg: Image):
        try:
            frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
        except Exception as e:
            self.get_logger().error(f"CvBridge error: {e}")
            return
        with self._frame_lock:
            self._latest_frame = frame

    def _timer_loop(self):
        while True:
            time.sleep(self.interval_s)
            if not self._calling_api:
                self._describe_scene()

    def _describe_scene(self):
        with self._frame_lock:
            frame = self._latest_frame

        if frame is None:
            return

        h, w = frame.shape[:2]
        if w > self.resize_width:
            scale = self.resize_width / w
            frame = cv2.resize(frame, (self.resize_width, int(h * scale)))

        _, buf = cv2.imencode(
            ".jpg", frame,
            [cv2.IMWRITE_JPEG_QUALITY, self.jpeg_quality]
        )
        b64_image = base64.standard_b64encode(buf.tobytes()).decode("utf-8")

        self._calling_api = True
        threading.Thread(
            target=self._call_api,
            args=(b64_image,),
            daemon=True,
        ).start()

    def _call_api(self, b64_image: str):
        try:
            if self.backend == "anthropic":
                description = self._call_anthropic(b64_image)
            else:
                description = self._call_openai(b64_image)

            if description:
                description = description.strip()
                if description == self._last_description:
                    self.get_logger().info("Scene unchanged — skipping")
                    return
                self._last_description = description
                msg = String()
                msg.data = description
                self.pub.publish(msg)
                self.get_logger().info(f"Scene: {msg.data}")
        except Exception as e:
            self.get_logger().error(f"API error: {e}")
        finally:
            self._calling_api = False

    def _call_anthropic(self, b64_image: str) -> str:
        import urllib.request
        import json

        payload = {
            "model": "claude-opus-4-5",
            "max_tokens": 120,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": b64_image,
                            },
                        },
                        {"type": "text", "text": SCENE_PROMPT},
                    ],
                }
            ],
        }
        req = urllib.request.Request(
            ANTHROPIC_API_URL,
            data=json.dumps(payload).encode(),
            headers={
                "x-api-key": self._api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        return data["content"][0]["text"]

    def _call_openai(self, b64_image: str) -> str:
        import urllib.request
        import json

        payload = {
            "model": "gpt-4o",
            "max_tokens": 120,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{b64_image}",
                                "detail": "low",
                            },
                        },
                        {"type": "text", "text": SCENE_PROMPT},
                    ],
                }
            ],
        }
        req = urllib.request.Request(
            OPENAI_API_URL,
            data=json.dumps(payload).encode(),
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        return data["choices"][0]["message"]["content"]


def main(args=None):
    rclpy.init(args=args)
    node = SceneDescriber()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()