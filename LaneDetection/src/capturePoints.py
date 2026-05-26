import cv2
import numpy as np

cap = cv2.VideoCapture("data/videos/nD_18.mp4")

current_frame = 0
points = []

def load_frame(frame_no):
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_no)
    ret, frame = cap.read()
    return frame if ret else None

frame = load_frame(current_frame)

def mouse_callback(event, x, y, flags, param):
    global frame

    if event == cv2.EVENT_LBUTTONDOWN:

        points.append([x, y])

        print(f"Point {len(points)}: ({x}, {y})")

        cv2.circle(frame, (x, y), 8, (0,0,255), -1)

cv2.namedWindow("Frame")
cv2.setMouseCallback("Frame", mouse_callback)

while True:

    cv2.imshow("Frame", frame)

    key = cv2.waitKey(0) & 0xFF

    if key == 27:          # ESC
        break

    elif key == ord('n'):  # Next frame

        current_frame += 1

        new_frame = load_frame(current_frame)

        if new_frame is not None:
            frame = new_frame.copy()

    elif key == ord('p'):  # Previous frame

        current_frame = max(0, current_frame - 1)

        new_frame = load_frame(current_frame)

        if new_frame is not None:
            frame = new_frame.copy()

cv2.destroyAllWindows()
cap.release()