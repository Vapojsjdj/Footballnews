from flask import Flask, render_template_string, request, render_template
import requests
import re
import time
import json

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
        print(f"Error in get_links: {str(e)}")
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
                
                # استخراج العنوان
                title_end = part.find('";')
                if title_end != -1:
                    article['title'] = part[:title_end]
                
                # استخراج المحتوى
                content_start = part.find('var article_content = "')
                if content_start != -1:
                    content_start += len('var article_content = "')
                    content_end = part.find('";', content_start)
                    if content_end != -1:
                        content = part[content_start:content_end]
                        content = content.replace('\\n', '\n').replace('\\"', '"').strip()
                        article['content'] = content
                
                # استخراج الصور
                article['images'] = extract_images(part)
                
                # استخراج التاريخ
                date_start = part.find('var article_date = "')
                if date_start != -1:
                    date_start += len('var article_date = "')
                    date_end = part.find('";', date_start)
                    if date_end != -1:
                        article['date'] = part[date_start:date_end]
                
                # استخراج المقالات ذات الصلة
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
                print(f"Error processing article part: {str(e)}")
                continue
                
        return articles
        
    except Exception as e:
        print(f"Error in get_article_content: {str(e)}")
        return []

def save_articles_to_file(articles):
    try:
        with open('articles_data.json', 'w', encoding='utf-8') as f:
            json.dump(articles, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        print(f"Error saving articles: {str(e)}")
        return False

def load_articles_from_file():
    try:
        with open('articles_data.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []

@app.route('/')
def home():
    return render_template_string(main_template)

@app.route('/articles')
def articles():
    return render_template('articles.html')

@app.route('/get_articles')
def get_articles():
    try:
        # محاولة تحميل المقالات المحفوظة
        cached_articles = load_articles_from_file()
        
        # التحقق من وقت آخر تحديث
        current_time = time.time()
        last_update = getattr(app, 'last_update', 0)
        
        # تحديث المقالات كل 5 دقائق
        if not cached_articles or (current_time - last_update) > 300:
            base_url = "https://m.kooora.com/?o=n"
            all_articles = []
            
            links = get_links(base_url)
            if not links:
                links = [base_url]
            
            # معالجة أول 10 روابط
            for link in links[:10]:
                articles = get_article_content(link)
                if articles:
                    all_articles.extend(articles)
                    if len(all_articles) >= 20:
                        break
            
            if all_articles:
                save_articles_to_file(all_articles)
                app.last_update = current_time
                return {"articles": all_articles}
            else:
                return {"articles": cached_articles}
        else:
            return {"articles": cached_articles}
            
    except Exception as e:
        print(f"Error in get_articles route: {str(e)}")
        return {"error": str(e)}

@app.route('/process', methods=['POST'])
def process():
    url = request.form.get('url')
    try:
        all_articles = []
        
        links = get_links(url)
        if not links:
            links = [url]
        
        for link in links[:5]:  # تحديد عدد الروابط للمعالجة
            articles = get_article_content(link)
            if articles:
                all_articles.extend(articles)
        
        return {"articles": all_articles}
    except Exception as e:
        return {"error": str(e)}

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500


if __name__ == "__main__":
    app.run()
