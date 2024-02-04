import json
import re

def parse_vtt(vtt_filename):
    with open(vtt_filename, 'r', encoding='utf-8') as file:
        lines = file.readlines()

    time_pattern = re.compile(r'(\d+\.\d{3}) --> (\d+\.\d{3})')

    subtitles = []
    current_subtitle = {}

    for line in lines[1:]:
        match = time_pattern.match(line)
        if match:
            current_subtitle['start'] = float(match.group(1))
            current_subtitle['end'] = float(match.group(2))
            current_subtitle['content'] = ""
        elif line.strip() == '':
            if current_subtitle:
                if current_subtitle['content'][-1] == "\n":
                    current_subtitle['content'] = current_subtitle['content'][:-1]
                subtitles.append(current_subtitle)
                current_subtitle = {}
        else:
            current_subtitle['content'] += line.strip() + "\n"  # Space to separate lines

    if current_subtitle:
        if current_subtitle['content'][-1] == "\n":
            current_subtitle['content'] = current_subtitle['content'][:-1]
        subtitles.append(current_subtitle)

    return subtitles

def subtitles_to_backup(subtitles):

    backup_data = {
        "subtitles": subtitles, 
        "script_lines": [],
        "line_index": len(subtitles),
        "current_subtitle": {}, 
        "play": 0
    }
    return backup_data

def main(vtt_filename, output_filename):
    subtitles = parse_vtt(vtt_filename)
    backup_data = subtitles_to_backup(subtitles)

    with open(output_filename, 'w', encoding='utf-8') as json_file:
        json.dump(backup_data, json_file, indent=2)

vtt_filename = 'audio.vtt'
output_filename = 'backup2.json'
main(vtt_filename, output_filename)
