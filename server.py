# server.py
import socket
import threading
import pygame
from dotenv import load_dotenv
from logs import log, trylog, inspect_object
import os
from utils import send, receive 
import datetime, time
import enums
from map import Map

from events import *

from message import ( 
    MoveMessage, SetPlayerNameMessage, GetPlayerMessage, 
    AllowCollectItemsMessage, RemoveInProcessMoveMessage, StillAliveMessage)

from game_board import GameBoard

from enums import GameStatus, PlayerStatus
from config import Config
import config_server


class Server:
    def __init__(self,  host=None, port=None, test_mode: bool= False):

        load_dotenv(override=True)

        self.host = host or os.environ.get('SERVER', '0.0.0.0')
        self.port = port or int(os.environ.get('PORT', 4444))
        self.test_mode = test_mode
        log(f'Listern to {self.host}:{self.port}', '[SERVER]')
        self.fps = Config.FPS #  frame per second
        self.clients = {}  
        self.client_ping_time = {}  # store ping time for each client
        self.lock = threading.Lock()

        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)


        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(20)  # Listen for up to 20 connections

        
        self.game_client_dispatcher = None

        self.tick_range_should_at_home: range = None
        
        self.current_event = None
        self.start_event_at_tick = None
        self.end_event_at_tick = None

        self.WIND_N_FABRIC = None
        self.WIND_N_WOOD = None
        self.FABRIC_TO_COTTON_RATIO = None
        self.game_board = GameBoard(self)
        
        
    def start(self):
        # Thread to connect to client
        threading.Thread(target=self.accept_clients, daemon=True).start()

        # Start game loop
        self.start_game_loop()
    
    def send(self, sock, obj):
        with self.lock:
            send(sock, obj)
    
    def get_file_name(self, player):
        return f'player_{player.id}_{player.name}.txt'

    def create_player_log(self, player):
        file_name = self.get_file_name(player)
        status = player.status
        tick = self.game_board.tick
        store = player.store
        log_text = f'{player.id}_{player.name} at: {tick}. status: {status}, store: {store}'
        
        open(file_name, 'wt').writelines(log_text)
    
    def update_player_log(self, player):
        file_name = file_name = self.get_file_name(player)
        status = player.status
        tick = self.game_board.tick
        store = player.store
        log_text = f'{player.id}_{player.name} at: {tick}. status: {status}, store: {store}'
        with open(file_name, 'at') as f:
            f.writelines(log_text)

    def accept_clients(self):
        if not self.game_client_dispatcher:
            log("Server started. Waiting for dispatcher...", "[SERVER]")
        else:
            log("Server started. Waiting for clients...", "[SERVER]")
            
        while True:
            if self.server_socket._closed:
                log("Server socket is closed, stopping accept_clients", "[SERVER]")
                return
            elif self.game_board.game_status == GameStatus.WAITING_FOR_PLAYERS:
                try:
                    client_socket, addr = self.server_socket.accept()
                except Exception as e:  
                    log(f"Error accepting client: {e}", "[SERVER]")
                    continue 
                log(f"New connection from addr: {addr}, client_socket: {client_socket}", "[SERVER]")
                if not self.game_client_dispatcher:
                    self.game_client_dispatcher = client_socket
                    threading.Thread(target=self.handle_client, args=(client_socket,), daemon=True).start()
                    time.sleep(.5)
                    self.send(client_socket, "Connected")

                else:
                    if len(self.game_board.players) < 5:
                        player = self.game_board.create_random_player(id=len(self.game_board.players))

                        self.create_player_log(player)
                        self.clients[client_socket] = player.id

                        log(f"Send init player {player} to client {addr}", "[SERVER]")
                        #  use thread for each client to receive client message 

                        threading.Thread(target=self.handle_client, args=(client_socket,), daemon=True).start()
                        time.sleep(.5)
                        self.send(client_socket, player)
                    else:
                        log(f"Send init player {player} to client {addr}", "[SERVER]")

    
    def move_player(self,player, dir):
        has_move = False
        r, c = player.row, player.col
        if dir == enums.Direction.LEFT.value:
            if self.game_board.map.can_move(player, enums.Direction.LEFT):
                player.col -= 1
                has_move = True
        elif dir == enums.Direction.RIGHT.value:
            if self.game_board.map.can_move(player, enums.Direction.RIGHT):
                player.col += 1
                has_move = True
        elif dir == enums.Direction.UP.value:
            if self.game_board.map.can_move(player, enums.Direction.UP):
                player.row -= 1
                has_move = True
        if dir == enums.Direction.DOWN.value:
            if self.game_board.map.can_move(player, enums.Direction.DOWN):
                player.row += 1
                has_move = True
        if has_move:
            self.game_board.map.set_value(r, c, 'g')
        return has_move

    def collision_result(self, player, other_player):

        # ⚔️ Sword vs ⚔️ Sword & ⚔️ Sword vs 🛡️ Shield: Agent loses tool and continues moving 

        if player.sword and other_player.sword:
            player.sword = 0
            other_player.sword = 0
        elif player.sword and other_player.armor:
            player.sword = 0
            other_player.armor = 0
        elif player.armor and other_player.sword:
            player.armor = 0
            other_player.sword = 0

        #- ⚔️ Sword vs No Sword/Shield: Agent loses sword & continues moving, the remaining agent is returned to Home & cannot 
        elif player.sword and not other_player.sword and not other_player.armor:
            other_player.items_on_hand = []
            self.game_board.map.set_value(other_player.row, other_player.col, 'g')
            other_player.row, other_player.col = other_player.home_row, other_player.home_col
            other_player.status = PlayerStatus.PAUSED
            other_player.paused_duration = 30
            other_player.paused_time = datetime.datetime.now().timestamp()
            

    def handle_collision_at_position(self, player, row, col):
        # Retrieve the grid element at the given position
        grid_element = player.grid[row][col]

        # Check if the element is numeric (indicating another player)
        if grid_element.isnumeric():
            # Get the other player using the grid value as the player index
            other_player_index = int(grid_element)
            other_player = self.game_board.players.get(other_player_index)

            # Ensure the player exists and is in the playing state
            if other_player and other_player.status == PlayerStatus.PLAYING:
                log(f'Player {player.name} collided with player {other_player.name}', '[SERVER]')
                self.collision_result(player, other_player)
    
    def collision(self, player):

        # check collision with other players in up
        if player.row>0:
            self.handle_collision_at_position(player, player.row-1, player.col)
        # check collision with other players in down
        if player.row<self.game_board.map.n_row-1:
            self.handle_collision_at_position(player, player.row+1, player.col)
        # check collision with other players in left
        if player.col>0:
            self.handle_collision_at_position(player, player.row, player.col-1)
        # check collision with other players in right
        if player.col<self.game_board.map.n_col-1:
            self.handle_collision_at_position(player, player.row, player.col+1)
        
    def update_player(self, player, dir=None):
        player.last_updated = datetime.datetime.now().timestamp()
        if player.status == PlayerStatus.PAUSED:
            log(f'Player {player.name} is paused and cannot move', '[SERVER]')
            # if player.paused_time + Config.PAUSED_TIME < datetime.datetime.now().timestamp():
            if player.paused_time + player.paused_duration < datetime.datetime.now().timestamp():
                player.status = PlayerStatus.PLAYING
                player.row, player.col = player.home_row, player.home_col
                self.game_board.map.set_value(player.row, player.col, player.id)
            return  
        
        
        if dir is not None:
            if player.status == PlayerStatus.PLAYING:
                self.move_player(player, dir)
        elif len(player.in_process_move_messages) > 0:
            message = player.in_process_move_messages.pop(0)
            if isinstance(message, MoveMessage):
                if player.status == PlayerStatus.PLAYING:
                    dir = message.dir
                    self.move_player(player, dir)
                            
        self.game_board.update_nearby_map_area(player)
        self.collision(player)
        self._collect_items(player)
        self._store_items_if_at_home(player)
        
        self.convert_wood_cotton_to_fabric(player)
        self._check_win_condition(player)

        self.game_board.map.set_value(player.row, player.col, player.id)
        self.update_player_log(player)
        

    def convert_wood_cotton_to_fabric(self, player):
        c = player.store.count('c')
        if c == 0:
            return
        fa = c // self.FABRIC_TO_COTTON_RATIO
        if fa > 0:
            log(f'Convert wood and cotton to fabric for player {player.name}', '[SERVER]')
            player.store = [x for x in player.store if x != 'c']
            player.store += ['fa'] * fa
            player.store += ['c'] * (c % self.FABRIC_TO_COTTON_RATIO)
                                
    def _collect_items(self, player):
        with self.lock:
            # Collect items
            self.game_board.map.collect_items(player)

            # update items bring to home
    
    def _store_items_if_at_home(self, player):
        if self.game_board.map.at_home(player):
            capacity = Config.MAX_STORAGE_CAPACITY - len(player.store)
            if capacity >= len(player.items_on_hand):
                player.store += player.items_on_hand
                player.items_on_hand = []
            else:
                # store only part of items
                player.store += player.items_on_hand[:capacity]
                player.items_on_hand = player.items_on_hand[capacity:]
    
    def _check_win_condition(self, player):
        fa = player.store.count('fa')
        w = player.store.count('w')
        # Wait for process events to set the win condition
        if self.WIND_N_FABRIC is None or self.WIND_N_WOOD is None:
            return
        if fa >= self.WIND_N_FABRIC and w >= self.WIND_N_WOOD:
            player.status = PlayerStatus.WIN
            log(f'Player {player.name} win the game', '[SERVER]')
            open(f'winner_{player.name}.txt', 'a').write(f'{player.name} won the game in {self.game_board.tick / Config.FPS}s\n')

    def process_events(self):
        if self.current_event is None:
            return
    
        if isinstance(self.current_event, FireEvent) or self.current_event ==FireEvent:
            if self.game_board.tick >= self.end_event_at_tick:
                log(f'Fire event ended at tick {self.game_board.tick}', '[SERVER]')
                self.current_event = None
                self.start_event_at_tick = None
                self.end_event_at_tick = None
                self.game_board.messages = []
                return
            
            self.game_board.message_tick_remaining= self.end_event_at_tick - self.game_board.tick
            
            log(f'Process fire event at tick {self.game_board.tick}', '[SERVER]')
            for _, player_id in self.clients.items():
                player = self.game_board.players[player_id]
                map = Map.from_player(player)
                items = map.get_neighbor_values(player.row, player.col, player.allow_collect_items)
                if 'w' in items:
                    log(f'Player {player.name} is on fire, remove wood', '[SERVER]')
                    player.items_on_hand = []
                    self.game_board.map.set_value(player.row, player.col, 'g')
                    player.row = player.home_row
                    player.col = player.home_col
                    player.status = PlayerStatus.PAUSED
                    player.paused_time = datetime.datetime.now().timestamp()
                    player.paused_duration = 45

        elif isinstance(self.current_event, RewardPunishmentEvent):
            if self.game_board.tick >= self.end_event_at_tick:
                log(f'Diamond event ended at tick {self.game_board.tick}', '[SERVER]')
                self.current_event = None
                self.start_event_at_tick = None
                self.end_event_at_tick = None
                self.game_board.messages = []
                return
            
            self.game_board.message_tick_remaining= self.end_event_at_tick - self.game_board.tick
            event_at_rows = self.current_event.event_at_rows
            event_at_cols = self.current_event.event_at_cols
            
            log(f'Process diamond event at tick {self.game_board.tick}', '[SERVER]')
            for _, player_id in self.clients.items():
                player = self.game_board.players[player_id]
                
                if player.row in event_at_rows and player.col in event_at_cols:
                    log(f'Player {player.name} collected diamond at ({player.row}, {player.col})', '[SERVER]')

                    player_row = player.row
                    player_col = player.col
                    # add or remove diamond from player
                    num_cottons = abs(self.current_event.cotton)
                    num_woods = abs(self.current_event.wood)

                    if self.current_event.cotton > 0 :
                        for _ in range(num_cottons):
                            player.store.append('c')
                        for _ in range(num_woods):
                            player.store.append('w')
                    elif self.current_event.cotton < 0:
                        for _ in range(num_cottons):
                            if 'c' in player.store:
                                player.store.remove('c')
                        for _ in range(num_woods):
                            if 'w' in player.store:
                                player.store.remove('w')
                        player.items_on_hand = []

                        # die 
                        player.row = player.home_row
                        player.col = player.home_col
                        player.status = PlayerStatus.PAUSED
                        player.paused_time = datetime.datetime.now().timestamp()
                        player.paused_duration = 30
                        self.game_board.map.set_value(player_row, player_col, 'g')
                    
                    # stop event
                    if len(self.current_event.event_at_rows) >0:
                        self.current_event.event_at_rows.remove(player_row)
                        self.current_event.event_at_cols.remove(player_col)
                        if len(self.current_event.event_at_rows) == 0:
                            log(f'All players collected diamond, end event at tick {self.game_board.tick}', '[SERVER]')
                            self.current_event = None
                            self.start_event_at_tick = None
                            self.end_event_at_tick = None
                            self.game_board.messages = []
                    
                
    def depatcher_process(self, client_socket):
        while True:
            client_message = receive(client_socket)
            if client_message is None:
                time.sleep(1/Config.FPS)
                continue

            if isinstance(client_message, WinConditionEvent):
                log(f'Broadcast WinConditionEvent message to all players', '[SERVER]')
                self.current_event = client_message
                
                self.WIND_N_FABRIC = self.current_event.fabric
                self.WIND_N_WOOD = self.current_event.wood
                self.FABRIC_TO_COTTON_RATIO = self.current_event.fabric_to_cotton_ratio
                for player_id in self.game_board.players:
                    self.game_board.messages.append(client_message.message)
                    self.game_board.players[player_id].message = client_message.message

            elif isinstance(client_message, Event):
                self.start_event_at_tick = self.game_board.tick
                self.end_event_at_tick = self.start_event_at_tick + client_message.duration 
                self.current_event = client_message
                self.game_board.messages = [client_message.message]
                
                log(f'Fire event started at tick {self.start_event_at_tick}, end at {self.end_event_at_tick}', '[SERVER]')
                
                log(f'Revceive from dispatcher: {client_message}', '[SERVER]')
            
           
            log(f'Broadcast message to all players')
            for player_id in self.game_board.players:
                self.game_board.messages.append(client_message.message)
                self.game_board.players[player_id].message = client_message.message
            
            # self.broadcast_message_start_game()
 
    def client_process(self, client_socket):
        
        player_id = self.clients[client_socket]
        player = self.game_board.players[player_id]
        self.client_ping_time[client_socket] = datetime.datetime.now().timestamp()
        log(f'Handle client with player id is {player_id}', '[SERVER]')
        try:
            while client_socket.fileno() != -1:  # kiểm tra kết nối còn mở

                # only process when time tick
                # Receive message from server
                
                if self.game_board.game_status == GameStatus.FINISHED:
                    continue

                client_message = receive(client_socket)
                if client_message is None:
                    if player.status != PlayerStatus.DISCONNECTED:
                        player.status = PlayerStatus.DISCONNECTED
                        log(f'Client {player_id} disconnected', '[SERVER]')
                    

                if isinstance(client_message, StillAliveMessage):
                    self.client_ping_time[client_socket] = datetime.datetime.now().timestamp()
                    

                # Messges need to process imeddiately

                if player.status == PlayerStatus.WIN:
                    continue

                if isinstance(client_message, SetPlayerNameMessage):
                    if self.game_board.game_status == GameStatus.WAITING_FOR_PLAYERS:
                        player.name = client_message.player_name
                        player.last_updated = datetime.datetime.now().timestamp()
                        log(f'Player {player_id} set name to {player.name}', '[SERVER]')
                        self.create_player_log(player)
                    continue

                if isinstance(client_message, AllowCollectItemsMessage):
                    player.last_updated = datetime.datetime.now().timestamp()
                    player.allow_collect_items = client_message.items
                    self.send(client_socket, player.allow_collect_items)
                    continue

                if isinstance(client_message, GetPlayerMessage):
                    self.send(client_socket, player)
                    continue

                # Process messages by time tick
                if self.game_board.game_status == GameStatus.PLAYING:
                    if isinstance(client_message, MoveMessage):
                        player.in_process_move_messages.append(client_message)
                    
                        continue

                if isinstance(client_message, RemoveInProcessMoveMessage):
                    # remove all in process messages
                    player.in_process_move_messages = []
                    continue
                
        except Exception as e:
            log(f"Error with client {player_id}: {e}", "[SERVER]")

        finally:
            with self.lock:
                if player_id in self.game_board.players:
                    del self.game_board.players[player_id]
                if client_socket in self.clients:
                    del self.clients[client_socket]
            client_socket.close()
            if self.game_board.current_player_index >= len(self.game_board.players):
                self.game_board.current_player_index = -1

    # Process client message
    def handle_client(self, client_socket):
        if client_socket == self.game_client_dispatcher:
            self.depatcher_process(client_socket)
        else:
            self.client_process(client_socket)

    def update_status_all_players(self, status):
        for client_socket, player_id in self.clients.items():
            player = self.game_board.players[player_id]
            player.status = status

    def broadcast_message(self):
        
        for client_socket, player_id in self.clients.items():
            player = self.game_board.players[player_id]
            self.send(client_socket, player)

    def test_mode_play(self, event):
        if self.game_board.current_player_index == -1:
            return
        player = self.game_board.players[self.game_board.current_player_index]
        if player.status != PlayerStatus.PLAYING:
            log(f'Player {player.name} is not playing, cannot move', '[SERVER]')
            return
        dir = 0
        if event.key == pygame.K_LEFT: dir = 0
        if event.key == pygame.K_RIGHT: dir = 1
        if event.key == pygame.K_UP: dir = 2
        if event.key == pygame.K_DOWN: dir = 3
        
        self.update_player(player, dir)

    def update(self):
        for player_id, player in self.game_board.players.items():
            if player.status != PlayerStatus.WIN:
                self.update_player(player)

    def start_game_loop(self):    
        clock = pygame.time.Clock()
        while True:
            events = pygame.event.get()

            self.process_events()

            # Process events
            for event in events:
                if event.type == pygame.QUIT:
                    pygame.quit()
                    return
                if event.type == pygame.KEYDOWN:
                    
                    # START GAME
                    if event.key == pygame.K_s:
                        # change to start game
                        self.game_board.game_status = GameStatus.PLAYING
                        self.game_board.tick =0
                        # notify all players
                        self.update_status_all_players(PlayerStatus.PLAYING)
                    elif event.key == pygame.K_EQUALS: #pygame.K_RIGHT:
                        self.game_board.current_player_index +=1
                        if self.game_board.current_player_index >= len(self.game_board.players):
                            self.game_board.current_player_index = -1
                    elif event.key == pygame.K_MINUS: #pygame.K_LEFT:
                        self.game_board.current_player_index -=1
                        if self.game_board.current_player_index <-1:
                            self.game_board.current_player_index = len(self.game_board.players) -1

                    elif event.key == pygame.K_ESCAPE:
                        for client_socket in list(self.clients.keys()):
                            client_socket.close()
                            log(f'Client {client_socket} disconnected', '[SERVER]')
                        self.server_socket.close()
                        log('Close server', '[SERVER]')

                        pygame.quit()
                        return
                    elif self.test_mode:
                        # allow move player in test mode
                        self.test_mode_play(event)
            
            

            if self.game_board.game_status == GameStatus.PLAYING:
                # Update game state
                self.update()
                if self.game_board.tick /Config.FPS >= Config.GAME_DURATION:
                    self.game_board.game_status = GameStatus.FINISHED
                    log(f'Game FINISHED', '[SERVER]')

            # Draw the game board
            self.game_board.draw()

            pygame.display.flip()
            clock.tick(self.fps)

                 
if __name__ == "__main__":
    server = Server(test_mode=True)
    server.start()