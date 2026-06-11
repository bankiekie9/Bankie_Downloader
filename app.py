from flask import Flask, request, jsonify, render_template_string, Response
import yt_dlp
import os
import requests
import re

app = Flask(__name__)

# Premium Video Downloader UI
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>All-In-One Video Downloader</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style> body { font-family: 'Inter', sans-serif; } </style>
</head>
<body class="bg-gray-50 min-h-screen flex flex-col items-center justify-center p-4">

    <div class="bg-white p-8 rounded-2xl shadow-xl w-full max-w-xl border border-gray-100">
        <div class="text-center mb-4">
            <span class="bg-[#5A4FCF] text-white text-xs font-semibold px-4 py-1 rounded-full shadow-sm">
                Premium Tool
            </span>
        </div>
        
        <h1 class="text-2xl font-bold text-center text-gray-800 mb-2">Social Media Downloader</h1>
        <p class="text-sm text-gray-500 text-center mb-6">Supports: YouTube, TikTok, Facebook, Instagram (1080p HD)</p>

        <div class="space-y-4">
            <input type="url" id="videoUrl" placeholder="Paste video link here..." 
                   class="w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-[#5A4FCF] text-base">
            
            <button onclick="getDownloadLink()" 
                    class="w-full bg-[#5A4FCF] hover:bg-[#483ebd] text-white font-semibold py-3 rounded-xl transition duration-200 shadow-md">
                Get Download Link
            </button>
        </div>

        <div id="loading" class="mt-6 text-center hidden text-gray-600 font-medium animate-pulse">
            Fetching highest quality video, please wait...
        </div>

        <div id="result" class="mt-6 hidden bg-green-50 p-5 rounded-xl text-center border border-green-200">
            <p id="videoTitle" class="text-gray-700 font-medium text-sm mb-2 truncate"></p>
            <p class="text-green-700 font-semibold mb-3">Video Found Successfully! 🎉</p>
            <a id="downloadBtn" href="#" 
               class="inline-block bg-green-500 hover:bg-green-600 text-white font-bold py-2.5 px-6 rounded-lg transition duration-200 shadow">
                Download Now
            </a>
        </div>
    </div>

    <script>
        async function getDownloadLink() {
            const url = document.getElementById('videoUrl').value;
            const loading = document.getElementById('loading');
            const result = document.getElementById('result');
            const downloadBtn = document.getElementById('downloadBtn');
            const videoTitleText = document.getElementById('videoTitle');

            if (!url) {
                alert('Please paste a video URL first!');
                return;
            }

            loading.classList.remove('hidden');
            result.classList.add('hidden');

            try {
                const response = await fetch(`/api/download?url=${encodeURIComponent(url)}`);
                const data = await response.json();

                if (data.success) {
                    // ប្តូរទៅហៅផ្លូវ Proxy ដើម្បីបង្ខំឱ្យ Browser លោតផ្ទាំង Save As ជាប់ចំណងជើង
                    downloadBtn.href = `/api/fetch?url=${encodeURIComponent(data.download_url)}&title=${encodeURIComponent(data.title)}`;
                    videoTitleText.innerText = "Title: " + data.title;
                    result.classList.remove('hidden');
                } else {
                    alert('Error: ' + data.error);
                }
            } catch (error) {
                alert('Failed to connect to the server!');
            } finally {
                loading.classList.add('hidden');
            }
        }
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/download')
def download():
    video_url = request.args.get('url')
    if not video_url:
        return jsonify({'success': False, 'error': 'No URL provided'})

    # កំណត់ទាញយកទម្រង់វីដេអូដែលច្បាស់បំផុត (HD/1080p) ដែលមានទាំងរូបភាពនិងសំឡេងស្រាប់
    ydl_opts = {
        'format': 'best[ext=mp4]/best', 
        'quiet': True,
        'no_warnings': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            direct_url = info.get('url')
            title = info.get('title', 'video')
            
            # លុបសញ្ញាពិសេសចេញពី Title ការពារការខូចឈ្មោះឯកសារពេល Save
            clean_title = re.sub(r'[^\w\s-]', '', title).strip().replace(' ', '_')
            
            if direct_url:
                return jsonify({'success': True, 'download_url': direct_url, 'title': clean_title})
            else:
                return jsonify({'success': False, 'error': 'Could not extract high-quality URL'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ផ្លូវពិសេស (Proxy Route) បង្ខំឱ្យ Browser លោតផ្ទាំងដោនឡូត "Save As" ចូល PC ភ្លាមៗ
@app.route('/api/fetch')
def fetch_video():
    target_url = request.args.get('url')
    filename = request.args.get('title', 'video')
    
    if not target_url:
        return "Missing URL", 400

    try:
        req = requests.get(target_url, stream=True)
        headers = {
            'Content-Disposition': f'attachment; filename="{filename}.mp4"',
            'Content-Type': req.headers.get('Content-Type', 'video/mp4')
        }
        
        # បញ្ជូនទិន្នន័យជាកញ្ចប់ៗ (Streaming) ដើម្បីកុំឱ្យណែន RAM របស់ Server Free លើ Render
        def generate():
            for chunk in req.iter_content(chunk_size=4096):
                if chunk:
                    yield chunk
                    
        return Response(generate(), headers=headers)
    except Exception as e:
        return str(e), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
