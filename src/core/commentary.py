import base64
import os
import time

import elevenlabs
from mutagen.mp3 import MP3
import openai
from PIL import Image
import pyautogui
import pygetwindow as gw

from core import common


class Commentary:
    """Manages the TextGenerator and VoiceGenerator classes.

    The Commentary class is responsible for generating text commentary based
    on events, roles, tones, and additional information. It is then responsible
    for generating audio for the commentary once it has been generated. This
    allows commentary to be generated by a single function call.
    """

    def __init__(self):
        """Initialize the Commentary class.

        Initializes the TextGenerator and VoiceGenerator classes.

        Attributes:
            text_generator (TextGenerator): The TextGenerator class.
            voice_generator (VoiceGenerator): The VoiceGenerator class.
        """
        # Create the text generator
        self.text_generator = TextGenerator()

        # Create the voice generator
        self.voice_generator = VoiceGenerator()

    def generate(
            self, 
            event,
            lap_percent,
            role, 
            tone, 
            other_info="", 
            yelling=False,
            rec_start_time=0
        ):
        """Generate commentary for the given event.

        Generates text commentary for the given event based on the provided
        instructions, then generates audio for the commentary.

        Args:
            event (str): The event that occurred.
            lap_percent (float): The percentage of the lap the event occurred
                on.
            role (str): The role of the commentator.
            tone (str): The tone of the commentary.
            other_info (str): Additional information to be included in the
                system message.
            yelling (bool): Whether or not to convert the text to yelling.
            rec_start_time (float): The time the recording started.
        """
        # Get the start time of this method
        start_time = time.time()

        # Get the timestamp
        timestamp = time.time() - rec_start_time

        # Convert the timestamp to milliseconds
        timestamp = int(timestamp * 1000)

        # Generate the commentary text
        text = self.text_generator.generate(
            event=event,
            lap_percent=lap_percent,
            role=role,
            tone=tone,
            other_info=other_info
        )

        # Add the message to the message box
        common.app.add_message(f"{role.title()}: {text}")

        # Pick the correct voice for the role
        if role == "play-by-play":
            voice = common.settings["commentary"]["pbp_voice"]
        elif role == "color":
            voice = common.settings["commentary"]["color_voice"]

        # Calculate how long it took to generate the text
        gpt_time = time.time() - start_time

        # Generate the audio
        self.voice_generator.generate(
            text=text,
            timestamp=timestamp,
            gpt_time=gpt_time,
            yelling=yelling,
            voice=voice
        )

class TextGenerator:
    """Handles text generation for race commentary.

    Uses OpenAI's GPT to generate text commentary based on events, roles,
    tones, and additional information. Maintains a list of previous responses
    to use as context for future commentary.
    """

    def __init__(self):
        """Initialize the TextGenerator class.
    
        Initializes the OpenAI API key and sets up an empty list to hold
        previous responses generated for commentary.

        Attributes:
            previous_responses (list): A list of previous responses generated
            for commentary.
        """

        # Create the OpenAI client
        self.client = openai.OpenAI(
            api_key=common.settings["keys"]["openai_api_key"]
        )

        # Pick the appropriate model based on settings
        model_setting = common.settings["commentary"]["gpt_model"]
        if model_setting == "GPT-3.5 Turbo":
            self.model = "gpt-3.5-turbo"
        elif model_setting == "GPT-4 Turbo":
            self.model = "gpt-4-1106-preview"
        elif model_setting == "GPT-4 Turbo with Vision":
            self.model = "gpt-4-vision-preview"
        else:
            raise ValueError("Invalid GPT model setting.")

        # Create an empty list to hold previous responses
        self.previous_responses = []
    
    def generate(self, event, lap_percent, role, tone, other_info=""):
        """Generate text commentary for the given event.
        
        Generates text commentary for the given event based on the provided
        instructions. Uses the provided iRacing information to provide context
        for the commentary. Adds the generated commentary to the list of
        previous responses.
        
        Args:
            event (str): The event that occurred.
            lap_percent (float): The percentage of the lap the event occurred
                on.
            role (str): The role of the commentator.
            tone (str): The tone of the commentary.
            other_info (str): Additional information to be included in the
                system message.
        
        Returns:
            str: The generated commentary.
        """
        # Create an empty list to hold the messages
        messages = []

        # Start building the system message
        new_msg = ""

        # Add messages based on role
        if role == "play-by-play":
            # Add the name to the system message
            new_msg += "You are an iRacing play-by-play commentator. "

            # Add play-by-play instructions
            new_msg += "You will respond with only one sentence. "
            new_msg += "Do not provide too much detail. Focus on the action. "
            new_msg += "Do not just say the word \"play-by-play\". "

        elif role == "color":
            # Add the name to the system message
            new_msg += "You are an iRacing color commentator. "

            # Add color instructions
            new_msg += "You will respond with one to two short sentences. "
            new_msg += "Stick to providing insight or context that enhances "
            new_msg += "the viewer's understanding. "
            new_msg += "Do not make up corner names or numbers. "
            new_msg += "Do not just say the word \"color\". "

        # Add common instructions
        new_msg += "Almost always refer to drivers by only their surname. "
        new_msg += f"Use a {tone} tone. "

        # Add additional info to the end of the system message
        new_msg += other_info

        # Add the initial system message
        sys_init = {
            "role": "system",
            "name": "instructions",
            "content": new_msg
        }
        messages.append(sys_init)

        # Start building the context system message
        new_msg = ""

        # For each available value, add it to the message
        if common.context.get("league", {}).get("name") is not None:
            new_msg += f"The league is {common.context['league']['name']}. "
        if common.context.get("league", {}).get("short_name") is not None:
            # If the league short name is one word, add hyphens between letters
            if len(common.context["league"]["short_name"].split()) == 1:
                short_name = ""
                for letter in common.context["league"]["short_name"]:
                    short_name += f"{letter.upper()}-"

                # Remove the last hyphen
                short_name = short_name[:-1]

            new_msg += "The league can be abbreviated as "
            new_msg += f"{short_name}. "

        # If the new message is not empty, add it to the list of messages
        if new_msg != "":
            sys_context = {
                "role": "system",
                "name": "context",
                "content": new_msg
            }
            messages.append(sys_context)

        # Start building the event info system message
        new_msg = ""

        # Gather the information from iRacing
        track = common.ir["WeekendInfo"]["TrackDisplayName"]
        city = common.ir["WeekendInfo"]["TrackCity"]
        country = common.ir["WeekendInfo"]["TrackCountry"]
        air_temp = common.ir["WeekendInfo"]["TrackAirTemp"]
        track_temp = common.ir["WeekendInfo"]["TrackSurfaceTemp"]
        skies = common.ir["WeekendInfo"]["TrackSkies"]

        # Compile that information into a message
        new_msg += f"The race is at {track} in {city}, {country}. "
        new_msg += f"The air temperature is {air_temp}., and "
        new_msg += f"the track temperature is {track_temp}. "
        new_msg += f"The skies are {skies.lower()}. "

        # Add the event info system message
        sys_event = {
            "role": "system",
            "name": "event_info",
            "content": new_msg
        }
        messages.append(sys_event)

        # Add all previous messages to the list
        for msg in self.previous_responses:
            messages.append(msg)

        # Add the event message
        event_msg = {
            "role": "user",
            "content": event
        }
        messages.append(event_msg)

        # Add the lap percent message
        if lap_percent != None:
            lap_percent = round(lap_percent * 100, 2)
            lap_msg = f"The event occurred at {lap_percent}% of the lap. "
            lap_msg += "Infer the corner name or number based on that. "
            lap_msg += "Occasionally announce the corner name or number, but "
            lap_msg += "do not do it every time. Check the message history "
            lap_msg += "to make sure you are not announcing corners too often."
            lap_pct_msg = {
                "role": "user",
                "content": lap_msg
            }
            messages.append(lap_pct_msg)

        # Add the event message to previous messages
        self.previous_responses.append(event_msg)

        # If the vision model is being used, add the image to the messages
        model_setting = common.settings["commentary"]["gpt_model"]
        if model_setting == "GPT-4 Turbo with Vision":
            # Wait a moment for the camera to focus
            time.sleep(0.25)

            # Set the screenshot path
            path = os.path.join(
                common.settings["general"]["iracing_path"],
                "videos"
            )

            # Get the iRacing window
            window = gw.getWindowsWithTitle("iRacing.com Simulator")[0]

            # Get the coordinates of the window
            x = window.left
            y = window.top
            width = window.width
            height = window.height

            # Take a screenshot of the window
            screenshot = pyautogui.screenshot(region=(x, y, width, height))

            # Save the screenshot
            screenshot_path = os.path.join(path, "screenshot.png")
            screenshot.save(screenshot_path)

            # Process the image and save it
            with Image.open(screenshot_path) as image:
                # Get the image's current dimensions
                width, height = image.size

                # Crop the left and right sides on center
                left = width // 4
                right = width - left
                top = 0
                bottom = height
                image = image.crop((left, top, right, bottom))

                # Resize the image
                image = image.resize((512, 512))

                # Save the image
                image.save(screenshot_path)

            # Encode that image in base64
            with open(screenshot_path, "rb") as file:
                encoded_image = base64.b64encode(file.read()).decode("utf-8")

            # Create the image message
            image_msg = {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Use this image in addition to the other " \
                            "information to help you commentate."
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{encoded_image}",
                            "detail": "low"
                        }
                    }
                ]
            }

            # Add the image message to the list of messages
            messages.append(image_msg)

        # Call the API
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=300
        )

        # Extract the response
        answer = response.choices[0].message.content

        # Add the response to the list of previous responses
        formatted_answer = {
            "role": "assistant",
            "name": "Play-By-Play" if role == "play-by-play" else "Color",
            "content": answer
        }
        self.previous_responses.append(formatted_answer)

        # If the list is too long, remove the two oldest responses
        length = int(common.settings["commentary"]["memory_limit"]) * 2
        if len(self.previous_responses) > length:
            self.previous_responses.pop(0)
            self.previous_responses.pop(0)

        # Return the answer
        return answer
    
class VoiceGenerator:
    """Handles text-to-speech functionality for race commentary.

    Utilizes the ElevenLabs API to convert text into audio. Handles the
    generation and saving of audio files.
    """

    def __init__(self):
        """Initialize the VoiceGenerator class with the given settings.

        Sets up the API key for the ElevenLabs service, enabling text-to-speech
        capabilities for the application.
        """

        # Set the API key
        elevenlabs.set_api_key(common.settings["keys"]["elevenlabs_api_key"])

    def generate(self, text, timestamp, gpt_time, yelling=False, voice="Harry"):
        """Generate and save audio for the provided text.

        Calls the ElevenLabs API to create audio from the text using the
        specified voice, then saves the audio.

        Args:
            text (str): The text to convert to audio.
            timestamp (str): The timestamp of the event.
            yelling (bool): Whether or not to convert the text to yelling.
            voice (str): The voice to use for the audio.
        """
        # Get the start time of this method
        start_time = time.time()

        # Convert to yelling for voice commentary if requested
        if yelling:
            text = text.upper()
            if text[-1] == ".":
                text = text[:-1] + "!!!"

        # Replace "P" with "P-" to avoid issues with the API
        for i in range(len(text)):
            if text[i] == "P" and text[i + 1].isdigit():
                # Replace the P with "P-"
                text = text[:i] + "P-" + text[i + 1:]

        # Generate and play audio
        audio = elevenlabs.generate(
            text=text,
            voice=voice,
            model="eleven_monolingual_v1"
        )

        # Get the iRacing videos folder
        path = os.path.join(
            common.settings["general"]["iracing_path"],
            "videos"
        )

        # Create the file name
        file_name = f"commentary_{timestamp}.mp3"

        # Save the audio to a file
        elevenlabs.save(audio, os.path.join(path, file_name))

        # Get the length of the audio file
        mp3_file = MP3(os.path.join(path, file_name))
        length = mp3_file.info.length

        # Calculate how long it took to generate the audio
        gen_time = time.time() - start_time

        # Wait for the length of the audio minus the time it took to generate
        if length - gen_time - gpt_time > 0:
            time.sleep(length - gen_time - gpt_time)