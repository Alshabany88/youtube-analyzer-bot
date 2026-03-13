# -*- coding: utf-8 -*-
"""
YouTube Data Analyzer Bot - Telegram Version
Analyzes YouTube videos and channels with comprehensive statistics
"""

import os
import re
import json
import logging
import asyncio
from datetime import datetime
from urllib.parse import urlparse, parse_qs

import googleapiclient.discovery
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# ========== إعدادات Flask للـ Health Check ==========
from flask import Flask
import threading

app = Flask(__name__)

@app.route('/')
@app.route('/health')
@app.route('/healthcheck')
def health():
    return "OK", 200

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

threading.Thread(target=run_flask, daemon=True).start()
# ==================================================

# ========== متغيرات البيئة ==========
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
YOUTUBE_API_KEY = os.environ.get('YOUTUBE_API_KEY')

if not TELEGRAM_TOKEN or not YOUTUBE_API_KEY:
    print("❌ خطأ: تأكد من تعيين متغيرات البيئة")
    exit(1)
# ==================================

# إعدادات logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# مجلد مؤقت للملفات
TEMP_FOLDER = '/tmp/youtube_analyzer'
os.makedirs(TEMP_FOLDER, exist_ok=True)

# تهيئة YouTube API
youtube = googleapiclient.discovery.build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)

# ==================== دوال المساعدة ====================

def format_number(num):
    """تنسيق الأرقام الكبيرة"""
    if num is None or num == 'N/A':
        return "N/A"
    try:
        num = int(num)
        if num >= 1_000_000_000:
            return f"{num/1_000_000_000:.1f}B"
        elif num >= 1_000_000:
            return f"{num/1_000_000:.1f}M"
        elif num >= 1_000:
            return f"{num/1_000:.1f}K"
        else:
            return str(num)
    except:
        return str(num)

def format_duration(duration_iso):
    """تحويل مدة الفيديو من ISO 8601"""
    if not duration_iso:
        return "N/A"
    
    duration = duration_iso[2:]  # Remove 'PT'
    hours = minutes = seconds = 0
    
    if 'H' in duration:
        h_part = duration.split('H')[0]
        hours = int(h_part)
        duration = duration.split('H')[1]
    
    if 'M' in duration:
        m_part = duration.split('M')[0]
        minutes = int(m_part)
        duration = duration.split('M')[1]
    
    if 'S' in duration:
        s_part = duration.split('S')[0]
        seconds = int(s_part)
    
    if hours > 0:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    else:
        return f"{minutes}:{seconds:02d}"

def extract_video_id(url):
    """استخراج معرف الفيديو من الرابط"""
    parsed = urlparse(url)
    
    if parsed.netloc in ['www.youtube.com', 'youtube.com', 'm.youtube.com']:
        if parsed.path == '/watch':
            return parse_qs(parsed.query).get('v', [None])[0]
        elif parsed.path.startswith('/embed/') or parsed.path.startswith('/v/'):
            return parsed.path.split('/')[-1]
    elif parsed.netloc == 'youtu.be':
        return parsed.path[1:] if parsed.path.startswith('/') else parsed.path
    
    return None

def extract_channel_input(text):
    """استخراج اسم القناة من النص"""
    text = text.strip()
    
    # إذا كان رابط قناة
    if 'youtube.com' in text:
        return text
    
    # إذا كان @username
    if text.startswith('@'):
        return text
    
    # إذا كان مجرد اسم
    return text

def clean_markdown(text):
    """تنظيف النص من علامات Markdown"""
    if not text:
        return text
    chars_to_escape = ['_', '*', '`', '[']
    for char in chars_to_escape:
        text = text.replace(char, '\\' + char)
    return text

# ==================== دوال تحليل يوتيوب ====================

async def get_video_details(video_id):
    """تحليل فيديو يوتيوب"""
    try:
        # جلب تفاصيل الفيديو
        video_response = youtube.videos().list(
            part='snippet,statistics,contentDetails',
            id=video_id
        ).execute()
        
        if not video_response['items']:
            return None, "لم يتم العثور على الفيديو"
        
        video_data = video_response['items'][0]
        snippet = video_data['snippet']
        statistics = video_data.get('statistics', {})
        content_details = video_data.get('contentDetails', {})
        
        # جلب تفاصيل القناة
        channel_id = snippet['channelId']
        channel_response = youtube.channels().list(
            part='snippet,statistics',
            id=channel_id
        ).execute()
        
        channel_data = channel_response['items'][0] if channel_response['items'] else {}
        channel_stats = channel_data.get('statistics', {})
        
        # جلب أفضل التعليقات
        comments = []
        try:
            comment_response = youtube.commentThreads().list(
                part='snippet',
                videoId=video_id,
                maxResults=5,
                order='relevance'
            ).execute()
            
            for item in comment_response.get('items', []):
                comment_snippet = item['snippet']['topLevelComment']['snippet']
                comments.append({
                    'author': comment_snippet['authorDisplayName'],
                    'text': comment_snippet['textDisplay'][:150],
                    'likes': comment_snippet.get('likeCount', 0)
                })
        except:
            comments = []
        
        # تجميع البيانات
        video_details = {
            'title': snippet['title'],
            'description': snippet.get('description', 'لا يوجد وصف')[:300] + ('...' if len(snippet.get('description', '')) > 300 else ''),
            'published_at': snippet['publishedAt'][:10],
            'channel_name': snippet['channelTitle'],
            'channel_subs': format_number(channel_stats.get('subscriberCount', 0)),
            'duration': format_duration(content_details.get('duration', '')),
            'views': format_number(statistics.get('viewCount', 0)),
            'likes': format_number(statistics.get('likeCount', 0)),
            'comments_count': format_number(statistics.get('commentCount', 0)),
            'url': f"https://www.youtube.com/watch?v={video_id}",
            'comments': comments[:3]
        }
        
        return video_details, None
        
    except Exception as e:
        return None, str(e)

async def get_channel_details(channel_input):
    """تحليل قناة يوتيوب"""
    try:
        channel_id = None
        channel_username = None
        
        # تحديد نوع المدخلات
        if 'youtube.com' in channel_input:
            # استخراج من رابط
            parsed = urlparse(channel_input)
            path = parsed.path
            if '/@' in path:
                channel_username = path.split('/@')[-1]
            elif '/channel/' in path:
                channel_id = path.split('/channel/')[-1]
        elif channel_input.startswith('@'):
            channel_username = channel_input[1:]
        else:
            channel_username = channel_input
        
        # البحث عن القناة إذا كان لدينا اسم مستخدم
        if channel_username:
            # استخدام maxResults=1 فقط لتجنب التأخير
            search_response = youtube.search().list(
                part='snippet',
                q=channel_username,
                type='channel',
                maxResults=1
            ).execute()
            
            if not search_response['items']:
                return None, "لم يتم العثور على القناة"
            
            channel_id = search_response['items'][0]['snippet']['channelId']
        
        # جلب تفاصيل القناة
        channel_response = youtube.channels().list(
            part='snippet,statistics,contentDetails,status',
            id=channel_id
        ).execute()
        
        if not channel_response['items']:
            return None, "لم يتم العثور على القناة"
        
        channel_data = channel_response['items'][0]
        snippet = channel_data['snippet']
        statistics = channel_data.get('statistics', {})
        content_details = channel_data.get('contentDetails', {})
        status = channel_data.get('status', {})
        
        # جلب أحدث الفيديوهات
        uploads_playlist_id = content_details.get('relatedPlaylists', {}).get('uploads')
        latest_videos = []
        
        if uploads_playlist_id:
            try:
                playlist_response = youtube.playlistItems().list(
                    part='snippet',
                    playlistId=uploads_playlist_id,
                    maxResults=5
                ).execute()
                
                for item in playlist_response.get('items', []):
                    video_snippet = item['snippet']
                    latest_videos.append({
                        'title': video_snippet['title'][:50],
                        'video_id': video_snippet['resourceId']['videoId'],
                        'published_at': video_snippet['publishedAt'][:10]
                    })
            except:
                latest_videos = []
        
        # حساب المتوسطات
        total_views = int(statistics.get('viewCount', 0))
        total_videos = int(statistics.get('videoCount', 1))
        avg_views_per_video = total_views / total_videos if total_videos > 0 else 0
        
        # تجميع البيانات
        channel_details = {
            'title': snippet['title'],
            'description': snippet.get('description', 'لا يوجد وصف')[:200] + ('...' if len(snippet.get('description', '')) > 200 else ''),
            'custom_url': snippet.get('customUrl', 'N/A'),
            'published_at': snippet['publishedAt'][:10],
            'country': snippet.get('country', 'غير محدد'),
            'subscribers': format_number(statistics.get('subscriberCount', 0)),
            'total_views': format_number(statistics.get('viewCount', 0)),
            'total_videos': format_number(statistics.get('videoCount', 0)),
            'hidden_subscribers': statistics.get('hiddenSubscriberCount', False),
            'privacy_status': status.get('privacyStatus', 'غير معروف'),
            'avg_views_per_video': format_number(avg_views_per_video),
            'latest_videos': latest_videos,
            'url': f"https://www.youtube.com/channel/{channel_id}",
            'channel_id': channel_id
        }
        
        return channel_details, None
        
    except Exception as e:
        return None, str(e)

# ==================== دوال إنشاء الملفات ====================

def create_video_file(video_details):
    """إنشاء ملف نصي بتفاصيل الفيديو"""
    filename = f"video_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    filepath = os.path.join(TEMP_FOLDER, filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write("="*80 + "\n")
        f.write("🎬 YouTube Video Analysis Report\n")
        f.write("="*80 + "\n\n")
        
        f.write(f"📹 Title: {video_details['title']}\n")
        f.write(f"🔗 URL: {video_details['url']}\n")
        f.write(f"📅 Published: {video_details['published_at']}\n")
        f.write(f"⏱️ Duration: {video_details['duration']}\n\n")
        
        f.write("📊 Statistics:\n")
        f.write("-"*40 + "\n")
        f.write(f"👁️ Views: {video_details['views']}\n")
        f.write(f"❤️ Likes: {video_details['likes']}\n")
        f.write(f"💬 Comments: {video_details['comments_count']}\n\n")
        
        f.write("📺 Channel Info:\n")
        f.write("-"*40 + "\n")
        f.write(f"Name: {video_details['channel_name']}\n")
        f.write(f"Subscribers: {video_details['channel_subs']}\n\n")
        
        f.write("📝 Description:\n")
        f.write("-"*40 + "\n")
        f.write(f"{video_details['description']}\n\n")
        
        if video_details['comments']:
            f.write("💬 Top Comments:\n")
            f.write("-"*40 + "\n")
            for i, c in enumerate(video_details['comments'], 1):
                f.write(f"{i}. {c['author']} (❤️ {c['likes']}): {c['text']}\n")
    
    return filepath

def create_channel_file(channel_details):
    """إنشاء ملف نصي بتفاصيل القناة"""
    filename = f"channel_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    filepath = os.path.join(TEMP_FOLDER, filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write("="*80 + "\n")
        f.write("📺 YouTube Channel Analysis Report\n")
        f.write("="*80 + "\n\n")
        
        f.write("📺 Channel Information\n")
        f.write("-"*40 + "\n")
        f.write(f"Name: {channel_details['title']}\n")
        f.write(f"URL: {channel_details['url']}\n")
        f.write(f"Channel ID: {channel_details['channel_id']}\n")
        f.write(f"Custom URL: @{channel_details['custom_url']}\n")
        f.write(f"Created: {channel_details['published_at']}\n")
        f.write(f"Country: {channel_details['country']}\n")
        f.write(f"Privacy Status: {channel_details['privacy_status']}\n\n")
        
        f.write("📊 Statistics:\n")
        f.write("-"*40 + "\n")
        if channel_details['hidden_subscribers']:
            f.write("Subscribers: 🔒 Hidden\n")
        else:
            f.write(f"Subscribers: {channel_details['subscribers']}\n")
        f.write(f"Total Videos: {channel_details['total_videos']}\n")
        f.write(f"Total Views: {channel_details['total_views']}\n")
        f.write(f"Avg Views/Video: {channel_details['avg_views_per_video']}\n\n")
        
        f.write("📝 Description:\n")
        f.write("-"*40 + "\n")
        f.write(f"{channel_details['description']}\n\n")
        
        if channel_details['latest_videos']:
            f.write("🆕 Latest Videos:\n")
            f.write("-"*40 + "\n")
            for i, v in enumerate(channel_details['latest_videos'], 1):
                f.write(f"{i}. {v['title']}\n")
                f.write(f"   https://www.youtube.com/watch?v={v['video_id']}\n")
                f.write(f"   📅 {v['published_at']}\n\n")
    
    return filepath

# ==================== أوامر البوت ====================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """رسالة الترحيب"""
    welcome_text = """
📊 **مرحباً بك في بوت تحليل يوتيوب المتقدم!**

🔍 **ماذا يمكنني أن أفعل؟**
• تحليل **أي فيديو يوتيوب** وإحصائياته الكاملة
• تحليل **أي قناة يوتيوب** ومعلوماتها الشاملة

📥 **كيف تستخدمني؟**
• لتحليل فيديو: أرسل رابط الفيديو
• لتحليل قناة: أرسل @اسم_القناة أو رابط القناة

✨ **المميزات:**
✅ تحليل دقيق باستخدام YouTube API الرسمي
✅ عرض الإحصائيات بشكل مرتب
✅ إرسال ملف نصي بالتحليل الكامل
✅ دعم اللغة العربية بالكامل

📌 **أمثلة:**
`@YouTube`
`https://youtube.com/@YouTube`

👨‍💻 **مطور:** @alshabany8
"""
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تعليمات المساعدة"""
    help_text = """
🆘 **مساعدة البوت**

🔹 **لتحليل فيديو:**
أرسل رابط الفيديو (YouTube, youtu.be)

🔹 **لتحليل قناة:**
• @Username
• رابط القناة

⚡ **ملاحظات:**
• القنوات الكبيرة قد تستغرق وقتاً أطول
• يتم إرسال ملف نصي بالتحليل الكامل
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معلومات عن البوت"""
    about_text = """
🔴 **بوت تحليل يوتيوب المتقدم** 🔴

📊 **الإصدار:** 2.1 (بوت تلجرام)

✨ **المميزات:**
• تحليل كامل للفيديوهات (مشاهدات، إعجابات، تعليقات)
• تحليل شامل للقنوات (مشتركين، فيديوهات، مشاهدات)
• عرض متوسط المشاهدات لكل فيديو
• تصدير النتائج لملف نصي منظم
• دعم كامل للغة العربية

👨‍💻 **المطور:** Ibrahim Alshabany
📧 **البريد:** central.app.ye@gmail.com
📱 **إنستغرام:** @ebrahim_alshabany

🚀 **تم النشر على Render مع Health Check - 2026**
"""
    await update.message.reply_text(about_text, parse_mode='Markdown')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة رسائل المستخدم"""
    text = update.message.text.strip()
    
    # إظهار أن البوت يكتب
    await context.bot.send_chat_action(update.effective_chat.id, action='typing')
    
    # التحقق مما إذا كان رابط فيديو
    video_id = extract_video_id(text)
    
    if video_id:
        # تحليل فيديو
        status_msg = await update.message.reply_text("⏳ جاري تحليل الفيديو...")
        
        video_details, error = await get_video_details(video_id)
        
        if error:
            await status_msg.edit_text(f"❌ حدث خطأ: {error}")
            return
        
        if not video_details:
            await status_msg.edit_text("❌ لم يتم العثور على الفيديو")
            return
        
        # إنشاء ملف التحليل
        filepath = create_video_file(video_details)
        
        # إرسال الملخص
        summary = f"""
✅ **تم تحليل الفيديو بنجاح!**

📹 **العنوان:** {clean_markdown(video_details['title'][:100])}
👤 **القناة:** {clean_markdown(video_details['channel_name'])}
📅 **النشر:** {video_details['published_at']}
⏱️ **المدة:** {video_details['duration']}

📊 **الإحصائيات:**
👁️ المشاهدات: {video_details['views']}
❤️ الإعجابات: {video_details['likes']}
💬 التعليقات: {video_details['comments_count']}
📺 مشتركي القناة: {video_details['channel_subs']}

📝 **الوصف:** {video_details['description']}
"""
        
        await status_msg.edit_text(summary, parse_mode='Markdown')
        
        # إرسال الملف
        with open(filepath, 'rb') as f:
            await update.message.reply_document(
                document=f,
                filename=os.path.basename(filepath),
                caption="📊 ملف التحليل الكامل"
            )
        
        # حذف الملف المؤقت
        os.remove(filepath)
        
    else:
        # تحليل قناة
        channel_input = extract_channel_input(text)
        status_msg = await update.message.reply_text("⏳ جاري تحليل القناة...")
        
        channel_details, error = await get_channel_details(channel_input)
        
        if error:
            await status_msg.edit_text(f"❌ حدث خطأ: {error}")
            return
        
        if not channel_details:
            await status_msg.edit_text("❌ لم يتم العثور على القناة")
            return
        
        # إنشاء ملف التحليل
        filepath = create_channel_file(channel_details)
        
        # إرسال الملخص
        subs_text = "🔒 مخفي" if channel_details['hidden_subscribers'] else channel_details['subscribers']
        
        summary = f"""
✅ **تم تحليل القناة بنجاح!**

📺 **القناة:** {clean_markdown(channel_details['title'])}
🆔 **اليوزر:** @{channel_details['custom_url']}
📅 **الإنشاء:** {channel_details['published_at']}
🌍 **البلد:** {channel_details['country']}

📊 **الإحصائيات:**
👥 المشتركين: {subs_text}
📹 عدد الفيديوهات: {channel_details['total_videos']}
👁️ إجمالي المشاهدات: {channel_details['total_views']}
📊 متوسط المشاهدات/فيديو: {channel_details['avg_views_per_video']}

📝 **الوصف:** {channel_details['description']}

🆕 **أحدث الفيديوهات:**
"""
        
        for i, v in enumerate(channel_details['latest_videos'][:3], 1):
            short_title = v['title'][:50] + '...' if len(v['title']) > 50 else v['title']
            summary += f"{i}. [{clean_markdown(short_title)}](https://www.youtube.com/watch?v={v['video_id']})\n"
        
        await status_msg.edit_text(summary, parse_mode='Markdown')
        
        # إرسال الملف
        with open(filepath, 'rb') as f:
            await update.message.reply_document(
                document=f,
                filename=os.path.basename(filepath),
                caption="📊 ملف التحليل الكامل"
            )
        
        # حذف الملف المؤقت
        os.remove(filepath)

# ==================== الدالة الرئيسية ====================

def main():
    """تشغيل البوت"""
    
    # إنشاء التطبيق
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # إضافة المعالجات
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("about", about_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # تشغيل البوت
    print("="*60)
    print("📊 YouTube Data Analyzer Bot")
    print("🤖 @YouTube_data_analyzer_bot")
    print("✅ تم إضافة أوامر /start /help /about")
    print("✅ تم إضافة متوسط المشاهدات لكل فيديو")
    print("✅ تم إضافة معرف القناة في الملف النصي")
    print("✅ تم تبسيط البحث لتجنب التأخير")
    print("="*60)
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
