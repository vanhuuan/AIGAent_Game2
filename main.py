from __future__ import annotations
import asyncio
import nest_asyncio
from faker import Faker
from dotenv import load_dotenv
import sys
import os
import time
import argparse
from logs import log

# Ensure the root directory is in the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from game.game_client import GameClient
from game.game_state import GameState
from game.game_workflow import GameWorkflow
from agents.event_handler_agent import EventHandlerAgent

# Enable nested asyncio for Jupyter notebooks support
nest_asyncio.apply()

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Run the game agent with specified name.')
    parser.add_argument('--name', type=str, help='Name of the player')
    return parser.parse_args()

async def main():
    """Main entry point for the game agent."""
    try:
        # Parse command line arguments
        args = parse_args()
        
        # Load environment variables (including OpenAI API key)
        load_dotenv()
        if not os.environ.get("OPENAI_API_KEY"):
            log("Warning: OPENAI_API_KEY not found in environment variables", "[Main]")
            log("LLM-based decision making will fall back to rule-based approach", "[Main]")
        
        # Get player name from command line args, environment variable, or generate random
        if args.name:
            player_name = args.name
        elif os.environ.get("USER_NAME"):
            player_name = os.environ.get("USER_NAME")
        else:
            fake = Faker()
            player_name = fake.first_name()
        
        log(f"Starting game with player name: {player_name}", "[Main]")
        
        # Initialize the game client
        client = GameClient(player_name)
        log("Game client initialized", "[Main]")
        
        # Initialize the event handler
        event_handler = EventHandlerAgent()
        log("Event handler initialized", "[Main]")
        
        # Initialize the game state
        game_state = GameState(client=client, event_handler=event_handler)
        log("Game state initialized", "[Main]")
        
        # Initialize the game workflow
        workflow = GameWorkflow(game_state)
        log("Game workflow initialized", "[Main]")
        
        # Wait for the game to start
        log("Waiting for game to start...", "[Main]")
        player = client.get_player()
        while player.status.value != 'playing':
            time.sleep(1)
            player = client.get_player()
        
        log("Game started!", "[Main]")
        
        # Start the game loop
        workflow.run_game_loop()
        
    except Exception as e:
        log(f"Error in main: {e}", "[Main]")
        raise

if __name__ == "__main__":
    asyncio.run(main()) 