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
            if kwargs["input"]["state"]["status"] == "Construct URL":
                kwargs["input"]["state"]["queue"].put(
                    {
                        "done": True,
                        "error": False,
                        "state": kwargs["input"]["state"]["status"],
                        "url": kwargs["input"]["state"]["final_url"],
                    }
                )
            else:
                kwargs["input"]["state"]["queue"].put(
                    {"done": False, "error": False, "state": kwargs["input"]["state"]["status"]}
                )
        except Exception as e:
            error = True
            kwargs["input"]["state"]["queue"].put(
                {
                    "done": False,
                    "error": True,
                    "exception": kwargs["input"]["state"]["status"] + " step failed with following error: " + str(e),
                    "state": "error_state",
                }
            )
            exception = str(e)

        return {
            "output": {
                "error": error,
                "exception": exception,
                "input": kwargs["input"]["input"],
                "state": kwargs["input"]["state"],
            }
        }
