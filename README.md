# 📊 YouTube Data Analyzer Bot

<div align="center">
  <img src="https://img.shields.io/badge/Python-3.11-blue?style=for-the-badge&logo=python" alt="Python">
  <img src="https://img.shields.io/badge/Telegram-Bot-26A5E4?style=for-the-badge&logo=telegram" alt="Telegram Bot">
  <img src="https://img.shields.io/badge/YouTube-API-FF0000?style=for-the-badge&logo=youtube" alt="YouTube API">
  <img src="https://img.shields.io/badge/Render-Deployed-46E3B7?style=for-the-badge&logo=render" alt="Deployed on Render">
  <img src="https://img.shields.io/badge/Version-2.0-success?style=for-the-badge" alt="Version 2.0">
</div>

<p align="center">
  <b>🤖 بوت تلجرام لتحليل فيديوهات وقنوات يوتيوب بشكل متقدم</b>
</p>

<p align="center">
  <b>📌 البوت المباشر:</b> <a href="https://t.me/YouTube_data_analyzer_bot">@YouTube_data_analyzer_bot</a>
</p>

---

## ✨ **المميزات**

### 📹 **تحليل الفيديوهات:**
- ✅ عنوان الفيديو وتاريخ النشر
- ✅ عدد المشاهدات والإعجابات والتعليقات
- ✅ مدة الفيديو والدقة
- ✅ معلومات القناة (المشتركين، عدد الفيديوهات)
- ✅ أفضل التعليقات
- ✅ وصف الفيديو كامل

### 📺 **تحليل القنوات:**
- ✅ اسم القناة وتاريخ الإنشاء
- ✅ عدد المشتركين (حتى لو كان مخفياً)
- ✅ إجمالي المشاهدات والفيديوهات
- ✅ أحدث 5 فيديوهات
- ✅ وصف القناة والبلد

### 🚀 **مميزات البوت:**
- ✅ دعم كامل للغة العربية
- ✅ إرسال ملف نصي بالتحليل الكامل
- ✅ معالجة سريعة باستخدام YouTube API
- ✅ Health Check لإبقاء البوت نشطاً

---

## 📋 **الأوامر المتاحة**

| الأمر | الوصف |
|-------|-------|
| `/start` | بدء استخدام البوت وعرض التعليمات |
| `/help` | عرض المساعدة |
| `/about` | معلومات عن البوت |

---

## 🚀 **طريقة الاستخدام**

### **لتحليل فيديو:**
أرسل رابط الفيديو مباشرة:
https://youtu.be/dQw4w9WgXcQ
https://www.youtube.com/watch?v=dQw4w9WgXcQ

### **لتحليل قناة:**
أرسل @اسم_القناة أو رابط القناة:
@YouTube
https://youtube.com/@YouTube
https://www.youtube.com/channel/UCBR8-60-B28hp2BmDPdntcQ

---

## 📦 **ملف المتطلبات (`requirements.txt`)**

```txt
google-api-python-client==2.190.0
python-telegram-bot==22.6
python-dotenv==1.2.1
httpx==0.28.1
flask==3.0.0
tqdm==4.66.2
colorama==0.4.6
