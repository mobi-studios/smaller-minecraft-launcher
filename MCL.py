from tkinter import messagebox, ttk
import tkinter as tk
from urllib.request import urlretrieve
import requests
import threading
import ctypes
import sys
import subprocess
import json
import os
import ssl


def load_config():
    """加载配置文件"""
    if os.path.exists('config.json'):
        with open('config.json') as f:
            return json.load(f)
    return {"username": "", "password": "", "api_url": "https://authserver.mojang.com/authenticate", "version": "1.16.5"}


def save_config(config):
    """保存配置文件"""
    with open('config.json', 'w') as f:
        json.dump(config, f, indent=4)


def authenticate(username, password, api_url):
    """使用提供的用户名、密码和 API URL 进行认证"""
    payload = {
        "client_id": "your_client_id",  # Replace with your Microsoft client ID
        "scope": "XboxLive.signin",
        "username": username,
        "password": password,
        "grant_type": "password"
    }

    try:
        response = requests.post(api_url, json=payload)
        response.raise_for_status()

        auth_data = response.json()
        access_token = auth_data.get("access_token")

        if access_token:
            return access_token
        else:
            return None

    except requests.exceptions.RequestException as e:
        print(f"Authentication error: {e}")
        return None


def get_player_id(username):
    """获取玩家的 ID"""
    url = f"https://api.mojang.com/users/profiles/minecraft/{username}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        player_data = response.json()
        return player_data.get("id")  # 返回玩家的 ID
    except requests.exceptions.RequestException as e:
        print(f"Error fetching player ID: {e}")
        return None


def get_minecraft_version_manifest():
    """获取 Minecraft 版本清单"""
    manifest_url = "https://launchermeta.mojang.com/mc/game/version_manifest.json"

    ssl_context = ssl.create_default_context()
    ssl_context.options |= ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1  # 禁用 TLS 1.0 和 1.1

    try:
        response = requests.get(manifest_url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching version manifest: {e}")
        return None


def get_available_versions():
    """获取可用的 Minecraft 版本列表"""
    manifest = get_minecraft_version_manifest()
    return [version['id'] for version in manifest['versions']]


def get_required_jdk(version):
    """根据版本返回所需的 JDK 和安装程序"""
    if version >= "1.20.3":
        return "21", "jdk-21_windows-x64_bin.exe"  # Return only two values
    elif version >= "1.16.5":
        return "17", "jdk17.0.1.0.exe"  # Return only two values
    elif version < "1.16.5":
        return "8", "jre-8u431-windows-x64.exe"  # Return only two values
    else:
        raise ValueError("Unsupported Java version")

# ... 省略其他函数 ...


def on_launch():
    """处理启动按钮点击事件"""
    config = load_config()
    username = username_entry.get()
    password = password_entry.get()
    api_url = api_url_entry.get()
    selected_version = version_combobox.get()

    access_token = None

    # 如果提供了用户名和密码，则进行认证
    if username and password:
        access_token = authenticate(username, password, api_url)

    # 获取玩家的 ID
    player_id = get_player_id(username)
    if player_id is None:
        messagebox.showerror("Error", "Unable to retrieve player ID.")
        return

    # 检查并下载 Minecraft jar 包和库文件
    if download_minecraft_jar(selected_version) and download_libraries(selected_version):
        if check_java_installed(selected_version):
            # Pass the player ID to the launch_game function
            launch_game({"id": selected_version},
                        username, access_token, player_id)
        else:
            messagebox.showwarning(
                "Java Not Found", "Java is not installed. Please download it from:\nhttps://www.java.com/en/download/")


# 创建 GUI
# 创建 GUI
root = tk.Tk()
root.title("Mobi Craft Launcher")

# 用户名输入框
tk.Label(root, text="Username:").pack()
username_entry = tk.Entry(root)
username_entry.pack()

# 密码输入框
tk.Label(root, text="Password:").pack()
password_entry = tk.Entry(root, show='*')
password_entry.pack()

# API URL 输入框
tk.Label(root, text="API URL:").pack()
api_url_entry = tk.Entry(root)
api_url_entry.pack()
api_url_entry.insert(0, "https://authserver.mojang.com/authenticate")  # 默认值

# 版本选择下拉框
tk.Label(root, text="Select Version:").pack()
version_combobox = ttk.Combobox(root)
version_combobox.pack()

# 获取可用版本并填充下拉框
available_versions = get_available_versions()
version_combobox['values'] = available_versions
version_combobox.current(0)  # 默认选择第一个版本

# 启动按钮
launch_button = tk.Button(root, text="Launch", command=on_launch)
launch_button.pack()


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


if is_admin():
    root.mainloop()
else:
    subprocess.call(["startonadmin.bat"])
