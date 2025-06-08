import pyautogui
import os
import sys
import time

def click(element_id: int, elements: list, wait_time: int = 0):
    """Simulate a mouse click on a specific UI element.
    
    Args:
        element_id (int): The index of the element to click in the elements list.
        elements (list): The list of current UI elements on the screen.
        wait_time (int): Time to wait after the action in seconds. Defaults to 0.
    """
    click_status = {}
    
    try:
        element_id = int(element_id)
        if not elements:
            raise ValueError("The 'elements' list is empty.")
        if not 0 <= element_id < len(elements):
            raise IndexError(f"Element ID {element_id} is out of bounds for elements list of size {len(elements)}.")
            
        element = elements[element_id]
        target_x = element.get('x')
        target_y = element.get('y')

        if target_x is None or target_y is None:
            raise ValueError(f"Element with ID {element_id} does not have 'x' or 'y' coordinates.")

        print(f"Attempting click on element {element_id}: {element.get('content', 'N/A')}")
        target_x = int(target_x)
        target_y = int(target_y)
        pyautogui.moveTo(target_x, target_y)
        pyautogui.click(target_x, target_y)
        print(f"🖱️ Clicked element {element_id} at coordinates: ({target_x}, {target_y})")
        click_status = {"status": "success", "message": f"Clicked element {element_id} at ({target_x}, {target_y})"}

    except (ValueError, IndexError) as e:
        print(f"🔴 Error: {e}")
        click_status = {"status": "error", "message": str(e)}
    except Exception as e:
        print(f"🔴 Error clicking element {element_id}: {e}")
        click_status = {"status": "error", "message": str(e)}

    if wait_time > 0:
        time.sleep(wait_time)
    return click_status

def right_click(element_id: int, elements: list, wait_time: int = 0):
    """Simulate a right mouse click on a specific UI element.
    
    Args:
        element_id (int): The index of the element to click in the elements list.
        elements (list): The list of current UI elements on the screen.
        wait_time (int): Time to wait after the action in seconds. Defaults to 0.
    """
    click_status = {}
    
    try:
        element_id = int(element_id)
        if not elements:
            raise ValueError("The 'elements' list is empty.")
        if not 0 <= element_id < len(elements):
            raise IndexError(f"Element ID {element_id} is out of bounds for elements list of size {len(elements)}.")
            
        element = elements[element_id]
        target_x = element.get('x')
        target_y = element.get('y')

        if target_x is None or target_y is None:
            raise ValueError(f"Element with ID {element_id} does not have 'x' or 'y' coordinates.")

        print(f"Attempting right-click on element {element_id}: {element.get('content', 'N/A')}")
        target_x = int(target_x)
        target_y = int(target_y)
        pyautogui.moveTo(target_x, target_y)
        pyautogui.rightClick(x=target_x, y=target_y)
        print(f"🖱️ Right-clicked element {element_id} at coordinates: ({target_x}, {target_y})")
        click_status = {"status": "success", "message": f"Right-clicked element {element_id} at ({target_x}, {target_y})"}

    except (ValueError, IndexError) as e:
        print(f"🔴 Error: {e}")
        click_status = {"status": "error", "message": str(e)}
    except Exception as e:
        print(f"🔴 Error right-clicking element {element_id}: {e}")
        click_status = {"status": "error", "message": str(e)}
    
    if wait_time > 0:
        time.sleep(wait_time)
    return click_status

def type_text(text: str, wait_time: int = 0):
    """Simulate typing the specified text.
    
    Args:
        text (str): The text to type.
        wait_time (int): Time to wait after the action in seconds. Defaults to 0.
    """
    type_status = {}
    try:
        pyautogui.write(text)
        print(f"⌨️ Typed text: {text}")
        type_status = {"status": "success", "message": f"Successfully typed: {text}"}
    except Exception as e:
        print(f"🔴 Error typing text: {e}")
        type_status = {"status": "error", "message": str(e)}
    
    if wait_time > 0:
        time.sleep(wait_time)
    return type_status

def press_key(key: str, wait_time: int = 0):
    """Simulate pressing a key. Uses xdotool for broader key support on Linux.
    
    Args:
        key (str): The key to press.
        wait_time (int): Time to wait after the action in seconds. Defaults to 0.
    """
    press_status = {}
    if sys.platform == "linux":
        try:
            key_mapping = {
                'enter': 'Return', 'return': 'Return',
                'space': 'space', 'tab': 'Tab',
                'esc': 'Escape', 'escape': 'Escape',
                'backspace': 'BackSpace', 'delete': 'Delete',
                'home': 'Home', 'end': 'End',
                'pageup': 'Page_Up', 'pagedown': 'Page_Down',
                'left': 'Left', 'right': 'Right', 'up': 'Up', 'down': 'Down',
                "windows": "Super_L", "win": "Super_L", "super": "Super_L"
            }
            normalized_key = key.lower()
            xdotool_key = key_mapping.get(normalized_key, key)
            
            if os.system("command -v xdotool > /dev/null") == 0:
                os.system(f"xdotool key {xdotool_key}")
                print(f"⌨️ Pressed key (via xdotool): {xdotool_key}")
                press_status = {"status": "success", "message": f"Successfully pressed (xdotool): {xdotool_key}"}
            else:
                print("xdotool not found, falling back to pyautogui.")
                raise Exception("xdotool not found")
        except Exception as e_xdotool:
            print(f"Attempting pyautogui due to xdotool issue: {e_xdotool}")
            try:
                pyautogui.press(key)
                print(f"⌨️ Pressed key (via pyautogui): {key}")
                press_status = {"status": "success", "message": f"Successfully pressed (pyautogui): {key}"}
            except Exception as e_pyautogui:
                print(f"🔴 Error pressing key with pyautogui: {e_pyautogui}")
                press_status = {"status": "error", "message": str(e_pyautogui)}
    else:
        try:
            pyautogui.press(key)
            print(f"⌨️ Pressed key (via pyautogui): {key}")
            press_status = {"status": "success", "message": f"Successfully pressed (pyautogui): {key}"}
        except Exception as e:
            print(f"🔴 Error pressing key with pyautogui: {e}")
            press_status = {"status": "error", "message": str(e)}
            
    if wait_time > 0:
        time.sleep(wait_time)
    return press_status

def hotkey(keys: list, wait_time: int = 0):
    """Simulate pressing a combination of keys simultaneously (hotkey).
    
    Args:
        keys (list or str): A list of strings (e.g., ['ctrl', 'c']) or a single string (e.g., "ctrl+alt+t") representing the keys.
        wait_time (int): Time to wait after the action in seconds. Defaults to 0.
    """
    hotkey_status = {}
    
    # If keys is a string, attempt to parse it into a list
    if isinstance(keys, str):
        keys = [key.strip() for key in keys.replace(' ', '').split('+')]

    if not isinstance(keys, list) or not all(isinstance(k, str) for k in keys):
        msg = f"Invalid 'keys' parameter: must be a list of strings, but received {type(keys)}."
        print(f"🔴 Error: {msg}")
        return {"status": "error", "message": msg}

    try:
        pyautogui.hotkey(*keys)
        print(f"⌨️ Pressed hotkey combination: {' + '.join(keys)}")
        hotkey_status = {"status": "success", "message": f"Successfully pressed hotkey: {' + '.join(keys)}"}
    except Exception as e:
        print(f"🔴 Error pressing hotkey: {e}")
        hotkey_status = {"status": "error", "message": str(e)}

    if wait_time > 0:
        time.sleep(wait_time)
    return hotkey_status

def scroll(direction: str, amount: int, wait_time: int = 0):
    """Simulate scrolling in a specified direction.
    
    Args:
        direction (str): The direction to scroll ('up' or 'down').
        amount (int): The amount to scroll (number of 'clicks' or lines).
        wait_time (int): Time to wait after the action in seconds. Defaults to 0.
    """
    scroll_status = {}
    try:
        scroll_amount_clicks = amount if direction.lower() == "up" else -amount
        pyautogui.scroll(scroll_amount_clicks)
        print(f"↕️ Scrolled {direction} by {amount} units (clicks: {scroll_amount_clicks})")
        scroll_status = {"status": "success", "message": f"Successfully scrolled {direction} by {amount} units"}
    except Exception as e:
        print(f"🔴 Error scrolling: {e}")
        scroll_status = {"status": "error", "message": str(e)}
    
    if wait_time > 0:
        time.sleep(wait_time)
    return scroll_status

def task_done(reason: str):
    """A special function to be called when the task is complete.
    
    Args:
        reason (str): A brief explanation of why the task is considered finished.
        
    Returns:
        dict: A dictionary indicating the task is done.
    """
    print(f"✅ Task considered complete. Reason: {reason}")
    return {"status": "done", "message": reason} 

def wait(wait_time: int):
    """Wait for a specified amount of time."""
    time.sleep(wait_time)
    return {"status": "success", "message": f"Successfully waited for {wait_time} seconds"}


if __name__ == "__main__":
    print(hotkey("ctrl+alt+t"))
    print(hotkey(['ctrl', 'alt', 't']))
