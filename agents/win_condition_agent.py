from pydantic import BaseModel
from pydantic_ai import Agent, RunContext, ModelRetry
from config import Config
from client_prompting import ClientPrompting

class WinCondition(BaseModel):
    wood_need: int
    cotton_need: int
    fabric_to_cotton_ratio: int
    explained: str = ""

class CalculateWinConditionAgent:
    def __init__(self):
        config = Config()

        agent = Agent(
            f'openai:{config.LLM_MODEL}',
            output_type=WinCondition,  
            system_prompt=(ClientPrompting.calculate_win_condition),
            result_retries=5,
        )

        self.agent = agent

        @agent.output_validator
        def validate_output(ctx: RunContext[None], result: WinCondition) -> WinCondition:
            if not result:
                raise ModelRetry(
                    "The result is empty. Please try again.")
            if result.wood_need <= 0:
                raise ModelRetry(
                    "The wood_need must be a positive integer. Please try again.")
            if result.cotton_need <= 0:
                raise ModelRetry(
                    "The cotton_need must be a positive integer. Please try again.")
            if not result.explained:
                raise ModelRetry(
                    "The explained field must not be empty. Please try again.")

            return result

    def calculate(self, message: str) -> WinCondition:
        return self.agent.run_sync(message).output 