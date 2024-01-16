import os

from customtkinter import filedialog
from moviepy.audio.AudioClip import CompositeAudioClip
from moviepy.audio.fx.audio_normalize import audio_normalize
from moviepy.audio.fx.volumex import volumex
from moviepy.audio.io.AudioFileClip import AudioFileClip
from moviepy.video.io.VideoFileClip import VideoFileClip

from core import common
from core import export


class Editor:
    """The editor class

    This class is responsible for creating the final video. It combines the
    original video with the commentary audio clips and exports the result to a
    file.
    """

    def _delete_commentary_audio(self):
        """Delete the commentary audio clips from the iRacing videos folder

        Deletes the commentary audio clips from the iRacing videos folder. This
        is used to clean up the videos folder after the video has been exported.
        """
        # Get the iRacing videos folder
        path = os.path.join(common.settings["general"]["iracing_path"], "videos")

        # Get a list of all of the .mp3 files in that folder
        files = []
        for file in os.listdir(path):
            if file.endswith(".mp3"):
                files.append(os.path.join(path, file))

        # Delete all of the .mp3 files
        for file in files:
            os.remove(file)

    def _delete_latest_video(self):
        """Delete the latest video from the iRacing videos folder
        
        Deletes the latest video from the iRacing videos folder. This is used to
        clean up the videos folder after the video has been exported.
        """
        # Get the iRacing videos folder
        path = os.path.join(common.settings["general"]["iracing_path"], "videos")

        # Find the most recent .mp4 video in that folder
        files = []
        for file in os.listdir(path):
            if file.endswith(".mp4"):
                files.append(os.path.join(path, file))
        latest_file = max(files, key=os.path.getctime)

        # Delete the file
        os.remove(latest_file)
    
    def _delete_screenshot(self):
        """Delete the screenshot from the iRacing videos folder
        
        Deletes the screenshot from the iRacing videos folder. This is used to
        clean up the videos folder after the video has been exported.
        """
        # Get the path to the screenshot
        path = os.path.join(
            common.settings["general"]["iracing_path"],
            "videos",
            "screenshot.png"
        )

        # Delete the file if it exists
        if os.path.exists(path):
            os.remove(path)

    def _get_commentary_audio(self):
        """Get the commentary audio clips from the iRacing videos folder
        
        Returns:
            list: A list of audio clips
        """
        # Get the iRacing videos folder
        path = os.path.join(common.settings["general"]["iracing_path"], "videos")

        # Get a list of all of the .mp3 files in that folder
        files = []
        for file in os.listdir(path):
            if file.endswith(".mp3"):
                files.append(os.path.join(path, file))

        audio_clips = []
        for file in files:
            # Get the file name
            file_name = os.path.basename(file)

            # Extract the timestamp from the file name
            timestamp = file_name.replace("commentary_", "")
            timestamp = timestamp.replace(".mp3", "")
            timestamp = float(timestamp) / 1000

            # Create the audio clip
            audio = AudioFileClip(file).set_start(timestamp)

            # Cut end of audio to avoid glitch
            audio = audio.subclip(0, audio.duration - 0.05)

            # Normalize the audio
            audio = audio_normalize(audio)

            # Add the audio clip to the list
            audio_clips.append(audio)

        # Return the list of audio clips
        return audio_clips

    def _get_latest_video(self):
        """Get the latest video clip from the iRacing videos folder
        
        Returns:
            VideoFileClip: The video clip
        """
        # Get the iRacing videos folder
        path = os.path.join(
            common.settings["general"]["iracing_path"],
            "videos"
        )

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

    def create_video(self):
        """Create the video

        Creates the video by combining the original video with the commentary
        audio clips. This method is called by the main window when the user
        clicks the 'Stop Commentary' button.
        """
        # Ask the user where to save the video
        target = filedialog.asksaveasfilename(
            filetypes=[(
                "Video File",
                f"*.{common.settings['general']['video_format']}"
            )],
            initialfile="output_video",
            title="Save Video"
        )
        
        # Return if the user canceled
        if target == "":
            # Clean up videos directory
            self._delete_commentary_audio()
            self._delete_latest_video()
            self._delete_screenshot()

            return

        # Create export window
        export_window = export.Export(common.app)

        # Load the video clip
        video = self._get_latest_video()

        # Normalize the original video audio
        original_audio = audio_normalize(video.audio)

        # Adjust the volume
        original_audio = original_audio.fx(volumex, 0.3)

        # Get all of the commentary audio
        commentary_audio = self._get_commentary_audio()

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
            f"{target}.{common.settings['general']['video_format']}",
            fps=int(common.settings["general"]["video_framerate"]),
            logger=export_window.progress_tracker
        )

        # Clean up videos directory
        self._delete_commentary_audio()
        self._delete_latest_video()
        self._delete_screenshot()