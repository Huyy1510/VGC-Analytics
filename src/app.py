import http.server
import socketserver
import urllib.parse
import urllib.request
import json
import os
import subprocess
import sys
import webbrowser
import threading
import time
import ssl
import re

APP_VERSION = "v2.0.1-beta"
# Get the directory where app.py is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Project root is the parent of SCRIPT_DIR
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

# Ensure results directories exist
os.makedirs(os.path.join(PROJECT_ROOT, "results", "usage"), exist_ok=True)
os.makedirs(os.path.join(PROJECT_ROOT, "results", "compare"), exist_ok=True)
os.makedirs(os.path.join(PROJECT_ROOT, "results", "top8"), exist_ok=True)
os.makedirs(os.path.join(PROJECT_ROOT, "results", "season"), exist_ok=True)

# Create templates dir if it doesn't exist
os.makedirs(os.path.join(SCRIPT_DIR, "templates"), exist_ok=True)

# Disable SSL verification for updates to avoid local network issues
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

def check_update():
    try:
        url = "https://api.github.com/repos/Huyy1510/VGC-Analytics/releases/latest"
        req = urllib.request.Request(
            url, 
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) VGC-Analytics-App"}
        )
        with urllib.request.urlopen(req, context=ssl_context, timeout=4) as response:
            data = json.loads(response.read().decode('utf-8'))
            return {
                "latest_version": data.get("tag_name", "").strip(),
                "url": data.get("html_url", ""),
                "description": data.get("body", "")
            }
    except Exception as e:
        return {"error": str(e)}

class LocalAppHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        query = urllib.parse.parse_qs(parsed_url.query)
        
        # Router
        if path == "/":
            self.serve_template("index.html")
        elif path == "/api/check-update":
            self.handle_check_update()
        elif path == "/api/reports":
            self.handle_get_reports()
        elif path == "/api/generate-usage":
            self.handle_generate_usage(query)
        elif path == "/api/compare":
            self.handle_compare_usage(query)
        elif path == "/api/generate-top8":
            self.handle_generate_top8(query)
        elif path == "/api/compare-season":
            self.handle_compare_season(query)
        elif path.startswith("/results/"):
            # Serve files from results directory
            rel_path = path[len("/results/"):]
            rel_path = rel_path.lstrip("/")
            full_path = os.path.normpath(os.path.join(PROJECT_ROOT, "results", rel_path))
            
            # Security safety check (stay inside results folder)
            expected_prefix = os.path.normpath(os.path.join(PROJECT_ROOT, "results"))
            if full_path.startswith(expected_prefix) and os.path.exists(full_path) and os.path.isfile(full_path):
                self.serve_file(full_path)
            else:
                self.send_error(404, "File not found")
        else:
            # Fallback to default handler
            super().do_GET()
            
    def serve_template(self, filename):
        template_path = os.path.join(SCRIPT_DIR, "templates", filename)
        if not os.path.exists(template_path):
            self.send_error(404, f"Template {filename} not found")
            return
        
        try:
            with open(template_path, "r", encoding="utf-8") as f:
                content = f.read()
            # Replace placeholder for APP_VERSION
            content = content.replace("{{APP_VERSION}}", APP_VERSION)
            
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(content.encode("utf-8"))
        except Exception as e:
            self.send_error(500, f"Error rendering template: {e}")
            
    def serve_file(self, full_path):
        mime_type = "application/octet-stream"
        if full_path.endswith(".html"):
            mime_type = "text/html; charset=utf-8"
        elif full_path.endswith(".css"):
            mime_type = "text/css; charset=utf-8"
        elif full_path.endswith(".js"):
            mime_type = "application/javascript; charset=utf-8"
        elif full_path.endswith(".png"):
            mime_type = "image/png"
        elif full_path.endswith(".json"):
            mime_type = "application/json; charset=utf-8"
            
        try:
            self.send_response(200)
            self.send_header("Content-Type", mime_type)
            self.send_header("Content-Length", str(os.path.getsize(full_path)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            with open(full_path, "rb") as f:
                self.wfile.write(f.read())
        except Exception as e:
            self.send_error(500, f"Error serving file: {e}")
            
    def send_json(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))
        
    def send_error_json(self, message, code=400):
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps({"error": message}).encode("utf-8"))
        
    def handle_check_update(self):
        update_info = check_update()
        latest_version = update_info.get("latest_version", "")
        
        needs_update = False
        if latest_version and latest_version != APP_VERSION:
            needs_update = True
            
        res = {
            "current_version": APP_VERSION,
            "latest_version": latest_version,
            "url": update_info.get("url", ""),
            "needs_update": needs_update
        }
        self.send_json(res)
        
    def handle_get_reports(self):
        reports = []
        
        # 1. Usage HTML reports
        usage_dir = os.path.join(PROJECT_ROOT, "results", "usage")
        if os.path.exists(usage_dir):
            for f in os.listdir(usage_dir):
                if f.endswith(".html"):
                    fp = os.path.join(usage_dir, f)
                    reports.append({
                        "type": "usage",
                        "name": f.replace("_usage.html", "").replace("__", " ").replace("_", " "),
                        "filename": f,
                        "url": f"/results/usage/{f}",
                        "mtime": os.path.getmtime(fp)
                    })
                    
        # 2. Compare HTML reports
        compare_dir = os.path.join(PROJECT_ROOT, "results", "compare")
        if os.path.exists(compare_dir):
            for f in os.listdir(compare_dir):
                if f.endswith(".html"):
                    fp = os.path.join(compare_dir, f)
                    reports.append({
                        "type": "compare",
                        "name": f.replace("_compare.html", "").replace("__", " ").replace("_", " "),
                        "filename": f,
                        "url": f"/results/compare/{f}",
                        "mtime": os.path.getmtime(fp)
                    })
                    
        # 3. Top 8 PNG graphics
        top8_dir = os.path.join(PROJECT_ROOT, "results", "top8")
        if os.path.exists(top8_dir):
            for f in os.listdir(top8_dir):
                if f.endswith(".png"):
                    fp = os.path.join(top8_dir, f)
                    reports.append({
                        "type": "top8",
                        "name": f.replace("_top8.png", "").replace("__", " ").replace("_", " "),
                        "filename": f,
                        "url": f"/results/top8/{f}",
                        "mtime": os.path.getmtime(fp)
                    })
                    
        # 4. Season HTML reports
        season_dir = os.path.join(PROJECT_ROOT, "results", "season")
        if os.path.exists(season_dir):
            for f in os.listdir(season_dir):
                if f.endswith(".html"):
                    fp = os.path.join(season_dir, f)
                    reports.append({
                        "type": "season",
                        "name": f.replace("_season.html", "").replace("__", " ").replace("_", " "),
                        "filename": f,
                        "url": f"/results/season/{f}",
                        "mtime": os.path.getmtime(fp)
                    })
                    
        # 4. JSON files for comparison select
        json_files = []
        if os.path.exists(usage_dir):
            for f in os.listdir(usage_dir):
                if f.endswith(".json"):
                    fp = os.path.join(usage_dir, f)
                    json_files.append({
                        "filename": f,
                        "name": f.replace("_usage.json", "").replace("__", " ").replace("_", " "),
                        "mtime": os.path.getmtime(fp)
                    })
                    
        # Sort files (newest first)
        reports.sort(key=lambda x: x["mtime"], reverse=True)
        json_files.sort(key=lambda x: x["mtime"], reverse=True)
        
        self.send_json({
            "reports": reports,
            "json_reports": json_files
        })
        
    def handle_generate_usage(self, query):
        tournament = query.get("tournament", [""])[0]
        api_key = query.get("api_key", [""])[0]
        
        if not tournament:
            self.send_error_json("Tournament ID or URL is required")
            return
            
        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream')
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('Connection', 'keep-alive')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        # Build command
        cmd = [sys.executable, os.path.join(SCRIPT_DIR, "fetch_usage.py"), tournament]
        if api_key:
            cmd.extend(["-k", api_key])
            
        self.run_and_stream_cmd(cmd, "usage")
        
    def handle_compare_usage(self, query):
        old_file = query.get("old", [""])[0]
        new_file = query.get("new", [""])[0]
        
        if not old_file or not new_file:
            self.send_error_json("Both old and new report files are required")
            return
            
        old_path = os.path.join(PROJECT_ROOT, "results", "usage", old_file)
        new_path = os.path.join(PROJECT_ROOT, "results", "usage", new_file)
        
        if not os.path.exists(old_path) or not os.path.exists(new_path):
            self.send_error_json("Selected report file(s) do not exist")
            return
            
        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream')
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('Connection', 'keep-alive')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        cmd = [sys.executable, os.path.join(SCRIPT_DIR, "compare_usage.py"), old_path, new_path]
        self.run_and_stream_cmd(cmd, "compare")
        
    def handle_generate_top8(self, query):
        tournament = query.get("tournament", [""])[0]
        
        if not tournament:
            self.send_error_json("Tournament ID or URL is required")
            return
            
        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream')
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('Connection', 'keep-alive')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        cmd = [sys.executable, os.path.join(SCRIPT_DIR, "generate_top8.py"), tournament]
        self.run_and_stream_cmd(cmd, "top8")
        
    def handle_compare_season(self, query):
        files_param = query.get("files", [])
        if len(files_param) == 1 and "," in files_param[0]:
            files_list = [f.strip() for f in files_param[0].split(",") if f.strip()]
        else:
            files_list = [f.strip() for f in files_param if f.strip()]
            
        season_name = query.get("name", ["VGC Season"])[0]
        
        if not files_list:
            self.send_error_json("No report files selected for season analysis")
            return
            
        absolute_paths = []
        for filename in files_list:
            path = os.path.join(PROJECT_ROOT, "results", "usage", filename)
            if os.path.exists(path):
                absolute_paths.append(path)
                
        if not absolute_paths:
            self.send_error_json("None of the selected report files exist")
            return
            
        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream')
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('Connection', 'keep-alive')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        cmd = [sys.executable, os.path.join(SCRIPT_DIR, "compare_season.py")]
        cmd.extend(absolute_paths)
        cmd.extend(["--name", season_name])
        
        self.run_and_stream_cmd(cmd, "season")
        
    def run_and_stream_cmd(self, cmd, cmd_type):
        try:
            env = os.environ.copy()
            env["PYTHONUNBUFFERED"] = "1"
            
            # Start process
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                cwd=PROJECT_ROOT,
                env=env
            )
            
            while True:
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                if line:
                    data_str = f"data: {json.dumps({'log': line.strip()})}\n\n"
                    self.wfile.write(data_str.encode('utf-8'))
                    self.wfile.flush()
                    
            return_code = process.poll()
            done_payload = {
                "done": True,
                "success": return_code == 0,
                "code": return_code
            }
            
            if return_code == 0:
                latest_file = self.get_latest_report(cmd_type)
                if latest_file:
                    done_payload["report_url"] = f"/results/{latest_file}"
                    
            done_str = f"data: {json.dumps(done_payload)}\n\n"
            self.wfile.write(done_str.encode('utf-8'))
            self.wfile.flush()
            
        except Exception as e:
            err_payload = {"done": True, "success": False, "error": str(e)}
            err_str = f"data: {json.dumps(err_payload)}\n\n"
            self.wfile.write(err_str.encode('utf-8'))
            self.wfile.flush()
            
    def get_latest_report(self, cmd_type):
        # Scan folder for latest file
        folder = os.path.join(PROJECT_ROOT, "results", cmd_type)
        if not os.path.exists(folder):
            return None
            
        extension = ".png" if cmd_type == "top8" else ".html"
        candidates = []
        for f in os.listdir(folder):
            if f.endswith(extension):
                fp = os.path.join(folder, f)
                candidates.append((os.path.getmtime(fp), f"{cmd_type}/{f}"))
                
        if candidates:
            candidates.sort(reverse=True)
            return candidates[0][1]
        return None

def find_free_port(start_port=5000):
    import socket
    port = start_port
    while True:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('127.0.0.1', port))
                return port
        except OSError:
            port += 1

def open_browser(port):
    # Give the server a small moment to spin up
    time.sleep(0.8)
    webbrowser.open(f"http://127.0.0.1:{port}")

def main():
    port = find_free_port(5000)
    
    # Start browser opener thread
    threading.Thread(target=open_browser, args=(port,), daemon=True).start()
    
    # Start web server
    server = socketserver.TCPServer(('127.0.0.1', port), LocalAppHandler)
    print(f"==================================================")
    print(f"  VGC-Analytics Desktop App v{APP_VERSION}")
    print(f"  Server is running at: http://127.0.0.1:{port}")
    print(f"  Press Ctrl+C to stop the application")
    print(f"==================================================")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping VGC-Analytics server...")
        server.shutdown()

if __name__ == "__main__":
    main()
