from abc import ABC, abstractmethod
import sys
import time
import asyncio
import base64

from pubsub import pub

import meshtastic
import meshtastic.tcp_interface
import meshtastic.mesh_interface
import meshtastic.protobuf.portnums_pb2
import logging

from functools import wraps
from concurrent.futures import ThreadPoolExecutor

from typing import Optional

logging.basicConfig(level=logging.INFO)
thread_pool = ThreadPoolExecutor()

_registered_bots = []
_connected_bots = []


def call_async(fn, *args, **kwargs):
    """
    turns a sync function to async function using threads
    """
    future = thread_pool.submit(fn, *args, **kwargs)
    return asyncio.wrap_future(future)


class NoEncryptionKey(Exception):
    pass


class Bottastic(ABC):
    def __init__(
        self,
        interface: meshtastic.mesh_interface.MeshInterface,
        echo_sent: bool = False,
        echo_recieved: bool = False,
    ):
        self.interface = interface
        self.echo_sent = echo_sent
        self.echo_recieved = echo_recieved
        self.loop = None
        self.my_node = None
        self.my_user = None
        _registered_bots.append(self)

    async def _on_connect(self):
        self.my_node = await call_async(self.interface.getMyNodeInfo)
        self.my_user = await call_async(self.interface.getMyUser)
        await self.on_initialized()

    def _handle_on_connection(self):
        if not self.loop:
            raise Exception("Loop not set up")
        asyncio.run_coroutine_threadsafe(self._on_connect(), self.loop)

    def _handle_on_recieve(self, packet):
        if not self.loop or not self.my_node:
            return
        user = None
        if packet["to"] != self.my_node["num"]:
            return
        if self.interface.nodesByNum:
            node = self.interface.nodesByNum.get(packet["from"])
            if node:
                user = node["user"]
        if "decoded" not in packet or "text" not in packet["decoded"]:
            return
        if self.echo_recieved:
            print(f"Message from {packet['from']}: {packet['decoded']['text']}")
        asyncio.run_coroutine_threadsafe(
            self.handle_message(packet["from"], packet["decoded"]["text"], user),
            self.loop,
        )

    def close(self):
        self.interface.close()
        _registered_bots.remove(self)

    async def on_initialized(self):
        pass

    async def send_message(
        self, to: int, text: str, require_encryption=True, want_response=False
    ):
        key = None
        if (
            self.interface.nodesByNum is not None
            and "user" in self.interface.nodesByNum[to]
            and "publicKey" in self.interface.nodesByNum[to]["user"]
        ):
            key = base64.b64decode(self.interface.nodesByNum[to]["user"]["publicKey"])
        else:
            if require_encryption:
                raise NoEncryptionKey()

        def _on_deliver(_):
            if self.echo_sent and self.echo_recieved:
                print(f"Delivered message to {to}: {text}")

        await call_async(
            self.interface.sendData,
            text.encode("utf-8"),
            to,
            wantAck=want_response,
            wantResponse=want_response,
            onResponse=_on_deliver if want_response else None,
            pkiEncrypted=key is not None,
            publicKey=key,
            portNum=meshtastic.portnums_pb2.PortNum.TEXT_MESSAGE_APP,
        )
        if self.echo_sent:
            print(f"Sent to {to} ({'enc' if key else 'no enc'}): {text}")

    async def handle_message(
        self, from_id: int, message: str, from_user: Optional[dict]
    ):
        pass

    async def event_loop(self):
        self.loop = asyncio.get_running_loop()
        if self.interface in _connected_bots:
            _connected_bots.remove(self.interface)
            await self._on_connect()
        while True:
            await asyncio.sleep(10)

    def run(self):
        asyncio.run(self.event_loop())


def on_receive(packet, interface: meshtastic.mesh_interface.MeshInterface):
    """called when a packet arrives"""
    for registered_bot in _registered_bots:
        if registered_bot.interface is interface:
            registered_bot._handle_on_recieve(packet)


def on_connection(
    interface: meshtastic.mesh_interface.MeshInterface, topic=pub.AUTO_TOPIC
):
    for registered_bot in _registered_bots:
        if registered_bot.interface is interface and registered_bot.loop:
            registered_bot._handle_on_connection()
            return
    _connected_bots.append(interface)


pub.subscribe(
    on_connection,
    "meshtastic.connection.established",
)
pub.subscribe(
    on_receive,
    "meshtastic.receive",
)


class PingPongBot(Bottastic):
    async def handle_message(
        self, from_id: int, message: str, from_user: Optional[dict]
    ):
        if message.strip().lower() == "ping":
            await self.send_message(from_id, "pong!")


if __name__ == "__main__":
    interface = meshtastic.tcp_interface.TCPInterface(hostname=sys.argv[1])
    PingPongBot(interface, echo_sent=True, echo_recieved=True).run()
