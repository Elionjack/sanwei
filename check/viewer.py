import json
import os
import socket
import shutil
import webbrowser
import http.server
import socketserver
import threading
from pathlib import Path
from functools import partial


class TilesetViewer:
    def __init__(self):
        self.server = None
        self.port = None

    def extract_camera_position(self, tileset_path):
        try:
            with open(tileset_path, 'r', encoding='utf-8') as f:
                tileset = json.load(f)

            if "root" in tileset and "boundingVolume" in tileset["root"]:
                bv = tileset["root"]["boundingVolume"]
                if "region" in bv:
                    region = bv["region"]
                    west, south, east, north, min_height, max_height = region
                    
                    import math
                    center_lon = (west + east) / 2
                    center_lat = (south + north) / 2
                    avg_height = (min_height + max_height) / 2
                    
                    center_lon_deg = math.degrees(center_lon)
                    center_lat_deg = math.degrees(center_lat)
                    camera_height = max(avg_height + 200, 300)
                    
                    return {
                        "longitude": center_lon_deg,
                        "latitude": center_lat_deg,
                        "height": camera_height
                    }
        
        except Exception as e:
            print(f"Failed to extract camera position: {e}")

        return {
            "longitude": 114.30,
            "latitude": 30.675,
            "height": 500
        }

    def copy_cesium_to_output(self, output_dir):
        output_path = Path(output_dir)
        cesium_source = Path(__file__).parent / "cesium" / "Build" / "Cesium"
        cesium_dest = output_path / "cesium"
        
        if cesium_dest.exists():
            shutil.rmtree(cesium_dest)
        
        shutil.copytree(cesium_source, cesium_dest)
        print(f"Copied CesiumJS to {cesium_dest}")

    def generate_html(self, output_dir, output_html_path=None):
        output_path = Path(output_dir)
        tileset_path = output_path / "tileset.json"
        
        if not tileset_path.exists():
            print(f"Error: tileset.json not found in {output_dir}")
            return None

        camera_pos = self.extract_camera_position(tileset_path)

        template_path = Path(__file__).parent / "viewer_template.html"
        with open(template_path, 'r', encoding='utf-8') as f:
            html_content = f.read()

        html_content = html_content.replace("{{CAMERA_POS}}", json.dumps(camera_pos))

        if output_html_path is None:
            output_html_path = output_path / "viewer.html"
        
        with open(output_html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return str(output_html_path)

    def _find_free_port(self, start_port=8000):
        for port in range(start_port, start_port + 100):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                if s.connect_ex(('localhost', port)) != 0:
                    return port
        return start_port

    def start_server(self, output_dir, port=None):
        output_path = Path(output_dir)
        
        if not output_path.exists():
            print(f"Error: Output directory does not exist: {output_dir}")
            return None

        self.copy_cesium_to_output(output_dir)
        self.generate_html(output_dir)

        if port is None:
            self.port = self._find_free_port()
        else:
            self.port = port

        Handler = partial(http.server.SimpleHTTPRequestHandler, directory=str(output_path))
        
        try:
            self.server = socketserver.TCPServer(('0.0.0.0', self.port), Handler)
            print(f"\nStarting HTTP server on port {self.port}...")
            print(f"Viewer URL: http://localhost:{self.port}/viewer.html")
            print(f"Tileset URL: http://localhost:{self.port}/tileset.json")
            print("Press Ctrl+C to stop the server")
            
            server_thread = threading.Thread(target=self.server.serve_forever)
            server_thread.daemon = True
            server_thread.start()
            
            webbrowser.open(f'http://localhost:{self.port}/viewer.html')
            
            try:
                while True:
                    import time
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\nStopping server...")
                self.server.shutdown()
                
        except OSError as e:
            if e.errno == 48:
                print(f"Port {self.port} is already in use. Trying another port...")
                return self.start_server(output_dir, port=self._find_free_port(self.port + 1))
            else:
                print(f"Failed to start server: {e}")
                return None

        return f"http://localhost:{self.port}/viewer.html"
