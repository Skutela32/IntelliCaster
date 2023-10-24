from moviepy.video.io.VideoFileClip import VideoFileClip
from moviepy.audio.io.AudioFileClip import AudioFileClip
from moviepy.audio.AudioClip import CompositeAudioClip
from moviepy.audio.fx.audio_normalize import audio_normalize
from moviepy.audio.fx.volumex import volumex
import os
from core import export


class Editor:
    def __init__(self, settings):
        # Member variables
        self.settings = settings

    def create_video(self, root_window):
        # Create export window
        export_window = export.Export(root_window)

        # Load the video clip
        video = self.get_latest_video()

        # Normalize the original video audio
        original_audio = audio_normalize(video.audio)

        # Adjust the volume
        original_audio = original_audio.fx(volumex, 0.3)

        # Get all of the commentary audio
        commentary_audio = self.get_commentary_audio()

        # Create a composite audio clip
        new_audio = CompositeAudioClip([original_audio] + commentary_audio)

        # Set the new audio's fps to 44.1kHz (workaround MoviePy issue #863)
        new_audio = new_audio.set_fps(44100)

        # Normalize the new audio
        new_audio = audio_normalize(new_audio)

        # Set the new audio to the video
        video = video.set_audio(new_audio)

        # Write the result to a file
        video.write_videofile(
            f"output_video.{self.settings['general']['video_format']}",
            fps=int(self.settings["general"]["video_framerate"]),
            logger=export_window.progress_tracker
        )

        # Clean up videos directory
        self.delete_commentary_audio()
        self.delete_latest_video()

    def delete_commentary_audio(self):
        # Get the iRacing videos folder
        path = os.path.join(self.settings["general"]["iracing_path"], "videos")

        # Get a list of all of the .wav files in that folder
        files = []
        for file in os.listdir(path):
            if file.endswith(".wav"):
                files.append(os.path.join(path, file))

        # Delete all of the .wav files
        for file in files:
            os.remove(file)

    def delete_latest_video(self):
        # Get the iRacing videos folder
        path = os.path.join(self.settings["general"]["iracing_path"], "videos")

        # Find the most recent .mp4 video in that folder
        files = []
        for file in os.listdir(path):
            if file.endswith(".mp4"):
                files.append(os.path.join(path, file))
        latest_file = max(files, key=os.path.getctime)

        # Delete the file
        os.remove(latest_file)

    def get_commentary_audio(self):
        # Get the iRacing videos folder
        path = os.path.join(self.settings["general"]["iracing_path"], "videos")

        # Get a list of all of the .wav files in that folder
        files = []
        for file in os.listdir(path):
            if file.endswith(".wav"):
                files.append(os.path.join(path, file))

        audio_clips = []
        for file in files:
            # Get the file name
            file_name = os.path.basename(file)

            # Extract the timestamp from the file name
            timestamp = file_name.replace("commentary_", "")
            timestamp = timestamp.replace(".wav", "")
            timestamp = float(timestamp) / 1000

            # Create the audio clip
            audio = AudioFileClip(file).set_start(timestamp)

            # Add the audio clip to the list
            audio_clips.append(audio)

        # Return the list of audio clips
        return audio_clips

    def get_latest_video(self):
        # Get the iRacing videos folder
        path = os.path.join(self.settings["general"]["iracing_path"], "videos")

        # Find the most recent .mp4 video in that folder
        files = []
        for file in os.listdir(path):
            if file.endswith(".mp4"):
                files.append(os.path.join(path, file))
        latest_file = max(files, key=os.path.getctime)

        # Convert it to a MoviePy video clip
        video_clip = VideoFileClip(latest_file)

        # Return the video clip
        return video_clip