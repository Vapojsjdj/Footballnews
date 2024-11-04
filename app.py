from flask import Flask, render_template_string, request, send_file
import requests
import re
import time
import os
from datetime import datetime 

app = Flask(__name__)

def extract_images(text):
    images = []
    image_start = text.find('var article_images = new Array (')
    if image_start != -1:
        image_end = text.find(');', image_start)
        if image_end != -1:
            image_text = text[image_start + len('var article_images = new Array ('):image_end]
            image_items = image_text.split(',')
            
            i = 0
            while i < len(image_items)-1:
                try:
                    image_url = image_items[i].strip(' "\n')
                    image_caption = image_items[i+1].strip(' "\n')
                    if image_url and not image_url.isdigit():
                        images.append({
                            'url': image_url,
                            'caption': image_caption
                        })
                    i += 2
                except:
                    i += 1
    return images

def get_links(url):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        response = requests.get(url, headers=headers)
        response.encoding = 'utf-8'
        content = response.text
        
        matches = re.findall(r'n=\d+', content)
        links = []
        if matches:
            links = [f'https://m.kooora.com/?n={match.replace("n=", "")}&pg=1&o=n' for match in matches]
            links = list(set(links))
        return links
    except Exception as e:
        return []

def get_article_content(url):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = 'utf-8'
        page_content = response.text
        
        articles = []
        parts = page_content.split('var article_title = "')
        
        for part in parts[1:]:
            try:
                article = {}
                title_end = part.find('";')
                if title_end != -1:
                    article['title'] = part[:title_end]
                
                content_start = part.find('var article_content = "')
                if content_start != -1:
                    content_start += len('var article_content = "')
                    content_end = part.find('";', content_start)
                    if content_end != -1:
                        content = part[content_start:content_end]
                        content = content.replace('\\n', '\n').replace('\\"', '"').strip()
                        article['content'] = content
                
                article['images'] = extract_images(part)
                
                related_start = part.find('var article_related = new Array (')
                if related_start != -1:
                    related_end = part.find(');', related_start)
                    if related_end != -1:
                        related_text = part[related_start + len('var article_related = new Array ('):related_end]
                        related_items = related_text.split(',')
                        
                        related_articles = []
                        i = 0
                        while i < len(related_items)-2:
                            try:
                                article_id = related_items[i].strip()
                                article_title = related_items[i+1].strip(' "')
                                article_url = related_items[i+2].strip(' "')
                                
                                if article_id and article_title:
                                    related_articles.append({
                                        'id': article_id,
                                        'title': article_title,
                                        'url': article_url
                                    })
                                i += 3
                            except:
                                i += 1
                        
                        article['related_articles'] = related_articles
                
                if article.get('title') and article.get('content'):
                    articles.append(article)
                    
            except Exception as e:
                continue
                
        return articles
        
    except Exception as e:
        return []

def generate_html_file(articles):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f'articles_{timestamp}.html'
    
    html_content = """
    <!DOCTYPE html>
    <html dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>المقالات المستخرجة</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                margin: 20px;
                background-color: #ffffff;
            }
            .article {
                margin: 20px 0;
                padding: 15px;
                border-bottom: 1px solid #eee;
            }
            .article-title {
                color: #1a0dab;
                font-size: 24px;
                margin-bottom: 10px;
            }
            .article-content {
                line-height: 1.6;
                margin: 15px 0;
            }
            .images-section {
                margin: 15px 0;
                padding: 10px;
                background: #f5f5f5;
            }
            .related-articles {
                margin: 15px 0;
                padding: 10px;
                background: #f5f5f5;
            }
        </style>
    </head>
    <body>
        <div class="container">
    """
    
    for article in articles:
        html_content += f"""
            <div class="article">
                <h2 class="article-title">{article['title']}</h2>
                <div class="article-content">{article['content']}</div>
        """
        
        if article.get('images'):
            html_content += """
                <div class="images-section">
                    <h3>الصور:</h3>
            """
            for img in article['images']:
                html_content += f"""
                    <div>
                        <p>الوصف: {img['caption']}</p>
                        <p>الرابط: {img['url']}</p>
                    </div>
                """
            html_content += "</div>"
        
        if article.get('related_articles'):
            html_content += """
                <div class="related-articles">
                    <h3>المقالات ذات الصلة:</h3>
            """
            for related in article['related_articles']:
                html_content += f"""
                    <p><a href="{related['url']}" target="_blank">{related['title']}</a></p>
                """
            html_content += "</div>"
        
        html_content += "</div>"
    
    html_content += """
        </div>
    </body>
    </html>
    """
    
    if not os.path.exists('downloads'):
        os.makedirs('downloads')
    
    file_path = os.path.join('downloads', filename)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    return file_path

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
        .button-group {
            margin: 10px 0;
        }
        button {
            background-color: #4CAF50;
            color: white;
            padding: 10px 20px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            margin-left: 10px;
        }
        .download-btn {
            background-color: #2196F3;
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
        <div class="button-group">
            <button onclick="processURL()">استخراج المقالات</button>
            <button class="download-btn" onclick="downloadHTML()" id="downloadBtn" disabled>تحميل HTML</button>
        </div>
        <div id="status"></div>
        <div id="loading" class="loading">جاري التحميل...</div>
        <div id="result"></div>
    </div>

    <script>
        let currentArticles = null;

        function processURL() {
            const url = document.getElementById('urlInput').value.trim();
            if (!url) {
                alert('الرجاء إدخال رابط صحيح');
                return;
            }

            document.getElementById('loading').style.display = 'block';
            document.getElementById('result').innerHTML = '';
            document.getElementById('status').innerHTML = '';
            document.getElementById('downloadBtn').disabled = true;

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

                currentArticles = data.articles;
                let resultHTML = '';
                if (data.articles && data.articles.length > 0) {
                    document.getElementById('downloadBtn').disabled = false;
                    
                    data.articles.forEach((article, index) => {
                        resultHTML += `
                            <div class="article">
                                <h3>${article.title}</h3>
                                
                                ${article.images && article.images.length > 0 ? `
                                    <div class="images-section">
                                        <h4>الصور:</h4>
                                        ${article.images.map(img => `
                                            <div>
                                                <p>الوصف: ${img.caption}</p>
                                                <p>الرابط: ${img.url}</p>
                                            </div>
                                        `).join('')}
                                    </div>
                                ` : ''}
                                
                                <div class="article-content">${article.content}</div>
                                
                                ${article.related_articles && article.related_articles.length > 0 ? `
                                    <div class="related-articles">
                                        <h4>المقالات ذات الصلة:</h4>
                                        ${article.related_articles.map(related => `
                                            <div>
                                                <a href="${related.url}" target="_blank">${related.title}</a>
                                            </div>
                                        `).join('')}
                                    </div>
                                ` : ''}
                            </div>
                        `;
                    });
                    document.getElementById('status').innerHTML = `تم العثور على ${data.articles.length} مقال`;
                } else {
                    document.getElementById('status').innerHTML = 'لم يتم العثور على مقالات';
                }
                
                document.getElementById('result').innerHTML = resultHTML;
            })
            .catch(error => {
                document.getElementById('loading').style.display = 'none';
                document.getElementById('status').innerHTML = 'حدث خطأ أثناء المعالجة';
            });
        }

        function downloadHTML() {
            if (!currentArticles) return;
            
            fetch('/download', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ articles: currentArticles })
            })
            .then(response => response.blob())
            .then(blob => {
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `articles_${new Date().toISOString().slice(0,19).replace(/:/g, '-')}.html`;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                a.remove();
            })
            .catch(error => {
                alert('حدث خطأ أثناء تحميل الملف');
            });
        }
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(main_template)

@app.route('/process', methods=['POST'])
def process():
    url = request.form.get('url')
    try:
        all_articles = []
        links = get_links(url)
        if not links:
            links = [url]
        
        for link in links:
            articles = get_article_content(link)
            if articles:
                all_articles.extend(articles)
        
        return {"articles": all_articles}
    except Exception as e:
        return {"error": str(e)}

@app.route('/download', methods=['POST'])
def download():
    try:
        articles = request.json.get('articles', [])
        if not articles:
            return "No articles to download", 400
        
        file_path = generate_html_file(articles)
        return send_file(file_path, as_attachment=True)
    except Exception as e:
        return str(e), 500

if __name__ == "__main__":
    app.run()
