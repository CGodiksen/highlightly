import re
import subprocess

import cv2


def scale_image(image: any, scale_percent) -> any:
    """Scale the given image while keeping the aspect ratio."""
    width = int(image.shape[1] * scale_percent / 100)
    height = int(image.shape[0] * scale_percent / 100)

    return cv2.resize(image, (width, height), interpolation=cv2.INTER_AREA)


def optical_character_recognition(path: str) -> dict:
    """Perform optical character recognition on the given images using PaddleOCR."""
    cmd = f"paddleocr --image_dir {path} --use_angle_cls false --lang en --use_gpu false --enable_mkldnn true " \
          f"--use_mp true --show_log false --use_dilation true --det_db_score_mode slow"

    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)

    # For each analyzed frame, save the detections in the frame.
    frame_detections = {}
    for detection in result.stdout.decode().split(f"**********{path}/"):
        split_detection = detection.replace("**********", "").split("\n")
        frame_second: str = split_detection[0].replace('.png', '')

        if frame_second.isdigit():
            frame_detections[int(frame_second)] = re.findall(r"'(.*?)'", detection, re.DOTALL)

    return frame_detections
