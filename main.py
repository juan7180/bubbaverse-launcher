import os
import sys
import hashlib
import urllib.request
import urllib.error
import time
import shutil
import zipfile
import platform
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple
from tqdm import tqdm
import colorama
from colorama import Fore, Style

colorama.init()

BASE_URL = "www.boblox.org"
SETUP_URL = "setup.boblox.org"
FALLBACK_SETUP_URL = "https://setup.boblox.org"
BOOTSTRAPPER_FILENAME = "BubbaversePlayerLauncher.exe" if platform.system() == "Windows" else "BubbaversePlayerLinuxLauncher"
BUILD_DATE = datetime.now().strftime("%Y-%m-%d")

def center_text(text, color=Fore.BLUE):
    try:
        columns = os.get_terminal_size().columns
    except:
        columns = 80
    return "\n".join(color + line.center(columns) + Style.RESET_ALL for line in text.split("\n"))

class Logger:
    @staticmethod
    def _get_time() -> str:
        return datetime.now().strftime("%H:%M:%S")

    @staticmethod
    def info(message: str) -> None:
        time_str = Logger._get_time()
        print(f"{Fore.BLUE}[{time_str}]{Style.RESET_ALL} [{Fore.GREEN}INFO{Style.RESET_ALL}] {message}")

    @staticmethod
    def error(message: str) -> None:
        time_str = Logger._get_time()
        print(f"{Fore.BLUE}[{time_str}]{Style.RESET_ALL} [{Fore.RED}ERROR{Style.RESET_ALL}] {message}")

    @staticmethod
    def debug(message: str) -> None:
        if __debug__:
            time_str = Logger._get_time()
            print(f"{Fore.BLUE}[{time_str}]{Style.RESET_ALL} [{Fore.YELLOW}DEBUG{Style.RESET_ALL}] {message}")

class HttpClient:
    @staticmethod
    def get(url: str, timeout=10) -> Optional[str]:
        Logger.debug(f"GET {url}")
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Bubbaverse Launcher'})
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return response.read().decode('utf-8')
        except urllib.error.URLError as e:
            Logger.debug(f"Failed to fetch {url}: {e}")
            return None
        except Exception as e:
            Logger.debug(f"Unexpected error fetching {url}: {e}")
            return None

    @staticmethod
    def download_file(url: str, path: Path) -> bool:
        Logger.debug(f"GET {url}")
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Bubbaverse Launcher'})
            response = urllib.request.urlopen(req)
            total_size = int(response.headers.get('content-length', 0))
            block_size = 1024
            
            with tqdm(
                total=total_size,
                unit='iB',
                unit_scale=True,
                desc=f"Downloading {path.name}",
                bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}{postfix}]"
            ) as progress_bar:
                with open(path, 'wb') as f:
                    while True:
                        buffer = response.read(block_size)
                        if not buffer:
                            break
                        f.write(buffer)
                        progress_bar.update(len(buffer))
            return True
        except urllib.error.URLError as e:
            Logger.error(f"Failed to download {url}: {e}")
            return False
        except Exception as e:
            Logger.error(f"Unexpected error during download: {e}")
            return False

class FileUtils:
    @staticmethod
    def generate_md5(input_str: str) -> str:
        return hashlib.md5(input_str.encode()).hexdigest()

    @staticmethod
    def get_sha1_hash_of_file(path: Path) -> str:
        sha1 = hashlib.sha1()
        with open(path, 'rb') as f:
            while True:
                data = f.read(65536)
                if not data:
                    break
                sha1.update(data)
        return sha1.hexdigest()

    @staticmethod
    def create_folder_if_not_exists(path: Path) -> None:
        if not path.exists():
            Logger.info(f"Creating folder {path}")
            path.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def extract_zip(zip_file: Path, target_dir: Path) -> bool:
        Logger.info(f"Extracting {zip_file} to {target_dir}")
        try:
            with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                zip_ref.extractall(target_dir)
            return True
        except zipfile.BadZipFile as e:
            Logger.error(f"Failed to extract {zip_file}: {e}")
            return False

class SystemUtils:
    @staticmethod
    def get_installation_directory() -> Path:
        if platform.system() == "Windows":
            return Path(os.getenv('LOCALAPPDATA')) / "Bubbaverse"
        else:
            return Path.home() / ".local" / "Bubbaverse"

    @staticmethod
    def clear_terminal() -> None:
        if platform.system() == "Windows":
            os.system('cls')
        else:
            os.system('clear')

    @staticmethod
    def register_url_scheme(bootstrapper_path: Path) -> None:
        if platform.system() == "Windows":
            try:
                import winreg
                hkey = winreg.HKEY_CURRENT_USER
                with winreg.CreateKey(hkey, r"Software\Classes\bubba-player") as key:
                    winreg.SetValue(key, '', winreg.REG_SZ, 'URL:BubbaVerse Protocol')
                    winreg.SetValueEx(key, 'URL Protocol', 0, winreg.REG_SZ, '')
                    with winreg.CreateKey(key, 'shell\\open\\command') as cmd_key:
                        winreg.SetValue(cmd_key, '', winreg.REG_SZ, f'"{bootstrapper_path}" "%1"')
                    with winreg.CreateKey(key, 'DefaultIcon') as icon_key:
                        winreg.SetValue(icon_key, '', winreg.REG_SZ, f'"{bootstrapper_path}",0')
            except Exception as e:
                Logger.error(f"Failed to register URL scheme: {e}")
        else:
            desktop_file = f"""[Desktop Entry]
Name=Bubbaverse Launcher
Exec={bootstrapper_path} %u
Icon={bootstrapper_path}
Type=Application
Terminal=true
Version={BUILD_DATE}
MimeType=x-scheme-handler/bubba-player;"""
            desktop_path = Path.home() / '.local' / 'share' / 'applications' / 'bubba-player.desktop'
            try:
                with open(desktop_path, 'w') as f:
                    f.write(desktop_file)
                os.chmod(desktop_path, 0o755)
            except Exception as e:
                Logger.error(f"Failed to create desktop file: {e}")

def get_version_info():
    try:
        if getattr(sys, 'frozen', False):
            try:
                import win32api
                info = win32api.GetFileVersionInfo(sys.executable, '\\')
                version = "%d.%d.%d.%d" % (
                    info['FileVersionMS'] / 65536,
                    info['FileVersionMS'] % 65536,
                    info['FileVersionLS'] / 65536,
                    info['FileVersionLS'] % 65536
                )
                return version
            except:
                pass
    except:
        pass
    return BUILD_DATE

class Bootstrapper:
    def __init__(self):
        self.args = sys.argv
        self.http_client = HttpClient
        self.file_utils = FileUtils
        self.system_utils = SystemUtils
        self.logger = Logger
        self.installation_dir = self.system_utils.get_installation_directory()
        self.versions_dir = self.installation_dir / "Versions"
        self.temp_dir = self.installation_dir / "Downloads"
        self.setup_url = SETUP_URL
        self.latest_version = None
        self.current_version_dir = None

    def display_startup_text(self) -> None:
        self.system_utils.clear_terminal()
        version = get_version_info()
        startup_text = f"""
        888888b.            888      888               
        888  "88b           888      888               
        888  .88P           888      888               
        8888888K.  888  888 88888b.  88888b.   8888b.  
        888  "Y88b 888  888 888 "88b 888 "88b     "88b 
        888    888 888  888 888  888 888  888 .d888888 
        888   d88P Y88b 888 888 d88P 888 d88P 888  888 
        8888888P"   "Y88888 88888P"  88888P"  "Y888888

       {BASE_URL} | Build Date: {BUILD_DATE} | Version: {version}"""
        print(center_text(startup_text))

    def get_latest_version(self) -> bool:
        version_urls = [
            f"https://{self.setup_url}/version",
            f"{FALLBACK_SETUP_URL}/version",
            f"http://{self.setup_url}/version"
        ]
        
        for url in version_urls:
            self.latest_version = self.http_client.get(url)
            if self.latest_version:
                self.setup_url = url.split('/')[2]
                self.logger.info(f"Latest Client Version: {self.latest_version}")
                self.current_version_dir = self.versions_dir / self.latest_version
                return True
            time.sleep(1)
        
        self.logger.error("Failed to fetch version from all servers")
        return False

    def setup_directories(self) -> None:
        self.file_utils.create_folder_if_not_exists(self.installation_dir)
        self.file_utils.create_folder_if_not_exists(self.versions_dir)
        self.file_utils.create_folder_if_not_exists(self.temp_dir)
        self.file_utils.create_folder_if_not_exists(self.current_version_dir)

    def download_bootstrapper(self) -> bool:
        bootstrapper_path = self.current_version_dir / BOOTSTRAPPER_FILENAME
        download_url = f"https://{self.setup_url}/{self.latest_version}-{BOOTSTRAPPER_FILENAME}"
        if not bootstrapper_path.exists():
            self.logger.info("Downloading latest bootstrapper")
            if not self.http_client.download_file(download_url, bootstrapper_path):
                return False
        if platform.system() != "Windows":
            os.chmod(bootstrapper_path, 0o755)
        return True

    def run_latest_bootstrapper(self) -> None:
        bootstrapper_path = self.current_version_dir / BOOTSTRAPPER_FILENAME
        current_hash = self.file_utils.get_sha1_hash_of_file(Path(sys.argv[0]))
        latest_hash = self.file_utils.get_sha1_hash_of_file(bootstrapper_path)
        if current_hash != latest_hash:
            self.logger.info("Starting latest bootstrapper")
            try:
                args = [str(bootstrapper_path)] + self.args[1:]
                subprocess.Popen(args)
                sys.exit(0)
            except Exception as e:
                self.logger.error(f"Failed to start bootstrapper: {e}")
                sys.exit(1)

    def download_client_files(self) -> bool:
        self.logger.info("Downloading client files")
        bootstrapper_path = self.current_version_dir / BOOTSTRAPPER_FILENAME
        for item in self.current_version_dir.iterdir():
            if item != bootstrapper_path:
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()
        version_url_prefix = f"https://{self.setup_url}/{self.latest_version}-"
        client_zip_url = f"{version_url_prefix}2021client.zip"
        client_zip_path = self.temp_dir / self.file_utils.generate_md5(client_zip_url)
        if not self.http_client.download_file(client_zip_url, client_zip_path):
            return False
        client_dir = self.current_version_dir / "Client2021"
        self.file_utils.create_folder_if_not_exists(client_dir)
        if not self.file_utils.extract_zip(client_zip_path, client_dir):
            return False
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        self.system_utils.register_url_scheme(bootstrapper_path)
        app_settings = f"""<?xml version="1.0" encoding="UTF-8"?>
<Settings>
    <ContentFolder>content</ContentFolder>
    <BaseUrl>http://{BASE_URL}</BaseUrl>
</Settings>"""
        with open(self.current_version_dir / "AppSettings.xml", 'w') as f:
            f.write(app_settings)
        for item in self.versions_dir.iterdir():
            if item.is_dir() and item != self.current_version_dir:
                shutil.rmtree(item, ignore_errors=True)
        return True

    def parse_launch_args(self) -> Tuple[str, str, str, str]:
        if len(self.args) == 1:
            return ("", "", "", "")
        main_arg = self.args[1].replace("bubba-player://", "")
        parts = main_arg.split("+")
        launch_mode = ""
        auth_ticket = ""
        join_script = ""
        client_year = ""
        for part in parts:
            if ":" in part:
                key, value = part.split(":", 1)
                if key == "launchmode":
                    launch_mode = value
                elif key == "gameinfo":
                    auth_ticket = value
                elif key == "placelauncherurl":
                    join_script = value
                elif key == "clientyear":
                    client_year = value
        return (launch_mode, auth_ticket, join_script, client_year)

    def launch_game(self, launch_mode: str, auth_ticket: str, join_script: str) -> bool:
        if launch_mode != "play":
            self.logger.error("Unknown launch mode")
            return False
        client_path = self.current_version_dir / "Client2021" / "BubbaversePlayerBeta.exe"
        if not client_path.exists():
            self.logger.error("Client executable not found")
            return False
        self.logger.info("Launching Bubbaverse Player")
        args = [
            str(client_path),
            "--play",
            "--authenticationUrl", f"https://{BASE_URL}/Login/Negotiate.ashx",
            "--authenticationTicket", auth_ticket,
            "--joinScriptUrl", join_script
        ]
        if platform.system() == "Windows":
            subprocess.Popen(args)
        else:
            wine_path = self._get_wine_path()
            args = [wine_path] + args
            subprocess.run(args)
        return True

    def _get_wine_path(self) -> str:
        wine_path_file = self.installation_dir / "winepath.txt"
        if wine_path_file.exists():
            with open(wine_path_file, 'r') as f:
                custom_wine = f.read().strip()
                self.logger.info(f"Using custom wine binary: {custom_wine}")
                return custom_wine
        return "wine"

    def run(self) -> None:
        self.display_startup_text()
        if not self.get_latest_version():
            time.sleep(10)
            sys.exit(1)
        self.setup_directories()
        if not self.download_bootstrapper():
            time.sleep(10)
            sys.exit(1)
        self.run_latest_bootstrapper()
        app_settings_path = self.current_version_dir / "AppSettings.xml"
        if not app_settings_path.exists():
            if not self.download_client_files():
                time.sleep(10)
                sys.exit(1)
        launch_mode, auth_ticket, join_script, _ = self.parse_launch_args()
        if not launch_mode:
            if platform.system() == "Windows":
                subprocess.Popen(["cmd", "/c", "start", f"https://{BASE_URL}/games"])
            else:
                subprocess.Popen(["xdg-open", f"https://{BASE_URL}/games"])
            sys.exit(0)
        if not self.launch_game(launch_mode, auth_ticket, join_script):
            time.sleep(10)
            sys.exit(1)

if __name__ == "__main__":
    try:
        bootstrapper = Bootstrapper()
        bootstrapper.run()
    except Exception as e:
        Logger.error(f"Fatal error: {e}")
        time.sleep(10)