click_declaration = {
    "name": "click",
    "description": "Simulates a mouse click using explicit x,y coordinates.",
    "parameters": {
        "type": "object",
        "properties": {
            "x": {"type": "integer", "description": "The x-coordinate of the click position."},
            "y": {"type": "integer", "description": "The y-coordinate of the click position."},
            "wait_time": {"type": "integer", "description": "Time in seconds to wait after performing the action. Defaults to 1."}
        },
        "required": ["x", "y", "wait_time"]
    }
}

right_click_declaration = {
    "name": "right_click",
    "description": "Simulates a right mouse click using explicit x,y coordinates.",
    "parameters": {
        "type": "object",
        "properties": {
            "x": {"type": "integer", "description": "The x-coordinate of the right-click position."},
            "y": {"type": "integer", "description": "The y-coordinate of the right-click position."},
            "wait_time": {"type": "integer", "description": "Time in seconds to wait after performing the action. Defaults to 0."}
        },
        "required": ["x", "y"]
    }
}

type_declaration = {
    "name": "type_text",
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

hotkey_declaration = {
    "name": "hotkey",
    "description": "Presses a combination of keys simultaneously (e.g., Ctrl+C, Alt+F4).",
    "parameters": {
        "type": "object",
        "properties": {
            "keys": {
                "type": "array",
                "items": {"type": "string"},
                "description": "A list of keys to press together. For example: ['ctrl', 'c']"
            },
            "wait_time": {"type": "integer", "description": "Time in seconds to wait after the action. Defaults to 0."}
        },
        "required": ["keys"]
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

wait_declaration = {
    "name": "wait",
    "description": "Waits for the specified amount of time.",
    "parameters": {
        "type": "object",
        "properties": {"wait_time": {"type": "integer", "description": "Time in seconds to wait."}},
        "required": ["wait_time"]
    }
}

task_done_declaration = {
    "name": "task_done",
    "description": "Call this function when the user's original request has been successfully completed.",
    "parameters": {
        "type": "object",
        "properties": {
            "reason": {"type": "string", "description": "A brief explanation of why the task is considered complete."}
        },
        "required": ["reason"]
    }
}

function_declarations = [
    press_key_declaration,
    hotkey_declaration,
    scroll_declaration,
    click_declaration,
    right_click_declaration,
    type_declaration,
    wait_declaration,
    task_done_declaration,
] 