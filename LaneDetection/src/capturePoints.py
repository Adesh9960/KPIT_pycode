import cv2

cap = cv2.VideoCapture("data/videos/nD_17.mp4")
paused = False
scale = 0.5
points = []

def mouse(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN:
        orig_x = int(x / scale)
        orig_y = int(y / scale)
        points.append((orig_x, orig_y))
        print(f"Original: ({orig_x}, {orig_y})")

cv2.namedWindow("Video")
cv2.setMouseCallback("Video", mouse)

while True:
    if not paused:
        ret, frame = cap.read()
        if not ret:
            break
    display = cv2.resize(frame, None, fx=scale, fy=scale)
    cv2.imshow("Video", display)

    key = cv2.waitKey(30) & 0xFF

    if key == ord('p'):  # pause/unpause
        paused = not paused
    elif key == 27:
        break

cap.release()
cv2.destroyAllWindows()
