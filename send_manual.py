import os
import threading
import requests
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_IDS_RAW = os.getenv("TELEGRAM_CHAT_IDS", "")
ENV_CHAT_IDS = [cid.strip() for cid in CHAT_IDS_RAW.split(",") if cid.strip()]

KELFIN_ID = "5880216671"
KENAR_ID = "5793257682"

BG_MAIN = "#0B0E14"
BG_CARD = "#151A23"
BG_INPUT = "#1E2532"
FG_TEXT = "#F1F5F9"
FG_MUTED = "#94A3B8"
ACCENT = "#FF4B4B"
ACCENT_HOVER = "#E03E3E"
BORDER_COLOR = "#2D3748"

class ModernTelegramSender:
    def __init__(self, root):
        self.root = root
        self.root.title("Bebebai Control Center • Manual Sender")
        self.root.geometry("540x680")
        self.root.configure(bg=BG_MAIN)
        self.root.resizable(True, True)

        self.selected_file = None

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
            padding=8
        )
        style.map(
            "Dark.TCombobox",
            fieldbackground=[("readonly", BG_INPUT)],
            foreground=[("readonly", FG_TEXT)],
            selectbackground=[("readonly", BG_INPUT)],
            selectforeground=[("readonly", FG_TEXT)]
        )
        self.root.option_add("*TCombobox*Listbox.background", BG_INPUT)
        self.root.option_add("*TCombobox*Listbox.foreground", FG_TEXT)
        self.root.option_add("*TCombobox*Listbox.selectBackground", ACCENT)
        self.root.option_add("*TCombobox*Listbox.selectForeground", "#FFFFFF")

        main_frame = tk.Frame(root, bg=BG_MAIN, padx=22, pady=16)
        main_frame.pack(fill="both", expand=True)

        # --- HEADER (TOP) ---
        header_frame = tk.Frame(main_frame, bg=BG_MAIN)
        header_frame.pack(side="top", fill="x", pady=(0, 12))

        tk.Label(
            header_frame, text="BEBEBAI MANUAL SENDER",
            font=("Segoe UI", 14, "bold"), bg=BG_MAIN, fg=FG_TEXT
        ).pack(anchor="w")
        tk.Label(
            header_frame, text="Kirim pesan teks, link, atau media langsung ke Telegram",
            font=("Segoe UI", 9), bg=BG_MAIN, fg=FG_MUTED
        ).pack(anchor="w", pady=(2, 0))

        # --- TOMBOL SEND (DIKUNCI DI BOTTOM AGAR TIDAK PERNAH TERPOTONG) ---
        self.btn_send = tk.Button(
            main_frame, text="🚀 KIRIM SEKARANG", command=self.start_sending,
            font=("Segoe UI", 10, "bold"), bg=ACCENT, fg="#FFFFFF",
            activebackground=ACCENT_HOVER, activeforeground="#FFFFFF",
            relief="flat", pady=12, cursor="hand2"
        )
        self.btn_send.pack(side="bottom", fill="x", pady=(12, 0))

        # --- CARD CONTAINER (MENGISI SISA RUANG TENGAH) ---
        card = tk.Frame(
            main_frame, bg=BG_CARD, padx=16, pady=14,
            highlightbackground=BORDER_COLOR, highlightthickness=1
        )
        card.pack(side="top", fill="both", expand=True)

        # 1. PILIHAN PENERIMA
        tk.Label(
            card, text="TUJUAN PENGIRIMAN", font=("Segoe UI", 8, "bold"),
            bg=BG_CARD, fg=FG_MUTED
        ).pack(anchor="w", pady=(0, 4))

        all_ids = ENV_CHAT_IDS if ENV_CHAT_IDS else [KENAR_ID, KELFIN_ID]
        self.contacts = {
            "👥 Semua Penerima (Broadcast)": all_ids,
            f"💖 Kenar ({KENAR_ID})": [KENAR_ID],
            f"🛠️ Kelfin ({KELFIN_ID})": [KELFIN_ID]
        }

        options = list(self.contacts.keys())
        self.target_var = tk.StringVar(value=options[1])
        self.target_dropdown = ttk.Combobox(
            card, textvariable=self.target_var, values=options,
            state="readonly", font=("Segoe UI", 10), style="Dark.TCombobox"
        )
        self.target_dropdown.pack(fill="x", pady=(0, 12))

        # 2. KOLOM TEKS PESAN
        tk.Label(
            card, text="ISI PESAN / CAPTION (SUPPORT MARKDOWN)",
            font=("Segoe UI", 8, "bold"), bg=BG_CARD, fg=FG_MUTED
        ).pack(anchor="w", pady=(0, 4))

        text_wrapper = tk.Frame(
            card, bg=BG_INPUT, highlightbackground=BORDER_COLOR, highlightthickness=1
        )
        text_wrapper.pack(fill="both", expand=True, pady=(0, 12))

        scrollbar = tk.Scrollbar(text_wrapper, bg=BG_INPUT, troughcolor=BG_CARD)
        scrollbar.pack(side="right", fill="y")

        self.text_box = tk.Text(
            text_wrapper, height=6, font=("Segoe UI", 10), wrap="word",
            bg=BG_INPUT, fg=FG_TEXT, insertbackground=FG_TEXT,
            selectbackground=ACCENT, relief="flat", padx=10, pady=8,
            yscrollcommand=scrollbar.set
        )
        self.text_box.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.text_box.yview)

        # 3. KOLOM LINK / URL
        tk.Label(
            card, text="TAUTAN / LINK URL (OPSIONAL)",
            font=("Segoe UI", 8, "bold"), bg=BG_CARD, fg=FG_MUTED
        ).pack(anchor="w", pady=(0, 4))

        link_wrapper = tk.Frame(
            card, bg=BG_INPUT, highlightbackground=BORDER_COLOR, highlightthickness=1
        )
        link_wrapper.pack(fill="x", pady=(0, 4))

        self.link_var = tk.StringVar()
        self.link_entry = tk.Entry(
            link_wrapper, textvariable=self.link_var, font=("Segoe UI", 10),
            bg=BG_INPUT, fg="#38BDF8", insertbackground=FG_TEXT,
            relief="flat"
        )
        self.link_entry.pack(fill="x", padx=10, pady=6)

        self.preview_var = tk.BooleanVar(value=True)
        self.chk_preview = tk.Checkbutton(
            card, text="Tampilkan web preview link di Telegram",
            variable=self.preview_var, bg=BG_CARD, fg=FG_MUTED,
            activebackground=BG_CARD, activeforeground=FG_TEXT,
            selectcolor=BG_INPUT, font=("Segoe UI", 8)
        )
        self.chk_preview.pack(anchor="w", pady=(0, 10))

        # 4. ATTACHMENT FILE
        tk.Label(
            card, text="LAMPIRAN MEDIA / DOKUMEN (OPSIONAL)",
            font=("Segoe UI", 8, "bold"), bg=BG_CARD, fg=FG_MUTED
        ).pack(anchor="w", pady=(0, 4))

        attach_frame = tk.Frame(card, bg=BG_CARD)
        attach_frame.pack(fill="x")

        self.btn_attach = tk.Button(
            attach_frame, text="📎 Pilih File", command=self.choose_file,
            font=("Segoe UI", 9, "bold"), bg=BG_INPUT, fg=FG_TEXT,
            activebackground=BORDER_COLOR, activeforeground=FG_TEXT,
            relief="flat", padx=12, pady=5, cursor="hand2"
        )
        self.btn_attach.pack(side="left")

        self.btn_clear_file = tk.Button(
            attach_frame, text="✕", command=self.clear_file,
            font=("Segoe UI", 9, "bold"), bg=BG_INPUT, fg=ACCENT,
            activebackground=BORDER_COLOR, activeforeground=ACCENT,
            relief="flat", padx=8, pady=5, state="disabled", cursor="hand2"
        )
        self.btn_clear_file.pack(side="left", padx=(6, 10))

        self.file_label = tk.Label(
            attach_frame, text="Belum ada file dilampirkan",
            font=("Segoe UI", 9, "italic"), bg=BG_CARD, fg=FG_MUTED
        )
        self.file_label.pack(side="left", fill="x")

    def choose_file(self):
        file_path = filedialog.askopenfilename(title="Pilih Gambar, Video, Audio, atau Dokumen")
        if file_path:
            self.selected_file = file_path
            filename = os.path.basename(file_path)
            display_name = filename if len(filename) <= 34 else filename[:31] + "..."
            self.file_label.config(text=display_name, fg="#34D399", font=("Segoe UI", 9, "bold"))
            self.btn_clear_file.config(state="normal")

    def clear_file(self):
        self.selected_file = None
        self.file_label.config(text="Belum ada file dilampirkan", fg=FG_MUTED, font=("Segoe UI", 9, "italic"))
        self.btn_clear_file.config(state="disabled")

    def start_sending(self):
        if not TOKEN:
            messagebox.showerror("Config Error", "TELEGRAM_TOKEN tidak ditemukan di file .env!")
            return

        raw_message = self.text_box.get("1.0", tk.END).strip()
        link_url = self.link_var.get().strip()

        if not raw_message and not link_url and not self.selected_file:
            messagebox.showwarning("Input Kosong", "Isi pesan teks, masukkan link, atau pilih file lampiran terlebih dahulu.")
            return

        if raw_message and link_url:
            final_message = f"{raw_message}\n\n🔗 {link_url}"
        elif link_url:
            final_message = link_url
        else:
            final_message = raw_message

        targets = self.contacts[self.target_var.get()]
        disable_preview = not self.preview_var.get()

        self.btn_send.config(state="disabled", text="⏳ MENGIRIM KE TELEGRAM...", bg="#475569")
        threading.Thread(
            target=self.execute_send,
            args=(targets, final_message, self.selected_file, disable_preview),
            daemon=True
        ).start()

    def execute_send(self, targets, message, file_path, disable_preview):
        success_count = 0
        errors = []

        for cid in targets:
            try:
                if file_path:
                    ext = os.path.splitext(file_path)[1].lower()
                    if ext in ['.jpg', '.jpeg', '.png', '.webp']:
                        endpoint, field = "sendPhoto", "photo"
                    elif ext in ['.mp4', '.mov', '.avi', '.mkv']:
                        endpoint, field = "sendVideo", "video"
                    elif ext in ['.mp3', '.wav', '.ogg', '.m4a', '.flac']:
                        endpoint, field = "sendAudio", "audio"
                    else:
                        endpoint, field = "sendDocument", "document"

                    url = f"https://api.telegram.org/bot{TOKEN}/{endpoint}"
                    data = {"chat_id": cid, "parse_mode": "Markdown"}
                    if message:
                        data["caption"] = message

                    with open(file_path, "rb") as f:
                        files = {field: f}
                        res = requests.post(url, data=data, files=files, timeout=60)
                else:
                    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
                    payload = {
                        "chat_id": cid,
                        "text": message,
                        "parse_mode": "Markdown",
                        "disable_web_page_preview": disable_preview
                    }
                    res = requests.post(url, json=payload, timeout=15)

                if res.status_code == 200:
                    success_count += 1
                else:
                    errors.append(f"ID {cid}: {res.json().get('description', res.text)}")
            except Exception as e:
                errors.append(f"ID {cid}: {str(e)}")

        self.root.after(0, self.on_send_complete, success_count, len(targets), errors)

    def on_send_complete(self, success_count, total, errors):
        self.btn_send.config(state="normal", text="🚀 KIRIM SEKARANG", bg=ACCENT)
        if success_count == total:
            messagebox.showinfo("Terkirim", f"✅ Pesan berhasil mendarat ke {success_count} penerima!")
            self.text_box.delete("1.0", tk.END)
            self.link_var.set("")
            self.clear_file()
        else:
            err_msg = "\n".join(errors)
            messagebox.showwarning("Sebagian / Gagal Terkirim", f"Berhasil: {success_count}/{total}\n\nDetail Error:\n{err_msg}")

if __name__ == "__main__":
    root = tk.Tk()
    app = ModernTelegramSender(root)
    root.mainloop()