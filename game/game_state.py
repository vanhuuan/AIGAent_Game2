import sys
import os
from enum import Enum

# Ensure the root directory is in the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from logs import log
from agents.event_handler_agent import EventHandlerAgent

class ObservationResult(Enum):
    EXPLORE = "EXPLORE"
    GET_MORE_WOOD = "GET_MORE_WOOD"
    GET_MORE_COTTON = "GET_MORE_COTTON"
    COLLECT_SWORD = "COLLECT_SWORD"
    COLLECT_ARMOR = "COLLECT_ARMOR"
    GO_HOME = "GO_HOME"
    COLLECT_REWARD = "COLLECT_REWARD"

class Resource:
    def __init__(self):
        self.wood = 0
        self.cotton = 0
        self.fabric = 0
        self.sword = 0
        self.armor = 0

class GameState:
    def __init__(self, client=None, event_handler=None):
        """Initialize the game state with a client and event handler."""
        self.client = client
        self.event_handler = event_handler or EventHandlerAgent()
        self.win_condition = {}
        self.event_tasks = []
        self.last_processed_message = None
        log("GameState initialized", "[GameState]")
        
    def process_messages(self):
        """Process any new messages from the server."""
        if not self.client:
            log("No client available to process messages", "[GameState]")
            return
            
        # Get current message from the client's player
        current_message = self.client.player.message
        
        # Only process if we have a new message
        if current_message and current_message != self.last_processed_message:
            log(f"Processing new message: {current_message}", "[GameState]")
            
            # Analyze the message for events
            event_result = self.event_handler.analyze_message(current_message)
            
            if event_result.get("event_detected"):
                event_type = event_result.get("event_type")
                log(f"Event detected: {event_type}", "[GameState]")
                
                # Handle win condition information
                if event_type == "win_condition":
                    self.win_condition = {
                        "wood": event_result.get("wood", 0),
                        "cotton": event_result.get("cotton_per_fabric", 0) * event_result.get("fabric", 0),
                        "fabric_ratio": event_result.get("cotton_per_fabric", 0)
                    }
                    log(f"Updated win condition: {self.win_condition}", "[GameState]")
                
                # Create a task from the event
                task = self.event_handler.create_task_from_event(event_result)
                if task:
                    self.event_tasks.append(task)
                    log(f"Added task: {task}", "[GameState]")
            
            # Update the last processed message
            self.last_processed_message = current_message
            
    def update_resource_positions(self):
        """Update the positions of resources based on the player's grid."""
        if not self.client:
            log("No client available to update resource positions", "[GameState]")
            return
            
        player = self.client.get_player()
        
        # Use the find_adjacent_resources function to update entity positions
        from pathfinding import find_adjacent_resources
        resources = find_adjacent_resources(player.grid, player.row, player.col)
        
        # Update entity positions in the client
        for resource_type, positions in resources.items():
            # Skip rocks as they're not collectible
            if resource_type == 'r':
                continue
                
            for position in positions:
                if position not in self.client.entity_positions[resource_type]:
                    self.client.entity_positions[resource_type].append(position)
                    log(f"Added {resource_type} at {position} to known positions", "[GameState]")
                    
    def get_resource_needs(self):
        """Calculate the resources still needed to win."""
        if not self.client or not self.win_condition:
            return {"wood": 0, "cotton": 0}
            
        player = self.client.get_player()
        
        wood_needed = max(0, self.win_condition.get("wood", 0) - 
                         player.store.count('w') - 
                         player.items_on_hand.count('w'))
                         
        cotton_needed = max(0, self.win_condition.get("cotton", 0) - 
                           player.store.count('c') - 
                           player.items_on_hand.count('c'))
                           
        return {"wood": wood_needed, "cotton": cotton_needed} 