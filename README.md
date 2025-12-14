## 🚀 快速开始

### 第一步：克隆项目
```bash
git clone https://github.com/your-username/rtmp-streaming-system.git
cd rtmp-streaming-system
```

### 第二步：安装 Python 依赖
```bash
pip install flask
```

或者使用 requirements.txt（如果有）：
```bash
pip install -r requirements.txt
```

---

### 第三步：下载并配置 SRS

SRS 是流媒体服务器，负责接收 OBS 推流并转发给 frpc。

#### Windows

1. **下载 SRS**
   
   访问: https://github.com/ossrs/srs/releases
   
   下载最新的 Windows 版本，例如: `SRS-Windows-x86_64-6.0.145.zip`

2. **解压到项目目录**
   
   解压后，将整个文件夹重命名为 `srs`，放到项目根目录：
```
   rtmp-streaming-system/
   └── srs/
       ├── srs.exe
       ├── srs-live.bat    ← 确保有这个文件
       ├── conf/
       └── objs/
```

3. **配置 SRS**
   
   在 `srs/conf/` 目录下创建 `live.conf` 文件：
```nginx
   # SRS 配置文件
   listen              19350;              # RTMP 监听端口
   max_connections     1000;
   daemon              off;
   srs_log_tank        console;
   
   vhost __defaultVhost__ {
       http_hooks {
           enabled         on;
           
           # 验证接口（连接到验证服务器）
           on_publish      http://127.0.0.1:8080/api/on_publish;
           on_play         http://127.0.0.1:8080/api/on_play;
           on_stop         http://127.0.0.1:8080/api/on_stop;
       }
   }
   
   http_api {
       enabled         on;
       listen          19850;
   }
   
   http_server {
       enabled         on;
       listen          19800;
       dir             ./objs/nginx/html;
   }
```
   
   **重要**：确保 `listen 19350;` 这个端口号记下来，后面需要用到。

4. **检查 srs-live.bat**
   
   确保 `srs/srs-live.bat` 文件内容为：
```bat
   @echo off
   cd /d %~dp0
   srs.exe -c conf/live.conf
   pause
```
   
5. **下载，解压并复制内容到frpc文件夹，然后配置 frpc**
   在 `frpc/` 目录下创建 `frpc.toml` 文件：
```toml
   # frpc 配置文件
   
   # FRP 服务器地址
   serverAddr = "改成你的服务器地址"
   serverPort = 7000
   
   # 认证配置（改成你的 Token）
   [auth]
   method = "token"
   token = "your_frp_token_here"
   
   # 日志配置
   [log]
   level = "info"
   to = "./frpc.log"
   
   # 代理配置
   [[proxies]]
   name = "rtmp-stream"
   type = "tcp"
   localIP = "127.0.0.1"
   localPort = 19350           # 本地 SRS 端口（与 live.conf 中的 listen 一致）
   remotePort = 20000         # 云端暴露端口（观看地址用这个端口）
   
   # 传输配置
   [transport]
   tcpMux = true
   
   [transport.tls]
   enable = true
   disableCustomTLSFirstByte = true
```

6. **运行**
   cd 项目目录
   python .\launcher.py