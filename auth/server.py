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

# 服务器监听端口
SERVER_PORT = 8080

# ============================================================
# 初始化
# ============================================================

app = Flask(__name__)

BASE_DIR = Path(__file__).parent
TOKEN_FILE = BASE_DIR / 'valid_tokens.json'
LOG_FILE = BASE_DIR / 'access.log'

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
    拉流验证 - 仅验证Token，不限制连接数
    
    验证逻辑:
    1. 检查是否提供 token
    2. 检查 token 是否有效
    3. 允许连接（不限制连接数）
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
    
    # Token 有效，允许连接（不限制连接数）
    log_access('观看', token, ip, True, f"连接已允许 (Client: {client_id})")
    
    return jsonify({"code": 0})


@app.route('/api/on_stop', methods=['POST'])
def on_stop():
    """停止观看 - 记录断开连接"""
    data = request.json
    param = data.get('param', '')
    ip = data.get('ip', 'unknown')
    client_id = data.get('client_id', 'unknown')

    # 提取 token
    if 'token=' in param:
        token = param.split('token=')[1].split('&')[0]
        log_access('停止', token, ip, True, f"连接已断开 (Client: {client_id})")
    
    return jsonify({"code": 0})


@app.route('/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({
        "status": "running",
        "total_tokens": len(load_tokens())
    })


# ============================================================
# 主程序
# ============================================================

if __name__ == '__main__':
    print("=" * 60)
    print("RTMP Token 验证服务器")
    print("=" * 60)
    print("功能:")
    print("  ✓ Token 验证（必须提供有效Token）")
    print("  ✓ 无连接数限制（一个Token可多人同时观看）")
    print("  ✓ 访问日志记录")
    print("=" * 60)
    print("配置:")
    print(f"  监听端口: {SERVER_PORT}")
    print("=" * 60)
    print(f"Token 文件: {TOKEN_FILE}")
    print(f"日志文件: {LOG_FILE}")
    print("=" * 60)
    print("API 端点:")
    print("  POST /api/on_publish  - 推流验证")
    print("  POST /api/on_play     - 拉流验证（不限制连接数）")
    print("  POST /api/on_stop     - 记录断开连接")
    print("  GET  /health          - 健康检查")
    print("=" * 60)
    print()
    
    app.run(host='0.0.0.0', port=SERVER_PORT, debug=False)