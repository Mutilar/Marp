"""
HTTP MJPEG streaming server with web viewer.
"""

import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from typing import TYPE_CHECKING

from ..config import PICAM_PRESETS, KINECT_WIDTH, KINECT_HEIGHT, KINECT_SOURCES, get_available_sources
from ..state import global_state

if TYPE_CHECKING:
    from ..manager import StreamManager


class MJPEGStreamHandler(BaseHTTPRequestHandler):
    """HTTP handler for MJPEG streaming and web viewer."""
    
    # Set by factory function
    manager: 'StreamManager' = None
    stream_id: str = 'main'
    debug: bool = False
    
    def log_message(self, format, *args):
        if self.debug:
            print(f"HTTP: {args[0]}")
            
    def do_GET(self):
        if self.path == '/' or self.path == '/index.html':
            self.send_viewer_page()
        elif self.path == '/dual' or self.path == '/dual.html':
            self.send_dual_viewer_page()
        elif self.path == '/stream.mjpg' or self.path == '/stream':
            self.send_mjpeg_stream()
        elif self.path.startswith('/stream/'):
            # /stream/main or /stream/secondary
            stream_name = self.path.split('/stream/')[-1].split('?')[0].rstrip('/')
            self.send_mjpeg_stream(stream_name)
        elif self.path == '/status':
            self.send_status()
        elif self.path.startswith('/switch'):
            self.handle_switch()
        elif self.path == '/favicon.ico':
            self.send_error(404)
        else:
            self.send_error(404)
            
    def do_POST(self):
        if self.path.startswith('/switch'):
            self.handle_switch()
        else:
            self.send_error(404)
            
    def send_viewer_page(self):
        """Send HTML page with embedded MJPEG viewer and multi-stream controls."""
        streams = self.manager.list_streams()
        stream_buttons = '\n'.join([
            f'<button onclick="selectStream(\'{s}\')" id="stream-btn-{s}" '
            f'class="{"active" if s == self.stream_id else ""}">{s.title()}</button>'
            for s in streams
        ])
        
        html = f'''<!DOCTYPE html>
<html>
<head>
    <title>Video Multiplexer - {self.stream_id}</title>
    <style>
        body {{ 
            font-family: Arial, sans-serif; 
            background: #1a1a2e; 
            color: #eee;
            margin: 0;
            padding: 20px;
        }}
        h1 {{ color: #00d9ff; margin-bottom: 10px; }}
        .container {{ max-width: 1300px; margin: 0 auto; }}
        .video-container {{
            background: #000;
            border-radius: 8px;
            overflow: hidden;
            margin-bottom: 20px;
        }}
        img {{ 
            width: 100%; 
            max-width: 1280px;
            display: block;
        }}
        .controls {{
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            margin-bottom: 15px;
            align-items: center;
        }}
        .control-group {{
            display: flex;
            gap: 8px;
            align-items: center;
            background: #16213e;
            padding: 8px 12px;
            border-radius: 6px;
        }}
        .control-group label {{
            font-size: 14px;
            color: #aaa;
        }}
        button {{
            padding: 10px 20px;
            font-size: 14px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            background: #16213e;
            color: #eee;
            transition: all 0.2s;
        }}
        button:hover {{ background: #0f3460; }}
        button.active {{ background: #00d9ff; color: #000; }}
        button:disabled {{ background: #333; color: #666; cursor: not-allowed; }}
        select, input[type="range"] {{
            background: #0f3460;
            color: #eee;
            border: 1px solid #00d9ff;
            border-radius: 4px;
            padding: 6px;
        }}
        input[type="range"] {{ width: 100px; }}
        .status {{
            background: #16213e;
            padding: 15px;
            border-radius: 8px;
            font-family: monospace;
            font-size: 13px;
        }}
        .status span {{ color: #00d9ff; }}
        h3 {{ margin: 15px 0 10px 0; color: #00d9ff; font-size: 14px; }}
        .stream-selector {{
            background: #0f3460;
            padding: 10px;
            border-radius: 8px;
            margin-bottom: 15px;
        }}
        .stream-selector button.active {{
            background: #e94560;
        }}
        .nav-links {{
            margin-bottom: 15px;
        }}
        .nav-links a {{
            color: #00d9ff;
            text-decoration: none;
            margin-right: 15px;
        }}
        .nav-links a:hover {{ text-decoration: underline; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🎥 Video Multiplexer</h1>
        
        <div class="nav-links">
            <a href="/">Single Stream View</a>
            <a href="/dual">Dual View (Both Streams)</a>
        </div>
        
        <div class="stream-selector">
            <label style="margin-right: 10px;">Viewing Stream:</label>
            {stream_buttons}
        </div>
        
        <div class="video-container">
            <img id="stream" src="/stream.mjpg" alt="Video Stream">
        </div>
        
        <h3>Video Source for <span id="current-stream-name">{self.stream_id}</span></h3>
        <div class="controls">
            <button onclick="switchSource('kinect_rgb')" id="btn-kinect_rgb">Kinect RGB</button>
            <button onclick="switchSource('kinect_ir')" id="btn-kinect_ir">Kinect IR</button>
            <button onclick="switchSource('kinect_depth')" id="btn-kinect_depth">Kinect Depth</button>
            <button onclick="switchSource('picam')" id="btn-picam">Pi Camera</button>
        </div>
        
        <h3>Quality & Resolution</h3>
        <div class="controls">
            <div class="control-group">
                <label>JPEG Quality:</label>
                <input type="range" id="quality" min="10" max="100" value="70" onchange="setQuality(this.value)">
                <span id="quality-val">70</span>
            </div>
            <div class="control-group">
                <label>Kinect Scale:</label>
                <select id="scale" onchange="setScale(this.value)">
                    <option value="0.5">320x240 (0.5x)</option>
                    <option value="0.75">480x360 (0.75x)</option>
                    <option value="1.0" selected>640x480 (1.0x)</option>
                    <option value="1.5">960x720 (1.5x)</option>
                    <option value="2.0">1280x960 (2.0x)</option>
                </select>
            </div>
            <div class="control-group">
                <label>Pi Cam Res:</label>
                <select id="picam_res" onchange="setPicamRes(this.value)">
                    <option value="low">640x480 (low)</option>
                    <option value="medium">1280x720 (medium)</option>
                    <option value="high" selected>1280x800 (high)</option>
                    <option value="full">1920x1080 (full)</option>
                </select>
            </div>
        </div>
        
        <div class="status" id="status">
            Stream: <span id="stream-id">{self.stream_id}</span> |
            Source: <span id="current-source">loading...</span> | 
            Kinect: <span id="kinect-status">-</span> |
            Resolution: <span id="resolution">-</span> | 
            Quality: <span id="jpeg-quality">-</span> |
            Frames: <span id="frames">0</span> |
            Clients: <span id="clients">0</span>
        </div>
    </div>
    <script>
        let currentStreamId = '{self.stream_id}';
        
        function selectStream(streamId) {{
            // Navigate to the other stream's port
            // For now, just update the UI - in production you'd switch ports
            window.location.href = '/?stream=' + streamId;
        }}
        
        function switchSource(source) {{
            fetch('/switch?source=' + source + '&stream=' + currentStreamId);
            document.querySelectorAll('.controls button[id^="btn-"]').forEach(b => b.classList.remove('active'));
            document.getElementById('btn-' + source).classList.add('active');
        }}
        
        function setQuality(val) {{
            document.getElementById('quality-val').textContent = val;
            fetch('/switch?quality=' + val + '&stream=' + currentStreamId);
        }}
        
        function setScale(val) {{
            fetch('/switch?scale=' + val + '&stream=' + currentStreamId);
        }}
        
        function setPicamRes(val) {{
            fetch('/switch?picam_res=' + val + '&stream=' + currentStreamId);
        }}
        
        function updateStatus() {{
            fetch('/status')
                .then(r => r.json())
                .then(data => {{
                    const streamData = data.streams[currentStreamId] || {{}};
                    
                    document.getElementById('stream-id').textContent = currentStreamId;
                    document.getElementById('current-source').textContent = streamData.source || '-';
                    document.getElementById('resolution').textContent = streamData.resolution || '-';
                    document.getElementById('jpeg-quality').textContent = streamData.jpeg_quality || '-';
                    document.getElementById('frames').textContent = streamData.frames_captured || 0;
                    document.getElementById('clients').textContent = streamData.clients_connected || 0;
                    
                    let kinectStatus = document.getElementById('kinect-status');
                    if (data.kinect_available) {{
                        kinectStatus.textContent = 'OK';
                        kinectStatus.style.color = '#00ff00';
                    }} else {{
                        kinectStatus.textContent = 'N/A';
                        kinectStatus.style.color = '#ff6666';
                    }}
                    
                    ['kinect_rgb', 'kinect_ir', 'kinect_depth'].forEach(src => {{
                        let btn = document.getElementById('btn-' + src);
                        if (btn) btn.disabled = !data.kinect_available;
                    }});
                    
                    if (streamData.jpeg_quality) {{
                        document.getElementById('quality').value = streamData.jpeg_quality;
                        document.getElementById('quality-val').textContent = streamData.jpeg_quality;
                    }}
                    if (streamData.scale_factor) {{
                        document.getElementById('scale').value = streamData.scale_factor;
                    }}
                    if (streamData.picam_preset) {{
                        document.getElementById('picam_res').value = streamData.picam_preset;
                    }}
                    
                    document.querySelectorAll('.controls button[id^="btn-"]').forEach(b => b.classList.remove('active'));
                    if (streamData.source) {{
                        let btn = document.getElementById('btn-' + streamData.source);
                        if (btn) btn.classList.add('active');
                    }}
                }});
        }}
        
        setInterval(updateStatus, 2000);
        updateStatus();
    </script>
</body>
</html>'''
        
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.send_header('Content-Length', len(html))
        self.end_headers()
        self.wfile.write(html.encode())

    def send_dual_viewer_page(self):
        """Send HTML page with both streams side-by-side."""
        streams = self.manager.list_streams()
        
        html = '''<!DOCTYPE html>
<html>
<head>
    <title>Video Multiplexer - Dual View</title>
    <style>
        body { 
            font-family: Arial, sans-serif; 
            background: #1a1a2e; 
            color: #eee;
            margin: 0;
            padding: 20px;
        }
        h1 { color: #00d9ff; margin-bottom: 10px; }
        .container { max-width: 1800px; margin: 0 auto; }
        .dual-view {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 20px;
        }
        @media (max-width: 1200px) {
            .dual-view {
                grid-template-columns: 1fr;
            }
        }
        .stream-panel {
            background: #16213e;
            border-radius: 8px;
            overflow: hidden;
            padding: 15px;
        }
        .stream-panel h2 {
            margin: 0 0 10px 0;
            color: #00d9ff;
            font-size: 18px;
        }
        .video-container {
            background: #000;
            border-radius: 8px;
            overflow: hidden;
            margin-bottom: 15px;
        }
        img { 
            width: 100%; 
            display: block;
        }
        .controls {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            margin-bottom: 10px;
        }
        button {
            padding: 8px 16px;
            font-size: 13px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            background: #0f3460;
            color: #eee;
            transition: all 0.2s;
        }
        button:hover { background: #1a5490; }
        button.active { background: #00d9ff; color: #000; }
        button:disabled { background: #333; color: #666; cursor: not-allowed; }
        .status-bar {
            font-family: monospace;
            font-size: 12px;
            color: #aaa;
        }
        .status-bar span { color: #00d9ff; }
        .nav-links {
            margin-bottom: 15px;
        }
        .nav-links a {
            color: #00d9ff;
            text-decoration: none;
            margin-right: 15px;
        }
        .nav-links a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎥 Video Multiplexer - Dual View</h1>
        
        <div class="nav-links">
            <a href="/">Single Stream View</a>
            <a href="/dual">Dual View</a>
        </div>
        
        <div class="dual-view">
            <div class="stream-panel">
                <h2>📹 Main Stream</h2>
                <div class="video-container">
                    <img id="stream-main" src="/stream/main" alt="Main Stream">
                </div>
                <div class="controls" id="controls-main">
                    <button onclick="switchSource('main', 'kinect_rgb')" id="btn-main-kinect_rgb">Kinect RGB</button>
                    <button onclick="switchSource('main', 'kinect_ir')" id="btn-main-kinect_ir">Kinect IR</button>
                    <button onclick="switchSource('main', 'kinect_depth')" id="btn-main-kinect_depth">Kinect Depth</button>
                    <button onclick="switchSource('main', 'picam')" id="btn-main-picam">Pi Camera</button>
                </div>
                <div class="status-bar">
                    Source: <span id="source-main">-</span> | 
                    Resolution: <span id="res-main">-</span> | 
                    Frames: <span id="frames-main">0</span>
                </div>
            </div>
            
            <div class="stream-panel">
                <h2>📹 Secondary Stream</h2>
                <div class="video-container">
                    <img id="stream-secondary" src="/stream/secondary" alt="Secondary Stream">
                </div>
                <div class="controls" id="controls-secondary">
                    <button onclick="switchSource('secondary', 'kinect_rgb')" id="btn-secondary-kinect_rgb">Kinect RGB</button>
                    <button onclick="switchSource('secondary', 'kinect_ir')" id="btn-secondary-kinect_ir">Kinect IR</button>
                    <button onclick="switchSource('secondary', 'kinect_depth')" id="btn-secondary-kinect_depth">Kinect Depth</button>
                    <button onclick="switchSource('secondary', 'picam')" id="btn-secondary-picam">Pi Camera</button>
                </div>
                <div class="status-bar">
                    Source: <span id="source-secondary">-</span> | 
                    Resolution: <span id="res-secondary">-</span> | 
                    Frames: <span id="frames-secondary">0</span>
                </div>
            </div>
        </div>
    </div>
    <script>
        function switchSource(streamId, source) {
            fetch('/switch?source=' + source + '&stream=' + streamId);
            // Update active button
            document.querySelectorAll('#controls-' + streamId + ' button').forEach(b => b.classList.remove('active'));
            document.getElementById('btn-' + streamId + '-' + source).classList.add('active');
        }
        
        function updateStatus() {
            fetch('/status')
                .then(r => r.json())
                .then(data => {
                    ['main', 'secondary'].forEach(streamId => {
                        const streamData = data.streams[streamId] || {};
                        
                        document.getElementById('source-' + streamId).textContent = streamData.source || '-';
                        document.getElementById('res-' + streamId).textContent = streamData.resolution || '-';
                        document.getElementById('frames-' + streamId).textContent = streamData.frames_captured || 0;
                        
                        // Disable Kinect buttons if not available
                        ['kinect_rgb', 'kinect_ir', 'kinect_depth'].forEach(src => {
                            let btn = document.getElementById('btn-' + streamId + '-' + src);
                            if (btn) btn.disabled = !data.kinect_available;
                        });
                        
                        // Update active button
                        document.querySelectorAll('#controls-' + streamId + ' button').forEach(b => b.classList.remove('active'));
                        if (streamData.source) {
                            let btn = document.getElementById('btn-' + streamId + '-' + streamData.source);
                            if (btn) btn.classList.add('active');
                        }
                    });
                });
        }
        
        setInterval(updateStatus, 2000);
        updateStatus();
    </script>
</body>
</html>'''
        
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.send_header('Content-Length', len(html))
        self.end_headers()
        self.wfile.write(html.encode())
        
    def send_mjpeg_stream(self, stream_id: str = None):
        """Send continuous MJPEG stream."""
        if stream_id is None:
            stream_id = self.stream_id
        stream = self.manager.get_stream(stream_id)
        if stream is None:
            self.send_error(404, f"Stream '{stream_id}' not found")
            return
            
        self.send_response(200)
        self.send_header('Content-Type', 
                         'multipart/x-mixed-replace; boundary=--jpgboundary')
        self.send_header('Cache-Control', 'no-cache, private')
        self.send_header('Pragma', 'no-cache')
        self.end_headers()
        
        stream.increment_clients()
        last_frame_id = 0
            
        try:
            while global_state.running:
                frame, last_frame_id = stream.get_frame(last_frame_id, timeout=1.0)
                
                if frame is None:
                    continue
                    
                try:
                    self.wfile.write(b'--jpgboundary\r\n')
                    self.wfile.write(b'Content-Type: image/jpeg\r\n')
                    self.wfile.write(f'Content-Length: {len(frame)}\r\n\r\n'.encode())
                    self.wfile.write(frame)
                    self.wfile.write(b'\r\n')
                    self.wfile.flush()
                    
                    stream.increment_frames_sent()
                        
                except (BrokenPipeError, ConnectionResetError):
                    break
                
        finally:
            stream.decrement_clients()
                
    def send_status(self):
        """Send JSON status for all streams."""
        status = self.manager.get_status()
        body = json.dumps(status).encode()
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', len(body))
        self.end_headers()
        self.wfile.write(body)
        
    def handle_switch(self):
        """Handle source/settings switch."""
        if '?' not in self.path:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b'ERROR: Missing parameters\n')
            return
            
        query = self.path.split('?')[1]
        params = dict(p.split('=') for p in query.split('&') if '=' in p)
        
        # Determine which stream to modify
        target_stream_id = params.get('stream', self.stream_id)
        stream = self.manager.get_stream(target_stream_id)
        
        if stream is None:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(f'ERROR: Stream "{target_stream_id}" not found\n'.encode())
            return
            
        response_parts = []
        
        # Handle source switch
        source = params.get('source', '')
        if source:
            success, msg = self.manager.switch_source(target_stream_id, source)
            if not success:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(f'ERROR: {msg}\n'.encode())
                return
            response_parts.append(f"source={source}")
        
        # Handle quality
        quality = params.get('quality', '')
        if quality:
            try:
                q = int(quality)
                if 1 <= q <= 100:
                    stream.update_settings(jpeg_quality=q)
                    response_parts.append(f"quality={q}")
                else:
                    raise ValueError("out of range")
            except:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b'ERROR: quality must be 1-100\n')
                return
                
        # Handle scale
        scale = params.get('scale', '')
        if scale:
            try:
                s = float(scale)
                if 0.25 <= s <= 2.0:
                    stream.update_settings(scale_factor=s)
                    response_parts.append(f"scale={s}")
                else:
                    raise ValueError("out of range")
            except:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b'ERROR: scale must be 0.25-2.0\n')
                return
                
        # Handle picam_res
        picam_res = params.get('picam_res', '')
        if picam_res:
            if picam_res in PICAM_PRESETS:
                stream.update_settings(picam_preset=picam_res)
                response_parts.append(f"picam_res={picam_res}")
            else:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(f'ERROR: picam_res must be: {list(PICAM_PRESETS.keys())}\n'.encode())
                return
        
        if response_parts:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(f'OK: {", ".join(response_parts)} (stream: {target_stream_id})\n'.encode())
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b'ERROR: No valid parameters. Use: source, quality, scale, picam_res\n')


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Threaded HTTP server for handling multiple clients."""
    daemon_threads = True
    allow_reuse_address = True


def create_http_server(manager: 'StreamManager', stream_id: str, port: int, 
                       debug: bool = False) -> ThreadedHTTPServer:
    """Create an HTTP MJPEG streaming server for a specific stream.
    
    Args:
        manager: The StreamManager instance
        stream_id: Which stream this server serves
        port: Port to listen on
        debug: Enable debug logging
        
    Returns:
        Configured ThreadedHTTPServer (not yet started)
    """
    # Create a custom handler class with the manager bound
    class BoundHandler(MJPEGStreamHandler):
        pass
        
    BoundHandler.manager = manager
    BoundHandler.stream_id = stream_id
    BoundHandler.debug = debug
    
    server = ThreadedHTTPServer(('0.0.0.0', port), BoundHandler)
    return server
