import cv2

def rotateImg(img):
    (h, w) = img.shape[:2]

    center = (w // 2, h // 2)


    angle = -14.5   # Positive values rotate counter-clockwise, negative clockwise
    scale = 1.0  # 1.0 keeps the original size. 0.5 shrinks it by half.

    rotation_matrix = cv2.getRotationMatrix2D(center, angle, scale)

    rotated_img = cv2.warpAffine(img, rotation_matrix, (w, h))
    return rotated_img
