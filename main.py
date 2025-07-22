import os
import sys
import threading
import re
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.label import Label
from kivy.uix.image import AsyncImage
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.uix.progressbar import ProgressBar
from kivy.uix.checkbox import CheckBox
from kivy.core.window import Window
from kivy.clock import mainthread
import yt_dlp
import requests

# --- Kivy App Styling and Configuration ---
Window.clearcolor = (0.109, 0.129, 0.156, 1) # #1C2128

class DownloaderLayout(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.padding = [20, 20, 20, 20]
        self.spacing = 20
        self.video_info = None
        self.format_data = {}

        # --- URL Input ---
        url_layout = BoxLayout(size_hint_y=None, height=50, spacing=10)
        self.url_input = TextInput(hint_text='Enter YouTube Video URL', multiline=False, size_hint_x=0.8)
        self.fetch_button = Button(text='Fetch', size_hint_x=0.2, on_press=self.fetch_info_thread)
        url_layout.add_widget(self.url_input)
        url_layout.add_widget(self.fetch_button)
        self.add_widget(url_layout)

        # --- Main Content Area ---
        content_layout = BoxLayout(spacing=20)
        
        # --- Thumbnail ---
        self.thumbnail = AsyncImage(source='', size_hint_x=0.4)
        content_layout.add_widget(self.thumbnail)

        # --- Info & Options ---
        info_options_layout = BoxLayout(orientation='vertical', spacing=10, size_hint_x=0.6)
        self.title_label = Label(text='Video Title', size_hint_y=None, height=40, bold=True)
        self.author_label = Label(text='Author', size_hint_y=None, height=30, italic=True)
        self.quality_spinner = Spinner(text='Select Quality', values=(), disabled=True, size_hint_y=None, height=44)
        info_options_layout.add_widget(self.title_label)
        info_options_layout.add_widget(self.author_label)
        info_options_layout.add_widget(self.quality_spinner)
        content_layout.add_widget(info_options_layout)
        
        self.add_widget(content_layout)

        # --- Trimming Section ---
        trim_layout = GridLayout(cols=2, size_hint_y=None, height=80, spacing=10)
        self.trim_checkbox = CheckBox(size_hint_x=0.1)
        self.trim_checkbox.bind(active=self.toggle_trim_fields)
        trim_layout.add_widget(Label(text='Download Clip:', size_hint_x=0.4))
        trim_layout.add_widget(self.trim_checkbox)
        self.start_time_input = TextInput(hint_text='Start (HH:MM:SS)', disabled=True)
        self.end_time_input = TextInput(hint_text='End (HH:MM:SS)', disabled=True)
        trim_layout.add_widget(self.start_time_input)
        trim_layout.add_widget(self.end_time_input)
        self.add_widget(trim_layout)

        # --- Download Button & Progress ---
        self.download_button = Button(text='Download', size_hint_y=None, height=50, on_press=self.download_thread, disabled=True)
        self.status_label = Label(text='Status: Ready', size_hint_y=None, height=30)
        self.progress_bar = ProgressBar(max=1, size_hint_y=None, height=10)
        self.add_widget(self.download_button)
        self.add_widget(self.status_label)
        self.add_widget(self.progress_bar)

    def fetch_info_thread(self, instance):
        url = self.url_input.text
        if not url:
            self.status_label.text = "Please enter a URL."
            return
        self.fetch_button.disabled = True
        self.status_label.text = "Fetching..."
        threading.Thread(target=self.fetch_info, args=(url,)).start()

    def fetch_info(self, url):
        try:
            ydl_opts = {'quiet': True, 'no_warnings': True, 'skip_download': True}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                self.video_info = ydl.extract_info(url, download=False)
            self.update_ui_on_main_thread()
        except Exception as e:
            self.status_label.text = f"Error: {e}"
        finally:
            self.fetch_button.disabled = False

    @mainthread
    def update_ui_on_main_thread(self):
        if not self.video_info: return
        self.title_label.text = self.video_info.get('title', 'N/A')
        self.author_label.text = f"by {self.video_info.get('uploader', 'N/A')}"
        self.thumbnail.source = self.video_info.get('thumbnail', '')
        
        self.format_data.clear()
        quality_tiers = [4320, 2160, 1440, 1080, 720, 480, 360, 240, 144]
        all_video_formats = [f for f in self.video_info.get('formats', []) if f.get('vcodec') != 'none' and f.get('height')]
        
        for height in quality_tiers:
            formats_for_tier = [f for f in all_video_formats if f.get('height') == height]
            if not formats_for_tier: continue
            best_format = max(formats_for_tier, key=lambda f: (f.get('fps', 0), f.get('tbr', 0)))
            desc = f"{height}p{best_format.get('fps', '') if best_format.get('fps', 0) > 30 else ''}"
            if desc not in self.format_data:
                self.format_data[desc] = {'format_id': best_format.get('format_id'), 'type': 'video'}
        
        if any(f.get('acodec') != 'none' for f in self.video_info.get('formats', [])):
            self.format_data["Audio Only MP3"] = {'type': 'audio'}
            
        self.quality_spinner.values = list(self.format_data.keys())
        self.quality_spinner.text = self.quality_spinner.values[0] if self.quality_spinner.values else 'No formats'
        self.quality_spinner.disabled = False
        self.download_button.disabled = False
        self.status_label.text = "Ready to download."

    def toggle_trim_fields(self, checkbox, value):
        self.start_time_input.disabled = not value
        self.end_time_input.disabled = not value

    def download_thread(self, instance):
        try:
            from android.storage import primary_external_storage_path
            self.save_path = os.path.join(primary_external_storage_path(), 'Download')
        except ImportError:
            self.save_path = os.path.join(os.path.expanduser('~'), 'Downloads')
        
        if not os.path.exists(self.save_path):
            os.makedirs(self.save_path)
            
        self.download_button.disabled = True
        threading.Thread(target=self.download_video).start()

    def download_video(self):
        try:
            selected_quality = self.quality_spinner.text
            selected_format = self.format_data[selected_quality]
            format_type = selected_format['type']
            
            output_template = os.path.join(self.save_path, f"{yt_dlp.utils.sanitize_filename(self.video_info['title'])}.%(ext)s")
            
            ydl_opts = {'outtmpl': output_template, 'progress_hooks': [self.progress_hook], 'noprogress': True}
            
            if self.trim_checkbox.active:
                start, end = self.start_time_input.text, self.end_time_input.text
                ydl_opts['postprocessor_args'] = {'ffmpeg': ['-ss', start, '-to', end, '-c', 'copy']}
                ydl_opts['format'] = 'bestvideo+bestaudio/best'
                ydl_opts['outtmpl'] = os.path.join(self.save_path, f"{yt_dlp.utils.sanitize_filename(self.video_info['title'])}_clip.%(ext)s")
            else:
                ydl_opts['merge_output_format'] = 'mp4'
                if format_type == 'audio':
                    ydl_opts['format'] = 'bestaudio/best'
                    ydl_opts['postprocessors'] = [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}]
                else:
                    ydl_opts['format'] = f"{selected_format['format_id']}+bestaudio/best"

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([self.video_info['webpage_url']])
            
            self.on_download_complete()

        except Exception as e:
            self.status_label.text = f"Download Error: {e}"
        finally:
            self.download_button.disabled = False
            
    @mainthread
    def progress_hook(self, d):
        if d['status'] == 'downloading':
            total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate')
            if total_bytes:
                progress = d.get('downloaded_bytes', 0) / total_bytes
                self.progress_bar.value = progress
                self.status_label.text = f"Downloading... {int(progress*100)}%"
        elif d['status'] == 'finished':
            self.status_label.text = "Finalizing..."
            
    @mainthread
    def on_download_complete(self):
        self.status_label.text = f"Download Complete! Saved in Downloads folder."
        self.progress_bar.value = 1

class DownloaderApp(App):
    def build(self):
        return DownloaderLayout()

if __name__ == '__main__':
    DownloaderApp().run()
