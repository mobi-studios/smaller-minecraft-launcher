import json
import os
import subprocess
import requests
import tkinter as tk
from tkinter import messagebox, ttk
from urllib.request import urlretrieve


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
    try:
        # Ensure this returns exactly two values
        # Updated to match the new return values
        required_jdk, installer = get_required_jdk(version)
    except ValueError as e:
        messagebox.showerror("Error", str(e))
        return False

    java_path = os.path.join(os.getcwd(), f"jdk{required_jdk}")

    if os.path.exists(java_path):
        java_executable = os.path.join(java_path, "bin", "java.exe")
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
            return False
    else:
        install_java(installer, required_jdk)
        return False


def install_java(installer, version):
    """安装所需的 Java 版本到指定目录"""
    installer_path = os.path.join(os.getcwd(), installer)
    install_dir = os.path.join(os.getcwd(), f"jdk{version}")

    if os.path.exists(installer_path):
        try:
            # Create the installation directory if it doesn't exist
            os.makedirs(install_dir, exist_ok=True)

            # Create a batch file to run the installer with elevated permissions
            batch_file_path = os.path.join(os.getcwd(), "install_java.bat")
            with open(batch_file_path, "w+") as batch_file:
                batch_file.write(
                    f'start /wait "" "{installer_path}" /s /D="{install_dir}"\n')
                # Delete the batch file after execution
                batch_file.write(f'del "{batch_file_path}"\n')

            # Run the batch file
            subprocess.run(["start ", '"Window Title"',
                           batch_file_path], check=True)
            messagebox.showinfo(
                "Installation", f"{installer} is being installed to {install_dir}.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to install Java: {e}")
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
        if check_java_installed(selected_version):  # Updated to pass selected version
            launch_game({"id": selected_version}, username, access_token)
        else:
            messagebox.showwarning(
                "Java Not Found", "Java is not installed. Please download it from:\nhttps://www.java.com/en/download/")




def launch_game(version_info, username=None, access_token=None):
    global java_path
    """启动 Minecraft 游戏"""
    minecraft_path = os.path.join("versions", f"{version_info['id']}.jar")
    command = [
        java_path,
        "java.exe", "-jar", minecraft_path,
        "--username", username if username else "Player",
        "--accessToken", access_token if access_token else "null",
        "--version", version_info["id"],
        "--offline" if access_token is None else ""
    ]

    # 过滤掉空字符串
    command = [arg for arg in command if arg]

    try:
        subprocess.Popen(command)
    except Exception as e:
        messagebox.showerror("Error", str(e))


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


# 启动 GUI
root.mainloop()
