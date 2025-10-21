# AI Water SANWA (LINE Bot อ่านมาตรวัดน้ำ)

## 📖 ภาพรวมโปรเจกต์

โปรเจกต์นี้คือ **LINE Chatbot ชื่อ "AI Water SANWA"** ที่สร้างขึ้นเพื่ออ่านค่าตัวเลขจากมาตรวัดน้ำผ่านรูปภาพ ผู้ใช้สามารถถ่ายรูปมาตรวัดน้ำและส่งเข้าไปในแชทบอท จากนั้นระบบ AI จะประมวลผลรูปภาพและส่งค่าตัวเลขที่อ่านได้กลับมาให้ผู้ใช้

ตัวระบบประกอบด้วย:
1.  **LINE Messaging API** สำหรับเป็น Chatbot Interface
2.  **โมเดล AI (Machine Learning)** สำหรับการตรวจจับและอ่านค่าตัวเลขจากภาพ (เช่น YOLO, ViT)
3.  **Backend API (Flask)** ที่เขียนด้วย Python เพื่อจัดการ Webhook จาก LINE และเรียกใช้โมเดล AI
4.  **ระบบ Deployment** โดยใช้ Docker เพื่อสร้าง Container และนำไปรันบน Google Cloud Run

---

## 🛠️ เทคโนโลยีที่ใช้

* **Backend:** Python, Flask
* **AI/ML:** PyTorch, YOLO, Vision Transformer (ViT)
* **Bot Framework:** LINE Messaging API
* **Deployment:** Docker, Docker Hub, Google Cloud Run

---

## 🚀 ขั้นตอนการติดตั้งและใช้งาน 

นี่คือขั้นตอนหลักในการติดตั้งโปรเจกต์ตามคู่มือ:

### 1. ตั้งค่า LINE Bot
1.  ไปที่ **LINE Developers** (`developers.line.biz`) และสร้าง Provider และ **Messaging API channel**
2.  ในแท็บ "Basic settings" จะได้ `Channel ID`
3.  ในแท็บ "Messaging API" ให้เลื่อนหา `Channel secret` และ `Channel access token (long-lived)` **ให้บันทึกค่าเหล่านี้ไว้**

### 2. ตั้งค่าสภาพแวดล้อม (Local Environment)
1.  ติดตั้ง **Visual Studio Code** และ **Python** (อย่าลืมติ๊ก "Add python.exe to PATH" ตอนติดตั้ง)
2.  ติดตั้ง **Extension "Python"** บน VS Code
3.  สร้าง **Virtual Environment** (`venv`) และ Activate
4.  ติดตั้งไลบรารีที่จำเป็นทั้งหมดด้วยคำสั่ง: `pip install -r requirements.txt`

### 3. ตั้งค่าโปรเจกต์ (Code)
1.  ดาวน์โหลดไฟล์โมเดล AI ทั้ง 3 ไฟล์ (`digits.pt`, `model-1-semi.pt`, `TB.pt`)
2.  เปิดไฟล์ **`WMDP.py`** และแก้ไข Path ที่ใช้โหลดโมเดลทั้ง 3 ให้ตรงกับตำแหน่งไฟล์ในเครื่องของคุณ
3.  เปิดไฟล์ **`app.py`** และนำ `Channel secret` กับ `Channel access token` ที่ได้จากข้อ 1 มาใส่ในบรรทัด `configuration = Configuration(...)` และ `handler = WebhookHandler(...)`

### 4. สร้างและ Push Docker Image
1.  ติดตั้ง **Docker Desktop** (และตรวจสอบว่า Virtualization เป็น "Enabled" ใน Task Manager)
2.  สร้าง **Repository บน Docker Hub** (ตั้งค่าเป็น Public)
3.  Build Docker image ด้วยคำสั่ง (เปลี่ยน `t43xd/water-meter-api` เป็นชื่อ repository ของคุณ):
    ```bash
    docker build -t t43xd/water-meter-api:latest .
    ```
4.  Push image ขึ้น Docker Hub ด้วยคำสั่ง:
    ```bash
    docker push t43xd/water-meter-api:latest
    ```

### 5. Deploy บน Google Cloud Run
1.  ไปที่ **Google Cloud Console** และไปที่ **Cloud Run** -> **Services**
2.  **Create Service** และเลือก "Deploy one revision from an existing container image"
3.  ใส่ **Container image URL** ที่ได้จาก Docker Hub (เช่น `docker.io/t43xd/water-meter-api:v3.1`)
4.  ตั้งค่า **Authentication** เป็น **"Allow public access"**
5.  ตั้งค่า Resources (CPU, Memory) แล้วกด **Create**
6.  เมื่อ Deploy เสร็จ ให้ **คัดลอก URL** ของ Service ที่ได้

### 6. เชื่อมต่อ Webhook
1.  กลับไปที่ **LINE Developers** -> **Messaging API**
2.  ไปที่ **Webhook settings** กด **Edit**
3.  นำ URL ที่คัดลอกจาก Cloud Run มาวาง และ**ต่อท้ายด้วย `/webhook`** (เช่น `https://...run.app/webhook`)
4.  กด **Verify**
5.  เพิ่มเพื่อน LINE ID ของ Bot (เช่น `@743iwcqc`) และทดลองส่งรูปมาตรวัดน้ำ

---

## 👥 ผู้จัดทำ
* Mr. Natchasit Chukiatkhajorn 
* Mr. Sujinda Jaipinta 
* Mr. Thanakrit Neangla 
* Mr. Borwornwich Pimason 
* Mr. Siwakorn Muangmala 
* Mr. Kwanchai Eurviriyanukul 
