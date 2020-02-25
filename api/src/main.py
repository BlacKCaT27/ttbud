import os
import signal

from wsmanager import start_websocket
from room_store import FileRoomStore
from game_state_server import GameStateServer


def main():
    websocket_port = int(os.environ['API_WEBSOCKET_PORT'])
    room_store_dir = os.environ['ROOM_STORE_DIR']

    room_store = FileRoomStore(room_store_dir)
    gss = GameStateServer(room_store)

    start_websocket(websocket_port, gss)
    signal.signal(signal.SIGTERM, gss.save_all)


if __name__ == '__main__':
    main()
