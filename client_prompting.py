
class ClientPrompting:
    calculate_win_condition = """
You are an expert in calculating the win condition for a game.
Your task is to calculate the win condition based on the provided task description.
The win condition includes:
    wood_need: the number of wood units required. it must be a positive integer.
    cotton_need: the number of cotton units required. it must be a positive integer. You can calculate fabric needed fisrt an then convert it to cotton_needed.
    fabric_to_cotton_ratio: the number of cotton units required to produce one fabric unit. It must be a positive integer.
    explained: explain why you produced this result
                               
You should thought step by step to calculate the win condition.  

    """

    parser_event_message_prompt="""
You are an expert in analyzing event messages. You will be given a text message describing an event. Your task is to extract and calculate the following:
    - duration: the time of the event in seconds
    - positions: a list of the cell positions mentioned
    - should_do: bool  # true if following the instructions in the message would be beneficial, otherwise false 

    """