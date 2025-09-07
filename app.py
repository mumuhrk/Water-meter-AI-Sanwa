import os, sys, cv2, numpy as np, traceback, uuid, threading, time, json, hashlib, random, platform
from flask import Flask, request, abort, jsonify
from flask_cors import CORS

# --- 1. ส่วน Import ของ LINE SDK ---
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration, ApiClient, MessagingApi,
    ReplyMessageRequest, TextMessage
)
from linebot.v3.webhooks import (
    MessageEvent, TextMessageContent, ImageMessageContent
)

# --- 2. ส่วน Import ของ AI ---
try:
    from WMDP import read_water_meter
    print("INFO: Successfully loaded 'read_water_meter' from WMDP.py")
except ImportError:
    print("ERROR: WMDP.py not found or failed to import.")
    sys.exit(1)


# --- 3. ตั้งค่า Flask App และส่วนกลาง ---
app = Flask(__name__)
CORS(app)

configuration = Configuration(access_token='GxQHa5n02D5+7m26nUE4uAOZxCI+xcZH0q+R8qipoRv285ftqsus24MIVsGggqbsJpY1cmKHZ5A6ULf70GjB+VXImKfIX8SCzH/j6WZ1Mj3uot/p18S7XDyi/+bZ/hmuazrHhQz0U2algMqZA7fpMgdB04t89/1O/w1cDnyilFU=')
handler = WebhookHandler('28a91b4bff1a14931c6124b347cd7d8b')

# --- Seed เพื่อความ reproducible ---
try:
    import torch
    torch.manual_seed(42)
    if torch.cuda.is_available():
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False
except ImportError:
    pass
np.random.seed(42)
random.seed(42)

# --- Debug: Log Environment ---
def log_environment():
    try:
        import torch
        torch_version = torch.__version__
    except ImportError:
        torch_version = "not-installed"

    print("===== DEBUG ENVIRONMENT =====")
    print(f"torch={torch_version}")
    print(f"cv2={cv2.__version__}")
    print(f"numpy={np.__version__}")
    print(f"python={platform.python_version()}")
    print(f"system={platform.system()}")
    print("=============================")

log_environment()

# --- Helper: Compute SHA256 of bytes ---
def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

# --- 4. ส่วนกลางสำหรับ Web API ---
TASKS = {}
def process_image_for_web(task_id, image_opencv):
    """ฟังก์ชันทำงานเบื้องหลังสำหรับเว็บ"""
    def update_progress(message):
        TASKS[task_id]['progress'] = message
    try:
        TASKS[task_id]['status'] = 'processing'
        result_dict = read_water_meter(image_opencv, update_status=update_progress)
        TASKS[task_id]['status'] = 'complete'
        TASKS[task_id]['result'] = result_dict
    except Exception as e:
        TASKS[task_id]['status'] = 'error'
        TASKS[task_id]['error_message'] = str(e)

# --- 5. API สำหรับหน้าเว็บ (แบบมี Progress) ---
@app.route("/submit_task", methods=['POST'])
def submit_task():
    if 'image' not in request.files: return jsonify({"error": "No image file"}), 400
    file = request.files['image']
    image_bytes = file.read()
    image_np_array = np.frombuffer(image_bytes, np.uint8)
    image_opencv = cv2.imdecode(image_np_array, cv2.IMREAD_COLOR)
    task_id = str(uuid.uuid4())
    TASKS[task_id] = {'status': 'queued', 'progress': 'queued'}
    thread = threading.Thread(target=process_image_for_web, args=(task_id, image_opencv))
    thread.start()
    return jsonify({"task_id": task_id}), 202

@app.route("/task_status/<task_id>", methods=['GET'])
def get_task_status(task_id):
    task = TASKS.get(task_id)
    if not task: return jsonify({"error": "Task not found"}), 404
    return jsonify(task)


# --- 6. API สำหรับ LINE Bot (แบบ Monolith ที่รวดเร็ว) ---
@app.route("/webhook", methods=['POST'])
def webhook():
    signature = request.headers.get('X-Line-Signature', '')
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    except Exception as e:
        app.logger.error(f"Webhook handler error: {traceback.format_exc()}")
        abort(500)
    return 'OK'

@handler.add(MessageEvent, message=ImageMessageContent)
def handle_image_message(event):
    start_time = time.time()
    try:
        with ApiClient(configuration) as api_client:
            resource_path = f'/v2/bot/message/{event.message.id}/content'
            http_response = api_client.call_api(
                resource_path, 'GET', response_types_map={ 200: "file" },
                auth_settings=['Bearer'], _return_http_data_only=False,
                _preload_content=False, _host="https://api-data.line.me"
            )
            message_content = http_response.raw_data
            
            # --- บันทึกไฟล์ที่ได้รับจาก LINE เพื่อใช้ Debug (เพิ่มส่วนนี้) ---
            debug_dir = "received_from_line"
            if not os.path.exists(debug_dir):
                os.makedirs(debug_dir)
            file_path = os.path.join(debug_dir, f"{event.message.id}.jpg")
            with open(file_path, "wb") as f:
                f.write(message_content)
            print(f"DEBUG: Saved incoming image to {file_path}")
            # --- จบส่วนบันทึกไฟล์ ---

            image_np_array = np.frombuffer(message_content, np.uint8)
            image_opencv = cv2.imdecode(image_np_array, cv2.IMREAD_COLOR)
            result_dict = read_water_meter(image_opencv, update_status=lambda msg: print(f"[WMDP] {msg}"))
            
            final_reading_display = None
            error_message = None
            if isinstance(result_dict, dict):
                error_message = result_dict.get('error')
                final_reading = result_dict.get('final_reading')
                if error_message:
                    final_reading_display = None
                else:
                    if final_reading is None:
                        final_reading_display = None
                    else:
                        final_reading_display = str(final_reading)
            else:
                error_message = str(result_dict)
                final_reading_display = None

            if error_message:
                reply_message_text = f"เกิดข้อผิดพลาดในการอ่านค่าน้ำ:\n{error_message}"
            else:
                if final_reading_display is None:
                    reply_message_text = "ไม่สามารถอ่านค่าน้ำได้อย่างชัดเจน (ผลไม่แน่นอน)"
                else:
                    reply_message_text = f"Water meter reading:\n{final_reading_display}"

            end_time = time.time()
            processing_duration = (end_time - start_time) * 1000
            print(f"AppAPI LATENCY_DATA: {{'server_processing_time_ms': {processing_duration:.2f}}}")
            
            line_bot_api = MessagingApi(api_client)
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=reply_message_text)]
                )
            )
    except Exception as e:
        app.logger.error(f"AN EXCEPTION OCCURRED in LINE Handler:\n{traceback.format_exc()}")


@handler.add(MessageEvent, message=TextMessageContent)
def handle_text_message(event):
    user_text = event.message.text.strip().lower()
    reply_text = ''
    if user_text == 'help':
        reply_text = "📸 How to Use 📸\n\n1. Take a clear picture of the water meter...\n2. Send the picture...\n3. Please wait a moment...\n4. The system will reply with the reading."
    elif user_text == 'credits':
        reply_text = "Developed by:\nMr. Sujinda...\nAdvisor:\nAsst. Prof. Dr. Khwanchai Ueaviriyanukul"
    else:
        reply_text = 'Please send a picture of a water meter for the AI to process, or try typing "help".'
    
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply_text)]
            )
        )

# --- 7. API สำหรับ Debugging (เพิ่มเข้ามาใหม่) ---
# Endpoint นี้ใช้สำหรับวินิจฉัยความแตกต่างระหว่าง Local และ Cloud Run
# อย่าลืมนำออกเมื่อ Debug เสร็จสิ้น
@app.route('/run-debug-analysis', methods=['GET'])
def run_debug_analysis():
    """
    Endpoint นี้เมื่อถูกเรียก จะสั่งรันการวินิจฉัยเปรียบเทียบผลลัพธ์
    และส่งผลลัพธ์กลับมาเป็น JSON
    """
    # --- Helper Functions (ยกมาจาก debug_compare.py) ---
    def set_deterministic_seed(seed=42):
        """ตั้งค่า Seed เพื่อให้ผลลัพธ์มีความแน่นอน (Deterministic)"""
        import random
        # ตรวจสอบว่า torch มีติดตั้งหรือไม่ก่อนเรียกใช้
        try:
            import torch
            torch.manual_seed(seed)
            if torch.cuda.is_available():
                torch.backends.cudnn.deterministic = True
                torch.backends.cudnn.benchmark = False
        except ImportError:
            print("DEBUG: PyTorch not found, skipping torch-related seed settings.")
            pass
        np.random.seed(seed)
        random.seed(seed)

    def log_model_outputs_for_debug(image_path):
        """
        รัน Inference และคืนค่าผลลัพธ์เป็น Dictionary
        หมายเหตุ: ฟังก์ชันนี้จะเรียกใช้โมเดล WMDP โดยตรง
        """
        print(f"DEBUG: Running inference on: {image_path}")
        if not os.path.exists(image_path):
            return {"error": f"Image not found at {image_path}"}
        
        image_cv2 = cv2.imread(image_path)
        if image_cv2 is None:
            return {"error": f"Could not read image at {image_path}"}
        
        result_dict = read_water_meter(image_cv2, update_status=lambda msg: print(f"[Debug WMDP] {msg}"))
        return result_dict

    # --- Main Logic ของ Endpoint ---
    try:
        # --- ตั้งค่า Configuration ---
        ORIGINAL_IMAGE_PATH = "test_images/orig_001.jpg"
        RECEIVED_IMAGE_PATH = "received_from_line/line_msg_id_123.jpg"

        print("--- DEBUG: Setting up environment for deterministic results ---")
        set_deterministic_seed()
        
        results_orig = log_model_outputs_for_debug(ORIGINAL_IMAGE_PATH)
        results_rec = log_model_outputs_for_debug(RECEIVED_IMAGE_PATH)

        return jsonify({
            "status": "Debug successful",
            "environment": "Google Cloud Run",
            "results_from_original_image": results_orig,
            "results_from_received_image": results_rec
        })

    except Exception as e:
        print(f"AN EXCEPTION OCCURRED in Debug Endpoint:\n{traceback.format_exc()}")
        return jsonify({"status": "error", "message": str(e)}), 500

# --- Run Application ---
if __name__ == "__main__":
    app.run(port=5000, debug=True)