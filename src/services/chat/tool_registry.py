import inspect
from typing import get_type_hints
from pydantic import BaseModel

_TOOL_REGISTRY = {}


def _type_to_json_schema_type(py_type):
    type_str = str(py_type)

    if py_type is int:
        return "integer"
    if py_type is float:
        return "number"
    if py_type is bool:
        return "boolean"
    if "List" in type_str:
        return "array"
    return "string"


def register_tool(name: str, description: str, args_schema: type[BaseModel] = None):
    def decorator(func):
        if args_schema:
            parameters = args_schema.model_json_schema()
        else:
            sig = inspect.signature(func)
            hints = get_type_hints(func)

            properties = {}
            required = []

            for param_name, param in sig.parameters.items():
                param_type = hints.get(param_name, str)

                json_type = _type_to_json_schema_type(param_type)
                prop_def = {"type": json_type}

                if json_type == "array":
                    prop_def["items"] = {"type": "string"}

                properties[param_name] = prop_def

                if param.default == inspect.Parameter.empty:
                    required.append(param_name)

            parameters = {"type": "object", "properties": properties, "required": required}

        schema = {
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": parameters
            }
        }

        _TOOL_REGISTRY[name] = {
            "function": func,
            "schema": schema
        }

        return func
    return decorator


def get_all_tool_schemas() -> list[dict]:
    tool_schemas = []
    for key, value in _TOOL_REGISTRY.items():
        tool_schemas.append(value['schema'])

    return tool_schemas


def execute_tool(tool_name: str, arguments: dict):
    if tool_name not in _TOOL_REGISTRY:
        return {"error": f"Tool {tool_name} not found"}
    
    function_to_call = _TOOL_REGISTRY[tool_name]['function']
    return function_to_call(**arguments)


__all__ = ["register_tool", "get_all_tool_schemas", "execute_tool"]
