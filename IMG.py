import cv2
import numpy as np
from skimage.metrics import structural_similarity as ssim
import math
import os

def psnr(img1, img2):
    """คำนวณค่า Peak Signal-to-Noise Ratio (PSNR)"""
    mse = np.mean((img1 - img2) ** 2)
    if mse == 0:
        return float("inf")
    PIXEL_MAX = 255.0
    return 20 * math.log10(PIXEL_MAX / math.sqrt(mse))

def analyze_images(original_path, line_path):
    # โหลดภาพแบบ BGR
    orig = cv2.imread(original_path)
    line = cv2.imread(line_path)

    if orig is None or line is None:
        raise ValueError("ไม่พบไฟล์ภาพ ตรวจสอบ path อีกครั้ง")

    # ขนาดภาพและไฟล์
    orig_size = os.path.getsize(original_path)
    line_size = os.path.getsize(line_path)

    print(f"Original image: {orig.shape[1]}x{orig.shape[0]} pixels, {orig_size/1024:.1f} KB")
    print(f"LINE image:     {line.shape[1]}x{line.shape[0]} pixels, {line_size/1024:.1f} KB")

    # ย่อ/ขยายภาพให้เท่ากันก่อนคำนวณ SSIM/PSNR
    if orig.shape != line.shape:
        line = cv2.resize(line, (orig.shape[1], orig.shape[0]))

    # แปลงเป็น grayscale
    orig_gray = cv2.cvtColor(orig, cv2.COLOR_BGR2GRAY)
    line_gray = cv2.cvtColor(line, cv2.COLOR_BGR2GRAY)

    # คำนวณ SSIM และ PSNR
    ssim_val = ssim(orig_gray, line_gray, data_range=255)
    psnr_val = psnr(orig_gray, line_gray)

    print(f"SSIM: {ssim_val:.4f} (1.0 = เหมือนเดิมเป๊ะ)")
    print(f"PSNR: {psnr_val:.2f} dB (ยิ่งสูง = ยิ่งใกล้เคียง)")
    print("-" * 50)


# ===== ตัวอย่างการใช้งาน =====
# กำหนด path ของรูปต้นฉบับ และรูปที่ได้จากการส่งผ่าน LINE
original = "TEST_71.jpg"
line_img = "line_oa_chat_250816_231010.jpg"

analyze_images(original, line_img)
