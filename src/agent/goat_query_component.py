from typing import Any, Callable, Dict

from llama_index.core.query_pipeline import CustomQueryComponent
from pydantic import Field


class GoatQueryComponent(CustomQueryComponent):
    fn: Callable = Field(..., description="Function to run")

    @property
    def _input_keys(self) -> set:
        """Input keys dict."""
        return {"input"}

    @property
    def _output_keys(self) -> set:
        return {"output"}

    def _run_component(self, **kwargs) -> Dict[str, Any]:
        """Run the component."""
        error = False
        exception = None
        try:
            self.fn(kwargs["input"]["input"], kwargs["input"]["state"])
        except Exception as e:
            error = True
            exception = str(e)

        return {
            "output": {
                "error": error,
                "exception": exception,
                "input": kwargs["input"]["input"],
                "state": kwargs["input"]["state"],
            }
        }
