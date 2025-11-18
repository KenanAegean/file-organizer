from __future__ import annotations
import threading
import time
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from file_organizer import OrganizerConfig, organize_folder, OrganizeResult


class OrganizerGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("File Organizator")
        self.geometry("650x450")

        self.folder_var = tk.StringVar()
        self.config_var = tk.StringVar(value="config.json")
        self.recursive_var = tk.BooleanVar(value=True)
        self.dry_run_var = tk.BooleanVar(value=False)
        self.interval_var = tk.StringVar(value="0")  # minutes

        self._auto_running = False
        self._auto_thread: threading.Thread | None = None

        self._build_widgets()

    # ---------- UI ----------

    def _build_widgets(self):
        padding = {"padx": 8, "pady": 4}

        frm_top = ttk.Frame(self)
        frm_top.pack(fill="x", pady=5)

        # Folder selection
        ttk.Label(frm_top, text="Folder:").grid(row=0, column=0, sticky="w", **padding)
        ttk.Entry(frm_top, textvariable=self.folder_var, width=50).grid(
            row=0, column=1, sticky="we", **padding
        )
        ttk.Button(frm_top, text="Browse...", command=self.browse_folder).grid(
            row=0, column=2, **padding
        )

        # Config
        ttk.Label(frm_top, text="Config:").grid(row=1, column=0, sticky="w", **padding)
        ttk.Entry(frm_top, textvariable=self.config_var, width=50).grid(
            row=1, column=1, sticky="we", **padding
        )
        ttk.Button(frm_top, text="Browse...", command=self.browse_config).grid(
            row=1, column=2, **padding
        )

        frm_top.columnconfigure(1, weight=1)

        # Options
        frm_opts = ttk.LabelFrame(self, text="Options")
        frm_opts.pack(fill="x", padx=8, pady=4)

        ttk.Checkbutton(frm_opts, text="Recursive", variable=self.recursive_var).grid(
            row=0, column=0, sticky="w", **padding
        )
        ttk.Checkbutton(frm_opts, text="Dry-run (no changes)", variable=self.dry_run_var).grid(
            row=0, column=1, sticky="w", **padding
        )

        ttk.Label(frm_opts, text="Auto-run interval (minutes, 0 = off):").grid(
            row=1, column=0, sticky="w", **padding
        )
        ttk.Entry(frm_opts, textvariable=self.interval_var, width=8).grid(
            row=1, column=1, sticky="w", **padding
        )

        # Buttons
        frm_btns = ttk.Frame(self)
        frm_btns.pack(fill="x", padx=8, pady=4)

        ttk.Button(frm_btns, text="Run once", command=self.run_once).pack(
            side="left", padx=4
        )
        self.btn_auto = ttk.Button(frm_btns, text="Start auto-run", command=self.toggle_auto_run)
        self.btn_auto.pack(side="left", padx=4)

        # Log area
        frm_log = ttk.LabelFrame(self, text="Log")
        frm_log.pack(fill="both", expand=True, padx=8, pady=6)

        self.txt_log = tk.Text(frm_log, height=15, wrap="word")
        self.txt_log.pack(fill="both", expand=True, padx=4, pady=4)

        # Small status bar
        self.status_var = tk.StringVar(value="Ready.")
        ttk.Label(self, textvariable=self.status_var, anchor="w").pack(
            fill="x", side="bottom", padx=4, pady=2
        )

    # ---------- Helpers ----------

    def log(self, msg: str):
        self.txt_log.insert("end", msg + "\n")
        self.txt_log.see("end")

    def browse_folder(self):
        folder = filedialog.askdirectory(title="Select folder to organize")
        if folder:
            self.folder_var.set(folder)

    def browse_config(self):
        path = filedialog.askopenfilename(
            title="Select config.json",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")],
        )
        if path:
            self.config_var.set(path)

    def _load_settings(self):
        folder = Path(self.folder_var.get().strip()).expanduser()
        config_path = Path(self.config_var.get().strip()).expanduser()

        if not folder.exists():
            raise ValueError(f"Folder does not exist: {folder}")
        if not config_path.exists():
            raise ValueError(f"Config file does not exist: {config_path}")

        recursive = self.recursive_var.get()
        dry_run = self.dry_run_var.get()

        interval_str = self.interval_var.get().strip() or "0"
        try:
            interval_min = int(interval_str)
            if interval_min < 0:
                raise ValueError
        except ValueError:
            raise ValueError("Interval must be a non-negative integer.")

        config = OrganizerConfig.from_json(config_path)
        return folder, config, recursive, dry_run, interval_min

    # ---------- Actions ----------

    def run_once(self):
        try:
            folder, config, recursive, dry_run, _ = self._load_settings()
        except ValueError as e:
            messagebox.showerror("Error", str(e))
            return

        self.status_var.set("Running...")
        self.log(f"\n=== Run started on {folder} ===")
        self.update_idletasks()

        def worker():
            result: OrganizeResult = organize_folder(
                folder, config, recursive=recursive, dry_run=dry_run, verbose=False
            )
            summary_lines = [
                "Summary:",
                *[f"  {cat}: {cnt} file(s)" for cat, cnt in result.moved.items()],
                f"  Unmapped: {result.skipped_unmapped}",
                f"  Other skipped: {result.skipped_other}",
            ]
            self.after(0, lambda: self._finish_run(summary_lines))

        threading.Thread(target=worker, daemon=True).start()

    def _finish_run(self, summary_lines):
        for line in summary_lines:
            self.log(line)
        self.status_var.set("Done.")

    def toggle_auto_run(self):
        if self._auto_running:
            self._auto_running = False
            self.btn_auto.configure(text="Start auto-run")
            self.status_var.set("Auto-run stopped.")
            return

        try:
            folder, config, recursive, dry_run, interval_min = self._load_settings()
        except ValueError as e:
            messagebox.showerror("Error", str(e))
            return

        if interval_min == 0:
            messagebox.showinfo("Info", "Set interval > 0 to enable auto-run.")
            return

        self._auto_running = True
        self.btn_auto.configure(text="Stop auto-run")
        self.status_var.set(f"Auto-run every {interval_min} minute(s).")

        def auto_worker():
            interval_sec = interval_min * 60
            while self._auto_running:
                self.log("\n=== Auto-run cycle started ===")
                try:
                    result: OrganizeResult = organize_folder(
                        folder, config, recursive=recursive, dry_run=dry_run, verbose=False
                    )
                    summary_lines = [
                        "Summary:",
                        *[f"  {cat}: {cnt} file(s)" for cat, cnt in result.moved.items()],
                        f"  Unmapped: {result.skipped_unmapped}",
                        f"  Other skipped: {result.skipped_other}",
                    ]
                    self.after(0, lambda sl=summary_lines: [self.log(line) for line in sl])
                except Exception as exc:
                    self.after(0, lambda e=exc: self.log(f"Error: {e}"))

                for _ in range(interval_sec):
                    if not self._auto_running:
                        break
                    time.sleep(1)

            self.after(0, lambda: self.status_var.set("Auto-run stopped."))

        self._auto_thread = threading.Thread(target=auto_worker, daemon=True)
        self._auto_thread.start()


if __name__ == "__main__":
    app = OrganizerGUI()
    app.mainloop()
