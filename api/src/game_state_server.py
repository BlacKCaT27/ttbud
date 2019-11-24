from websockets import WebSocketServerProtocol
from dataclasses import dataclass

from room_store import RoomStore


@dataclass
class Token:
    id: str
    icon_id: str
    start_x: int
    start_y: int
    start_z: int
    end_x: int
    end_y: int
    end_z: int

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'icon_id': self.icon_id,
            'start_x': self.start_x,
            'start_y': self.start_y,
            'start_z': self.start_z,
            'end_x': self.end_x,
            'end_y': self.end_y,
            'end_z': self.end_z,
        }


class RoomData:
    def __init__(self, room_id: str, initial_connection=None):
        self.room_id = room_id
        self.game_state = {}
        self.id_to_positions = {}
        self.positions_to_ids = {}
        self.clients = set()
        if initial_connection:
            self.clients.add(initial_connection)


class MessageError(Exception):
    def __init__(self, message):
        self.message = message


class GameStateServer:
    def __init__(self, room_store_dir):
        self._rooms = {}
        self.rs = RoomStore(room_store_dir)

    def valid_previous_rooms(self) -> list:
        return self.rs.get_all_room_ids()

    def new_connection_request(
        self, client: WebSocketServerProtocol, room_id: str
    ) -> dict:
        if self._rooms.get(room_id, False):
            self._rooms[room_id].clients.add(client)
        else:
            self._rooms[room_id] = RoomData(room_id, initial_connection=client)
            if self.rs.room_data_exists(room_id):
                self._rooms[room_id].game_state = self.rs.read_room_data(room_id)
        return {'type': 'state', 'data': self.get_state(room_id)}

    def connection_dropped(self, client: WebSocketServerProtocol, room_id: str) -> None:
        if self._rooms.get(room_id, False):
            self._rooms[room_id].clients.remove(client)
            if not self._rooms[room_id].clients:
                print('Writing room data')
                self.rs.write_room_data(room_id, self._rooms[room_id].game_state)
            else:
                print(f'{len(self._rooms[room_id].clients)} clients remaining')

    def process_update(self, message: dict, room_id: str) -> dict:
        if not (self._rooms.get(room_id, False) and self._rooms[room_id].clients):
            raise MessageError('Your room does not exist, somehow')
        action = message.get('action', None)
        data = message.get('data', None)
        if not action or not data:
            raise MessageError('Did not receive a full message')

        reply = {'type': None, 'data': None}
        if action == 'create' or action == 'update':
            token = self.dict_to_token(data)
            if not token or not self.is_valid_token(token):
                raise MessageError(f'Received a bad token {data}')
            if not self.is_valid_position(token, room_id):
                raise MessageError('That position is occupied, bucko')
            self.create_or_update_token(token, room_id)
            reply['type'] = 'state'
            reply['data'] = self.get_state(room_id)
        elif action == 'delete':
            if type(data) != str:
                raise MessageError('Data for delete actions must be a token ID')
            if self._rooms[room_id].game_state.get(data, False):
                self.delete_token(data, room_id)
                reply['type'] = 'state'
                reply['data'] = self.get_state(room_id)
        elif action == 'ping':
            reply['type'] = 'ping'
            reply['data'] = data
        else:
            raise MessageError(f'Invalid action: {action}')
        return reply

    @staticmethod
    def dict_to_token(data: dict):
        try:
            token = Token(**data)
        except TypeError:
            return None
        return token

    @staticmethod
    def is_valid_token(token: Token) -> bool:
        return (
            token.start_x < token.end_x
            and token.start_y < token.end_y
            and token.start_z < token.end_z
        )

    def is_valid_position(self, token: Token, room_id: str) -> bool:
        blocks = self.get_unit_blocks(token)
        for block in blocks:
            if self._rooms[room_id].positions_to_ids.get(block, False):
                return False
        return True

    def create_or_update_token(self, token: Token, room_id: str) -> None:
        print(f'New token: {token}')
        if self._rooms[room_id].game_state.get(token.id):
            self.remove_positions(token.id, room_id)

        # Update state for new or existing token
        blocks = self.get_unit_blocks(token)
        self._rooms[room_id].id_to_positions[token.id] = blocks
        for block in blocks:
            self._rooms[room_id].positions_to_ids[block] = token.id
        self._rooms[room_id].game_state[token.id] = token.to_dict()

    def delete_token(self, token_id: str, room_id: str) -> None:
        # Remove token data from position dictionaries
        self.remove_positions(token_id, room_id)
        if self._rooms[room_id].id_to_positions.get(token_id, False):
            del self._rooms[room_id].id_to_positions[token_id]
        # Remove the token from the state
        if self._rooms[room_id].game_state.get(token_id, False):
            del self._rooms[room_id].game_state[token_id]

    def remove_positions(self, token_id: str, room_id: str) -> None:
        positions = self._rooms[room_id].id_to_positions[token_id]
        for pos in positions:
            if self._rooms[room_id].positions_to_ids.get(pos, False):
                del self._rooms[room_id].positions_to_ids[pos]

    @staticmethod
    def get_unit_blocks(token: Token) -> list:
        unit_blocks = []
        for x in range(token.start_x, token.end_x):
            for y in range(token.start_y, token.end_y):
                for z in range(token.start_z, token.end_z):
                    unit_blocks.append((x, y, z))
        return unit_blocks

    def get_state(self, room_id: str) -> list:
        return list(self._rooms[room_id].game_state.values())

    def get_clients(self, room_id: str) -> set:
        return self._rooms[room_id].clients
