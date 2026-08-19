import customtkinter as ctk
from tkinter import ttk, messagebox, StringVar
from tkcalendar import DateEntry
import sqlite3
import requests
import threading
import webbrowser
import datetime
import urllib.parse
import subprocess
import json
import time
import random
import math

# ---------------- DATABASE ----------------
conn = sqlite3.connect("productivity.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    priority TEXT,
    date TEXT,
    time TEXT,
    status TEXT,
    category TEXT DEFAULT 'General',
    notes TEXT DEFAULT ''
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS pomodoro_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_name TEXT,
    duration INTEGER,
    completed_at TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS habits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    streak INTEGER DEFAULT 0,
    last_done TEXT,
    icon TEXT DEFAULT '⭐'
)
""")

# Add new columns if upgrading from old DB
try:
    cursor.execute("ALTER TABLE tasks ADD COLUMN category TEXT DEFAULT 'General'")
except:
    pass
try:
    cursor.execute("ALTER TABLE tasks ADD COLUMN notes TEXT DEFAULT ''")
except:
    pass

conn.commit()

# ---------------- CONSTANTS ----------------
CATEGORIES = ["General", "Work", "Health", "Learning", "Personal", "Finance", "Creative"]
HABIT_ICONS = ["💪", "📚", "🏃", "💧", "🧘", "🥗", "😴", "✍️", "🎯", "🌱"]

COLORS = {
    "bg_dark": "#0d0f1a",
    "bg_card": "#141624",
    "bg_hover": "#1c1f30",
    "accent_purple": "#7c3aed",
    "accent_blue": "#2563eb",
    "accent_green": "#059669",
    "accent_orange": "#ea580c",
    "accent_red": "#dc2626",
    "accent_yellow": "#d97706",
    "text_primary": "#f1f5f9",
    "text_secondary": "#94a3b8",
    "border": "#1e2235",
    "sidebar": "#0a0c16",
}

# Priority color map
PRIORITY_COLORS = {
    "High": "#dc2626",
    "Medium": "#d97706",
    "Low": "#059669"
}

# ---------------- GET LIVE LOCATION ----------------
def get_location():
    try:
        data = requests.get("http://ip-api.com/json", timeout=5).json()
        city = data.get("city", "Ahmedabad")
        lat = data.get("lat")
        lon = data.get("lon")
        return city, lat, lon
    except:
        return "Ahmedabad", 23.0225, 72.5714

# ---------------- AI CHATBOT (Free, No API Key) ----------------
def ask_ai(prompt, context=""):
    """Uses Pollinations AI (free, no API key required)"""
    
    try:
        system_msg = (
            "You are an elite AI Productivity Coach named ARIA (Advanced Responsive Intelligence Agent). "
            "You are sharp, direct, motivating, and data-driven. "
            "You help users with task management, time blocking, productivity strategies, focus techniques, habit building, and mental wellness. "
            "Keep responses concise (under 150 words) but impactful. Use emojis sparingly for key points. "
            f"{context}"
        )
        full_prompt = f"{system_msg}\n\nUser: {prompt}\nARIA:"
        encoded = urllib.parse.quote(full_prompt)
        url = f"https://text.pollinations.ai/{encoded}"
        response = requests.get(url, timeout=20)
        if response.status_code == 200:
            return response.text.strip()
        else:
            return get_offline_response(prompt)
    except Exception as e:
        return get_offline_response(prompt)

def get_offline_response(message):
    lower_msg = message.lower()
    if any(x in lower_msg for x in ["hello", "hi", "hey"]):
        return "Hello! I'm ARIA, your AI Productivity Coach. I seem to be offline right now, but I can still help with your tasks. Ask me about your score, plan, or tasks!"
    elif any(x in lower_msg for x in ["score", "productivity", "progress"]):
        cursor.execute("SELECT COUNT(*) FROM tasks")
        total = cursor.fetchone()[0] or 0
        cursor.execute("SELECT COUNT(*) FROM tasks WHERE status='Done'")
        done = cursor.fetchone()[0] or 0
        score = (done / total) * 100 if total > 0 else 0
        return f"📊 Your productivity score is {score:.1f}%. You've completed {done}/{total} tasks. {'Keep pushing!' if score < 50 else 'Great work!'}"
    elif "plan" in lower_msg:
        cursor.execute("SELECT * FROM tasks WHERE status='Pending' ORDER BY priority DESC LIMIT 3")
        tasks = cursor.fetchall()
        if not tasks:
            return "🎉 No pending tasks! You're crushing it. Time to set new goals!"
        result = "📋 Your top priorities:\n"
        for t in tasks:
            result += f"• [{t[2]}] {t[1]}\n"
        return result
    elif "task" in lower_msg:
        cursor.execute("SELECT COUNT(*) FROM tasks WHERE status='Pending'")
        count = cursor.fetchone()[0] or 0
        return f"📝 You have {count} pending tasks. Head to the Tasks tab to manage them efficiently."
    elif any(x in lower_msg for x in ["focus", "pomodoro", "concentrate"]):
        return "🎯 Try the Pomodoro Technique: 25 min deep work → 5 min break → repeat 4x → 30 min long break. Use the Pomodoro tab to track sessions!"
    elif any(x in lower_msg for x in ["tired", "exhausted", "burnout"]):
        return "😮‍💨 Rest is productive. Take a 20-min nap, drink water, and do 5 min of deep breathing. Your brain needs recovery to perform at peak."
    elif any(x in lower_msg for x in ["motivat", "inspire", "stuck"]):
        quotes = [
            "🔥 'The secret of getting ahead is getting started.' — Mark Twain",
            "💪 'Focus on progress, not perfection.' — Anonymous",
            "🚀 'Done is better than perfect.' — Sheryl Sandberg",
            "⚡ 'Energy flows where attention goes.' — Tony Robbins"
        ]
        return random.choice(quotes)
    else:
        return "🤖 I'm currently offline. I can answer questions about your tasks, productivity score, plan, focus techniques, and motivation. Try asking about those!"


# ---------------- MAIN APP ----------------
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class ProductivityApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("ARIA — AI Productivity Agent")
        self.geometry("1200x780")
        self.minsize(1000, 680)
        self.configure(fg_color=COLORS["bg_dark"])

        # Grid layout
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self._build_sidebar()
        self._build_frames()
        self.select_frame("dashboard")

    # ============================================================
    # SIDEBAR
    # ============================================================
    def _build_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=230, corner_radius=0, fg_color=COLORS["sidebar"])
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)
        self.sidebar.grid_rowconfigure(10, weight=1)

        # Logo
        logo_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        logo_frame.grid(row=0, column=0, padx=20, pady=(28, 10), sticky="ew")
        ctk.CTkLabel(logo_frame, text="ARIA", font=ctk.CTkFont(family="Courier", size=28, weight="bold"),
                     text_color="#7c3aed").pack(anchor="w")
        ctk.CTkLabel(logo_frame, text="AI Productivity Agent",
                     font=ctk.CTkFont(size=11), text_color=COLORS["text_secondary"]).pack(anchor="w")

        # Divider
        ctk.CTkFrame(self.sidebar, height=1, fg_color=COLORS["border"]).grid(
            row=1, column=0, sticky="ew", padx=15, pady=(0, 15))

        # Nav items: (label, icon, frame_name)
        nav_items = [
            ("Dashboard", "🏠", "dashboard"),
            ("Tasks", "📝", "tasks"),
            ("Pomodoro", "🍅", "pomodoro"),
            ("Habits", "🔥", "habits"),
            ("Plan & Score", "📊", "plan"),
            ("Relax Agent", "📍", "agent"),
            ("AI Chat", "💬", "chat"),
            ("AI Coach", "⚡", "coach"),
        ]

        self.nav_buttons = {}
        for i, (label, icon, name) in enumerate(nav_items):
            btn = ctk.CTkButton(
                self.sidebar, text=f"  {icon}  {label}", anchor="w",
                font=ctk.CTkFont(size=14), height=42,
                corner_radius=10, border_spacing=10,
                fg_color="transparent", text_color=COLORS["text_secondary"],
                hover_color=COLORS["bg_hover"],
                command=lambda n=name: self.select_frame(n)
            )
            btn.grid(row=i+2, column=0, padx=12, pady=3, sticky="ew")
            self.nav_buttons[name] = btn

        # Bottom: appearance
        ctk.CTkLabel(self.sidebar, text="Theme", font=ctk.CTkFont(size=11),
                     text_color=COLORS["text_secondary"]).grid(row=11, column=0, padx=20, pady=(10, 0), sticky="w")
        self.appearance_menu = ctk.CTkOptionMenu(
            self.sidebar, values=["Dark", "Light", "System"],
            command=ctk.set_appearance_mode,
            fg_color=COLORS["bg_hover"], button_color=COLORS["accent_purple"],
            font=ctk.CTkFont(size=12)
        )
        self.appearance_menu.grid(row=12, column=0, padx=12, pady=(5, 20), sticky="ew")
        self.appearance_menu.set("Dark")

        # Live clock
        self.clock_label = ctk.CTkLabel(self.sidebar, text="", font=ctk.CTkFont(family="Courier", size=13),
                                         text_color=COLORS["text_secondary"])
        self.clock_label.grid(row=13, column=0, padx=20, pady=(0, 15))
        self._update_clock()

    def _update_clock(self):
        now = datetime.datetime.now().strftime("%H:%M:%S\n%a, %d %b %Y")
        self.clock_label.configure(text=now)
        self.after(1000, self._update_clock)

    # ============================================================
    # FRAMES SETUP
    # ============================================================
    def _build_frames(self):
        self.frames = {}
        for name in ["dashboard", "tasks", "pomodoro", "habits", "plan", "agent", "chat", "coach"]:
            frame = ctk.CTkFrame(self, fg_color="transparent")
            self.frames[name] = frame

        self._setup_dashboard_frame()
        self._setup_tasks_frame()
        self._setup_pomodoro_frame()
        self._setup_habits_frame()
        self._setup_plan_frame()
        self._setup_agent_frame()
        self._setup_chat_frame()
        self._setup_coach_frame()

    def select_frame(self, name):
        for n, btn in self.nav_buttons.items():
            if n == name:
                btn.configure(
                    fg_color=COLORS["bg_hover"],
                    text_color=COLORS["text_primary"],
                    font=ctk.CTkFont(size=14, weight="bold")
                )
            else:
                btn.configure(
                    fg_color="transparent",
                    text_color=COLORS["text_secondary"],
                    font=ctk.CTkFont(size=14)
                )
        for f in self.frames.values():
            f.grid_forget()
        self.frames[name].grid(row=0, column=1, sticky="nsew", padx=24, pady=20)
        if name == "tasks":
            self.view_tasks()
        elif name == "dashboard":
            self._refresh_dashboard()
        elif name == "habits":
            self._refresh_habits()

    def _make_card(self, parent, row, col, rowspan=1, colspan=1, padx=8, pady=8):
        card = ctk.CTkFrame(parent, fg_color=COLORS["bg_card"], corner_radius=14,
                             border_width=1, border_color=COLORS["border"])
        card.grid(row=row, column=col, rowspan=rowspan, columnspan=colspan,
                  padx=padx, pady=pady, sticky="nsew")
        return card

    def _section_title(self, parent, text, row=0, col=0, color=None):
        label = ctk.CTkLabel(
            parent, text=text,
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=color or COLORS["text_primary"]
        )
        label.grid(row=row, column=col, sticky="w", pady=(0, 16))
        return label

    # ============================================================
    # DASHBOARD FRAME
    # ============================================================
    def _setup_dashboard_frame(self):
        f = self.frames["dashboard"]
        f.grid_columnconfigure((0, 1, 2, 3), weight=1)
        f.grid_rowconfigure(1, weight=1)

        self._section_title(f, "🏠  Dashboard", row=0, col=0)

        # Stat cards row
        self.dash_stat_frames = []
        stat_info = [
            ("Total Tasks", "📋", COLORS["accent_blue"]),
            ("Completed", "✅", COLORS["accent_green"]),
            ("Pending", "⏳", COLORS["accent_orange"]),
            ("Score", "🏆", COLORS["accent_purple"]),
        ]
        for i, (label, icon, color) in enumerate(stat_info):
            card = self._make_card(f, row=0, col=i, pady=(28, 8))
            card.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(card, text=icon, font=ctk.CTkFont(size=26)).grid(row=0, column=0, pady=(12, 0))
            val_lbl = ctk.CTkLabel(card, text="—", font=ctk.CTkFont(size=28, weight="bold"), text_color=color)
            val_lbl.grid(row=1, column=0)
            ctk.CTkLabel(card, text=label, font=ctk.CTkFont(size=12),
                         text_color=COLORS["text_secondary"]).grid(row=2, column=0, pady=(0, 12))
            self.dash_stat_frames.append(val_lbl)

        # Lower cards
        bottom = ctk.CTkFrame(f, fg_color="transparent")
        bottom.grid(row=1, column=0, columnspan=4, sticky="nsew", pady=(8, 0))
        bottom.grid_columnconfigure((0, 1), weight=1)
        bottom.grid_rowconfigure(0, weight=1)

        # Upcoming tasks card
        left_card = self._make_card(bottom, 0, 0)
        left_card.grid_columnconfigure(0, weight=1)
        left_card.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(left_card, text="📅 Upcoming Tasks", font=ctk.CTkFont(size=15, weight="bold")).grid(
            row=0, column=0, padx=16, pady=(14, 8), sticky="w")
        self.dash_upcoming_box = ctk.CTkTextbox(left_card, font=("Consolas", 13), fg_color="transparent",
                                                 text_color=COLORS["text_primary"])
        self.dash_upcoming_box.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        self.dash_upcoming_box.configure(state="disabled")

        # Quick tips card
        right_card = self._make_card(bottom, 0, 1)
        right_card.grid_columnconfigure(0, weight=1)
        right_card.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(right_card, text="💡 Daily Tip", font=ctk.CTkFont(size=15, weight="bold")).grid(
            row=0, column=0, padx=16, pady=(14, 8), sticky="w")
        tips = [
            "🧠 The 2-minute rule: if a task takes less than 2 minutes, do it NOW.",
            "🎯 Time-block your calendar. Schedule deep work in the morning.",
            "📵 Turn off notifications during focus sessions for 10x productivity.",
            "💧 Drink water every 30 minutes — dehydration kills focus by 20%.",
            "✍️ Write down your top 3 MITs (Most Important Tasks) each morning.",
            "🌙 Plan tomorrow the night before. Sleep preps your brain for it.",
            "🔁 Batch similar tasks together to reduce context-switching overhead.",
            "🏃 A 10-minute walk boosts creativity and problem-solving significantly.",
        ]
        tip_text = random.choice(tips)
        tip_label = ctk.CTkLabel(right_card, text=tip_text, font=ctk.CTkFont(size=13),
                                  text_color=COLORS["text_primary"], wraplength=380, justify="left")
        tip_label.grid(row=1, column=0, padx=16, pady=(0, 16), sticky="nw")

        # Quote
        quotes = [
            ("The secret of getting ahead is getting started.", "Mark Twain"),
            ("Focus on being productive instead of busy.", "Tim Ferriss"),
            ("Done is better than perfect.", "Sheryl Sandberg"),
            ("You don't have to be great to start, but you have to start to be great.", "Zig Ziglar"),
        ]
        q, a = random.choice(quotes)
        quote_card = self._make_card(f, row=2, col=0, colspan=4, pady=(8, 0))
        quote_card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(quote_card, text=f'"{q}"  —  {a}',
                     font=ctk.CTkFont(size=13, slant="italic"),
                     text_color=COLORS["text_secondary"]).grid(row=0, column=0, padx=20, pady=14)
        f.grid_rowconfigure(2, weight=0)

    def _refresh_dashboard(self):
        cursor.execute("SELECT COUNT(*) FROM tasks")
        total = cursor.fetchone()[0] or 0
        cursor.execute("SELECT COUNT(*) FROM tasks WHERE status='Done'")
        done = cursor.fetchone()[0] or 0
        pending = total - done
        score = (done / total * 100) if total > 0 else 0

        vals = [str(total), str(done), str(pending), f"{score:.0f}%"]
        for lbl, val in zip(self.dash_stat_frames, vals):
            lbl.configure(text=val)

        # Upcoming tasks (next 5 pending sorted by date)
        cursor.execute("SELECT name, priority, date, time FROM tasks WHERE status='Pending' ORDER BY date, time LIMIT 5")
        rows = cursor.fetchall()
        self.dash_upcoming_box.configure(state="normal")
        self.dash_upcoming_box.delete("1.0", "end")
        if not rows:
            self.dash_upcoming_box.insert("end", "🎉 All tasks completed! Add new ones to stay on track.")
        for name, pri, date, t in rows:
            dot = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}.get(pri, "⚪")
            self.dash_upcoming_box.insert("end", f"{dot} {name}  ·  {date} {t}\n")
        self.dash_upcoming_box.configure(state="disabled")

    # ============================================================
    # TASKS FRAME
    # ============================================================
    def _setup_tasks_frame(self):
        f = self.frames["tasks"]
        f.grid_columnconfigure(0, weight=1)
        f.grid_rowconfigure(3, weight=1)

        self._section_title(f, "📝  Task Manager", row=0)

        # Input Card
        input_card = self._make_card(f, row=1, col=0, pady=(0, 16))
        input_card.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)

        self.entry_name = ctk.CTkEntry(input_card, placeholder_text="Task name...",
                                        font=ctk.CTkFont(size=14), height=40, corner_radius=8)
        self.entry_name.grid(row=0, column=0, padx=10, pady=(16, 8), sticky="ew")

        self.priority_var = StringVar(value="Medium")
        self.combo_priority = ctk.CTkComboBox(input_card, variable=self.priority_var,
                                               values=["Low", "Medium", "High"],
                                               font=ctk.CTkFont(size=14), height=40, corner_radius=8)
        self.combo_priority.grid(row=0, column=1, padx=10, pady=(16, 8), sticky="ew")

        self.category_var = StringVar(value="General")
        ctk.CTkComboBox(input_card, variable=self.category_var, values=CATEGORIES,
                        font=ctk.CTkFont(size=14), height=40, corner_radius=8).grid(
            row=0, column=2, padx=10, pady=(16, 8), sticky="ew")

        self.entry_date = DateEntry(input_card, width=14, font=("Segoe UI", 13),
                                    background='#1c1f30', foreground='white',
                                    borderwidth=0, date_pattern='yyyy-mm-dd', year=2026)
        self.entry_date.grid(row=0, column=3, padx=10, pady=(16, 8), sticky="ew")

        # Time picker
        time_frame = ctk.CTkFrame(input_card, fg_color="transparent")
        time_frame.grid(row=0, column=4, padx=10, pady=(16, 8), sticky="ew")
        self.hour_var = StringVar(value="09")
        self.min_var = StringVar(value="00")
        self.ampm_var = StringVar(value="AM")
        ctk.CTkOptionMenu(time_frame, variable=self.hour_var, width=65,
                          values=[f"{i:02d}" for i in range(1, 13)]).pack(side="left", padx=2)
        ctk.CTkLabel(time_frame, text=":", font=ctk.CTkFont(size=18, weight="bold")).pack(side="left")
        ctk.CTkOptionMenu(time_frame, variable=self.min_var, width=65,
                          values=[f"{i:02d}" for i in range(0, 60, 5)]).pack(side="left", padx=2)
        ctk.CTkOptionMenu(time_frame, variable=self.ampm_var, width=68,
                          values=["AM", "PM"]).pack(side="left", padx=2)

        # Notes
        self.entry_notes = ctk.CTkEntry(input_card, placeholder_text="Notes (optional)...",
                                         font=ctk.CTkFont(size=13), height=36, corner_radius=8)
        self.entry_notes.grid(row=1, column=0, columnspan=3, padx=10, pady=(0, 12), sticky="ew")

        # Buttons
        btn_frame = ctk.CTkFrame(input_card, fg_color="transparent")
        btn_frame.grid(row=1, column=3, columnspan=2, padx=10, pady=(0, 12), sticky="e")
        ctk.CTkButton(btn_frame, text="➕ Add", height=36, corner_radius=8,
                      fg_color=COLORS["accent_purple"], hover_color="#6d28d9",
                      command=self.add_task).pack(side="left", padx=4)
        ctk.CTkButton(btn_frame, text="✔ Done", height=36, corner_radius=8,
                      fg_color=COLORS["accent_green"], hover_color="#047857",
                      command=self.mark_done).pack(side="left", padx=4)
        ctk.CTkButton(btn_frame, text="🗑 Delete", height=36, corner_radius=8,
                      fg_color=COLORS["accent_red"], hover_color="#b91c1c",
                      command=self.delete_task).pack(side="left", padx=4)

        # Search & filter bar
        filter_frame = ctk.CTkFrame(f, fg_color="transparent")
        filter_frame.grid(row=2, column=0, sticky="ew", pady=(0, 8))
        self.search_var = StringVar()
        self.search_var.trace("w", lambda *a: self.view_tasks())
        ctk.CTkEntry(filter_frame, textvariable=self.search_var, placeholder_text="🔍 Search tasks...",
                     width=280, height=36, corner_radius=8).pack(side="left", padx=(0, 10))
        self.filter_status = StringVar(value="All")
        ctk.CTkSegmentedButton(filter_frame, variable=self.filter_status,
                                values=["All", "Pending", "Done"],
                                command=lambda v: self.view_tasks()).pack(side="left", padx=10)

        # Treeview
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background="#141624", foreground="#f1f5f9",
                        rowheight=38, fieldbackground="#141624", borderwidth=0,
                        font=("Segoe UI", 12))
        style.map("Treeview", background=[("selected", "#7c3aed")])
        style.configure("Treeview.Heading", background="#1c1f30", foreground="#94a3b8",
                        relief="flat", font=("Segoe UI", 11, "bold"))
        style.map("Treeview.Heading", background=[("active", "#7c3aed")])

        self.tree = ttk.Treeview(f, columns=(1, 2, 3, 4, 5, 6, 7), show="headings")
        cols = [("ID", 50, "center"), ("Task", 250, "w"), ("Category", 100, "center"),
                ("Priority", 90, "center"), ("Date", 110, "center"),
                ("Time", 90, "center"), ("Status", 90, "center")]
        for i, (col, w, anchor) in enumerate(cols, 1):
            self.tree.heading(i, text=col)
            self.tree.column(i, width=w, anchor=anchor)
        self.tree.grid(row=3, column=0, sticky="nsew")

        # Color tags
        self.tree.tag_configure("High", foreground="#fca5a5")
        self.tree.tag_configure("Medium", foreground="#fde68a")
        self.tree.tag_configure("Low", foreground="#86efac")
        self.tree.tag_configure("Done", foreground="#64748b")

    def add_task(self):
        name = self.entry_name.get().strip()
        priority = self.priority_var.get()
        category = self.category_var.get()
        date = self.entry_date.get().strip()
        t = f"{self.hour_var.get()}:{self.min_var.get()} {self.ampm_var.get()}"
        notes = self.entry_notes.get().strip()
        if not name or not date:
            messagebox.showwarning("Missing Info", "Please enter a task name and date.")
            return
        cursor.execute("INSERT INTO tasks VALUES (NULL,?,?,?,?,?,?,?)",
                       (name, priority, date, t, "Pending", category, notes))
        conn.commit()
        self.entry_name.delete(0, "end")
        self.entry_notes.delete(0, "end")
        self.view_tasks()

    def view_tasks(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        search = self.search_var.get().lower() if hasattr(self, "search_var") else ""
        status_filter = self.filter_status.get() if hasattr(self, "filter_status") else "All"
        cursor.execute("SELECT id, name, category, priority, date, time, status FROM tasks")
        for row in cursor.fetchall():
            tid, name, cat, pri, date, t, status = row
            if search and search not in name.lower():
                continue
            if status_filter != "All" and status != status_filter:
                continue
            tag = "Done" if status == "Done" else pri
            self.tree.insert("", "end", values=(tid, name, cat or "General", pri, date, t, status), tags=(tag,))

    def mark_done(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Select Task", "Please select a task first.")
            return
        tid = self.tree.item(sel)["values"][0]
        cursor.execute("UPDATE tasks SET status='Done' WHERE id=?", (tid,))
        conn.commit()
        self.view_tasks()

    def delete_task(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Select Task", "Please select a task first.")
            return
        tid = self.tree.item(sel)["values"][0]
        if messagebox.askyesno("Confirm", "Delete this task?"):
            cursor.execute("DELETE FROM tasks WHERE id=?", (tid,))
            conn.commit()
            self.view_tasks()

    # ============================================================
    # POMODORO FRAME
    # ============================================================
    def _setup_pomodoro_frame(self):
        f = self.frames["pomodoro"]
        f.grid_columnconfigure(0, weight=1)
        f.grid_rowconfigure(2, weight=1)

        self._section_title(f, "🍅  Pomodoro Timer", row=0)

        # Timer Card
        timer_card = self._make_card(f, row=1, col=0)
        timer_card.grid_columnconfigure(0, weight=1)

        # Mode selector
        self.pomo_mode = StringVar(value="Focus")
        mode_frame = ctk.CTkFrame(timer_card, fg_color="transparent")
        mode_frame.grid(row=0, column=0, pady=(20, 10))
        ctk.CTkSegmentedButton(mode_frame, variable=self.pomo_mode,
                                values=["Focus (25m)", "Short Break (5m)", "Long Break (15m)"],
                                command=self._pomo_mode_changed).pack()

        # Big timer display
        self.pomo_time_var = StringVar(value="25:00")
        self.pomo_display = ctk.CTkLabel(timer_card, textvariable=self.pomo_time_var,
                                          font=ctk.CTkFont(family="Courier", size=72, weight="bold"),
                                          text_color=COLORS["accent_purple"])
        self.pomo_display.grid(row=1, column=0, pady=10)

        # Progress ring (canvas)
        self.pomo_canvas = ctk.CTkCanvas(timer_card, width=200, height=200,
                                          bg=COLORS["bg_card"], highlightthickness=0)
        self.pomo_canvas.grid(row=2, column=0, pady=5)
        self._draw_pomo_ring(1.0)

        # Session label
        self.pomo_session_label = ctk.CTkLabel(timer_card, text="Session 1 of 4",
                                                font=ctk.CTkFont(size=14),
                                                text_color=COLORS["text_secondary"])
        self.pomo_session_label.grid(row=3, column=0)

        # Task label
        self.pomo_task_var = StringVar(value="No task selected")
        ctk.CTkLabel(timer_card, textvariable=self.pomo_task_var,
                     font=ctk.CTkFont(size=13), text_color=COLORS["text_secondary"]).grid(row=4, column=0)

        # Controls
        ctrl_frame = ctk.CTkFrame(timer_card, fg_color="transparent")
        ctrl_frame.grid(row=5, column=0, pady=(10, 20))
        self.pomo_start_btn = ctk.CTkButton(ctrl_frame, text="▶  Start", width=120, height=44,
                                             corner_radius=22, font=ctk.CTkFont(size=16, weight="bold"),
                                             fg_color=COLORS["accent_green"], hover_color="#047857",
                                             command=self._pomo_toggle)
        self.pomo_start_btn.pack(side="left", padx=8)
        ctk.CTkButton(ctrl_frame, text="↺  Reset", width=100, height=44,
                      corner_radius=22, font=ctk.CTkFont(size=15),
                      fg_color=COLORS["bg_hover"], hover_color=COLORS["border"],
                      command=self._pomo_reset).pack(side="left", padx=8)

        # Stats card
        stats_card = self._make_card(f, row=2, col=0)
        stats_card.grid_columnconfigure((0, 1, 2), weight=1)
        ctk.CTkLabel(stats_card, text="Today's Pomodoro Stats",
                     font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, columnspan=3,
                                                                      padx=16, pady=(14, 8))
        self.pomo_count_lbl = ctk.CTkLabel(stats_card, text="0\nSessions", font=ctk.CTkFont(size=20, weight="bold"),
                                            text_color=COLORS["accent_purple"], justify="center")
        self.pomo_count_lbl.grid(row=1, column=0, padx=20, pady=(0, 14))
        self.pomo_focus_lbl = ctk.CTkLabel(stats_card, text="0m\nFocus Time", font=ctk.CTkFont(size=20, weight="bold"),
                                            text_color=COLORS["accent_blue"], justify="center")
        self.pomo_focus_lbl.grid(row=1, column=1, padx=20, pady=(0, 14))
        self.pomo_streak_lbl = ctk.CTkLabel(stats_card, text="0\nStreak", font=ctk.CTkFont(size=20, weight="bold"),
                                             text_color=COLORS["accent_orange"], justify="center")
        self.pomo_streak_lbl.grid(row=1, column=2, padx=20, pady=(0, 14))

        # State vars
        self.pomo_running = False
        self.pomo_seconds = 25 * 60
        self.pomo_total_seconds = 25 * 60
        self.pomo_sessions = 0
        self.pomo_focus_mins = 0
        self._pomo_after_id = None

    def _pomo_mode_changed(self, val):
        self._pomo_reset()
        durations = {"Focus (25m)": 25, "Short Break (5m)": 5, "Long Break (15m)": 15}
        mins = durations.get(val, 25)
        self.pomo_seconds = mins * 60
        self.pomo_total_seconds = mins * 60
        self.pomo_time_var.set(f"{mins:02d}:00")
        self._draw_pomo_ring(1.0)

    def _draw_pomo_ring(self, fraction):
        self.pomo_canvas.delete("all")
        cx, cy, r = 100, 100, 80
        # Background circle
        self.pomo_canvas.create_oval(cx-r, cy-r, cx+r, cy+r, outline="#1e2235", width=12)
        # Progress arc
        angle = fraction * 360
        start = 90
        self.pomo_canvas.create_arc(cx-r, cy-r, cx+r, cy+r,
                                     start=start, extent=-angle,
                                     outline=COLORS["accent_purple"], width=12, style="arc")

    def _pomo_toggle(self):
        if not self.pomo_running:
            self.pomo_running = True
            self.pomo_start_btn.configure(text="⏸  Pause", fg_color=COLORS["accent_orange"])
            self._pomo_tick()
        else:
            self.pomo_running = False
            self.pomo_start_btn.configure(text="▶  Resume", fg_color=COLORS["accent_green"])
            if self._pomo_after_id:
                self.after_cancel(self._pomo_after_id)

    def _pomo_tick(self):
        if self.pomo_seconds > 0 and self.pomo_running:
            self.pomo_seconds -= 1
            m, s = divmod(self.pomo_seconds, 60)
            self.pomo_time_var.set(f"{m:02d}:{s:02d}")
            frac = self.pomo_seconds / self.pomo_total_seconds
            self._draw_pomo_ring(frac)
            self._pomo_after_id = self.after(1000, self._pomo_tick)
        elif self.pomo_seconds == 0:
            self.pomo_running = False
            self._pomo_complete()

    def _pomo_complete(self):
        mode = self.pomo_mode.get()
        if "Focus" in mode:
            self.pomo_sessions += 1
            self.pomo_focus_mins += 25
            cursor.execute("INSERT INTO pomodoro_log VALUES (NULL, ?, ?, ?)",
                           (self.pomo_task_var.get(), 25, datetime.datetime.now().isoformat()))
            conn.commit()
            self.pomo_count_lbl.configure(text=f"{self.pomo_sessions}\nSessions")
            self.pomo_focus_lbl.configure(text=f"{self.pomo_focus_mins}m\nFocus Time")
            self.pomo_session_label.configure(text=f"Session {self.pomo_sessions} completed! 🎉")
            self._play_voice("Focus session complete! Time for a break.")
        else:
            self.pomo_session_label.configure(text="Break over! Ready to focus? 🔥")
            self._play_voice("Break over. Let's get back to work!")
        self.pomo_start_btn.configure(text="▶  Start", fg_color=COLORS["accent_green"])
        self._draw_pomo_ring(0)
        messagebox.showinfo("Timer Complete!", f"{'🍅 Focus session' if 'Focus' in mode else '☕ Break'} complete!")

    def _pomo_reset(self):
        if self._pomo_after_id:
            self.after_cancel(self._pomo_after_id)
        self.pomo_running = False
        self.pomo_start_btn.configure(text="▶  Start", fg_color=COLORS["accent_green"])
        durations = {"Focus (25m)": 25, "Short Break (5m)": 5, "Long Break (15m)": 15}
        mins = durations.get(self.pomo_mode.get(), 25)
        self.pomo_seconds = mins * 60
        self.pomo_total_seconds = mins * 60
        self.pomo_time_var.set(f"{mins:02d}:00")
        self._draw_pomo_ring(1.0)

    # ============================================================
    # HABITS FRAME
    # ============================================================
    def _setup_habits_frame(self):
        f = self.frames["habits"]
        f.grid_columnconfigure(0, weight=1)
        f.grid_rowconfigure(2, weight=1)

        self._section_title(f, "🔥  Habit Tracker", row=0)

        # Add habit card
        add_card = self._make_card(f, row=1, col=0, pady=(0, 16))
        add_card.grid_columnconfigure((0, 1, 2), weight=1)
        self.habit_name_entry = ctk.CTkEntry(add_card, placeholder_text="Habit name (e.g. Drink 2L water)",
                                              height=40, font=ctk.CTkFont(size=14))
        self.habit_name_entry.grid(row=0, column=0, padx=12, pady=14, sticky="ew")
        self.habit_icon_var = StringVar(value="⭐")
        ctk.CTkOptionMenu(add_card, variable=self.habit_icon_var,
                          values=HABIT_ICONS, width=90).grid(row=0, column=1, padx=10)
        ctk.CTkButton(add_card, text="+ Add Habit", height=40, corner_radius=8,
                      fg_color=COLORS["accent_purple"], hover_color="#6d28d9",
                      command=self._add_habit).grid(row=0, column=2, padx=12)

        # Habits grid container
        self.habits_scroll = ctk.CTkScrollableFrame(f, fg_color="transparent")
        self.habits_scroll.grid(row=2, column=0, sticky="nsew")
        self.habits_scroll.grid_columnconfigure((0, 1, 2), weight=1)

    def _add_habit(self):
        name = self.habit_name_entry.get().strip()
        if not name:
            return
        icon = self.habit_icon_var.get()
        cursor.execute("INSERT INTO habits (name, streak, icon) VALUES (?, 0, ?)", (name, icon))
        conn.commit()
        self.habit_name_entry.delete(0, "end")
        self._refresh_habits()

    def _refresh_habits(self):
        for widget in self.habits_scroll.winfo_children():
            widget.destroy()
        cursor.execute("SELECT * FROM habits")
        habits = cursor.fetchall()
        if not habits:
            ctk.CTkLabel(self.habits_scroll, text="No habits yet. Add your first habit above! 🚀",
                         font=ctk.CTkFont(size=15), text_color=COLORS["text_secondary"]).grid(
                row=0, column=0, columnspan=3, pady=40)
            return
        today = datetime.date.today().isoformat()
        for idx, (hid, name, streak, last_done, icon) in enumerate(habits):
            col = idx % 3
            row = idx // 3
            card = ctk.CTkFrame(self.habits_scroll, fg_color=COLORS["bg_card"],
                                 corner_radius=14, border_width=1, border_color=COLORS["border"])
            card.grid(row=row, column=col, padx=8, pady=8, sticky="ew")
            card.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(card, text=icon, font=ctk.CTkFont(size=32)).grid(row=0, column=0, pady=(16, 4))
            ctk.CTkLabel(card, text=name, font=ctk.CTkFont(size=14, weight="bold"),
                         wraplength=160).grid(row=1, column=0, padx=12)
            streak_color = COLORS["accent_orange"] if streak >= 7 else COLORS["accent_green"] if streak >= 3 else COLORS["text_secondary"]
            ctk.CTkLabel(card, text=f"🔥 {streak} day streak",
                         font=ctk.CTkFont(size=13), text_color=streak_color).grid(row=2, column=0, pady=4)
            done_today = last_done == today
            btn_text = "✅ Done Today!" if done_today else "Mark Done"
            btn_color = COLORS["accent_green"] if not done_today else COLORS["bg_hover"]
            ctk.CTkButton(card, text=btn_text, height=36, corner_radius=8,
                          fg_color=btn_color, state="disabled" if done_today else "normal",
                          command=lambda h=hid, s=streak: self._mark_habit(h, s)).grid(
                row=3, column=0, padx=12, pady=(8, 4))
            ctk.CTkButton(card, text="🗑", width=36, height=28, corner_radius=6,
                          fg_color="transparent", text_color=COLORS["text_secondary"],
                          hover_color=COLORS["accent_red"],
                          command=lambda h=hid: self._delete_habit(h)).grid(row=4, column=0, pady=(0, 12))

    def _mark_habit(self, hid, streak):
        today = datetime.date.today().isoformat()
        new_streak = streak + 1
        cursor.execute("UPDATE habits SET streak=?, last_done=? WHERE id=?", (new_streak, today, hid))
        conn.commit()
        self._refresh_habits()

    def _delete_habit(self, hid):
        cursor.execute("DELETE FROM habits WHERE id=?", (hid,))
        conn.commit()
        self._refresh_habits()

    # ============================================================
    # PLAN & SCORE FRAME
    # ============================================================
    def _setup_plan_frame(self):
        f = self.frames["plan"]
        f.grid_columnconfigure(0, weight=1)
        f.grid_rowconfigure(3, weight=1)

        self._section_title(f, "📊  Plan & Productivity Score", row=0)

        btn_card = self._make_card(f, row=1, col=0, pady=(0, 14))
        btn_card.grid_columnconfigure((0, 1, 2), weight=1)
        ctk.CTkButton(btn_card, text="📋 Generate SMART Plan",
                      fg_color=COLORS["accent_purple"], hover_color="#6d28d9",
                      command=self.generate_plan).grid(row=0, column=0, padx=12, pady=14)
        ctk.CTkButton(btn_card, text="📈 Calculate Score",
                      fg_color=COLORS["accent_blue"], hover_color="#1d4ed8",
                      command=self.productivity_score).grid(row=0, column=1, padx=12, pady=14)

        email_frame = ctk.CTkFrame(btn_card, fg_color="transparent")
        email_frame.grid(row=0, column=2, padx=12, pady=14)
        self.email_entry = ctk.CTkEntry(email_frame, placeholder_text="email@example.com",
                                         width=200, height=38)
        self.email_entry.pack(side="left", padx=(0, 8))
        ctk.CTkButton(email_frame, text="📧 Share", height=38, width=80,
                      fg_color=COLORS["accent_green"], hover_color="#047857",
                      command=self.email_plan).pack(side="left")

        # Score bar
        score_card = self._make_card(f, row=2, col=0, pady=(0, 14))
        score_card.grid_columnconfigure(0, weight=1)
        self.score_label = ctk.CTkLabel(score_card, text="Productivity Score: —",
                                         font=ctk.CTkFont(size=16, weight="bold"))
        self.score_label.grid(row=0, column=0, padx=16, pady=(14, 6), sticky="w")
        self.score_bar = ctk.CTkProgressBar(score_card, height=18, corner_radius=9,
                                             progress_color=COLORS["accent_green"])
        self.score_bar.set(0)
        self.score_bar.grid(row=1, column=0, padx=16, pady=(0, 14), sticky="ew")

        self.plan_output = ctk.CTkTextbox(f, font=("Consolas", 13))
        self.plan_output.grid(row=3, column=0, sticky="nsew")

    def email_plan(self):
        text = self.plan_output.get("1.0", "end").strip()
        if not text:
            messagebox.showinfo("Empty", "Generate a plan first!")
            return
        email = self.email_entry.get().strip()
        subject = urllib.parse.quote("My AI Productivity Plan — ARIA")
        body = urllib.parse.quote(text + "\n\nGenerated by ARIA — AI Productivity Agent 🤖")
        webbrowser.open(f"mailto:{email}?subject={subject}&body={body}")

    def generate_plan(self):
        cursor.execute("SELECT * FROM tasks WHERE status='Pending' ORDER BY CASE priority WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END, date, time")
        tasks = cursor.fetchall()
        self.plan_output.delete("1.0", "end")
        if not tasks:
            self.plan_output.insert("end", "🎉 No pending tasks! You're all caught up.\n\nAdd new tasks to plan your next sprint.")
            return
        today = datetime.date.today()
        self.plan_output.insert("end", f"╔══════════════════════════════════════════════╗\n")
        self.plan_output.insert("end", f"║          ARIA — SMART PRODUCTIVITY PLAN       ║\n")
        self.plan_output.insert("end", f"║          Generated: {today.strftime('%d %b %Y')}                  ║\n")
        self.plan_output.insert("end", f"╚══════════════════════════════════════════════╝\n\n")
        current_date = None
        for t in tasks:
            tid, name, pri, date, time_, status, cat, notes = t[0], t[1], t[2], t[3], t[4], t[5], t[6] if len(t) > 6 else "General", t[7] if len(t) > 7 else ""
            if date != current_date:
                current_date = date
                try:
                    d = datetime.date.fromisoformat(date)
                    diff = (d - today).days
                    tag = " (TODAY)" if diff == 0 else f" (in {diff}d)" if diff > 0 else f" ({abs(diff)}d overdue!)"
                except:
                    tag = ""
                self.plan_output.insert("end", f"\n📅 {date}{tag}\n{'─'*40}\n")
            icon = "🔴" if pri == "High" else "🟡" if pri == "Medium" else "🟢"
            self.plan_output.insert("end", f"  {icon} [{pri}] {name}  ({cat})\n")
            self.plan_output.insert("end", f"     ⏰ {time_}\n")
            if notes:
                self.plan_output.insert("end", f"     📝 {notes}\n")

        self.plan_output.insert("end", f"\n{'─'*44}\n")
        self.plan_output.insert("end", f"  Total pending: {len(tasks)} tasks\n")
        high = sum(1 for t in tasks if t[2] == "High")
        if high:
            self.plan_output.insert("end", f"  ⚠️  {high} HIGH priority tasks need immediate attention!\n")

    def productivity_score(self):
        cursor.execute("SELECT COUNT(*) FROM tasks")
        total = cursor.fetchone()[0] or 0
        cursor.execute("SELECT COUNT(*) FROM tasks WHERE status='Done'")
        done = cursor.fetchone()[0] or 0
        cursor.execute("SELECT COUNT(*) FROM tasks WHERE status='Pending' AND date < ?",
                       (datetime.date.today().isoformat(),))
        overdue = cursor.fetchone()[0] or 0
        score = (done / total * 100) if total > 0 else 0
        adjusted = max(0, score - overdue * 5)
        grade = "S" if adjusted >= 90 else "A" if adjusted >= 80 else "B" if adjusted >= 70 else "C" if adjusted >= 60 else "D" if adjusted >= 50 else "F"
        msg = ("🔥 LEGENDARY! You're absolutely crushing it!" if adjusted >= 90 else
               "⚡ Excellent work! You're in peak performance mode." if adjusted >= 80 else
               "💪 Great job! A few more completions and you'll be elite." if adjusted >= 70 else
               "👍 Good progress. Focus on clearing your High priority tasks." if adjusted >= 60 else
               "⚠️ Needs improvement. Let's tackle one task at a time." if adjusted >= 50 else
               "🆘 Low score detected. Let's break tasks into smaller steps and rebuild momentum.")
        self.plan_output.delete("1.0", "end")
        self.plan_output.insert("end", f"╔══════════════════════════════════════╗\n")
        self.plan_output.insert("end", f"║      ARIA — PRODUCTIVITY REPORT       ║\n")
        self.plan_output.insert("end", f"╚══════════════════════════════════════╝\n\n")
        self.plan_output.insert("end", f"  🏆 Score    : {adjusted:.1f}%  (Grade: {grade})\n")
        self.plan_output.insert("end", f"  ✅ Completed: {done}\n")
        self.plan_output.insert("end", f"  📋 Total    : {total}\n")
        self.plan_output.insert("end", f"  ⏳ Pending  : {total - done}\n")
        self.plan_output.insert("end", f"  🚨 Overdue  : {overdue}\n\n")
        self.plan_output.insert("end", f"  Feedback: {msg}\n")
        self.score_label.configure(text=f"Productivity Score: {adjusted:.1f}%  (Grade {grade})")
        self._animate_progress(0, adjusted / 100)

    def _animate_progress(self, curr, target):
        if curr < target:
            curr = min(curr + 0.03, target)
            self.score_bar.set(curr)
            color = COLORS["accent_red"] if curr < 0.4 else COLORS["accent_yellow"] if curr < 0.7 else COLORS["accent_green"]
            self.score_bar.configure(progress_color=color)
            self.after(16, lambda: self._animate_progress(curr, target))

    # ============================================================
    # RELAX AGENT FRAME
    # ============================================================
    def _setup_agent_frame(self):
        f = self.frames["agent"]
        f.grid_columnconfigure(0, weight=1)
        f.grid_rowconfigure(2, weight=1)

        self._section_title(f, "📍  Nearby Places Finder", row=0)

        btn_card = self._make_card(f, row=1, col=0, pady=(0, 16))
        btn_card.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)
        ctk.CTkLabel(btn_card, text="Find Nearby:", font=ctk.CTkFont(size=14)).grid(row=0, column=0, padx=16, pady=14)
        places = [("🌳 Gardens", "garden"), ("☕ Cafes", "cafe"),
                  ("📚 Libraries", "library"), ("🏋️ Gyms", "gym")]
        for i, (label, kw) in enumerate(places, 1):
            ctk.CTkButton(btn_card, text=label, height=40, corner_radius=8,
                          fg_color=COLORS["bg_hover"], hover_color=COLORS["accent_purple"],
                          command=lambda k=kw: self._find_places_thread(k)).grid(
                row=0, column=i, padx=8, pady=14)

        self.agent_output = ctk.CTkTextbox(f, font=("Consolas", 14))
        self.agent_output.grid(row=2, column=0, sticky="nsew")
        self.agent_output.insert("end", "Click a button above to find places near you 🗺️")

    def _find_places_thread(self, kw):
        self.agent_output.delete("1.0", "end")
        self.agent_output.insert("end", f"🔍 Finding {kw}s near you...\n")
        threading.Thread(target=self._find_places, args=(kw,), daemon=True).start()

    def _find_places(self, kw):
        try:
            city, lat, lon = get_location()
            url = "https://nominatim.openstreetmap.org/search"
            params = {"q": f"{kw} {city}", "format": "json", "limit": 6}
            headers = {"User-Agent": "ARIAProductivityApp/2.0"}
            res = requests.get(url, params=params, headers=headers, timeout=10).json()
            self.agent_output.delete("1.0", "end")
            self.agent_output.insert("end", f"📍 Your Location: {city}  ({lat}, {lon})\n")
            self.agent_output.insert("end", f"🔍 Top {kw.capitalize()}s Nearby:\n")
            self.agent_output.insert("end", "═" * 55 + "\n\n")
            if not res:
                self.agent_output.insert("end", "No results found. Try a different category.")
                return
            for i, p in enumerate(res, 1):
                self.agent_output.insert("end", f"  {i}. {p.get('display_name', 'Unknown')}\n")
                self.agent_output.insert("end", f"     📌 {p.get('lat')}, {p.get('lon')}\n\n")
                maps_url = f"https://www.openstreetmap.org/?mlat={p.get('lat')}&mlon={p.get('lon')}&zoom=16"
                self.agent_output.insert("end", f"     🗺  {maps_url}\n\n")
        except Exception as e:
            self.agent_output.delete("1.0", "end")
            self.agent_output.insert("end", f"❌ Error: {str(e)}")

    # ============================================================
    # AI CHAT FRAME
    # ============================================================
    def _setup_chat_frame(self):
        f = self.frames["chat"]
        f.grid_columnconfigure(0, weight=1)
        f.grid_rowconfigure(1, weight=1)

        # Header
        header = ctk.CTkFrame(f, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        ctk.CTkLabel(header, text="💬  ARIA Chat",
                     font=ctk.CTkFont(size=20, weight="bold")).pack(side="left")
        self.chat_status = ctk.CTkLabel(header, text="● Online",
                                         font=ctk.CTkFont(size=12), text_color=COLORS["accent_green"])
        self.chat_status.pack(side="right")

        # Chat display
        self.chat_display = ctk.CTkTextbox(f, font=("Segoe UI", 14), wrap="word",
                                            fg_color=COLORS["bg_card"])
        self.chat_display.grid(row=1, column=0, sticky="nsew", pady=(0, 10))
        self.chat_display.configure(state="disabled")
        self._chat_insert("ARIA", "Hello! 👋 I'm ARIA, your AI Productivity Coach. I'm powered by real AI (online) so I can answer any productivity, focus, or motivation question you have.\n\nTry asking me:\n• 'How can I improve my focus?'\n• 'What are the best productivity techniques?'\n• 'Help me plan my day'\n• Or anything about tasks, habits, and goals!", "#7c3aed")

        # Input row
        input_row = ctk.CTkFrame(f, fg_color="transparent")
        input_row.grid(row=2, column=0, sticky="ew")
        input_row.grid_columnconfigure(0, weight=1)
        self.chat_input = ctk.CTkEntry(input_row, placeholder_text="Ask ARIA anything...",
                                        height=46, font=ctk.CTkFont(size=14), corner_radius=12)
        self.chat_input.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.chat_input.bind("<Return>", lambda e: self._send_message())
        ctk.CTkButton(input_row, text="Send ➤", width=100, height=46, corner_radius=12,
                      fg_color=COLORS["accent_purple"], hover_color="#6d28d9",
                      font=ctk.CTkFont(size=14, weight="bold"),
                      command=self._send_message).grid(row=0, column=1)

        # Quick prompts
        quick_frame = ctk.CTkFrame(f, fg_color="transparent")
        quick_frame.grid(row=3, column=0, sticky="ew", pady=(8, 0))
        prompts = ["🎯 Daily Plan", "💡 Focus Tips", "⚡ Motivation", "😮‍💨 Burnout Help"]
        for p in prompts:
            ctk.CTkButton(quick_frame, text=p, height=30, corner_radius=15,
                          font=ctk.CTkFont(size=12), fg_color=COLORS["bg_hover"],
                          hover_color=COLORS["accent_purple"],
                          command=lambda x=p: self._quick_prompt(x)).pack(side="left", padx=4)

    def _quick_prompt(self, prompt):
        self.chat_input.delete(0, "end")
        self.chat_input.insert(0, prompt.split(" ", 1)[1])
        self._send_message()

    def _chat_insert(self, sender, text, color=None):
        self.chat_display.configure(state="normal")
        self.chat_display.insert("end", f"\n{sender}:\n", ("sender",))
        self.chat_display.insert("end", f"{text}\n")
        self.chat_display.yview_moveto(1)
        self.chat_display.configure(state="disabled")

    def _send_message(self):
        msg = self.chat_input.get().strip()
        if not msg:
            return
        self.chat_input.delete(0, "end")
        self._chat_insert("You", msg, COLORS["accent_blue"])
        self._chat_insert("ARIA", "⏳ Thinking...", COLORS["text_secondary"])
        self.chat_status.configure(text="● Thinking...", text_color=COLORS["accent_yellow"])
        threading.Thread(target=self._process_chat, args=(msg,), daemon=True).start()

    def _process_chat(self, msg):
        # Build context from current tasks
        cursor.execute("SELECT COUNT(*) FROM tasks WHERE status='Pending'")
        pending = cursor.fetchone()[0] or 0
        cursor.execute("SELECT COUNT(*) FROM tasks WHERE status='Done'")
        done = cursor.fetchone()[0] or 0
        context = f"The user has {pending} pending tasks and {done} completed tasks. Today is {datetime.date.today().strftime('%A, %d %B %Y')}."
        response = ask_ai(msg, context)
        self.after(0, lambda: self._update_chat(response))

    def _update_chat(self, response):
        self.chat_display.configure(state="normal")
        # Remove "thinking" line
        content = self.chat_display.get("1.0", "end")
        lines = content.splitlines()
        # Find and remove last "⏳ Thinking..." block
        idx = None
        for i in range(len(lines) - 1, -1, -1):
            if "⏳ Thinking..." in lines[i]:
                idx = i
                break
        if idx is not None:
            # Remove from that line
            line_count = self.chat_display.index("end-1c").split(".")[0]
            # Simpler: rebuild
            new_lines = [l for l in lines if "⏳ Thinking..." not in l]
            self.chat_display.delete("1.0", "end")
            self.chat_display.insert("end", "\n".join(new_lines))
        self.chat_display.configure(state="disabled")
        self._chat_insert("ARIA", response, COLORS["accent_purple"])
        self.chat_status.configure(text="● Online", text_color=COLORS["accent_green"])
        self._play_voice(response[:200])

    # ============================================================
    # AI COACH FRAME
    # ============================================================
    def _setup_coach_frame(self):
        f = self.frames["coach"]
        f.grid_columnconfigure(0, weight=1)
        f.grid_rowconfigure(3, weight=1)

        self._section_title(f, "⚡  AI Coach Check-in", row=0)

        q_label = ctk.CTkLabel(f, text="How are you feeling right now?",
                                font=ctk.CTkFont(size=16), text_color=COLORS["text_secondary"])
        q_label.grid(row=1, column=0, sticky="w", pady=(0, 16))

        btn_card = ctk.CTkFrame(f, fg_color="transparent")
        btn_card.grid(row=2, column=0, sticky="ew", pady=(0, 16))
        btn_card.grid_columnconfigure((0, 1, 2, 3), weight=1)

        states = [
            ("🔥 High Energy", "high", COLORS["accent_orange"], "#c2410c"),
            ("🙂 Normal", "normal", COLORS["accent_blue"], "#1d4ed8"),
            ("🥱 Tired", "tired", COLORS["accent_yellow"], "#b45309"),
            ("😵 Burned Out", "burnout", COLORS["accent_red"], "#b91c1c"),
        ]
        for i, (label, state, fg, hov) in enumerate(states):
            ctk.CTkButton(btn_card, text=label, height=54, corner_radius=12,
                          font=ctk.CTkFont(size=15, weight="bold"),
                          fg_color=fg, hover_color=hov,
                          command=lambda s=state: self._coach_suggest(s)).grid(
                row=0, column=i, padx=6, sticky="ew")

        self.coach_output = ctk.CTkTextbox(f, font=("Segoe UI", 15), wrap="word")
        self.coach_output.grid(row=3, column=0, sticky="nsew")
        self.coach_output.insert("end", "Select your energy level above for an instant AI coaching recommendation!")

        self.coach_action_frame = ctk.CTkFrame(f, fg_color="transparent")
        self.coach_action_frame.grid(row=4, column=0, sticky="ew", pady=(12, 0))

    def _coach_suggest(self, state):
        self.coach_output.configure(state="normal")
        self.coach_output.delete("1.0", "end")
        for w in self.coach_action_frame.winfo_children():
            w.destroy()

        cursor.execute("SELECT * FROM tasks WHERE status='Pending'")
        tasks = cursor.fetchall()
        today = datetime.date.today().isoformat()
        high = [t for t in tasks if t[2] == "High"]
        med = [t for t in tasks if t[2] == "Medium"]
        low = [t for t in tasks if t[2] == "Low"]
        due_today_high = [t for t in high if t[3] == today]
        msg = ""
        action_task = None
        action_type = None

        if not tasks:
            msg = "🎉 You have NO pending tasks! Absolutely incredible. Take a moment to celebrate your productivity. Then set new goals to keep the momentum going!"
        elif state in ["tired", "normal"] and due_today_high:
            msg = f"🚨 ALERT: Despite how you're feeling, you have {len(due_today_high)} HIGH PRIORITY task(s) due TODAY!\n\n"
            msg += f"You must complete: '{due_today_high[0][1]}' before resting.\nI believe in you — one focused sprint and you're done."
            action_task = due_today_high[0]
            action_type = "done"
        elif state == "high":
            msg = "🔥 PEAK STATE DETECTED!\n\nYou're in flow. This is your PRIME window for deep work. Don't waste it on emails or low-value tasks.\n\n"
            target = high[0] if high else (med[0] if med else low[0] if low else None)
            if target:
                msg += f"➡️ Attack your hardest task NOW: '{target[1]}'\n\nAfter completion, take a 5-minute break. You'll build incredible momentum."
                action_task = target
            action_type = "done"
        elif state == "normal":
            msg = "🙂 Solid state. You're reliable and consistent right now.\n\n"
            target = med[0] if med else (high[0] if high else low[0] if low else None)
            if target:
                msg += f"Recommended: '{target[1]}'\n\nWork in 25-min Pomodoro blocks. Steady consistency beats erratic bursts every time."
                action_task = target
            action_type = "done"
        elif state == "tired":
            msg = "🥱 You're running low on fuel.\n\nDon't force deep cognitive work — you'll make mistakes and it'll take longer anyway.\n\n"
            if low:
                msg += f"Try something easy: '{low[0][1]}' — a quick win will re-ignite your momentum.\n\nThen take a proper 20-min nap or go for a short walk outside."
                action_task = low[0]
                action_type = "done"
            else:
                msg += "Take a 15-minute break. Step away from the screen completely."
                action_type = "timer"
        elif state == "burnout":
            msg = "😵 BURNOUT WARNING.\n\n⛔ STOP WORKING IMMEDIATELY.\n\nContinuing will damage your productivity for the NEXT 3 days, not just today. Your brain needs recovery.\n\n"
            msg += "Required actions:\n1. Step outside for 15 minutes\n2. Drink a full glass of water\n3. Call or message a friend\n4. Sleep at least 8 hours tonight\n\nI'll reschedule all your tasks to tomorrow."
            action_type = "reschedule"

        self.coach_output.insert("end", msg)
        self._play_voice(msg[:300])

        if action_type == "done" and action_task:
            ctk.CTkButton(self.coach_action_frame,
                          text=f"✔  Mark '{action_task[1][:30]}...' as Done",
                          height=46, corner_radius=10, font=ctk.CTkFont(size=14, weight="bold"),
                          fg_color=COLORS["accent_green"], hover_color="#047857",
                          command=lambda t=action_task: self._coach_mark_done(t)).pack(pady=8)
        elif action_type == "reschedule":
            ctk.CTkButton(self.coach_action_frame, text="🗓️  Auto-Reschedule All Tasks to Tomorrow",
                          height=46, corner_radius=10, font=ctk.CTkFont(size=14, weight="bold"),
                          fg_color=COLORS["accent_red"], hover_color="#b91c1c",
                          command=self._coach_reschedule).pack(pady=8)
        elif action_type == "timer":
            ctk.CTkButton(self.coach_action_frame, text="⏱️  Start 15-Minute Break Timer",
                          height=46, corner_radius=10, font=ctk.CTkFont(size=14, weight="bold"),
                          fg_color=COLORS["accent_blue"], hover_color="#1d4ed8",
                          command=self._coach_start_timer).pack(pady=8)

    def _coach_mark_done(self, task):
        cursor.execute("UPDATE tasks SET status='Done' WHERE id=?", (task[0],))
        conn.commit()
        for w in self.coach_action_frame.winfo_children():
            w.destroy()
        self.coach_output.insert("end", f"\n\n✅ Done! '{task[1]}' marked complete. Great work!")
        self._play_voice("Awesome! Task marked complete. Great work!")

    def _coach_reschedule(self):
        tomorrow = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()
        cursor.execute("UPDATE tasks SET date=? WHERE status='Pending'", (tomorrow,))
        conn.commit()
        for w in self.coach_action_frame.winfo_children():
            w.destroy()
        self.coach_output.insert("end", f"\n\n🗓️ All tasks rescheduled to {tomorrow}. Now go rest — you've earned it!")
        self._play_voice("All tasks rescheduled to tomorrow. Go rest now!")

    def _coach_start_timer(self):
        for w in self.coach_action_frame.winfo_children():
            w.destroy()
        self.timer_label = ctk.CTkLabel(self.coach_action_frame, text="15:00",
                                         font=ctk.CTkFont(family="Courier", size=40, weight="bold"),
                                         text_color=COLORS["accent_green"])
        self.timer_label.pack(pady=8)
        self._timer_secs = 15 * 60
        self._run_coach_timer()
        self._play_voice("Break timer started. Enjoy your rest.")

    def _run_coach_timer(self):
        if self._timer_secs > 0:
            m, s = divmod(self._timer_secs, 60)
            self.timer_label.configure(text=f"{m:02d}:{s:02d}")
            self._timer_secs -= 1
            self.after(1000, self._run_coach_timer)
        else:
            self.timer_label.configure(text="Break Over! 🔥", text_color=COLORS["accent_orange"])
            self._play_voice("Break over. Time to get back to work!")

    # ============================================================
    # UTILITIES
    # ============================================================
    def _play_voice(self, text):
        clean = text.replace("'", "").replace('"', '').replace('\n', ' ')
        # Limit length for TTS
        clean = clean[:250]
        script = f"Add-Type -AssemblyName System.speech; $s = New-Object System.Speech.Synthesis.SpeechSynthesizer; $s.Speak('{clean}');"
        threading.Thread(
            target=lambda: subprocess.Popen(
                ["powershell", "-NoProfile", "-Command", script],
                creationflags=0x08000000
            ), daemon=True
        ).start()


if __name__ == "__main__":
    app = ProductivityApp()
    app.mainloop()
