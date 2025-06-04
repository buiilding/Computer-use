click_declaration = {
    "name": "click",
    "description": "Simulates a mouse click using EITHER an element index OR explicit x,y coordinates.",
    "parameters": {
        "type": "object",
        "properties": {
            "index": {"type": "integer", "description": "The index of the element in the screenshot to click. Use this OR x and y."},
            "x": {"type": "integer", "description": "The x-coordinate of the click position. Use this OR index."},
            "y": {"type": "integer", "description": "The y-coordinate of the click position. Use this OR index."},
            "wait_time": {"type": "integer", "description": "Time in seconds to wait after performing the action. Defaults to 1."}
        },
        "required": ["wait_time"]
    }
}

type_declaration = {
    "name": "type",
    "description": "Simulates typing the specified text.",
    "parameters": {
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "The text to type."},
            "wait_time": {"type": "integer", "description": "Time in seconds to wait after performing the action. Defaults to 0."}
        },
        "required": ["text"]
    }
}

press_key_declaration = {
    "name": "press_key",
    "description": "Presses a key on the keyboard.",
    "parameters": {
        "type": "object",
        "properties": {
            "key": {"type": "string", "description": "The key to press."},
            "wait_time": {"type": "integer", "description": "Time in seconds to wait after performing the action. Defaults to 0."}
        },
        "required": ["key"]
    }
}

scroll_declaration = {
    "name": "scroll",
    "description": "Scrolls the screen in a specified direction.",
    "parameters": {
        "type": "object",
        "properties": {
            "direction": {"type": "string", "description": "The direction to scroll ('up' or 'down')."},
            "amount": {"type": "integer", "description": "The amount to scroll (number of 'clicks' or lines)."},
            "wait_time": {"type": "integer", "description": "Time in seconds to wait after performing the action. Defaults to 0."}
        },
        "required": ["direction", "amount"]
    }
}

function_declarations = [
    press_key_declaration,
    scroll_declaration,
    click_declaration,
    type_declaration,
] 