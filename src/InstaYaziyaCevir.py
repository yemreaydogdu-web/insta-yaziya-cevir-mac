import gc
import inspect
import os
import unicodedata
import queue
import re
import threading
import time
import traceback
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional, Tuple

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import yt_dlp
from faster_whisper import WhisperModel


APP_NAME = "Insta Yazıya Çevir"
APP_VERSION = "1.6.0"
DEFAULT_OUTPUT_DIR = Path.home() / "Documents" / "InstaYaziyaCevir"


@dataclass
class JobOptions:
    instagram_url: str
    local_file: str
    output_dir: Path
    model_size: str
    cookies_browser: str
    language: str
    test_first_minute: bool


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


def format_elapsed(seconds: float) -> str:
    seconds = max(0, int(seconds))
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def format_percent(value: float) -> str:
    value = max(0.0, min(100.0, value))
    if value >= 99.5:
        return "100%"
    return f"{value:.0f}%"


def write_txt(path: Path, segments: Iterable) -> None:
    lines = []
    for seg in segments:
        text = seg.text.strip()
        if text:
            lines.append(f"[{format_timestamp(seg.start)} - {format_timestamp(seg.end)}] {text}")
    path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


def write_plain_txt(path: Path, segments: Iterable) -> None:
    text = " ".join(seg.text.strip() for seg in segments if seg.text.strip())
    text = re.sub(r"\s+", " ", text).strip()
    path.write_text(text + "\n", encoding="utf-8")


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


def build_initial_prompt(context_prompt: str, language: str) -> Optional[str]:
    """Whisper'a konu/özel terim bağlamı verir.

    Bu bir LLM düzeltmesi değildir; sadece transkripsiyon sırasında modelin
    olası özel kelimeleri daha doğru seçmesine yardım eden güvenli bir ipucudur.
    """
    context_prompt = (context_prompt or "").strip()
    if not context_prompt:
        return None

    if language == "tr":
        return (
            "Bu videoda geçen özel isimler, teknik terimler veya konu bağlamı şunlar olabilir: "
            f"{context_prompt}. "
            "Konuşmayı Türkçe olarak, duyulan anlama sadık kalarak yaz."
        )

    return (
        "Possible topic context, proper nouns, and technical terms in this video: "
        f"{context_prompt}. Transcribe faithfully without adding new meaning."
    )


def supported_transcribe_kwargs(model: WhisperModel, kwargs: dict) -> dict:
    """faster-whisper sürüm farklarına dayanıklı parametre filtresi."""
    try:
        sig = inspect.signature(model.transcribe)
    except Exception:
        return kwargs

    allowed = set(sig.parameters.keys())
    return {key: value for key, value in kwargs.items() if key in allowed and value is not None}


@dataclass
class CleanSegment:
    start: float
    end: float
    text: str


class UserCancelled(Exception):
    pass


SUSPICIOUS_ENDING_PATTERNS = [
    "altyazi",
    "altyazi mk",
    "altyazi m k",
    "altyazilar",
    "ceviri ve altyazi",
    "subtitles by",
    "captions by",
    "caption",
    "transcription by",
    "izlediginiz icin tesekkurler",
    "abone olmayi unutmayin",
    "like ve abone",
    "www.",
    ".com",
]


def normalize_for_filter(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower()
    # Türkçe karakterleri filtre eşleştirmesi için sadeleştir. Özellikle "altyazı" -> "altyazi" gerekli.
    table = str.maketrans({
        "ı": "i", "ğ": "g", "ü": "u", "ş": "s", "ö": "o", "ç": "c",
    })
    text = text.translate(table)
    text = re.sub(r"[^a-z0-9\s\.]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def contains_suspicious_signature(norm: str) -> bool:
    """Kısa jenerik/altyazı imzası yakalar; normal konuşmadaki 'çeviriyor' gibi kelimeleri yakalamaz."""
    if not norm:
        return False

    # Çok tipik altyazı/jenerik imzaları.
    phrase_patterns = [
        "altyazi", "altyazi mk", "altyazi m k", "altyazilar",
        "ceviri ve altyazi", "subtitles by", "captions by", "caption by",
        "transcription by", "izlediginiz icin tesekkurler", "abone olmayi unutmayin",
        "like ve abone", "www.", ".com",
    ]
    if any(pattern in norm for pattern in phrase_patterns):
        return True

    # Tek başına "çeviri" sadece satır gerçekten jenerik imzası gibi çok kısaysa yakalansın.
    if re.fullmatch(r"(ceviri|translated by|translation by)( [a-z0-9]{1,20}){0,4}", norm):
        return True

    return False


def is_suspicious_segment(seg, total_duration: Optional[float] = None) -> bool:
    """Whisper'ın sessizlik/jenerik sonunda uydurabildiği kısa kapanış satırlarını yakalar.

    Bu filtre genel konuşma metnini düzeltmez; sadece çok tipik sahte altyazı/jenerik
    satırlarını ana çıktıdan temizler. Ham çıktı ayrıca kaydedildiği için izlenebilirlik korunur.
    """
    text = (getattr(seg, "text", "") or "").strip()
    if not text:
        return True

    norm = normalize_for_filter(text)
    duration = float(getattr(seg, "end", 0) or 0) - float(getattr(seg, "start", 0) or 0)
    start = float(getattr(seg, "start", 0) or 0)

    # Çok kısa jenerik/altyazı imzası tipi satırları sil.
    if len(norm) <= 120 and contains_suspicious_signature(norm):
        return True

    # Videonun son bölümünde çok uzun süreye yayılan ama çok kısa kalan jenerik satırlar şüpheli.
    if total_duration and total_duration > 0:
        in_last_third = start >= total_duration * 0.60
        if in_last_third and duration >= 8 and len(norm) <= 120 and contains_suspicious_signature(norm):
            return True

    # Tek satırın 20+ saniyeye uzayıp birkaç kelimeden ibaret olması genellikle sessizlik hallucination'ıdır.
    if duration >= 20 and len(norm.split()) <= 5:
        return True

    return False


def clean_segments(segments: list, total_duration: Optional[float] = None):
    cleaned = []
    removed = []
    for seg in segments:
        text = (getattr(seg, "text", "") or "").strip()
        if is_suspicious_segment(seg, total_duration):
            removed.append(seg)
            continue
        cleaned.append(CleanSegment(float(seg.start), float(seg.end), text))
    return cleaned, removed


def download_media(url: str, output_dir: Path, cookies_browser: str, log) -> Path:
    """Video linkinden ffmpeg gerektirmeden sesli tek dosya indirir.

    Önce audio-only format dener. Yoksa tek parça, sesi olan en iyi formatı indirir.
    Bilerek video+audio merge istemeyiz; çünkü merge ffmpeg gerektirir.
    Transkripsiyon için görüntüye değil, sese ihtiyacımız var.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    downloads_dir = output_dir / "downloads"
    downloads_dir.mkdir(parents=True, exist_ok=True)

    ydl_opts = {
        "outtmpl": str(downloads_dir / "%(title).80s-%(id)s.%(ext)s"),
        # Tek dosya seç: ffmpeg merge gerektiren bv+ba formatlarından kaçın.
        "format": "bestaudio/best[acodec!=none]/best",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": False,
        "retries": 3,
    }

    if cookies_browser and cookies_browser != "Yok":
        ydl_opts["cookiesfrombrowser"] = (cookies_browser.lower(),)
        log(f"{cookies_browser} çerezleri deneniyor. macOS parola/anahtar zinciri izni isteyebilir.")

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            log("Video/ses linki indiriliyor...")
            info = ydl.extract_info(url, download=True)
            path = Path(ydl.prepare_filename(info))

            requested = info.get("requested_downloads") or []
            if requested:
                for item in requested:
                    fp = item.get("filepath") or item.get("filename")
                    if fp and Path(fp).exists():
                        path = Path(fp)
                        break
    except yt_dlp.utils.DownloadError as exc:
        msg = str(exc)
        if "empty media response" in msg.lower() or "cookies" in msg.lower():
            raise RuntimeError(
                "Link indirilemedi. Bu içerik giriş/çerez istiyor olabilir. "
                "Tarayıcıda içeriği açıp giriş yaptığından emin ol; uygulamada Tarayıcı çerezi olarak Chrome/Safari seç."
            ) from exc
        if "ffmpeg" in msg.lower():
            raise RuntimeError(
                "Link indirilemedi çünkü indirme aracı ffmpeg isteyen bir format seçti. "
                "Bu sürümde tek dosya/ses indirme ile azaltıldı; farklı bir link deneyebilir veya videoyu dosya olarak indirebilirsin."
            ) from exc
        raise

    if not path.exists():
        candidates = sorted(downloads_dir.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not candidates:
            raise FileNotFoundError("İndirilen medya dosyası bulunamadı.")
        path = candidates[0]

    return path


def is_instagram_url(url: str) -> bool:
    return bool(re.search(r"https?://([^/]+\.)?instagram\.com/", url or "", re.I))


class InstaYaziyaCevirApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} v{APP_VERSION}")
        self.geometry("950x760")
        self.minsize(800, 660)
        self.log_queue: queue.Queue[str] = queue.Queue()
        self.worker: Optional[threading.Thread] = None
        self.preload_worker: Optional[threading.Thread] = None
        self.selected_file = tk.StringVar(value="")
        self.url_var = tk.StringVar(value="")
        self.output_var = tk.StringVar(value=str(DEFAULT_OUTPUT_DIR))
        self.model_var = tk.StringVar(value="small")
        self.cookies_var = tk.StringVar(value="Yok")
        self.language_var = tk.StringVar(value="tr")
        self.test_first_minute_var = tk.BooleanVar(value=False)
        self.status_var = tk.StringVar(value="Hazır")
        self.stage_var = tk.StringVar(value="Aşama: Hazır")
        self.elapsed_var = tk.StringVar(value="Geçen süre: 00:00")
        self.loaded_model_var = tk.StringVar(value="Yüklü model: Yok")
        self.progress_detail_var = tk.StringVar(value="İlerleme: -")
        self.eta_var = tk.StringVar(value="Tahmini kalan: -")
        self.last_segment_var = tk.StringVar(value="Son metin: -")
        self.progress_value = tk.DoubleVar(value=0.0)
        self.cancel_requested = False
        self.model_hint_var = tk.StringVar(value="Small: hızlı taslak. Large-v3: kalite modu. Turbo: deneysel hızlı kalite. v1.6 Instagram/altyazı filtresi iyileştirildi.")
        self.cached_model: Optional[WhisperModel] = None
        self.cached_model_size: Optional[str] = None
        self.activity_start_time: Optional[float] = None
        self.activity_running = False
        self.current_progress_total: Optional[float] = None
        self._build_ui()
        self.after(100, self._poll_log)
        self.after(250, self._update_elapsed)

    def _build_ui(self):
        pad = 14
        root = ttk.Frame(self, padding=pad)
        root.pack(fill="both", expand=True)

        title = ttk.Label(root, text="Videoyu yazıya çevir", font=("Arial", 20, "bold"))
        title.pack(anchor="w")

        desc = ttk.Label(
            root,
            text=(
                "Video linki yapıştır veya bilgisayardan video/ses dosyası seç. "
                "v1.6: Instagram uyarısı, kısa altyazı filtresi ve tamamlanınca %100 düzeltmesi eklendi."
            ),
            wraplength=900,
        )
        desc.pack(anchor="w", pady=(4, 16))

        url_frame = ttk.LabelFrame(root, text="1) Video linki")
        url_frame.pack(fill="x", pady=(0, 10))
        ttk.Entry(url_frame, textvariable=self.url_var).pack(side="left", fill="x", expand=True, padx=10, pady=10)
        ttk.Button(url_frame, text="Temizle", command=lambda: self.url_var.set("")).pack(side="left", padx=(0, 10))

        file_frame = ttk.LabelFrame(root, text="Alternatif: Bilgisayardan dosya seç")
        file_frame.pack(fill="x", pady=(0, 10))
        ttk.Entry(file_frame, textvariable=self.selected_file).pack(side="left", fill="x", expand=True, padx=10, pady=10)
        ttk.Button(file_frame, text="Dosya seç", command=self.choose_file).pack(side="left", padx=(0, 8))
        ttk.Button(file_frame, text="Temizle", command=lambda: self.selected_file.set("")).pack(side="left", padx=(0, 10))

        options = ttk.LabelFrame(root, text="2) Ayarlar")
        options.pack(fill="x", pady=(0, 10))

        row = ttk.Frame(options)
        row.pack(fill="x", padx=10, pady=10)

        ttk.Label(row, text="Model:").grid(row=0, column=0, sticky="w")
        model_box = ttk.Combobox(
            row,
            textvariable=self.model_var,
            values=["tiny", "base", "small", "medium", "large-v3", "turbo"],
            width=12,
            state="readonly",
        )
        model_box.grid(row=0, column=1, padx=(8, 24), sticky="w")
        model_box.bind("<<ComboboxSelected>>", self.on_model_changed)

        ttk.Label(row, text="Dil:").grid(row=0, column=2, sticky="w")
        lang_box = ttk.Combobox(
            row,
            textvariable=self.language_var,
            values=["tr", "auto", "en", "de", "fr", "es", "it", "ar"],
            width=10,
            state="readonly",
        )
        lang_box.grid(row=0, column=3, padx=(8, 24), sticky="w")

        ttk.Label(row, text="Tarayıcı çerezi:").grid(row=0, column=4, sticky="w")
        cookies_box = ttk.Combobox(
            row,
            textvariable=self.cookies_var,
            values=["Yok", "Chrome", "Safari", "Firefox", "Edge"],
            width=12,
            state="readonly",
        )
        cookies_box.grid(row=0, column=5, padx=(8, 0), sticky="w")

        hint = ttk.Label(options, textvariable=self.model_hint_var, wraplength=900)
        hint.pack(anchor="w", padx=10, pady=(0, 8))

        test_row = ttk.Frame(options)
        test_row.pack(fill="x", padx=10, pady=(0, 8))
        ttk.Checkbutton(
            test_row,
            text="Sadece ilk 1 dakikayı test et",
            variable=self.test_first_minute_var,
        ).pack(side="left")
        ttk.Label(test_row, text="Uzun linklerde hızlı deneme için kullan.").pack(side="left", padx=(10, 0))

        out_frame = ttk.Frame(options)
        out_frame.pack(fill="x", padx=10, pady=(0, 10))
        ttk.Label(out_frame, text="Çıktı klasörü:").pack(side="left")
        ttk.Entry(out_frame, textvariable=self.output_var).pack(side="left", fill="x", expand=True, padx=8)
        ttk.Button(out_frame, text="Klasör seç", command=self.choose_output).pack(side="left")

        progress_frame = ttk.LabelFrame(root, text="İşlem durumu")
        progress_frame.pack(fill="x", pady=(0, 10))
        top_status = ttk.Frame(progress_frame)
        top_status.pack(fill="x", padx=10, pady=(10, 6))
        ttk.Label(top_status, textvariable=self.stage_var).pack(side="left")
        ttk.Label(top_status, textvariable=self.elapsed_var).pack(side="right")
        self.progress = ttk.Progressbar(progress_frame, mode="determinate", maximum=100, variable=self.progress_value)
        self.progress.pack(fill="x", padx=10, pady=(0, 6))
        detail_row = ttk.Frame(progress_frame)
        detail_row.pack(fill="x", padx=10, pady=(0, 4))
        ttk.Label(detail_row, textvariable=self.progress_detail_var).pack(side="left")
        ttk.Label(detail_row, textvariable=self.eta_var).pack(side="right")
        ttk.Label(progress_frame, textvariable=self.last_segment_var, wraplength=900).pack(anchor="w", padx=10, pady=(0, 6))
        ttk.Label(progress_frame, textvariable=self.loaded_model_var).pack(anchor="w", padx=10, pady=(0, 10))

        buttons = ttk.Frame(root)
        buttons.pack(fill="x", pady=(0, 10))
        self.start_button = ttk.Button(buttons, text="Yazıya çevir", command=self.start_job)
        self.start_button.pack(side="left")
        self.cancel_button = ttk.Button(buttons, text="İptal", command=self.cancel_job, state="disabled")
        self.cancel_button.pack(side="left", padx=(8, 0))
        self.preload_button = ttk.Button(buttons, text="Seçili modeli hazırla", command=self.preload_selected_model)
        self.preload_button.pack(side="left", padx=(8, 0))
        ttk.Button(buttons, text="Çıktı klasörünü aç", command=self.open_output_dir).pack(side="left", padx=8)
        ttk.Button(buttons, text="Modeli RAM'den temizle", command=self.unload_model).pack(side="left")
        ttk.Label(buttons, textvariable=self.status_var).pack(side="right")

        log_frame = ttk.LabelFrame(root, text="Durum kaydı")
        log_frame.pack(fill="both", expand=True)
        self.log_text = tk.Text(log_frame, wrap="word", height=18)
        self.log_text.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=10)
        scroll = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        scroll.pack(side="right", fill="y", padx=(0, 10), pady=10)
        self.log_text.configure(yscrollcommand=scroll.set)

        self.log("Hazır. Video linki gir veya dosya seç.")
        self.log("Not: Aynı oturumda aynı model tekrar yüklenmez; ikinci video daha hızlı başlar.")
        self.log("Not: large-v3 ve turbo ilk kullanımda indirilebilir/yüklenebilir; sayaçtan bekleme süresini takip edebilirsin.")
        self.log("Not: v1.6 işlem bittiğinde ilerleme %100/kalan 00:00 gösterir; kısa sahte altyazı imzalarını da temizler.")
        self.log("Not: Linkten indirirken ffmpeg merge istemez; YouTube/Instagram linklerini tek dosya/ses olarak dener.")

    def on_model_changed(self, _event=None):
        model = self.model_var.get()
        if model == "large-v3":
            self.model_hint_var.set("Large-v3 ana kalite modudur. İlk kullanımda uzun sürebilir; ikinci kullanımda cache sayesinde hızlı başlar.")
        elif model == "turbo":
            self.model_hint_var.set("Turbo deneysel hızlı kalite modudur. Kalite large-v3 kadar stabil olmayabilir; güvenli bitiş filtresi açıktır.")
        elif model == "medium":
            self.model_hint_var.set("Medium dengeli moddur ama testte large-v3 kadar iyi çıkmayabilir.")
        elif model == "small":
            self.model_hint_var.set("Small hızlı günlük kullanım modudur; kalite gerekirse large-v3 veya turbo dene.")
        else:
            self.model_hint_var.set("Tiny/base çok hızlıdır ama Türkçe kalite düşük olabilir.")

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

    def unload_model(self):
        if self.is_busy():
            messagebox.showinfo(APP_NAME, "İşlem devam ederken model temizlenemez.")
            return
        self.cached_model = None
        self.cached_model_size = None
        gc.collect()
        self.loaded_model_var.set("Yüklü model: Yok")
        self.log("Model RAM'den temizlendi.")
        self.status_var.set("Hazır")

    def is_busy(self) -> bool:
        return bool(
            (self.worker and self.worker.is_alive())
            or (self.preload_worker and self.preload_worker.is_alive())
        )

    def log(self, msg: str):
        stamp = datetime.now().strftime("%H:%M:%S")
        self.log_queue.put(f"[{stamp}] {msg}")

    def _poll_log(self):
        try:
            while True:
                msg = self.log_queue.get_nowait()
                self.log_text.insert("end", msg + "\n")
                self.log_text.see("end")
        except queue.Empty:
            pass
        self.after(100, self._poll_log)

    def _start_activity(self, stage: str):
        self.activity_start_time = time.monotonic()
        self.activity_running = True
        self.cancel_requested = False
        self.current_progress_total = None
        self.stage_var.set(f"Aşama: {stage}")
        self.elapsed_var.set("Geçen süre: 00:00")
        self.progress.configure(mode="indeterminate")
        self.progress.start(12)
        self.progress_detail_var.set("İlerleme: hazırlanıyor")
        self.eta_var.set("Tahmini kalan: -")
        self.last_segment_var.set("Son metin: -")

    def _finish_activity(self, stage: str = "Tamamlandı"):
        self.activity_running = False
        if self.activity_start_time is not None:
            self.elapsed_var.set(f"Geçen süre: {format_elapsed(time.monotonic() - self.activity_start_time)}")
        self.stage_var.set(f"Aşama: {stage}")
        self.progress.stop()
        self.progress.configure(mode="determinate")
        if stage == "Tamamlandı":
            self.progress_value.set(100)
            total = self.current_progress_total or 0
            if total > 0:
                self.progress_detail_var.set(
                    f"İşlenen: {format_elapsed(total)} / {format_elapsed(total)} (100%)"
                )
            else:
                self.progress_detail_var.set("İşlenen: tamamlandı (100%)")
            self.eta_var.set("Tahmini kalan: 00:00")
        elif stage == "İptal edildi":
            self.progress_detail_var.set("İlerleme: işlem iptal edildi")
            self.eta_var.set("Tahmini kalan: -")

    def start_indeterminate_progress(self):
        self.after(0, lambda: (self.progress.configure(mode="indeterminate"), self.progress.start(12)))

    def start_determinate_progress(self):
        self.after(0, lambda: (self.progress.stop(), self.progress.configure(mode="determinate"), self.progress_value.set(0)))

    def _update_elapsed(self):
        if self.activity_running and self.activity_start_time is not None:
            elapsed = time.monotonic() - self.activity_start_time
            self.elapsed_var.set(f"Geçen süre: {format_elapsed(elapsed)}")
        self.after(500, self._update_elapsed)

    def set_stage(self, stage: str):
        self.after(0, lambda: self.stage_var.set(f"Aşama: {stage}"))

    def set_status(self, status: str):
        self.after(0, lambda: self.status_var.set(status))

    def set_loaded_model_label(self, model_size: Optional[str]):
        text = f"Yüklü model: {model_size}" if model_size else "Yüklü model: Yok"
        self.after(0, lambda: self.loaded_model_var.set(text))

    def set_buttons_busy(self, busy: bool):
        state = "disabled" if busy else "normal"
        self.start_button.configure(state=state)
        self.preload_button.configure(state=state)
        self.cancel_button.configure(state="normal" if busy else "disabled")

    def cancel_job(self):
        if not self.is_busy():
            return
        self.cancel_requested = True
        self.log("İptal istendi. Mevcut segment tamamlanınca işlem duracak.")
        self.set_status("İptal ediliyor...")
        self.set_stage("İptal ediliyor")

    def set_transcribe_progress(self, processed: float, total: Optional[float], last_text: str = ""):
        def _apply():
            if total and total > 0:
                self.current_progress_total = float(total)
                percent = max(0.0, min(100.0, (processed / total) * 100.0))
                self.progress_value.set(percent)
                self.progress_detail_var.set(
                    f"İşlenen: {format_elapsed(processed)} / {format_elapsed(total)} ({format_percent(percent)})"
                )
                if self.activity_start_time and processed > 1:
                    elapsed = time.monotonic() - self.activity_start_time
                    remaining = max(0.0, elapsed * (total - processed) / max(processed, 1.0))
                    self.eta_var.set(f"Tahmini kalan: {format_elapsed(remaining)}")
            else:
                self.progress_detail_var.set(f"İşlenen: {format_elapsed(processed)}")
                self.eta_var.set("Tahmini kalan: -")
            if last_text:
                preview = re.sub(r"\s+", " ", last_text).strip()
                if len(preview) > 160:
                    preview = preview[:157].rstrip() + "..."
                self.last_segment_var.set(f"Son metin: {preview}")

        self.after(0, _apply)

    def start_job(self):
        if self.is_busy():
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
            test_first_minute=self.test_first_minute_var.get(),
        )

        if not opts.instagram_url and not opts.local_file:
            messagebox.showwarning(APP_NAME, "Video linki gir veya dosya seç.")
            return

        if opts.instagram_url and opts.local_file:
            messagebox.showwarning(APP_NAME, "Hem link hem dosya seçili. Lütfen birini temizle ve tekrar dene.")
            return

        if is_instagram_url(opts.instagram_url) and opts.cookies_browser == "Yok":
            proceed = messagebox.askyesno(
                APP_NAME,
                "Bu bir Instagram linki. Instagram içerikleri çoğunlukla tarayıcı çerezi ister.\n\n"
                "Şu an Tarayıcı çerezi 'Yok' seçili. Yine de çerezsiz deneyeyim mi?\n\n"
                "Öneri: Hayır de, Tarayıcı çerezi olarak Chrome veya Safari seç ve tekrar dene.",
            )
            if not proceed:
                return

        if opts.instagram_url and not opts.test_first_minute:
            proceed = messagebox.askyesno(
                APP_NAME,
                "Linkten gelen videonun süresi uzun olabilir. Devam edeyim mi?\n\n"
                "Hızlı deneme için 'Sadece ilk 1 dakikayı test et' seçeneğini kullanabilirsin.",
            )
            if not proceed:
                return

        self.set_buttons_busy(True)
        self.status_var.set("Çalışıyor...")
        self._start_activity("Başlatılıyor")
        self.worker = threading.Thread(target=self.run_job, args=(opts,), daemon=True)
        self.worker.start()

    def preload_selected_model(self):
        if self.is_busy():
            messagebox.showinfo(APP_NAME, "Zaten devam eden bir işlem var.")
            return
        model_size = self.model_var.get()
        self.set_buttons_busy(True)
        self.status_var.set("Model hazırlanıyor...")
        self._start_activity(f"Model hazırlanıyor — {model_size}")
        self.preload_worker = threading.Thread(target=self.run_preload, args=(model_size,), daemon=True)
        self.preload_worker.start()

    def run_preload(self, model_size: str):
        try:
            self.get_model(model_size)
            self.log(f"Seçili model hazır: {model_size}")
            self.set_status("Model hazır")
            self.after(0, lambda: self._finish_activity("Model hazır"))
        except Exception as exc:
            self.log("HATA:")
            self.log(str(exc))
            self.log(traceback.format_exc())
            self.set_status("Hata")
            self.after(0, lambda: self._finish_activity("Hata"))
            self.after(0, lambda: messagebox.showerror(APP_NAME, f"Model hazırlanamadı:\n\n{exc}"))
        finally:
            self.after(0, lambda: self.set_buttons_busy(False))

    def get_model(self, model_size: str) -> WhisperModel:
        if self.cached_model is not None and self.cached_model_size == model_size:
            self.log(f"Önceden yüklenmiş model kullanılıyor: {model_size}")
            self.set_stage(f"Hazır model kullanılıyor — {model_size}")
            return self.cached_model

        self.set_stage(f"Model yükleniyor — {model_size}")
        self.log(f"Model yükleniyor: {model_size}")
        if model_size in {"large-v3", "turbo"}:
            self.log("Büyük model seçildi. İlk kullanımda indirme/yükleme birkaç dakika sürebilir; sayaç işlem süresini gösterir.")
        else:
            self.log("İlk kez kullanılıyorsa model indirilebilir; bu işlem biraz sürebilir.")
        model = WhisperModel(model_size, device="cpu", compute_type="int8")
        self.cached_model = model
        self.cached_model_size = model_size
        self.set_loaded_model_label(model_size)
        self.log(f"Model hazır: {model_size}")
        self.set_stage(f"Model hazır — {model_size}")
        return model

    def run_job(self, opts: JobOptions):
        try:
            opts.output_dir.mkdir(parents=True, exist_ok=True)

            if opts.local_file:
                media_path = Path(opts.local_file)
                self.log(f"Dosya seçildi: {media_path}")
            else:
                self.set_stage("Video linki indiriliyor")
                media_path = download_media(opts.instagram_url, opts.output_dir, opts.cookies_browser, self.log)
                self.log(f"İndirildi: {media_path}")

            if not media_path.exists():
                raise FileNotFoundError(f"Dosya bulunamadı: {media_path}")

            base_name = safe_filename(media_path.stem)
            txt_timed = opts.output_dir / f"{base_name}.zamanli.txt"
            txt_plain = opts.output_dir / f"{base_name}.duz_metin.txt"
            srt_path = opts.output_dir / f"{base_name}.srt"
            raw_txt_timed = opts.output_dir / f"{base_name}.ham.zamanli.txt"
            raw_txt_plain = opts.output_dir / f"{base_name}.ham.duz_metin.txt"
            raw_srt_path = opts.output_dir / f"{base_name}.ham.srt"

            model = self.get_model(opts.model_size)

            language = None if opts.language == "auto" else opts.language
            initial_prompt = None

            self.set_stage("Yazıya çeviriliyor")
            self.log("Yazıya çevirme başladı...")
            kwargs = {
                "language": language,
                "vad_filter": True,
                "vad_parameters": {
                    "min_silence_duration_ms": 700,
                    "speech_pad_ms": 200,
                },
                "beam_size": 5,
                "initial_prompt": initial_prompt,
                "condition_on_previous_text": False,
                "temperature": 0,
                "no_speech_threshold": 0.72,
                "compression_ratio_threshold": 2.4,
                "log_prob_threshold": -1.0,
                "word_timestamps": True,
                "hallucination_silence_threshold": 2.0,
            }
            if opts.test_first_minute:
                kwargs["clip_timestamps"] = "0,60"
                self.log("Test modu açık: sadece ilk 1 dakika çevrilecek.")

            kwargs = supported_transcribe_kwargs(model, kwargs)
            segments_iter, info = model.transcribe(str(media_path), **kwargs)

            detected = getattr(info, "language", "?")
            total_duration = getattr(info, "duration", None)
            progress_total = float(total_duration or 0)
            if opts.test_first_minute and progress_total:
                progress_total = min(progress_total, 60.0)
            self.log(f"Algılanan dil: {detected}")
            if total_duration:
                self.log(f"Medya süresi: {format_elapsed(float(total_duration))}")
                if float(total_duration) >= 600 and not opts.test_first_minute:
                    self.log("Uzun medya algılandı. İşlem sürebilir; yüzde ve tahmini kalan süre ekranda güncellenecek.")

            self.start_determinate_progress()
            self.set_transcribe_progress(0, progress_total if progress_total else None)

            raw_segments = []
            for seg in segments_iter:
                if self.cancel_requested:
                    raise UserCancelled("İşlem kullanıcı tarafından iptal edildi.")
                if opts.test_first_minute and float(getattr(seg, "start", 0) or 0) >= 60.0:
                    break
                raw_segments.append(seg)
                processed = float(getattr(seg, "end", 0) or 0)
                if opts.test_first_minute:
                    processed = min(processed, 60.0)
                self.set_transcribe_progress(processed, progress_total if progress_total else None, getattr(seg, "text", ""))

            if self.cancel_requested:
                raise UserCancelled("İşlem kullanıcı tarafından iptal edildi.")

            self.set_stage("Güvenli bitiş filtresi uygulanıyor")
            segments, removed_segments = clean_segments(raw_segments, total_duration)
            if removed_segments:
                self.log(f"Güvenli bitiş filtresi {len(removed_segments)} şüpheli segmenti ana çıktıdan kaldırdı.")
                for removed in removed_segments[:5]:
                    self.log(f"Kaldırılan segment: [{format_timestamp(removed.start)} - {format_timestamp(removed.end)}] {removed.text.strip()}")
                write_txt(raw_txt_timed, raw_segments)
                write_plain_txt(raw_txt_plain, raw_segments)
                write_srt(raw_srt_path, raw_segments)
                self.log(f"Ham çıktı ayrıca kaydedildi: {raw_txt_plain}")
            else:
                self.log("Güvenli bitiş filtresi kaldırılacak şüpheli segment bulmadı.")

            if segments:
                self.set_transcribe_progress(progress_total if progress_total else float(segments[-1].end), progress_total if progress_total else None, segments[-1].text)

            self.set_stage("Çıktılar yazılıyor")
            write_txt(txt_timed, segments)
            write_plain_txt(txt_plain, segments)
            write_srt(srt_path, segments)

            self.log("Bitti.")
            self.log(f"Zamanlı TXT: {txt_timed}")
            self.log(f"Düz metin TXT: {txt_plain}")
            self.log(f"SRT altyazı: {srt_path}")
            self.set_status("Bitti")
            self.after(0, lambda: self._finish_activity("Tamamlandı"))
            self.after(0, lambda: messagebox.showinfo(APP_NAME, "Yazıya çevirme tamamlandı. Çıktı klasörünü açabilirsin."))
        except UserCancelled as exc:
            self.log(str(exc))
            self.set_status("İptal edildi")
            self.after(0, lambda: self._finish_activity("İptal edildi"))
            self.after(0, lambda: messagebox.showinfo(APP_NAME, "İşlem iptal edildi."))
        except Exception as exc:
            self.log("HATA:")
            self.log(str(exc))
            self.log(traceback.format_exc())
            self.set_status("Hata")
            self.after(0, lambda: self._finish_activity("Hata"))
            self.after(0, lambda: messagebox.showerror(APP_NAME, f"İşlem başarısız oldu:\n\n{exc}"))
        finally:
            self.after(0, lambda: self.set_buttons_busy(False))


if __name__ == "__main__":
    app = InstaYaziyaCevirApp()
    app.mainloop()
