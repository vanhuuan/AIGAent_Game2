import asyncio
from dotenv import load_dotenv
import sys
import os

# Ensure the root directory is in the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from agents.event_handler_agent import EventHandlerAgent
from logs import log

async def test_event_handler():
    """Test the event handler agent with various sample messages."""
    # Load environment variables
    load_dotenv('./.env', override=True)
    
    # Initialize the event handler agent
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
    
    print("\n===== EVENT HANDLER TEST =====\n")
    
    # Process each test message
    for i, message in enumerate(test_messages):
        print(f"\nTest {i+1}: \"{message}\"")
        
        # Analyze the message
        result = event_handler.analyze_message(message)
        
        # Print the results
        print(f"  should_go_home: {result.should_go_home}")
        print(f"  has_reward: {result.has_reward}")
        print(f"  reward_position: {result.reward_position}")
        print(f"  duration: {result.duration} seconds")
        print(f"  priority: {result.priority}")
        print(f"  summary: \"{result.summary}\"")
    
    print("\n===== TEST COMPLETE =====")

if __name__ == "__main__":
    asyncio.run(test_event_handler()) 