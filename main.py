import os
import json
import webbrowser
import subprocess
import string
import random
import socket
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import time
import threading
from datetime import datetime

app = Flask(__name__, static_folder=None)
CORS(app)

# 配置数据文件夹
APP_NAME = "P2PChat"
APPDATA_LOCAL = Path(os.getenv('APPDATA')) / APP_NAME
CHAT_DATA_FILE = APPDATA_LOCAL / "chat_data.json"
CACHE_DIR = Path(__file__).parent / "cache"

# 确保文件夹存在
APPDATA_LOCAL.mkdir(parents=True, exist_ok=True)
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# 获取本地设备序列号
LOCAL_DEVICE_ID = None

def get_device_serial_number():
    """获取 Windows 设备序列号"""
    try:
        result = subprocess.run(
            ["powershell", "-Command", "Get-WmiObject -Class Win32_BIOS | Select-Object -ExpandProperty SerialNumber"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            serial = result.stdout.strip()
            if serial and serial.lower() != "systemproduct":
                return serial
    except Exception as e:
        print(f"Error getting device serial: {e}")
    return None

LOCAL_DEVICE_ID = get_device_serial_number() or "unknown_device"
print(f"Device Serial: {LOCAL_DEVICE_ID}")

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

def generate_verification_code(length=2):
    """生成随机验证码"""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def save_local_message(remote_device_id, message, sender_id, verification_code):
    """保存消息到本地缓存文件"""
    try:
        # 创建联系人文件夹
        contact_dir = CACHE_DIR / remote_device_id
        contact_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建年-月文件夹
        now = datetime.now()
        year_month = now.strftime("%Y-%m")
        month_dir = contact_dir / year_month
        month_dir.mkdir(parents=True, exist_ok=True)
        
        # 获取当天的 chatlog 文件
        day = now.strftime("%d")
        chatlog_file = month_dir / day
        
        # 读取现有数据或创建新的
        if chatlog_file.exists():
            data = json.loads(chatlog_file.read_text(encoding='utf-8'))
        else:
            data = {
                "local_device_id": LOCAL_DEVICE_ID,
                "remote_device_id": remote_device_id,
                "created_at": now.isoformat(),
                "messages": []
            }
        
        # 添加消息
        data["messages"].append({
            "from": sender_id,
            "text": message,
            "verification_code": verification_code,
            "timestamp": now.isoformat()
        })
        
        # 保存文件
        chatlog_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        return True
    except Exception as e:
        print(f"Error saving local message: {e}")
        return False

# ===== API 端点 =====

@app.route('/')
def serve_index():
    """提供 index.html 文件"""
    html_path = Path(__file__).parent / "index.html"
    if html_path.exists():
        return send_from_directory(Path(__file__).parent, "index.html")
    return jsonify({"error": "index.html not found"}), 404

@app.route('/api/device/serial-number', methods=['GET'])
def get_serial_number():
    """获取本地设备序列号"""
    return jsonify({
        "device_id": LOCAL_DEVICE_ID,
        "success": True
    })

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

@app.route('/api/message/send', methods=['POST'])
def send_message():
    """发送消息 - 生成验证码并保存到本地"""
    try:
        data = request.get_json()
        remote_device_id = data.get('remote_device_id')
        message_text = data.get('message')
        
        if not remote_device_id or not message_text:
            return jsonify({"success": False, "message": "Missing parameters"}), 400
        
        # 生成验证码
        verification_code = generate_verification_code(2)
        
        # 保存到本地
        save_local_message(remote_device_id, message_text, LOCAL_DEVICE_ID, verification_code)
        
        # 返回消息+验证码给发送方
        return jsonify({
            "success": True,
            "message": message_text,
            "verification_code": verification_code,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400

@app.route('/api/chat/contacts', methods=['GET'])
def get_contacts():
    """获取所有联系人列表（cache 第一层目录）"""
    try:
        contacts = []
        if CACHE_DIR.exists():
            for item in CACHE_DIR.iterdir():
                if item.is_dir():
                    contacts.append({
                        "device_id": item.name,
                        "path": str(item)
                    })
        return jsonify({
            "success": True,
            "contacts": contacts
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400

@app.route('/api/chat/history/<remote_device_id>', methods=['GET'])
def get_chat_history(remote_device_id):
    """获取指定联系人的聊天记录"""
    try:
        date_str = request.args.get('date')  # 格式: 2026-01-03
        
        if not date_str:
            date_str = datetime.now().strftime("%Y-%m-%d")
        
        # 解析日期
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        year_month = date_obj.strftime("%Y-%m")
        day = date_obj.strftime("%d")
        
        # 构建路径
        chatlog_file = CACHE_DIR / remote_device_id / year_month / day
        
        if not chatlog_file.exists():
            return jsonify({
                "success": True,
                "messages": [],
                "date": date_str
            })
        
        # 读取聊天记录
        data = json.loads(chatlog_file.read_text(encoding='utf-8'))
        
        return jsonify({
            "success": True,
            "messages": data.get("messages", []),
            "date": date_str,
            "remote_device_id": remote_device_id
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400
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

def find_available_port(start_port=5000, max_attempts=10):
    """查找可用的端口"""
    for port in range(start_port, start_port + max_attempts):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind(('localhost', port))
            sock.close()
            return port
        except OSError:
            continue
    return start_port

def open_browser(port=5000):
    """延迟打开浏览器，确保服务器已启动"""
    time.sleep(2)
    webbrowser.open(f"http://localhost:{port}")

if __name__ == '__main__':
    port = find_available_port(5000)
    
    # 在后台线程中打开浏览器
    browser_thread = threading.Thread(target=open_browser, args=(port,), daemon=True)
    browser_thread.start()
    
    print(f"Starting P2P Chat application...")
    print(f"Device Serial: {LOCAL_DEVICE_ID}")
    print(f"Cache folder: {CACHE_DIR}")
    print(f"Opening browser at http://localhost:{port}")
    
    # 启动 Flask 服务器
    app.run(host='localhost', port=port, debug=False, use_reloader=False, threaded=True)
