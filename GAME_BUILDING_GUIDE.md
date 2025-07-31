# 🎮 Game Building Guide for Non-Programmers

This guide will help you understand and edit the `game_config.json` file to create your own text adventure games!

## 📋 Table of Contents
1. [Understanding JSON Basics](#json-basics)
2. [Game Structure Overview](#game-structure)
3. [Creating Items](#creating-items)
4. [Building Rooms](#building-rooms)
5. [Simple Event Scripts](#simple-events)
6. [Common Patterns](#common-patterns)
7. [Tips and Troubleshooting](#tips)

---

## 🔤 JSON Basics {#json-basics}

JSON is like a recipe card - it has a specific format that must be followed exactly:

### ✅ **Important Rules:**
- Always use **double quotes** `"` around text, never single quotes `'`
- Put **commas** `,` after each item (except the last one)
- Use **curly braces** `{}` for objects (like items, rooms)
- Use **square brackets** `[]` for lists (like aliases, room items)
- **Indentation** makes it readable but isn't required

### ❌ **Common Mistakes:**
```json
❌ Wrong: 'single quotes'
✅ Right: "double quotes"

❌ Wrong: {name: brass key}
✅ Right: {"name": "brass key"}

❌ Wrong: ["item1", "item2",]  (extra comma)
✅ Right: ["item1", "item2"]
```

---

## 🏗️ Game Structure Overview {#game-structure}

Your game file has these main sections:

```json
{
  "items": { /* All the objects players can interact with */ },
  "rooms": { /* All the locations in your game */ },
  "event_handlers": [ /* The magic that makes things happen */ ],
  "initial_flags": { /* Starting conditions for your game */ }
}
```

---

## 🎁 Creating Items {#creating-items}

Items are objects players can find, take, and use. Here's the basic template:

### **Simple Item Template:**
```json
"item_id": {
  "name": "what players see",
  "description": "what they see when examining it",
  "can_take": true,
  "aliases": ["other", "names", "for", "item"],
  "properties": {
    "custom_property": "custom_value"
  }
}
```

### **Real Examples:**

#### **🗝️ A Simple Key:**
```json
"magic_key": {
  "name": "magic key",
  "description": "A shimmering key that glows with mystical energy.",
  "can_take": true,
  "aliases": ["key", "magical key"],
  "properties": {
    "unlocks": "magic_door"
  }
}
```

#### **🚪 A Locked Door:**
```json
"magic_door": {
  "name": "magic door",
  "description": "A tall door covered in glowing runes. It appears to be locked.",
  "can_take": false,
  "aliases": ["door", "magical door"],
  "properties": {
    "locked": true,
    "blocks_exit": "north"
  }
}
```

#### **📦 A Container with Treasure:**
```json
"treasure_box": {
  "name": "treasure box",
  "description": "A wooden box with a golden lock.",
  "can_take": false,
  "aliases": ["box", "chest"],
  "properties": {
    "locked": true,
    "contains": ["gold_ring", "silver_coin"]
  }
}
```

### **Item Properties You Can Use:**
- `"unlocks": "door_id"` - This item can unlock that door
- `"locked": true` - This item is locked
- `"contains": ["item1", "item2"]` - Items inside this container
- `"value": 100` - Point value when taken
- `"fuel": 50` - For items like lanterns
- `"lit": false` - For light sources
- Any custom property you want!

---

## 🏠 Building Rooms {#building-rooms}

Rooms are the locations players can visit. Here's the template:

### **Room Template:**
```json
"room_id": {
  "name": "Room Name Players See",
  "description": "What players see when they look around",
  "exits": {
    "north": "another_room_id",
    "south": "different_room_id"
  },
  "items": ["item1_id", "item2_id"],
  "properties": {
    "custom_property": "value"
  }
}
```

### **Real Example:**
```json
"enchanted_forest": {
  "name": "Enchanted Forest",
  "description": "You stand in a mystical forest where the trees seem to whisper ancient secrets. Glowing mushrooms light the path ahead.",
  "exits": {
    "north": "fairy_clearing",
    "south": "village_entrance",
    "east": "dark_cave"
  },
  "items": ["magic_mushroom", "fallen_branch"],
  "properties": {
    "ambient_light": true,
    "fairy_blessing": false
  }
}
```

### **Direction Names You Can Use:**
- Standard: `"north"`, `"south"`, `"east"`, `"west"`
- Vertical: `"up"`, `"down"`
- Special: `"enter"`, `"exit"`, `"in"`, `"out"`
- Custom: `"through_portal"`, `"climb_ladder"`, etc.

---

## ✨ Simple Event Scripts {#simple-events}

Events make your game interactive! Here are simple patterns you can copy and modify:

### **🔓 Key Unlocks Door Pattern:**
```json
{
  "type": "script",
  "scope": "global",
  "conditions": {
    "event_type": "use_item",
    "player_has_item": "YOUR_KEY_ID"
  },
  "script": "if event.data.get('item2') and event.data['item2'].name == 'YOUR_DOOR_NAME':\n    door = event.data['item2']\n    if door.get_property('locked'):\n        door.set_property('locked', False)\n        door.description = 'The door is now open, revealing the path beyond.'\n        # Add new exit\n        current_room = game_state.get_room(player.current_room)\n        current_room.exits['DIRECTION'] = 'NEW_ROOM_ID'\n        response = 'The key fits perfectly! The door swings open.'\n        player.score += 50\n    else:\n        response = 'The door is already open.'\nelse:\n    response = None"
}
```

**To customize this:**
1. Replace `YOUR_KEY_ID` with your key's ID
2. Replace `YOUR_DOOR_NAME` with your door's name
3. Replace `DIRECTION` with the direction (like "north")
4. Replace `NEW_ROOM_ID` with the room beyond the door

### **📦 Key Opens Container Pattern:**
```json
{
  "type": "script",
  "scope": "global",
  "conditions": {
    "event_type": "use_item",
    "player_has_item": "YOUR_KEY_ID"
  },
  "script": "if event.data.get('item2') and event.data['item2'].name == 'YOUR_CONTAINER_NAME':\n    container = event.data['item2']\n    if container.get_property('locked'):\n        container.set_property('locked', False)\n        container.description = 'An open container revealing its treasures!'\n        # Add treasure to room\n        current_room = game_state.get_room(player.current_room)\n        treasure_items = ['ITEM1_ID', 'ITEM2_ID']\n        for item_id in treasure_items:\n            if item_id in game_state.items:\n                current_room.add_item(game_state.items[item_id])\n        response = 'The container opens, revealing valuable treasures inside!'\n        player.score += 100\n    else:\n        response = 'The container is already open.'\nelse:\n    response = None"
}
```

### **🚫 Block Movement Until Condition Met:**
```json
{
  "type": "script",
  "scope": "global",
  "conditions": {
    "event_type": "attempt_move"
  },
  "script": "direction = event.data.get('direction')\nfrom_room = event.data.get('from_room')\nif from_room == 'ROOM_ID' and direction == 'DIRECTION':\n    if not game_state.get_flag('CONDITION_FLAG'):\n        response = 'BLOCK:Something blocks your path! You need to find another way.'\n    else:\n        response = None\nelse:\n    response = None"
}
```

### **🎁 Automatic Points for Taking Items:**
```json
{
  "type": "script",
  "scope": "global",
  "conditions": {
    "event_type": "item_taken"
  },
  "script": "item = event.data.get('item')\nif item and item.name == 'YOUR_ITEM_NAME':\n    points = item.get_property('value', 10)\n    player.score += points\n    response = f'You gained {points} points for taking the {item.name}!'\nelse:\n    response = None"
}
```

---

## 🔄 Common Patterns {#common-patterns}

### **🏁 Victory Room:**
```json
{
  "type": "script",
  "scope": "room:treasure_chamber",
  "conditions": {
    "event_type": "look_room"
  },
  "script": "if not game_state.get_flag('victory_achieved'):\n    game_state.set_flag('victory_achieved', True)\n    player.score += 500\n    response = '\\n\\n🎉 CONGRATULATIONS! 🎉\\nYou have completed your quest!'\nelse:\n    response = None"
}
```

### **🔮 Magic Item Effects:**
```json
{
  "type": "script",
  "scope": "global",
  "conditions": {
    "event_type": "use_item"
  },
  "script": "item = event.data.get('item1')\nif item and item.name == 'magic_wand':\n    if player.current_room == 'wizard_tower':\n        response = 'The wand glows brightly! You feel magical energy flowing through you.'\n        player.set_property('has_magic', True)\n        player.score += 25\n    else:\n        response = 'The wand flickers weakly. It needs to be in a place of power.'\nelse:\n    response = None"
}
```

---

## 💡 Tips and Troubleshooting {#tips}

### **✅ Testing Your Game:**
1. Start small - add one room and one item first
2. Test each interaction before adding more
3. Save backup copies of working versions

### **🔍 Common Issues:**

#### **"JSON Error" when starting:**
- Check for missing commas between items
- Make sure all quotes are double quotes `"`
- Verify all brackets `{}` and `[]` are properly closed

#### **Events not triggering:**
- Check that item IDs match exactly (case-sensitive)
- Verify the event conditions match your game state
- Make sure the script has proper line breaks (`\n`)

#### **Items not appearing:**
- Check that item IDs in room's `"items"` list match the item definitions
- Verify items aren't marked as `"hidden": true`

### **🛠️ Easy Editing Tools:**
- Use a text editor with JSON syntax highlighting
- Online JSON validators can check for errors
- Many editors will show you matching brackets

### **📖 Step-by-Step Process:**
1. **Plan your game** on paper first
2. **Start with basic rooms** and connections  
3. **Add simple items** players can take
4. **Create one key-door interaction** 
5. **Test everything** before adding more
6. **Gradually add complexity**

---

## 🎯 Quick Start Checklist

To create your first simple game:

- [ ] Copy the existing `game_config.json` 
- [ ] Change room names and descriptions
- [ ] Modify item names and descriptions
- [ ] Test with `look` and `take` commands
- [ ] Add one simple key-unlock interaction
- [ ] Expand from there!

Remember: Start simple and build up gradually. Every expert was once a beginner! 🌟