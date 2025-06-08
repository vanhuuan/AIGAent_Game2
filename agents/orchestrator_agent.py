from dataclasses import dataclass
from pydantic_ai import Agent, RunContext, ModelRetry
from config import Config
from models.tasks import (
    Task, CalCulateWinConditionTask, CollectFoodTask, CollectWoodTask, 
    CollectCottonTask, GoHomeTask, DiscoverMapTask, UnknownTask, WinCondition
)

@dataclass
class OrchestratorAgent:
    """
    High-level decision-making agent that determines what task the player 
    should perform next based on the current state of the game and resource needs.
    """
    
    # Define constants for actions
    KILL_OTHERS_TASK = "kill other players"
    COLLECT_FOOD_TASK = "collect food"
    COLLECT_WOOD_TASK = "collect wood"
    COLLECT_COTTON_TASK = "collect cotton"
    GOTO_CELL_TASK = "Go to cell to collect resource"
    DISCOVER_MAP_TASK = "discover map"
    CALCULATE_WIN_CONDITION = "calculate condition to win the game"
    
    GO_HOME_TASK = "go home"
    UNKNOWN_TASK = "unknown"
    config = Config()
    
    agent = Agent(
        f'openai:{config.LLM_MODEL}',
        output_type=CalCulateWinConditionTask | CollectFoodTask | CollectWoodTask | CollectCottonTask | GoHomeTask | Task | DiscoverMapTask | UnknownTask,
        system_prompt=(
            "You are a helpful ai assistant\n"
            "Suggest the task to win the game"
        ),
        result_retries=2,
    )

    @agent.system_prompt
    def system_prompt(ctx: RunContext[WinCondition]) -> str:
        wood_need = max(0, ctx.deps.wood_need - ctx.deps.player.store.count('w'))
        cotton_need = max(0, ctx.deps.cotton_need - ctx.deps.player.store.count('c'))

        return f"""Identify the task should be to do
You are an agent to play a 2D game. The map is a matrix 2D, cell values can be:
  - 'g': cell is ground and you can step into it
  - '-1': invisibe cell, you can can step into it 
  - 'f', 'w', 'c': food, wood, cotton cell. You can collect it.

The **IMPORTANCE TASK IS COLLECT ONLY NEEDED RESOURCE** as wood, cotton to win the game. 



Base on the current map, your current resource or notify you suggest which task should to take.
The task is choosen from these options: `{OrchestratorAgent.KILL_OTHERS_TASK}`, `{OrchestratorAgent.COLLECT_FOOD_TASK}`, `{OrchestratorAgent.COLLECT_WOOD_TASK}`, `{OrchestratorAgent.COLLECT_COTTON_TASK}`, `{OrchestratorAgent.DISCOVER_MAP_TASK}`, `{OrchestratorAgent.GOTO_CELL_TASK}`, `{OrchestratorAgent.CALCULATE_WIN_CONDITION}`, `{OrchestratorAgent.GO_HOME_TASK}` and `{OrchestratorAgent.UNKNOWN_TASK}`

- If task is "calculate condition to win the game" try to number wood, cotton need to collect.

- If you do not see any resource you should suggest the Discorver Task 

- If task is goto cell you should extract position of cell and return it

Below helpfull info help you decine to select task:
 - Resource need to collect:
     - wood needed to collect: {wood_need}\n"
     - cotton needed to collect: {cotton_need}\n"

 - Your info : {ctx.deps.player}"
            "Action will be invalid for all invalid messages"
"""
    
    @agent.output_validator
    def validate_output(ctx: RunContext[None], result: Task) -> Task:
        print(f'Validate task: {result}')
        if isinstance(result, UnknownTask):
            raise ModelRetry(
                f"Try to determine task or suggest discover map task"
            )
        
        return result 