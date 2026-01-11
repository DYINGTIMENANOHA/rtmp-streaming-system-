#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import subprocess
import time
import json
import secrets
from pathlib import Path
import platform
import sys
from datetime import datetime

class StreamingLauncher:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("RTMP 直播系统")
        self.root.geometry("950x750")
        
        self.root_dir = Path(__file__).parent
        self.is_windows = platform.system() == "Windows"
        self.token_file = self.root_dir / "auth" / "valid_tokens.json"
        self.config_file = self.root_dir / "user_config.json"
        
        self.processes = []
        self.is_running = False
        
        self._create_widgets()
        self._load_config()
        self._refresh_token_list()
        
        # 启动自动刷新
        self._auto_refresh()
        
    def _create_widgets(self):
        # 创建 Notebook（标签页）
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        # 标签页 1: 配置
        config_tab = ttk.Frame(notebook)
        notebook.add(config_tab, text="⚙️ 配置")
        
        # 标签页 2: Token 管理
        token_tab = ttk.Frame(notebook)
        notebook.add(token_tab, text="🔑 Token 管理")
        
        # 标签页 3: 运行日志
        log_tab = ttk.Frame(notebook)
        notebook.add(log_tab, text="📋 运行日志")
        
        # === 配置标签页 ===
        self._create_config_tab(config_tab)
        
        # === Token 管理标签页 ===
        self._create_token_tab(token_tab)
        
        # === 日志标签页 ===
        self._create_log_tab(log_tab)
        
        # 状态栏
        self.status_label = ttk.Label(
            self.root, 
            text="准备就绪", 
            relief=tk.SUNKEN, 
            anchor="w"
        )
        self.status_label.pack(fill="x", side="bottom")
    
    def _create_config_tab(self, parent):
        """创建配置标签页"""
        # 标题
        title = ttk.Label(
            parent, 
            text="系统配置", 
            font=("Arial", 16, "bold")
        )
        title.pack(pady=15)
        
        info = ttk.Label(
            parent,
            text="请填写以下信息用于生成观看链接（与 srs/conf/live.conf 和 frpc/frpc.toml 保持一致）",
            font=("Arial", 9),
            foreground="gray"
        )
        info.pack()
        
        # 配置表单
        config_frame = ttk.LabelFrame(parent, text="配置信息", padding=20)
        config_frame.pack(fill="x", padx=20, pady=15)
        
        # FRP 服务器地址
        row = 0
        ttk.Label(config_frame, text="FRP 服务器地址:", font=("Arial", 10)).grid(
            row=row, column=0, sticky="w", pady=8
        )
        self.frp_server = ttk.Entry(config_frame, width=40, font=("Arial", 10))
        self.frp_server.grid(row=row, column=1, pady=8, padx=10)
        ttk.Label(config_frame, text="你的 frp网络地址", foreground="gray").grid(
            row=row, column=2, sticky="w"
        )
        
        # 云端暴露端口
        row += 1
        ttk.Label(config_frame, text="云端暴露端口:", font=("Arial", 10, "bold")).grid(
            row=row, column=0, sticky="w", pady=8
        )
        self.remote_port = ttk.Entry(config_frame, width=40, font=("Arial", 10))
        self.remote_port.grid(row=row, column=1, pady=8, padx=10)
        ttk.Label(config_frame, text="frpc.toml 中的 remotePort", foreground="blue").grid(
            row=row, column=2, sticky="w"
        )
        
        # 本地 RTMP 端口
        row += 1
        ttk.Label(config_frame, text="本地 RTMP 端口:", font=("Arial", 10)).grid(
            row=row, column=0, sticky="w", pady=8
        )
        self.local_port = ttk.Entry(config_frame, width=40, font=("Arial", 10))
        self.local_port.grid(row=row, column=1, pady=8, padx=10)
        self.local_port.insert(0, "19350")
        ttk.Label(config_frame, text="live.conf 中的 listen", foreground="gray").grid(
            row=row, column=2, sticky="w"
        )
        
        # 应用名称
        row += 1
        ttk.Label(config_frame, text="应用名称:", font=("Arial", 10)).grid(
            row=row, column=0, sticky="w", pady=8
        )
        self.app_name = ttk.Entry(config_frame, width=40, font=("Arial", 10))
        self.app_name.grid(row=row, column=1, pady=8, padx=10)
        self.app_name.insert(0, "live")
        ttk.Label(config_frame, text="推流 URL 的 app 部分", foreground="gray").grid(
            row=row, column=2, sticky="w"
        )
        
        # 流名称
        row += 1
        ttk.Label(config_frame, text="流名称:", font=("Arial", 10)).grid(
            row=row, column=0, sticky="w", pady=8
        )
        self.stream_name = ttk.Entry(config_frame, width=40, font=("Arial", 10))
        self.stream_name.grid(row=row, column=1, pady=8, padx=10)
        self.stream_name.insert(0, "stream")
        ttk.Label(config_frame, text="推流 URL 的 stream 部分", foreground="gray").grid(
            row=row, column=2, sticky="w"
        )
        
        # 保存按钮
        row += 1
        ttk.Button(
            config_frame, 
            text="💾 保存配置", 
            command=self._save_config,
            width=20
        ).grid(row=row, column=1, pady=15)
        
        # 控制按钮
        control_frame = ttk.Frame(parent)
        control_frame.pack(pady=20)
        
        self.start_btn = ttk.Button(
            control_frame, 
            text="▶ 启动所有服务", 
            command=self._start_system,
            width=25
        )
        self.start_btn.pack(side="left", padx=10)
        
        self.stop_btn = ttk.Button(
            control_frame, 
            text="⏹ 停止所有服务", 
            command=self._stop_system,
            width=25,
            state="disabled"
        )
        self.stop_btn.pack(side="left", padx=10)
        
        # OBS 配置提示
        obs_frame = ttk.LabelFrame(parent, text="📺 OBS 推流配置", padding=15)
        obs_frame.pack(fill="x", padx=20, pady=10)
        
        self.obs_config_text = scrolledtext.ScrolledText(
            obs_frame,
            height=6,
            wrap=tk.WORD,
            font=("Courier New", 9),
            state="disabled"
        )
        self.obs_config_text.pack(fill="x")
        
        self._update_obs_config_display()
    
    def _create_token_tab(self, parent):
        # 标题
        title = ttk.Label(
            parent, 
            text="观看 Token 管理", 
            font=("Arial", 16, "bold")
        )
        title.pack(pady=15)
        
        subtitle = ttk.Label(
            parent,
            text="✓ 每个 Token 可供多人同时观看 | 自动刷新:每5秒",
            font=("Arial", 10),
            foreground="green"
        )
        subtitle.pack()
        
        # Token 管理区域
        token_management_frame = ttk.Frame(parent)
        token_management_frame.pack(fill="both", padx=20, pady=15, expand=True)
        
        # Token 列表
        list_frame = ttk.Frame(token_management_frame)
        list_frame.pack(side="left", fill="both", expand=True)
        
        # 列标题
        columns = ("token",)
        self.token_tree = ttk.Treeview(
            list_frame, 
            columns=columns, 
            show="tree headings",
            height=12
        )
        
        self.token_tree.heading("#0", text="序号")
        self.token_tree.heading("token", text="Token")
        
        self.token_tree.column("#0", width=50, anchor="center")
        self.token_tree.column("token", width=400)
        
        # 滚动条
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.token_tree.yview)
        self.token_tree.configure(yscrollcommand=scrollbar.set)
        
        self.token_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 操作按钮
        button_frame = ttk.Frame(token_management_frame)
        button_frame.pack(side="right", fill="y", padx=(15, 0))
        
        ttk.Button(
            button_frame,
            text="🔑 生成新 Token",
            command=self._generate_token,
            width=18
        ).pack(pady=5)
        
        ttk.Button(
            button_frame,
            text="📋 复制 Token",
            command=self._copy_token,
            width=18
        ).pack(pady=5)
        
        ttk.Button(
            button_frame,
            text="🔗 复制观看链接",
            command=self._copy_watch_url,
            width=18
        ).pack(pady=5)
        
        ttk.Button(
            button_frame,
            text="🗑️ 删除 Token",
            command=self._delete_token,
            width=18
        ).pack(pady=5)
        
        ttk.Separator(button_frame, orient="horizontal").pack(fill="x", pady=10)
        
        ttk.Button(
            button_frame,
            text="🔄 刷新列表",
            command=self._refresh_token_list,
            width=18
        ).pack(pady=5)
        
        # Token 详情显示
        detail_frame = ttk.LabelFrame(parent, text="Token 详情", padding=10)
        detail_frame.pack(fill="x", padx=20, pady=10)
        
        self.detail_text = scrolledtext.ScrolledText(
            detail_frame,
            height=5,
            wrap=tk.WORD,
            font=("Courier New", 9),
            state="disabled"
        )
        self.detail_text.pack(fill="x")
        
        # 绑定选择事件
        self.token_tree.bind("<<TreeviewSelect>>", self._on_token_select)
    
    def _create_log_tab(self, parent):
        """创建日志标签页"""
        self.log_text = scrolledtext.ScrolledText(
            parent, 
            wrap=tk.WORD,
            font=("Consolas", 9)
        )
        self.log_text.pack(fill="both", expand=True, padx=10, pady=10)
    
    def _log(self, message):
        """添加日志"""
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
    
    def _load_config(self):
        """加载配置"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                self.frp_server.insert(0, config.get('frp_server', ''))
                self.remote_port.insert(0, config.get('remote_port', ''))
                
                local_port = config.get('local_port', '19350')
                self.local_port.delete(0, tk.END)
                self.local_port.insert(0, local_port)
                
                app_name = config.get('app_name', 'live')
                self.app_name.delete(0, tk.END)
                self.app_name.insert(0, app_name)
                
                stream_name = config.get('stream_name', 'stream')
                self.stream_name.delete(0, tk.END)
                self.stream_name.insert(0, stream_name)
                
                self._update_obs_config_display()
                
            except Exception as e:
                self._log(f"加载配置失败: {e}")
    
    def _save_config(self):
        config = {
            'frp_server': self.frp_server.get().strip(),
            'remote_port': self.remote_port.get().strip(),
            'local_port': self.local_port.get().strip(),
            'app_name': self.app_name.get().strip(),
            'stream_name': self.stream_name.get().strip()
        }
        
        # 验证
        if not all([config['frp_server'], config['remote_port']]):
            messagebox.showerror("错误", "请填写 FRP 服务器地址和云端端口")
            return
        
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        self._update_obs_config_display()
        messagebox.showinfo("成功", "配置已保存")
        self.status_label.config(text="✓ 配置已保存")
        self._log("配置已保存")
    
    def _update_obs_config_display(self):
        """更新 OBS 配置显示"""
        local_port = self.local_port.get().strip() or "19350"
        app_name = self.app_name.get().strip() or "live"
        stream_name = self.stream_name.get().strip() or "stream"
        
        obs_text = f"""OBS 推流配置:

服务器: rtmp://127.0.0.1:{local_port}/{app_name}
推流密钥: {stream_name}

配置步骤:
1. OBS → 设置 → 推流
2. 服务: 自定义
3. 服务器: 复制上面的服务器地址
4. 推流密钥: 复制上面的推流密钥
"""
        
        self.obs_config_text.config(state="normal")
        self.obs_config_text.delete(1.0, tk.END)
        self.obs_config_text.insert(1.0, obs_text)
        self.obs_config_text.config(state="disabled")
    
    def _get_watch_url(self, token):
        """生成观看地址"""
        frp_server = self.frp_server.get().strip() or "YOUR-SERVER"
        remote_port = self.remote_port.get().strip() or "PORT"
        app_name = self.app_name.get().strip() or "live"
        stream_name = self.stream_name.get().strip() or "stream"
        
        return f"rtmp://{frp_server}:{remote_port}/{app_name}/{stream_name}?token={token}"

    def _load_tokens(self):
        """加载 Token 列表"""
        if not self.token_file.exists():
            return []
        
        try:
            with open(self.token_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    
    def _save_tokens(self, tokens):
        """保存 Token 列表"""
        self.token_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.token_file, 'w', encoding='utf-8') as f:
            json.dump(tokens, f, indent=2, ensure_ascii=False)
    
    def _refresh_token_list(self):
        """刷新 Token 列表显示"""
        # 保存当前选中的项
        current_selection = None
        selection = self.token_tree.selection()
        if selection:
            item = self.token_tree.item(selection[0])
            current_selection = item['values'][0] if item['values'] else None
        
        # 清空列表
        for item in self.token_tree.get_children():
            self.token_tree.delete(item)
        
        tokens = self._load_tokens()
        
        # 重新填充列表
        for i, token in enumerate(tokens, 1):
            item_id = self.token_tree.insert(
                "", 
                "end", 
                text=str(i),
                values=(token,),
                tags=("token",)
            )
            
            # 恢复之前的选中状态
            if current_selection and token == current_selection:
                self.token_tree.selection_set(item_id)
                self.token_tree.focus(item_id)
                self.token_tree.see(item_id)
        
        if not tokens:
            self._update_detail("暂无 Token,点击'生成新 Token'创建")
    
    def _auto_refresh(self):
        """每5秒自动刷新一次 token 状态"""
        try:
            # 只在 token_tree 存在时刷新
            if hasattr(self, 'token_tree') and self.token_tree.winfo_exists():
                self._refresh_token_list()
        except:
            pass
        
        # 5秒后再次执行
        self.root.after(5000, self._auto_refresh)
    
    def _on_token_select(self, event):
        """Token 选择事件"""
        selection = self.token_tree.selection()
        if not selection:
            return
        
        item = self.token_tree.item(selection[0])
        token = item['values'][0]
        
        watch_url = self._get_watch_url(token)
        
        detail = f"""Token: {token}

观看地址:
{watch_url}

提示: 此 Token 支持多人同时观看
分享此链接给观看者,在 VLC 中打开网络串流即可观看"""
        
        self._update_detail(detail)
    
    def _update_detail(self, text):
        """更新详情显示"""
        self.detail_text.config(state="normal")
        self.detail_text.delete(1.0, tk.END)
        self.detail_text.insert(1.0, text)
        self.detail_text.config(state="disabled")
    
    def _generate_token(self):
        """生成新 Token"""
        new_token = f"token_{secrets.token_hex(8)}"
        
        tokens = self._load_tokens()
        tokens.append(new_token)
        self._save_tokens(tokens)
        
        self._refresh_token_list()
        self._log(f"已生成新 Token: {new_token}")
        
        # 自动选中新生成的 token
        children = self.token_tree.get_children()
        if children:
            last_item = children[-1]
            self.token_tree.selection_set(last_item)
            self.token_tree.focus(last_item)
            self.token_tree.see(last_item)
        
        messagebox.showinfo("成功", f"已生成新 Token:\n\n{new_token}\n\n请选中后点击'复制观看链接'")
    
    def _copy_token(self):
        """复制 Token"""
        selection = self.token_tree.selection()
        if not selection:
            messagebox.showwarning("提示", "请先选择一个 Token")
            return
        
        item = self.token_tree.item(selection[0])
        token = item['values'][0]
        
        self.root.clipboard_clear()
        self.root.clipboard_append(token)
        
        self._log(f"已复制 Token: {token}")
        messagebox.showinfo("成功", "Token 已复制到剪贴板")
    
    def _copy_watch_url(self):
        """复制观看链接"""
        selection = self.token_tree.selection()
        if not selection:
            messagebox.showwarning("提示", "请先选择一个 Token")
            return
        
        item = self.token_tree.item(selection[0])
        token = item['values'][0]
        
        watch_url = self._get_watch_url(token)
        
        self.root.clipboard_clear()
        self.root.clipboard_append(watch_url)
        
        self._log(f"已复制观看链接")
        messagebox.showinfo("成功", f"观看链接已复制:\n\n{watch_url}")
    
    def _delete_token(self):
        """删除 Token"""
        selection = self.token_tree.selection()
        if not selection:
            messagebox.showwarning("提示", "请先选择一个 Token")
            return
        
        item = self.token_tree.item(selection[0])
        token = item['values'][0]
        
        result = messagebox.askyesno(
            "确认删除",
            f"确定要删除这个 Token 吗?\n\n{token}\n\n删除后使用此 Token 的用户将无法继续观看。"
        )
        
        if not result:
            return
        
        tokens = self._load_tokens()
        if token in tokens:
            tokens.remove(token)
            self._save_tokens(tokens)
            self._refresh_token_list()
            self._log(f"已删除 Token: {token}")
            messagebox.showinfo("成功", "Token 已删除")
    
    def _check_files(self):
        """检查必要文件"""
        errors = []
        
        # 检查 SRS
        srs_bat = self.root_dir / "srs" / "srs-live.bat"
        if not srs_bat.exists():
            errors.append("未找到 srs/srs-live.bat")
        
        # 检查 frpc
        frpc_exe = self.root_dir / "frpc" / ("frpc.exe" if self.is_windows else "frpc")
        if not frpc_exe.exists():
            errors.append("未找到 frpc/frpc.exe")
        
        frpc_toml = self.root_dir / "frpc" / "frpc.toml"
        if not frpc_toml.exists():
            errors.append("未找到 frpc/frpc.toml")
        
        # 检查验证服务器
        auth_server = self.root_dir / "auth" / "server.py"
        if not auth_server.exists():
            errors.append("未找到 auth/server.py")
        
        return errors
    
    def _start_system(self):
        """启动系统"""
        errors = self._check_files()
        if errors:
            messagebox.showerror(
                "缺少文件", 
                "请按照 README 配置以下文件:\n\n" + "\n".join(errors)
            )
            return
        
        self._log("="*50)
        self._log("开始启动所有服务...")
        self.status_label.config(text="正在启动...")
        
        try:
            # 1. 启动验证服务器
            self._log("▶ 启动验证服务器 (auth/server.py)...")
            self._start_auth_server()
            time.sleep(2)
            
            # 2. 启动 SRS
            self._log("▶ 启动 SRS (srs/srs-live.bat)...")
            self._start_srs()
            time.sleep(2)
            
            # 3. 启动 frpc
            self._log("▶ 启动 frpc (frpc/frpc.exe)...")
            self._start_frpc()
            time.sleep(2)
            
            self._log("="*50)
            self._log("✓ 所有服务启动完成!")
            self._log("")
            self._log("下一步:")
            self._log("1. 切换到'Token 管理'标签页生成观看链接")
            self._log("2. 配置 OBS 并开始推流")
            self._log("="*50)
            
            self.is_running = True
            self.start_btn.config(state="disabled")
            self.stop_btn.config(state="normal")
            self.status_label.config(text="✓ 系统运行中")
            
        except Exception as e:
            self._log(f"✗ 启动失败: {e}")
            messagebox.showerror("启动失败", str(e))
    
    def _start_auth_server(self):
        """启动验证服务器"""
        auth_dir = self.root_dir / "auth"
        
        if self.is_windows:
            cmd = f'start "验证服务器" /D "{auth_dir}" python server.py'
            subprocess.Popen(cmd, shell=True)
        else:
            proc = subprocess.Popen(
                [sys.executable, "server.py"],
                cwd=auth_dir
            )
            self.processes.append(proc)
    
    def _start_srs(self):
        """启动 SRS"""
        srs_dir = self.root_dir / "srs"
        
        if self.is_windows:
            # 直接运行 srs-live.bat
            cmd = f'start "SRS" /D "{srs_dir}" srs-live.bat'
            subprocess.Popen(cmd, shell=True)
        else:
            self._log("警告: Linux/Mac 请手动启动 SRS")
    
    def _start_frpc(self):
        """启动 frpc"""
        frpc_dir = self.root_dir / "frpc"
        
        if self.is_windows:
            # 直接运行 frpc.exe
            # cmd = f'start "frpc" /D "{frpc_dir}" frpc.exe -c frpc.toml'
            cmd = f'start "frpc" /D "{frpc_dir}" frpc.exe -c frpchongkong.toml'
            subprocess.Popen(cmd, shell=True)
        else:
            # proc = subprocess.Popen(
            #     ["./frpc", "-c", "frpc.toml"],
            #     cwd=frpc_dir
            # )
            # self.processes.append(proc)

            proc = subprocess.Popen(
                ["./frpc", "-c", "frpchongkong.toml"],
                cwd=frpc_dir
            )
            self.processes.append(proc)
    
    def _stop_system(self):
        """停止系统"""
        self._log("="*50)
        self._log("正在停止所有服务...")
        
        for proc in self.processes:
            proc.terminate()
        
        self.processes = []
        
        self.is_running = False
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.status_label.config(text="系统已停止")
        self._log("✓ 系统已停止")
        self._log("="*50)
        
        # 刷新 token 列表以更新状态
        self._refresh_token_list()
        
        if self.is_windows:
            self._log("")
            self._log("请手动关闭以下窗口:")
            self._log("  - 验证服务器")
            self._log("  - SRS")
            self._log("  - frpc")
            messagebox.showinfo(
                "提示", 
                "请手动关闭所有服务窗口:\n\n- 验证服务器\n- SRS\n- frpc"
            )
    
    def run(self):
        """运行主循环"""
        self.root.mainloop()

if __name__ == "__main__":
    app = StreamingLauncher()
    app.run()