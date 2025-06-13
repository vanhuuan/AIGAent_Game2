import sys
import os
import asyncio
from dotenv import load_dotenv
from logs import log
import logging
from unittest.mock import MagicMock

# Ensure the root directory is in the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from agents.event_handler_agent import EventHandlerAgent
from game.game_client import GameClient
from game.game_state import GameState

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

async def test_event_handler():
    """Test the event handler agent with various sample messages."""
    log("Starting event handler test", "[Test]")
    
    # Load environment variables
    load_dotenv('./.env', override=True)
    log("Environment variables loaded", "[Test]")
    
    # Initialize the event handler agent
    log("Initializing event handler agent", "[Test]")
    event_handler = EventHandlerAgent()
    
    # Test messages
    test_messages = [
        "Go home immediately, or you'll die.",
        "Go to the cell at (10, 18) to obtain one unit of fabric.",
        "All wood is fire, it take about 60s. If you collect it, you will lose all items on hand, go home and paused in 60 seconds",
        "A storm is approaching! You must return to your home base within 30 seconds or risk losing all collected items.",
        "A rare treasure has appeared at position (5, 12). Be the first to collect it for a bonus!",
        "To complete this game, you need to collect 3 units of wood and 2 units of fabric. Every 4 units of cotton can be converted into 1 unit of fabric."
    ]
    
    log("\n===== EVENT HANDLER TEST =====\n", "[Test]")
    
    # Process each test message
    for i, message in enumerate(test_messages):
        log(f"\nTest {i+1}: \"{message}\"", "[Test]")
        
        # Analyze the message
        result = event_handler.analyze_message(message)
        
        # Print the results
        log(f"  should_go_home: {result.should_go_home}", "[Test]")
        log(f"  has_reward: {result.has_reward}", "[Test]")
        log(f"  reward_position: {result.reward_position}", "[Test]")
        log(f"  duration: {result.duration} seconds", "[Test]")
        log(f"  priority: {result.priority}", "[Test]")
        log(f"  summary: \"{result.summary}\"", "[Test]")
    
    log("\n===== TEST COMPLETE =====", "[Test]")

def test_game_state_message_processing():
    """Test the game state's ability to process messages and create tasks."""
    log("Starting game state message processing test", "[Test]")
    
    # Create a mock client
    mock_client = MagicMock()
    mock_client.messages = [
        "To complete this game, you need to collect 2 units of wood and 1 unit of fabric. Every 2 units of cotton can be converted into 1 unit of fabric.",
        "Go home immediately, or you'll die."
    ]
    
    # Create a mock event handler
    mock_event_handler = MagicMock()
    mock_event_handler.analyze_message.side_effect = [
        {
            "event_detected": True,
            "event_type": "win_condition",
            "wood": 2,
            "fabric": 1,
            "cotton_per_fabric": 2,
            "description": "Need 2 wood and 1 fabric to win. 2 cotton makes 1 fabric."
        },
        {
            "event_detected": True,
            "event_type": "go_home",
            "description": "Danger alert - return home immediately"
        }
    ]
    
    mock_event_handler.create_task_from_event.side_effect = [
        {
            "type": "win_condition",
            "wood": 2,
            "fabric": 1,
            "cotton_per_fabric": 2,
            "description": "Need 2 wood and 1 fabric to win. 2 cotton makes 1 fabric."
        },
        {
            "type": "go_home",
            "description": "Danger alert - return home immediately"
        }
    ]
    
    # Create the game state
    game_state = GameState(client=mock_client, event_handler=mock_event_handler)
    
    # Process messages
    game_state.process_messages()
    
    # Check if tasks were created
    log(f"Win condition: {game_state.win_condition}", "[Test]")
    log(f"Event tasks: {game_state.event_tasks}", "[Test]")
    
    log("Game state message processing test completed", "[Test]")

def test_resource_detection():
    """Test the game client's ability to detect resources."""
    log("Starting resource detection test", "[Test]")
    
    # Create a mock client with a mock grid
    mock_client = MagicMock()
    
    # Set up a mock grid with various resources
    import numpy as np
    mock_grid = np.array([
        ['g', 'g', 'w', 'g', 'g'],
        ['g', 'r', 'g', 'c', 'g'],  # 'r' for rock instead of 'f' for food
        ['g', 'g', 'g', 'g', 'g'],
        ['g', 's', 'g', 'a', 'g'],
        ['g', 'g', 'g', 'g', 'g']
    ])
    
    # Set up mock player
    mock_player = MagicMock()
    mock_player.grid = mock_grid
    mock_player.row = 2
    mock_player.col = 2
    
    mock_client.get_player.return_value = mock_player
    mock_client.entity_positions = {
        'w': [],
        'c': [],
        'r': [],  # Rock instead of food
        's': [],
        'a': [],
        '0': [],
        '1': [],
        '2': [],
        '3': [],
        '4': [],
        '5': [],
        '6': []
    }
    
    # Create the game state
    game_state = GameState(client=mock_client)
    
    # Update resource positions
    game_state.update_resource_positions()
    
    # Check detected resources
    log(f"Detected wood positions: {mock_client.entity_positions['w']}", "[Test]")
    log(f"Detected cotton positions: {mock_client.entity_positions['c']}", "[Test]")
    log(f"Detected rock positions: {mock_client.entity_positions['r']}", "[Test]")  # Should be empty as rocks aren't collectible
    log(f"Detected sword positions: {mock_client.entity_positions['s']}", "[Test]")
    log(f"Detected armor positions: {mock_client.entity_positions['a']}", "[Test]")
    
    log("Resource detection test completed", "[Test]")

if __name__ == "__main__":
    log("Starting test suite", "[Test]")
    
    test_event_handler()
    test_game_state_message_processing()
    test_resource_detection()
    
    log("All tests completed", "[Test]")

    # Use nest_asyncio to avoid "This event loop is already running" error
    import nest_asyncio
    nest_asyncio.apply()
    
    # Run the test
    asyncio.run(test_event_handler()) 