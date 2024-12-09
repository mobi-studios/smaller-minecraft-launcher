import json
import os
import subprocess
import requests
import tkinter as tk
from tkinter import messagebox, ttk
from urllib.request import urlretrieve
import ctypes, sys
import threading

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False





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
        "agent": {
            "name": "Minecraft",
            "version": 1
        },
        "username": username,
        "password": password,
        "requestUser": True
    }

    try:
        response = requests.post(api_url, json=payload)
        response.raise_for_status()

        auth_data = response.json()
        access_token = auth_data.get("accessToken")

        if access_token:
            return access_token
        else:
            return None

    except requests.exceptions.RequestException as e:
        print(f"Authentication error: {e}")
        return None


def get_minecraft_version_manifest():
    """获取 Minecraft 版本清单"""
    manifest_url = "https://launchermeta.mojang.com/mc/game/version_manifest.json"
    response = requests.get(manifest_url)
    response.raise_for_status()
    return response.json()


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


def check_java_installed(version):
    """检查所需的 Java 版本是否已安装"""
    global java_path
    global installer
    try:
        # Ensure this returns exactly two values
        # Updated to match the new return values
        required_jdk, installer = get_required_jdk(version)
    except ValueError as e:
        messagebox.showerror("Error", str(e))
        return False

    java_path = os.path.join(os.getcwd(), f"jdk{required_jdk}","bin")

    if os.path.exists(java_path):
        java_executable = os.path.join(java_path, "java.exe")
        if os.path.exists(java_executable):
            try:
                # Attempt to run the Java executable to check its version
                result = subprocess.run([java_executable, "-version"],
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                # Check if the output contains the expected version
                if required_jdk in result.stderr.decode():
                    return True
                else:
                    messagebox.showerror(
                        "Error", f"Java version mismatch. Expected: {required_jdk}.")
                    return False
            except Exception as e:
                messagebox.showerror("Error", f"Failed to run Java: {e}")
                return False
        else:
            messagebox.showerror(
                "Error", f"Java executable not found at {java_executable}.")
            install_java(installer, required_jdk)
            return False
    else:
        install_java(installer, required_jdk)
        return False


def install_java(installer, version):
    """安装所需的 Java 版本到指定目录"""
    global install_dir
    installer_path = os.path.join(os.getcwd(), installer)
    install_dir = os.path.join(os.getcwd(), f"jdk{version}")
    messagebox.showerror("java",f"java is not installed. we will install it.(not in {install_dir})")
    messagebox.showinfo("java install","java installing...")
    if os.path.exists(installer_path):
        try:
            # Run the java installer
            subprocess.run([installer,f"INSTALLDIR={install_dir}"], check=True)
            messagebox.showinfo("install java","java installed!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to install Java: {e}")
            print(f"{e}")
    else:
        messagebox.showerror(
            "Error", f"Installer {installer} not found in the current directory.")


def download_minecraft_jar(version):
    """下载 Minecraft jar 包"""
    manifest = get_minecraft_version_manifest()

    # 查找指定版本的 jar 文件 URL
    for version_info in manifest['versions']:
        if version_info['id'] == version:
            version_details_url = version_info['url']
            version_details = requests.get(version_details_url).json()
            jar_url = version_details['downloads']['client']['url']
            jar_path = os.path.join("versions", f"{version}.jar")

            # 确保目标目录存在
            os.makedirs(os.path.dirname(jar_path), exist_ok=True)

            if not os.path.exists(jar_path):
                try:
                    messagebox.showinfo("download",f"Downloading {version}.jar...")
                    urlretrieve(jar_url, jar_path)
                    messagebox.showinfo("download","Download complete.")
                except Exception as e:
                    messagebox.showerror(
                        "Error", f"Failed to download {version}.jar: {e}")
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

                    # 确保目标目录存在
                    os.makedirs(os.path.dirname(library_path), exist_ok=True)

                    if not os.path.exists(library_path):
                        try:
                            print(f"Downloading {artifact['path']}...")
                            urlretrieve(library_url, library_path)
                            print("Download complete.")
                        except Exception as e:
                            messagebox.showerror(
                                "Error", f"Failed to download {artifact['path']}: {e}")
                            return False
            return True
    messagebox.showerror("Error", f"Version {version} not found.")
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

    # 检查并下载 Minecraft jar 包和库文件
    if download_minecraft_jar(selected_version) and download_libraries(selected_version):
        if check_java_installed(selected_version):  
            threading.Thread(target=launch_game({"id": selected_version}, username, access_token)).start()# Updated to pass selected version
        else:
            messagebox.showwarning(
                "Java Not Found", f"Java can't be installed. please install it or copy to {install_dir}")




def launch_game(version_info, username=None, access_token=None):
    global java_path
    """启动 Minecraft 游戏并写入 .bat 文件"""
    
    # Minecraft JAR 文件路径
    minecraft_path = os.path.join("versions", f"{version_info['id']}.jar")
    
    # 构建类路径
    classpath = [minecraft_path]
    
    # 添加所有库文件到类路径
    manifest = get_minecraft_version_manifest()
    for version_info in manifest['versions']:
        if version_info['id'] == version_info["id"]:
            version_details_url = version_info['url']
            version_details = requests.get(version_details_url).json()
            libraries = version_details.get('libraries', [])
            for library in libraries:
                if 'downloads' in library and 'artifact' in library['downloads']:
                    artifact = library['downloads']['artifact']
                    library_path = os.path.join("libraries", artifact['path'])
                    classpath.append(library_path)

    # 将类路径转换为字符串
    classpath_str = ";".join(classpath)

    if access_token is not None:
        offline = "" 
        accesstoken = access_token
    else:
        offline = "--offline"
        accesstoken = "null"

    # 构建命令
    command = [
        os.path.join(java_path, "java.exe"),
        "-cp", classpath_str,
        "net.minecraft.client.main.Main",
        "--username", username if username else "Player",
        "--accessToken", accesstoken,
        "--version", version_info["id"],
        offline
    ]

    # 写入到 .bat 文件
    bat_file_path = "launch_minecraft.bat"
    with open(bat_file_path, "w") as bat_file:
        bat_file.write(f'@echo off\n')
        bat_file.write(f'cd /d "{os.getcwd()}"\n')  # 切换到当前工作目录
        bat_file.write(f'"{os.path.join(java_path, "java.exe")}" -cp "{classpath_str}" net.minecraft.client.main.Main --username "{username if username else "Player"}" --accessToken "{accesstoken}" --version "{version_info["id"]}" {offline}\n')
        bat_file.write(f'pause\n')  # 暂停以查看输出

    print(f"Batch file created: {bat_file_path}")

    # 可选：直接运行 .bat 文件
    os.startfile(bat_file_path)




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

    # 检查并下载 Minecraft jar 包和库文件
    if download_minecraft_jar(selected_version) and download_libraries(selected_version):
        # Updated to pass selected version
        if check_java_installed(selected_version):
            launch_game({"id": selected_version}, username, access_token)
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

if is_admin():
    # 启动 GUI
    root.mainloop()
else:
    subprocess.call(["startonadmin.bat"])

