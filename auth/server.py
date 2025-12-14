#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Flask, request, jsonify
import json
import os
from datetime import datetime
from pathlib import Path

app = Flask(__name__)

BASE_DIR = Path(__file__).parent
TOKEN_FILE = BASE_DIR / 'valid_tokens.json'
LOG_FILE = BASE_DIR / 'access.log'
ACTIVE_SESSIONS_FILE = BASE_DIR / 'active_sessions.json'

# ============================================================
# Token manage
# ============================================================

def load_tokens():
    if TOKEN_FILE.exists():
        try:
            with open(TOKEN_FILE, 'r', encoding='utf-8') as f:
                return set(json.load(f))
        except:
            return set()
    return set()


def load_active_sessions():

    if ACTIVE_SESSIONS_FILE.exists():
        try:
            with open(ACTIVE_SESSIONS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_active_sessions(sessions):

    with open(ACTIVE_SESSIONS_FILE, 'w', encoding='utf-8') as f:
        json.dump(sessions, f, indent=2, ensure_ascii=False)

def is_token_in_use(token, current_client_id):

    sessions = load_active_sessions()
    
    if token in sessions:
        session = sessions[token]
        # 如果是同一个客户端（重连），允许
        if session['client_id'] == current_client_id:
            return False, None
        # 不同客户端，拒绝
        else:
            return True, session
    
    return False, None

def register_session(token, client_id, ip):
    sessions = load_active_sessions()
    
    sessions[token] = {
        'client_id': client_id,
        'ip': ip,
        'started_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    save_active_sessions(sessions)

def unregister_session(token):
    sessions = load_active_sessions()
    
    if token in sessions:
        del sessions[token]
        save_active_sessions(sessions)

def log_access(action, token, ip, allowed, reason=""):

    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    status = "✓ allow" if allowed else "✗ decline"
    
    if reason:
        log_line = f"[{timestamp}] {status} | {action} | Token: {token} | IP: {ip} | reason: {reason}\n"
    else:
        log_line = f"[{timestamp}] {status} | {action} | Token: {token} | IP: {ip}\n"
    
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(log_line)
    
    print(log_line.strip())


@app.route('/api/on_publish', methods=['POST'])
def on_publish():

    data = request.json
    ip = data.get('ip', 'unknown')
    stream = data.get('stream', 'unknown')
    
    log_access('publish', '-', ip, True, f"推流到 {stream}")
    
    return jsonify({"code": 0})

@app.route('/api/on_play', methods=['POST'])
def on_play():

    data = request.json
    param = data.get('param', '')
    ip = data.get('ip', 'unknown')
    client_id = data.get('client_id', 'unknown')
    
    # 提取 token
    if 'token=' not in param:
        log_access('play', '无token', ip, False, "未提供 Token")
        return jsonify({"code": 1})
    
    token = param.split('token=')[1].split('&')[0]
    
    # 加载有效 tokens
    valid_tokens = load_tokens()
    
    # 检查 token 是否有效
    if token not in valid_tokens:
        log_access('play', token, ip, False, "Token 无效")
        return jsonify({"code": 1})
    
    # 检查是否已被占用
    in_use, session_info = is_token_in_use(token, client_id)
    
    if in_use:
        # Token 正在被其他人使用
        occupier_ip = session_info['ip']
        started_at = session_info['started_at']
        reason = f"Token 已被占用 (IP: {occupier_ip}, 开始时间: {started_at})"
        
        log_access('play', token, ip, False, reason)
        return jsonify({"code": 1})
    
    # Token 有效且未被占用，注册会话
    register_session(token, client_id, ip)
    log_access('play', token, ip, True, "会话已建立")
    
    return jsonify({"code": 0})

@app.route('/api/on_stop', methods=['POST'])
def on_stop():

    data = request.json
    param = data.get('param', '')
    ip = data.get('ip', 'unknown')
    
    # 提取 token
    if 'token=' in param:
        token = param.split('token=')[1].split('&')[0]
        
        # 释放会话
        unregister_session(token)
        log_access('stop', token, ip, True, "会话已释放")
    
    return jsonify({"code": 0})

@app.route('/api/sessions', methods=['GET'])
def get_sessions():

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
        "active_sessions": len(load_active_sessions())
    })

if __name__ == '__main__':
    print("=" * 60)
    print("RTMP Token 验证服务器")
    print("=" * 60)
    print("功能:")
    print("  ✓ Token 验证")
    print("  ✓ 单用户限制（每个 Token 同时只允许 1 人观看）")
    print("  ✓ 访问日志记录")
    print("  ✓ 自动会话管理")
    print("=" * 60)
    print(f"Token 文件: {TOKEN_FILE}")
    print(f"日志文件: {LOG_FILE}")
    print(f"会话文件: {ACTIVE_SESSIONS_FILE}")
    print("=" * 60)
    print("监听端口: 8080")
    print("=" * 60)
    print("API 端点:")
    print("  POST /api/on_publish  - 推流验证")
    print("  POST /api/on_play     - 拉流验证")
    print("  POST /api/on_stop     - 释放会话")
    print("  GET  /api/sessions    - 查看活跃会话")
    print("  GET  /health          - 健康检查")
    print("=" * 60)
    print()
    
    app.run(host='0.0.0.0', port=8080, debug=False)
