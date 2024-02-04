#!/usr/bin/env python3

import tkinter as tk
from tkinter import filedialog
from tkinter import simpledialog
from tkinter import messagebox
import vlc
import time, sys

vlc_instance = vlc.Instance('--verbose=0')
player = vlc_instance.media_player_new()

audio_started = False

script_lines, line_index, current_subtitle = [], 0, {}

subtitles = []

MediaTotalLength = 0

stdout_buf = []

class TextRedirector(object):
    def __init__(self, buf, origin):
        self.buffer = buf
        self.origin = origin

    def write(self, string):
        self.origin.write(string)
        self.buffer.append(string)

    def flush(self):
        self.origin.flush()

def toggle_audio(event = None):
  global audio_started
  if not audio_started:
    print("Audio Play.")
    player.play()
    audio_started = True
  elif player.is_playing():
    print("Audio Pause.")
    player.pause()
  else:
    print("Audio Play.")
    player.play()

def rewind_audio(event = None):
  new_time = max(player.get_time() - 5000, 0)
  player.set_time(new_time)

def fastforward_audio(event = None):
  new_time = player.get_time() + 5000
  player.set_time(new_time)

def mark_start():
  timestamp = player.get_time() / 1000.0
  current_subtitle["start"] = timestamp
  if line_index > len(script_lines) or not len(script_lines):
    print("Please load first..")
    return
  current_subtitle["content"] = current_subtitle.get("content","") + script_lines[line_index]
  update_display()
  print(f"\n{timestamp} --> ", end="")

def mark_end():
  if current_subtitle.get("content") == None:
    print("Please load first..")
    return
  timestamp = player.get_time() / 1000.0
  current_subtitle["end"] = timestamp
  subtitles.append(current_subtitle.copy())
  print(f"{current_subtitle["end"]}\n{current_subtitle["content"]}")
  current_subtitle["content"] = current_subtitle["content"] + "\n"
  current_subtitle["start"] = None
  load_next_line()
  update_display()

def on_next_press(event = None):
  if current_subtitle.get("start") is None:
    mark_start()
  else:
    mark_end()

def on_autonext_press(event = None):
  if current_subtitle.get("start") is None:
    mark_start()
  else:
    mark_end()
    mark_start()

def on_skip_press(event = None):
  if line_index < 1:
    return
  if current_subtitle["start"] == None:
    current_subtitle["content"] = ""
    current_subtitle["start"] = None
    load_next_line()
    update_display()
    return  
  timestamp = player.get_time() / 1000.0
  current_subtitle["end"] = timestamp
  subtitles.append(current_subtitle.copy())
  print(f"{current_subtitle["end"]}\n{current_subtitle["content"]}")
  current_subtitle["content"] = ""
  current_subtitle["start"] = None
  load_next_line()
  update_display()

def on_back(event = None):
  global subtitles
  if len(subtitles) == 0:
    messagebox.showerror("Error", f"No subtitle to remove.")
    return
  if current_subtitle["start"]:
    messagebox.showerror("Error", f"\nDeleting \"{current_subtitle.get("content")}\" \n You need to go back and mark start again.")
    if len(subtitles) > 2:
      current_subtitle["content"] = subtitles[-2]["content"] + "\n"
    current_subtitle["content"] = ""
    current_subtitle["start"] = None
  else:
    messagebox.showerror("Error", f"\nDeleting \"{subtitles[-1].get("content")}\" \n You need to go back and mark start again.")
    del(subtitles[-1])
  print(f"\nCurrent: #{len(subtitles)+1} {current_subtitle}")
  load_next_line(diff = -1)

def update_timestamp():
  current_pos = max(player.get_time() / 1000, 0)
  timestamp_label.config(text=f"{current_pos:.3f}s / {MediaTotalLength}s")
  root.after(200, update_timestamp)

def multiline(content):
  return content.strip()
  if content:
    return "- " + content.strip().replace("\n", "\n- ")

def to_time(seconds):
  minutes = int(seconds // 60)
  second = seconds % 60
  hours = int(minutes // 60)
  minute = minutes % 60
  return f"{hours}:{minute:02}:{second:06.3f}"

def update_display():
    script_listbox.delete(0, tk.END)
    subtitle_text.config(state=tk.NORMAL)
    subtitle_text.delete("1.0", tk.END)

    for n, line in enumerate(script_lines):
        display_line = " " + line
        script_listbox.insert(tk.END, display_line)

        if n < len(subtitles):
            lstart = subtitles[n]["start"]
            lend = subtitles[n]["end"]
            subtitle_display = f"{n+1}\n{to_time(lstart)} --> {to_time(lend)}\n{multiline(subtitles[n]['content']).replace("\n", "↵\n")} \n\n"
            subtitle_text.insert(tk.END, subtitle_display)
        
        elif n == len(subtitles) :
          lstart = current_subtitle.get("start", "")

          if lstart:
            subtitle_display = f"{n+1}\n{to_time(lstart)} -> \n{multiline(current_subtitle.get('content'))} \n\n"
            subtitle_text.insert(tk.END, subtitle_display)
        
        if n == line_index:
            script_listbox.itemconfig(n, {'bg': 'lightgrey'})

        if player.is_playing():
          script_listbox.see(min(line_index + 5, len(script_lines)))
          subtitle_text.see(tk.END)

    subtitle_text.config(state=tk.DISABLED)

def load_next_line(diff = 1):
  global line_index
  if line_index < len(script_lines):
    line_index += diff
    update_display()

def load_file(label):
    file_path = filedialog.askopenfilename()
    if file_path:
        label.config(text=file_path.split("/")[-1])
        return file_path
    return None

def choose_audio():
    global player, MediaTotalLength
    file_path = load_file(audio_label)
    if file_path:
        player.set_media(media := vlc.Media(file_path))
        media.parse_with_options(vlc.MediaParseFlag.fetch_network, 0)
        while not media.is_parsed():
          time.sleep(0.1)
        MediaTotalLength = (media.get_duration() // 1000)

def choose_script():
    global script_lines, line_index, current_subtitle
    file_path = load_file(script_label)
    if file_path:
        script_lines = open(file_path, 'r').read().splitlines()
        subtitles.clear()
        line_index, current_subtitle = 0, {}
        update_display()

def save_subtitles():
    vtt_path = filedialog.asksaveasfilename(defaultextension=".vtt", filetypes=[("VTT files", "*.vtt"), ("All files", "*.*")])
    if vtt_path:
        with open(vtt_path, 'w') as f:
            f.write('WEBVTT\n\n')
            for subtitle in subtitles:
                f.write(f"{to_time(subtitle['start'])} --> {to_time(subtitle['end'])}\n")
                f.write(multiline(subtitle['content']))
                f.write("\n\n")

    print(f"Done saving {len(subtitles)} subtitles")

def save_prog():
  import json
  fpath = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json"), ("All files", "*.*")])
  if fpath:
      with open(fpath, 'w') as f:
        f.write(json.dumps({"subtitles": subtitles, "script_lines": script_lines,"line_index": line_index,"current_subtitle": current_subtitle, "play": player.get_time()}, indent=2))
     
def load_prog():
  global subtitles, player, script_lines, line_index, current_subtitle
  import json
  fpath = filedialog.askopenfilename()    
  if fpath:
    with open(fpath, 'r') as f:
      back = json.loads(f.read())
    subtitles = back["subtitles"]
    script_lines = back["script_lines"]
    line_index = back["line_index"]
    current_subtitle = back["current_subtitle"]
    curpos = int(back["play"])
    messagebox.showinfo("Loaded", f"Loaded {len(subtitles)} subtitles.")
    player.play()
    player.set_time(curpos)
    time.sleep(0.3)
    player.pause()
    update_display()

def skip_to_time():
    try:
        time_seconds = float(skip_time_entry.get())
        player.set_time(int(time_seconds * 1000))
        update_timestamp()
    except ValueError:
        messagebox.showerror("Error", "Please enter a valid number of seconds.")

    except Exception as e:
        print(e)

def on_list_right_click(event):
    try:
        context_menu.tk_popup(event.x_root, event.y_root)
    finally:
        context_menu.grab_release()

def on_left_click(event):
  context_menu.unpost()

def on_list_left_click(event):
  if player.is_playing():
    player.pause()
  on_left_click(event)

def merge_selected(event = None):
    selected_indices = script_listbox.curselection()
    if not selected_indices:
        messagebox.showinfo("No selection", "Please select items to merge.")
        return
    
    if len(selected_indices) == 1:
        messagebox.showinfo("Not enough selection", "Please select multiple item to merge.")
        return

    selected_lines = [script_lines[i] for i in selected_indices]
    print("Merge", selected_lines)
    merged_line = ' '.join(selected_lines)
    
    script_lines[selected_indices[0]] = merged_line
    for i in selected_indices[1:]:
      del(script_lines[i])

    update_display()

def edit_selected(event = None, selected_idx = None):
    if not selected_idx:
      selected_indices = script_listbox.curselection()
      if not selected_indices:
          messagebox.showinfo("No selection", "Please select item to split.")
          return
      
      if len(selected_indices) > 1:
          messagebox.showinfo("Too many selection", "Please select one item.")
          return
        
      selected_idx = selected_indices[0]

    selected_line = script_lines[selected_idx]
    
    print("Edit",  selected_line)

    top = tk.Toplevel(root)
    top.title("Edit and Split Line")
    text = tk.Text(top, height=5, width=50)
    text.pack(padx=10, pady=10)
    text.insert(tk.END, selected_line)
    
    editted_lines = []
    def edit_and_close(event = None):
        global splitted_lines
        edited_line = text.get('1.0', tk.END).strip()
        editted_lines = edited_line.split('\n')
        top.destroy()

        del(script_lines[selected_idx])
        print(editted_lines)
        for i in reversed(editted_lines):
          script_lines.insert(selected_idx, i)
        
        update_display()

    text.bind("<Control-Return>", edit_and_close)
    text.bind("<FocusOut>", edit_and_close)
    text.bind("<Escape>", lambda e: top.destroy()) 

    button = tk.Button(top, text="Done", command=lambda: edit_and_close())
    button.pack(pady=5)


def remove_selected(event = None):
    selected_indices = script_listbox.curselection()
    if not selected_indices:
        messagebox.showinfo("No selection", "Please select items to remove.")
        return
    print("Delete", selected_lines)
    for i in selected_indices[1:]:
      del(script_lines[i])
    update_display()

def on_list_double_click(event):
  index = script_listbox.nearest(event.y)
  if not script_listbox.selection_includes(index):
      return

  text = script_listbox.get(index)
  
  entry = tk.Entry(root, bd=1, highlightthickness=1, )
  entry.insert(0, text)
  entry.select_range(0, tk.END)
  
  def save_edit(event=None):
      script_listbox.delete(index)
      script_listbox.insert(index, entry.get())
      entry.destroy()
  
  bbox = script_listbox.bbox(index)
  entry.place(x=bbox[0], y=bbox[1], width=bbox[2], height=bbox[3])
  
  entry.bind("<Return>", save_edit)
  entry.bind("<FocusOut>", save_edit)
  entry.bind("<Escape>", lambda e: entry.destroy())
  
  entry.focus_set()

def on_list_double_click(event):
  index = script_listbox.nearest(event.y)
  if not script_listbox.selection_includes(index):
      return
  edit_selected(selected_idx = index)

def update_stdout():
    stdoutext.config(state=tk.NORMAL)
    stdoutext.delete("1.0", tk.END)
    stdoutext.insert(tk.END, "".join(stdout_buf))
    stdoutext.config(state=tk.DISABLED)
    debugwindow.after(100, update_stdout)

def show_console_output_screen():
  global stdoutext, debugwindow
  debugwindow = tk.Toplevel(root)
  debugwindow.geometry("700x400")
  stdoutext = tk.Text(debugwindow, state=tk.DISABLED)
  stdoutext.pack(padx=15, pady=15, fill=tk.BOTH)
  update_stdout()


root = tk.Tk()
root.title("Subtitle Timing Editor")
root.geometry('1000x800')
root.resizable(False, False)

content_frame = tk.Frame(root)
content_frame.pack(side=tk.LEFT, padx=5, pady=5)

subtitle_text = tk.Text(content_frame, width=100, height=20, borderwidth=1, relief="solid", state=tk.DISABLED)
subtitle_text.pack(side=tk.BOTTOM, fill='both', expand=True)

script_listbox = tk.Listbox(content_frame, width=100, height=20, borderwidth=1, relief="solid", selectmode=tk.EXTENDED)
script_listbox.pack(side=tk.BOTTOM, fill='both', expand=True)

context_menu = tk.Menu(root, tearoff=0)
context_menu.add_command(label="Merge (M)", command=merge_selected)
context_menu.add_command(label="Edit (E)", command=edit_selected)
context_menu.add_command(label="Remove (R)", command=remove_selected)
context_menu.add_separator()
context_menu.add_command(label="Exit", command=root.quit)

script_listbox.bind("M", merge_selected)
script_listbox.bind("E", edit_selected)
script_listbox.bind("R", remove_selected)

script_listbox.bind("<Button-3>", on_list_right_click)
script_listbox.bind("<Double-1>", on_list_double_click)


button_frame = tk.Frame(root)
button_frame.pack(side=tk.BOTTOM, pady=(0,15))

rewind_button = tk.Button(button_frame, text='-5s', width=2, command=rewind_audio)
rewind_button.pack(side=tk.LEFT, padx=5, pady=5)

play_button = tk.Button(button_frame, text='P/P',  width=2, command=toggle_audio)
play_button.pack(side=tk.LEFT, padx=5, pady=5)

fastforward_button = tk.Button(button_frame, text='+5s', width=2, command=fastforward_audio)
fastforward_button.pack(side=tk.LEFT, padx=5, pady=5)

timestamp_label = tk.Label(root, text="0.00s / 0.00s")
timestamp_label.pack(side=tk.BOTTOM, pady=5)



btn_frame = tk.Frame(root, borderwidth=0, relief="solid")
btn_frame.pack(side=tk.BOTTOM, padx=5)

next_button = tk.Button(btn_frame, text='Mark', width=2, command=on_next_press)
next_button.pack(side=tk.LEFT, padx=5, pady=5)

autonext_button = tk.Button(btn_frame, text='Next', width=2, command=on_autonext_press)
autonext_button.pack(side=tk.LEFT, padx=5, pady=5)

skip_button = tk.Button(btn_frame, text='Done', width=2, command=on_skip_press)
skip_button.pack(side=tk.LEFT, padx=5, pady=5)



file_frame = tk.Frame(root, padx=10, pady=5, borderwidth=0, relief="solid")
file_frame.pack(side=tk.TOP, padx=(0,5), pady=5, fill=tk.BOTH)

audio_button = tk.Button(file_frame, text='Choose Audio', command=choose_audio)
audio_button.pack(side=tk.TOP, fill=tk.X)

audio_label = tk.Label(file_frame, text='No audio file selected')
audio_label.pack(side=tk.TOP, pady=5)

script_button = tk.Button(file_frame, text='Choose Script',  command=choose_script)
script_button.pack(side=tk.TOP, fill=tk.X)

script_label = tk.Label(file_frame, text='No script file selected')
script_label.pack(side=tk.TOP, pady=5)

saveprog_button = tk.Button(file_frame, text='Save progress', command=save_prog)
saveprog_button.pack(side=tk.TOP, pady=5, fill=tk.X)

loadprog_button = tk.Button(file_frame, text='Load progress',  command=load_prog)
loadprog_button.pack(side=tk.TOP, fill=tk.X)

save_button = tk.Button(file_frame, text='Save Subtitles', command=save_subtitles)
save_button.pack(side=tk.TOP, pady=10, fill=tk.X)

skip_time_frame = tk.Frame(file_frame)
skip_time_frame.pack(side=tk.TOP, fill=tk.X)

skip_time_button = tk.Button(skip_time_frame, text='Skip To', command=skip_to_time)
skip_time_button.pack(side=tk.LEFT)

skip_time_entry = tk.Entry(skip_time_frame)
skip_time_entry.pack(side=tk.LEFT, padx=5, fill=tk.X)
skip_time_entry.insert(0, "0")

info_frame = tk.Frame(root, borderwidth=0, relief="solid", width=10, height=10, padx=10)
info_frame.pack(side=tk.TOP, expand=True, anchor="nw", padx=(5,15), pady=(10,15))

info_label = tk.Label(info_frame, text='VTT Maker by @morgan9e\n\nUsage:\n Mark <\'>\n Next <;>\n Done <Return>\n'
  '\n- Creates \"stacked\" subtitles easily.\n- It stacks subtitle from previous scene.\n- You can save and load progress.'
  '\n- Load audio before loading progress.\n- You can Edit, Merge, Delete script with left click.'
  , font=("monospace", 8), wraplength=140, justify=tk.LEFT)

info_label.pack(side=tk.TOP, anchor="nw")

debug_button = tk.Button(root, text='Show stdout', command=show_console_output_screen, borderwidth=0)
debug_button.pack(side=tk.TOP, pady=(0,5))

def presskey(btn, func):
  def wrapper(event):
    btn.config(relief=tk.SUNKEN)
    root.after(100, lambda: btn.config(relief=tk.RAISED))
    return func()
  return wrapper

root.bind('\'', presskey(next_button,on_next_press))
root.bind(';', presskey(autonext_button,on_autonext_press))
root.bind('<Return>', presskey(skip_button,on_skip_press))
root.bind('<Control-z>', on_back)
root.bind('<space>', presskey(play_button,toggle_audio))

root.bind('<Left>', presskey(rewind_button,rewind_audio))
root.bind('<Right>', presskey(fastforward_button,fastforward_audio))

root.bind("<Button-1>", on_left_click)

def on_closing():
    if messagebox.askokcancel("Quit", "Do you want to quit?"):
        player.stop()
        root.destroy()

root.protocol("WM_DELETE_WINDOW", on_closing)

update_timestamp()
update_display()

stdout = sys.stdout  
stderr = sys.stderr  
sys.stdout = TextRedirector(stdout_buf, stdout)
sys.stderr = TextRedirector(stdout_buf, stderr)

root.mainloop()

sys.stdout = stdout
sys.stderr = stderr