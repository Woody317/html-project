import os
import json
import webbrowser
from pathlib import Path
from flask import Flask, request, jsonify
from flask_cors import CORS
import time
import threading

app = Flask(__name__)
CORS(app)

# 配置数据文件夹
APP_NAME = "P2PChat"
APPDATA_LOCAL = Path(os.getenv('APPDATA')) / APP_NAME
CHAT_DATA_FILE = APPDATA_LOCAL / "chat_data.json"

# 确保文件夹存在
APPDATA_LOCAL.mkdir(parents=True, exist_ok=True)

# 初始化聊天数据文件
if not CHAT_DATA_FILE.exists():
    CHAT_DATA_FILE.write_text(json.dumps({"messages": [], "timestamp": time.time()}, ensure_ascii=False, indent=2))

def read_chat_data():
    """读取聊天记录"""
    try:
        if CHAT_DATA_FILE.exists():
            return json.loads(CHAT_DATA_FILE.read_text(encoding='utf-8'))
        return {"messages": [], "timestamp": time.time()}
    except Exception as e:
        print(f"Error reading chat data: {e}")
        return {"messages": [], "timestamp": time.time()}

def write_chat_data(data):
    """写入聊天记录"""
    try:
        data['timestamp'] = time.time()
        CHAT_DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        return True
    except Exception as e:
        print(f"Error writing chat data: {e}")
        return False

# ===== API 端点 =====

@app.route('/api/chat/load', methods=['GET'])
def load_chat():
    """加载聊天记录"""
    data = read_chat_data()
    return jsonify(data)

@app.route('/api/chat/save', methods=['POST'])
def save_chat():
    """保存聊天记录"""
    try:
        data = request.get_json()
        if write_chat_data(data):
            return jsonify({"success": True, "message": "Chat data saved successfully"})
        else:
            return jsonify({"success": False, "message": "Failed to save chat data"}), 500
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400

@app.route('/api/chat/append', methods=['POST'])
def append_message():
    """添加单条消息"""
    try:
        message = request.get_json()
        data = read_chat_data()
        
        if 'messages' not in data:
            data['messages'] = []
        
        data['messages'].append(message)
        
        if write_chat_data(data):
            return jsonify({"success": True, "message": "Message added successfully", "data": data})
        else:
            return jsonify({"success": False, "message": "Failed to add message"}), 500
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400

@app.route('/api/chat/clear', methods=['POST'])
def clear_chat():
    """清空聊天记录"""
    try:
        data = {"messages": [], "timestamp": time.time()}
        if write_chat_data(data):
            return jsonify({"success": True, "message": "Chat data cleared"})
        else:
            return jsonify({"success": False, "message": "Failed to clear chat data"}), 500
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400

@app.route('/api/status', methods=['GET'])
def status():
    """获取服务状态"""
    return jsonify({
        "status": "running",
        "app_data_path": str(APPDATA_LOCAL),
        "chat_file": str(CHAT_DATA_FILE)
    })

@app.route('/api/settings/path', methods=['GET'])
def get_data_path():
    """获取数据文件夹路径"""
    return jsonify({
        "path": str(APPDATA_LOCAL),
        "exists": APPDATA_LOCAL.exists()
    })

# ===== 启动函数 =====

def open_browser(port=5000):
    """延迟打开浏览器，确保服务器已启动"""
    time.sleep(2)
    html_path = Path(__file__).parent / "index.html"
    
    if html_path.exists():
        webbrowser.open(f"file:///{html_path.absolute()}")
    else:
        webbrowser.open(f"http://localhost:{port}")

if __name__ == '__main__':
    port = 5000
    
    # 在后台线程中打开浏览器
    browser_thread = threading.Thread(target=open_browser, args=(port,), daemon=True)
    browser_thread.start()
    
    print(f"Starting P2P Chat application...")
    print(f"Data folder: {APPDATA_LOCAL}")
    print(f"Chat file: {CHAT_DATA_FILE}")
    print(f"Opening browser at http://localhost:{port}")
    
    # 启动Flask服务器
    app.run(host='localhost', port=port, debug=False, use_reloader=False)
