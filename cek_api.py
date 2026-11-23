import os
import time
import threading
import webbrowser
import requests
import tkinter as tk
from tkinter import ttk, messagebox
from dotenv import load_dotenv

# Load environment variables dari .env
load_dotenv()

DEFAULT_GEMINI_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""
OPENWEATHER_KEY = os.getenv("OPENWEATHER_API_KEY", "")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")

# Palet Warna Modern Dark UI (Senada dengan send_manual.py)
BG_MAIN = "#0B0E14"
BG_CARD = "#151A23"
BG_INPUT = "#1E2532"
FG_TEXT = "#F1F5F9"
FG_MUTED = "#94A3B8"
ACCENT = "#FF4B4B"
ACCENT_HOVER = "#E03E3E"
ACCENT_BLUE = "#38BDF8"
SUCCESS = "#34D399"
WARNING = "#FBBF24"
BORDER_COLOR = "#2D3748"

# Info Kuota Free Tier Google AI Studio
FREE_TIER_QUOTA_INFO = {
    "gemini-3.5-flash-lite": "Free Tier: Limit RPM & RPD tertinggi (seri Flash-Lite terbaru, hemat token & cepat)",
    "gemini-3.8-flash": "Free Tier: Limit RPM & RPD tinggi (seri Flash terbaru untuk respon cepat)",
    "gemini-3.1-pro-preview": "Free Tier: Limit harian lebih ketat (seri Pro untuk penalaran kompleks)",
}


class GeminiApiCheckerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Bebebai Control Center • Cek API & Kuota Gemini")
        self.root.geometry("560x690")
        self.root.configure(bg=BG_MAIN)
        self.root.resizable(True, True)

        self.show_key = False

        # Setup Style ttk
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Dark.TCombobox",
            fieldbackground=BG_INPUT,
            background=BG_CARD,
            foreground=FG_TEXT,
            arrowcolor=FG_TEXT,
            bordercolor=BORDER_COLOR,
            lightcolor=BG_INPUT,
            darkcolor=BG_INPUT,
            padding=8,
        )
        style.map(
            "Dark.TCombobox",
            fieldbackground=[("readonly", BG_INPUT)],
            foreground=[("readonly", FG_TEXT)],
            selectbackground=[("readonly", BG_INPUT)],
            selectforeground=[("readonly", FG_TEXT)],
        )
        self.root.option_add("*TCombobox*Listbox.background", BG_INPUT)
        self.root.option_add("*TCombobox*Listbox.foreground", FG_TEXT)
        self.root.option_add("*TCombobox*Listbox.selectBackground", ACCENT)
        self.root.option_add("*TCombobox*Listbox.selectForeground", "#FFFFFF")

        main_frame = tk.Frame(root, bg=BG_MAIN, padx=22, pady=16)
        main_frame.pack(fill="both", expand=True)

        # --- HEADER ---
        header_frame = tk.Frame(main_frame, bg=BG_MAIN)
        header_frame.pack(side="top", fill="x", pady=(0, 12))

        tk.Label(
            header_frame,
            text="BEBEBAI API & QUOTA CHECKER",
            font=("Segoe UI", 14, "bold"),
            bg=BG_MAIN,
            fg=FG_TEXT,
        ).pack(anchor="w")
        tk.Label(
            header_frame,
            text="Validasi Gemini API Key, kecepatan respon, daftar model & limit kuota",
            font=("Segoe UI", 9),
            bg=BG_MAIN,
            fg=FG_MUTED,
        ).pack(anchor="w", pady=(2, 0))

        # --- TOMBOL AKSI BAWAH (DIKUNCI DI BOTTOM) ---
        btn_frame = tk.Frame(main_frame, bg=BG_MAIN)
        btn_frame.pack(side="bottom", fill="x", pady=(12, 0))

        self.btn_test = tk.Button(
            btn_frame,
            text="⚡ CEK GEMINI API & KUOTA",
            command=self.start_check_gemini,
            font=("Segoe UI", 10, "bold"),
            bg=ACCENT,
            fg="#FFFFFF",
            activebackground=ACCENT_HOVER,
            activeforeground="#FFFFFF",
            relief="flat",
            pady=11,
            cursor="hand2",
        )
        self.btn_test.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.btn_other = tk.Button(
            btn_frame,
            text="🌐 Cek .env Lain",
            command=self.start_check_other_apis,
            font=("Segoe UI", 9, "bold"),
            bg=BG_INPUT,
            fg=FG_TEXT,
            activebackground=BORDER_COLOR,
            activeforeground=FG_TEXT,
            relief="flat",
            padx=14,
            pady=11,
            cursor="hand2",
        )
        self.btn_other.pack(side="right")

        # --- CARD UTAMA ---
        card = tk.Frame(
            main_frame,
            bg=BG_CARD,
            padx=16,
            pady=14,
            highlightbackground=BORDER_COLOR,
            highlightthickness=1,
        )
        card.pack(side="top", fill="both", expand=True)

        # 1. INPUT GEMINI API KEY
        key_header = tk.Frame(card, bg=BG_CARD)
        key_header.pack(fill="x", pady=(0, 4))

        tk.Label(
            key_header,
            text="GEMINI API KEY (OTOMATIS DARI .ENV / INPUT MANUAL)",
            font=("Segoe UI", 8, "bold"),
            bg=BG_CARD,
            fg=FG_MUTED,
        ).pack(side="left")

        link_ai_studio = tk.Label(
            key_header,
            text="Buka AI Studio ↗",
            font=("Segoe UI", 8, "underline"),
            bg=BG_CARD,
            fg=ACCENT_BLUE,
            cursor="hand2",
        )
        link_ai_studio.pack(side="right")
        link_ai_studio.bind(
            "<Button-1>", lambda e: webbrowser.open("https://aistudio.google.com/apikey")
        )

        key_wrapper = tk.Frame(
            card, bg=BG_INPUT, highlightbackground=BORDER_COLOR, highlightthickness=1
        )
        key_wrapper.pack(fill="x", pady=(0, 12))

        self.api_key_var = tk.StringVar(value=DEFAULT_GEMINI_KEY)
        self.key_entry = tk.Entry(
            key_wrapper,
            textvariable=self.api_key_var,
            font=("Consolas", 10),
            bg=BG_INPUT,
            fg=FG_TEXT,
            insertbackground=FG_TEXT,
            relief="flat",
            show="•",
        )
        self.key_entry.pack(side="left", fill="x", expand=True, padx=10, pady=8)

        self.btn_toggle_key = tk.Button(
            key_wrapper,
            text="👁️",
            command=self.toggle_key_visibility,
            font=("Segoe UI", 9),
            bg=BG_INPUT,
            fg=FG_MUTED,
            activebackground=BORDER_COLOR,
            activeforeground=FG_TEXT,
            relief="flat",
            padx=8,
            cursor="hand2",
        )
        self.btn_toggle_key.pack(side="right")

        # 2. PILIHAN MODEL GEMINI (SERI TERBARU)
        tk.Label(
            card,
            text="MODEL TARGET PENGUJIAN (OTOMATIS UPDATE DARI SERVER)",
            font=("Segoe UI", 8, "bold"),
            bg=BG_CARD,
            fg=FG_MUTED,
        ).pack(anchor="w", pady=(0, 4))

        models = [
            "gemini-3.5-flash-lite",
            "gemini-3.8-flash",
            "gemini-3.1-pro-preview",
        ]
        self.model_var = tk.StringVar(value=models[0])
        self.model_dropdown = ttk.Combobox(
            card,
            textvariable=self.model_var,
            values=models,
            state="readonly",
            font=("Segoe UI", 10),
            style="Dark.TCombobox",
        )
        self.model_dropdown.pack(fill="x", pady=(0, 12))

        # 3. STATUS BADGE RINGKAS
        status_bar = tk.Frame(
            card, bg=BG_INPUT, padx=12, pady=8, highlightbackground=BORDER_COLOR, highlightthickness=1
        )
        status_bar.pack(fill="x", pady=(0, 12))

        self.status_badge = tk.Label(
            status_bar,
            text="⚪ SIAP DICEK — Klik tombol di bawah untuk mulai",
            font=("Segoe UI", 9, "bold"),
            bg=BG_INPUT,
            fg=FG_MUTED,
        )
        self.status_badge.pack(anchor="w")

        # 4. OUTPUT LOG / DETAIL KUOTA
        log_header = tk.Frame(card, bg=BG_CARD)
        log_header.pack(fill="x", pady=(0, 4))

        tk.Label(
            log_header,
            text="HASIL DIAGNOSA API, TOKEN & INFORMASI KUOTA",
            font=("Segoe UI", 8, "bold"),
            bg=BG_CARD,
            fg=FG_MUTED,
        ).pack(side="left")

        link_quota = tk.Label(
            log_header,
            text="Cek Grafik Kuota Live ↗",
            font=("Segoe UI", 8, "underline"),
            bg=BG_CARD,
            fg=ACCENT_BLUE,
            cursor="hand2",
        )
        link_quota.pack(side="right")
        link_quota.bind(
            "<Button-1>", lambda e: webbrowser.open("https://aistudio.google.com/rate-limit")
        )

        log_wrapper = tk.Frame(
            card, bg=BG_INPUT, highlightbackground=BORDER_COLOR, highlightthickness=1
        )
        log_wrapper.pack(fill="both", expand=True)

        scrollbar = tk.Scrollbar(log_wrapper, bg=BG_INPUT, troughcolor=BG_CARD)
        scrollbar.pack(side="right", fill="y")

        self.log_box = tk.Text(
            log_wrapper,
            height=12,
            font=("Consolas", 9),
            wrap="word",
            bg=BG_INPUT,
            fg=FG_TEXT,
            insertbackground=FG_TEXT,
            selectbackground=ACCENT,
            relief="flat",
            padx=10,
            pady=10,
            yscrollcommand=scrollbar.set,
        )
        self.log_box.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.log_box.yview)

        self.write_log(
            "💡 Tips:\n"
            "• Model default sudah diperbarui ke 'gemini-3.5-flash-lite' dan 'gemini-3.8-flash'.\n"
            "• Setelah tombol cek ditekan, dropdown model juga otomatis diisi daftar model aktif dari akunmu.\n"
            "• Klik '⚡ CEK GEMINI API & KUOTA' untuk memulai pengujian."
        )

    def toggle_key_visibility(self):
        self.show_key = not self.show_key
        self.key_entry.config(show="" if self.show_key else "•")
        self.btn_toggle_key.config(text="🙈" if self.show_key else "👁️")

    def write_log(self, text, clear=True):
        self.log_box.config(state="normal")
        if clear:
            self.log_box.delete("1.0", tk.END)
        self.log_box.insert(tk.END, text + "\n")
        self.log_box.see(tk.END)
        self.log_box.config(state="disabled")

    def update_dropdown_models(self, available_models):
        if not available_models:
            return
        priority = ["gemini-3.5-flash-lite", "gemini-3.8-flash", "gemini-3.1-pro-preview"]
        merged = list(dict.fromkeys(priority + available_models))
        self.model_dropdown["values"] = merged

    def start_check_gemini(self):
        api_key = self.api_key_var.get().strip()
        if not api_key:
            messagebox.showwarning(
                "API Key Kosong",
                "Masukkan GEMINI_API_KEY terlebih dahulu atau simpan di file .env!",
            )
            return

        model = self.model_var.get()
        self.btn_test.config(state="disabled", text="⏳ MENGECEK API...", bg="#475569")
        self.status_badge.config(text="🟡 Menghubungi server Google Gemini API...", fg=WARNING)
        self.write_log(f"🔍 Memulai pengecekan model: {model}...\n")

        threading.Thread(
            target=self.execute_gemini_check, args=(api_key, model), daemon=True
        ).start()

    def execute_gemini_check(self, api_key, model):
        lines = []
        badge_text = ""
        badge_color = ACCENT

        try:
            # 1. Cek Validitas Key & Daftar Model Aktif
            models_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
            res_models = requests.get(models_url, timeout=15)

            if res_models.status_code != 200:
                err_json = res_models.json()
                err_msg = err_json.get("error", {}).get("message", res_models.text)
                badge_text = f"🔴 API KEY BERMASALAH (HTTP {res_models.status_code})"
                lines.append(f"❌ Gagal verifikasi API Key:\n{err_msg}")
                self.root.after(0, self.finish_check, badge_text, badge_color, "\n".join(lines))
                return

            raw_models = res_models.json().get("models", [])
            gen_models = [
                m.get("name", "").replace("models/", "")
                for m in raw_models
                if "generateContent" in m.get("supportedGenerationMethods", [])
            ]
            self.root.after(0, self.update_dropdown_models, gen_models)

            latest_models = [m for m in gen_models if "gemini-3" in m]

            lines.append("✅ STATUS API KEY : VALID & AKTIF")
            lines.append(f"📦 Model Generate  : {len(gen_models)} model siap pakai")
            if latest_models:
                lines.append(f"✨ Seri Gemini 3   : {', '.join(latest_models[:6])}")
            lines.append("-" * 48)

            # 2. Kirim Test Prompt Ringan (1-token test) untuk cek Kuota & Latency
            gen_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
            payload = {
                "contents": [{"parts": [{"text": "Balas 1 kata saja: OK"}]}],
                "generationConfig": {"maxOutputTokens": 10},
            }

            t0 = time.time()
            res_gen = requests.post(gen_url, json=payload, timeout=20)
            latency_ms = int((time.time() - t0) * 1000)

            rl_headers = {
                k: v for k, v in res_gen.headers.items() if "ratelimit" in k.lower() or "quota" in k.lower()
            }

            if res_gen.status_code == 200:
                data = res_gen.json()
                reply_text = (
                    data.get("candidates", [{}])[0]
                    .get("content", {})
                    .get("parts", [{}])[0]
                    .get("text", "")
                    .strip()
                )
                usage = data.get("usageMetadata", {})
                p_tok = usage.get("promptTokenCount", 0)
                c_tok = usage.get("candidatesTokenCount", 0)
                t_tok = usage.get("totalTokenCount", 0)

                badge_text = f"🟢 API BERFUNGSI NORMAL ({latency_ms} ms)"
                badge_color = SUCCESS

                lines.append(f"🚀 TEST GENERATE ({model}): BERHASIL")
                lines.append(f"⏱️ Kecepatan Respon : {latency_ms} ms")
                lines.append(f"💬 Balasan Test     : '{reply_text}'")
                lines.append(f"🎟️ Pemakaian Token  : {t_tok} token (Input: {p_tok}, Output: {c_tok})")
                lines.append("-" * 48)
                lines.append("📊 INFORMASI KUOTA & LIMIT:")
                lines.append("• Status Kuota Saat Ini : TERSEDIA (Tidak terkena limit 429)")
                lines.append(f"• {FREE_TIER_QUOTA_INFO.get(model, 'Free Tier Google AI Studio aktif')}")
                lines.append(
                    "• Catatan: Klik 'Cek Grafik Kuota Live ↗' di kanan atas untuk melihat sisa kuota harian di AI Studio."
                )
                if rl_headers:
                    lines.append(f"• Header Rate-Limit: {rl_headers}")

            elif res_gen.status_code == 429:
                err_msg = res_gen.json().get("error", {}).get("message", "Quota exceeded")
                badge_text = "🟠 KUOTA HABIS / RATE LIMIT (HTTP 429)"
                badge_color = WARNING
                lines.append(f"⚠️ TEST GENERATE ({model}): LIMIT KUOTA TERCAPAI (429)")
                lines.append(f"Detail: {err_msg}")
                lines.append("\n💡 Solusi: Tunggu 1 menit (jika limit RPM) atau ganti ke model 'gemini-3.5-flash-lite'.")
            else:
                err_msg = res_gen.json().get("error", {}).get("message", res_gen.text)
                badge_text = f"🔴 GAGAL TEST MODEL (HTTP {res_gen.status_code})"
                lines.append(f"❌ Error pada model {model}:\n{err_msg}")

        except Exception as e:
            badge_text = "🔴 KONEKSI ERROR"
            lines.append(f"❌ Terjadi kesalahan jaringan:\n{str(e)}")

        self.root.after(0, self.finish_check, badge_text, badge_color, "\n".join(lines))

    def start_check_other_apis(self):
        self.btn_other.config(state="disabled", text="⏳ Mengecek...")
        self.status_badge.config(text="🟡 Mengecek OpenWeather & Telegram Bot Token...", fg=WARNING)
        threading.Thread(target=self.execute_other_checks, daemon=True).start()

    def execute_other_checks(self):
        lines = ["🌐 PENGECEKAN API PENDUKUNG BEBEBAI (.ENV)", "-" * 48]

        if OPENWEATHER_KEY:
            try:
                r = requests.get(
                    f"https://api.openweathermap.org/data/2.5/weather?lat=-7.76&lon=110.40&appid={OPENWEATHER_KEY}",
                    timeout=10,
                )
                if r.status_code == 200:
                    lines.append("✅ OpenWeatherMap API : AKTIF (Limit Free: 60 req/menit, 1.000 req/hari)")
                else:
                    lines.append(f"❌ OpenWeatherMap API : ERROR (HTTP {r.status_code})")
            except Exception as e:
                lines.append(f"❌ OpenWeatherMap API : GAGAL ({e})")
        else:
            lines.append("⚠️ OpenWeatherMap API : Tidak ditemukan di .env")

        if TELEGRAM_TOKEN:
            try:
                r = requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getMe", timeout=10)
                if r.status_code == 200:
                    bot_user = r.json().get("result", {}).get("username", "-")
                    lines.append(f"✅ Telegram Bot API   : AKTIF (@{bot_user})")
                else:
                    lines.append(f"❌ Telegram Bot API   : ERROR (HTTP {r.status_code})")
            except Exception as e:
                lines.append(f"❌ Telegram Bot API   : GAGAL ({e})")
        else:
            lines.append("⚠️ Telegram Bot API   : Tidak ditemukan di .env")

        self.root.after(
            0,
            self.finish_other_check,
            "🟢 SELESAI CEK API PENDUKUNG",
            SUCCESS,
            "\n".join(lines),
        )

    def finish_check(self, badge_text, badge_color, full_log):
        self.btn_test.config(state="normal", text="⚡ CEK GEMINI API & KUOTA", bg=ACCENT)
        self.status_badge.config(text=badge_text, fg=badge_color)
        self.write_log(full_log)

    def finish_other_check(self, badge_text, badge_color, full_log):
        self.btn_other.config(state="normal", text="🌐 Cek .env Lain")
        self.status_badge.config(text=badge_text, fg=badge_color)
        self.write_log(full_log)


if __name__ == "__main__":
    root = tk.Tk()
    app = GeminiApiCheckerApp(root)
    root.mainloop()