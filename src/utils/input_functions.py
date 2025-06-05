import pyautogui
import os
import sys
import time

def click(x: int, y: int, wait_time: int = 1):
    """Simulate a mouse click at the specified x and y coordinates.
    
    Args:
        x (int): The x-coordinate for the click.
        y (int): The y-coordinate for the click.
        wait_time (int): Time to wait after the action in seconds. Defaults to 1.
    """
    click_status = {}
    target_x, target_y = x, y # Directly use provided x, y

    print(f"Attempting click by coordinates: ({target_x}, {target_y})")

    if target_x is not None and target_y is not None: # Check if x and y are provided (though they are mandatory by signature now)
        try:
            # Ensure x and y are integers before passing to pyautogui
            target_x = int(target_x)
            target_y = int(target_y)
            pyautogui.moveTo(target_x, target_y)
            pyautogui.click(target_x, target_y)
            print(f"🖱️ Clicked at coordinates: ({target_x}, {target_y})")
            click_status = {"status": "success", "message": f"Clicked at ({target_x}, {target_y})"}
        except ValueError:
            msg = f"Invalid coordinate type: x ({x}) or y ({y}) must be integers."
            print(f"🔴 Error: {msg}")
            click_status = {"status": "error", "message": msg}
        except Exception as e:
            print(f"🔴 Error clicking at ({target_x}, {target_y}): {e}")
            click_status = {"status": "error", "message": str(e)}
    else:
        # This case should ideally not be reached if x and y are enforced by type hints and function signature.
        msg = "Invalid parameters for click. Both 'x' and 'y' coordinates are required and must be provided."
        print(f"🔴 Error: {msg}")
        click_status = {"status": "error", "message": msg}
    
    time.sleep(wait_time if wait_time > 0 else 1) # Ensure wait_time is positive for sleep
    return click_status
    
def type(text: str, wait_time: int = 0):
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
            
    time.sleep(wait_time)
    return press_status

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
    
    time.sleep(wait_time)
    return scroll_status 