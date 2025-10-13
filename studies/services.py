import requests
from django.core.cache import cache

def get_study_page_html(repo_url):
    if not repo_url:
        return "<h2>Study page has not been configured.</h2>"
    
    page_url = f"{repo_url}/front_page.html"
    
    cache_key = f'study_page_html_{repo_url}'
    cached_html = cache.get(cache_key)
    if cached_html:
        return cached_html
    try:
        response = requests.get(page_url, timeout=5)
        response.raise_for_status()
        html_content = response.text
        cache.set(cache_key, html_content, 300) 
        return html_content
    except requests.RequestException as e:
        return f"<h2>Error fetching study page: {e}</h2>"