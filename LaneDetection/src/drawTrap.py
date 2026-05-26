import cv2
import numpy as np
def draw_trap(frame, src):
    frame_copy = frame.copy()

    # Draw points
    for i, point in enumerate(src.astype(int)):
        cv2.circle(frame_copy, tuple(point), 8, (0, 0, 255), -1)
        cv2.putText(
            frame_copy,
            str(i),
            tuple(point + np.array([10, -10])),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 0, 0),
            2
        )

    # Draw trapezoid
    cv2.polylines(
        frame_copy,
        [src.astype(np.int32)],
        True,
        (0, 255, 0),
        3
    )
    cv2.imshow("Source Points", frame_copy)