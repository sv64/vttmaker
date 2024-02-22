import json
import os, sys


def readFile(file):
    if not os.path.exists(file):
        raise Exception(f"File {file} doesn't exists.")
    with open(file, "r") as f:
        data = f.read()
    return data


def writeFile(file, data, overwrite=False):
    if (not overwrite) and os.path.exists(file):
        raise Exception(f"File {file} already exists.")
    if not len(data):
        raise Exception(f"Tried to write empty data.")
    with open(file, "w") as f:
        ret = f.write(data)
    return ret


file = sys.argv[1]

if ".json" in file:
    subtitles = json.loads(readFile(file))
    output = ""
    index = 0
    for subtitle in subtitles:
        if subtitle.get("split", False):
            output += "\n"
        else:
            index += 1
            start = subtitle["start"]
            end = subtitle["end"]
            content = subtitle["content"]
            "| {start:>10} --> {end:>10} |"
            output += f"{index:03} | {content.strip()}\n"

    output += "############ TIMESTAMPS ############\n\n"

    index = 0
    for subtitle in subtitles:
        if not subtitle.get("split", False):
            index += 1
            start = subtitle["start"]
            end = subtitle["end"]
            output += f"{index:03} | {start} --> {end} \n"

    writeFile(os.path.splitext(file)[0] + ".edit", output)

elif ".edit" in file:
    subtitles = json.loads(readFile(os.path.splitext(file)[0] + ".json"))
    lines = readFile(file)

    idx, sub = 0, {}
    for subtitle in subtitles:
        if not subtitle.get("split", False):
            sub[idx] = subtitle
            idx += 1

    new_brk, new_sub = [], {}
    for line in lines.split("\n"):
        if "############ TIMESTAMPS ############" in line:
            break
        if line:
            idx, content = line.split(" | ")
            idx = int(idx) - 1
            if sub[idx]["content"] != content:
                print(f"{idx} {sub[idx]["content"]} -> {content}")
            new_sub[idx] = {
                "content": content,
                "start": sub[idx]["start"],
                "end": sub[idx]["end"],
            }
        else:
            new_brk.append(idx)

    output = []
    for n in sorted(new_sub):
        subtitle = new_sub[n]
        output.append(subtitle)
        if n in new_brk:
            output.append(
                {"content": "Break", "start": None, "end": None, "split": True}
            )

    writeFile(os.path.splitext(file)[0] + ".json.1", json.dumps(output, indent=2))
