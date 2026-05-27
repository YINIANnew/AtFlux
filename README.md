# YINIAN - AtFlux

![GitHub release](https://img.shields.io/github/v/release/yourusername/atflux)
![GitHub license](https://img.shields.io/github/license/yourusername/atflux)
![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)
![Platform](https://img.shields.io/badge/platform-Windows-blue)

A powerful P2P cross-network collaboration tool that enables secure, direct communication between devices across different networks without relying on third-party services.

一款强大的P2P跨网协同工具，无需依赖第三方服务即可实现不同网络设备之间的安全直接通信。

---

## Features / 功能特性

### Network Penetration / 网络穿透
- **STUN-based External IP Detection**: Automatically discovers external IP and port using standard STUN protocol
  - **基于STUN的外网IP探测**: 使用标准STUN协议自动发现外网IP和端口
- **UDP NAT Traversal**: Implements P2P direct connection via UDP hole punching
  - **UDP NAT打洞**: 通过UDP打洞实现P2P直连
- **Automatic Relay Fallback**: Seamlessly switches to TURN relay mode when P2P fails
  - **自动中继降级**: P2P失败时自动切换到TURN中继模式
- **Protocol Optimization**: UDP for handshake/hole punching, TCP for reliable data transfer
  - **协议优化**: UDP用于握手/打洞，TCP用于可靠数据传输

### Identity Authentication / 身份鉴权
- **Temporary Key Mode**: Secure one-time collaboration with bidirectional key verification
  - **临时密钥模式**: 双向密钥验证的安全临时协作
- **Whitelist Mode**: Permanent device collaboration with automatic P2P connection
  - **白名单模式**: 设备自动P2P连接的永久协作
- **Hardware-based Device ID**: Unique, tamper-proof device identification using hardware hash
  - **硬件设备ID**: 基于硬件哈希的唯一防篡改设备标识
- **Dual-layer Whitelist**: Local + server-side whitelist validation
  - **双层白名单**: 本地+服务端双重白名单验证

### File Sharing / 文件共享
- **Directory Isolation**: Secure path restriction prevents unauthorized system access
  - **目录隔离**: 安全路径限制防止越权访问系统目录
- **Remote Directory Browsing**: List files and directories remotely
  - **远程目录浏览**: 远程列出文件和目录
- **File Upload/Download**: Reliable file transfer with hash verification
  - **文件上传下载**: 带哈希校验的可靠文件传输
- **Error Handling**: Comprehensive error handling for transfer interruptions
  - **错误处理**: 传输中断的全面错误处理

### Remote Desktop / 远程桌面
- **Real-time Screen Capture**: High-performance screen capture using Windows APIs
  - **实时屏幕采集**: 使用Windows API的高性能屏幕采集
- **Intelligent Compression**: zlib compression for optimized bandwidth usage
  - **智能压缩**: zlib压缩优化带宽使用
- **Bidirectional Input**: Mouse and keyboard control from remote device
  - **双向输入**: 远程设备的鼠标键盘控制
- **Stream Multiplexing**: Video and control data share single connection
  - **流复用**: 视频和控制数据共享单连接

### Security / 安全性
- **RSA Encryption**: 2048-bit RSA for session key exchange
  - **RSA加密**: 2048位RSA会话密钥交换
- **AES Encryption**: 256-bit AES for all data transmission
  - **AES加密**: 256位AES加密所有数据传输
- **Secure Storage**: Encrypted local storage for credentials and whitelist
  - **安全存储**: 凭证和白名单的加密本地存储

---

## Tech Stack / 技术栈

| Component / 组件 | Technology / 技术 |
|------------------|-------------------|
| Language / 语言 | Python 3.8+ |
| Cryptography / 加密 | cryptography (RSA/AES) |
| Networking / 网络 | Standard socket library |
| Screen Capture / 屏幕采集 | pywin32 |
| Data Compression / 数据压缩 | zlib |

---

## Quick Start / 快速开始

### Prerequisites / 前置条件

```bash
pip install -r requirements.txt
```

### Run Signaling Server / 启动信令服务端

```bash
python server/signaling_server.py
```

### Run Client / 启动客户端

```bash
# Whitelist mode (recommended for permanent collaboration)
# 白名单模式（推荐用于永久协作）
python client/atflux_client.py --mode whitelist

# Temporary key mode (for one-time collaboration)
# 临时密钥模式（用于一次性协作）
python client/atflux_client.py --mode temp_key --key your_secret_key
```

---

## Usage / 使用说明

### Command Line Options / 命令行参数

```
AtFlux - P2P Cross-Network Collaboration Tool

optional arguments:
  --mode MODE           Connection mode: whitelist or temp_key (default: whitelist)
                        连接模式: whitelist(白名单模式) 或 temp_key(临时密钥模式)
  --key KEY             Temporary collaboration key
                        临时协作密钥
  --device-id ID        Target device ID
                        目标设备ID
  --add-whitelist ID    Add device to whitelist
                        添加设备到白名单
  --remove-whitelist ID Remove device from whitelist
                        从白名单移除设备
  --list-files          List shared files
                        列出共享文件
  --download REMOTE LOCAL
                        Download file from remote
                        从远程下载文件
  --upload LOCAL REMOTE Upload file to remote
                        上传文件到远程
  --remote-desktop      Start remote desktop session
                        启动远程桌面会话
```

### Examples / 示例

```bash
# Add device to whitelist
# 添加设备到白名单
python client/atflux_client.py --add-whitelist <device_id>

# List shared files
# 列出共享文件
python client/atflux_client.py --mode whitelist --list-files

# Download file
# 下载文件
python client/atflux_client.py --mode whitelist --download /remote/path.txt local.txt

# Upload file
# 上传文件
python client/atflux_client.py --mode whitelist --upload local.txt remote_name.txt

# Start remote desktop
# 启动远程桌面
python client/atflux_client.py --mode whitelist --remote-desktop
```

---

## Project Structure / 项目结构

```
AtFlux/
├── client/
│   └── atflux_client.py      # Main client application / 主客户端应用
├── common/
│   ├── crypto.py             # Encryption utilities (RSA/AES) / 加密工具
│   ├── network.py            # Network components (STUN/P2P/TURN) / 网络组件
│   ├── file_share.py         # File sharing protocol / 文件共享协议
│   └── remote_desktop.py     # Remote desktop components / 远程桌面组件
├── server/
│   └── signaling_server.py   # Signaling server for device discovery / 设备发现信令服务
├── config/
│   ├── app.json              # Application configuration / 应用配置
│   └── whitelist.json        # Device whitelist / 设备白名单
├── requirements.txt          # Dependencies / 依赖列表
└── .gitignore               # Git ignore rules / Git忽略规则
```

---

## Configuration / 配置说明

All configuration is managed in `config/app.json`:

所有配置在 `config/app.json` 中管理：

```json
{
  "signaling_server": {
    "host": "localhost",
    "port": 8888
  },
  "stun_server": {
    "host": "stun.l.google.com",
    "port": 19302
  },
  "network": {
    "local_port": 9999,
    "connection_timeout": 30
  },
  "encryption": {
    "rsa_key_size": 2048,
    "aes_key_size": 256
  }
}
```

---

## Architecture / 架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        Internet                               │
│                         互联网                                 │
├─────────────────────────────────────────────────────────────────┤
│                     Signaling Server                          │
│               (Device Registration & Address Exchange)         │
│                     信令服务器                                 │
│              (设备注册与地址交换)                              │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐              P2P Direct / Relay             │
│  │  Client A    │◄──────────────────────────────────────►│  Client B    │
│  │ (Device ID)  │                    Connection              │  (Device ID) │
│  │  客户端A     │           P2P直连 / 中继连接               │  客户端B     │
│  └──────────────┘                                          └──────────────┘
│       │                                                           │
│       ├── File Share                                              │
│       ├── Remote Desktop                                          │
│       └── Authentication                                           │
│       │                                                           │
│       ├── 文件共享                                                 │
│       ├── 远程桌面                                                 │
│       └── 身份认证                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Security / 安全

- All communications are encrypted end-to-end
  - 所有通信均为端到端加密
- Device authentication before any data transfer
  - 数据传输前进行设备认证
- Path isolation prevents directory traversal attacks
  - 路径隔离防止目录遍历攻击
- No sensitive data stored in plain text
  - 敏感数据不以明文形式存储

---

## License / 许可证

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件。

---

## Contributing / 贡献

Contributions are welcome! Please feel free to submit issues and pull requests.

欢迎贡献！欢迎提交 issue 和 pull request。

---

## Acknowledgments / 致谢

- STUN protocol implementation based on RFC 5389
  - STUN协议实现基于 RFC 5389
- TURN protocol implementation based on RFC 5766
  - TURN协议实现基于 RFC 5766
- Windows API integration for screen capture
  - Windows API屏幕采集集成

---

**Note**: This tool is designed for legitimate network administration and collaboration purposes only. Always ensure you have proper authorization before accessing any network or device.

**注意**: 本工具仅用于合法的网络管理和协作目的。访问任何网络或设备前，请确保已获得适当授权。

备注：在制作/撰写本项目时，使用了人工智能以辅助。
