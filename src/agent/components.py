import json
import urllib
from typing import Any, Dict, List

from llama_index.core.agent import AgentChatResponse, ReActChatFormatter, Task
from llama_index.core.agent.react.output_parser import ReActOutputParser
from llama_index.core.agent.react.types import (
    ActionReasoningStep,
    ObservationReasoningStep,
    ResponseReasoningStep,
)
from llama_index.core.llms import ChatMessage, ChatResponse, MessageRole
from llama_index.core.query_pipeline import (
    AgentFnComponent,
    AgentInputComponent,
    ToolRunnerComponent,
)
from llama_index.core.tools import BaseTool

from agent.tools import query_engine_tools
from prompt import AGENT_SYSTEM_PROMPT


def agent_input_fn(task: Task, state: Dict[str, Any]) -> Dict[str, Any]:
    """Agent input function.

    Returns:
        A Dictionary of output keys and values. If you are specifying
        src_key when defining links between this component and other
        components, make sure the src_key matches the specified output_key.

    """
    # initialize current_reasoning
    if "current_reasoning" not in state:
        state["current_reasoning"] = []
    reasoning_step = ObservationReasoningStep(observation=task.input)
    state["current_reasoning"].append(reasoning_step)
    return {"input": task.input}


agent_input_component = AgentInputComponent(fn=agent_input_fn)


def react_prompt_fn(
    task: Task, state: Dict[str, Any], input: str, tools: List[BaseTool]
) -> List[ChatMessage]:
    # Add input to reasoning
    chat_formatter = ReActChatFormatter.from_defaults(
        system_header=AGENT_SYSTEM_PROMPT, context=AGENT_SYSTEM_PROMPT
    )
    return chat_formatter.format(
        tools,
        chat_history=task.memory.get() + state["memory"].get_all(),
        current_reasoning=state["current_reasoning"],
    )


react_prompt_component = AgentFnComponent(
    fn=react_prompt_fn, partial_dict={"tools": query_engine_tools}
)


def parse_react_output_fn(
    task: Task, state: Dict[str, Any], chat_response: ChatResponse
):
    """Parse ReAct output into a reasoning step."""
    output_parser = ReActOutputParser()
    reasoning_step = output_parser.parse(chat_response.message.content)
    return {"done": reasoning_step.is_done, "reasoning_step": reasoning_step}


parse_react_output = AgentFnComponent(fn=parse_react_output_fn)


def run_tool_fn(task: Task, state: Dict[str, Any], reasoning_step: ActionReasoningStep):
    """Run tool and process tool output."""
    tool_runner_component = ToolRunnerComponent(
        query_engine_tools, callback_manager=task.callback_manager
    )
    tool_output = tool_runner_component.run_component(
        tool_name=reasoning_step.action,
        tool_input=reasoning_step.action_input,
    )
    observation_step = ObservationReasoningStep(observation=str(tool_output))
    state["current_reasoning"].append(observation_step)
    # TODO: get output

    return {"response_str": observation_step.get_content(), "is_done": False}


run_tool = AgentFnComponent(fn=run_tool_fn)


def process_response_fn(
    task: Task, state: Dict[str, Any], response_step: ResponseReasoningStep
):
    """Process response."""
    state["current_reasoning"].append(response_step)
    response_str = response_step.response
    # Now that we're done with this step, put into memory
    state["memory"].put(ChatMessage(content=task.input, role=MessageRole.USER))
    state["memory"].put(ChatMessage(content=response_str, role=MessageRole.ASSISTANT))

    return {"response_str": response_str, "is_done": True}


process_response = AgentFnComponent(fn=process_response_fn)


def process_agent_response_fn(task: Task, state: Dict[str, Any], response_dict: dict):
    """Process agent response."""
    return (
        AgentChatResponse(response_dict["response_str"]),
        response_dict["is_done"],
    )


process_agent_response = AgentFnComponent(fn=process_agent_response_fn)


def construct_url(
    task: Task, state: Dict[str, Any], response_step: ResponseReasoningStep
):
    json_output = json.loads(response_step.response.strip("```"))
    base_url = "https://goat.genomehubs.org/"
    endpoint = "search?"
    suffix = (
        "&result=taxon&summaryValues=count&taxonomy=ncbi&offset=0"
        + "&fields=assembly_level%2Cassembly_span%2Cgenome_size%2C"
        + "chromosome_number%2Chaploid_number&names=common_name&ranks="
        + "&includeEstimates=false&size=100"
    )

    if json_output["intent"] == "count":
        endpoint = "api/v2/count?"
    elif json_output["intent"] == "record":
        endpoint = "record?"

    params = []

    if "taxon" in json_output:
        params.append(f"tax_tree(* {json_output['taxon']})")
    if "rank" in json_output:
        params.append(f"tax_rank({json_output['rank']})")
    if "field" in json_output:
        params.append(f"{json_output['field']}")
    if "time_frame_query" in json_output:
        params.append(f"{json_output['time_frame_query']}")
        suffix = (
            "&result=assembly&summaryValues=count&taxonomy=ncbi&offset=0"
            + "&fields=assembly_level%2Cassembly_span%2Cgenome_size%2C"
            + "chromosome_number%2Chaploid_number&names=common_name&ranks="
            + "&includeEstimates=false&size=100"
        )

    query_string = " AND ".join(params)
    return {
        "response_str": base_url
        + endpoint
        + "query="
        + urllib.parse.quote(query_string)
        + suffix,
        "is_done": True,
    }


construct_url_component = AgentFnComponent(fn=construct_url)
