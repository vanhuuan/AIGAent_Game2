import os
import sys
import json
import logging
from unittest.mock import MagicMock
from dotenv import load_dotenv

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from game.game_workflow import GameWorkflow
from game.game_state import GameState
from logs import log

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

def test_llm_decision_making():
    """Test the LLM-based decision making system."""
    log("Starting LLM decision making test", "[Test]")
    
    # Load environment variables
    load_dotenv()
    if not os.environ.get("OPENAI_API_KEY"):
        log("Warning: OPENAI_API_KEY not found in environment variables", "[Test]", level="WARNING")
        log("This test requires a valid OpenAI API key", "[Test]", level="WARNING")
        return
    
    # Create a mock client
    mock_client = MagicMock()
    
    # Set up mock player
    mock_player = MagicMock()
    mock_player.row = 5
    mock_player.col = 5
    mock_player.store = ['w', 'w', 'c']
    mock_player.items_on_hand = []
    mock_player.home_row = 0
    mock_player.home_col = 0
    
    mock_client.get_player.return_value = mock_player
    
    # Set up entity positions
    mock_client.entity_positions = {
        'w': [(7, 7), (8, 8)],
        'c': [(3, 3)],
        'r': [],  # Rocks are not collectible
        's': [(10, 10)],
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
    
    # Set win condition
    game_state.win_condition = {
        "wood": 5,
        "cotton": 6,
        "fabric_ratio": 3
    }
    
    # Create the workflow
    workflow = GameWorkflow(game_state)
    
    # Test 1: Normal resource collection scenario
    log("Test 1: Normal resource collection scenario", "[Test]")
    action = workflow.decide_next_action()
    log(f"Decision: {action}", "[Test]")
    
    # Test 2: Add an event task
    log("Test 2: With go_home event task", "[Test]")
    game_state.event_tasks = [{
        "type": "go_home",
        "description": "Storm coming, return home immediately"
    }]
    action = workflow.decide_next_action()
    log(f"Decision with go_home event: {action}", "[Test]")
    
    # Test 3: Add a reward collection task
    log("Test 3: With collect_reward event task", "[Test]")
    game_state.event_tasks = [{
        "type": "collect_reward",
        "position": (15, 15),
        "description": "Collect reward at position (15, 15)"
    }]
    action = workflow.decide_next_action()
    log(f"Decision with collect_reward event: {action}", "[Test]")
    
    # Test 4: Player carrying items
    log("Test 4: Player carrying items", "[Test]")
    game_state.event_tasks = []
    mock_player.items_on_hand = ['w', 'c']
    action = workflow.decide_next_action()
    log(f"Decision when carrying items: {action}", "[Test]")
    
    # Test 5: Sword available
    log("Test 5: Sword available nearby", "[Test]")
    mock_player.items_on_hand = []
    mock_client.entity_positions['s'] = [(6, 6)]
    action = workflow.decide_next_action()
    log(f"Decision with sword nearby: {action}", "[Test]")
    
    log("LLM decision making test completed", "[Test]")

if __name__ == "__main__":
    log("Starting test suite", "[Test]")
    test_llm_decision_making()
    log("All tests completed", "[Test]") 