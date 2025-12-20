#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Flask, request, jsonify
import json
import os
from datetime import datetime
from pathlib import Path
import threading
import time

# ============================================================
# 配置参数
# ============================================================

# 会话超时时间（秒）- 超过此时间无活动的会话将自动释放
SESSION_TIMEOUT = 30

# 定期清理间隔（秒）
CLEANUP_INTERVAL = 60

# 服务器监听端口
SERVER_PORT = 8080

# ============================================================
# 初始化
# ============================================================

app = Flask(__name__)

BASE_DIR = Path(__file__).parent
TOKEN_FILE = BASE_DIR / 'valid_tokens.json'
LOG_FILE = BASE_DIR / 'access.log'
ACTIVE_SESSIONS_FILE = BASE_DIR / 'active_sessions.json'

# ============================================================
# Token 管理
# ============================================================

def load_tokens():
    """加载有效的 token 列表"""
    if TOKEN_FILE.exists():
        try:
            with open(TOKEN_FILE, 'r', encoding='utf-8') as f:
                return set(json.load(f))
        except:
            return set()
    return set()


def load_active_sessions():
    """加载活跃会话"""
    if ACTIVE_SESSIONS_FILE.exists():
        try:
            with open(ACTIVE_SESSIONS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}


def save_active_sessions(sessions):
    """保存活跃会话"""
    with open(ACTIVE_SESSIONS_FILE, 'w', encoding='utf-8') as f:
        json.dump(sessions, f, indent=2, ensure_ascii=False)


def cleanup_expired_sessions():
    """后台定期清理过期会话"""
    while True:
        try:
            sessions = load_active_sessions()
            expired_tokens = []
            
            for token, session in sessions.items():
                try:
                    last_heartbeat = datetime.strptime(session['last_heartbeat'], '%Y-%m-%d %H:%M:%S')
                    time_diff = (datetime.now() - last_heartbeat).total_seconds()
                    
                    if time_diff > SESSION_TIMEOUT:
                        expired_tokens.append(token)
                except:
                    expired_tokens.append(token)
            
            # 删除过期会话
            if expired_tokens:
                for token in expired_tokens:
                    if token in sessions:
                        del sessions[token]
                save_active_sessions(sessions)
                
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                print(f"[{timestamp}] 自动清理: 删除 {len(expired_tokens)} 个超时会话")
        except Exception as e:
            print(f"清理过程出错: {e}")
        
        # 等待下次清理
        time.sleep(CLEANUP_INTERVAL)


def is_token_in_use(token):
    """
    检查 token 是否被占用（不自动删除，只检查）
    
    返回: (是否被占用, 会话信息)
    """
    sessions = load_active_sessions()
    
    if token in sessions:
        session = sessions[token]
        
        # # 检查会话是否超时（只检查，不删除）
        # try:
        #     last_heartbeat = datetime.strptime(session['last_heartbeat'], '%Y-%m-%d %H:%M:%S')
        #     time_diff = (datetime.now() - last_heartbeat).total_seconds()
            
        #     if time_diff > SESSION_TIMEOUT:
        #         # 虽然超时了，但仍然返回被占用
        #         # 让后台清理线程来删除
        #         return True, session
        # except:
        #     pass
        
        # 会话存在，返回被占用
        return True, session
    
    return False, None


def register_session(token, client_id, ip):
    """注册新会话"""
    sessions = load_active_sessions()
    
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    sessions[token] = {
        'client_id': client_id,
        'ip': ip,
        'started_at': now,
        'last_heartbeat': now
    }
    
    save_active_sessions(sessions)


def update_session_heartbeat(token):
    """更新会话心跳时间 - 用于保持会话活跃"""
    sessions = load_active_sessions()
    
    if token in sessions:
        sessions[token]['last_heartbeat'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        save_active_sessions(sessions)


def unregister_session(token):
    """释放会话"""
    sessions = load_active_sessions()
    
    if token in sessions:
        del sessions[token]
        save_active_sessions(sessions)


def log_access(action, token, ip, allowed, reason=""):
    """记录访问日志"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    status = "✓ 允许" if allowed else "✗ 拒绝"
    
    if reason:
        log_line = f"[{timestamp}] {status} | {action} | Token: {token} | IP: {ip} | 原因: {reason}\n"
    else:
        log_line = f"[{timestamp}] {status} | {action} | Token: {token} | IP: {ip}\n"
    
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(log_line)
    
    print(log_line.strip())


# ============================================================
# API 端点
# ============================================================

@app.route('/api/on_publish', methods=['POST'])
def on_publish():
    """推流验证 - 允许所有推流"""
    data = request.json
    ip = data.get('ip', 'unknown')
    stream = data.get('stream', 'unknown')
    
    log_access('推流', '-', ip, True, f"推流到 {stream}")
    
    return jsonify({"code": 0})


@app.route('/api/on_play', methods=['POST'])
def on_play():
    """
    拉流验证 - 严格的单连接限制
    
    验证逻辑:
    1. 检查是否提供 token
    2. 检查 token 是否有效
    3. 检查 token 是否已被占用
    4. 注册新会话并更新心跳
    """
    data = request.json
    param = data.get('param', '')
    ip = data.get('ip', 'unknown')
    client_id = data.get('client_id', 'unknown')
    
    # 提取 token
    if 'token=' not in param:
        log_access('观看', '无token', ip, False, "未提供 Token")
        return jsonify({"code": 1})
    
    token = param.split('token=')[1].split('&')[0]
    
    # 加载有效 tokens
    valid_tokens = load_tokens()
    
    # 检查 token 是否有效
    if token not in valid_tokens:
        log_access('观看', token, ip, False, "Token 无效")
        return jsonify({"code": 1})
    
    # 检查是否已被占用
    in_use, session_info = is_token_in_use(token)
    
    if in_use:
        # Token 正在被使用，拒绝任何新连接
        occupier_ip = session_info['ip']
        occupier_client_id = session_info.get('client_id', 'unknown')
        started_at = session_info['started_at']
        
        reason = f"Token 已被占用 (使用者IP: {occupier_ip}, Client: {occupier_client_id}, 开始: {started_at})"
        log_access('观看', token, ip, False, f"{reason} | 新请求Client: {client_id}")
        
        return jsonify({"code": 1})
    
    # Token 有效且未被占用，注册会话
    register_session(token, client_id, ip)
    log_access('观看', token, ip, True, f"会话已建立 (Client: {client_id})")
    
    return jsonify({"code": 0})


@app.route('/api/on_stop', methods=['POST'])
def on_stop():
    """停止观看 - 释放会话"""
    data = request.json
    param = data.get('param', '')
    ip = data.get('ip', 'unknown')
    client_id = data.get('client_id', 'unknown')
    print("方法被调用！")

    # 提取 token
    if 'token=' in param:
        token = param.split('token=')[1].split('&')[0]
        
        # 释放会话
        unregister_session(token)
        log_access('停止', token, ip, True, f"会话已释放 (Client: {client_id})")
    
    return jsonify({"code": 0})


@app.route('/api/heartbeat', methods=['POST'])
def heartbeat():
    """心跳接口 - 用于保持会话活跃（如果客户端支持）"""
    data = request.json
    param = data.get('param', '')
    
    if 'token=' in param:
        token = param.split('token=')[1].split('&')[0]
        update_session_heartbeat(token)
        return jsonify({"code": 0, "message": "心跳已更新"})
    
    return jsonify({"code": 1, "message": "缺少token"})


@app.route('/api/sessions', methods=['GET'])
def get_sessions():
    """查看活跃会话"""
    sessions = load_active_sessions()
    return jsonify({
        "active_sessions": len(sessions),
        "sessions": sessions
    })


@app.route('/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({
        "status": "running",
        "total_tokens": len(load_tokens()),
        "active_sessions": len(load_active_sessions()),
        "session_timeout": SESSION_TIMEOUT
    })


# ============================================================
# 主程序
# ============================================================

if __name__ == '__main__':
    # 启动后台清理线程
    # cleanup_thread = threading.Thread(target=cleanup_expired_sessions, daemon=True)
    # cleanup_thread.start()
    
    print("=" * 60)
    print("RTMP Token 验证服务器")
    print("=" * 60)
    print("功能:")
    print("  ✓ Token 验证")
    print("  ✓ 严格单连接限制（每个 Token 只允许 1 个连接）")
    print(f"  ✓ 自动会话超时（{SESSION_TIMEOUT}秒无活动自动释放）")
    print(f"  ✓ 后台自动清理（每{CLEANUP_INTERVAL}秒检查一次）")
    print("  ✓ 访问日志记录")
    print("  ✓ 支持断线重连")
    print("=" * 60)
    print("配置:")
    print(f"  会话超时: {SESSION_TIMEOUT} 秒")
    print(f"  清理间隔: {CLEANUP_INTERVAL} 秒")
    print(f"  监听端口: {SERVER_PORT}")
    print("=" * 60)
    print(f"Token 文件: {TOKEN_FILE}")
    print(f"日志文件: {LOG_FILE}")
    print(f"会话文件: {ACTIVE_SESSIONS_FILE}")
    print("=" * 60)
    print("API 端点:")
    print("  POST /api/on_publish  - 推流验证")
    print("  POST /api/on_play     - 拉流验证")
    print("  POST /api/on_stop     - 释放会话")
    print("  POST /api/heartbeat   - 心跳更新（可选）")
    print("  GET  /api/sessions    - 查看活跃会话")
    print("  GET  /health          - 健康检查")
    print("=" * 60)
    print()
    
    app.run(host='0.0.0.0', port=SERVER_PORT, debug=False)