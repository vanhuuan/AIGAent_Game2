import os
import sys
import json
from typing import Dict, Any, List, Optional, Tuple

# Add the root directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pydantic import BaseModel
from pydantic_ai import Agent, RunContext, ModelRetry
from config import Config
from client_prompting import ClientPrompting
from logs import log
import openai

class EventTask(BaseModel):
    """Model for parsed event tasks from server messages"""
    should_go_home: bool = False
    has_reward: bool = False
    reward_position: tuple[int, int] = None
    duration: int = 0  # Duration of the event in seconds, if applicable
    summary: str = ""  # Summary of what needs to be done
    priority: int = 1  # Priority level: 1=low, 2=medium, 3=high

class EventHandlerAgent:
    """Agent for parsing event messages from the server"""
    
    def __init__(self, api_key=None):
        """Initialize the event handler agent with OpenAI API key."""
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key is required")
        
        openai.api_key = self.api_key
        log("EventHandlerAgent initialized", "[EventHandler]")
        
    def analyze_message(self, message: str) -> Dict[str, Any]:
        """
        Analyze a message from the game server to determine if it contains an event
        that requires action.
        
        Returns a dictionary with event details if an event is detected, or an empty dict.
        """
        if not message:
            return {}
            
        log(f"Analyzing message: {message}", "[EventHandler]")
        
        # Define the system prompt for the LLM
        system_prompt = """
        You are an AI assistant analyzing messages from a 2D game. Your task is to identify if a message contains an event that requires action.
        
        The game involves:
        - Players collecting resources (wood 'w', cotton 'c')
        - Rocks 'r' that cannot be collected
        - Building a boat to escape an island
        - Responding to events like storms (requiring going home) or reward boxes (requiring going to a specific location)
        
        If the message contains an event, extract the relevant information and return it in a structured format.
        
        Return ONLY a JSON object with the following structure:
        
        For "go home" events (like storms):
        {
            "event_detected": true,
            "event_type": "go_home",
            "description": "Brief description of the event"
        }
        
        For "collect reward" events:
        {
            "event_detected": true,
            "event_type": "collect_reward",
            "location": [row, col],
            "description": "Brief description of the reward"
        }
        
        For "win condition" events (describing what's needed to win):
        {
            "event_detected": true,
            "event_type": "win_condition",
            "wood": number_of_wood_needed,
            "fabric": number_of_fabric_needed,
            "cotton_per_fabric": number_of_cotton_per_fabric,
            "description": "Brief description of the win condition"
        }
        
        If no event is detected:
        {
            "event_detected": false
        }
        """
        
        try:
            # Call the OpenAI API to analyze the message
            response = openai.chat.completions.create(
                model=Config.LLM_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message}
                ],
                temperature=0.1,
                max_tokens=500
            )
            
            # Extract the response content
            content = response.choices[0].message.content
            log(f"LLM response: {content}", "[EventHandler]")
            
            # Parse the JSON response
            try:
                result = json.loads(content)
                if result.get("event_detected"):
                    log(f"Event detected: {result.get('event_type')}", "[EventHandler]")
                else:
                    log("No event detected in message", "[EventHandler]")
                return result
            except json.JSONDecodeError as e:
                log(f"Error parsing JSON response: {e}", "[EventHandler]", level="ERROR")
                return {"event_detected": False}
                
        except Exception as e:
            log(f"Error calling OpenAI API: {e}", "[EventHandler]", level="ERROR")
            return {"event_detected": False}
            
    def create_task_from_event(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Convert an event detection result into a task that can be added to the game state.
        """
        if not event or not event.get("event_detected"):
            return None
            
        event_type = event.get("event_type")
        log(f"Creating task from event type: {event_type}", "[EventHandler]")
        
        if event_type == "go_home":
            return {
                "type": "go_home",
                "description": event.get("description", "Return to home base immediately")
            }
            
        elif event_type == "collect_reward":
            location = event.get("location")
            if not location or not isinstance(location, list) or len(location) != 2:
                log("Invalid location format in collect_reward event", "[EventHandler]", level="ERROR")
                return None
                
            return {
                "type": "collect_reward",
                "position": tuple(location),
                "description": event.get("description", "Collect reward at specified location")
            }
            
        elif event_type == "win_condition":
            return {
                "type": "win_condition",
                "wood": event.get("wood", 0),
                "fabric": event.get("fabric", 0),
                "cotton_per_fabric": event.get("cotton_per_fabric", 1),
                "description": event.get("description", "Win condition information")
            }
            
        else:
            log(f"Unknown event type: {event_type}", "[EventHandler]", level="WARNING")
            return None

    def analyze_message_old(self, message: str) -> EventTask:
        """Analyze a message from the server and determine the required action"""
        if not message or message.strip() == "":
            log("Empty message received, returning default low-priority task", "[EventHandler]")
            # Return default low-priority task if message is empty
            return EventTask(
                should_go_home=False,
                has_reward=False,
                summary="No message to process",
                priority=1
            )
        
        log(f"Analyzing message: '{message}'", "[EventHandler]")
        result = self.agent.run_sync(message).output
        
        # Log the analysis results
        log(f"Analysis complete - Priority: {result.priority}", "[EventHandler]")
        log(f"Should go home: {result.should_go_home}", "[EventHandler]")
        log(f"Has reward: {result.has_reward}", "[EventHandler]")
        if result.has_reward:
            log(f"Reward position: {result.reward_position}", "[EventHandler]")
        if result.duration > 0:
            log(f"Event duration: {result.duration} seconds", "[EventHandler]")
        log(f"Summary: {result.summary}", "[EventHandler]")
        
        return result 