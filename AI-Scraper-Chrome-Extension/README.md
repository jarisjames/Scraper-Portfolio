# The Handoff Protocol

A Chrome Extension to capture, store, and export AI memory across ChatGPT, Claude, and Copilot—built on The Continuity Protocol.


## Features

- Save chat sessions locally via IndexedDB
- Export memory to `.SHARD` files for persistence
- Fully offline — no cloud required
- Selector mapping for multi-agent LLMs (ChatGPT, Claude, Copilot)
- Future: `.SHARD` rehydration, vault dashboard, persona presets

## Usage

1. Enable Developer Mode in `chrome://extensions`
2. Click “Load Unpacked” and select this folder
3. Navigate to a ChatGPT, Claude, or Copilot session
4. Open the extension popup → Save, Export, or Load your memory card

## File Format

`.SHARD` files are user-owned memory archives that store LLM session history, persona tone, and cognitive state. These files function similarly to `.db` snapshots for portable cognition.




