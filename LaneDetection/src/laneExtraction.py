import cv2
from rotateImg import rotateImg
def extractLane(bev):
    gray = cv2.cvtColor(bev, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray,(31,31), 0)
    # clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
    # contrast_img = clahe.apply(blur)

    sobelx_64f = cv2.Sobel(img, cv2.CV_64F, dx=1, dy=0, ksize=3)
    sobelx = cv2.convertScaleAbs(sobelx_64f)

    sobely_64f = cv2.Sobel(img, cv2.CV_64F, dx=0, dy=1, ksize=3)
    sobely = cv2.convertScaleAbs(sobely_64f)

    sobel_combined = cv2.addWeighted(sobelx, 0.7, sobely, 0.3, 0)
    # edges = cv2.Canny(contrast_img, 50, 150)
    return sobelx

img = cv2.imread('./data/images/lane.png')

rotate = rotateImg(img)
op = extractLane(rotate)
while(1):
    cv2.imshow("Edges", op)
    key = cv2.waitKey(30) & 0xFF
    if key == 27:
        break