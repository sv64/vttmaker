#!/usr/bin/env python3

import re, json
import os
from datetime import timedelta

def from_vtt(vtt_string):
  VTT_TIMECODE_PATTERN = r"((?:\d{2}:)?\d{2}:\d{2}\.\d{3}) --> ((?:\d{2}:)?\d{2}:\d{2}\.\d{3})"
  VTT_LINE_NUMBER_PATTERN = r"^\d+$"
  parts = re.split(r'\n\n+', vtt_string.strip())
  if parts[0].startswith('WEBVTT'):
    parts.pop(0)

  subtitles = []
  for part in parts:
    lines = part.split('\n')
    match = re.match(VTT_TIMECODE_PATTERN, lines[0])
    if not match:
      if re.match(VTT_LINE_NUMBER_PATTERN, lines[0]):
        lines.pop(0)
      match = re.match(VTT_TIMECODE_PATTERN, lines[0])
    if not match:
      continue

    start, end = match.groups()
    content = '\n'.join(lines[1:])
    subtitles.append({
      'start': start,
      'end': end,
      'content': content
    })

  return subtitles

def to_vtt(subtitles):
    vtt_content = "WEBVTT\n\n\n"
    for idx, subtitle in enumerate(subtitles):
        content = subtitle['content']
        if not subtitle.get("split", False):
          start = subtitle['start']
          end = subtitle['end']
          vtt_content += f"{start} --> {end}\n{content}\n\n\n"
        else:
          vtt_content += f"NOTE {content}\n\n\n"

    return vtt_content.strip()

def to_stacked_vtt(subtitles):
  vtt_content = "WEBVTT\n\n\n"
  buffer = ""
  for subtitle in subtitles:
    if subtitle.get("split", False):
      buffer = ""
      continue
    if len(buffer) != 0:
      if str(subtitle['content'].strip())[-1] == ".":
        buffer += "\n"
      else:
        buffer += " "
    buffer += subtitle['content'].strip()
    vtt_content += f"{to_time(subtitle['start'])} --> {to_time(subtitle['end'])}\n"
    vtt_content += buffer
    vtt_content += "\n\n\n"

def create_word_scenes(wordvtt, scriptraw):
  subtitles = from_vtt(wordvtt)
  scripts   = [i for i in scriptraw.split("\n") if i]
  print(f"VTT {len(subtitles)} lines, Script {len(scripts)} lines")
  scenes = []
  for n, script in enumerate(scripts):
    if len(script.split(" ")) == 1:
      continue
    scenes.append({"scene": script, "timestamp": []})

  scenes_cur = 0
  for n, subtitle in enumerate(subtitles):
    sentence = subtitle["content"].replace("<u>", "").replace("</u>", "")
    if len(sentence.split(" ")) == 1:
      continue

    if sentence != scenes[scenes_cur].get("scene"):
      if sentence == scenes[scenes_cur+1].get("scene"):
        scenes_cur += 1
      else:
        print(f"Error, Mismatch\n=> scenes[{scenes_cur}] != \"{sentence}\"")
        return

    current_scene = scenes[scenes_cur]
    if current_scene["timestamp"]:
      word_idx = current_scene["timestamp"][-1]["index"] + 1
    else:
      word_idx = 0

    if "<u>" in subtitle["content"]:
      word = subtitle["content"].split("<u>")[1].split("</u>")[0]
      if word not in sentence:
        print(f"Error, Mismatch\n=> \"{word}\" not in \"{sentence}\"")
        return

      try:
        assert sentence.split(" ")[word_idx] == word
      except:
        print(f"Error, Mismatch\n=> \"{word}\" != [{word_idx}] of \"{sentence}\"")
        return

      word_time = {"start": subtitle["start"], "end": subtitle["end"], "index": word_idx, "word": word}
      current_scene["timestamp"].append(word_time)

  # print(json.dumps(scenes, indent=2))

  for scene in scenes:
    if len(scene["scene"].split(" ")) != len(scene["timestamp"]):
      print("Error, Mismatch length")
      return

  full_script, full_scenes = [], []
  for scene in scenes:
    full_script += scene["scene"].split(" ")
    full_scenes += scene["timestamp"]

  for i, j in zip(full_script, full_scenes):
    if i != j["word"]:
      print("Error, Mismatch")
      return

  assert len(full_scenes) == len(full_script)

  return full_script, full_scenes
  
def scene_from_new_script(raw_script, full_script, full_scenes):
  mod_script = raw_script.replace("\n", " \n ").split(" ")
  mod_script = [i for i in mod_script if i]
  n = 0
  while True:
    if mod_script[n] == "\n":
      mod_script[n-1] += "\n"
      del(mod_script[n])
      n -= 1
    n += 1
    if n == len(mod_script):
      break
  # print(mod_script)
  print(f"Original: {len(full_script)}, Modded: {len(mod_script)}")
  allowed_list = [".", "\n", "\n\n", ","]

  def normalized(x):
    for i in allowed_list:
      x = x.replace(i, "")
    return x.upper()
  
  same = lambda a, b: normalized(a) == normalized(b)
  new_script, new_timestamp, orig_index, n = [], [], 0, 0
  while n < len(mod_script):
    # print(f"{repr(mod_script[n]):>20} ? {repr(full_script[orig_index])}")
    word = mod_script[n]
    if same(word, full_script[orig_index]):
      cur = full_scenes[orig_index]
      new_script.append(word)
      new_timestamp.append({"start": cur["start"], "end": cur["end"]})
    else:
      # print("Back")
      n -= 1
    n, orig_index = n+1, orig_index+1

  assert len(new_script) == len(new_timestamp)
  return new_script, new_timestamp

def build_new_subtitle(new_script, new_timestamp):
  buffer, new_scenes, start, end = [], [], None, None
  current_scene = []
  # print(" ".join(new_script).split("\n"))

  for i, j in zip(new_script, new_timestamp):
    if "\n" in i:
      buffer.append(i.replace("\n", ""))
      current_scene.append({"content": " ".join(buffer), "start": start, "end": j["end"]})
      buffer, start = [], None
      if "\n\n" in i:
        print(f"Section break at line #{len(current_scene):<3}| \"{current_scene[-1]["content"]}\"")
        new_scenes.append(current_scene)
        current_scene = []
    else:
      buffer.append(i)
      if not start:
        start = j["start"]

  if start:
      buffer.append(i.replace("\n", ""))
      current_scene.append({"content": " ".join(buffer), "start": start, "end": j["end"]})

  if current_scene != (new_scenes[-1] if new_scenes else None):
    new_scenes.append(current_scene)

  # print("\n\n".join(["\n".join([j["content"] for j in i]) for i in new_scenes]))
  newsub = []
  for n, i in enumerate(new_scenes):
    newsub += i
    if n < len(new_scenes) - 1:
      newsub.append({"content": "Break", "start": None, "end": None, "split": True})

  return newsub

def saveFile(filename, data, override = False):
  if os.path.exists(filename) and not override:
    print(f"File {filename} already exists.")
    return -1
  with open(filename, "w") as f:
    f.write(data)

def openFile(filename):
  with open(filename, "r") as f:
    data = f.read()
  if not data:
    return -1
  return data

def main():
  vttfile    = "test.vtt"
  scriptfile = "test.txt"
  modfile    = "test.script"

  full_script, full_scenes = create_word_scenes(openFile(vttfile), openFile(scriptfile))
  saveFile("test.script", " ".join(full_script).replace(". ", ".\n"))
  a, b = scene_from_new_script(openFile(modfile), full_script, full_scenes)
  final_vtt = build_new_subtitle(a, b)
  # print(final_vtt)
  saveFile("test.final.vtt", to_vtt(final_vtt), True)
  saveFile("test.final.json", json.dumps(final_vtt, indent=2), True)

if __name__=="__main__":
  main()