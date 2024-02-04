import re
from datetime import timedelta

VTT_TIMECODE_PATTERN = r"((?:\d{2}:)?\d{2}:\d{2}\.\d{3}) --> ((?:\d{2}:)?\d{2}:\d{2}\.\d{3})"
VTT_LINE_NUMBER_PATTERN = r"^\d+$"

def parse_vtt(vtt_string):
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
    vtt_content = "WEBVTT\n\n"
    for idx, subtitle in enumerate(subtitles):
        # print(subtitle, idx)
        start = subtitle['start']
        end = subtitle['end']
        content = subtitle['content']
        vtt_content += f"{start} --> {end}\n{content}\n\n"
    return vtt_content.strip()


with open("example.vtt", "r") as f:
    vtt_content = f.read()

parsed_vtt = parse_vtt(vtt_content)
#print(len(parsed_vtt))

buffer = []
linebuf = []

for line in parsed_vtt:
#    print(line["content"].strip())
    content = line["content"].strip()
    if "".join([i["content"] for i in linebuf]).count(".") < 4   or   len(linebuf) < 5:
        linebuf.append(line)
    else:
        linebuf.append(line)
        buffer.append(linebuf)
        linebuf = []

# print(buffer)

sub = []
for section in buffer:
    strbuf = ""
    for scene in section:
        strbuf += scene["content"]
        # if scene["content"][-1] == ".":
        strbuf += "\n"
        # else:
            # strbuf += " "
        scene["content"] = strbuf
        sub.append(scene)

# print(buffer[0])

print(to_vtt(sub))