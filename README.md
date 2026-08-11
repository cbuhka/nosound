# NoSound

A simple Windows GUI application for removing audio from video files without re-encoding the video.

## Features

- Batch processing of multiple video files
- Removes the audio stream from videos
- Copies the video stream without re-encoding
- Supports multiple video formats
- Selectable output folder
- Automatic sequential processing
- Failed files remain in the list and are not deleted
- Successfully converted files are automatically removed from the list
- Progress bar for the current file
- Overall conversion progress
- Estimated remaining time for the current file and the entire batch
- Optional deletion of successfully converted source files
- FFmpeg included in the executable

No rights reserved.

## FFmpeg

NoSound uses FFmpeg for video processing.

The included FFmpeg executable is from the
[FFmpeg Essentials Build](https://www.gyan.dev/ffmpeg/builds/).

FFmpeg:
https://ffmpeg.org/

FFmpeg source code:
https://github.com/FFmpeg/FFmpeg

FFmpeg is a separate project and is distributed under its own license.
