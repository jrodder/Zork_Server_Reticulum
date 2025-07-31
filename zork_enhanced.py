# Enhanced Zork-like LXMF Game Server
# A comprehensive text-based adventure game with inventory, multiple verbs, and rich gameplay

import RNS
import LXMF
import time
import threading
import json
import copy

# --- Game World Data Structures ---

class GameItem:
    def __init__(self, name, description, can_take=True, aliases=None):
        self.name = name
        self.description = description
        self.can_take = can_take
        self.aliases = aliases or []
        self.hidden = False
    
    def matches(self, text):
        """Check if the given text matches this item"""
        return text.lower() in [self.name.lower()] + [alias.lower() for alias in self.aliases]

class GameRoom:
    def __init__(self, name, description, exits=None, items=None):
        self.name = name
        self.description = description
        self.exits = exits or {}
        self.items = items or []
        self.visited = False
    
    def get_item(self, item_name):
        """Get an item from this room by name"""
        for item in self.items:
            if item.matches(item_name):
                return item
        return None
    
    def remove_item(self, item):
        """Remove an item from this room"""
        if item in self.items:
            self.items.remove(item)
            return True
        return False
    
    def add_item(self, item):
        """Add an item to this room"""
        self.items.append(item)

class Player:
    def __init__(self, address):
        self.address = address
        self.current_room = 'entrance_hall'
        self.inventory = []
        self.max_inventory = 10
        self.score = 0
        self.moves = 0
    
    def get_item(self, item_name):
        """Get an item from player's inventory by name"""
        for item in self.inventory:
            if item.matches(item_name):
                return item
        return None
    
    def add_item(self, item):
        """Add an item to player's inventory"""
        if len(self.inventory) < self.max_inventory:
            self.inventory.append(item)
            return True
        return False
    
    def remove_item(self, item):
        """Remove an item from player's inventory"""
        if item in self.inventory:
            self.inventory.remove(item)
            return True
        return False

# --- Game World Definition ---

# Create game items
GAME_ITEMS = {
    'brass_lantern': GameItem('brass lantern', 'A brass lantern. It appears to be switched off.', True, ['lantern', 'lamp']),
    'leaflet': GameItem('leaflet', 'A small leaflet with instructions for playing this game.', True, ['pamphlet', 'paper']),
    'wooden_door': GameItem('wooden door', 'A sturdy wooden door with iron hinges.', False, ['door']),
    'mailbox': GameItem('mailbox', 'A small mailbox. It appears to be closed.', False, ['box']),
    'sword': GameItem('elvish sword', 'An ancient elvish sword with runes carved into the blade.', True, ['sword', 'blade']),
    'rope': GameItem('rope', 'A sturdy rope, about 20 feet long.', True),
    'chest': GameItem('treasure chest', 'A heavy wooden chest bound with iron.', False, ['chest']),
    'key': GameItem('brass key', 'A small brass key with intricate engravings.', True, ['key']),
    'crystal': GameItem('crystal', 'A glowing crystal that pulses with inner light.', True, ['gem']),
}

# Create game rooms with items
GAME_WORLD = {
    'entrance_hall': GameRoom(
        'Entrance Hall',
        'You are standing in an open field west of a white house, with a boarded front door. There is a small mailbox here.',
        {'north': 'forest_path', 'south': 'garden', 'east': 'living_room'},
        [GAME_ITEMS['mailbox'], GAME_ITEMS['leaflet']]
    ),
    'living_room': GameRoom(
        'Living Room',
        'You are in the living room. There is a doorway to the west and a wooden staircase leading upward.',
        {'west': 'entrance_hall', 'up': 'attic'},
        [GAME_ITEMS['brass_lantern']]
    ),
    'attic': GameRoom(
        'Attic',
        'You are in the attic. The room is dimly lit by small windows. There is a ladder leading down.',
        {'down': 'living_room'},
        [GAME_ITEMS['rope']]
    ),
    'forest_path': GameRoom(
        'Forest Path',
        'You are on a winding forest path. Dense trees surround you on both sides. The path continues north and south.',
        {'north': 'clearing', 'south': 'entrance_hall'},
        []
    ),
    'clearing': GameRoom(
        'Forest Clearing',
        'You are in a small clearing surrounded by tall trees. Sunlight filters through the canopy above.',
        {'south': 'forest_path', 'east': 'cave_entrance'},
        [GAME_ITEMS['sword']]
    ),
    'cave_entrance': GameRoom(
        'Cave Entrance',
        'You stand before the mouth of a dark cave. The entrance is partially blocked by fallen rocks.',
        {'west': 'clearing', 'enter': 'cave'},
        []
    ),
    'cave': GameRoom(
        'Dark Cave',
        'You are in a dark cave. Without light, you can barely see anything. There might be passages leading deeper.',
        {'out': 'cave_entrance', 'north': 'treasure_room'},
        []
    ),
    'treasure_room': GameRoom(
        'Treasure Room',
        'You have discovered a hidden treasure room! Ancient treasures glitter in the dim light.',
        {'south': 'cave'},
        [GAME_ITEMS['chest'], GAME_ITEMS['key'], GAME_ITEMS['crystal']]
    ),
    'garden': GameRoom(
        'Garden',
        'You are in a small garden behind the house. Flowers bloom around a small fountain.',
        {'north': 'entrance_hall'},
        []
    )
}

# --- Player Management ---
players = {}  # Dictionary to store player objects by address

def get_player(address):
    """Get or create a player object"""
    if address not in players:
        players[address] = Player(address)
        print(f"New player created: {RNS.prettyhexrep(bytes.fromhex(address))}")
    return players[address]

# --- Game Commands ---

def cmd_look(player, args):
    """Look around the current room or at a specific item"""
    current_room = GAME_WORLD[player.current_room]
    
    if not args:
        # Look around the room
        response = f"{current_room.name}\n{current_room.description}"
        
        # List visible items
        if current_room.items:
            visible_items = [item for item in current_room.items if not item.hidden]
            if visible_items:
                response += "\n\nYou can see:"
                for item in visible_items:
                    response += f"\n  {item.name}"
        
        # List exits
        if current_room.exits:
            response += f"\n\nExits: {', '.join(current_room.exits.keys())}"
        
        current_room.visited = True
        return response
    else:
        # Look at specific item
        item_name = ' '.join(args)
        
        # Check room first
        item = current_room.get_item(item_name)
        if not item:
            # Check inventory
            item = player.get_item(item_name)
        
        if item:
            return item.description
        else:
            return f"You don't see any '{item_name}' here."

def cmd_take(player, args):
    """Take an item from the current room"""
    if not args:
        return "Take what?"
    
    item_name = ' '.join(args)
    current_room = GAME_WORLD[player.current_room]
    item = current_room.get_item(item_name)
    
    if not item:
        return f"There is no '{item_name}' here."
    
    if not item.can_take:
        return f"You can't take the {item.name}."
    
    if len(player.inventory) >= player.max_inventory:
        return "Your inventory is full!"
    
    current_room.remove_item(item)
    player.add_item(item)
    player.score += 5
    return f"Taken: {item.name}."

def cmd_drop(player, args):
    """Drop an item from inventory"""
    if not args:
        return "Drop what?"
    
    item_name = ' '.join(args)
    item = player.get_item(item_name)
    
    if not item:
        return f"You don't have any '{item_name}'."
    
    current_room = GAME_WORLD[player.current_room]
    player.remove_item(item)
    current_room.add_item(item)
    return f"Dropped: {item.name}."

def cmd_inventory(player, args):
    """Show player's inventory"""
    if not player.inventory:
        return "You are carrying nothing."
    
    response = "You are carrying:"
    for item in player.inventory:
        response += f"\n  {item.name}"
    return response

def cmd_go(player, args):
    """Move to another room"""
    if not args:
        return "Go where?"
    
    direction = args[0].lower()
    current_room = GAME_WORLD[player.current_room]
    
    if direction not in current_room.exits:
        return f"You can't go {direction} from here."
    
    new_room_key = current_room.exits[direction]
    player.current_room = new_room_key
    player.moves += 1
    
    # Automatically look around the new room
    return cmd_look(player, [])

def cmd_examine(player, args):
    """Examine an item closely (alias for look)"""
    return cmd_look(player, args)

def cmd_score(player, args):
    """Show player's score and statistics"""
    return f"Score: {player.score} points\nMoves: {player.moves}\nItems carried: {len(player.inventory)}/{player.max_inventory}"

def cmd_help(player, args):
    """Show available commands"""
    return """Available commands:
look [item] - Look around or examine an item
take <item> - Take an item
drop <item> - Drop an item from your inventory
go <direction> - Move in a direction (north, south, east, west, up, down, enter, out)
inventory (i) - Show your inventory
examine <item> - Examine an item closely
score - Show your score and statistics
help - Show this help message
quit - Quit the game

You can use abbreviated forms: l (look), t (take), d (drop), i (inventory), x (examine)"""

def cmd_quit(player, args):
    """Quit the game"""
    return f"Thanks for playing! Final score: {player.score} points in {player.moves} moves."

# Command mapping
COMMANDS = {
    'look': cmd_look, 'l': cmd_look,
    'take': cmd_take, 't': cmd_take, 'get': cmd_take,
    'drop': cmd_drop, 'd': cmd_drop,
    'go': cmd_go, 'move': cmd_go,
    'inventory': cmd_inventory, 'i': cmd_inventory,
    'examine': cmd_examine, 'x': cmd_examine,
    'score': cmd_score,
    'help': cmd_help, '?': cmd_help,
    'quit': cmd_quit, 'exit': cmd_quit,
}

# --- LXMF Setup (same as before) ---

RNS.Reticulum()
APP_NAME = "zork_enhanced"

# Load or create identity
identity_file = "zork_server_identity"
if RNS.Identity.from_file(identity_file):
    identity = RNS.Identity.from_file(identity_file)
    print(f"Loaded existing identity from {identity_file}")
else:
    identity = RNS.Identity()
    identity.to_file(identity_file)
    print(f"Created new identity and saved to {identity_file}")

# Create destination
destination = RNS.Destination(
    identity,
    RNS.Destination.IN,
    RNS.Destination.SINGLE,
    APP_NAME
)

# Create LXMF router
router = LXMF.LXMRouter(storagepath="./lxmf_storage")
lxmf_destination = router.register_delivery_identity(identity)

def message_received(message):
    """Handle incoming game commands"""
    sender_address = message.source_hash.hex()
    command_text = message.content.decode('utf-8').strip()
    
    print(f"Received command '{command_text}' from {RNS.prettyhexrep(message.source_hash)}")
    
    # Get or create player
    player = get_player(sender_address)
    
    # Parse command
    parts = command_text.lower().split()
    if not parts:
        response_text = "Please enter a command. Type 'help' for available commands."
    else:
        verb = parts[0]
        args = parts[1:]
        
        if verb in COMMANDS:
            try:
                response_text = COMMANDS[verb](player, args)
            except Exception as e:
                response_text = f"Error processing command: {e}"
                print(f"Command error: {e}")
        else:
            response_text = f"I don't understand '{verb}'. Type 'help' for available commands."
    
    # Send response
    print(f"Sending game response to {RNS.prettyhexrep(message.source_hash)}: \"{response_text[:50]}...\"")
    
    try:
        sender_identity = RNS.Identity.recall(message.source_hash)
        if sender_identity is not None:
            reply_destination = RNS.Destination(
                sender_identity,
                RNS.Destination.OUT,
                RNS.Destination.SINGLE,
                "lxmf", "delivery"
            )
            
            response_message = LXMF.LXMessage(
                reply_destination,
                lxmf_destination,
                response_text,
                desired_method=LXMF.LXMessage.DIRECT
            )
            
            router.handle_outbound(response_message)
            print(f"Response sent to {RNS.prettyhexrep(message.source_hash)}")
            
        else:
            print(f"Could not recall identity for {RNS.prettyhexrep(message.source_hash)}, trying alternative...")
            if hasattr(message, 'destination') and message.destination is not None:
                response_message = LXMF.LXMessage(
                    message.destination,
                    lxmf_destination,
                    response_text,
                    desired_method=LXMF.LXMessage.OPPORTUNISTIC
                )
                router.handle_outbound(response_message)
                print(f"Response sent via alternative method")
            else:
                print(f"Cannot send response - no valid destination found")
                
    except Exception as e:
        print(f"Error sending response: {e}")

def main():
    router.register_delivery_callback(message_received)
    
    print("Enhanced Zork Server Initialized.")
    print(f"Listening for messages at: {RNS.prettyhexrep(destination.hash)}")
    print("Game features:")
    print("- Multiple rooms to explore")
    print("- Items to collect and use")
    print("- Player inventory system")
    print("- Score tracking")
    print("- Multiple game commands")
    
    while True:
        time.sleep(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Shutting down Enhanced Zork server.")
        RNS.Reticulum.exit()