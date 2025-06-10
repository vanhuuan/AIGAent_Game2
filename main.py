import asyncio
import logging
import os
import datetime
from game_client import GameClient
from workflow.game_graph import GameState, CreateGame, Graph

# Configure logging
def setup_logging():
    """Set up logging configuration"""
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)
    
    # Create timestamped log file
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"logs/agent_log_{timestamp}.log"
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger("agent_logger")

async def main():
    """
    Entry point for running the autonomous agent
    """
    # Set up logging
    logger = setup_logging()
    logger.info("Starting Rules of Survival Agent")
    
    # Initialize game client
    client = GameClient()
    client.set_player_name("AIAgent2")
    logger.info(f"Player name set to: {client.player.name}")
    
    # Enable collection of all resource types
    client.allow_collect_items(items=['w', 'f', 'c'])
    logger.info("Enabled collection of wood, food, and cotton")
    
    # Monkey patch the agent run methods to log OpenAI interactions
    original_orchestrator_run = client.orchestrator_agent.agent.run_sync
    original_play_game_run = client.play_game_agent.agent.run_sync
    
    def log_api_call(agent_type, query, result):
        logger.info(f"OpenAI API Call - {agent_type}")
        logger.info(f"Query: {query}")
        logger.info(f"Response: {result.output}")
        return result
    
    # Override the run_sync methods to add logging
    def orchestrator_run_with_logging(query, deps=None):
        logger.info(f"Orchestrator Agent Query: {query}")
        result = original_orchestrator_run(query, deps=deps)
        logger.info(f"Orchestrator Agent Response: {result.output}")
        return result
    
    def play_game_run_with_logging(query, deps=None):
        logger.info(f"Play Game Agent Query: {query}")
        result = original_play_game_run(query, deps=deps)
        logger.info(f"Play Game Agent Response: {result.output}")
        return result
    
    # Replace the original methods with our logging versions
    client.orchestrator_agent.agent.run_sync = orchestrator_run_with_logging
    client.play_game_agent.agent.run_sync = play_game_run_with_logging
    
    # Monkey patch the client's move method to log player actions
    original_move = client.move
    def move_with_logging(direction):
        directions = {0: "left", 1: "right", 2: "up", 3: "down"}
        direction_name = directions.get(direction, str(direction))
        logger.info(f"Player Action: Moving {direction_name}")
        return original_move(direction)
    
    client.move = move_with_logging
    
    # Initialize game state
    game_state = GameState(
        client=client,
        name="Rules of Survival Agent"
    )
    
    # Create and run the workflow graph
    graph = Graph(
        initial_node=CreateGame(),
        state=game_state
    )
    
    try:
        # Run the graph until completion
        logger.info("Starting game workflow")
        await graph.run()
        logger.info("Game completed!")
    except KeyboardInterrupt:
        logger.info("Game stopped by user")
    except Exception as e:
        logger.error(f"Error during game: {e}", exc_info=True)
    finally:
        # Clean up resources
        client.close()
        logger.info("Game client closed")

if __name__ == "__main__":
    asyncio.run(main()) 