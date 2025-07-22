import os
import sys
import time
import hashlib
import requests
import platform
import zipfile
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional, List
import subprocess
import winreg

if platform.system() == "Windows":
    import ctypes
    from ctypes import wintypes

class Colors:
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    ITALIC = '\033[3m'
    BLACK_BG = '\033[40m'
    END = '\033[0m'

def colored(text: str, color: str) -> str:
    return f"{color}{text}{Colors.END}"

def info(message: str):
    time_str = datetime.now().strftime("%H:%M:%S")
    print(f"[{colored(time_str, Colors.BLUE + Colors.BOLD)}] [{colored('INFO', Colors.GREEN + Colors.BOLD)}] {message}")

def error(message: str):
    time_str = datetime.now().strftime("%H:%M:%S")
    print(f"[{colored(time_str, Colors.BLUE + Colors.BOLD)}] [{colored('ERROR', Colors.RED + Colors.BOLD)}] {message}")

def debug(message: str):
    if __debug__:
        time_str = datetime.now().strftime("%H:%M:%S")
        print(f"[{colored(time_str, Colors.BLUE + Colors.BOLD)}] [{colored('DEBUG', Colors.YELLOW + Colors.BOLD)}] {message}")

def clear_screen():
    if platform.system() == "Windows":
        os.system("cls")
    else:
        os.system("clear")

def get_terminal_width() -> int:
    try:
        return os.get_terminal_size().columns
    except:
        return 80

def print_centered(text: str, color: str = Colors.MAGENTA + Colors.ITALIC + Colors.BLACK_BG):
    width = get_terminal_width()
    for line in text.splitlines():
        spaces = (width - len(line)) // 2
        print(" " * spaces + colored(line, color))

def set_console_title_and_icon():
    if platform.system() == "Windows":
        icon_path = Path("assets/icon.ico")
        if icon_path.exists():
            try:
                ctypes.windll.kernel32.SetConsoleTitleW("Bubbaverse Launcher")
                
                hwnd = ctypes.windll.kernel32.GetConsoleWindow()
                if hwnd != 0:
                    hicon = ctypes.windll.user32.LoadImageW(
                        None,
                        str(icon_path.absolute()),
                        1,
                        0, 0,
                        0x00000010 | 0x00000040
                    )
                    if hicon != 0:
                        ctypes.windll.user32.SendMessageW(hwnd, 0x0080, 0, hicon)
                        ctypes.windll.user32.SendMessageW(hwnd, 0x0080, 1, hicon)
            except Exception as e:
                debug(f"Failed to set console icon: {e}")
        else:
            ctypes.windll.kernel32.SetConsoleTitleW("Bubbaverse Launcher")

def http_get(client: requests.Session, url: str) -> Optional[str]:
    debug(colored("GET", Colors.GREEN) + " " + colored(url, Colors.BLUE))
    try:
        response = client.get(url)
        return response.text
    except Exception as e:
        debug(f"Failed to fetch {colored(url, Colors.BLUE)}: {e}")
        return None

def download_file(client: requests.Session, url: str, path: Path):
    debug(colored("GET", Colors.GREEN) + " " + colored(url, Colors.BLUE))
    try:
        with client.get(url, stream=True) as response:
            response.raise_for_status()
            total_size = int(response.headers.get('content-length', 0))
            debug(f"Content Length: {total_size}")
            
            time_str = datetime.now().strftime("%H:%M:%S")
            info_message = f"[{colored(time_str, Colors.BLUE + Colors.BOLD)}] [{colored('INFO', Colors.GREEN + Colors.BOLD)}] Downloading {colored(url, Colors.BLUE)}"
            
            with open(path, 'wb') as f:
                downloaded = 0
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    downloaded += len(chunk)
                    progress = downloaded / total_size * 100
                    print(f"\r{info_message} [{progress:.1f}%]", end="")
            print()
            info(f"Finished downloading {colored(url, Colors.GREEN)}")
    except Exception as e:
        error(f"Failed to download {url}: {e}")
        raise

def generate_md5(input_str: str) -> str:
    return hashlib.md5(input_str.encode()).hexdigest()

def download_file_prefix(client: requests.Session, url: str, path_prefix: Path) -> Path:
    path = path_prefix / generate_md5(url)
    download_file(client, url, path)
    return path

def create_folder_if_not_exists(path: Path):
    if not path.exists():
        info(f"Creating folder {colored(str(path), Colors.BLUE)}")
        path.mkdir(parents=True, exist_ok=True)

def get_sha1_hash_of_file(path: Path) -> str:
    sha1 = hashlib.sha1()
    with open(path, 'rb') as f:
        while True:
            data = f.read(65536)
            if not data:
                break
            sha1.update(data)
    return sha1.hexdigest()

def get_installation_directory() -> Path:
    if platform.system() == "Windows":
        appdata = os.getenv('LOCALAPPDATA')
        if appdata:
            return Path(appdata) / "Bubbaverse"
    return Path.home() / ".local" / "share" / "Bubbaverse"

def extract_to_dir(zip_file: Path, target_dir: Path):
    info(f"Extracting {colored(str(zip_file), Colors.BLUE)} to {colored(str(target_dir), Colors.BLUE)}")
    with zipfile.ZipFile(zip_file, 'r') as zip_ref:
        zip_ref.extractall(target_dir)

def install_windows_protocol(bootstrapper_path: Path):
    try:
        icon_path = Path("assets/icon.ico")
        icon_str = f'"{icon_path.absolute()}",0' if icon_path.exists() else f'"{bootstrapper_path}",0'
        
        hkey_current_user = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
        hkey_classes_root = winreg.OpenKey(hkey_current_user, r"Software\Classes")
        
        hkey_syntax_player = winreg.CreateKey(hkey_classes_root, "bubba-player")
        winreg.SetValue(hkey_syntax_player, "", winreg.REG_SZ, "URL: BubbaVerse Protocol")
        winreg.SetValueEx(hkey_syntax_player, "URL Protocol", 0, winreg.REG_SZ, "")
        
        hkey_shell = winreg.CreateKey(hkey_syntax_player, "shell")
        hkey_open = winreg.CreateKey(hkey_shell, "open")
        hkey_command = winreg.CreateKey(hkey_open, "command")
        winreg.SetValue(hkey_command, "", winreg.REG_SZ, f'"{bootstrapper_path}" "%1"')
        
        hkey_icon = winreg.CreateKey(hkey_syntax_player, "DefaultIcon")
        winreg.SetValue(hkey_icon, "", winreg.REG_SZ, icon_str)
    except Exception as e:
        error(f"Failed to install protocol: {e}")

def install_linux_desktop(bootstrapper_path: Path, version: str):
    desktop_dir = Path.home() / ".local" / "share" / "applications"
    desktop_dir.mkdir(parents=True, exist_ok=True)
    
    icon_path = Path("assets/icon.ico")
    icon_str = str(icon_path.absolute()) if icon_path.exists() else str(bootstrapper_path)
    
    desktop_content = f"""[Desktop Entry]
Name=Bubbaverse Launcher
Exec={bootstrapper_path} %u
Icon={icon_str}
Type=Application
Terminal=true
Version={version}
MimeType=x-scheme-handler/bubba-player;"""
    
    desktop_path = desktop_dir / "bubba-player.desktop"
    with open(desktop_path, 'w') as f:
        f.write(desktop_content)
    
    os.chmod(desktop_path, 0o755)
    os.chmod(bootstrapper_path, 0o755)
    
    subprocess.run(["xdg-mime", "default", "bubba-player.desktop", "x-scheme-handler/bubba-player"])

def main():
    set_console_title_and_icon()
    clear_screen()
    
    args = sys.argv
    base_url = "www.boblox.org"
    setup_url = "setup.boblox.org"
    fallback_setup_url = "https://setup.boblox.org"
    bootstrapper_filename = "BubbaversePlayerLauncher.exe" if platform.system() == "Windows" else "BubbaversePlayerLinuxLauncher"
    
    startup_text = f"""
    888888b.   888     888 888888b.   888888b.         d8888 
    888  "88b  888     888 888  "88b  888  "88b       d88888 
    888  .88P  888     888 888  .88P  888  .88P      d88P888 
    8888888K.  888     888 8888888K.  8888888K.     d88P 888 
    888  "Y88b 888     888 888  "Y88b 888  "Y88b   d88P  888 
    888    888 888     888 888    888 888    888  d88P   888 
    888   d88P Y88b. .d88P 888   d88P 888   d88P d8888888888 
    8888888P"   "Y88888P"  8888888P"  8888888P" d88P     888

    {base_url} | Version: {os.getenv('VERSION', '1.0.0')}"""
    
    if get_terminal_width() < 80:
        print(colored(f"Bubbaverse Bootstrapper | {base_url} | Version: {os.getenv('VERSION', '1.0.0')}", 
                     Colors.MAGENTA + Colors.CYAN + Colors.ITALIC + Colors.BLACK_BG))
    else:
        print_centered(startup_text)
    
    http_client = requests.Session()
    debug(f"Setup Server: {colored(setup_url, Colors.BLUE)} | Base Server: {colored(base_url, Colors.BLUE)}")
    debug("Fetching latest client version from setup server")
    
    latest_client_version = None
    version_url = f"https://{setup_url}/version"
    version_response = http_get(http_client, version_url)
    
    if version_response is None:
        error(f"Failed to fetch latest client version from setup server, attempting fallback to {colored(fallback_setup_url, Colors.BLUE)}")
        version_url = f"https://{fallback_setup_url}/version"
        version_response = http_get(http_client, version_url)
        if version_response is None:
            error("Failed to fetch latest client version from fallback setup server, are you connected to the internet?")
            time.sleep(10)
            sys.exit(0)
        setup_url = fallback_setup_url
    
    latest_client_version = version_response.strip()
    info(f"Latest Client Version: {colored(latest_client_version, Colors.CYAN + Colors.UNDERLINE)}")
    debug(f"Setup Server: {colored(setup_url, Colors.CYAN + Colors.UNDERLINE)}")
    
    installation_directory = get_installation_directory()
    debug(f"Installation Directory: {colored(str(installation_directory), Colors.BLUE)}")
    create_folder_if_not_exists(installation_directory)
    
    versions_directory = installation_directory / "Versions"
    debug(f"Versions Directory: {colored(str(versions_directory), Colors.BLUE)}")
    create_folder_if_not_exists(versions_directory)
    
    temp_downloads_directory = installation_directory / "Downloads"
    debug(f"Temp Downloads Directory: {colored(str(temp_downloads_directory), Colors.BLUE)}")
    create_folder_if_not_exists(temp_downloads_directory)
    
    current_version_directory = versions_directory / latest_client_version
    debug(f"Current Version Directory: {colored(str(current_version_directory), Colors.BLUE)}")
    create_folder_if_not_exists(current_version_directory)
    
    latest_bootstrapper_path = current_version_directory / bootstrapper_filename
    current_exe_path = Path(sys.executable)
    
    if not str(current_exe_path).startswith(str(current_version_directory)):
        if not latest_bootstrapper_path.exists():
            info("Downloading the latest bootstrapper")
            download_url = f"https://{setup_url}/{latest_client_version}-{bootstrapper_filename}"
            download_file(http_client, download_url, latest_bootstrapper_path)
        
        latest_bootstrapper_hash = get_sha1_hash_of_file(latest_bootstrapper_path)
        current_exe_hash = get_sha1_hash_of_file(current_exe_path)
        
        debug(f"Latest Bootstrapper Hash: {colored(latest_bootstrapper_hash, Colors.BLUE)}")
        debug(f"Current Bootstrapper Hash: {colored(current_exe_hash, Colors.BLUE)}")
        
        if latest_bootstrapper_hash != current_exe_hash:
            info("Starting latest bootstrapper")
            if platform.system() == "Windows":
                try:
                    subprocess.Popen([str(latest_bootstrapper_path)] + args[1:])
                except Exception as e:
                    debug(f"Bootstrapper errored with error {e}")
                    info("Found bootstrapper was corrupted! Downloading...")
                    latest_bootstrapper_path.unlink()
                    download_file(http_client, download_url, latest_bootstrapper_path)
                    subprocess.Popen([str(latest_bootstrapper_path)] + args[1:])
                    time.sleep(20)
            else:
                os.chmod(latest_bootstrapper_path, 0o755)
                install_linux_desktop(latest_bootstrapper_path, os.getenv('VERSION', '1.0.0'))
                info("Please launch Bubbaverse from the website to continue with the update process.")
                time.sleep(20)
            sys.exit(0)
    
    app_settings_path = current_version_directory / "AppSettings.xml"
    if not app_settings_path.exists():
        info("Downloading the latest client files, this may take a while.")
        for item in current_version_directory.iterdir():
            if item != latest_bootstrapper_path:
                if item.is_file():
                    item.unlink()
                else:
                    shutil.rmtree(item)
        
        version_url_prefix = f"https://{setup_url}/{latest_client_version}-"
        client_zip = download_file_prefix(http_client, f"{version_url_prefix}2021client.zip", temp_downloads_directory)
        info("Download finished, extracting files.")
        
        client_2021_directory = current_version_directory / "Client2021"
        create_folder_if_not_exists(client_2021_directory)
        extract_to_dir(client_zip, client_2021_directory)
        
        info("Finished extracting files, cleaning up.")
        shutil.rmtree(temp_downloads_directory)
        
        info("Installing bubba-player scheme")
        if platform.system() == "Windows":
            install_windows_protocol(latest_bootstrapper_path)
        else:
            install_linux_desktop(latest_bootstrapper_path, os.getenv('VERSION', '1.0.0'))
        
        app_settings_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Settings>
    <ContentFolder>content</ContentFolder>
    <BaseUrl>http://{base_url}</BaseUrl>
</Settings>"""
        with open(app_settings_path, 'w') as f:
            f.write(app_settings_xml)
        
        for item in versions_directory.iterdir():
            if item.is_dir() and item != current_version_directory:
                shutil.rmtree(item)
    
    debug(f"Arguments Passed: {colored(' '.join(args), Colors.BLUE)}")
    if len(args) == 1:
        if platform.system() == "Windows":
            subprocess.Popen(["cmd", "/c", "start", f"https://{base_url}/games"])
        else:
            subprocess.Popen(["xdg-open", f"https://{base_url}/games"])
        sys.exit(0)
    
    main_args = args[1].replace("bubba-player://", "").split("+")
    launch_mode = ""
    authentication_ticket = ""
    join_script = ""
    client_year = ""
    
    for arg in main_args:
        parts = arg.split(":", 1)
        key = parts[0]
        value = parts[1] if len(parts) > 1 else ""
        debug(f"{colored(key, Colors.BLUE)}: {colored(value, Colors.BLUE)}")
        
        if key == "launchmode":
            launch_mode = value
        elif key == "gameinfo":
            authentication_ticket = value
        elif key == "placelauncherurl":
            join_script = value
        elif key == "clientyear":
            client_year = value
    
    custom_wine = "wine"
    if platform.system() != "Windows":
        wine_path_file = installation_directory / "winepath.txt"
        if wine_path_file.exists():
            with open(wine_path_file, 'r') as f:
                custom_wine = f.read().strip()
            info(f"Using custom wine binary: {colored(custom_wine, Colors.BLUE)}")
        else:
            info("No custom wine binary specified, using default wine command")
            info(f"If you want to use a custom wine binary, please create a file at {wine_path_file}")
    
    client_executable_path = current_version_directory / "Client2021" / "BubbaversePlayerBeta.exe"
    if not client_executable_path.exists():
        app_settings_path.unlink()
        error("Failed to run BubbaversePlayerBeta.exe, is your antivirus removing it? The bootstrapper will attempt to redownload the client on next launch.")
        time.sleep(20)
        sys.exit(0)
    
    if launch_mode == "play":
        info("Launching Bubbaverse Player")
        if platform.system() == "Windows":
            subprocess.Popen([
                str(client_executable_path),
                "--play",
                "--authenticationUrl", f"https://{base_url}/Login/Negotiate.ashx",
                "--authenticationTicket", authentication_ticket,
                "--joinScriptUrl", join_script
            ])
            time.sleep(5)
        else:
            subprocess.run([
                custom_wine,
                str(client_executable_path),
                "--play",
                "--authenticationUrl", f"https://{base_url}/Login/Negotiate.ashx",
                "--authenticationTicket", authentication_ticket,
                "--joinScriptUrl", join_script
            ])
            time.sleep(1)
        sys.exit(0)
    else:
        error("Unknown launch mode, exiting.")
        time.sleep(10)
        sys.exit(0)

if __name__ == "__main__":
    main()