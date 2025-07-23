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
import psutil
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
MAX_FILE_SIZE = 500 * 1024 * 1024

def center_text(text, color=Fore.BLUE):
    try:
        columns = os.get_terminal_size().columns
    except:
        columns = 80
    return "\n".join(color + line.center(columns) + Style.RESET_ALL for line in text.split("\n"))

def check_memory_safety(required_bytes):
    available = psutil.virtual_memory().available
    if required_bytes > available * 0.8:
        raise MemoryError(f"Insufficient memory (needed: {required_bytes}, available: {available})")

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
                return response.read().decode('utf-8').strip()
        except Exception as e:
            Logger.debug(f"Error fetching {url}: {e}")
            return None

    @staticmethod
    def download_file(url: str, path: Path) -> bool:
        Logger.debug(f"GET {url}")
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Bubbaverse Launcher'})
            with urllib.request.urlopen(req) as response:
                total_size = min(int(response.headers.get('content-length', 0)), MAX_FILE_SIZE)
                check_memory_safety(total_size)
                with tqdm(total=total_size, unit='iB', unit_scale=True, desc=f"Downloading {path.name}") as progress_bar:
                    with open(path, 'wb') as f:
                        for chunk in iter(lambda: response.read(65536), b''):
                            f.write(chunk)
                            progress_bar.update(len(chunk))
                            if progress_bar.n > MAX_FILE_SIZE:
                                raise MemoryError("File too large")
            return True
        except Exception as e:
            Logger.error(f"Download failed: {e}")
            return False

class FileUtils:
    @staticmethod
    def generate_md5(input_str: str) -> str:
        return hashlib.md5(input_str.encode()).hexdigest()

    @staticmethod
    def get_sha1_hash_of_file(path: Path) -> str:
        sha1 = hashlib.sha1()
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(65536), b''):
                sha1.update(chunk)
        return sha1.hexdigest()

    @staticmethod
    def create_folder_if_not_exists(path: Path) -> None:
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def extract_zip(zip_file: Path, target_dir: Path) -> bool:
        try:
            with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                total_size = sum(file.file_size for file in zip_ref.infolist())
                check_memory_safety(total_size)
                zip_ref.extractall(target_dir)
            return True
        except Exception as e:
            Logger.error(f"Extraction failed: {e}")
            return False

class SystemUtils:
    @staticmethod
    def get_installation_directory() -> Path:
        if platform.system() == "Windows":
            return Path(os.getenv('LOCALAPPDATA')) / "Bubbaverse"
        return Path.home() / ".local" / "Bubbaverse"

    @staticmethod
    def clear_terminal() -> None:
        os.system('cls' if platform.system() == "Windows" else 'clear')

    @staticmethod
    def register_url_scheme(bootstrapper_path: Path) -> None:
        if platform.system() == "Windows":
            try:
                import winreg
                with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\\Classes\\bubba-player") as key:
                    winreg.SetValue(key, '', winreg.REG_SZ, 'URL:BubbaVerse Protocol')
                    winreg.SetValueEx(key, 'URL Protocol', 0, winreg.REG_SZ, '')
                    with winreg.CreateKey(key, 'shell\\open\\command') as cmd_key:
                        winreg.SetValue(cmd_key, '', winreg.REG_SZ, f'"{bootstrapper_path}" "%1"')
            except Exception as e:
                Logger.error(f"Registry error: {e}")
        elif platform.system() == "Linux":
            try:
                import subprocess
                from pathlib import Path
                desktop_dir = Path.home() / ".local/share/applications"
                desktop_dir.mkdir(parents=True, exist_ok=True)
                desktop_file = desktop_dir / "bubba-player.desktop"
                exec_path = str(bootstrapper_path.resolve())
                # Check if already registered
                mime_query = subprocess.run([
                    "xdg-mime", "query", "default", "x-scheme-handler/bubba-player"
                ], capture_output=True, text=True)
                if mime_query.returncode == 0 and "bubba-player.desktop" in mime_query.stdout:
                    Logger.info("bubba-player scheme already registered.")
                    return
                # Write .desktop file
                desktop_content = f"""[Desktop Entry]
Name=BubbaVerse Player Launcher
Exec={exec_path} %u
Type=Application
Terminal=false
NoDisplay=true
MimeType=x-scheme-handler/bubba-player;
"""
                with open(desktop_file, "w") as f:
                    f.write(desktop_content)
                # Register the handler
                subprocess.run(["update-desktop-database", str(desktop_dir)], check=False)
                subprocess.run([
                    "xdg-mime", "default", "bubba-player.desktop", "x-scheme-handler/bubba-player"
                ], check=False)
                Logger.info("Registered bubba-player URL scheme for this user.")
            except Exception as e:
                Logger.error(f"Failed to register URL scheme on Linux: {e}")

def get_version_info():
    try:
        if getattr(sys, 'frozen', False):
            import win32api
            info = win32api.GetFileVersionInfo(sys.executable, '\\')
            return "%d.%d.%d.%d" % (
                info['FileVersionMS'] / 65536,
                info['FileVersionMS'] % 65536,
                info['FileVersionLS'] / 65536,
                info['FileVersionLS'] % 65536
            )
    except:
        pass
    version_path = Path(__file__).parent / 'version'
    if version_path.exists():
        with open(version_path, 'r') as f:
            version = f.read().strip()
            if version.startswith('version-'):
                return version[8:]
            return version
    return BUILD_DATE

class Bootstrapper:
    def __init__(self):
        self.args = sys.argv
        self.installation_dir = SystemUtils.get_installation_directory()
        self.versions_dir = self.installation_dir / "Versions"
        self.temp_dir = self.installation_dir / "Downloads"
        self.setup_url = SETUP_URL
        self.latest_version = None
        self.current_version_dir = None

    def display_startup_text(self) -> None:
        SystemUtils.clear_terminal()
        version = get_version_info()
        banner = f"""
        888888b.            888      888               
        888  "88b           888      888               
        888  .88P           888      888               
        8888888K.  888  888 88888b.  88888b.   8888b.  
        888  "Y88b 888  888 888 "88b 888 "88b     "88b 
        888    888 888  888 888  888 888  888 .d888888 
        888   d88P Y88b 888 888 d88P 888 d88P 888  888 
        8888888P"   "Y88888 88888P"  88888P"  "Y888888

       {BASE_URL} | Build Date: {BUILD_DATE} | Version: {version}"""
        print(center_text(banner))

    def get_latest_version(self) -> bool:
        for url in [f"https://{self.setup_url}/version", 
                   f"{FALLBACK_SETUP_URL}/version",
                   f"http://{self.setup_url}/version"]:
            version = HttpClient.get(url)
            if version:
                self.latest_version = version.strip()
                clean_version = ''.join(c for c in self.latest_version if c.isalnum())
                self.setup_url = url.split('/')[2]
                Logger.info(f"Latest Version: {self.latest_version}")
                self.current_version_dir = self.versions_dir / clean_version
                return True
            time.sleep(1)
        Logger.error("Version check failed")
        return False

    def setup_directories(self) -> None:
        FileUtils.create_folder_if_not_exists(self.installation_dir)
        FileUtils.create_folder_if_not_exists(self.versions_dir)
        FileUtils.create_folder_if_not_exists(self.temp_dir)
        FileUtils.create_folder_if_not_exists(self.current_version_dir)

    def download_bootstrapper(self) -> bool:
        bootstrapper_path = self.current_version_dir / BOOTSTRAPPER_FILENAME
        if not bootstrapper_path.exists():
            url = f"https://{self.setup_url}/{self.latest_version}-{BOOTSTRAPPER_FILENAME}"
            if not HttpClient.download_file(url, bootstrapper_path):
                return False
        if platform.system() != "Windows":
            os.chmod(bootstrapper_path, 0o755)
        return True

    def run_latest_bootstrapper(self) -> None:
        bootstrapper_path = self.current_version_dir / BOOTSTRAPPER_FILENAME
        if FileUtils.get_sha1_hash_of_file(Path(sys.argv[0])) != FileUtils.get_sha1_hash_of_file(bootstrapper_path):
            try:
                subprocess.Popen([str(bootstrapper_path)] + self.args[1:])
                sys.exit(0)
            except Exception as e:
                Logger.error(f"Launch failed: {e}")
                sys.exit(1)

    def download_client_files(self) -> bool:
        bootstrapper_path = self.current_version_dir / BOOTSTRAPPER_FILENAME
        for item in self.current_version_dir.iterdir():
            if item != bootstrapper_path:
                shutil.rmtree(item) if item.is_dir() else item.unlink()
        
        zip_url = f"https://{self.setup_url}/{self.latest_version}-2021client.zip"
        zip_path = self.temp_dir / FileUtils.generate_md5(zip_url)
        
        if not HttpClient.download_file(zip_url, zip_path):
            return False
            
        if not FileUtils.extract_zip(zip_path, self.current_version_dir / "Client2021"):
            return False
            
        SystemUtils.register_url_scheme(bootstrapper_path)
        with open(self.current_version_dir / "AppSettings.xml", 'w') as f:
            f.write(f"""<?xml version="1.0" encoding="UTF-8"?>
<Settings>
    <ContentFolder>content</ContentFolder>
    <BaseUrl>http://{BASE_URL}</BaseUrl>
</Settings>""")
        return True

    def parse_launch_args(self) -> Tuple[str, str, str, str]:
        if len(self.args) == 1:
            return ("", "", "", "")
        parts = self.args[1].replace("bubba-player://", "").split("+")
        result = ["", "", "", ""]
        for part in parts:
            if ":" in part:
                key, value = part.split(":", 1)
                if key == "launchmode": result[0] = value
                elif key == "gameinfo": result[1] = value
                elif key == "placelauncherurl": result[2] = value
                elif key == "clientyear": result[3] = value
        return tuple(result)

    def launch_game(self, launch_mode: str, auth_ticket: str, join_script: str) -> bool:
        if launch_mode != "play":
            Logger.error("Invalid launch mode")
            return False
            
        client_path = self.current_version_dir / "Client2021" / "BubbaversePlayerBeta.exe"
        if not client_path.exists():
            Logger.error(f"Client not found at {client_path}")
            return False
            
        args = [str(client_path), "--play",
               "--authenticationUrl", f"https://{BASE_URL}/Login/Negotiate.ashx",
               "--authenticationTicket", auth_ticket,
               "--joinScriptUrl", join_script]
               
        try:
            if platform.system() == "Windows":
                creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP
                process = subprocess.Popen(args, creationflags=creation_flags)
                time.sleep(2)
                return True
            else:
                wine_path = Path(self.installation_dir / "winepath.txt").read_text().strip() if (
                    self.installation_dir / "winepath.txt").exists() else "wine"
                subprocess.run([wine_path] + args)
                time.sleep(2)
                return True
        except Exception as e:
            Logger.error(f"Game launch failed: {e}")
            return False

    def run(self) -> None:
        # Register URL scheme as the very first thing
        SystemUtils.register_url_scheme(Path(sys.argv[0]))
        self.display_startup_text()
        
        if not self.get_latest_version():
            time.sleep(10)
            sys.exit(1)
        
        self.setup_directories()
        
        if not self.download_bootstrapper():
            time.sleep(10)
            sys.exit(1)
        
        self.run_latest_bootstrapper()
        
        if not (self.current_version_dir / "AppSettings.xml").exists():
            Logger.info("Downloading client files...")
            if not self.download_client_files():
                Logger.error("Failed to download client files")
                time.sleep(10)
                sys.exit(1)
        
        if len(self.args) > 1:
            mode, ticket, script, _ = self.parse_launch_args()
            if mode == "play":
                Logger.info("Launching game...")
                if not self.launch_game(mode, ticket, script):
                    time.sleep(10)
                    sys.exit(1)
        else:
            Logger.info("Opening website...")
            if platform.system() == "Windows":
                subprocess.Popen(["cmd", "/c", "start", f"https://{BASE_URL}/games"])
            else:
                subprocess.Popen(["xdg-open", f"https://{BASE_URL}/games"])
            sys.exit(0)

if __name__ == "__main__":
    try:
        if psutil.virtual_memory().available < 100 * 1024 * 1024:
            Logger.error("Low system memory")
            time.sleep(10)
            sys.exit(1)
        Bootstrapper().run()
    except MemoryError as e:
        Logger.error(f"Memory error: {e}")
        time.sleep(10)
        sys.exit(1)
    except Exception as e:
        Logger.error(f"Fatal error: {e}")
        time.sleep(10)
        sys.exit(1)