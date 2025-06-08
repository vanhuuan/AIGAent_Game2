import asyncio
from game_client import GameClient
from workflow.game_graph import GameState, CreateGame, Graph

async def main():
    """
    Entry point for running the autonomous agent
    """
    print("Starting Rules of Survival Agent")
    
    # Initialize game client
    client = GameClient()
    client.set_player_name("AIAgent")
    
    # Enable collection of all resource types
    client.allow_collect_items(items=['w', 'f', 'c'])
    
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
        await graph.run()
        print("Game completed!")
    except KeyboardInterrupt:
        print("Game stopped by user")
    except Exception as e:
        print(f"Error during game: {e}")
    finally:
        # Clean up resources
        client.close()
        print("Game client closed")

if __name__ == "__main__":
    asyncio.run(main()) 