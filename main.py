import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
import sys
import subprocess
import threading
import time
import re


def get_ffmpeg_path():
    if getattr(sys, "frozen", False):
        return os.path.join(sys._MEIPASS, "ffmpeg.exe")
    else:
        return os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "ffmpeg.exe"
        )


FFMPEG = get_ffmpeg_path()

file_list = []
successful_files = []

current_process = None
stop_requested = False
converting = False

current_file_duration = 0
current_file_progress = 0
current_file_start_time = 0

completed_count = 0
total_count = 0
total_start_time = 0


def add_files():
    files = filedialog.askopenfilenames(
        title="Select video files",
        filetypes=[
            (
                "Video files",
                "*.mp4 *.mkv *.avi *.mov *.wmv *.flv *.webm "
                "*.m4v *.ts *.mts *.m2ts *.3gp"
            ),
            ("All files", "*.*")
        ]
    )

    for file in files:
        if file not in file_list:
            file_list.append(file)
            listbox.insert(tk.END, file)

    if files and not output_folder.get():
        output_folder.set(os.path.dirname(files[0]))


def remove_files():
    selected = listbox.curselection()

    for index in reversed(selected):
        listbox.delete(index)
        del file_list[index]


def browse_output_folder():
    folder = filedialog.askdirectory(
        title="Select output folder"
    )

    if folder:
        output_folder.set(folder)


def remove_successful_from_list(file):
    if file in file_list:
        index = file_list.index(file)
        file_list.remove(file)
        listbox.delete(index)


def format_time(seconds):
    if seconds is None or seconds < 0:
        return "--:--:--"

    seconds = int(seconds)

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60

    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def get_video_duration(file):
    command = [
        FFMPEG,
        "-i", file
    ]

    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )

        _, stderr = process.communicate()

        match = re.search(
            r"Duration:\s*(\d+):(\d+):([\d.]+)",
            stderr
        )

        if match:
            hours = int(match.group(1))
            minutes = int(match.group(2))
            seconds = float(match.group(3))

            return hours * 3600 + minutes * 60 + seconds

    except Exception:
        pass

    return 0


def update_progress(current_time):
    global current_file_progress

    if current_file_duration > 0:
        current_file_progress = min(
            current_time / current_file_duration,
            1.0
        )

        current_progress["value"] = current_file_progress * 100

        elapsed = time.time() - current_file_start_time

        if current_time > 0 and elapsed > 0:
            speed = current_time / elapsed
            remaining_video = current_file_duration - current_time

            current_remaining = remaining_video / speed

            current_time_label.config(
                text=f"Current file remaining: ~{format_time(current_remaining)}"
            )

    if total_count > 0:
        completed_progress = completed_count + current_file_progress

        total_progress_value = (
            completed_progress / total_count
        ) * 100

        total_progress["value"] = total_progress_value

        elapsed_total = time.time() - total_start_time

        if completed_progress > 0 and elapsed_total > 0:
            speed = completed_progress / elapsed_total

            remaining_files = total_count - completed_progress

            total_remaining = remaining_files / speed

            total_time_label.config(
                text=f"Total remaining: ~{format_time(total_remaining)}"
            )


def parse_ffmpeg_time(line):
    match = re.search(
        r"time=(\d+):(\d+):([\d.]+)",
        line
    )

    if not match:
        return None

    hours = int(match.group(1))
    minutes = int(match.group(2))
    seconds = float(match.group(3))

    return hours * 3600 + minutes * 60 + seconds


def start_conversion():
    global converting
    global stop_requested
    global total_count
    global completed_count
    global total_start_time

    if converting:
        return

    if not file_list:
        messagebox.showinfo(
            "Video Converter",
            "No files selected."
        )
        return

    dest = output_folder.get().strip()

    if not dest:
        messagebox.showwarning(
            "Video Converter",
            "Please select an output folder."
        )
        return

    if not os.path.isdir(dest):
        try:
            os.makedirs(dest)
        except Exception as error:
            messagebox.showerror(
                "Video Converter",
                f"Could not create output folder:\n{error}"
            )
            return

    if not os.path.isfile(FFMPEG):
        messagebox.showerror(
            "Video Converter",
            "FFmpeg was not found."
        )
        return

    successful_files.clear()

    stop_requested = False
    converting = True

    completed_count = 0
    total_count = len(file_list)
    total_start_time = time.time()

    current_progress["value"] = 0
    total_progress["value"] = 0

    current_time_label.config(
        text="Current file remaining: --:--:--"
    )

    total_time_label.config(
        text="Total remaining: --:--:--"
    )

    start_button.config(state=tk.DISABLED)
    add_button.config(state=tk.DISABLED)
    remove_button.config(state=tk.DISABLED)
    browse_button.config(state=tk.DISABLED)

    files = list(file_list)

    thread = threading.Thread(
        target=conversion_worker,
        args=(files, dest),
        daemon=True
    )

    thread.start()


def conversion_worker(files, dest):
    global current_process
    global converting
    global current_file_duration
    global current_file_progress
    global current_file_start_time
    global completed_count

    for file in files:

        if stop_requested:
            break

        source_folder = os.path.normcase(
            os.path.abspath(os.path.dirname(file))
        )

        destination_folder = os.path.normcase(
            os.path.abspath(dest)
        )

        if source_folder == destination_folder:
            print(f"Skipped: {file}")
            continue

        current_file_duration = get_video_duration(file)
        current_file_progress = 0
        current_file_start_time = time.time()

        root.after(
            0,
            lambda: current_progress.config(value=0)
        )

        root.after(
            0,
            lambda f=file: current_file_label.config(
                text=f"Current file: {os.path.basename(f)}"
            )
        )

        output_file = os.path.join(
            dest,
            os.path.splitext(os.path.basename(file))[0] + ".mp4"
        )

        print(f"Processing: {file}")

        command = [
            FFMPEG,
            "-i", file,
            "-an",
            "-c:v", "copy",
            "-loglevel", "error",
            "-stats",
            "-y",
            output_file
        ]

        try:
            current_process = subprocess.Popen(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                creationflags=subprocess.CREATE_NO_WINDOW
            )

            stderr_lines = []

            while True:

                if stop_requested:
                    try:
                        current_process.terminate()
                    except Exception:
                        pass
                    break

                line = current_process.stderr.readline()

                if not line:
                    if current_process.poll() is not None:
                        break
                    continue

                stderr_lines.append(line)

                video_time = parse_ffmpeg_time(line)

                if video_time is not None:
                    root.after(
                        0,
                        update_progress,
                        video_time
                    )

            return_code = current_process.wait()

            stderr = "".join(stderr_lines)

            current_process = None

        except Exception as error:
            current_process = None

            print(f"Failed: {file}")
            print(error)

            continue

        if stop_requested:
            break

        if return_code == 0 and os.path.isfile(output_file):

            print(f"Completed: {file}")

            successful_files.append(file)

            completed_count += 1

            root.after(
                0,
                lambda f=file: remove_successful_from_list(f)
            )

        else:

            print(f"Failed: {file}")

            if stderr:
                print(stderr.strip())

    current_process = None
    converting = False

    root.after(
        0,
        conversion_finished
    )


def conversion_finished():
    global stop_requested

    current_progress["value"] = 100

    if not stop_requested:
        total_progress["value"] = 100

        current_time_label.config(
            text="Current file remaining: 00:00:00"
        )

        total_time_label.config(
            text="Total remaining: 00:00:00"
        )

    start_button.config(state=tk.NORMAL)
    add_button.config(state=tk.NORMAL)
    remove_button.config(state=tk.NORMAL)
    browse_button.config(state=tk.NORMAL)

    if stop_requested:

        stop_requested = False

        successful_files.clear()

        messagebox.showinfo(
            "Video Converter",
            "Conversion stopped."
        )

        return

    if successful_files:

        delete_files = messagebox.askyesno(
            "Video Converter",
            "Delete successfully processed source files from disk?"
        )

        if delete_files:

            for file in successful_files:

                try:
                    if os.path.isfile(file):
                        os.remove(file)
                        print(f"Deleted: {file}")

                except Exception as error:
                    print(f"Could not delete: {file}")
                    print(error)

        else:
            print("Source files were preserved.")

    successful_files.clear()

    messagebox.showinfo(
        "Video Converter",
        "Conversion completed."
    )


def stop_conversion():
    global stop_requested
    global current_process

    if not converting:
        return

    stop_requested = True

    if current_process is not None:

        try:
            current_process.terminate()
        except Exception:
            pass


# -------------------------------------------------
# GUI
# -------------------------------------------------

root = tk.Tk()

root.title("Video Converter")
root.geometry("800x650")


# Title

title = tk.Label(
    root,
    text="Video files for conversion",
    font=("Arial", 16)
)

title.pack(pady=10)


# File list

listbox = tk.Listbox(
    root,
    selectmode=tk.EXTENDED,
    font=("Arial", 10)
)

listbox.pack(
    fill=tk.BOTH,
    expand=True,
    padx=15,
    pady=10
)


# Add / Remove buttons

button_frame = tk.Frame(root)

button_frame.pack(pady=5)


add_button = tk.Button(
    button_frame,
    text="Add files",
    width=18,
    command=add_files
)

add_button.pack(
    side=tk.LEFT,
    padx=5
)


remove_button = tk.Button(
    button_frame,
    text="Remove from list",
    width=18,
    command=remove_files
)

remove_button.pack(
    side=tk.LEFT,
    padx=5
)


# Start / Stop buttons

control_frame = tk.Frame(root)

control_frame.pack(pady=5)


start_button = tk.Button(
    control_frame,
    text="Start",
    width=18,
    command=start_conversion
)

start_button.pack(
    side=tk.LEFT,
    padx=5
)


stop_button = tk.Button(
    control_frame,
    text="Stop",
    width=18,
    command=stop_conversion
)

stop_button.pack(
    side=tk.LEFT,
    padx=5
)


# Output folder

output_folder = tk.StringVar()

output_frame = tk.Frame(root)

output_frame.pack(
    fill=tk.X,
    padx=15,
    pady=10
)


output_label = tk.Label(
    output_frame,
    text="Output folder:"
)

output_label.pack(
    side=tk.LEFT,
    padx=(0, 8)
)


output_entry = tk.Entry(
    output_frame,
    textvariable=output_folder,
    font=("Arial", 10)
)

output_entry.pack(
    side=tk.LEFT,
    fill=tk.X,
    expand=True
)


browse_button = tk.Button(
    output_frame,
    text="Browse...",
    width=12,
    command=browse_output_folder
)

browse_button.pack(
    side=tk.LEFT,
    padx=(8, 0)
)


# Current file

current_file_label = tk.Label(
    root,
    text="Current file:",
    anchor="w"
)

current_file_label.pack(
    fill=tk.X,
    padx=15,
    pady=(5, 0)
)


current_progress = ttk.Progressbar(
    root,
    orient="horizontal",
    mode="determinate",
    maximum=100
)

current_progress.pack(
    fill=tk.X,
    padx=15,
    pady=5
)


current_time_label = tk.Label(
    root,
    text="Current file remaining: --:--:--",
    anchor="w"
)

current_time_label.pack(
    fill=tk.X,
    padx=15
)


# Total progress

total_progress = ttk.Progressbar(
    root,
    orient="horizontal",
    mode="determinate",
    maximum=100
)

total_progress.pack(
    fill=tk.X,
    padx=15,
    pady=(10, 5)
)


total_time_label = tk.Label(
    root,
    text="Total remaining: --:--:--",
    anchor="w"
)

total_time_label.pack(
    fill=tk.X,
    padx=15,
    pady=(0, 10)
)


root.mainloop()