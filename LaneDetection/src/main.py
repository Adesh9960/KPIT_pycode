import cv2
import os
import numpy as np
from drawTrap import draw_trap
from laneExtraction import extractLane
cap = cv2.VideoCapture("data/videos/nD_18.mp4")
print(cap)
print(os.path.exists("data/videos/nD_11.mp4"))
src = np.float32([
    [290, 750],
    [1394, 750],
    [1394, 1070],
    [290, 1070],
])

width = src[1][0] - src[0][0]
height = src[2][1] - src[1][1]
dist = 306
dst = np.float32([
    [0, 0],
    [width, 0],
    [width/2 + dist, height],
    [width/2, height],
])
if not cap.isOpened():
    print("Could not open video")
    exit()

paused = False
while True:
    if not paused:
        ret, frame = cap.read()
        print(ret, frame)
        if not ret:
            break
        car_perspective = draw_trap(frame, src)
        M = cv2.getPerspectiveTransform(src, dst)
        warped = cv2.warpPerspective(
            frame,
            M,
            (int(width), int(height))
        )

        bird_eye_resized = cv2.resize(
            warped,
            (
                int(warped.shape[1] * frame.shape[0] / warped.shape[0]),
                frame.shape[0]
            )
        )
        # combined = np.hstack((car_perspective, bird_eye_resized))
        # display = cv2.resize(
        #     combined,
        #     None,
        #     fx=0.5,
        #     fy=0.5
        # )
        cv2.imshow("Original | Bird Eye", warped)
        # cv2.imshow( "Original ",car_perspective)
    key = cv2.waitKey(30) & 0xFF
    if key == ord('p'):      # pause/resume
        paused = not paused
    elif key == ord('a'):   # rewind 30 frames
        current = int(cap.get(cv2.CAP_PROP_POS_FRAMES))
        cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, current - 30))

    elif key == ord('d'):   # forward 30 frames
        current = int(cap.get(cv2.CAP_PROP_POS_FRAMES))
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        cap.set(cv2.CAP_PROP_POS_FRAMES, min(total - 1, current + 30))
    if key == 27:
        break

cap.release()
cv2.destroyAllWindows()
