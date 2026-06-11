from flask import Flask, request, jsonify, render_template_string
import yt_dlp
import os
import re

app = Flask(__name__)

# Professional Professional UI like FDOWN.net
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Social Media Video Downloader</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style> body { font-family: 'Inter', sans-serif; } </style>
</head>
<body class="bg-gray-50 min-h-screen flex flex-col items-center justify-center p-4">

    <div class="bg-white p-6 md:p-8 rounded-2xl shadow-xl w-full max-w-2xl border border-gray-100 text-center">
        
        <div class="mb-6">
            <div class="inline-block bg-[#5A4FCF] text-white text-3xl font-black px-5 py-2 rounded-xl shadow-md mb-2">
                F
            </div>
            <h1 class="text-2xl font-bold text-gray-800">Social Video Downloader</h1>
            <p class="text-sm text-gray-500">Download Your Favorite Videos Easily</p>
        </div>

        <div class="flex flex-col sm:flex-row gap-2 max-w-xl mx-auto mb-6">
            <input type="url" id="videoUrl" placeholder="Enter video link here..." 
                   class="w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-[#5A4FCF] text-base">
            <button onclick="getDownloadData()" 
                    class="bg-[#5A4FCF] hover:bg-[#483ebd] text-white font-semibold py-3 px-6 rounded-xl transition duration-200 whitespace-nowrap">
                Download
            </button>
        </div>

        <div id="loading" class="hidden my-8 text-gray-600 font-medium animate-pulse">
            Analyzing video link, please wait...
        </div>

        <div id="result" class="hidden mt-6 border-t pt-6 text-left">
            
            <div class="flex flex-col md:flex-row bg-gray-50 border border-gray-200 rounded-xl p-4 gap-4 mb-6">
                <div class="w-full md:w-48 h-32 bg-gray-200 rounded-lg overflow-hidden flex-shrink-0 shadow-sm">
                    <img id="videoThumb" src="" alt="Thumbnail" class="w-full h-full object-cover">
                </div>
                <div class="flex flex-col justify-center overflow-hidden">
                    <h2 id="videoTitle" class="text-lg font-bold text-gray-800 truncate">No video title</h2>
                    <p id="videoDuration" class="text-sm text-gray-500 mt-1">Duration: --:--</p>
                    <p class="text-xs text-green-600 font-semibold mt-2">✓ Link generated successfully!</p>
                </div>
            </div>

            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <button onclick="triggerDownload('normal')" 
                   class="bg-slate-700 hover:bg-slate-800 text-white font-bold py-3 px-4 rounded-xl text-center transition shadow">
                    Download Video in Normal Quality
                </button>
                <button onclick="triggerDownload('hd')" 
                   class="bg-[#5A4FCF] hover:bg-[#483ebd] text-white font-bold py-3 px-4 rounded-xl text-center transition shadow">
                    Download Video in HD Quality
                </button>
            </div>
        </div>

        <div id="savingAlert" class="hidden mt-4 text-sm text-blue-600 font-medium animate-bounce">
            Preparing file... Your browser will prompt the "Save As" window shortly.
        </div>
    </div>

    <script>
        let videoData = null;

        async function getDownloadData() {
            const url = document.getElementById('videoUrl').value;
            const loading = document.getElementById('loading');
            const result = document.getElementById('result');
            const savingAlert = document.getElementById('savingAlert');

            if (!url) {
                alert('Please enter a video link first!');
                return;
            }

            loading.classList.remove('hidden');
            result.classList.add('hidden');
            savingAlert.classList.add('hidden');

            try {
                const response = await fetch(`/api/download?url=${encodeURIComponent(url)}`);
                const data = await response.json();

                if (data.success) {
                    videoData = data;
                    
                    // Display Data
                    document.getElementById('videoThumb').src = data.thumbnail || 'https://placehold.co/192x128?text=Video';
                    document.getElementById('videoTitle').innerText = data.title_display;
                    document.getElementById('videoDuration').innerText = "Duration: " + data.duration;
                    
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

        // Advanced JS Blob download method to force folder prompt and keep custom title
        async function triggerDownload(quality) {
            if (!videoData) return;

            const savingAlert = document.getElementById('savingAlert');
            savingAlert.classList.remove('hidden');

            // Select quality link
            let targetUrl = videoData.normal_url;
            if (quality === 'hd' && videoData.hd_url) {
                targetUrl = videoData.hd_url;
            }

            const fileName = `${videoData.title}_${quality}.mp4`;

            try {
                const response = await fetch(targetUrl);
                const blob = await response.blob();
                const blobUrl = window.URL.createObjectURL(blob);
                
                const tempLink = document.createElement('a');
                tempLink.href = blobUrl;
                tempLink.setAttribute('download', fileName);
                document.body.appendChild(tempLink);
                tempLink.click();
                
                document.body.removeChild(tempLink);
                window.URL.revokeObjectURL(blobUrl);
            } catch (error) {
                // CORS Fallback helper
                alert("Direct save blocked by browser policy. Opening video link... Please right-click and choose 'Save video as...'");
                window.open(targetUrl, '_blank');
            } finally {
                savingAlert.classList.add('hidden');
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

    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            
            # Formats separation handling
            formats = info.get('formats', [])
            normal_url = info.get('url') # Default fallback link
            hd_url = info.get('url')     # Default fallback link
            
            # Find better formats if available
            mp4_formats = [f for f in formats if f.get('vcodec') != 'none' and f.get('acodec') != 'none' and f.get('ext') == 'mp4']
            
            if mp4_formats:
                # Sort by resolution height
                mp4_formats = sorted(mp4_formats, key=lambda x: x.get('height', 0))
                normal_url = mp4_formats[0].get('url') # Lowest resolution format
                hd_url = mp4_formats[-1].get('url')    # Highest resolution format

            original_title = info.get('title', 'video')
            clean_title = re.sub(r'[^\w\s-]', '', original_title).strip().replace(' ', '_')
            
            # Convert raw seconds into MM:SS format display
            duration_secs = info.get('duration', 0)
            mins = duration_secs // 60
            secs = duration_secs % 60
            duration_str = f"{mins:02d}:{secs:02d} minutes" if duration_secs else "Unknown"

            return jsonify({
                'success': True,
                'normal_url': normal_url,
                'hd_url': hd_url,
                'title': clean_title,
                'title_display': original_title,
                'thumbnail': info.get('thumbnail'),
                'duration': duration_str
            })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
