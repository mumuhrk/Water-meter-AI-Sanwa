import os
import cv2
import torch
import torchvision.transforms as transforms
from PIL import Image
from ultralytics import YOLO
from openpyxl import Workbook
from openpyxl.drawing.image import Image as ExcelImage
import math
import numpy as np
import io
import re
from scipy.ndimage import rotate as scipy_rotate
from transformers import ViTForImageClassification, AutoImageProcessor
import time
# ฟังก์ชันคำนวณจุดศูนย์กลางและรัศมีของ Bounding Box
def calculate_circle(bbox):
    x_min, y_min, x_max, y_max = bbox
    x_c = (x_min + x_max) / 2
    y_c = (y_min + y_max) / 2
    radius = math.sqrt(((x_max - x_c) ** 2) + ((y_max - y_c) ** 2))
    return x_c, y_c, radius

# ฟังก์ชันคำนวณมุมของ Bounding Box ที่สอง
def calculate_angle(center_x, center_y, point_x, point_y):
    angle = math.degrees(math.atan2(point_y - center_y, point_x - center_x))
    if angle < 0:
        angle += 360
    return angle

# ฟังก์ชันหมุนภาพ
def rotate_image(image, angle, center):
    (h, w) = image.shape[:2]
    rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated_image = cv2.warpAffine(image, rotation_matrix, (w, h))
    return rotated_image

# ฟังก์ชันการรีขนาดภาพ
def resize_image(image, max_width=400, max_height=400):
    """
    ปรับขนาดภาพให้พอดีกับหน้าจอ
    :param image: ภาพที่ต้องการปรับขนาด
    :param max_width: ความกว้างสูงสุดของภาพ
    :param max_height: ความสูงสูงสุดของภาพ
    :return: ภาพที่มีขนาดถูกปรับ
    """
    # หาค่าสัดส่วนการปรับขนาด
    height, width = image.shape[:2]
    scale = min(max_width / width, max_height / height)
    
    # ปรับขนาดภาพ
    new_width = int(width * scale)
    new_height = int(height * scale)
    
    resized_image = cv2.resize(image, (new_width, new_height))
    return resized_image

# ฟังก์ขันแบ่งองศาเป็น 10 ส่วน
def get_radiant_circle_section(angle):
    """
    แบ่งมุมออกเป็น 10 ส่วน (0-9) โดยแต่ละส่วนมีมุม 36°
    """
    section = int(angle // 36)  # แบ่ง 360° ออกเป็น 10 ส่วน (36° ต่อส่วน)
    return section
# ฟังก์ชันเรียงไฟล์ให้เรียงตามชื่อไฟล์
def natural_sort_key(s):
    return [int(text) if text.isdigit() else text.lower() for text in re.split('(\d+)', s)]

print("กำลังโหลดโมเดล AI...")
try:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    processor = AutoImageProcessor.from_pretrained("google/vit-base-patch16-224-in21k")
    # โหลดโมเดลที่ฝึกไว้
    modelTB = ViTForImageClassification.from_pretrained(
    'google/vit-base-patch16-224-in21k',
    num_labels=20  # ใส่จำนวนคลาสให้ตรงกับตอนเทรน
    )
    # โหลด state_dict จาก .pt
    model = YOLO("model-1-semi.pt")
    model2 = YOLO("digits.pt")
    # ย้ายโมเดลไปยัง GPU (ถ้ามี)
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    modelTB.load_state_dict(torch.load('TB.pt', map_location=device)) 
    modelTB.to(device)
    modelTB.eval()  # ตั้งค่าเป็นโหมด evaluation (ปิด dropout, batch norm)


    # การแปลงรูปภาพ
    transform = transforms.Compose([ 
    transforms.Resize((224, 224)), 
    transforms.ToTensor(), 
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]) 
    ])
    print("โหลดโมเดล AI สำเร็จ!")
except Exception as e:
    print(f"!!! CRITICAL ERROR: ไม่สามารถโหลดโมเดลได้ - {e}")
    model = None

def read_water_meter(image_input , update_status=lambda msg: None):
    start_total_time = time.perf_counter()
    if model is None:
        return "เกิดข้อผิดพลาด: โมเดล AI ยังไม่ถูกโหลด"
    try:  
        final_reading = None
        final_number_str = ""
        class_namess = []
        avg_inference_time = 0
        error_message = None
         # อ่านภาพ
        update_status("ขั้นตอนที่ 1/5: กำลังจัดแนวรูปภาพ...")
        image = image_input
        result = None


        # ใช้โมเดลตรวจจับมิเตอร์นำ้เเละเข็มหน้าปัดเพื่อหมุนครั่งที่ 1 
        results = model.predict(
            source=image,
            conf=0.7,  # กำหนดความมั่นใจขั้นต่ำ
            classes=[0,1],  # กำหนด class ที่สนใจ
            line_width=1
        )
        # ข้อมูล Bounding Box จากผลลัพธ์ของโมเดล
        boxesRotate1 = results[0].boxes.xyxy.cpu().numpy()  # แปลงผลลัพธ์ Bounding Box เป็น numpy array
        checkclass = results[0].boxes.cls
        bbox1 = None
        bbox2 = None
        rotated_image = None
        # สมมติว่า Bounding Box แรกและที่สองถูกดึงจากผลลัพธ์โมเดล
        match len(boxesRotate1):
            case 0:
                print("ไม่พบอะไรเลย")
            case 1:
                print("พบเเค่วัตถุเดียว")
                bbox1 = boxesRotate1[0]
            case 2:
                print("พบสองวัตถุ")
                if checkclass[0] == 0:
                    bbox1 = boxesRotate1[0]  # [x_min, y_min, x_max, y_max] ของ meter
                    bbox2 = boxesRotate1[1]  # [x_min, y_min, x_max, y_max] ของ dial
                else:
                    bbox1 = boxesRotate1[1]  # [x_min, y_min, x_max, y_max] ของ meter
                    bbox2 = boxesRotate1[0]  # [x_min, y_min, x_max, y_max] ของ dial
        # คำนวณ Radiant Circle จาก Bounding Box แรก
        if bbox1 is None or bbox2 is None :
            print("ไม่สามารถคำนวนมุมครั้งเเรกได้")
        else:
            x_c1, y_c1, radius1 = calculate_circle(bbox1)
            # คำนวณจุดศูนย์กลางของ Bounding Box ที่สอง
            x_c2 = (bbox2[0] + bbox2[2]) / 2
            y_c2 = (bbox2[1] + bbox2[3]) / 2
            # คำนวณมุมของ Bounding Box ที่สองเมื่อเทียบกับศูนย์กลาง Radiant Circle
            angle = calculate_angle(x_c1, y_c1, x_c2, y_c2)
            # หมุนภาพตามมุมที่คำนวณได้
            rotated_image = rotate_image(image, angle, (x_c1, y_c1))
            print("หมุนภาพครั้งเเรกสำเร็จ")



         # ใช้โมเดลตรวจจับมิเตอร์นำ้เเละเข็มหน้าปัดเพื่อหมุนครั่งที่ 2 
        match rotated_image:
            case None : 
                print("เลือกได้ใข้ภาพต้นฉบับ")
                results2 = model.predict(
                    source=image,
                    conf=0.7,  # กำหนดความมั่นใจขั้นต่ำ
                    classes=[0,1],  # กำหนด class ที่สนใจ
                    line_width=1
                )
            case _ :
                print("เลือกใช้ภาพที่หมุุน")
                results2 = model.predict(
                    source=rotated_image,
                    conf=0.7,  # กำหนดความมั่นใจขั้นต่ำ
                    classes=[0,1],  # กำหนด class ที่สนใจ
                    line_width=1
                )
        # ข้อมูล Bounding Box จากผลลัพธ์ของโมเดล
        update_status("ขั้นตอนที่ 2/5: กำลังค้นหาหน้าจอแสดงตัวเลข...")
        boxesRotate2 = results2[0].boxes.xyxy.cpu().numpy()  # แปลงผลลัพธ์ Bounding Box เป็น numpy array
        checkclass = results2[0].boxes.cls
        # สมมติว่า Bounding Box แรกและที่สองถูกดึงจากผลลัพธ์โมเดล
        match len(boxesRotate2):
            case 0:
                print("ไม่พบอะไรเลย")
            case 1:
                print("พบเเค่วัตถุเดียว")
                bbox1 = boxesRotate2[0]
            case 2:
                print("พบสองวัตถุ")
                if checkclass[0] == 0:
                    bbox1 = boxesRotate2[0]  # [x_min, y_min, x_max, y_max] ของ meter
                    bbox2 = boxesRotate2[1]  # [x_min, y_min, x_max, y_max] ของ dial
                else:
                    bbox1 = boxesRotate2[1]  # [x_min, y_min, x_max, y_max] ของ meter
                    bbox2 = boxesRotate2[0]  # [x_min, y_min, x_max, y_max] ของ dial      
        if bbox1 is None or bbox2 is None :
            print("ไม่สามารถคำนวนมุมครั้งที่ 2 ได้")
        else:   
            # คำนวณ Radiant Circle จาก Bounding Box แรก
            x_c1, y_c1, radius1 = calculate_circle(bbox1)
            # คำนวณจุดศูนย์กลางของ Bounding Box ที่สอง
            x_c2 = (bbox2[0] + bbox2[2]) / 2
            y_c2 = (bbox2[1] + bbox2[3]) / 2
            # คำนวณมุมของ Bounding Box ที่สองเมื่อเทียบกับศูนย์กลาง Radiant Circle
            angle2 = calculate_angle(x_c1, y_c1, x_c2, y_c2)
            # หมุนภาพตามมุมที่คำนวณได้
            rotated_image2 = rotate_image(rotated_image, angle2, (x_c1, y_c1))
            print("หมุนภาพครั้งที่สองสำเร็จ")
        # ดึงข้อมูล bounding boxes เเรก จากผลลัพธ์ และ crop ภาพมิเตอร์นำ้
        # Crop ภาพตาม bounding box
        update_status("ขั้นตอนที่ 3/5: กำลังตรวจจับตำแหน่งของตัวเลข...")
        match rotated_image2:
            case None:
                x1, y1, x2, y2 = map(int, bbox1)
                cropped_image = image[y1:y2, x1:x2]
                meterimage = cropped_image
            case _:
                x1, y1, x2, y2 = map(int, bbox1)
                cropped_image = rotated_image2[y1:y2, x1:x2]
                meterimage = cropped_image

        # ใช้โมเดลตรวจจับ blackscreen 
        resultsscreen = model.predict(
            source=meterimage,
            conf=0.5,  # กำหนดความมั่นใจขั้นต่ำ
            classes=[2],  # กำหนด class ที่สนใจ
            line_width=1
        )
        checkcount = resultsscreen[0].boxes.xyxy.cpu().numpy()
        rotate = 1
        while (len(checkcount) != 1 and rotate != 5 ):
            resultsscreen = model.predict(
            source=meterimage,
            conf=0.5,  # กำหนดความมั่นใจขั้นต่ำ
            classes=[2],  # กำหนด class ที่สนใจ
            line_width=1
            )
            meterimage = scipy_rotate(meterimage, rotate, reshape=True).astype(meterimage.dtype)
            rotate = rotate + 1
            checkcount = resultsscreen[0].boxes.xyxy.cpu().numpy()
        boxesscreen = resultsscreen[0].boxes.xyxy.cpu().numpy()  # แปลงผลลัพธ์ Bounding Box เป็น numpy array
        if boxesscreen is None or boxesscreen.size == 0:
            print("ไม่เจอ blackscreen")
        else:
            # สมมติว่า Bounding Box แรกและที่สองถูกดึงจากผลลัพธ์โมเดล
            bboxblackscreen = boxesscreen[0] 
            x1, y1, x2, y2 = map(int, bboxblackscreen)
            screencropped_image1 = meterimage[y1:y2, x1:x2]
            screenimage = screencropped_image1
        


        # ใช้โมเดลตรวจจับเลข
        update_status("ขั้นตอนที่ 4/5: กำลังอ่านค่าตัวเลขแต่ละหลัก...")
        if screenimage is None :
            print("ข้ามไป")
        else:
            resultsnumber = model2.predict(
                source=screenimage,
                conf=0.5,  # กำหนดความมั่นใจขั้นต่ำ
                iou=0.5,
                line_width=1
            )
        checkcount = resultsnumber[0].boxes.xyxy.cpu().numpy()
        rotate = 0
        while len(checkcount) != 4 and rotate != 15 :
            resultsnumber = model2.predict(
                source=screenimage,
                conf=0.5,  # กำหนดความมั่นใจขั้นต่ำ
                iou=0.5,
                line_width=1
            )
            screenimage = scipy_rotate(screenimage, rotate, reshape=True).astype(screenimage.dtype)
            rotate = rotate + 1
            checkcount = resultsnumber[0].boxes.xyxy.cpu().numpy()        
        cropped_data = []
        if len(checkcount) != 0:
            for result in resultsnumber:  
                for box in result.boxes.xyxy:  # ดึงข้อมูล bounding box ในรูปแบบ (x1, y1, x2, y2)
                    x1, y1, x2, y2 = map(int, box)
                    # ตรวจสอบขอบเขตเพื่อหลีกเลี่ยงข้อผิดพลาด
                    y1 = max(0, y1)
                    y2 = min(image.shape[0], y2)
                    x1 = max(0, x1)
                    x2 = min(image.shape[1], x2)
                    # Crop ภาพตาม bounding box
                    cropped_image = screenimage[y1:y2, x1:x2]
                    center_x = (x1 + x2) // 2
                    center_y = (y1 + y2) // 2
                    cropped_data.append((x1, y1, cropped_image))
            # -------------------------------
            # คำนวณหาแนวทางการจัดเรียง
            x_values = [x for x, y, img in cropped_data]
            y_values = [y for x, y, img in cropped_data]

            range_x = max(x_values) - min(x_values)
            range_y = max(y_values) - min(y_values)

            # -------------------------------
            # วิเคราะห์แนว
            if range_y > range_x:
                # แนวตั้ง
                print("แนวตั้ง")
                direction = "top-down" if y_values[0] > y_values[-1] else "bottom-up"
                sort_key = lambda item: item[1]  # ใช้ y
                reverse = direction == "bottom-up"
                print("direction = " ,direction)
            else:
                # แนวนอน
                print("แนวนอน")
                # direction = "left-right" if x_values[0] < x_values[-1] else "right-left"
                direction = "left-right"
                sort_key = lambda item: item[0]  # ใช้ x
                reverse = direction == "right-left"
                print("direction = " ,direction)

            # -------------------------------
            update_status("ขั้นตอนที่ 5/5: กำลังรวบรวมผลลัพธ์...")
            cropped_data.sort(key=sort_key, reverse=reverse)
            # cropped_data.sort(key=lambda x: x[0], reverse=reverse)  # เรียงตาม x1 จากซ้ายไปขวา
            detected_numbers = []
            classes_map = {
                0: "0", 1: "0", 2: "1", 3: "1", 4: "2", 5: "2", 6: "3", 7: "3", 
                8: "4", 9: "4", 10: "5", 11: "5", 12: "6", 13: "6", 14: "7", 15: "7", 
                16: "8", 17: "8", 18: "9", 19: "9"
            }
            class_namess = []
            classes_names_map = {
                0: "0", 1: "0-1", 2: "1", 3: "1-2", 4: "2", 5: "2-3", 6: "3", 7: "3-4", 
                8: "4", 9: "4-5", 10: "5", 11: "5-6", 12: "6", 13: "6-7", 14: "7", 15: "7-8", 
                16: "8", 17: "8-9", 18: "9", 19: "9-0"
            }

            formatted_digit_details = []
            
            for x,y,cropped_item in cropped_data:
                cropped_image = cropped_item  # ดึงเฉพาะภาพจาก tuple
                if cropped_image is None or cropped_image.shape[0] == 0 or cropped_image.shape[1] == 0:
                    print("Invalid cropped image detected")
                    continue
                # แปลง cropped_image เป็น PIL Image
                pil_image = Image.fromarray(cv2.cvtColor(cropped_image, cv2.COLOR_BGR2RGB))
                # แปลงภาพเป็น tensor
                input_tensor = processor(images=pil_image, return_tensors='pt')  # เพิ่มมิติ batch
                input_tensor  = {k: v.to(device) for k, v in input_tensor.items()}
                # วัดเวลาเริ่มต้น
                
                # คำนวณผลลัพธ์ด้วย ResNet
                with torch.no_grad():
                    output = modelTB(**input_tensor)
                    logits = output.logits
                    predicted_class_idx = logits.argmax(-1).item()
                    predicted_class = modelTB.config.id2label[predicted_class_idx]
                    print(f'Predicted class: {predicted_class}')
               
                mapped_value_for_json = classes_map.get(predicted_class_idx, "N/A")

                digit_object = {
                    "predicted_class": predicted_class,
                    "mapped_value": mapped_value_for_json
                }
                formatted_digit_details.append(digit_object)
            
                if predicted_class_idx in classes_map:
                    detected_numbers.append(classes_map[predicted_class_idx])     
                else:
                    print(f"Class {predicted_class_idx} is not in the classes_map.")               
                if predicted_class_idx in classes_names_map:
                    class_namess.append(classes_names_map[predicted_class_idx])     
                else:
                    print(f"Class {predicted_class_idx} is not in the classes_names_map.")
                # วัดเวลาสิ้นสุด
  
        else:
            print("ไม่เจอตัวเลข")
            detected_numbers = []
            class_namess = []
            formatted_digit_details = []
            rotate = "หาตัวเลขไม่เจอ"
        
        
        if 'detected_numbers' in locals() and detected_numbers:
            final_number_str = ''.join(detected_numbers).strip()
             
        if final_number_str:
            try:
                final_reading = int(final_number_str)
            except ValueError:
                final_reading = None
                print(f"ไม่สามารถแปลง '{final_number_str}' เป็น int")
        
        end_total_time = time.perf_counter()
        total_duration_ms = (end_total_time - start_total_time) * 1000
        print(f"CPU LOG: [Water Meter AI] Total processing time: {total_duration_ms:.2f} ms")

        return {
            "final_reading": final_reading,
            "digit_details": formatted_digit_details,
            "error": None
        }

    except Exception as e:
        update_status(f"เกิดข้อผิดพลาด: {str(e)}")
        return {
            "final_reading": None,
            "digit_details": [],
            "error": f"เกิดข้อผิดพลาดรุนแรงใน AI: {str(e)}"
        }