"""
OpenHub In-App Auto-Updater & OTA Sync Engine
Checks local dev server for new APK builds, downloads with live progress, and triggers Android PackageInstaller.
"""
import os
import json
import time
import threading
import urllib.request
from kivy.clock import Clock
from kivy.utils import platform

DEFAULT_SERVER_HOST = "10.112.214.29:8080"
DEFAULT_GITHUB_REPO = "marcelum83/openhub-toolbox"
DEFAULT_GITHUB_BRANCH = "master"
DEFAULT_CATALOG_SOURCE = "github"
SETTINGS_FILE = "settings.json"

class UpdateManager:
    def __init__(self, app_root, current_version="1.0.0"):
        self.app_root = app_root
        self.current_version = current_version
        self.settings_path = os.path.join(app_root, SETTINGS_FILE)
        settings = self.load_settings()
        self.server_host = settings.get("server_host", DEFAULT_SERVER_HOST)
        self.github_repo = settings.get("github_repo", DEFAULT_GITHUB_REPO)
        self.github_branch = settings.get("github_branch", DEFAULT_GITHUB_BRANCH)
        self.github_token = settings.get("github_token", "")
        self.catalog_source = settings.get("catalog_source", DEFAULT_CATALOG_SOURCE)
        self.latest_update_info = None
        self.is_downloading = False
        self.local_build_ts = 0

        # Load last known build timestamp if stored
        self.load_local_meta()

    def load_settings(self):
        if os.path.exists(self.settings_path):
            try:
                with open(self.settings_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def get_api_key(self):
        data = self.load_settings()
        return data.get("gemini_api_key", os.getenv("GEMINI_API_KEY", ""))

    def get_github_repo(self):
        data = self.load_settings()
        return data.get("github_repo", self.github_repo or DEFAULT_GITHUB_REPO)

    def get_github_branch(self):
        data = self.load_settings()
        return data.get("github_branch", self.github_branch or DEFAULT_GITHUB_BRANCH)

    def get_github_token(self):
        data = self.load_settings()
        return data.get("github_token", self.github_token or "")

    def get_catalog_source(self):
        data = self.load_settings()
        return data.get("catalog_source", self.catalog_source or DEFAULT_CATALOG_SOURCE)

    def save_settings(self, server_host=None, gemini_api_key=None, github_repo=None, github_branch=None, github_token=None, catalog_source=None):
        data = self.load_settings()
        if server_host is not None:
            self.server_host = server_host.strip() or DEFAULT_SERVER_HOST
            data["server_host"] = self.server_host
        if gemini_api_key is not None:
            data["gemini_api_key"] = gemini_api_key.strip()
        if github_repo is not None:
            self.github_repo = github_repo.strip() or DEFAULT_GITHUB_REPO
            data["github_repo"] = self.github_repo
        if github_branch is not None:
            self.github_branch = github_branch.strip() or DEFAULT_GITHUB_BRANCH
            data["github_branch"] = self.github_branch
        if github_token is not None:
            self.github_token = github_token.strip()
            data["github_token"] = self.github_token
        if catalog_source is not None:
            self.catalog_source = catalog_source.strip() or DEFAULT_CATALOG_SOURCE
            data["catalog_source"] = self.catalog_source
        try:
            with open(self.settings_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[UpdateManager] Error saving settings: {e}")

    def load_server_host(self):
        return self.server_host

    def save_server_host(self, host):
        self.save_settings(server_host=host)

    def load_local_meta(self):
        meta_file = os.path.join(self.app_root, "installed_meta.json")
        if os.path.exists(meta_file):
            try:
                with open(meta_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.local_build_ts = data.get("build_timestamp", 0)
            except Exception:
                pass

    def save_installed_meta(self, build_ts, version):
        self.local_build_ts = build_ts
        meta_file = os.path.join(self.app_root, "installed_meta.json")
        try:
            with open(meta_file, 'w', encoding='utf-8') as f:
                json.dump({"build_timestamp": build_ts, "version": version}, f)
        except Exception:
            pass

    def check_for_updates(self, on_result=None):
        """Asynchronously queries the server version.json endpoint."""
        def _worker():
            host = self.server_host
            url = f"http://{host}/version.json"
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'OpenHub-Client'})
                with urllib.request.urlopen(req, timeout=3.5) as resp:
                    if resp.status == 200:
                        raw = resp.read().decode('utf-8')
                        data = json.loads(raw)
                        server_ts = data.get("build_timestamp", 0)
                        server_ver = data.get("version", "1.0.0")
                        
                        has_update = False
                        if self.local_build_ts == 0:
                            # First time check: compare if server exists
                            has_update = True
                        elif server_ts > self.local_build_ts:
                            has_update = True
                        
                        self.latest_update_info = data
                        if on_result:
                            Clock.schedule_once(lambda dt: on_result(has_update, data, None), 0)
                        return
            except Exception as e:
                if on_result:
                    Clock.schedule_once(lambda dt, err=e: on_result(False, None, str(err)), 0)

        t = threading.Thread(target=_worker, daemon=True)
        t.start()

    def start_download_and_install(self, update_info, on_progress=None, on_complete=None):
        """Downloads APK in chunks with progress reporting and opens installer."""
        if self.is_downloading:
            return
        self.is_downloading = True

        def _download_worker():
            try:
                apk_name = update_info.get("apk_filename", "openhub-1.0.0-arm64-v8a-debug.apk")
                url = f"http://{self.server_host}/{apk_name}"
                
                # Determine download destination
                if platform == 'android':
                    from jnius import autoclass
                    Environment = autoclass('android.os.Environment')
                    dl_dir = Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS).getAbsolutePath()
                    dest_path = os.path.join(dl_dir, "openhub_update.apk")
                else:
                    dest_path = os.path.join(self.app_root, "bin", "openhub_update.apk")
                    os.makedirs(os.path.dirname(dest_path), exist_ok=True)

                req = urllib.request.Request(url, headers={'User-Agent': 'OpenHub-Client'})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    total_size = int(resp.headers.get('Content-Length', 0))
                    downloaded = 0
                    chunk_size = 65536 # 64 KB

                    with open(dest_path, 'wb') as f:
                        while True:
                            chunk = resp.read(chunk_size)
                            if not chunk:
                                break
                            f.write(chunk)
                            downloaded += len(chunk)
                            percent = (downloaded / total_size * 100.0) if total_size > 0 else 0.0
                            if on_progress:
                                Clock.schedule_once(lambda dt, p=percent, d=downloaded, t_s=total_size: on_progress(p, d, t_s), 0)

                self.is_downloading = False
                
                # Save meta on successful download
                self.save_installed_meta(update_info.get("build_timestamp", 0), update_info.get("version", "1.0.0"))

                # Launch installer intent
                success = self.install_apk(dest_path, url)
                if on_complete:
                    Clock.schedule_once(lambda dt, s=success, p=dest_path: on_complete(s, p, None), 0)

            except Exception as e:
                self.is_downloading = False
                if on_complete:
                    Clock.schedule_once(lambda dt, err=e: on_complete(False, None, str(err)), 0)

        t = threading.Thread(target=_download_worker, daemon=True)
        t.start()

    def install_apk(self, apk_path, fallback_url=None):
        """Triggers native Android package installer intent or browser fallback."""
        if platform == 'android':
            try:
                from jnius import autoclass
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                Intent = autoclass('android.content.Intent')
                Uri = autoclass('android.net.Uri')
                File = autoclass('java.io.File')
                
                file_obj = File(apk_path)
                intent = Intent(Intent.ACTION_VIEW)
                
                try:
                    FileProvider = autoclass('androidx.core.content.FileProvider')
                    context = PythonActivity.mActivity.getApplicationContext()
                    uri = FileProvider.getUriForFile(context, "org.nexus.openhub.fileprovider", file_obj)
                    intent.setDataAndType(uri, "application/vnd.android.package-archive")
                    intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                except Exception:
                    uri = Uri.fromFile(file_obj)
                    intent.setDataAndType(uri, "application/vnd.android.package-archive")

                intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                PythonActivity.mActivity.startActivity(intent)
                return True
            except Exception as e:
                print(f"[UpdateManager] Native install intent error: {e}")
                # Fallback to opening browser URL
                try:
                    import webbrowser
                    if fallback_url:
                        webbrowser.open(fallback_url)
                        return True
                except Exception:
                    pass
        else:
            print(f"[UpdateManager] Desktop simulation: downloaded APK to {apk_path}")
            return True
        return False
