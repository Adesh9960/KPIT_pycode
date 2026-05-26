import cv2
import os
import numpy as np
from KPIT_pycode.LaneDetection.src.drawTrap import draw_trap
cap = cv2.VideoCapture("data/videos/nD_18.mp4")
print(cap)
print(os.path.exists("data/videos/nD_18.mp4"))
src = np.float32([
     [826, 750],
 [1078, 758],
 [1086, 713],
 [934, 709]
]
 )
#     [1085, 795],
#  [995, 703],
#  [858, 701],
#  [742, 787]

dst = np.float32([
    [300,720],
    [300,0],
    [1000,0],
    [1000,720]
])
if not cap.isOpened():
    print("Could not open video")
    exit()
while True:
    ret, frame = cap.read()
    print(ret, frame)
    if not ret:
        break
    draw_trap(frame, src)
    # M = cv2.getPerspectiveTransform(src, dst)
    # warped = cv2.warpPerspective(
    #     frame,
    #     M,
    #     (frame.shape[1], frame.shape[0])
    # )
    # print("Working")
    # cv2.imshow("Frame", warped)
    cv2.imshow("Frame", frame)

    if cv2.waitKey(1) == 27:
        break

cap.release()
cv2.destroyAllWindows()
