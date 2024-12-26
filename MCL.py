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
        "client_id": "your_client_id",  # 替换为您的 Microsoft 客户端 ID
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

def install_java(installer, required_jdk):
    """安装所需的 Java 版本"""
    installer_path = os.path.join(os.getcwd(), installer)
    if not os.path.exists(installer_path):
        messagebox.showerror("Error", f"Installer not found: {installer_path}")
        return False

    try:
        messagebox.showinfo("Installing Java", f"Installing JDK {required_jdk}...")
        subprocess.run([installer_path], check=True)
        messagebox.showinfo("Success", "Java installation complete.")
        return True
    except subprocess.CalledProcessError as e:
        messagebox.showerror("Error", f"Java installation failed: {e}")
        return False


def launch_game(version_info, username, access_token, player_id):
    """启动 Minecraft 游戏"""
    game_dir = os.path.join(os.getcwd(), "games", version_info['id'])
    assets_dir = os.path.join(os.getcwd(), "assets")
    jar_file = f"versions/{version_info['id']}.jar"

    # 检查路径是否有效
    if not os.path.exists(jar_file):
        messagebox.showerror("Error", f"Jar file not found: {jar_file}")
        return

    # 构建类路径，包括 Minecraft jar 和所有库文件
    libraries_path = os.path.join(os.getcwd(), "libraries")
    classpath = [jar_file]  # 开始时包含 Minecraft jar 文件

    # 收集所有库文件的路径
    for root, dirs, files in os.walk(libraries_path):
        for file in files:
            if file.endswith('.jar'):
                classpath.append(os.path.join(root, file))

    # 使用分隔符构建类路径字符串
    path_separator = ";" if os.name == "nt" else ":"
    classpath_str = path_separator.join(classpath)

    command = [
        "java",
        "-Xmx2G",  # 示例 JVM 参数
        "-Djava.library.path=libraries",  # 示例 JVM 参数
        "-cp", classpath_str,  # 更新类路径，包含所有依赖项
        "net.minecraft.client.main.Main",
        "--username", username,
        "--version", version_info['id'],
        "--gameDir", game_dir,
        "--assetsDir", assets_dir,
        "--assetIndex", "1.16",  # 示例资源索引版本
        "--uuid", player_id,
    ]

    # 处理 access_token 为 None 的情况
    if access_token is not None:
        command += ["--accessToken", access_token]
    else:
        command += ["--accessToken", "placeholder"]  # 使用占位符或省略

    command += [
        "--userType", "mojang",
        "--versionType", "release",
        "--width", "854",  # 窗口宽度
        "--height", "480"  # 窗口高度
    ]

    # 检查命令中的每个参数是否为 None
    for arg in command:
        if arg is None:
            messagebox.showerror("Error", "One of the command arguments is None.")
            return

    try:
        # 写入命令到文件
        command_str = ' '.join(map(str, command))
        with open("launch_command.txt", "w") as f:
            f.write(command_str)

        # 启动 Minecraft
        subprocess.Popen(command)
        messagebox.showinfo("Launching", "Minecraft is launching...")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to launch Minecraft: {e}")




def get_available_versions():
    """获取可用的 Minecraft 版本列表"""
    manifest = get_minecraft_version_manifest()
    return [version['id'] for version in manifest['versions']]

def get_required_jdk(version):
    """根据版本返回所需的 JDK 和安装程序"""
    if version >= "1.20.3":
        return "21", "jdk-21_windows-x64_bin.exe"
    elif version >= "1.16.5":
        return "17", "jdk17.0.1.0.exe"
    elif version < "1.16.5":
        return "8", "jre-8u431-windows-x64.exe"
    else:
        raise ValueError("Unsupported Java version")

def download_minecraft_jar(version):
    """下载 Minecraft jar 包"""
    manifest = get_minecraft_version_manifest()
    for version_info in manifest['versions']:
        if version_info['id'] == version:
            version_details_url = version_info['url']
            version_details = requests.get(version_details_url).json()
            jar_url = version_details['downloads']['client']['url']
            jar_path = os.path.join("versions", f"{version}.jar")
            os.makedirs(os.path.dirname(jar_path), exist_ok=True)

            if not os.path.exists(jar_path):
                try:
                    messagebox.showinfo("download", f"Downloading {version}.jar...")
                    urlretrieve(jar_url, jar_path)
                    messagebox.showinfo("download", "Download complete.")
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to download {version}.jar: {e}")
                    return False
            return True
    messagebox.showerror("Error", f"Version {version} not found.")
    return False

def download_libraries(version):
    """下载 Minecraft 补全文件（库文件）"""
    manifest = get_minecraft_version_manifest()
    for version_info in manifest['versions']:
        if version_info['id'] == version:
            version_details_url = version_info['url']
            version_details = requests.get(version_details_url).json()
            libraries = version_details.get('libraries', [])

            for library in libraries:
                if 'downloads' in library and 'artifact' in library['downloads']:
                    artifact = library['downloads']['artifact']
                    library_url = artifact['url']
                    library_path = os.path.join("libraries", artifact['path'])
                    os.makedirs(os.path.dirname(library_path), exist_ok=True)

                    if not os.path.exists(library_path):
                        try:
                            print(f"Downloading {artifact['path']}...")
                            urlretrieve(library_url, library_path)
                            print("Download complete.")
                        except Exception as e:
                            messagebox.showerror("Error", f"Failed to download {artifact['path']}: {e}")
                            return False
            return True
    messagebox.showerror("Error", f"Version {version} not found.")
    return False

def check_java_installed(version):
    """检查所需的 Java 版本是否已安装"""
    global java_path
    global installer
    try:
        required_jdk, installer = get_required_jdk(version)
        if required_jdk is None or installer is None:
            messagebox.showerror("Error", "Required JDK or installer is not available.")
            return False
    except ValueError as e:
        messagebox.showerror("Error", str(e))
        return False

    java_path = os.path.join(os.getcwd(), f"jdk{required_jdk}", "bin")

    if os.path.exists(java_path):
        java_executable = os.path.join(java_path, "java.exe")
        if os.path.exists(java_executable):
            try:
                result = subprocess.run([java_executable, "-version"],
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                if required_jdk in result.stderr.decode():
                    return True
                else:
                    messagebox.showerror("Error", f"Java version mismatch. Expected: {required_jdk}.")
                    return False
            except Exception as e:
                messagebox.showerror("Error", f"Failed to run Java: {e}")
                return False
        else:
            messagebox.showerror("Error", f"Java executable not found at {java_executable}.")
            install_java(installer, required_jdk)
            return False
    else:
        install_java(installer, required_jdk)
        return False

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
