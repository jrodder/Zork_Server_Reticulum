# Scriptable Zork-like LXMF Game Engine
# Advanced game framework with event system, scripting, and dynamic interactions

import RNS
import LXMF
import time
import threading
import json
import copy
import re
from typing import Dict, List, Any, Optional, Callable

# --- Event System ---

class GameEvent:
    """Represents a game event that can be triggered"""
    def __init__(self, event_type: str, data: Dict[str, Any] = None):
        self.event_type = event_type
        self.data = data or {}
        self.timestamp = time.time()

class EventHandler:
    """Base class for event handlers"""
    def __init__(self, conditions: Dict[str, Any] = None):
        self.conditions = conditions or {}
    
    def can_handle(self, event: GameEvent, game_state: 'GameState') -> bool:
        """Check if this handler can handle the given event"""
        # Check event type
        if 'event_type' in self.conditions:
            if event.event_type != self.conditions['event_type']:
                return False
        
        # Check player conditions
        if 'player_has_item' in self.conditions:
            player = game_state.get_player(event.data.get('player_address'))
            if not player or not player.has_item(self.conditions['player_has_item']):
                return False
        
        # Check room conditions
        if 'player_in_room' in self.conditions:
            player = game_state.get_player(event.data.get('player_address'))
            if not player or player.current_room != self.conditions['player_in_room']:
                return False
        
        # Check game flags
        if 'flag_set' in self.conditions:
            flag_name = self.conditions['flag_set']
            if not game_state.get_flag(flag_name):
                return False
        
        return True
    
    def handle(self, event: GameEvent, game_state: 'GameState') -> str:
        """Handle the event and return response text"""
        return "Event handled."

class ScriptHandler(EventHandler):
    """Handler that executes Python code snippets"""
    def __init__(self, conditions: Dict[str, Any] = None, script: str = ""):
        super().__init__(conditions)
        self.script = script
    
    def handle(self, event: GameEvent, game_state: 'GameState') -> str:
        """Execute the script with access to game state"""
        # Create safe execution environment
        safe_globals = {
            'event': event,
            'game_state': game_state,
            'player': game_state.get_player(event.data.get('player_address')),
        }
        
        try:
            # Execute the script
            exec(self.script, safe_globals)
            return safe_globals.get('response', "Script executed.")
        except Exception as e:
            print(f"Script execution error: {e}")
            return "Something mysterious happens..."

# --- Enhanced Game Objects ---

class GameItem:
    def __init__(self, name: str, description: str, can_take: bool = True, 
                 aliases: List[str] = None, properties: Dict[str, Any] = None,
                 verb_interactions: Dict[str, Dict[str, Any]] = None):
        self.name = name
        self.description = description
        self.can_take = can_take
        self.aliases = aliases or []
        self.properties = properties or {}
        self.verb_interactions = verb_interactions or {}
        self.hidden = False
        self.event_handlers = []
    
    def matches(self, text: str) -> bool:
        return text.lower() in [self.name.lower()] + [alias.lower() for alias in self.aliases]
    
    def get_property(self, prop_name: str) -> Any:
        return self.properties.get(prop_name)
    
    def set_property(self, prop_name: str, value: Any):
        self.properties[prop_name] = value
    
    def add_event_handler(self, handler: EventHandler):
        self.event_handlers.append(handler)
    
    def can_perform_verb(self, verb: str) -> bool:
        """Check if this item can respond to the given verb"""
        return verb.lower() in self.verb_interactions
    
    def get_verb_interaction(self, verb: str) -> Optional[Dict[str, Any]]:
        """Get the interaction definition for a verb"""
        return self.verb_interactions.get(verb.lower())

class GameRoom:
    def __init__(self, name: str, description: str, exits: Dict[str, str] = None, 
                 items: List[GameItem] = None, properties: Dict[str, Any] = None):
        self.name = name
        self.description = description
        self.exits = exits or {}
        self.items = items or []
        self.properties = properties or {}
        self.visited = False
        self.event_handlers = []
    
    def get_item(self, item_name: str) -> Optional[GameItem]:
        for item in self.items:
            if item.matches(item_name):
                return item
        return None
    
    def remove_item(self, item: GameItem) -> bool:
        if item in self.items:
            self.items.remove(item)
            return True
        return False
    
    def add_item(self, item: GameItem):
        self.items.append(item)
    
    def get_property(self, prop_name: str) -> Any:
        return self.properties.get(prop_name)
    
    def set_property(self, prop_name: str, value: Any):
        self.properties[prop_name] = value
    
    def add_event_handler(self, handler: EventHandler):
        self.event_handlers.append(handler)
    
    def get_exit_description(self, direction: str) -> Optional[str]:
        """Get custom description for an exit"""
        return self.properties.get(f'exit_{direction}_desc')

class Player:
    def __init__(self, address: str):
        self.address = address
        self.current_room = 'entrance_hall'
        self.inventory = []
        self.max_inventory = 10
        self.score = 0
        self.moves = 0
        self.properties = {}  # Custom player properties
    
    def get_item(self, item_name: str) -> Optional[GameItem]:
        for item in self.inventory:
            if item.matches(item_name):
                return item
        return None
    
    def has_item(self, item_name: str) -> bool:
        return self.get_item(item_name) is not None
    
    def add_item(self, item: GameItem) -> bool:
        if len(self.inventory) < self.max_inventory:
            self.inventory.append(item)
            return True
        return False
    
    def remove_item(self, item: GameItem) -> bool:
        if item in self.inventory:
            self.inventory.remove(item)
            return True
        return False
    
    def get_property(self, prop_name: str) -> Any:
        return self.properties.get(prop_name)
    
    def set_property(self, prop_name: str, value: Any):
        self.properties[prop_name] = value

# --- Game State Management ---

class GameState:
    def __init__(self):
        self.players = {}
        self.rooms = {}
        self.items = {}
        self.global_flags = {}  # Global game state flags
        self.event_handlers = []  # Global event handlers
        self.starting_room = 'entrance_hall'  # Default starting room
    
    def get_player(self, address: str) -> Optional[Player]:
        if address not in self.players:
            player = Player(address)
            player.current_room = self.starting_room  # Use configured starting room
            self.players[address] = player
            self.trigger_event(GameEvent('player_joined', {'player_address': address}))
        return self.players[address]
    
    def get_room(self, room_id: str) -> Optional[GameRoom]:
        return self.rooms.get(room_id)
    
    def get_item(self, item_id: str) -> Optional[GameItem]:
        return self.items.get(item_id)
    
    def set_flag(self, flag_name: str, value: Any = True):
        """Set a global game flag"""
        old_value = self.global_flags.get(flag_name)
        self.global_flags[flag_name] = value
        if old_value != value:
            self.trigger_event(GameEvent('flag_changed', {
                'flag_name': flag_name,
                'old_value': old_value,
                'new_value': value
            }))
    
    def get_flag(self, flag_name: str) -> Any:
        """Get a global game flag"""
        return self.global_flags.get(flag_name, False)
    
    def add_event_handler(self, handler: EventHandler):
        """Add a global event handler"""
        self.event_handlers.append(handler)
    
    def trigger_event(self, event: GameEvent) -> List[str]:
        """Trigger an event and return all responses"""
        responses = []
        
        # Check global handlers
        for handler in self.event_handlers:
            if handler.can_handle(event, self):
                response = handler.handle(event, self)
                if response:
                    responses.append(response)
        
        # Check room handlers
        if 'player_address' in event.data:
            player = self.get_player(event.data['player_address'])
            if player:
                room = self.get_room(player.current_room)
                if room:
                    for handler in room.event_handlers:
                        if handler.can_handle(event, self):
                            response = handler.handle(event, self)
                            if response:
                                responses.append(response)
        
        return responses

# --- Game Definition System ---

class GameBuilder:
    """Build games from configuration data"""
    
    @staticmethod
    def load_from_json(filename: str) -> GameState:
        """Load a game from JSON configuration"""
        with open(filename, 'r') as f:
            config = json.load(f)
        
        game_state = GameState()
        
        # Load items
        for item_id, item_data in config.get('items', {}).items():
            # Skip comment fields
            if item_id.startswith('_'):
                continue
            
            item = GameItem(
                name=item_data['name'],
                description=item_data['description'],
                can_take=item_data.get('can_take', True),
                aliases=item_data.get('aliases', []),
                properties=item_data.get('properties', {}),
                verb_interactions=item_data.get('verb_interactions', {})
            )
            game_state.items[item_id] = item
        
        # Load rooms
        for room_id, room_data in config.get('rooms', {}).items():
            # Skip comment fields
            if room_id.startswith('_'):
                continue
                
            # Get items for this room
            room_items = []
            for item_id in room_data.get('items', []):
                if item_id in game_state.items:
                    room_items.append(game_state.items[item_id])
            
            room = GameRoom(
                name=room_data['name'],
                description=room_data['description'],
                exits=room_data.get('exits', {}),
                items=room_items,
                properties=room_data.get('properties', {})
            )
            game_state.rooms[room_id] = room
        
        # Load event handlers
        for handler_data in config.get('event_handlers', []):
            if handler_data['type'] == 'script':
                handler = ScriptHandler(
                    conditions=handler_data.get('conditions', {}),
                    script=handler_data['script']
                )
                
                # Add to appropriate scope
                scope = handler_data.get('scope', 'global')
                if scope == 'global':
                    game_state.add_event_handler(handler)
                elif scope.startswith('room:'):
                    room_id = scope.split(':', 1)[1]
                    if room_id in game_state.rooms:
                        game_state.rooms[room_id].add_event_handler(handler)
                elif scope.startswith('item:'):
                    item_id = scope.split(':', 1)[1]
                    if item_id in game_state.items:
                        game_state.items[item_id].add_event_handler(handler)
        
        # Set initial flags
        for flag_name, flag_value in config.get('initial_flags', {}).items():
            game_state.set_flag(flag_name, flag_value)
        
        # Find and set the starting room
        starting_room = None
        for room_id, room in game_state.rooms.items():
            if room.get_property('starting_room'):
                starting_room = room_id
                break
        
        # If no starting room specified, use the first room or default
        if not starting_room:
            if game_state.rooms:
                starting_room = list(game_state.rooms.keys())[0]
            else:
                starting_room = 'entrance_hall'  # fallback default
        
        game_state.starting_room = starting_room
        return game_state

# --- Enhanced Command System ---

class GameEngine:
    def __init__(self, game_state: GameState):
        self.game_state = game_state
        self.commands = {
            'look': self.cmd_look, 'l': self.cmd_look,
            'take': self.cmd_take, 't': self.cmd_take, 'get': self.cmd_take,
            'drop': self.cmd_drop, 'd': self.cmd_drop,
            'go': self.cmd_go, 'move': self.cmd_go,
            'inventory': self.cmd_inventory, 'i': self.cmd_inventory,
            'examine': self.cmd_examine, 'x': self.cmd_examine,
            'use': self.cmd_use, 'u': self.cmd_use,
            'unlock': self.cmd_unlock,
            'open': self.cmd_open,
            'close': self.cmd_close,
            'score': self.cmd_score,
            'help': self.cmd_help, '?': self.cmd_help,
            'quit': self.cmd_quit, 'exit': self.cmd_quit,
        }
        
        # Define verb categories for verb-object interactions
        self.verb_categories = {
            'physical': ['push', 'pull', 'throw', 'break', 'shake', 'turn', 'move_object'],
            'sensory': ['read', 'listen', 'smell', 'taste', 'touch'],
            'tool_usage': ['cut', 'dig', 'light', 'extinguish'],
            'magic': ['cast', 'enchant', 'bless', 'curse'],
            'social': ['talk', 'ask', 'tell', 'show']
        }
        
        # All verbs that can be used on objects (excluding movement commands)
        self.object_verbs = []
        for category in self.verb_categories.values():
            self.object_verbs.extend(category)
        
        # Common prepositions to strip from commands for natural language
        self.prepositions = {
            'at', 'to', 'on', 'in', 'into', 'from', 'with', 'against', 'upon', 
            'onto', 'under', 'over', 'through', 'around', 'behind', 'beside',
            'near', 'by', 'across', 'along', 'above', 'below', 'within'
        }
    
    def parse_command_with_prepositions(self, command_text: str) -> tuple:
        """Parse a command, removing prepositions for natural language support"""
        parts = command_text.lower().split()
        if not parts:
            return None, []
        
        verb = parts[0]
        remaining_words = parts[1:]
        
        # Handle special verb+preposition combinations that should be preserved
        special_combinations = {
            'put': ['in', 'on', 'into', 'onto', 'under'],
            'throw': ['at', 'to'],
            'look': ['at', 'in', 'under', 'behind'],
            'listen': ['to'],
            'talk': ['to', 'with'],
            'give': ['to'],
            'show': ['to']
        }
        
        # For certain verbs, preserve meaningful prepositions
        if verb in special_combinations and len(remaining_words) >= 2:
            # Check if there's a meaningful preposition to preserve context
            for i, word in enumerate(remaining_words):
                if word in special_combinations[verb]:
                    # Keep structure: verb + object1 + preposition + object2
                    # e.g., "put key in chest" -> verb="put", args=["key", "in", "chest"]
                    return verb, remaining_words
        
        # For most cases, just remove prepositions for cleaner parsing
        filtered_words = []
        for word in remaining_words:
            if word not in self.prepositions:
                filtered_words.append(word)
        
        return verb, filtered_words
    
    def process_command(self, player_address: str, command_text: str) -> str:
        """Process a command and return the response"""
        player = self.game_state.get_player(player_address)
        
        # Parse command with preposition support
        verb, filtered_args = self.parse_command_with_prepositions(command_text)
        
        if not verb:
            return "Please enter a command. Type 'help' for available commands."
        
        # Keep original args for compatibility with existing commands
        args = filtered_args
        
        # Trigger command event
        event = GameEvent('command', {
            'player_address': player_address,
            'verb': verb,
            'args': args,
            'full_command': command_text
        })
        event_responses = self.game_state.trigger_event(event)
        
        # Process command
        if verb in self.commands:
            try:
                command_response = self.commands[verb](player, args)
            except Exception as e:
                command_response = f"Error processing command: {e}"
                print(f"Command error: {e}")
        elif verb in self.object_verbs:
            # Handle verb-object interactions
            try:
                command_response = self.cmd_verb_object(player, verb, args)
            except Exception as e:
                command_response = f"Error processing verb command: {e}"
                print(f"Verb command error: {e}")
        else:
            command_response = f"I don't understand '{verb}'. Type 'help' for available commands."
        
        # Combine responses
        all_responses = event_responses + [command_response]
        return '\n\n'.join(filter(None, all_responses))
    
    def cmd_look(self, player: Player, args: List[str]) -> str:
        """Look around or examine something"""
        print(f"DEBUG: Player {player.address[:8]} trying to look in room '{player.current_room}'")
        current_room = self.game_state.get_room(player.current_room)
        print(f"DEBUG: Found room: {current_room.name if current_room else 'None'}")
        
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
            
            # List exits with custom descriptions
            if current_room.exits:
                response += f"\n\nExits: {', '.join(current_room.exits.keys())}"
            
            current_room.visited = True
            
            # Trigger look event
            self.game_state.trigger_event(GameEvent('look_room', {
                'player_address': player.address,
                'room_id': player.current_room
            }))
            
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
                # Trigger examine event
                self.game_state.trigger_event(GameEvent('examine_item', {
                    'player_address': player.address,
                    'item_name': item.name,
                    'item': item
                }))
                return item.description
            else:
                return f"You don't see any '{item_name}' here."
    
    def cmd_take(self, player: Player, args: List[str]) -> str:
        """Take an item"""
        if not args:
            return "Take what?"
        
        item_name = ' '.join(args)
        current_room = self.game_state.get_room(player.current_room)
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
        
        # Trigger take event
        self.game_state.trigger_event(GameEvent('item_taken', {
            'player_address': player.address,
            'item_name': item.name,
            'item': item
        }))
        
        return f"Taken: {item.name}."
    
    def cmd_use(self, player: Player, args: List[str]) -> str:
        """Use an item"""
        if not args:
            return "Use what?"
        
        # Parse "use X on Y" or "use X with Y"
        args_text = ' '.join(args)
        if ' on ' in args_text:
            item1_name, item2_name = args_text.split(' on ', 1)
        elif ' with ' in args_text:
            item1_name, item2_name = args_text.split(' with ', 1)
        else:
            item1_name = args_text
            item2_name = None
        
        # Find the first item (should be in inventory)
        item1 = player.get_item(item1_name.strip())
        if not item1:
            return f"You don't have any '{item1_name.strip()}'."
        
        # Trigger use event
        event_data = {
            'player_address': player.address,
            'item1_name': item1.name,
            'item1': item1
        }
        
        if item2_name:
            # Find second item (room or inventory)
            current_room = self.game_state.get_room(player.current_room)
            item2 = current_room.get_item(item2_name.strip())
            if not item2:
                item2 = player.get_item(item2_name.strip())
            
            if not item2:
                return f"You don't see any '{item2_name.strip()}' here."
            
            event_data['item2_name'] = item2.name
            event_data['item2'] = item2
        
        responses = self.game_state.trigger_event(GameEvent('use_item', event_data))
        
        if responses:
            return '\n'.join(responses)
        else:
            if item2_name:
                return f"You can't use the {item1.name} with the {item2.name}."
            else:
                return f"You can't use the {item1.name} here."
    
    # ... (other command methods remain similar but with event triggers)
    
    def cmd_unlock(self, player: Player, args: List[str]) -> str:
        """Unlock something"""
        if not args:
            return "Unlock what?"
        
        target_name = ' '.join(args)
        current_room = self.game_state.get_room(player.current_room)
        target = current_room.get_item(target_name)
        
        if not target:
            return f"There is no '{target_name}' here to unlock."
        
        # Trigger unlock event
        responses = self.game_state.trigger_event(GameEvent('unlock_attempt', {
            'player_address': player.address,
            'target_name': target.name,
            'target': target
        }))
        
        if responses:
            return '\n'.join(responses)
        else:
            return f"You can't unlock the {target.name}."
    
    def cmd_go(self, player: Player, args: List[str]) -> str:
        """Move to another room"""
        if not args:
            return "Go where?"
        
        direction = args[0].lower()
        current_room = self.game_state.get_room(player.current_room)
        
        # Check if movement is blocked by events
        movement_event = GameEvent('attempt_move', {
            'player_address': player.address,
            'direction': direction,
            'from_room': player.current_room
        })
        
        event_responses = self.game_state.trigger_event(movement_event)
        
        # Check if any event response blocks movement
        for response in event_responses:
            if response.startswith("BLOCK:"):
                return response[6:]  # Return message without BLOCK: prefix
        
        if direction not in current_room.exits:
            return f"You can't go {direction} from here."
        
        new_room_key = current_room.exits[direction]
        old_room = player.current_room
        player.current_room = new_room_key
        player.moves += 1
        
        # Trigger movement event
        self.game_state.trigger_event(GameEvent('player_moved', {
            'player_address': player.address,
            'from_room': old_room,
            'to_room': new_room_key,
            'direction': direction
        }))
        
        # Automatically look around the new room
        look_response = self.cmd_look(player, [])
        
        # Add any event responses
        if event_responses:
            return '\n\n'.join(event_responses + [look_response])
        else:
            return look_response
    
    def cmd_inventory(self, player: Player, args: List[str]) -> str:
        if not player.inventory:
            return "You are carrying nothing."
        
        response = "You are carrying:"
        for item in player.inventory:
            response += f"\n  {item.name}"
        return response
    
    def cmd_examine(self, player: Player, args: List[str]) -> str:
        return self.cmd_look(player, args)
    
    def cmd_open(self, player: Player, args: List[str]) -> str:
        if not args:
            return "Open what?"
        
        target_name = ' '.join(args)
        current_room = self.game_state.get_room(player.current_room)
        target = current_room.get_item(target_name)
        
        if not target:
            return f"There is no '{target_name}' here to open."
        
        responses = self.game_state.trigger_event(GameEvent('open_attempt', {
            'player_address': player.address,
            'target_name': target.name,
            'target': target
        }))
        
        if responses:
            return '\n'.join(responses)
        else:
            return f"You can't open the {target.name}."
    
    def cmd_close(self, player: Player, args: List[str]) -> str:
        if not args:
            return "Close what?"
        
        target_name = ' '.join(args)
        current_room = self.game_state.get_room(player.current_room)
        target = current_room.get_item(target_name)
        
        if not target:
            return f"There is no '{target_name}' here to close."
        
        responses = self.game_state.trigger_event(GameEvent('close_attempt', {
            'player_address': player.address,
            'target_name': target.name,
            'target': target
        }))
        
        if responses:
            return '\n'.join(responses)
        else:
            return f"You can't close the {target.name}."
    
    def cmd_score(self, player: Player, args: List[str]) -> str:
        return f"Score: {player.score} points\nMoves: {player.moves}\nItems carried: {len(player.inventory)}/{player.max_inventory}"
    
    def cmd_help(self, player: Player, args: List[str]) -> str:
        return """Available commands:
look [at item] - Look around or examine an item
take <item> - Take an item  
drop <item> - Drop an item from your inventory
go <direction> - Move in a direction
inventory (i) - Show your inventory
examine <item> - Examine an item closely
use <item> [on/with <target>] - Use an item
unlock <item> - Unlock something
open <item> - Open something
close <item> - Close something
score - Show your score and statistics
help - Show this help message
quit - Quit the game

Natural language examples:
look at chest, listen to door, throw sword at monster
read scroll, light lantern, push boulder, cast spell

Verb actions: read, listen, smell, taste, touch, push, pull, 
throw, break, shake, turn, move_object, light, extinguish, 
cast, enchant

Abbreviations: l (look), t (take), d (drop), i (inventory), x (examine), u (use)"""
    
    def cmd_quit(self, player: Player, args: List[str]) -> str:
        return f"Thanks for playing! Final score: {player.score} points in {player.moves} moves."
    
    def cmd_drop(self, player: Player, args: List[str]) -> str:
        if not args:
            return "Drop what?"
        
        item_name = ' '.join(args)
        item = player.get_item(item_name)
        
        if not item:
            return f"You don't have any '{item_name}'."
        
        current_room = self.game_state.get_room(player.current_room)
        player.remove_item(item)
        current_room.add_item(item)
        
        # Trigger drop event
        self.game_state.trigger_event(GameEvent('item_dropped', {
            'player_address': player.address,
            'item_name': item.name,
            'item': item
        }))
        
        return f"Dropped: {item.name}."
    
    def cmd_verb_object(self, player: Player, verb: str, args: List[str]) -> str:
        """Handle verb-object interactions"""
        if not args:
            return f"{verb.capitalize()} what?"
        
        target_name = ' '.join(args)
        
        # Find target in room or inventory
        current_room = self.game_state.get_room(player.current_room)
        target = current_room.get_item(target_name)
        location = 'room'
        
        if not target:
            target = player.get_item(target_name)
            location = 'inventory'
        
        if not target:
            return f"There is no '{target_name}' here."
        
        if not target.can_perform_verb(verb):
            return f"You can't {verb} the {target.name}."
        
        return self.process_verb_interaction(player, target, verb, location)
    
    def process_verb_interaction(self, player: Player, target: 'GameItem', verb: str, location: str) -> str:
        """Process a verb interaction with an item"""
        interaction = target.get_verb_interaction(verb)
        if not interaction:
            return f"You can't {verb} the {target.name}."
        
        # Check requirements
        requirements = interaction.get('requires', [])
        for requirement in requirements:
            if not self.check_requirement(player, requirement):
                return interaction.get('failure_response', f"You can't {verb} the {target.name} right now.")
        
        # Apply effects
        effects = interaction.get('effects', {})
        self.apply_verb_effects(player, target, effects, location)
        
        # Get response with variable substitution
        response = interaction.get('response', f"You {verb} the {target.name}.")
        response = response.replace('{item_name}', target.name)
        response = response.replace('{player_name}', 'you')
        
        return response
    
    def check_requirement(self, player: Player, requirement: str) -> bool:
        """Check if a requirement is met"""
        if requirement.startswith('flag:'):
            flag_name = requirement[5:]
            return self.game_state.get_flag(flag_name)
        elif requirement.startswith('item:'):
            item_name = requirement[5:]
            return player.has_item(item_name)
        elif requirement.startswith('in_room:'):
            room_id = requirement[8:]
            return player.current_room == room_id
        elif requirement.startswith('property:'):
            prop_check = requirement[9:]
            if '=' in prop_check:
                prop_name, prop_value = prop_check.split('=', 1)
                return player.get_property(prop_name) == prop_value
            else:
                return bool(player.get_property(prop_check))
        else:
            # Simple flag check
            return self.game_state.get_flag(requirement)
    
    def apply_verb_effects(self, player: Player, target: 'GameItem', effects: Dict[str, Any], location: str):
        """Apply the effects of a verb interaction"""
        current_room = self.game_state.get_room(player.current_room)
        
        for effect_type, effect_value in effects.items():
            if effect_type == 'score':
                player.score += effect_value
            elif effect_type == 'remove_item':
                if effect_value and location == 'inventory':
                    player.remove_item(target)
                elif effect_value and location == 'room':
                    current_room.remove_item(target)
            elif effect_type == 'move_item_to_room':
                if effect_value and location == 'inventory':
                    player.remove_item(target)
                    current_room.add_item(target)
            elif effect_type == 'add_room_exit':
                if isinstance(effect_value, dict):
                    direction = effect_value.get('direction')
                    to_room = effect_value.get('to_room')
                    if direction and to_room:
                        current_room.exits[direction] = to_room
            elif effect_type == 'set_flag':
                if isinstance(effect_value, dict):
                    for flag_name, flag_value in effect_value.items():
                        self.game_state.set_flag(flag_name, flag_value)
                else:
                    self.game_state.set_flag(effect_value, True)
            elif effect_type == 'set_player_property':
                if isinstance(effect_value, dict):
                    for prop_name, prop_value in effect_value.items():
                        player.set_property(prop_name, prop_value)
            elif effect_type == 'set_item_property':
                if isinstance(effect_value, dict):
                    for prop_name, prop_value in effect_value.items():
                        target.set_property(prop_name, prop_value)
            elif effect_type == 'teleport_to':
                if isinstance(effect_value, str) and effect_value in self.game_state.rooms:
                    player.current_room = effect_value

# --- LXMF Integration ---

# Initialize game
import os
import sys
import argparse

def load_game_config():
    """Load game configuration from command line argument or default location"""
    parser = argparse.ArgumentParser(
        description='Scriptable Zork LXMF Game Server',
        epilog='''Examples:
  python zork_scriptable.py                    # Use default game_config.json
  python zork_scriptable.py examples_config.json  # Use examples_config.json
  python zork_scriptable.py simple_game_example.json  # Use simple example
  python zork_scriptable.py /path/to/my_game.json     # Use absolute path''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('config', nargs='?', default='game_config.json',
                       help='Game configuration JSON file (default: game_config.json)')
    
    args = parser.parse_args()
    
    # Get the directory where the script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # If config path is not absolute, look in script directory
    if not os.path.isabs(args.config):
        config_path = os.path.join(script_dir, args.config)
    else:
        config_path = args.config
    
    print(f"Looking for game config at: {config_path}")
    
    try:
        game_state = GameBuilder.load_from_json(config_path)
        config_name = os.path.basename(config_path)
        print(f"Successfully loaded game from {config_name}")
        print(f"Loaded {len(game_state.rooms)} rooms: {list(game_state.rooms.keys())}")
        print(f"Loaded {len(game_state.items)} items: {list(game_state.items.keys())}")
        return game_state, config_name
    except FileNotFoundError:
        print(f"Config file '{config_path}' not found, creating default game...")
        return create_default_game(), "default"
    except Exception as e:
        print(f"Error loading game config '{config_path}': {e}")
        print("Creating default game...")
        return create_default_game(), "default"

def create_default_game():
    """Create a basic default game when no config is found"""
    game_state = GameState()
    
    # Create a basic default game
    default_item = GameItem("leaflet", "A small leaflet with game instructions.", True, ["paper", "instructions"])
    game_state.items["leaflet"] = default_item
    
    default_room = GameRoom(
        "Starting Room", 
        "You are in a simple room. There appears to be a leaflet here. Try typing 'help' for available commands.",
        {},
        [default_item]
    )
    game_state.rooms["entrance_hall"] = default_room
    
    print("Created basic default game with starting room")
    return game_state

# Load game configuration
game_state, config_name = load_game_config()
game_engine = GameEngine(game_state)

# LXMF setup (same as before)
RNS.Reticulum()
APP_NAME = "zork_scriptable"

identity_file = "zork_server_identity"
if RNS.Identity.from_file(identity_file):
    identity = RNS.Identity.from_file(identity_file)
    print(f"Loaded existing identity from {identity_file}")
else:
    identity = RNS.Identity()
    identity.to_file(identity_file)
    print(f"Created new identity and saved to {identity_file}")

destination = RNS.Destination(identity, RNS.Destination.IN, RNS.Destination.SINGLE, APP_NAME)
router = LXMF.LXMRouter(storagepath="./lxmf_storage")
lxmf_destination = router.register_delivery_identity(identity)

def message_received(message):
    """Handle incoming game commands"""
    sender_address = message.source_hash.hex()
    command_text = message.content.decode('utf-8').strip()
    
    print(f"Received command '{command_text}' from {RNS.prettyhexrep(message.source_hash)}")
    
    # Process command through game engine
    response_text = game_engine.process_command(sender_address, command_text)
    
    # Send response (same LXMF code as before)
    print(f"Sending response to {RNS.prettyhexrep(message.source_hash)}")
    print(f"Response content: {response_text[:100]}...")
    
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

def main():
    router.register_delivery_callback(message_received)
    
    print("Scriptable Zork Server Initialized.")
    print(f"Game Configuration: {config_name}")
    print(f"Listening for messages at: {RNS.prettyhexrep(destination.hash)}")
    print("Features:")
    print("- Event-driven gameplay")
    print("- Scriptable interactions") 
    print("- JSON-configurable games")
    print("- Advanced command system")
    print("- Verb-object interactions")
    
    while True:
        time.sleep(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Shutting down Scriptable Zork server.")
        RNS.Reticulum.exit()