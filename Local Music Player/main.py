import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pygame
import os
import json
import time
import io
import sys
import math
import random


# PyInstaller资源访问支持
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


# 导入依赖
try:
    import mutagen
    from mutagen.mp3 import MP3
    from mutagen.id3 import ID3, USLT, COMM, APIC

    MUTAGEN_AVAILABLE = True
except ImportError:
    MUTAGEN_AVAILABLE = False

try:
    from PIL import Image, ImageTk, ImageDraw

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


class MusicPlayer:
    def __init__(self, root):
        self.root = root
        self.root.title("Python 极简音乐播放器 - 黑胶律动版")
        self.root.geometry("1100x850")
        self.root.resizable(True, True)

        # 样式配置
        self.setup_styles()

        # 初始化pygame
        pygame.init()
        pygame.mixer.init()
        self.MUSIC_END_EVENT = pygame.USEREVENT + 1
        pygame.mixer.music.set_endevent(self.MUSIC_END_EVENT)

        # 核心变量
        self.current_song = -1
        self.is_playing = False
        self.playlist = []
        self.lyrics = []
        self.current_lyric_index = 0
        self.play_mode = "list_loop"
        self.volume = 0.6
        pygame.mixer.music.set_volume(self.volume)

        # 时间控制
        self.song_total_length = 0.0
        self.start_offset = 0.0
        self.is_dragging_progress = False
        self.paused_time = 0.0

        # --- 歌词滚动显示相关 ---
        self.lyric_font = ("微软雅黑", 14)
        self.lyric_height = 28          # 每行歌词之间的垂直间距
        self.visible_lines = 7          # 同时可见的行数

        # --- 频谱图物理模拟变量 ---
        self.spectrum_bars = 64
        self.spec_heights = [0.0] * self.spectrum_bars
        self.spec_velocities = [0.0] * self.spectrum_bars
        self.energy_offset = 0.0

        self.spectrum_colors = [
            "#5D3FD3", "#4B0082", "#0000FF", "#0096FF", "#00FFFF",
            "#00FF99", "#33FF33", "#CCFF00", "#FFFF00", "#FFCC00"
        ]

        # --- 封面动画变量 ---
        self.rotation_angle = 0
        self.rotation_timer = None
        self.vinyl_image = None
        self.original_cover = None

        self.create_ui()
        self.auto_load_music()
        self.load_play_memory()
        self.check_events_and_lyrics()

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TFrame", background="#f5f6fa")
        style.configure("TLabel", background="#f5f6fa", foreground="#2f3640", font=("微软雅黑", 10))
        style.configure("TButton", font=("微软雅黑", 10))
        style.configure("Card.TFrame", background="#ffffff", relief="flat")
        self.root.configure(bg="#f5f6fa")

    def create_ui(self):
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # --- 左侧：播放列表 ---
        left_panel = ttk.Frame(main_frame, width=300)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 20))

        ttk.Label(left_panel, text="播放列表", font=("微软雅黑", 14, "bold")).pack(anchor="w", pady=(0, 10))

        list_frame = ttk.Frame(left_panel, style="Card.TFrame")
        list_frame.pack(fill=tk.BOTH, expand=True)

        self.playlist_box = tk.Listbox(
            list_frame, selectmode=tk.SINGLE,
            font=("微软雅黑", 10), bd=0, highlightthickness=0,
            activestyle='none', bg="#ffffff", fg="#2f3640",
            selectbackground="#a29bfe", selectforeground="white"
        )
        self.playlist_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.playlist_box.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.playlist_box.config(yscrollcommand=scrollbar.set)

        # 双击播放
        def on_double_click(event):
            selection = self.playlist_box.curselection()
            if selection:
                self.current_song = selection[0]
                self.play_song()
        self.playlist_box.bind("<Double-Button-1>", on_double_click)

        left_btn_frame = ttk.Frame(left_panel)
        left_btn_frame.pack(fill=tk.X, pady=10)
        ttk.Button(left_btn_frame, text="添加音乐", command=self.import_music).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5)
        )
        ttk.Button(left_btn_frame, text="清空", command=self.clear_playlist).pack(
            side=tk.RIGHT, fill=tk.X, expand=True, padx=(5, 0)
        )

        # --- 右侧：可视化与控制 ---
        right_panel = ttk.Frame(main_frame)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # 1. 黑胶唱片区域
        self.cover_size = 320
        self.cover_canvas = tk.Canvas(
            right_panel, width=self.cover_size, height=self.cover_size,
            bg="#f5f6fa", highlightthickness=0
        )
        self.cover_canvas.pack(pady=10)
        self.draw_default_vinyl()

        # 2. 歌曲信息
        info_frame = ttk.Frame(right_panel)
        info_frame.pack(fill=tk.X, pady=10)
        self.current_song_label = ttk.Label(
            info_frame, text="Python Music Player",
            font=("微软雅黑", 16, "bold"), anchor="center"
        )
        self.current_song_label.pack(fill=tk.X)

        # 3. 歌词显示（滚动）
        self.lyric_canvas = tk.Canvas(
            right_panel, bg="#f5f6fa", height=180, highlightthickness=0
        )
        self.lyric_canvas.pack(fill=tk.X, pady=5)
        self.lyric_canvas.bind("<Configure>", self.on_lyric_canvas_resize)

        # 4. 律动频谱图
        spectrum_container = ttk.Frame(right_panel, style="Card.TFrame", padding=1)
        spectrum_container.pack(fill=tk.X, pady=(10, 20), ipady=5)

        self.spectrum_canvas = tk.Canvas(
            spectrum_container, bg="#1e272e", height=100, highlightthickness=0
        )
        self.spectrum_canvas.pack(fill=tk.BOTH, expand=True)

        # 5. 进度条
        progress_frame = ttk.Frame(right_panel)
        progress_frame.pack(fill=tk.X)

        self.cur_time_label = ttk.Label(progress_frame, text="00:00", font=("Consolas", 9))
        self.cur_time_label.pack(side=tk.LEFT)

        self.progress_var = tk.DoubleVar()
        self.progress_scale = ttk.Scale(
            progress_frame, from_=0, to=100, variable=self.progress_var,
            orient=tk.HORIZONTAL, command=self.on_progress_click
        )
        self.progress_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)
        self.progress_scale.bind("<ButtonPress-1>", self.on_drag_start)
        self.progress_scale.bind("<ButtonRelease-1>", self.on_drag_end)

        self.end_time_label = ttk.Label(progress_frame, text="00:00", font=("Consolas", 9))
        self.end_time_label.pack(side=tk.RIGHT)

        # 6. 控制按钮
        ctrl_frame = ttk.Frame(right_panel)
        ctrl_frame.pack(fill=tk.X, pady=20)

        self.mode_btn = ttk.Button(
            ctrl_frame, text="🔁 列表循环", command=self.toggle_play_mode, width=12
        )
        self.mode_btn.pack(side=tk.LEFT)

        center_ctrl = ttk.Frame(ctrl_frame)
        center_ctrl.pack(side=tk.LEFT, expand=True)

        ttk.Button(center_ctrl, text="⏮", width=5, command=self.prev_song).pack(side=tk.LEFT, padx=5)
        self.play_btn = ttk.Button(center_ctrl, text="▶", width=8, command=self.play_pause)
        self.play_btn.pack(side=tk.LEFT, padx=5)
        ttk.Button(center_ctrl, text="⏭", width=5, command=self.next_song).pack(side=tk.LEFT, padx=5)

        vol_frame = ttk.Frame(ctrl_frame)
        vol_frame.pack(side=tk.RIGHT)
        ttk.Label(vol_frame, text="🔊").pack(side=tk.LEFT)
        self.volume_scale = ttk.Scale(
            vol_frame, from_=0, to=100, orient=tk.HORIZONTAL,
            command=self.set_volume, length=80
        )
        self.volume_scale.set(self.volume * 100)
        self.volume_scale.pack(side=tk.LEFT, padx=5)

    # ---------- 歌词滚动显示相关 ----------
    def on_lyric_canvas_resize(self, event):
        """Canvas 大小变化时重绘歌词"""
        self.update_lyric_display()

    def update_lyric_display(self):
        """
        滚动显示歌词：
        - 当前行居中加粗高亮
        - 已唱/未唱行上下排布，颜色变浅模拟透明
        """
        self.lyric_canvas.delete("all")
        w = self.lyric_canvas.winfo_width()
        h = self.lyric_canvas.winfo_height()
        center_y = h // 2 if h > 0 else 90

        # 未选中歌曲
        if self.current_song == -1 or not self.playlist:
            self.lyric_canvas.create_text(
                w // 2, center_y,
                text="等待播放...",
                font=("微软雅黑", 14),
                fill="#95a5a6"
            )
            return

        # 无歌词
        if not self.lyrics:
            self.lyric_canvas.create_text(
                w // 2, center_y,
                text="纯音乐 / 无歌词",
                font=("微软雅黑", 14),
                fill="#95a5a6"
            )
            return

        idx = self.current_lyric_index
        total = len(self.lyrics)

        # 计算可见范围
        half = self.visible_lines // 2
        start = max(0, idx - half)
        end = min(total, idx + half + 1)

        for i in range(start, end):
            offset = i - idx
            y = center_y + offset * self.lyric_height

            text = self.lyrics[i][1]
            if i == idx:
                # 当前行：高亮显示
                font = ("微软雅黑", 16, "bold")
                color = "#2f3640"
            else:
                # 已唱/未唱：弱化显示（模拟透明度）
                # 已唱在上面偏灰一点，未唱在下面稍微亮一点
                if i < idx:
                    color = "#b2bec3"   # 已经唱过，浅灰
                else:
                    color = "#dfe6e9"   # 还未唱，更淡一点
                font = ("微软雅黑", 13)

            self.lyric_canvas.create_text(
                w // 2, y,
                text=text,
                font=font,
                fill=color,
                width=w - 40,
                justify=tk.CENTER
            )

    # ---------- 黑胶唱片 ----------
    def create_vinyl_record(self, cover_img):
        size = 600
        record = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(record)

        draw.ellipse((0, 0, size, size), fill="#111111")

        center = size // 2
        for r in range(int(size * 0.18), int(size * 0.48), 3):
            color = random.choice(["#222222", "#1a1a1a", "#252525"])
            bbox = (center - r, center - r, center + r, center + r)
            draw.ellipse(bbox, outline=color, width=1)

        label_size = int(size * 0.35)
        if cover_img:
            cover_img = cover_img.resize((label_size, label_size), Image.LANCZOS)
            mask = Image.new("L", (label_size, label_size), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.ellipse((0, 0, label_size, label_size), fill=255)
            offset = (size - label_size) // 2
            record.paste(cover_img, (offset, offset), mask)
        else:
            offset = (size - label_size) // 2
            draw.ellipse(
                (offset, offset, offset + label_size, offset + label_size),
                fill="#e74c3c"
            )

        hole_size = 15
        hole_bbox = (center - hole_size, center - hole_size,
                     center + hole_size, center + hole_size)
        draw.ellipse(hole_bbox, fill="#f5f6fa")

        display_size = self.cover_size - 20
        return record.resize((display_size, display_size), Image.LANCZOS)

    def draw_default_vinyl(self):
        if PIL_AVAILABLE:
            vinyl = self.create_vinyl_record(None)
            self.vinyl_image = vinyl
            self.update_cover_canvas(0)
        else:
            self.cover_canvas.create_oval(10, 10, 310, 310, fill="black")
            self.cover_canvas.create_oval(110, 110, 210, 210, fill="red")

    def update_cover_canvas(self, angle):
        if not self.vinyl_image:
            return
        self.cover_canvas.delete("all")
        rotated = self.vinyl_image.rotate(angle, resample=Image.BICUBIC)
        self.tk_image = ImageTk.PhotoImage(rotated)
        center = self.cover_size // 2
        self.cover_canvas.create_image(center, center, image=self.tk_image)

    def rotate_cover_animation(self):
        if self.is_playing:
            self.rotation_angle = (self.rotation_angle - 1.5) % 360
            self.update_cover_canvas(self.rotation_angle)
            self.rotation_timer = self.root.after(30, self.rotate_cover_animation)

    # ---------- 频谱图 ----------
    def update_spectrum(self):
        self.spectrum_canvas.delete("all")
        width = self.spectrum_canvas.winfo_width()
        height = self.spectrum_canvas.winfo_height()
        bar_width = width / self.spectrum_bars

        if self.is_playing:
            t = time.time()
            beat = (math.sin(t * 5) + 1) * 0.5
            base_energy = self.volume * 80
            is_active = True
        else:
            base_energy = 5
            beat = 0
            is_active = False

        for i in range(self.spectrum_bars):
            if is_active and random.random() < 0.2:
                dist_from_center = abs(i - self.spectrum_bars / 2) / (self.spectrum_bars / 2)
                freq_bias = 1.0 - dist_from_center * 0.5
                boost = random.uniform(5, 20) * self.volume * freq_bias * (0.5 + beat)
                self.spec_velocities[i] += boost

            gravity = 2.5
            self.spec_velocities[i] -= gravity
            self.spec_heights[i] += self.spec_velocities[i]

            if self.spec_heights[i] < 0:
                self.spec_heights[i] = 0
                self.spec_velocities[i] = 0

            max_h = height
            if self.spec_heights[i] > max_h:
                self.spec_heights[i] = max_h
                self.spec_velocities[i] *= -0.5

            self.spec_velocities[i] *= 0.85

        new_heights = list(self.spec_heights)
        for i in range(1, self.spectrum_bars - 1):
            avg = (self.spec_heights[i - 1] +
                   self.spec_heights[i] +
                   self.spec_heights[i + 1]) / 3
            new_heights[i] = self.spec_heights[i] * 0.6 + avg * 0.4
        self.spec_heights = new_heights

        for i in range(self.spectrum_bars):
            x1 = i * bar_width + 1
            y1 = height
            h = self.spec_heights[i]
            if is_active:
                h = max(h, 2)
            y2 = height - h
            x2 = x1 + bar_width - 2

            ratio = min(1.0, h / height)
            color_idx = int(ratio * (len(self.spectrum_colors) - 1))
            color = self.spectrum_colors[color_idx]

            self.spectrum_canvas.create_rectangle(
                x1, y2, x2, y1, fill=color, outline=""
            )
            self.spectrum_canvas.create_rectangle(
                x1, y2 - 4, x2, y2 - 2, fill="#ffffff", outline=""
            )

    # ---------- 播放逻辑 ----------
    def play_song(self):
        if 0 <= self.current_song < len(self.playlist):
            song_path = self.playlist[self.current_song]
            try:
                self.stop_rotation()

                self.song_total_length = 0
                if MUTAGEN_AVAILABLE:
                    try:
                        audio = mutagen.File(song_path)
                        if audio and audio.info:
                            self.song_total_length = audio.info.length
                    except:
                        pass
                if self.song_total_length <= 0:
                    self.song_total_length = 180

                self.progress_scale.config(to=self.song_total_length)
                self.end_time_label.config(text=self.format_time(self.song_total_length))

                pygame.mixer.music.load(song_path)
                pygame.mixer.music.play()

                self.is_playing = True
                self.play_btn.config(text="⏸")
                self.current_song_label.config(text=os.path.basename(song_path))

                self.playlist_box.selection_clear(0, tk.END)
                self.playlist_box.selection_set(self.current_song)
                self.playlist_box.see(self.current_song)

                self.load_lyrics(song_path)
                self.load_cover_image(song_path)

                self.rotate_cover_animation()
                self.save_play_memory()
            except Exception as e:
                print(f"Error: {e}")
                self.next_song()

    def load_cover_image(self, song_path):
        img = None
        if MUTAGEN_AVAILABLE and PIL_AVAILABLE:
            try:
                file = mutagen.File(song_path)
                art_data = None
                if isinstance(file, mutagen.mp3.MP3):
                    if 'APIC:' in file.tags:
                        art_data = file.tags['APIC:'].data
                    else:
                        for tag in file.tags.values():
                            if isinstance(tag, APIC):
                                art_data = tag.data
                                break
                elif isinstance(file, mutagen.id3.ID3):
                    for tag in file.values():
                        if isinstance(tag, APIC):
                            art_data = tag.data
                            break
                elif hasattr(file, 'pictures'):
                    if file.pictures:
                        art_data = file.pictures[0].data

                if art_data:
                    img = Image.open(io.BytesIO(art_data))
            except Exception as e:
                print(f"Cover load error: {e}")

        self.vinyl_image = self.create_vinyl_record(img)
        self.update_cover_canvas(0)

    def play_pause(self):
        if not self.playlist:
            return

        if self.is_playing:
            pygame.mixer.music.pause()
            self.is_playing = False
            self.play_btn.config(text="▶")
            self.paused_time = self.get_current_time()
            self.stop_rotation()
        else:
            if self.current_song == -1:
                self.current_song = 0
                self.play_song()
            else:
                pygame.mixer.music.unpause()
                self.is_playing = True
                self.play_btn.config(text="⏸")
                self.rotate_cover_animation()

    def stop_rotation(self):
        if self.rotation_timer:
            self.root.after_cancel(self.rotation_timer)
            self.rotation_timer = None

    def check_events_and_lyrics(self):
        for event in pygame.event.get():
            if event.type == self.MUSIC_END_EVENT:
                if self.play_mode == "single_loop":
                    self.play_song()
                else:
                    self.next_song()

        if self.is_playing and not self.is_dragging_progress:
            cur_time = self.get_current_time()
            self.progress_var.set(cur_time)
            self.cur_time_label.config(text=self.format_time(cur_time))
            self.sync_lyrics(cur_time)

        self.update_spectrum()

        self.root.after(30, self.check_events_and_lyrics)

    def sync_lyrics(self, current_time):
        """根据当前时间更新当前歌词索引，并触发重绘"""
        if not self.lyrics:
            self.current_lyric_index = 0
            self.update_lyric_display()
            return

        idx = self.current_lyric_index
        for i, (t, _) in enumerate(self.lyrics):
            if current_time >= t:
                idx = i
            else:
                break

        if idx != self.current_lyric_index:
            self.current_lyric_index = idx
            self.update_lyric_display()

    # ---------- 工具函数 ----------
    def get_current_time(self):
        if not self.is_playing:
            return self.paused_time
        return self.start_offset + pygame.mixer.music.get_pos() / 1000.0

    def format_time(self, seconds):
        seconds = max(0, int(seconds))
        return f"{seconds // 60:02d}:{seconds % 60:02d}"

    def on_drag_start(self, event):
        self.is_dragging_progress = True

    def on_drag_end(self, event):
        if self.current_song == -1:
            return
        target = self.progress_scale.get()
        try:
            pygame.mixer.music.play(start=target)
            self.start_offset = target
            self.is_playing = True
            self.play_btn.config(text="⏸")
            self.rotate_cover_animation()
        except:
            pass
        self.is_dragging_progress = False

    def on_progress_click(self, val):
        pass

    def set_volume(self, val):
        self.volume = float(val) / 100
        pygame.mixer.music.set_volume(self.volume)

    def prev_song(self):
        if self.playlist:
            self.current_song = (self.current_song - 1) % len(self.playlist)
            self.play_song()

    def next_song(self):
        if self.playlist:
            self.current_song = (self.current_song + 1) % len(self.playlist)
            self.play_song()

    def toggle_play_mode(self):
        self.play_mode = "single_loop" if self.play_mode == "list_loop" else "list_loop"
        self.mode_btn.config(text="🔂 单曲循环" if self.play_mode == "single_loop" else "🔁 列表循环")

    def import_music(self):
        files = filedialog.askopenfilenames(filetypes=[("Audio", "*.mp3;*.wav;*.ogg")])
        for f in files:
            if f not in self.playlist:
                self.playlist.append(f)
                self.playlist_box.insert(tk.END, os.path.basename(f))

    def clear_playlist(self):
        self.playlist = []
        self.playlist_box.delete(0, tk.END)
        self.stop_rotation()
        pygame.mixer.music.stop()
        self.is_playing = False
        self.draw_default_vinyl()
        self.current_song = -1
        self.lyrics = []
        self.current_lyric_index = 0
        self.update_lyric_display()

    def auto_load_music(self):
        music_dir = resource_path("music")
        if os.path.exists(music_dir):
            for f in os.listdir(music_dir):
                if f.endswith((".mp3", ".wav")):
                    path = os.path.join(music_dir, f)
                    if path not in self.playlist:
                        self.playlist.append(path)
                        self.playlist_box.insert(tk.END, f)

    def load_lyrics(self, path):
        self.lyrics = []
        self.current_lyric_index = 0
        lrc_path = os.path.splitext(path)[0] + ".lrc"
        content = ""
        if os.path.exists(lrc_path):
            try:
                with open(lrc_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except:
                try:
                    with open(lrc_path, 'r', encoding='gbk') as f:
                        content = f.read()
                except:
                    pass

        if content:
            import re
            for line in content.splitlines():
                m = re.findall(r'\[(\d+):(\d+(?:\.\d+)?)\]', line)
                if m:
                    text = re.sub(r'\[.*?\]', '', line).strip()
                    for mm, ss in m:
                        self.lyrics.append((int(mm) * 60 + float(ss), text))
            self.lyrics.sort(key=lambda x: x[0])

        # 加载完立即刷新一次显示
        self.update_lyric_display()

    def load_play_memory(self):
        pass

    def save_play_memory(self):
        pass


if __name__ == "__main__":
    root = tk.Tk()
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass

    app = MusicPlayer(root)
    root.mainloop()