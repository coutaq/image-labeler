import pytesseract
from pytesseract import Output

import math
from typing import Tuple, Union

import cv2
import numpy as np

from deskew import determine_skew
from matplotlib import pyplot as plt
from cv2 import dnn_superres
    

image = cv2.imread('img4.jpg')
config = r'--psm 3 -l rus'
sr = dnn_superres.DnnSuperResImpl_create()
path = "ESPCN_x3.pb"
sr.readModel(path)
sr.setModel("espcn", 3)



def ResizeWithAspectRatio(image, width=None, height=None, inter=cv2.INTER_AREA):
    dim = None
    (h, w) = image.shape[:2]

    if width is None and height is None:
        return image
    if width is None:
        r = height / float(h)
        dim = (int(w * r), height)
    else:
        r = width / float(w)
        dim = (width, int(h * r))

    return cv2.resize(image, dim, interpolation=inter)
# Upscale the image
image = sr.upsample(image)

image = ResizeWithAspectRatio(image, width=1280)
# lab= cv2.cvtColor(image, cv2.COLOR_BGR2LAB)

# #-----Splitting the LAB image to different channels-------------------------
# l, a, b = cv2.split(lab)

# #-----Applying CLAHE to L-channel-------------------------------------------
# clahe = cv2.createCLAHE(clipLimit=50.0, tileGridSize=(8,8))
# cl = clahe.apply(l)
# #-----Merge the CLAHE enhanced L-channel with the a and b channel-----------
# limg = cv2.merge((cl,a,b))

# #-----Converting image from LAB Color model to RGB model--------------------
# final = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)
# final = cv2.cvtColor(final, cv2.COLOR_BGR2GRAY)
def rotate(
        image: np.ndarray, angle: float, background: Union[int, Tuple[int, int, int]]
) -> np.ndarray:
    old_width, old_height = image.shape[:2]
    angle_radian = math.radians(angle)
    width = abs(np.sin(angle_radian) * old_height) + abs(np.cos(angle_radian) * old_width)
    height = abs(np.sin(angle_radian) * old_width) + abs(np.cos(angle_radian) * old_height)

    image_center = tuple(np.array(image.shape[1::-1]) / 2)
    rot_mat = cv2.getRotationMatrix2D(image_center, angle, 1.0)
    rot_mat[1, 2] += (width - old_width) / 2
    rot_mat[0, 2] += (height - old_height) / 2
    return cv2.warpAffine(image, rot_mat, (int(round(height)), int(round(width))), borderValue=background)
    

custom_oem_psm_config = r' --psm 11'


# Create custom kernel
kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2,2))
# Perform closing (dilation followed by erosion)
# close = cv2.morphologyEx(image, cv2.MORPH_CLOSE, kernel)

# Invert image to use for Tesseract
# result = cv2.dilate(close,kernel,iterations = 1)
# result = cv2.morphologyEx(result, cv2.MORPH_OPEN, kernel)
# result = cv2.morphologyEx(result, cv2.MORPH_CLOSE, kernel)

# thresh=255-thresh
# cv2.imshow("thrah", thresh)
# cv2.imshow("res", result)
close = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
ret2,result = cv2.threshold(close,0,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C+cv2.THRESH_OTSU)
# Throw image into tesseract
# angle = determine_skew(result)

gray = cv2.bitwise_not(result)
cv2.imshow("g", gray)
cv2.waitKey(0)
# result = cv2.dilate(result,kernel,iterations = 1)
coords = np.column_stack(np.where(result > 0))
angle = cv2.minAreaRect(coords)[-1]
# the `cv2.minAreaRect` function returns values in the
# range [-90, 0); as the rectangle rotates clockwise the
# returned angle trends to 0 -- in this special case we
# need to add 90 degrees to the angle
if angle < -45:
	angle = -(90 + angle)
# otherwise, just take the inverse of the angle to make
# it positive
else:
	angle = -angle

print(angle)
angle_rad = math.radians(angle)
(h, w) = result.shape[:2]
center = (w // 2, h // 2)
M = cv2.getRotationMatrix2D(center, angle, 1.0)
rotated = cv2.warpAffine(gray, M, (w, h),
	flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
cv2.imshow("gray", rotated)
cv2.waitKey(0)
d = pytesseract.image_to_data(rotated, output_type=Output.DICT, config=config)
n_boxes = len(d['text'])
for i in range(n_boxes):
    if int(d['conf'][i]) > 70:
        (x, y, w, h) = (d['left'][i], d['top'][i], d['width'][i], d['height'][i])
        sin = np.sin(angle_rad)
        cos = np.cos(angle_rad)
        pts = np.array([[x,y],[x+w+w*cos,y+h*sin],[x+w+w*cos,y+h+h*sin],[x+w*cos,y+h+h*sin]], np.int32)
        pts = pts.reshape((-1,1,2))
        close = cv2.polylines(image,[pts],True,(0,255,255))
        print(d["text"][i])
cv2.imshow("img", close)
cv2.waitKey(0)
   
