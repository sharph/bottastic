#!/usr/bin/env python3
import argparse
import importlib
import logging
import sys
from typing import Type, Dict, Any

import meshtastic
import meshtastic.tcp_interface
import meshtastic.serial_interface

from bottastic.bottastic import Bottastic


def import_bot_class(bot_path: str) -> Type[Bottastic]:
    """
    Dynamically import a bot class from a string path like 'bottastic:PingPongBot'
    """
    try:
        module_path, class_name = bot_path.split(":")
        module = importlib.import_module(module_path)
        bot_class = getattr(module, class_name)

        if not issubclass(bot_class, Bottastic):
            raise TypeError(f"{bot_path} is not a subclass of Bottastic")

        return bot_class
    except (ImportError, AttributeError, ValueError) as e:
        raise ImportError(f"Could not import bot class {bot_path}: {e}")


def create_interface(args):
    """Create the appropriate Meshtastic interface based on command line args"""
    if args.host:
        return meshtastic.tcp_interface.TCPInterface(hostname=args.host)
    elif args.port:
        return meshtastic.serial_interface.SerialInterface(devPath=args.port)
    else:
        # Default: try to find a connected device automatically
        return meshtastic.serial_interface.SerialInterface()


def extract_bot_kwargs(args_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Extract kwargs for the bot from the parsed args"""
    # Remove args used by the CLI itself
    cli_args = ["host", "port", "bot_class", "verbose"]

    # Convert remaining args to kwargs for the bot
    return {k: v for k, v in args_dict.items() if k not in cli_args and v is not None}


def main():
    parser = argparse.ArgumentParser(description="Bottastic CLI for Meshtastic bots")

    # Connection options
    connection_group = parser.add_argument_group("Connection Options")
    connection_group.add_argument(
        "--host", type=str, help="Connect via TCP to a specified hostname/IP"
    )
    connection_group.add_argument(
        "--port",
        type=str,
        help="Connect via serial to a specified port (e.g., /dev/ttyUSB0)",
    )

    # Bot options
    parser.add_argument(
        "bot_class", type=str, help="Bot class to run in format 'module:ClassName'"
    )
    parser.add_argument(
        "--echo_sent", type=bool, default=False, help="Echo sent messages to console"
    )
    parser.add_argument(
        "--echo_recieved",
        type=bool,
        default=False,
        help="Echo received messages to console",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )

    args = parser.parse_args()

    # Set up logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level)

    # Import the specified bot class
    try:
        bot_class = import_bot_class(args.bot_class)
    except ImportError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Create the appropriate interface
    try:
        interface = create_interface(args)
    except Exception as e:
        print(f"Error connecting to Meshtastic device: {e}", file=sys.stderr)
        sys.exit(1)

    # Extract kwargs for the bot
    kwargs = extract_bot_kwargs(vars(args))

    # Create and run the bot
    try:
        bot = bot_class(interface, **kwargs)
        bot.run()
    except KeyboardInterrupt:
        print("Bot stopped by user")
    except Exception as e:
        print(f"Error running bot: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        interface.close()


if __name__ == "__main__":
    main()
