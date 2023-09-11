import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from moviepy.editor import VideoFileClip
import threading
import logging
from ttkthemes import ThemedStyle
from PIL import Image, ImageTk
import imageio

# Define the application version
APP_VERSION = "1.0.0b"

# Added a configuration file to store and retrieve last input and export directories
CONFIG_FILE = "config.txt"

class VideoToImageConverter:
    def __init__(self, root):
        self.root = root
        self.root.title(f"Slice v{APP_VERSION}")

        # Set the custom application icon
        icon_path = "SliceSmall.ico"  # Change to the path of your custom icon
        if os.path.exists(icon_path):
            self.root.iconbitmap(icon_path)

        self.style = ThemedStyle(self.root)
        self.style.set_theme("arc")  # Change the theme to your preference

        self.create_gui()

        # Initialize last input and export directories
        self.last_input_dir = ""
        self.last_export_dir = ""

        # Load last input and export directories from the configuration file
        self.load_config()

        self.video_file = None
        self.export_dir = None
        self.export_format = "jpeg"
        self.export_quality_var = tk.DoubleVar(value=1.0)  # Default export quality
        self.frame_skip_var = tk.IntVar(value=1)  # Default frame skipping
        self.is_converting = False
        self.cancel_conversion_flag = False
        self.log_filename = "conversion_log.txt"
        self.conversion_thread = None

        logging.basicConfig(filename=self.log_filename, level=logging.INFO,
                            format='%(asctime)s [%(levelname)s]: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

    def create_gui(self):
        self.frame = ttk.Frame(self.root, padding=20)
        self.frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        self.create_widgets()

    def create_widgets(self):
        ttk.Label(self.frame, text="Video file:").grid(row=0, column=0, sticky="w")
        self.video_file_entry = ttk.Entry(self.frame, state="readonly")
        self.video_file_entry.grid(row=0, column=1, padx=5, pady=5, sticky="we")
        ttk.Button(self.frame, text="Browse", command=self.browse_video).grid(row=0, column=2, padx=5, pady=5)

        ttk.Label(self.frame, text="Export directory:").grid(row=1, column=0, sticky="w")
        self.export_dir_entry = ttk.Entry(self.frame, state="readonly")
        self.export_dir_entry.grid(row=1, column=1, padx=5, pady=5, sticky="we")
        ttk.Button(self.frame, text="Browse", command=self.browse_export_directory).grid(row=1, column=2, padx=5, pady=5)

        ttk.Label(self.frame, text="Format:").grid(row=2, column=0, sticky="w")
        self.export_format_var = tk.StringVar(value="JPEG")
        self.export_format_menu = ttk.Combobox(self.frame, textvariable=self.export_format_var, values=["PNG", "JPEG", "GIF"])
        self.export_format_menu.grid(row=2, column=1, padx=5, pady=5, sticky="we")

        ttk.Label(self.frame, text="Export Quality:").grid(row=3, column=0, sticky="w")
        self.export_quality_var = tk.DoubleVar(value=1.0)  # Default export quality
        self.export_quality_slider = ttk.Scale(self.frame, from_=0.1, to=1.0, orient="horizontal", variable=self.export_quality_var)
        self.export_quality_slider.grid(row=3, column=1, padx=5, pady=5, sticky="we")

        ttk.Label(self.frame, text="Frame Skipping:").grid(row=4, column=0, sticky="w")
        self.frame_skip_var = tk.IntVar(value=1)  # Default frame skipping
        self.frame_skip_entry = ttk.Entry(self.frame, textvariable=self.frame_skip_var)
        self.frame_skip_entry.grid(row=4, column=1, padx=5, pady=5, sticky="we")

        ttk.Button(self.frame, text="Slice!", command=self.convert_video).grid(row=5, column=0, columnspan=3, pady=10)
        ttk.Button(self.frame, text="Cancel", state="enabled", command=self.cancel_conversion).grid(row=6, column=0, columnspan=3, pady=10)

        self.progress_label = ttk.Label(self.frame, text="", wraplength=400)
        self.progress_label.grid(row=7, column=0, columnspan=3, pady=10)

        self.progress_bar = ttk.Progressbar(self.frame, length=300, mode="determinate")
        self.progress_bar.grid(row=8, column=0, columnspan=3, pady=10)

        self.current_frame_image_label = ttk.Label(self.frame)
        self.current_frame_image_label.grid(row=9, column=0, columnspan=3, pady=10)

    def browse_video(self):
        self.video_file = filedialog.askopenfilename(filetypes=[("Video Files", "*.mp4 *.avi *.mkv *.mov *.wmv *.flv *.mkv")])
        if self.video_file:
            self.video_file_entry.configure(state="normal")
            self.video_file_entry.delete(0, tk.END)
            self.video_file_entry.insert(0, self.video_file)
            self.video_file_entry.configure(state="readonly")

    def browse_export_directory(self):
        self.export_dir = filedialog.askdirectory()
        if self.export_dir:
            self.export_dir_entry.configure(state="normal")
            self.export_dir_entry.delete(0, tk.END)
            self.export_dir_entry.insert(0, self.export_dir)
            self.export_dir_entry.configure(state="readonly")

    def convert_video(self):
        if not self.video_file:
            messagebox.showerror("Error", "Can't Slice air..")
            return

        if not os.path.isfile(self.video_file):
            messagebox.showerror("Error", "Unsliceable File")
            return

        if not self.export_dir:
            messagebox.showerror("Error", "Please select an export directory.")
            return

        self.export_format = self.export_format_var.get()

        self.video_file_entry.configure(state="readonly")
        self.export_dir_entry.configure(state="readonly")
        self.export_format_menu.configure(state="disabled")
        self.export_quality_slider.configure(state="disabled")
        self.frame_skip_entry.configure(state="readonly")
        self.is_converting = True
        self.cancel_conversion_flag = False
        self.conversion_thread = threading.Thread(target=self._convert_video)
        self.conversion_thread.start()

    def update_current_frame_image(self, frame_image):
        self.current_frame_image_label.configure(image=frame_image)
        self.current_frame_image_label.image = frame_image

    def _convert_video(self):
        try:
            video_path = self.video_file
            clip = VideoFileClip(video_path)
            frame_rate = clip.fps
            total_frames = int(clip.duration * frame_rate)
            frame_skip = self.frame_skip_var.get()

            export_folder = os.path.join(self.export_dir, "")
            os.makedirs(export_folder, exist_ok=True)

            frames = []

            for i, frame in enumerate(clip.iter_frames(), start=1):
                if self.cancel_conversion_flag:
                    break

                if i % frame_skip != 0:
                    continue

                frame_filename = os.path.join(export_folder, f"frame_{i:04d}.{self.export_format}")
                frame_image = Image.fromarray(frame)
                frame_image.save(frame_filename, quality=int(self.export_quality_var.get() * 95))  # 95 is the maximum JPEG quality

                progress_percent = int((i / total_frames) * 100)
                progress_text = f"Slicing... {progress_percent}%"
                if not (self.is_converting and not self.cancel_conversion_flag):
                    progress_text = "Slicing cancelled."

                self.progress_bar["value"] = progress_percent
                self.progress_label["text"] = progress_text

                if i % 1 == 0:
                    self.root.update_idletasks()

                current_frame_image = Image.fromarray(clip.get_frame(i / frame_rate))
                current_frame_image.thumbnail((200, 200))
                current_frame_image_tk = ImageTk.PhotoImage(current_frame_image)

                self.root.after(0, lambda: self.update_current_frame_image(current_frame_image_tk))

                frames.append(frame_filename)

            if self.export_format == "GIF":
                gif_path = os.path.join(self.export_dir, "output.gif")
                imageio.mimsave(gif_path, [imageio.imread(frame) for frame in frames], duration=1 / frame_rate)

                # Delete individual frame files after creating the GIF
                for frame_file in frames:
                    os.remove(frame_file)

            def reenable_buttons():
                self.is_converting = False
                if not (self.is_converting and not self.cancel_conversion_flag):
                    self.progress_bar["value"] = 0
                    self.progress_label["text"] = ""

                self.video_file_entry.configure(state="normal")
                self.export_dir_entry.configure(state="normal")
                self.export_format_menu.configure(state="readonly")
                self.export_quality_slider.configure(state="normal")
                self.frame_skip_entry.configure(state="normal")
                ttk.Button(self.frame, text="Slice!", command=self.convert_video).grid(row=5, column=0, columnspan=3, pady=10)
                ttk.Button(self.frame, text="Cancel", state="enabled", command=self.cancel_conversion).grid(row=6, column=0, columnspan=3, pady=10)

            self.root.after(0, reenable_buttons)

        except Exception as e:
            logging.error(f"Error during conversion: {e}")
            messagebox.showerror("Error", f"An error occurred during conversion: {e}")

    def cancel_conversion(self):
        self.cancel_conversion_flag = True

    # Save the last input and export directories to a configuration file
    def save_config(self):
        with open(CONFIG_FILE, "w") as config_file:
            config_file.write(f"last_input_dir={self.last_input_dir}\n")
            config_file.write(f"last_export_dir={self.last_export_dir}\n")

    # Load the last input and export directories from the configuration file
    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as config_file:
                for line in config_file:
                    if line.startswith("last_input_dir="):
                        self.last_input_dir = line.split("=")[1].strip()
                    elif line.startswith("last_export_dir="):
                        self.last_export_dir = line.split("=")[1].strip()

    # Handle window closing event
    def on_closing(self):
        # Save the last input and export directories when the application closes
        self.save_config()
        self.root.destroy()
        

if __name__ == "__main__":
    root = tk.Tk()
    root.resizable(False, False)
    app = VideoToImageConverter(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)  # Bind to the window close event
    root.mainloop()