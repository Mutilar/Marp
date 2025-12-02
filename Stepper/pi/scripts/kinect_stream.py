#!/usr/bin/env python3
import sys
import os
import time
import threading
import socket
import cv2
import numpy as np

# Add libfreenect python wrapper to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../libfreenect/build/wrappers/python/python3')))

try:
    import freenect
except ImportError:
    print("Error: Could not import freenect. Make sure it is built and the path is correct.")
    sys.exit(1)

RGB_PORT = 5601
DEPTH_PORT = 5602
CONTROL_PORT = 5603

keep_running = True
latest_video = None
latest_depth = None
frame_lock = threading.Lock()

# Mode state
current_video_mode = freenect.VIDEO_RGB
mode_change_requested = False
mode_lock = threading.Lock()

def get_video():
    global mode_change_requested
    
    # Check if a mode change is pending
    with mode_lock:
        if mode_change_requested:
            print("Switching video mode...")
            try:
                freenect.sync_stop()
            except Exception as e:
                print(f"Error stopping sync: {e}")
            mode_change_requested = False
            # Give it a moment to settle
            time.sleep(0.5)
            
        mode = current_video_mode

    return freenect.sync_get_video(0, mode)

def get_depth():
    return freenect.sync_get_depth()

def camera_loop():
    global latest_video, latest_depth
    print("Starting Kinect capture loop...")
    while keep_running:
        try:
            # Fetch frames
            # We fetch sequentially. sync_get_* functions manage the context.
            video_data = get_video()
            depth_data = get_depth()
            
            if video_data is not None:
                with frame_lock:
                    latest_video = video_data[0]
            
            if depth_data is not None:
                with frame_lock:
                    latest_depth = depth_data[0]
                    
        except Exception as e:
            print(f"Error in camera loop: {e}")
            # If we hit an error (e.g. device disconnected or mode switch fail), wait a bit
            time.sleep(1)

def process_video(frame):
    # Auto-detect format based on shape
    if len(frame.shape) == 2:
        # IR is 8-bit grayscale (480, 640)
        return cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
    else:
        # RGB is (480, 640, 3)
        return cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

def process_depth(frame):
    # Clip to max range (approx 2048 for Kinect v1)
    np.clip(frame, 0, 2047, out=frame)
    # Scale to 8-bit
    frame = (frame >> 3).astype(np.uint8)
    # Apply colormap
    return cv2.applyColorMap(frame, cv2.COLORMAP_JET)

def stream_client(client_socket, get_frame_func, process_func):
    try:
        while keep_running:
            frame = None
            with frame_lock:
                frame = get_frame_func()
            
            if frame is None:
                time.sleep(0.01)
                continue
            
            # Process frame
            processed = process_func(frame)
            
            # Encode to JPEG
            ret, jpeg = cv2.imencode('.jpg', processed, [int(cv2.IMWRITE_JPEG_QUALITY), 60])
            if not ret:
                continue
            
            # Send raw JPEG data
            try:
                client_socket.sendall(jpeg.tobytes())
            except (BrokenPipeError, ConnectionResetError):
                break
            
            # Limit framerate slightly to avoid saturating CPU/Network if no new frame
            time.sleep(0.03) 
            
    except Exception as e:
        print(f"Stream client error: {e}")
    finally:
        client_socket.close()

def server_thread(port, get_frame_func, process_func):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        server_socket.bind(('0.0.0.0', port))
        server_socket.listen(5)
        print(f"Listening on port {port}")
        
        while keep_running:
            server_socket.settimeout(1.0)
            try:
                client, addr = server_socket.accept()
                print(f"Accepted connection from {addr} on port {port}")
                t = threading.Thread(target=stream_client, args=(client, get_frame_func, process_func))
                t.daemon = True
                t.start()
            except socket.timeout:
                continue
            except Exception as e:
                print(f"Accept error on port {port}: {e}")
                
    except Exception as e:
        print(f"Server thread error on port {port}: {e}")
    finally:
        server_socket.close()

def control_client_handler(client_socket):
    global current_video_mode, mode_change_requested
    try:
        while keep_running:
            data = client_socket.recv(1024)
            if not data:
                break
            cmd = data.decode('utf-8').strip().lower()
            print(f"Received control command: {cmd}")
            
            if cmd == 'ir':
                with mode_lock:
                    if current_video_mode != freenect.VIDEO_IR_8BIT:
                        current_video_mode = freenect.VIDEO_IR_8BIT
                        mode_change_requested = True
                        client_socket.sendall(b"OK: Switched to IR\n")
                    else:
                        client_socket.sendall(b"OK: Already IR\n")
            elif cmd == 'rgb':
                with mode_lock:
                    if current_video_mode != freenect.VIDEO_RGB:
                        current_video_mode = freenect.VIDEO_RGB
                        mode_change_requested = True
                        client_socket.sendall(b"OK: Switched to RGB\n")
                    else:
                        client_socket.sendall(b"OK: Already RGB\n")
            else:
                client_socket.sendall(b"ERROR: Unknown command. Use 'ir' or 'rgb'\n")
    except Exception as e:
        print(f"Control client error: {e}")
    finally:
        client_socket.close()

def control_server_thread():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        server_socket.bind(('0.0.0.0', CONTROL_PORT))
        server_socket.listen(1)
        print(f"Control server listening on port {CONTROL_PORT}")
        
        while keep_running:
            server_socket.settimeout(1.0)
            try:
                client, addr = server_socket.accept()
                print(f"Control connection from {addr}")
                t = threading.Thread(target=control_client_handler, args=(client,))
                t.daemon = True
                t.start()
            except socket.timeout:
                continue
            except Exception as e:
                print(f"Control accept error: {e}")
    except Exception as e:
        print(f"Control server error: {e}")
    finally:
        server_socket.close()

def get_latest_video():
    return latest_video

def get_latest_depth():
    return latest_depth

if __name__ == "__main__":
    # Start camera thread
    cam_thread = threading.Thread(target=camera_loop)
    cam_thread.daemon = True
    cam_thread.start()
    
    # Start server threads
    # Port 5601: Video (RGB or IR)
    video_thread = threading.Thread(target=server_thread, args=(RGB_PORT, get_latest_video, process_video))
    video_thread.daemon = True
    video_thread.start()
    
    # Port 5602: Depth
    depth_thread = threading.Thread(target=server_thread, args=(DEPTH_PORT, get_latest_depth, process_depth))
    depth_thread.daemon = True
    depth_thread.start()
    
    # Port 5603: Control
    control_thread = threading.Thread(target=control_server_thread)
    control_thread.daemon = True
    control_thread.start()
    
    print(f"Kinect Streamer Running.")
    print(f"  - Video Stream (RGB/IR): Port {RGB_PORT}")
    print(f"  - Depth Stream:          Port {DEPTH_PORT}")
    print(f"  - Control (TCP):         Port {CONTROL_PORT} (Send 'ir' or 'rgb')")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping...")
        keep_running = False
