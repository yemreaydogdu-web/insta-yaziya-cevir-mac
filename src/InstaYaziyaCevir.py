import os
import queue
import re
import threading
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import yt_dlp
from faster_whisper import WhisperModel


APP_NAME = "Insta Yazıya Çevir"
DEFAULT_OUTPUT_DIR = Path.home() / "Documents" / "InstaYaziyaCevir"


@dataclass
class JobOptions:
    instagram_url: str
    local_file: str
    output_dir: Path
    model_size: str
    cookies_browser: str
    language: str


def safe_filename(text: str, fallback: str = "video") -> str:
    text = text.strip() or fallback
    text = re.sub(r"[\\/:*?\"<>|]+", "_", text)
    text = re.sub(r"\s+", " ", text)
    return text[:90].strip(" ._") or fallback


def format_timestamp(seconds: float, srt: bool = False) -> str:
    millis = int(round(seconds * 1000))
    hours = millis // 3_600_000
    millis %= 3_600_000
    minutes = millis // 60_000
    millis %= 60_000
    secs = millis // 1000
    ms = millis % 1000
    sep = "," if srt else "."
    return f"{hours:02d}:{minutes:02d}:{secs:02d}{sep}{ms:03d}"


def write_txt(path: Path, segments: Iterable) -> None:
    lines = []
    for seg in segments:
        text = seg.text.strip()
        if text:
            lines.append(f"[{format_timestamp(seg.start)} - {format_timestamp(seg.end)}] {text}")
    path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


def write_plain_txt(path: Path, segments: Iterable) -> None:
    text = " ".join(seg.text.strip() for seg in segments if seg.text.strip())
    path.write_text(text.strip() + "\n", encoding="utf-8")


def write_srt(path: Path, segments: Iterable) -> None:
    blocks = []
    for index, seg in enumerate(segments, start=1):
        text = seg.text.strip()
        if not text:
            continue
        blocks.append(
            f"{index}\n{format_timestamp(seg.start, srt=True)} --> {format_timestamp(seg.end, srt=True)}\n{text}\n"
        )
    path.write_text("\n".join(blocks).strip() + "\n", encoding="utf-8")


def download_instagram(url: str, output_dir: Path, cookies_browser: str, log) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)

    ydl_opts = {
        "outtmpl": str(output_dir / "downloads" / "%(title).80s-%(id)s.%(ext)s"),
        "format": "bv*+ba/best/bestvideo+bestaudio",
        "merge_output_format": "mp4",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": False,
        "retries": 3,
    }

    if cookies_browser and cookies_browser != "Yok":
        ydl_opts["cookiesfrombrowser"] = (cookies_browser.lower(),)
        log(f"Instagram erişimi için {cookies_browser} çerezleri deneniyor...")

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        log("Instagram linki indiriliyor...")
        info = ydl.extract_info(url, download=True)
        path = Path(ydl.prepare_filename(info))

        requested = info.get("requested_downloads") or []
        if requested and requested[0].get("filepath"):
            path = Path(requested[0]["filepath"])

    if not path.exists():
        candidates = sorted((output_dir / "downloads").glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not candidates:
            raise FileNotFoundError("İndirilen video dosyası bulunamadı.")
        path = candidates[0]

    return path


class InstaYaziyaCevirApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        self.geometry("880x720")
        self.minsize(760, 620)
        self.log_queue: queue.Queue[str] = queue.Queue()
        self.worker: Optional[threading.Thread] = None
        self.selected_file = tk.StringVar(value="")
        self.url_var = tk.StringVar(value="")
        self.output_var = tk.StringVar(value=str(DEFAULT_OUTPUT_DIR))
        self.model_var = tk.StringVar(value="base")
        self.cookies_var = tk.StringVar(value="Yok")
        self.language_var = tk.StringVar(value="tr")
        self.status_var = tk.StringVar(value="Hazır")
        self._build_ui()
        self.after(100, self._poll_log)

    def _build_ui(self):
        pad = 14
        root = ttk.Frame(self, padding=pad)
        root.pack(fill="both", expand=True)

        title = ttk.Label(root, text="Instagram videosunu yazıya çevir", font=("Arial", 20, "bold"))
        title.pack(anchor="w")

        desc = ttk.Label(
            root,
            text="Instagram linki yapıştır veya bilgisayardan video/ses dosyası seç. Çıktı olarak TXT ve SRT üretir.",
            wraplength=820,
        )
        desc.pack(anchor="w", pady=(4, 16))

        url_frame = ttk.LabelFrame(root, text="1) Instagram linki")
        url_frame.pack(fill="x", pady=(0, 10))
        ttk.Entry(url_frame, textvariable=self.url_var).pack(side="left", fill="x", expand=True, padx=10, pady=10)
        ttk.Button(url_frame, text="Temizle", command=lambda: self.url_var.set("")).pack(side="left", padx=(0, 10))

        file_frame = ttk.LabelFrame(root, text="Alternatif: Bilgisayardan dosya seç")
        file_frame.pack(fill="x", pady=(0, 10))
        ttk.Entry(file_frame, textvariable=self.selected_file).pack(side="left", fill="x", expand=True, padx=10, pady=10)
        ttk.Button(file_frame, text="Dosya seç", command=self.choose_file).pack(side="left", padx=(0, 10))

        options = ttk.LabelFrame(root, text="2) Ayarlar")
        options.pack(fill="x", pady=(0, 10))

        row = ttk.Frame(options)
        row.pack(fill="x", padx=10, pady=10)

        ttk.Label(row, text="Model:").grid(row=0, column=0, sticky="w")
        model_box = ttk.Combobox(row, textvariable=self.model_var, values=["tiny", "base", "small", "medium", "large-v3"], width=12, state="readonly")
        model_box.grid(row=0, column=1, padx=(8, 24), sticky="w")

        ttk.Label(row, text="Dil:").grid(row=0, column=2, sticky="w")
        lang_box = ttk.Combobox(row, textvariable=self.language_var, values=["tr", "auto", "en", "de", "fr", "es", "it", "ar"], width=10, state="readonly")
        lang_box.grid(row=0, column=3, padx=(8, 24), sticky="w")

        ttk.Label(row, text="Instagram çerezi:").grid(row=0, column=4, sticky="w")
        cookies_box = ttk.Combobox(row, textvariable=self.cookies_var, values=["Yok", "Chrome", "Safari", "Firefox", "Edge"], width=12, state="readonly")
        cookies_box.grid(row=0, column=5, padx=(8, 0), sticky="w")

        out_frame = ttk.Frame(options)
        out_frame.pack(fill="x", padx=10, pady=(0, 10))
        ttk.Label(out_frame, text="Çıktı klasörü:").pack(side="left")
        ttk.Entry(out_frame, textvariable=self.output_var).pack(side="left", fill="x", expand=True, padx=8)
        ttk.Button(out_frame, text="Klasör seç", command=self.choose_output).pack(side="left")

        buttons = ttk.Frame(root)
        buttons.pack(fill="x", pady=(0, 10))
        self.start_button = ttk.Button(buttons, text="Yazıya çevir", command=self.start_job)
        self.start_button.pack(side="left")
        ttk.Button(buttons, text="Çıktı klasörünü aç", command=self.open_output_dir).pack(side="left", padx=8)
        ttk.Label(buttons, textvariable=self.status_var).pack(side="right")

        log_frame = ttk.LabelFrame(root, text="Durum")
        log_frame.pack(fill="both", expand=True)
        self.log_text = tk.Text(log_frame, wrap="word", height=18)
        self.log_text.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=10)
        scroll = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        scroll.pack(side="right", fill="y", padx=(0, 10), pady=10)
        self.log_text.configure(yscrollcommand=scroll.set)

        self.log("Hazır. Instagram linki gir veya dosya seç.")
        self.log("Not: İlk kullanımda seçilen Whisper modeli indirileceği için biraz bekleyebilir.")

    def choose_file(self):
        path = filedialog.askopenfilename(
            title="Video veya ses dosyası seç",
            filetypes=[
                ("Video/Ses dosyaları", "*.mp4 *.mov *.m4v *.mkv *.webm *.mp3 *.m4a *.wav *.aac *.flac"),
                ("Tüm dosyalar", "*.*"),
            ],
        )
        if path:
            self.selected_file.set(path)

    def choose_output(self):
        path = filedialog.askdirectory(title="Çıktı klasörü seç")
        if path:
            self.output_var.set(path)

    def open_output_dir(self):
        out = Path(self.output_var.get()).expanduser()
        out.mkdir(parents=True, exist_ok=True)
        os.system(f'open "{out}"')

    def log(self, msg: str):
        self.log_queue.put(msg)

    def _poll_log(self):
        try:
            while True:
                msg = self.log_queue.get_nowait()
                self.log_text.insert("end", msg + "\n")
                self.log_text.see("end")
        except queue.Empty:
            pass
        self.after(100, self._poll_log)

    def start_job(self):
        if self.worker and self.worker.is_alive():
            messagebox.showinfo(APP_NAME, "Zaten devam eden bir işlem var.")
            return

        output_dir = Path(self.output_var.get()).expanduser()
        opts = JobOptions(
            instagram_url=self.url_var.get().strip(),
            local_file=self.selected_file.get().strip(),
            output_dir=output_dir,
            model_size=self.model_var.get(),
            cookies_browser=self.cookies_var.get(),
            language=self.language_var.get(),
        )

        if not opts.instagram_url and not opts.local_file:
            messagebox.showwarning(APP_NAME, "Instagram linki gir veya dosya seç.")
            return

        self.start_button.configure(state="disabled")
        self.status_var.set("Çalışıyor...")
        self.worker = threading.Thread(target=self.run_job, args=(opts,), daemon=True)
        self.worker.start()

    def run_job(self, opts: JobOptions):
        try:
            opts.output_dir.mkdir(parents=True, exist_ok=True)

            if opts.local_file:
                media_path = Path(opts.local_file)
                self.log(f"Dosya seçildi: {media_path}")
            else:
                media_path = download_instagram(opts.instagram_url, opts.output_dir, opts.cookies_browser, self.log)
                self.log(f"İndirildi: {media_path}")

            base_name = safe_filename(media_path.stem)
            txt_timed = opts.output_dir / f"{base_name}.zamanli.txt"
            txt_plain = opts.output_dir / f"{base_name}.duz_metin.txt"
            srt_path = opts.output_dir / f"{base_name}.srt"

            self.log(f"Model yükleniyor: {opts.model_size}")
            model = WhisperModel(opts.model_size, device="cpu", compute_type="int8")

            language = None if opts.language == "auto" else opts.language
            self.log("Yazıya çevirme başladı...")
            segments_iter, info = model.transcribe(
                str(media_path),
                language=language,
                vad_filter=True,
                beam_size=5,
            )
            segments = list(segments_iter)

            detected = getattr(info, "language", "?")
            self.log(f"Algılanan dil: {detected}")

            write_txt(txt_timed, segments)
            write_plain_txt(txt_plain, segments)
            write_srt(srt_path, segments)

            self.log("Bitti.")
            self.log(f"Zamanlı TXT: {txt_timed}")
            self.log(f"Düz metin TXT: {txt_plain}")
            self.log(f"SRT altyazı: {srt_path}")
            self.status_var.set("Bitti")
            messagebox.showinfo(APP_NAME, "Yazıya çevirme tamamlandı. Çıktı klasörünü açabilirsin.")
        except Exception as exc:
            self.log("HATA:")
            self.log(str(exc))
            self.log(traceback.format_exc())
            self.status_var.set("Hata")
            messagebox.showerror(APP_NAME, f"İşlem başarısız oldu:\n\n{exc}")
        finally:
            self.start_button.configure(state="normal")


if __name__ == "__main__":
    app = InstaYaziyaCevirApp()
    app.mainloop()
