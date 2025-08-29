
from flask import Flask, request, Response, render_template, jsonify
import requests
from urllib.parse import urlparse, urljoin
import re
import logging
from functools import wraps
import os

app = Flask(__name__)
app.logger.setLevel(logging.INFO)

# Configure to use USA servers (Heroku will deploy in US region)
USA_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"

def validate_mp4_url(url):
    """Validate that the URL points to an MP4 resource"""
    try:
        # Check if it's a valid URL
        parsed = urlparse(url)
        if not all([parsed.scheme, parsed.netloc]):
            return False
            
        # Check if it ends with .mp4 or has video/mp4 content type
        if url.lower().endswith('.mp4'):
            return True
            
        # We'll check the content type during the actual request
        return True
    except:
        return False

def add_us_headers(headers=None):
    """Add headers that make the request appear to come from the USA"""
    if headers is None:
        headers = {}
    
    headers.update({
        'User-Agent': USA_USER_AGENT,
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'identity;q=1, *;q=0',
        'Accept': '*/*',
        'Referer': 'https://www.google.com/',
        'Origin': 'https://www.google.com',
        'Connection': 'keep-alive',
    })
    return headers

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/proxy')
def proxy_video():
    video_url = request.args.get('url')
    if not video_url:
        return jsonify({'error': 'URL parameter is required'}), 400
    
    if not validate_mp4_url(video_url):
        return jsonify({'error': 'Invalid MP4 URL'}), 400
    
    try:
        # Make the request with USA headers
        headers = add_us_headers()
        req = requests.get(video_url, headers=headers, stream=True, timeout=30)
        
        # Check if the response is successful
        if req.status_code != 200:
            return jsonify({'error': f'Failed to fetch video. Status code: {req.status_code}'}), 500
        
        # Stream the video content through our proxy
        def generate():
            for chunk in req.iter_content(chunk_size=8192):
                yield chunk
                
        response_headers = {
            'Content-Type': req.headers.get('Content-Type', 'video/mp4'),
            'Content-Length': req.headers.get('Content-Length', ''),
            'Accept-Ranges': 'bytes',
            'Cache-Control': 'public, max-age=3600',
        }
        
        return Response(generate(), headers=response_headers, status=req.status_code)
        
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Proxy error: {str(e)}")
        return jsonify({'error': f'Proxy error: {str(e)}'}), 500
    except Exception as e:
        app.logger.error(f"Unexpected error: {str(e)}")
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500

@app.route('/health')
def health_check():
    return jsonify({'status': 'healthy', 'server': 'USA proxy'})
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))  # Heroku provides PORT env var
    app.run(host='0.0.0.0', port=port)
