import http.server
import socketserver
import os

# ==================== 在这里分开指定你的【三个】目录 ====================
# 1. index.html 网页文件所在的目录
HTML_DIR = r"E:\learning\whch_sanwei\check"

# 2. Cesium 库所在的目录 (该目录下应该直接有 Widgets、Cesium.js 等)
CESIUM_DIR = r"E:\learning\whch_sanwei\check\Cesium"

# 3. 3D 模型数据所在的目录 (该目录下有 Data 文件夹和 json 文件)
DATA_DIR = r"E:\learning\data\output\OSG_python"

PORT = 8000


# ===================================================================

class ThreeDirectoryHandler(http.server.SimpleHTTPRequestHandler):
    def translate_path(self, path):
        # 1. 路由拦截：如果是请求 Cesium 库文件（URL 以 /Cesium/ 开头）
        if path.startswith('/Cesium/'):
            relative_path = path[len('/Cesium/'):]
            return os.path.join(CESIUM_DIR, relative_path)

        # 2. 路由拦截：如果是请求 3D 模型瓦片（URL 以 /data_tiles/ 开头）
        if path.startswith('/data_tiles/'):
            relative_path = path[len('/data_tiles/'):]
            return os.path.join(DATA_DIR, relative_path)

        # 3. 默认处理：其他普通请求（如 index.html 等）都去网页目录下寻找
        return os.path.join(HTML_DIR, path.lstrip('/'))

    def end_headers(self):
        # 允许跨域（Cesium 加载本地瓦片必备）
        self.send_header('Access-Control-Allow-Origin', '*')
        super().end_headers()


if __name__ == '__main__':
    # 强制将服务器的工作目录指向网页 HTML 目录
    os.chdir(HTML_DIR)

    with socketserver.TCPServer(("", PORT), ThreeDirectoryHandler) as httpd:
        print("====== 定制三目录 3D Tiles 开发服务器已启动 ======")
        print(f" 1. 网页 HTML 目录 : {HTML_DIR}")
        print(f" 2. Cesium 库目录  : {CESIUM_DIR}")
        print(f" 3. 3D 模型数据目录 : {DATA_DIR}")
        print(f" 浏览器访问地址   : http://localhost:{PORT}/index.html")
        print("==================================================")
        print("提示: 按 Ctrl+C 可以关闭服务器")
        httpd.serve_forever()