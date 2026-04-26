from setuptools import find_packages, setup
import os
from glob import glob

package_name = "echonav"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
        (os.path.join("share", package_name, "launch"), glob("launch/*.launch.py")),
        (os.path.join("share", package_name, "config"), glob("config/*.yaml")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="EchoNav Team",
    maintainer_email="you@example.com",
    description="Wearable AI navigation assistant for the visually impaired",
    license="MIT",
    entry_points={
        "console_scripts": [
            "obstacle_detector = echonav.obstacle_detector:main",
            "scene_describer   = echonav.scene_describer:main",
            "tts_queue         = echonav.tts_queue:main",
        ],
    },
)
