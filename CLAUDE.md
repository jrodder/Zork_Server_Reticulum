# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This repository contains a single Python script implementing a text-based adventure game server using the Reticulum mesh networking stack and LXMF (Lxmf eXtensible Message Format) protocol. The project is a simple "Zork-style" game server that can handle multiple players over a mesh network.

## Architecture

The codebase consists of one main file:
- `script.py` - A complete LXMF server implementing a multi-user text adventure game

### Key Components:
- **Game World**: Dictionary-based room system with descriptions and exits
- **Player State Management**: Persistent player locations stored by LXMF address
- **Message Handling**: Asynchronous message processing for player commands
- **Reticulum Integration**: Mesh networking setup with LXMF endpoint

### Dependencies:
- `RNS` (Reticulum Network Stack)
- `LXMF` (Lxmf eXtensible Message Format)
- Standard Python libraries: `time`, `threading`

## Running the Server

```bash
python script.py
```

The server will:
1. Initialize Reticulum networking
2. Create an LXMF destination endpoint
3. Listen for incoming messages from game clients
4. Process game commands and maintain player state

## Game Commands

Players can send these commands via LXMF messages:
- `look` - Get current room description
- `go <direction>` - Move to adjacent room (north, south, east, west)
- `quit` - Exit the game

## Development Notes

- Player state is maintained in memory using LXMF addresses as keys
- The game world is hardcoded in the `GAME_WORLD` dictionary
- No persistent storage - player positions reset on server restart
- Server runs indefinitely until interrupted with Ctrl+C
- All networking handled through Reticulum's mesh protocol