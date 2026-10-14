from __future__ import annotations

import json
import os
import sys
import threading
import time
import uuid
import webbrowser
from pathlib import Path

import yt_dlp
from yt_dlp.utils import DownloadCancelled

APP_NAME = "Luma Downloader"
DEFAULT_FOLDER = Path.home() / "Downloads" / "Luma Downloader"
FFMPEG_PAGE = "https://ffmpeg.org/download.html"


def send(event, **data):
    sys.stdout.write(json.dumps({"event": event, **data}, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def quality_label(mode, quality):
    if mode == "Áudio":
        return quality
    return {"Melhor qualidade": "MP4 · melhor qualidade", "1080p": "MP4 · até 1080p",
            "720p": "MP4 · até 720p", "480p": "MP4 · até 480p"}.get(quality, "MP4")


def make_job(url, category, title, thumbnail, fmt, folder, mode, quality, count=0):
    return {"id": uuid.uuid4().hex, "url": url, "category": category, "title": title,
            "thumbnail": thumbnail or "", "format": fmt, "folder": str(Path(folder)), "mode": mode,
            "quality": quality, "count": int(count or 0), "status": "Na fila", "final": "", "size": 0,
            "progress": 0, "downloaded": 0, "total": 0, "speed": 0, "eta": None}


def is_ffmpeg_error(message):
    lower = message.lower()
    return "ffmpeg" in lower or "ffprobe" in lower or "ffmpegextractaudio" in lower


def friendly_error(exc):
    message, lower = str(exc), str(exc).lower()
    if is_ffmpeg_error(message):
        return "O Luma não encontrou o FFmpeg, necessário para converter áudio e combinar algumas faixas de vídeo."
    if any(term in lower for term in ("429", "too many requests", "rate limit", "throttl")):
        return "O site limitou temporariamente as solicitações. Aguarde e tente novamente mais tarde."
    if "403" in lower or "forbidden" in lower:
        return "O YouTube recusou esta requisição (HTTP 403). A URL temporária pode ter expirado ou o conteúdo pode estar indisponível para esta solicitação. Atualize o Luma/yt-dlp e tente novamente mais tarde; o aplicativo não contorna controles de acesso.\n\nDetalhe: " + message
    if any(term in lower for term in ("sign in", "login", "members-only", "private video", "confirm you are not a bot")):
        return "Este conteúdo exige autenticação ou está restrito. Confira se você tem acesso permitido."
    if "unavailable" in lower or "not available" in lower:
        return "Este conteúdo não está disponível. Confira o link e as permissões do vídeo."
    return f"Não foi possível concluir. Atualize o Luma/yt-dlp e tente novamente.\n\nDetalhe: {message}"


class Service:
    def __init__(self, settings_path):
        self.settings_path = Path(settings_path)
        self.settings_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self.settings = json.loads(self.settings_path.read_text(encoding="utf-8"))
        except Exception:
            self.settings = self.read_legacy_qsettings()
        self.settings.setdefault("videoFolder", str(DEFAULT_FOLDER / "Vídeos"))
        self.settings.setdefault("audioFolder", str(DEFAULT_FOLDER / "Áudios"))
        self.settings.setdefault("automatic", True)
        self.settings.setdefault("notifications", True)
        self.settings.setdefault("dark", True)
        self.settings.setdefault("ffmpegLocation", "")
        self.queue = []
        self.history_path = self.settings_path.with_name("history.json")
        try:
            self.history = json.loads(self.history_path.read_text(encoding="utf-8"))
            if not isinstance(self.history, list): self.history = []
        except Exception:
            self.history = []
        self.playlist = None
        self.lock = threading.RLock()
        self.io_lock = threading.Lock()
        self.busy = False
        self.inspecting = False
        self.cancel = threading.Event()
        self.pause = threading.Event()
        self.current_id = ""
        self.download_thread = None
        self.emit_snapshot()

    @staticmethod
    def read_legacy_qsettings():
        """Migrate the former Qt preferences on first Electron launch."""
        if os.name != "nt": return {}
        try:
            import winreg
            base = r"Software\Luma\Downloader"
            found = {}
            def visit(key, prefix=""):
                i = 0
                while True:
                    try: name, value, _ = winreg.EnumValue(key, i)
                    except OSError: break
                    found[(prefix + "/" + name).strip("/").replace("\\", "/").lower()] = value
                    i += 1
                i = 0
                while True:
                    try: name = winreg.EnumKey(key, i)
                    except OSError: break
                    try:
                        with winreg.OpenKey(key, name) as child: visit(child, (prefix + "/" + name).strip("/"))
                    except OSError: pass
                    i += 1
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, base) as root: visit(root)
            mappings = {"folder/video":"videoFolder", "folder/audio":"audioFolder", "theme/dark":"dark",
                "downloads/auto_start":"automatic", "notifications/completed":"notifications", "ffmpeg/location":"ffmpegLocation"}
            migrated = {}
            for old, new in mappings.items():
                if old not in found: continue
                value = found[old]
                migrated[new] = bool(value) if new in ("dark", "automatic", "notifications") else str(value)
            return migrated
        except OSError:
            return {}

    def emit(self, event, **data):
        with self.io_lock:
            send(event, **data)

    def save_settings(self):
        temp = self.settings_path.with_suffix(".tmp")
        temp.write_text(json.dumps(self.settings, ensure_ascii=False, indent=2), encoding="utf-8")
        temp.replace(self.settings_path)

    def emit_snapshot(self):
        self.emit("snapshot", settings=self.settings, queue=self.queue, history=self.history, playlist=self.playlist, busy=self.busy)

    def changed(self):
        self.emit("queue", queue=self.queue, history=self.history, busy=self.busy)

    def record_history(self, job):
        if job.get("status") not in ("Concluído", "Falhou", "Cancelado"):
            return
        job["finishedAt"] = time.time()
        self.history = [item for item in self.history if item.get("id") != job.get("id")]
        self.history.append(dict(job))
        self.history = self.history[-300:]
        try:
            temp = self.history_path.with_suffix(".tmp")
            temp.write_text(json.dumps(self.history, ensure_ascii=False, indent=2), encoding="utf-8")
            temp.replace(self.history_path)
        except OSError:
            pass

    def command(self, message):
        cmd = message.get("command")
        if cmd == "setSetting":
            key = message.get("key")
            if key in {"automatic", "notifications", "dark", "ffmpegLocation"}:
                self.settings[key] = message.get("value")
                self.save_settings()
                self.emit("settings", settings=self.settings)
                if key == "automatic" and self.settings[key]: self.start_queue()
        elif cmd == "setFolder":
            key = "videoFolder" if message.get("kind") == "video" else "audioFolder"
            self.settings[key] = message.get("path") or self.settings[key]
            self.save_settings(); self.emit("settings", settings=self.settings)
        elif cmd == "inspect":
            with self.lock:
                if not self.inspecting: self.inspecting = True
                else:
                    self.emit("error", kind="busy", message="Aguarde a análise atual terminar."); return
            self.changed()
            threading.Thread(target=self.inspect, args=(message,), daemon=True).start()
        elif cmd == "selectPlaylist": self.select_playlist(message.get("indexes", []))
        elif cmd == "closePlaylist": self.playlist = None; self.emit("playlist", playlist=None)
        elif cmd == "startQueue": self.start_queue()
        elif cmd == "pause":
            if self.busy and self.current_id:
                self.pause.clear() if self.pause.is_set() else self.pause.set()
                self.changed()
        elif cmd == "cancel": self.cancel.set(); self.pause.clear(); self.changed()
        elif cmd == "remove":
            with self.lock:
                job = next((j for j in self.queue if j["id"] == message.get("id")), None)
                if job and job["status"] not in ("Baixando", "Pausado", "Preparando"):
                    self.queue.remove(job); self.changed()
        elif cmd == "clearFinished":
            self.queue = [j for j in self.queue if j["status"] not in ("Concluído", "Falhou", "Cancelado")]; self.changed()
        elif cmd == "openFfmpeg": webbrowser.open(FFMPEG_PAGE)

    def inspect(self, message):
        url, mode, quality = (str(message.get(k, "")).strip() for k in ("url", "mode", "quality"))
        folder = self.settings["audioFolder" if mode == "Áudio" else "videoFolder"]
        try:
            with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True, "skip_download": True,
                    "noplaylist": False, "extract_flat": "in_playlist", "socket_timeout": 20,
                    "retries": 5, "extractor_retries": 4}) as ydl:
                info = ydl.extract_info(url, download=False)
            if not info: raise RuntimeError("O site não retornou informações para este link.")
            entries = info.get("entries") or []
            is_playlist = info.get("_type") == "playlist" or bool(entries)
            fmt = quality_label(mode, quality)
            if is_playlist:
                normalized = []
                for e in entries:
                    if not e: continue
                    vid = e.get("id") or e.get("url")
                    if not vid: continue
                    link = e.get("url") or f"https://www.youtube.com/watch?v={vid}"
                    if not str(link).startswith(("http://", "https://")): link = f"https://www.youtube.com/watch?v={vid}"
                    normalized.append({"id": str(vid), "url": str(link), "title": e.get("title") or "Vídeo",
                        "thumbnail": e.get("thumbnail") or f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg",
                        "duration": e.get("duration") or 0})
                self.playlist = {"url": url, "title": info.get("title") or "Playlist", "entries": normalized,
                    "count": info.get("playlist_count") or info.get("n_entries") or len(normalized),
                    "format": fmt, "mode": mode, "quality": quality, "folder": folder}
                self.emit("playlist", playlist=self.playlist)
            else:
                category = "audio" if mode == "Áudio" else "video"
                self.queue.append(make_job(url, category, info.get("title") or "Conteúdo online",
                    info.get("thumbnail") or f"https://i.ytimg.com/vi/{info.get('id','')}/hqdefault.jpg",
                    fmt, folder, mode, quality))
                self.changed()
        except Exception as exc:
            self.emit("error", kind="inspect", message=friendly_error(exc))
        finally:
            with self.lock: self.inspecting = False
            self.changed()
            if self.settings.get("automatic") and not self.playlist:
                self.start_queue()

    def select_playlist(self, indexes):
        data = self.playlist
        if not data: return
        selected = set(int(i) for i in indexes)
        if -1 in selected:
            self.queue.append(make_job(data["url"], "playlist", data["title"], "", data["format"], data["folder"], data["mode"], data["quality"], data["count"]))
        else:
            category = "audio" if data["mode"] == "Áudio" else "video"
            for i, entry in enumerate(data["entries"]):
                if i in selected:
                    job = make_job(entry["url"], category, entry["title"], entry["thumbnail"], data["format"], data["folder"], data["mode"], data["quality"])
                    job["playlistTitle"] = data["title"]
                    self.queue.append(job)
        self.playlist = None
        self.emit("playlist", playlist=None); self.changed()
        if self.settings.get("automatic"): self.start_queue()

    def start_queue(self):
        with self.lock:
            pending = [j for j in self.queue if j["status"] == "Na fila"]
            if self.busy or not pending: return
            self.busy = True; self.cancel.clear(); self.pause.clear()
            self.current_id = pending[0]["id"]
            for j in pending: j["status"] = "Preparando"
            self.changed()
            self.download_thread = threading.Thread(target=self.download, args=(pending,), daemon=True)
            self.download_thread.start()

    def download(self, jobs):
        try:
            for job in jobs:
                if self.cancel.is_set(): break
                self.current_id = job["id"]
                job["status"] = "Baixando"; self.changed()
                try:
                    folder = Path(job["folder"]); folder.mkdir(parents=True, exist_ok=True)
                    opts = self.options(job)
                    with yt_dlp.YoutubeDL(opts) as ydl:
                        info = ydl.extract_info(job["url"], download=True)
                        candidates = [Path(job["final"])] if job.get("final") else []
                        try: candidates.append(Path(ydl.prepare_filename(info)))
                        except Exception: pass
                        final = next((p for p in candidates if p.is_file()), None)
                        if not final:
                            vid = str(info.get("id") or "")
                            found = sorted((p for p in folder.iterdir() if p.is_file() and f"[{vid}]" in p.name), key=lambda p:p.stat().st_mtime, reverse=True) if vid else []
                            final = next(iter(found), None)
                        if final: job["final"] = str(final.resolve()); job["size"] = final.stat().st_size
                        job["status"] = "Cancelado" if self.cancel.is_set() else "Concluído"
                        if job["status"] == "Concluído": job["progress"] = 100
                        self.record_history(job)
                        self.changed()
                        if job["status"] == "Concluído" and self.settings.get("notifications"):
                            self.emit("completed", title=job["title"], path=job.get("final") or job["folder"])
                except DownloadCancelled:
                    job["status"] = "Cancelado"; self.record_history(job); self.changed()
                except Exception as exc:
                    job["status"] = "Falhou"; self.record_history(job); self.changed()
                    self.emit("error", kind="ffmpeg" if is_ffmpeg_error(str(exc)) else "download", message=friendly_error(exc))
            if self.cancel.is_set():
                for job in jobs:
                    if job["status"] in ("Na fila", "Preparando"):
                        job["status"] = "Cancelado"; self.record_history(job)
        finally:
            self.current_id = ""; self.busy = False; self.pause.clear(); self.cancel.clear(); self.changed()
            if self.settings.get("automatic") and any(j["status"] == "Na fila" for j in self.queue):
                self.start_queue()

    def options(self, job):
        opts = {"outtmpl": os.path.join(job["folder"], "%(title)s [%(id)s].%(ext)s"),
            "noplaylist": job["category"] != "playlist", "quiet": True, "no_warnings": True,
            "windowsfilenames": os.name == "nt", "socket_timeout": 30, "retries": 3,
            "fragment_retries": 6, "extractor_retries": 4, "file_access_retries": 5,
            "progress_hooks": [lambda d: self.progress(job, d)],
            "postprocessor_hooks": [lambda d: self.capture_final(job, d)]}
        ffmpeg = self.settings.get("ffmpegLocation")
        if ffmpeg and Path(ffmpeg).exists(): opts["ffmpeg_location"] = ffmpeg
        if job["mode"] == "Áudio":
            opts["format"] = "bestaudio/best"
            if job["quality"] in ("MP3", "M4A"):
                opts["postprocessors"] = [{"key":"FFmpegExtractAudio", "preferredcodec":job["quality"].lower(), "preferredquality":"192" if job["quality"]=="MP3" else "0"}]
        else:
            height = next((n for n in (1080,720,480) if f"{n}p" in job["quality"]), None)
            opts["format"] = f"bestvideo[height<={height}]+bestaudio/best[height<={height}]/best" if height else "bestvideo*+bestaudio/best"
            opts["merge_output_format"] = "mp4"
        return opts

    def progress(self, job, data):
        while self.pause.is_set() and not self.cancel.is_set():
            job["status"] = "Pausado"; self.changed(); time.sleep(.15)
        if self.cancel.is_set(): raise DownloadCancelled("Cancelado pelo usuário")
        if data.get("status") == "downloading":
            done = data.get("downloaded_bytes") or 0; total = data.get("total_bytes") or data.get("total_bytes_estimate") or 0
            job.update(downloaded=done,total=total,speed=data.get("speed") or 0,eta=data.get("eta"),progress=(done*100/total if total else 0),status="Baixando")
            self.changed()
        elif data.get("status") == "finished":
            filename = data.get("filename") or data.get("tmpfilename")
            if filename and Path(filename).is_file(): job["final"] = str(Path(filename).resolve()); job["size"] = Path(filename).stat().st_size

    def capture_final(self, job, data):
        info=data.get("info_dict") or {}; filename=info.get("filepath") or info.get("_filename")
        if filename and Path(filename).is_file(): job["final"]=str(Path(filename).resolve()); job["size"]=Path(filename).stat().st_size


def main():
    # Electron IPC uses UTF-8 JSON lines on Windows; force an invariant codec.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stdin, "reconfigure"):
        sys.stdin.reconfigure(encoding="utf-8", errors="replace")
    settings_path = sys.argv[1] if len(sys.argv) > 1 else str(Path.home()/"AppData"/"Roaming"/"Luma Downloader"/"settings.json")
    service = Service(settings_path)
    for line in sys.stdin:
        try: service.command(json.loads(line))
        except Exception as exc: service.emit("error", kind="backend", message=friendly_error(exc))


if __name__ == "__main__": main()
