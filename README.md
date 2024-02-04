## VTT Maker.
Python GUI app for VTT subtitling.

Just makes stacking subtitle. Nothing more, nothing advanced.

### Usage
Load audio, load script, play audio, make subtitle.

Script files are linebreaked text file, each line acts as single scene. 
When from openai/whisper, you usually have to edit it manually.

You can save your progress, and restore it. Script file also saved in savefile.

You can edit, merge, delete each script lines.

- **Mark(<;>)**

  Marks start or end of scene.

- **Next(<'>)**

  Marks end, and starts next scene.

- **Done(\<Return\>)**

 Marks breaks scene, resets scene stack.
  
<br />

### Stacking subtitle?

It's subtitle that just stackes from previous scene until it gets too long, usually for lecture sutitles.

```
01:29.000 --> 01:38.000
Welcome to our lecture on system programming, an essential field that serves as the backbone of computer operation and performance. 

01:39.000 --> 01:49.000
Welcome to our lecture on system programming, an essential field that serves as the backbone of computer operation and performance. 
Today, we're going to dive deep into the intricacies of system-level software,

01:50.000 --> 01:54.000
Welcome to our lecture on system programming, an essential field that serves as the backbone of computer operation and performance. 
Today, we're going to dive deep into the intricacies of system-level software,
exploring how it interfaces directly with the hardware, providing a platform for all other application software to run.

01:55.000 --> 01:57.000
System programming is often characterized by its complexity and the need for precision, as it operates close to the machine. 

01:58.000 --> 02:00.000
System programming is often characterized by its complexity and the need for precision, as it operates close to the machine. 
We'll cover key concepts including memory management, process scheduling, and file systems,

02:00.000 --> 02:10.000
System programming is often characterized by its complexity and the need for precision, as it operates close to the machine. 
We'll cover key concepts including memory management, process scheduling, and file systems,
which are critical for ensuring that our computers run efficiently and reliably.
```
