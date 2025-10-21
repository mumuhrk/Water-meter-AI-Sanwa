# AI Water SANWA (LINE Bot อ่านมาตรวัดน้ำ)

## 📖 ภาพรวมโปรเจกต์

[cite_start]โปรเจกต์นี้คือ **LINE Chatbot ชื่อ "AI Water SANWA"** ที่สร้างขึ้นเพื่ออ่านค่าตัวเลขจากมาตรวัดน้ำผ่านรูปภาพ [cite: 757, 765, 778] [cite_start]ผู้ใช้สามารถถ่ายรูปมาตรวัดน้ำและส่งเข้าไปในแชทบอท [cite: 765] [cite_start]จากนั้นระบบ AI จะประมวลผลรูปภาพและส่งค่าตัวเลขที่อ่านได้กลับมาให้ผู้ใช้ [cite: 766, 767, 824]

ตัวระบบประกอบด้วย:
1.  [cite_start]**LINE Messaging API** สำหรับเป็น Chatbot Interface [cite: 3, 59]
2.  [cite_start]**โมเดล AI (Machine Learning)** สำหรับการตรวจจับและอ่านค่าตัวเลขจากภาพ (เช่น YOLO, ViT) [cite: 171, 180, 199, 200, 201]
3.  [cite_start]**Backend API (Flask)** ที่เขียนด้วย Python เพื่อจัดการ Webhook จาก LINE และเรียกใช้โมเดล AI [cite: 221, 287]
4.  [cite_start]**ระบบ Deployment** โดยใช้ Docker เพื่อสร้าง Container และนำไปรันบน Google Cloud Run [cite: 324, 325, 540]

---

## 🛠️ เทคโนโลยีที่ใช้

* [cite_start]**Backend:** Python [cite: 85][cite_start], Flask [cite: 221]
* [cite_start]**AI/ML:** PyTorch [cite: 201, 203][cite_start], YOLO [cite: 199, 200][cite_start], Vision Transformer (ViT) [cite: 180, 181]
* [cite_start]**Bot Framework:** LINE Messaging API [cite: 3, 59]
* [cite_start]**Deployment:** Docker [cite: 325][cite_start], Docker Hub [cite: 475, 530][cite_start], Google Cloud Run [cite: 540, 605]

---

## 🚀 ขั้นตอนการติดตั้งและใช้งาน (สรุป)

นี่คือขั้นตอนหลักในการติดตั้งโปรเจกต์ตามคู่มือ:

### 1. ตั้งค่า LINE Bot
1.  [cite_start]ไปที่ **LINE Developers** (`developers.line.biz`) และสร้าง Provider และ **Messaging API channel** [cite: 1, 2, 3]
2.  [cite_start]ในแท็บ "Basic settings" จะได้ `Channel ID` [cite: 35]
3.  [cite_start]ในแท็บ "Messaging API" ให้เลื่อนหา `Channel secret` และ `Channel access token (long-lived)` **ให้บันทึกค่าเหล่านี้ไว้** [cite: 40, 59, 60]

### 2. ตั้งค่าสภาพแวดล้อม (Local Environment)
1.  [cite_start]ติดตั้ง **Visual Studio Code** และ **Python** [cite: 85] [cite_start](อย่าลืมติ๊ก "Add python.exe to PATH" ตอนติดตั้ง [cite: 135])
2.  [cite_start]ติดตั้ง **Extension "Python"** บน VS Code [cite: 138]
3.  [cite_start]สร้าง **Virtual Environment** (`venv`) [cite: 146] [cite_start]และ Activate [cite: 154]
4.  [cite_start]ติดตั้งไลบรารีที่จำเป็นทั้งหมดด้วยคำสั่ง: `pip install -r requirements.txt` [cite: 148, 155]

### 3. ตั้งค่าโปรเจกต์ (Code)
1.  [cite_start]ดาวน์โหลดไฟล์โมเดล AI ทั้ง 3 ไฟล์ (`digits.pt`, `model-1-semi.pt`, `TB.pt`) [cite: 158, 199, 200, 201]
2.  [cite_start]เปิดไฟล์ **`WMDP.py`** และแก้ไข Path ที่ใช้โหลดโมเดลทั้ง 3 ให้ตรงกับตำแหน่งไฟล์ในเครื่องของคุณ [cite: 160, 199, 200, 201]
3.  [cite_start]เปิดไฟล์ **`app.py`** [cite: 221] [cite_start]และนำ `Channel secret` กับ `Channel access token` ที่ได้จากข้อ 1 มาใส่ในบรรทัด `configuration = Configuration(...)` และ `handler = WebhookHandler(...)` [cite: 289, 290, 291, 292]

### 4. สร้างและ Push Docker Image
1.  [cite_start]ติดตั้ง **Docker Desktop** [cite: 325, 326] [cite_start](และตรวจสอบว่า Virtualization เป็น "Enabled" ใน Task Manager [cite: 366, 405])
2.  [cite_start]สร้าง **Repository บน Docker Hub** (ตั้งค่าเป็น Public) [cite: 475, 484, 496]
3.  [cite_start]Build Docker image ด้วยคำสั่ง (เปลี่ยน `t43xd/water-meter-api` เป็นชื่อ repository ของคุณ)[cite: 521, 522]:
    ```bash
    docker build -t t43xd/water-meter-api:latest .
    ```
4.  [cite_start]Push image ขึ้น Docker Hub ด้วยคำสั่ง[cite: 530, 531]:
    ```bash
    docker push t43xd/water-meter-api:latest
    ```

### 5. Deploy บน Google Cloud Run
1.  [cite_start]ไปที่ **Google Cloud Console** และไปที่ **Cloud Run** -> **Services** [cite: 541, 605]
2.  [cite_start]**Create Service** และเลือก "Deploy one revision from an existing container image" [cite: 617, 627]
3.  [cite_start]ใส่ **Container image URL** ที่ได้จาก Docker Hub (เช่น `docker.io/t43xd/water-meter-api:v3.1`) [cite: 652, 655]
4.  [cite_start]ตั้งค่า **Authentication** เป็น **"Allow public access"** [cite: 642, 664]
5.  [cite_start]ตั้งค่า Resources (CPU, Memory) [cite: 689, 707] [cite_start]แล้วกด **Create** [cite: 709]
6.  [cite_start]เมื่อ Deploy เสร็จ ให้ **คัดลอก URL** ของ Service ที่ได้ [cite: 736, 740, 744]

### 6. เชื่อมต่อ Webhook
1.  [cite_start]กลับไปที่ **LINE Developers** -> **Messaging API** [cite: 59]
2.  [cite_start]ไปที่ **Webhook settings** กด **Edit** [cite: 74, 750]
3.  [cite_start]นำ URL ที่คัดลอกจาก Cloud Run มาวาง และ**ต่อท้ายด้วย `/webhook`** (เช่น `https://...run.app/webhook`) [cite: 74, 750]
4.  [cite_start]กด **Verify** [cite: 78, 750]
5.  [cite_start]เพิ่มเพื่อน LINE ID ของ Bot (เช่น `@743iwcqc`) และทดลองส่งรูปมาตรวัดน้ำ [cite: 751]

---

## 👥 ผู้จัดทำ
* [cite_start]Mr. Natchasit Chukiatkhajorn [cite: 774, 790, 791]
* [cite_start]Mr. Sujinda Jaipinta [cite: 769, 782]
* [cite_start]Mr. Thanakrit Neangla [cite: 770, 783]
* [cite_start]Mr. Borwornwich Pimason [cite: 771, 784]
* [cite_start]Mr. Siwakorn Muangmala [cite: 772, 785]
* [cite_start]Mr. Kwanchai Eurviriyanukul [cite: 774, 790, 791]
