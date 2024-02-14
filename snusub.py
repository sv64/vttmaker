#!/usr/bin/env python3

import re, json
import os, sys
from datetime import timedelta

###

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
    content = '\n'.join(lines[1:]) + "\n"
    # if start == end:
    #   continue
      
    subtitles.append({
      'start': start,
      'end': end,
      'content': (content.replace("-\n", "\n").replace("</u>-\n", "</u>\n").replace("-", " ").replace("%", " ").replace("<u> "," <u>").replace(" </u>","</u> ").replace("<u> </u>","").replace("<u></u>","").replace(" \n", "\n"))[:-1]
    })

  return subtitles

def to_vtt(subtitles):
    vtt_content = "WEBVTT\n\n\n"
    for idx, subtitle in enumerate(subtitles):
        content = subtitle['content']
        if not subtitle.get("split", False):
          start = subtitle['start']
          end = subtitle['end']
          if not start or not end or start == end:
            raise Exception(f"VTT timestamp parse error from #{idx}.")
          vtt_content += f"{start} --> {end}\n{content}\n\n\n"
        else:
          vtt_content += f"NOTE {content}\n\n\n"

    return vtt_content.strip()

def to_stacked_vtt(subtitles, continous = True):
  vtt_content = "WEBVTT\n\n\n"
  buffer = ""
  for n, subtitle in enumerate(subtitles):
    if subtitle.get("split", False):
      buffer = ""
      continue

    if len(buffer) != 0:
      if str(subtitle['content'].strip())[-1] == ".":
        buffer += "\n"
      else:
        buffer += " "

    buffer += subtitle['content'].strip()

    if n < len(subtitles) - 1:
      end_time = subtitles[n+1]['start'] if continous and not subtitles[n+1].get("split", False) else subtitle['end']
    else:
      end_time = subtitle['end']
    
    if not subtitle['start'] or not end_time:
      raise Exception(f"VTT timestamp parse error from #{idx}.")
    if subtitle['start'] == end_time:
      raise Exception(f"Error, subtitle timestamp overlaps.\n{subtitle['start']} --> {end_time} {subtitle['content'].strip()}")
    vtt_content += f"{subtitle['start']} --> {end_time}\n"
    vtt_content += buffer
    vtt_content += "\n\n\n"

    print(f"{subtitle['start']} --> {end_time}\n{buffer}\n\n")

  return vtt_content

###

def script_from_word_vtt(wordvtt):
  subtitles = from_vtt(wordvtt)
  print(f"Generating script file from VTT...")
  sentences = []
  ADD_NEXT_SENTENCE = 0
  for n, subtitle in enumerate(subtitles):
    sentence = subtitle["content"].replace("<u>", "").replace("</u>", "")
    if ((sentences[-1] if sentences else None) != sentence) or ADD_NEXT_SENTENCE:
      sentences.append(sentence)
      ADD_NEXT_SENTENCE = 0
    if subtitle["content"][-4:] == "</u>":
      ADD_NEXT_SENTENCE = 1
      if n + 2 < len(subtitles):
        if subtitles[n+2]["content"].replace("<u>", "").replace("</u>", "") != sentence:
          ADD_NEXT_SENTENCE = 0
  return sentences

def create_word_scenes(raw_vtt, raw_script):
  subtitles = from_vtt(raw_vtt)
  scripts   = [i for i in raw_script.split("\n") if i]
  print(f"Found {len(subtitles)} subtitles, {len(scripts)} scenes.\nTimestamping each words...")

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
        raise Exception(f"Error, Failed to match sentence with scene.\n\"{scenes[scenes_cur].get("scene")}\" or \"[{scenes_cur+1}] {scenes[scenes_cur+1].get("scene")}\" != \"{sentence}\"")

    current_scene = scenes[scenes_cur]
    if current_scene["timestamp"]:
      word_idx = current_scene["timestamp"][-1]["index"] + 1
    else:
      word_idx = 0

    if ("<u>" not in subtitle["content"]) and word_idx >= len(sentence.split(" ")):
      # Ignore trailing dummy subtitle after last word indexed.
      pass

    if ("<u>" in subtitle["content"]) and word_idx >= len(sentence.split(" ")):
      # If there is trailing non-dummy timestamped subtitle, Reset word_idx and step to next scene. (Repeating sentence doesnt increment cur.)
      print(f"Error, Index wrong. {scenes_cur}, word: {word_idx}, total words: {len(sentence.split(" "))}\n{subtitle}")
      word_idx = 0
      scenes_cur += 1
      current_scene = scenes[scenes_cur]
      if current_scene["timestamp"]:
        word_idx = current_scene["timestamp"][-1]["index"] + 1
      else:
        word_idx = 0
      print(f"Changed to {word_idx}, {scenes_cur}")

    # Start matching words.
    if "<u>" in subtitle["content"]:
      word = subtitle["content"].split("<u>")[1].split("</u>")[0]

      if word not in sentence.split(" "):
        raise Exception(f"Error, Mismatch\n=> \"{word}\" not in \"{sentence}\"")
        return

      try:
        assert sentence.split(" ")[word_idx] == word
      except:
        raise Exception(f"Error, Mismatch\n=> \"{word}\" != [{word_idx}] of \"{sentence}\"")

      word_time = {"start": subtitle["start"], "end": subtitle["end"], "index": word_idx, "word": word}
      current_scene["timestamp"].append(word_time)

  for scene in scenes:
    if len(scene["scene"].split(" ")) != len(scene["timestamp"]):
      raise Exception("Error, Scene length and timestamp length doesnt match.")
    if "" in scene["scene"].split(" "):
      print(repr(scene["scene"]))

  full_script, full_scenes = [], []
  for scene in scenes:
    full_script += scene["scene"].split(" ")[:-1]
    full_script.append(scene["scene"].split(" ")[-1]+"##")
    full_scenes += scene["timestamp"]

  for i, j in zip(full_script, full_scenes):
    if i.replace("##", "") != j["word"]:
      raise Exception("Error, Mismatch")
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
  
  print(f"Original: {len(full_script)}, Modded: {len(mod_script)}")
  allowed_list = [".", "\n", "\n\n", ",", "?", "##"]

  def normalized(x):
    for i in allowed_list:
      x = x.replace(i, "")
    return x.upper()
  
  same = lambda a, b: normalized(a) == normalized(b)
  new_script, new_timestamp, orig_index, n = [], [], 0, 0
  fail = 0
  while n < len(mod_script):
    print(f"{repr(mod_script[n]):>20} ? {repr(full_script[orig_index])}")
    word = mod_script[n]
    if same(word, full_script[orig_index].replace("##", "")):
      cur = full_scenes[orig_index]
      new_script.append(word.replace("##", ""))
      new_timestamp.append({"start": cur["start"], "end": cur["end"]})
      fail = 0
    else:
      if fail > 10:
        raise Exception("Error: Failed to match words,")
        return
      fail += 1
      n -= 1
    n, orig_index = n+1, orig_index+1
  assert len(new_script) == len(new_timestamp)
  return new_script, new_timestamp

def build_new_subtitle(new_script, new_timestamp):
  buffer, new_scenes, start, end = [], [], None, None
  current_scene = []
 
  for i, j in zip(new_script, new_timestamp):
    buffer.append(i.replace("\n", ""))
    if not start:
      start = j["start"]

    if "\n" in i:
      current_scene.append({"content": " ".join(buffer).replace("##", ""), "start": start, "end": j["end"]})
      buffer, start = [], None
 
    if "\n\n" in i:
      print(f"Section break at line #{len(current_scene):<3}| \"{current_scene[-1]["content"]}\"")
      new_scenes.append(current_scene)
      current_scene = []

  if start:
      buffer.append(i.replace("\n", ""))
      current_scene.append({"content": " ".join(buffer), "start": start, "end": j["end"]})

  if current_scene != (new_scenes[-1] if new_scenes else None):
    new_scenes.append(current_scene)

  newsub = []
  for n, i in enumerate(new_scenes):
    newsub += i
    if n < len(new_scenes) - 1:
      newsub.append({"content": "Break", "start": None, "end": None, "split": True})

  return newsub

###

def autobreak(lines, times):
  from datetime import timedelta

  def parsetime(time_str):
    minutes, seconds = time_str.split(':')
    seconds, milliseconds = seconds.split('.')
    td = timedelta(minutes=int(minutes), seconds=int(seconds), milliseconds=int(milliseconds))
    return td

  script = []
  long_breaks = []
  tmark = parsetime("0:0.0")
  for i, j in zip(lines, times):
    tdiff = parsetime(j["start"]) - tmark
    tmark = parsetime(j["end"])
    if tdiff > parsetime("0:0.0"):
      long_breaks.append(tdiff)

  mean_break = parsetime("0:0.0")
  for i in long_breaks:
    mean_break += i/len(long_breaks)
  print(mean_break)

  script = ""
  tmark = parsetime("0:0.0")
  tmp = " "

  continous_line = 0
  for i, j in zip(lines, times):
    tdiff = parsetime(j["start"]) - tmark
    tmark = parsetime(j["end"])
    if tdiff > mean_break and tmp[-1] != ".":
      script += "\n"

    if (tdiff >= mean_break and tmp[-1] == "."):
        script += "\n"
        continous_line = 0
    else:
      continous_line += 1

    script += i.replace("##", "")

    if i[-1] == ".":
      script += "\n"
    elif "##" in i:
        script += "\n"
    else:
      script += " " 
    tmp = i
  
  return script

############################################

def saveFile(filename, data, override = False):
  if os.path.exists(filename) and not override:
    raise Exception(f"File {filename} already exists.")
    return
  with open(filename, "w") as f:
    f.write(data)

def openFile(filename):
  if not os.path.exists(filename):
    raise Exception(f"File {filename} doesnt exists.")
    return
  with open(filename, "r") as f:
    data = f.read()
  if not data:
    raise Exception("Data empty.")
    return
  return data

############################################

if __name__=="__main__":
  PROG = sys.argv[0].split("/")[-1]
  if len(sys.argv) not in (3, 4):
    print( \
f"""Usage: {PROG} [COMMAND] [FILES]...

Commands:
 - script   <VTT file>                    Generates script file from vtt file.
 - apply    <VTT file> <script file>      Applies new scripted file to create JSON file.
 - create   <JSON file>                   Creates new vtt from given JSON.
 """)                              
    sys.exit()

  COMMAND = sys.argv[1]
  if COMMAND not in ["script", "apply", "create"]:
    print("Error. Command not found.")
    sys.exit()

  print(f"-> {sys.argv}")
  if COMMAND == "script":
    FILE = sys.argv[2]
    if (not os.path.exists(FILE)):
      print(f"Input file doesnt exists.")
      sys.exit(-1)

    modfile = ".".join(scriptfile.split(".")[:-1]) + ".script"
    x = create_word_scenes(openFile(FILE), "\n".join(script_from_word_vtt(openFile(FILE))))
    if not x:
      sys.exit(-1)

    full_script, full_scenes = x
    genscript = autobreak(full_script, full_scenes)
    saveFile(modfile, genscript)
    print(f"Saved script file {modfile}.")
  
  elif COMMAND == "apply":
    if len(sys.argv) != 4:
      print(f"Not sufficient input.")
      sys.exit()

    FILE1, FILE2 = sys.argv[2], sys.argv[3]
    if (not os.path.exists(FILE1)) or (not os.path.exists(FILE2)):
      print(f"Input file doesnt exists.")
      sys.exit(-1)

    x = create_word_scenes(openFile(FILE1), "\n".join(script_from_word_vtt(openFile(FILE1))))
    if not x:
      sys.exit(-1)
    full_script, full_scenes = x

    x = scene_from_new_script(openFile(FILE2), full_script, full_scenes)
    if not x:
      sys.exit(-1)
    a, b = x

    final_sub = build_new_subtitle(a, b)
    jsonfile = ".".join(FILE1.split(".")[:-1]) + ".json"
    saveFile(jsonfile, json.dumps(final_sub, indent=2), True)
    print(f"Saved JSON file {jsonfile}.")
    sys.exit(0)
  
  elif COMMAND == "create":
    FILE = sys.argv[2]
    if (not os.path.exists(FILE)):
      print(f"Input file doesnt exists.")
      sys.exit(-1)

    final_vtt = json.loads(openFile(FILE))
    orgf = ".".join(FILE.split(".")[:-1])
    print(f"Saved VTT file as {orgf}.final.vtt.")

    if os.path.exists(orgf + ".vtt"):
      saveFile(orgf + ".stacked.vtt", to_stacked_vtt(final_vtt), True)
    else:
      saveFile(orgf + ".vtt", to_stacked_vtt(final_vtt), True)
    sys.exit(0)