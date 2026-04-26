"""
EchoNav – Obstacle Detector Node (Fast Loop)
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import String
from cv_bridge import CvBridge
import numpy as np


ZONES = {
    "left":   (0.0,  0.33),
    "center": (0.33, 0.67),
    "right":  (0.67, 1.0),
}

DANGER_M   = 0.8
WARNING_M  = 1.5
CLEAR_M    = 2.5
MM_TO_M    = 0.001


class ObstacleDetector(Node):
    def __init__(self):
        super().__init__("obstacle_detector")

        self.declare_parameter("danger_m",  DANGER_M)
        self.declare_parameter("warning_m", WARNING_M)
        self.declare_parameter("clear_m",   CLEAR_M)
        self.declare_parameter("fps",       2.0)

        self.danger_m  = self.get_parameter("danger_m").value
        self.warning_m = self.get_parameter("warning_m").value
        self.clear_m   = self.get_parameter("clear_m").value

        self.bridge = CvBridge()
        self._last_msg_time = 0.0

        fps = self.get_parameter("fps").value
        self._min_interval = 1.0 / fps

        self.sub = self.create_subscription(
            Image,
            "/camera/camera/depth/image_rect_raw",
            self._depth_callback,
            10,
        )
        self.pub = self.create_publisher(String, "/echonav/obstacle_alert", 10)

        self.get_logger().info("ObstacleDetector ready")

    def _depth_callback(self, msg: Image):
        now = self.get_clock().now().nanoseconds * 1e-9
        if now - self._last_msg_time < self._min_interval:
            return
        self._last_msg_time = now

        try:
            depth_img = self.bridge.imgmsg_to_cv2(msg, desired_encoding="passthrough")
        except Exception as e:
            self.get_logger().error(f"CvBridge error: {e}")
            return

        depth_m = depth_img.astype(np.float32) * MM_TO_M
        depth_m[depth_m == 0] = np.nan

        h, w = depth_m.shape
        alerts = []

        for zone_name, (frac_start, frac_end) in ZONES.items():
            col_s = int(frac_start * w)
            col_e = int(frac_end * w)
            zone  = depth_m[:, col_s:col_e]

            valid = zone[~np.isnan(zone)]
            if valid.size == 0:
                continue
            dist = float(np.percentile(valid, 5))

            if dist < self.danger_m:
                level = "DANGER"
            elif dist < self.warning_m:
                level = "WARNING"
            elif dist < self.clear_m:
                level = "CAUTION"
            else:
                continue

            alerts.append((level, zone_name, dist))

        if not alerts:
            return

        priority = {"DANGER": 0, "WARNING": 1, "CAUTION": 2}
        alerts.sort(key=lambda x: (priority[x[0]], x[2]))

        parts = []
        for level, zone, dist in alerts:
            if zone == "center":
                direction = "ahead"
            elif zone == "left":
                direction = "left"
            else:
                direction = "right"

            parts.append(f"{direction} {dist:.1f}")

        msg_out = String()
        msg_out.data = ". ".join(parts)
        self.pub.publish(msg_out)
        self.get_logger().debug(f"Alert: {msg_out.data}")


def main(args=None):
    rclpy.init(args=args)
    node = ObstacleDetector()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()