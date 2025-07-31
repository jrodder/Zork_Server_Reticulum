# zork_server.py
# A very simple, bare-bones LXMF server for a multi-user, text-based adventure game.
# This code is heavily commented to be easy to understand for learning purposes.

import RNS
import LXMF
import time
import threading

# --- Game Data and State ---
# This is the simplest possible way to represent the game world.
# It's a dictionary where each key is a "room" and the value is another
# dictionary containing the room's description and possible exits.
GAME_WORLD = {
    'start': {
        'desc': "You are in a dusty, square room. A single lightbulb hangs from the ceiling. There is a wooden door to the north.",
        'exits': {'north': 'hallway'}
    },
    'hallway': {
        'desc': "You are in a long, narrow hallway. The walls are cold stone. To the south is the room you started in. To the east is a heavy iron door.",
        'exits': {'south': 'start', 'east': 'treasury'}
    },
    'treasury': {
        'desc': "You've found the treasury! Piles of gold and jewels glitter in the dim light. A door leads west back to the hallway.",
        'exits': {'west': 'hallway'}
    }
}

# This dictionary will store the state of each player.
# The key will be the player's unique LXMF address (as a string).
# The value will be the 'room' key from GAME_WORLD where the player currently is.
# This is how we achieve persistence and support multiple players.
player_states = {}

# --- Reticulum and LXMF Setup ---

# This part is standard for any Reticulum application.
# We first initialize Reticulum.
RNS.Reticulum()

# Define a name for our LXMF endpoint. This is like a username for our application.
# The destination will be created based on this name.
APP_NAME = "zork_game"

# Create a Reticulum Identity. This is the cryptographic identity of our server.
# We load from a file to maintain the same address across restarts.
identity_file = "zork_server_identity"
if RNS.Identity.from_file(identity_file):
    identity = RNS.Identity.from_file(identity_file)
    print(f"Loaded existing identity from {identity_file}")
else:
    identity = RNS.Identity()
    identity.to_file(identity_file)
    print(f"Created new identity and saved to {identity_file}")

# Create the LXMF endpoint (a "destination") for our server.
# This is the address that clients will send messages to.
destination = RNS.Destination(
    identity,
    RNS.Destination.IN,
    RNS.Destination.SINGLE,
    APP_NAME
)

# Create LXMF router to handle messages
router = LXMF.LXMRouter(storagepath="./lxmf_storage")

# Register our destination with the router so it can receive messages
# This returns our LXMF destination that we'll use as the source for outbound messages
lxmf_destination = router.register_delivery_identity(identity)


# --- Message Handling ---

def message_received(message):
    """
    This function is the heart of our server. It gets called automatically
    by LXMF every time a new message arrives at our destination.
    """
    # Get the sender's address. This is how we know who sent the message.
    # We convert it to a hex string to use it as a dictionary key.
    sender_address = message.source_hash.hex()

    # Get the content of the message (what the player typed).
    # We convert it to lowercase and remove leading/trailing whitespace.
    command = message.content.decode('utf-8').lower().strip()

    print(f"Received command '{command}' from {RNS.prettyhexrep(message.source_hash)}")

    # --- Game Logic ---

    # Check if this is a new player. If their address isn't in our state
    # dictionary, we add them and place them in the 'start' room.
    if sender_address not in player_states:
        player_states[sender_address] = 'start'
        print(f"New player joined: {RNS.prettyhexrep(message.source_hash)}")

    # Get the player's current room from the state dictionary.
    current_room_key = player_states[sender_address]
    current_room = GAME_WORLD[current_room_key]

    # Default response if the command is not understood.
    response_text = "I don't understand that command."

    # Parse the player's command.
    parts = command.split()
    if len(parts) > 0:
        verb = parts[0]

        if verb == 'look':
            response_text = current_room['desc']

        elif verb == 'go' and len(parts) > 1:
            direction = parts[1]
            if direction in current_room['exits']:
                # The move is valid. Update the player's state.
                new_room_key = current_room['exits'][direction]
                player_states[sender_address] = new_room_key
                # Set the response to the description of the new room.
                response_text = GAME_WORLD[new_room_key]['desc']
            else:
                response_text = "You can't go that way."

        elif verb == 'quit':
            response_text = "Thanks for playing!"
            # Optionally, you could remove the player from the state here.
            # del player_states[sender_address]

    # --- Sending the Response ---

    print(f"Game response for {RNS.prettyhexrep(message.source_hash)}: \"{response_text}\"")
    
    # Send the response back to the player
    try:
        # Create a destination object for the sender to reply to
        # We need to recall their identity from their source hash
        sender_identity = RNS.Identity.recall(message.source_hash)
        if sender_identity is not None:
            # Create an outbound destination for the sender
            reply_destination = RNS.Destination(
                sender_identity,
                RNS.Destination.OUT,
                RNS.Destination.SINGLE,
                "lxmf", "delivery"
            )
            
            # Create the LXMF response message
            response_message = LXMF.LXMessage(
                reply_destination,          # Where the message is going (the player)
                lxmf_destination,          # Where it's coming from (our server)
                response_text,             # The game response text
                desired_method=LXMF.LXMessage.DIRECT  # Send directly if possible
            )
            
            # Send the message through the router
            router.handle_outbound(response_message)
            print(f"Response sent to {RNS.prettyhexrep(message.source_hash)}")
            
        else:
            print(f"Could not recall identity for {RNS.prettyhexrep(message.source_hash)}, trying alternative method...")
            
            # Alternative method: Try using the message source directly
            # This works if the incoming message has the sender's full destination info
            if hasattr(message, 'destination') and message.destination is not None:
                # Create response message using the original message's destination info
                response_message = LXMF.LXMessage(
                    message.destination,       # Reply to the original sender's destination
                    lxmf_destination,         # From our server
                    response_text,            # The game response
                    desired_method=LXMF.LXMessage.OPPORTUNISTIC  # Try opportunistic delivery
                )
                router.handle_outbound(response_message)
                print(f"Response sent via alternative method to {RNS.prettyhexrep(message.source_hash)}")
            else:
                print(f"Cannot send response - no valid destination found for {RNS.prettyhexrep(message.source_hash)}")
            
    except Exception as e:
        print(f"Error sending response to {RNS.prettyhexrep(message.source_hash)}: {e}")
        # Fall back to just printing the response if sending fails


# --- Main Program Loop ---

def main():
    # Tell LXMF to call our `message_received` function for every new message.
    router.register_delivery_callback(message_received)

    print("Zork Server Initialized.")
    print(f"Listening for messages at: {RNS.prettyhexrep(destination.hash)}")

    # This loop keeps the program running and listening for messages.
    # It will run forever until you stop it with Ctrl+C.
    while True:
        time.sleep(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Shutting down server.")
        # This is a clean way to exit.
        # It's important to call RNS.Reticulum.exit() to allow Reticulum
        # to shut down its background processes gracefully.
        RNS.exit()