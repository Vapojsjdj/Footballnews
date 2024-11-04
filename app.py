from flask import Flask, render_template_string, request
import requests
import re
import json
import os
import time

app = Flask(__name__)

# تأكد من وجود ملف للتخزين
STORAGE_FILE = 'articles_storage.json'

def load_saved_articles():
    if os.path.exists(STORAGE_FILE):
        with open(STORAGE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_articles(articles):
    with open(STORAGE_FILE, 'w', encoding='utf-8') as f:
        json.dump(articles, f, ensure_ascii=False, indent=4)

# [باقي الدوال الموجودة تبقى كما هي: extract_images, get_links, get_article_content]

main_template = """
<!DOCTYPE html>
<html dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>استخراج المقالات</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f0f0f0;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
        }
        .url-input {
            width: 100%;
            padding: 10px;
            margin: 10px 0;
            border: 1px solid #ddd;
            border-radius: 4px;
            direction: ltr;
        }
        button {
            background-color: #4CAF50;
            color: white;
            padding: 10px 20px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            margin-right: 10px;
        }
        .clear-button {
            background-color: #f44336;
        }
        .article {
            margin: 20px 0;
            padding: 15px;
            background: #f9f9f9;
            border-radius: 8px;
        }
        .images-section {
            margin: 15px 0;
            padding: 10px;
            background: #f5f5f5;
            border-radius: 4px;
        }
        .related-articles {
            margin: 15px 0;
            padding: 10px;
            background: #f5f5f5;
            border-radius: 4px;
        }
        .article-content {
            white-space: pre-line;
            line-height: 1.6;
        }
        #status {
            margin: 10px 0;
            color: #666;
        }
        .loading {
            display: none;
            margin: 10px 0;
        }
    </style>
</head>
<body>
    <div class="container">
        <h2>استخراج المقالات</h2>
        <input type="text" id="urlInput" class="url-input" placeholder="أدخل رابط الصفحة هنا...">
        <button onclick="processURL()">استخراج المقالات</button>
        <button onclick="clearArticles()" class="clear-button">مسح جميع المقالات</button>
        <div id="status"></div>
        <div id="loading" class="loading">جاري التحميل...</div>
        <div id="savedArticles">{{ saved_articles_html|safe }}</div>
        <div id="result"></div>
    </div>

    <script>
        function processURL() {
            const url = document.getElementById('urlInput').value.trim();
            if (!url) {
                alert('الرجاء إدخال رابط صحيح');
                return;
            }

            document.getElementById('loading').style.display = 'block';
            document.getElementById('result').innerHTML = '';
            document.getElementById('status').innerHTML = '';

            fetch('/process', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: 'url=' + encodeURIComponent(url)
            })
            .then(response => response.json())
            .then(data => {
                document.getElementById('loading').style.display = 'none';
                if (data.error) {
                    document.getElementById('status').innerHTML = 'حدث خطأ: ' + data.error;
                    return;
                }
                // تحديث الصفحة لعرض المقالات المحفوظة
                window.location.reload();
            })
            .catch(error => {
                document.getElementById('loading').style.display = 'none';
                document.getElementById('status').innerHTML = 'حدث خطأ أثناء المعالجة';
            });
        }

        function clearArticles() {
            if (confirm('هل أنت متأكد من رغبتك في مسح جميع المقالات المحفوظة؟')) {
                fetch('/clear', {
                    method: 'POST'
                })
                .then(response => response.json())
                .then(data => {
                    window.location.reload();
                });
            }
        }
    </script>
</body>
</html>
"""

def generate_articles_html(articles):
    html = ""
    for article in articles:
        html += f"""
            <div class="article">
                <h3>{article['title']}</h3>
        """
        
        if article.get('images'):
            html += """
                <div class="images-section">
                    <h4>الصور:</h4>
            """
            for img in article['images']:
                html += f"""
                    <div>
                        <p>الوصف: {img['caption']}</p>
                        <p>الرابط: {img['url']}</p>
                    </div>
                """
            html += "</div>"
        
        html += f"""
            <div class="article-content">{article['content']}</div>
        """
        
        if article.get('related_articles'):
            html += """
                <div class="related-articles">
                    <h4>المقالات ذات الصلة:</h4>
            """
            for related in article['related_articles']:
                html += f"""
                    <div>
                        <a href="{related['url']}" target="_blank">{related['title']}</a>
                    </div>
                """
            html += "</div>"
        
        html += "</div>"
    
    return html

@app.route('/')
def home():
    saved_articles = load_saved_articles()
    saved_articles_html = generate_articles_html(saved_articles)
    return render_template_string(main_template, saved_articles_html=saved_articles_html)

@app.route('/process', methods=['POST'])
def process():
    url = request.form.get('url')
    try:
        all_articles = []
        
        # استخراج الروابط أولاً
        links = get_links(url)
        if not links:
            links = [url]
        
        # استخراج المقالات من كل رابط
        for link in links:
            articles = get_article_content(link)
            if articles:
                all_articles.extend(articles)
        
        # حفظ المقالات الجديدة مع المقالات القديمة
        saved_articles = load_saved_articles()
        saved_articles.extend(all_articles)
        save_articles(saved_articles)
        
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}

@app.route('/clear', methods=['POST'])
def clear_articles():
    if os.path.exists(STORAGE_FILE):
        os.remove(STORAGE_FILE)
    return {"success": True}

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080, debug=True)
