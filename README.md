# Bottastic

A framework for building bots for Meshtastic networks.

## Installation

```bash
git clone https://github.com/sharph/bottastic.git
cd bottastic
uv sync
```

## Usage

Bottastic provides a command-line interface to run your bots. You can [connect to a Meshtastic device via serial or TCP](https://meshtastic.org/docs/software/python/cli/usage).

### Basic Usage

```bash
# Run a bot using automatic serial device detection
bottastic bottastic:PingPongBot

# Run a bot with a specific serial port
bottastic --port /dev/ttyUSB0 bottastic:PingPongBot

# Run a bot using TCP connection
bottastic --host 192.168.1.100 bottastic:PingPongBot

# Enable echo options
bottastic --port /dev/ttyUSB0 bottastic:PingPongBot --echo_sent=True --echo_received=True

# Enable verbose logging
bottastic --port /dev/ttyUSB0 bottastic:PingPongBot -v
```

### Creating Your Own Bot

Create a Python module with a class that inherits from `Bottastic`:

```python
# mybot.py
from bottastic.bottastic import Bottastic, MeshtasticNode

class MyCustomBot(Bottastic):
    async def handle_message(self, from_node: MeshtasticNode, message: str, channel: MeshtasticChannel):
        if message.startswith('hello'):
            await channel.send_message(f"Hello there, {from_node.short_name}!")

    async def handle_direct_message(self, from_node: MeshtasticNode, message: str):
        await from_node.send_message(f"You sent me: {message}")

    async def on_initialized(self):
        print(f"Bot initialized with node ID: {self.my_node['id']}")
        # Send a startup message
        await self.send_message("MyCustomBot is now online!")
```

Then run your bot:

```bash
bottastic --port /dev/ttyUSB0 mybot:MyCustomBot
```

## Available Options

- `--host HOST` - Connect via TCP to a specified hostname/IP
- `--port PATH` - Connect via serial to a specified port (e.g., /dev/ttyUSB0)
- `--echo_sent BOOL` - Whether to print sent messages to console
- `--echo_received BOOL` - Whether to print received messages to console
- `--verbose`, `-v` - Enable verbose logging
