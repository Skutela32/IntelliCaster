import time


class Events:
    def __init__(self):
        # Initialize the events list and id counter
        self.events = []
        self.id_counter = 0

    def _add_event(self, type, description, focus=None):
        """Add a new event to the list.
        
        Args:
            type (str): The type of event
            description (str): A description of the event
            focus (str): The driver that the event is focused on
        """
        # Create a new event
        new_event = {
            "id": self.id_counter,
            "type": type,
            "description": description,
            "focus": focus,
            "timestamp": time.time()
        }

        # Add the event to the list
        self.events.insert(0, new_event)

        # Increment the id counter
        self.id_counter += 1

    def _remove_event(self, id):
        """Remove an event from the list.
        
        Args:
            id (int): The id of the event to remove
        """
        # Remove the event from the list
        for event in self.events:
            if event["id"] == id:
                self.events.remove(event)