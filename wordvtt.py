#!/usr/bin/env python3

import re, json
import os
from datetime import timedelta


def from_vtt(vtt_string):
    VTT_TIMECODE_PATTERN = (
        r"((?:\d{2}:)?\d{2}:\d{2}\.\d{3}) --> ((?:\d{2}:)?\d{2}:\d{2}\.\d{3})"
    )
    VTT_LINE_NUMBER_PATTERN = r"^\d+$"
    parts = re.split(r"\n\n+", vtt_string.strip())
    if parts[0].startswith("WEBVTT"):
        parts.pop(0)

    subtitles = []
    for part in parts:
        lines = part.split("\n")
        match = re.match(VTT_TIMECODE_PATTERN, lines[0])
        if not match:
            if re.match(VTT_LINE_NUMBER_PATTERN, lines[0]):
                lines.pop(0)
            match = re.match(VTT_TIMECODE_PATTERN, lines[0])
        if not match:
            continue

        start, end = match.groups()
        content = "\n".join(lines[1:]) + "\n"
        subtitles.append(
            {
                "start": start,
                "end": end,
                "content": (
                    content.replace("-\n", "\n")
                    .replace("</u>-\n", "</u>\n")
                    .replace("-", " ")
                    .replace("%", " ")
                    .replace("<u> ", " <u>")
                    .replace(" </u>", "</u> ")
                    .replace("<u> </u>", "")
                    .replace("<u></u>", "")
                    .replace(" \n", "\n")
                )[:-1],
            }
        )
    # def sanitizevttwordlevel(subtitles):
    #   errorwords = []
    #   newords = {}
    #   for subtitle in subtitles:
    #     for word in subtitle["content"].split(" "):
    #       if ("<u>" in word):
    #         newword = None
    #         if (len(word.split("<u>")) > 1):
    #           newword = word.replace("<u>", " <u>")
    #         if (len(word.split("</u>")) > 1):
    #           newword = word.replace("</u>", "</u> ")
    #         if newword:
    #           original = word.split("<u>")[1].split("</u>")[0]
    #           if original in errorwords:
    #             for i in errorwords[original]:

    #           else:
    #             errorwords[orig].append(word)

    #   error = False
    #   if "<u>" in subtitle["content"]:
    #     if len(subtitle["content"].split("<u>")) > 1:
    #       if subtitle["content"].split("<u>")[0][-1] != " ":
    #         error = True
    #     if len(subtitle["content"].split("</u>")) > 1:
    #       if subtitle["content"].split("</u>")[1][0] != " ":
    #         error = True
    #   if error:
    #     word = subtitle["content"].split("<u>")[1].split("</u>")[0]
    #     errorwords.append(word)
    #     for word in subtitle["content"].split(" "):
    #       if word.replace("<u>")

    #   for subtitle in subtitles:
    #     for words in subtitle["content"].split(" "):
    #       if word in errorwords:
    #         subtitle["content"]

    # sanitizevttwordlevel(subtitles)
    return subtitles


def to_vtt(subtitles):
    vtt_content = "WEBVTT\n\n\n"
    for idx, subtitle in enumerate(subtitles):
        content = subtitle["content"]
        if not subtitle.get("split", False):
            start = subtitle["start"]
            end = subtitle["end"]
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
            if str(subtitle["content"].strip())[-1] == ".":
                buffer += "\n"
            else:
                buffer += " "
        buffer += subtitle["content"].strip()
        vtt_content += f"{subtitle['start']} --> {subtitle['end']}\n"
        vtt_content += buffer
        vtt_content += "\n\n\n"
    return vtt_content


def script_from_word_vtt(wordvtt):
    subtitles = from_vtt(wordvtt)
    print(f"VTT {len(subtitles)} lines. Generating script file from VTT.")
    sentences = []
    EXCEPTION_FLAG, ADD_NEXT_SENTENCE = "", 0
    for n, subtitle in enumerate(subtitles):
        sentence = subtitle["content"].replace("<u>", "").replace("</u>", "")
        if ((sentences[-1] if sentences else None) != sentence) or ADD_NEXT_SENTENCE:
            sentences.append(sentence)
        ADD_NEXT_SENTENCE = 0
        if subtitle["content"][-4:] == "</u>":
            # print(f"{len(sentences)} END {subtitle["content"]}")
            ADD_NEXT_SENTENCE = 1
            if n + 2 < len(subtitles):
                if (
                    subtitles[n + 2]["content"].replace("<u>", "").replace("</u>", "")
                    != sentence
                ):
                    ADD_NEXT_SENTENCE = 0
    return sentences


def create_word_scenes(wordvtt, scriptraw):
    subtitles = from_vtt(wordvtt)
    scripts = [i for i in scriptraw.split("\n") if i]
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
            if sentence == scenes[scenes_cur + 1].get("scene"):
                scenes_cur += 1
            else:
                print(
                    f"Error, Mismatch in scenes\n=>\"[{scenes_cur}] {scenes[scenes_cur].get("scene")}\" or \"[{scenes_cur+1}] {scenes[scenes_cur+1].get("scene")}\" != \"{sentence}\""
                )
                return

        current_scene = scenes[scenes_cur]
        if current_scene["timestamp"]:
            word_idx = current_scene["timestamp"][-1]["index"] + 1
        else:
            word_idx = 0

        # print(scenes_cur, subtitle, word_idx, sentence)
        if ("<u>" not in subtitle["content"]) and word_idx >= len(sentence.split(" ")):
            pass
        if ("<u>" in subtitle["content"]) and word_idx >= len(sentence.split(" ")):
            print(
                f"Error, index wrong. {scenes_cur}, word: {word_idx}, total words: {len(sentence.split(" "))}\n{subtitle}"
            )
            word_idx = 0
            scenes_cur += 1
            current_scene = scenes[scenes_cur]
            if current_scene["timestamp"]:
                word_idx = current_scene["timestamp"][-1]["index"] + 1
            else:
                word_idx = 0
            print(f"Changed to {word_idx}, {scenes_cur}")

        if "<u>" in subtitle["content"]:
            # print(subtitle["content"])
            word = subtitle["content"].split("<u>")[1].split("</u>")[0]

            if word not in sentence.split(" "):
                print(f'Error, Mismatch\n=> "{word}" not in "{sentence}"')
                return

            try:
                assert sentence.split(" ")[word_idx] == word
            except:
                print(f'Error, Mismatch\n=> "{word}" != [{word_idx}] of "{sentence}"')
                return

            word_time = {
                "start": subtitle["start"],
                "end": subtitle["end"],
                "index": word_idx,
                "word": word,
            }
            current_scene["timestamp"].append(word_time)

    # print(json.dumps(scenes, indent=2))

    for scene in scenes:
        if len(scene["scene"].split(" ")) != len(scene["timestamp"]):
            print("Error, Mismatch length")
            return
        if "" in scene["scene"].split(" "):
            print(repr(scene["scene"]))

    full_script, full_scenes = [], []
    for scene in scenes:
        full_script += scene["scene"].split(" ")[:-1]
        full_script.append(scene["scene"].split(" ")[-1] + "##")
        full_scenes += scene["timestamp"]

    for i, j in zip(full_script, full_scenes):
        if i.replace("##", "") != j["word"]:
            print("Error, Mismatch")
            return

    assert len(full_scenes) == len(full_script)

    return full_script, full_scenes


# Detect long break or change in context, inserts section break into script.
def autobreak(lines, times):
    from datetime import timedelta

    def parsetime(time_str):
        minutes, seconds = time_str.split(":")
        seconds, milliseconds = seconds.split(".")
        td = timedelta(
            minutes=int(minutes), seconds=int(seconds), milliseconds=int(milliseconds)
        )
        return td

    script = []
    long_breaks = []
    tmark = parsetime("0:0.0")
    for i, j in zip(lines, times):
        tdiff = parsetime(j["start"]) - tmark
        tmark = parsetime(j["end"])
        if tdiff > parsetime("0:0.0"):
            long_breaks.append(tdiff)
            # print()
        # print(i, end=" ")
    # print()

    mean_break = parsetime("0:0.0")
    for i in long_breaks:
        mean_break += i / len(long_breaks)
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

        if tdiff >= mean_break and tmp[-1] == ".":
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


def scene_from_new_script(raw_script, full_script, full_scenes):
    mod_script = raw_script.replace("\n", " \n ").split(" ")
    mod_script = [i for i in mod_script if i]
    n = 0
    while True:
        if mod_script[n] == "\n":
            mod_script[n - 1] += "\n"
            del mod_script[n]
            n -= 1
        n += 1
        if n == len(mod_script):
            break
    # print(mod_script)
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
                print("Error: Failed to match words,")
                return
            # print("Back")
            fail += 1
            n -= 1
        n, orig_index = n + 1, orig_index + 1
    assert len(new_script) == len(new_timestamp)
    return new_script, new_timestamp


def build_new_subtitle(new_script, new_timestamp):
    buffer, new_scenes, start, end = [], [], None, None
    current_scene = []
    # print(" ".join(new_script).split("\n"))

    for i, j in zip(new_script, new_timestamp):
        if "\n" in i:
            buffer.append(i.replace("\n", ""))
            current_scene.append(
                {
                    "content": " ".join(buffer).replace("##", ""),
                    "start": start,
                    "end": j["end"],
                }
            )
            buffer, start = [], None
            if "\n\n" in i:
                print(
                    f"Section break at line #{len(current_scene):<3}| \"{current_scene[-1]["content"]}\""
                )
                new_scenes.append(current_scene)
                current_scene = []
        else:
            buffer.append(i)
            if not start:
                start = j["start"]

    if start:
        buffer.append(i.replace("\n", ""))
        current_scene.append(
            {"content": " ".join(buffer), "start": start, "end": j["end"]}
        )

    if current_scene != (new_scenes[-1] if new_scenes else None):
        new_scenes.append(current_scene)

    # print("\n\n".join(["\n".join([j["content"] for j in i]) for i in new_scenes]))
    newsub = []
    for n, i in enumerate(new_scenes):
        newsub += i
        if n < len(new_scenes) - 1:
            newsub.append(
                {"content": "Break", "start": None, "end": None, "split": True}
            )

    return newsub


def saveFile(filename, data, override=False):
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


def main(vttfile, scriptfile):
    modfile = ".".join(scriptfile.split(".")[:-1]) + ".script"
    x = create_word_scenes(openFile(vttfile), openFile(scriptfile))
    if not x:
        sys.exit(-1)
    full_script, full_scenes = x

    if not os.path.exists(modfile):
        genscript = autobreak(full_script, full_scenes)
        saveFile(modfile, genscript)
        print(f"Saved modification file as {modfile}. Modify it and return back.")
    else:
        x = scene_from_new_script(openFile(modfile), full_script, full_scenes)
        if not x:
            sys.exit(-1)
        a, b = x

        final_vtt = build_new_subtitle(a, b)
        jsonfile = ".".join(vttfile.split(".")[:-1]) + ".json"
        saveFile(jsonfile, json.dumps(final_vtt, indent=2), True)
        print(f"Saved JSON file as {jsonfile}. Fix it, and convert it to VTT.")


if __name__ == "__main__":
    import sys

    if len(sys.argv) not in (2, 3):
        print(
            f"Usage: {sys.argv[0].split("/")[-1]} [vtt file] (txt file)\n"
            f"       {sys.argv[0].split("/")[-1]} [JSON file]\n"
            "** Only output from openai-whisper with '--word-timestamp true' is accepted.)\n"
            "** You have to run this for first time, and then fix .script file, and then re-run this script.\n"
            "** Adding newline/period/commas are onlt permitted. Fix else in JSON file."
        )
        sys.exit()

    vtt = sys.argv[1]
    print(f"\n[{vtt}]")
    if len(sys.argv) == 3:
        script = sys.argv[2]
        if (not os.path.exists(vtt)) or (not os.path.exists(script)):
            print(f"Input file doesnt exists.")
            sys.exit(-1)
        main(vtt, script)
    else:
        if ".json" in vtt:
            final_vtt = json.loads(openFile(vtt))
            orgf = ".".join(vtt.split(".")[:-1])
            print(f"Saved VTT file as {orgf}.final.vtt.")
            saveFile(orgf + ".final.vtt", to_vtt(final_vtt), True)
            saveFile(orgf + ".stacked.vtt", to_stacked_vtt(final_vtt), True)
            sys.exit(0)
        if not os.path.exists(vtt):
            print(f"Input file doesnt exists.")
            sys.exit(-1)
        script = ".".join(vtt.split(".")[:-1]) + ".txt"
        saveFile(script, "\n".join(script_from_word_vtt(openFile(vtt))))
        main(vtt, script)
