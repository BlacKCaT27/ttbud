import os
import json


class RoomStore:
    def __init__(self):
        self.path = os.environ['ROOM_STORE_DIR']
        if not os.path.exists(self.path):
            os.mkdir(self.path)

    def get_all_room_ids(self):
        return os.listdir(self.path)

    def write_room_data(self, room, data):
        with open(f'{self.path}/{room}', 'w') as f:
            f.write(json.dumps(data))

    def read_room_data(self, room):
        with open(f'{self.path}/{room}', 'r') as f:
            return json.loads(f.read())

    def room_data_exists(self, room):
        return os.path.exists(f'{self.path}/{room}')