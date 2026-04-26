"""
EchoNav – TTS Queue Node (gTTS + mpg123 version)
Only speaks scene descriptions, obstacle alerts are display-only.
"""

import queue
import threading
import time
import os
import tempfile
from dataclasses import dataclass, field

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

try:
    from gtts import gTTS
    _HAS_GTTS = True
except ImportError:
    _HAS_GTTS = False


PRIORITY_SCENE = 1


@dataclass(order=True)
class TTSItem:
    priority: int
    text: str = field(compare=False)
    timestamp: float = field(compare=False, default_factory=time.time)


class TTSQueue(Node):
    def __init__(self):
        super().__init__("tts_queue")

        self.declare_parameter("scene_cooldown_s", 0.1)
        self.scene_cooldown_s = self.get_parameter("scene_cooldown_s").value

        self._q: queue.PriorityQueue[TTSItem] = queue.PriorityQueue()
        self._last_scene_time = 0.0
        self._last_spoken_text = ""

        if _HAS_GTTS:
            self.get_logger().info("gTTS + mpg123 ready")
        else:
            self.get_logger().warn("gTTS not found — pip install gtts")

        self.create_subscription(String, "/echonav/scene_description", self._scene_cb, 10)

        threading.Thread(target=self._audio_worker, daemon=True).start()

        self.get_logger().info("TTSQueue ready — speaking scene descriptions only")

    def _scene_cb(self, msg: String):
        now = time.time()
        if now - self._last_scene_time < self.scene_cooldown_s:
            return
        if msg.data == self._last_spoken_text:
            return
        self._last_scene_time = now
        self._q.put(TTSItem(priority=PRIORITY_SCENE, text=msg.data))

    def _audio_worker(self):
        while True:
            try:
                item = self._q.get(timeout=0.2)
            except queue.Empty:
                continue
            self._speak(item.text)

    def _speak(self, text: str):
        self.get_logger().info(f"Speaking: {text}")
        if not _HAS_GTTS:
            return
        try:
            self._last_spoken_text = text
            tts = gTTS(text=text, lang="en", tld="com")
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                tmp_path = f.name
            tts.save(tmp_path)
            os.system(f"mpg123 -q --pitch 0.3 {tmp_path}")
            os.unlink(tmp_path)
        except Exception as e:
            self.get_logger().error(f"TTS error: {e}")


def main(args=None):
    rclpy.init(args=args)
    node = TTSQueue()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()