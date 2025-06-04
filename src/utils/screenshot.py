import io
import cv2
import base64
import pyautogui
import screeninfo
import numpy as np
from google.cloud import vision
from PIL import Image
# Assuming util.utils is now src.utils.model_loader or similar based on structure
# For now, let's assume these will be top-level imports in model_loader.py
# and then imported here, or directly from where they are defined.
# This needs to be resolved based on where get_yolo_model etc. are finally placed.
# from .model_loader import get_yolo_model, get_caption_model_processor, get_som_labeled_img

# Placeholder: these imports will need to be correct based on final util structure
# For now, this will cause an error if run directly unless those functions are globally available
# or model_loader.py correctly exposes them and is imported. The original Ho.py had them
# in a util.utils, which isn't directly mapped yet.

# To make this runnable for now, I'll assume they might be moved to this file or a sibling
# This is a temporary measure for refactoring.

# ---- Placeholder for model loading functions ----
# These would ideally be in src.utils.model_loader.py and imported.
# For now, to avoid import errors during refactoring if model_loader.py isn't done yet,
# let's define dummy versions or expect them to be passed in if not found.

try:
    from .model_helpers import get_som_labeled_img
except ImportError:
    print("Warning: model_helpers.py not found or functions not available. Screenshot AI features will be limited.")
    def get_yolo_model(*args, **kwargs):
        print("Dummy get_yolo_model called")
        return None
    def get_caption_model_processor(*args, **kwargs):
        print("Dummy get_caption_model_processor called")
        return None, None # It used to return two items
    def get_som_labeled_img(*args, **kwargs):
        print("Dummy get_som_labeled_img called")
        return "", [], [] # It used to return three items

# ---- End Placeholder ----


def take_screenshot(som_model, caption_model_processor, omni_enabled: bool = True) -> tuple[io.BytesIO | None, list]:
    """Take a screenshot of the specified monitor and return the screenshot along with the coordinates of the elements in the screenshot.
    
    Args:
        som_model: The SOM model instance.
        caption_model_processor: The caption model/processor instance.
        omni_enabled (bool): Whether to perform AI-based Omni processing.

    Returns:
        tuple: (image_io, transformed_list)
               image_io is a BytesIO object of the screenshot, None on critical error.
               transformed_list is a list of detected UI elements.
    """
    try:
        # Get cursor position before taking screenshot
        cursor_x, cursor_y = pyautogui.position()
        
        # First try to get monitor info
        try:
            monitors = screeninfo.get_monitors()
            if not monitors:
                print("⚠️ No monitors detected by screeninfo, using full screen capture")
                screenshot = pyautogui.screenshot()
                monitor_x, monitor_y = 0, 0
                monitor = None # Define monitor as None if not detected
            else:
                monitor = monitors[0] # using first monitor for now
                print(f"📸 Taking screenshot of monitor {monitor.width}x{monitor.height} at ({monitor.x}, {monitor.y})")
                screenshot = pyautogui.screenshot(region=(monitor.x, monitor.y, monitor.width, monitor.height))
                monitor_x, monitor_y = monitor.x, monitor.y
        except Exception as e:
            print(f"⚠️ Error getting monitor info: {e}. Using full screen capture.")
            screenshot = pyautogui.screenshot()
            monitor_x, monitor_y = 0, 0
            monitor = None # Define monitor as None on error

        # Basic screenshot processing without AI if we at least got the screenshot
        try:
            # Convert PIL Image to numpy array for cursor drawing
            screenshot_np = np.array(screenshot)
            
            # Calculate cursor position relative to the screenshot
            relative_cursor_x = cursor_x - monitor_x
            relative_cursor_y = cursor_y - monitor_y
            
            # Check if cursor is within the screenshot bounds
            if 0 <= relative_cursor_x < screenshot_np.shape[1] and 0 <= relative_cursor_y < screenshot_np.shape[0]:
                # Draw cursor on the image
                cursor_size = 20  # Size of the cursor indicator
                cursor_color = (255, 0, 0)  # Red color (BGR format for OpenCV)
                
                cv2.circle(screenshot_np, (relative_cursor_x, relative_cursor_y), cursor_size//2, cursor_color, 2)
                cv2.line(screenshot_np, (relative_cursor_x - cursor_size//2, relative_cursor_y), 
                        (relative_cursor_x + cursor_size//2, relative_cursor_y), cursor_color, 2)
                cv2.line(screenshot_np, (relative_cursor_x, relative_cursor_y - cursor_size//2), 
                        (relative_cursor_x, relative_cursor_y + cursor_size//2), cursor_color, 2)
                
                print(f"🖱️ Cursor drawn at position ({relative_cursor_x}, {relative_cursor_y})")
            else:
                print(f"🖱️ Cursor at ({cursor_x}, {cursor_y}) is outside screenshot bounds")
            
            screenshot_with_cursor = Image.fromarray(screenshot_np)
            
            print(f"✅ Basic screenshot captured successfully: {screenshot_with_cursor.size[0]}x{screenshot_with_cursor.size[1]}")
            transformed_list_final = [] # Initialize here

            # Try AI processing, but have a fallback if it fails
            try:
                if omni_enabled:
                    image_rgb = screenshot_with_cursor.convert('RGB')
                    # convert image_rgb to bytes
                    buffer = io.BytesIO()
                    image_rgb.save(buffer, format='PNG')
                    image_rgb_bytes = buffer.getvalue()
                    try:
                        text, ocr_bbox = detect_text_and_draw_boxes(image_rgb_bytes)
                        box_overlay_ratio = max(screenshot_with_cursor.size) / 3200
                        draw_bbox_config = {
                            'text_scale': 0.8 * box_overlay_ratio,
                            'text_thickness': max(int(3 * box_overlay_ratio), 1),
                            'text_padding': max(int(3 * box_overlay_ratio), 1),
                            'thickness': max(int(5 * box_overlay_ratio), 1),
                        }
                        BOX_TRESHOLD = 0.05
                        (dino_labled_img,
                        label_coordinates,
                        parsed_content_list) = get_som_labeled_img(image_rgb, 
                                                                som_model, 
                                                                BOX_TRESHOLD=BOX_TRESHOLD, 
                                                                output_coord_in_ratio=False, 
                                                                ocr_bbox=ocr_bbox,
                                                                draw_bbox_config=draw_bbox_config, 
                                                                caption_model_processor=caption_model_processor, 
                                                                ocr_text=text,
                                                                use_local_semantics=True, 
                                                                iou_threshold=0.7, 
                                                                batch_size=128)
                        

                        try:
                            debug_image = Image.open(io.BytesIO(base64.b64decode(dino_labled_img)))
                            debug_image.save('debug_dino_labeled.png')
                        except Exception as e:
                            print(f"⚠️ Failed to save debug image: {e}")

                        # Use actual monitor dimensions and position
                        screen_width = monitor.width if monitor else screenshot_with_cursor.size[0]
                        screen_height = monitor.height if monitor else screenshot_with_cursor.size[1]
                        screen_x = monitor.x if monitor else 0
                        screen_y = monitor.y if monitor else 0

                        print(f"📏 Using screen dimensions: {screen_width}x{screen_height} at position ({screen_x}, {screen_y}) for coordinate mapping")

                        transformed_list_final = [] # Clear previous list
                        for idx, item in enumerate(parsed_content_list):
                            bbox = item['bbox']
                            center_x_ratio = (bbox[0] + bbox[2]) / 2
                            center_y_ratio = (bbox[1] + bbox[3]) / 2
                            center_x_pixel = int(center_x_ratio * screen_width)
                            center_y_pixel = int(center_y_ratio * screen_height)
                            global_x = center_x_pixel + screen_x
                            global_y = center_y_pixel + screen_y

                            new_item = {
                                "content": item['content'], "coordinates": (global_x, global_y), "index": idx,
                                "type": item['type'], "interactivity": item['interactivity']
                            }
                            transformed_list_final.append(new_item)
                            
                        image_io = io.BytesIO()
                        screenshot_with_cursor.save(image_io, format='PNG')
                        image_io.seek(0)
                        print(f"✅ Omni processing succeeded")
                        return image_io, transformed_list_final
                    except Exception as e:
                        print(f"⚠️ Omni processing failed: {e}. Falling back to basic screenshot.")
                        image_io = io.BytesIO()
                        screenshot_with_cursor.save(image_io, format='PNG')
                        image_io.seek(0)
                        return image_io, [] # Return empty list on Omni failure
                else:
                    print("Taking screenshot without Omni...")
                    image_io = io.BytesIO()
                    screenshot_with_cursor.save(image_io, format='PNG')
                    image_io.seek(0)
                    return image_io, [] # Return empty list if Omni disabled
            except Exception as e:
                print(f"⚠️ Error in AI processing: {e}. Falling back to basic screenshot.")
                image_io = io.BytesIO()
                screenshot_with_cursor.save(image_io, format='PNG')
                image_io.seek(0)
                return image_io, [] # Return empty list on AI processing error
        except Exception as e:
            print(f"🔴 Error processing screenshot: {e}")
            raise # Re-raise as this is a critical failure in basic screenshot processing
            
    except Exception as e:
        error_msg = f"Error taking screenshot: {str(e)}"
        print(f"🔴 {error_msg}")
        # Returning a tuple consistent with the success path but with None and empty list
        return None, []


def detect_text_and_draw_boxes(image_file):
    # Initialize Vision client
    client = vision.ImageAnnotatorClient()

    image = vision.Image(content=image_file)

    # Detect text
    response = client.text_detection(image=image)
    if response.error.message:
        raise Exception(
            f"{response.error.message}\nFor more info on error messages, check: "
            "https://cloud.google.com/apis/design/errors"
        )

    texts = response.text_annotations

    # Output lists
    texts_list = []
    bboxes_list = []

    # Skip the first annotation (it's the full text)
    for text in texts[1:]:
        if len(text.description.strip()) <= 2:
            continue  # Skip short text

        vertices = [(v.x, v.y) for v in text.bounding_poly.vertices]
        
        xs = [v[0] for v in vertices]
        ys = [v[1] for v in vertices]
        x1, y1, x2, y2 = min(xs), min(ys), max(xs), max(ys)
        
        texts_list.append(text.description)
        bboxes_list.append((x1, y1, x2, y2))
    return texts_list, bboxes_list

# Note: initialize_omni_models was in Ho.py. It should be moved to src.utils.model_loader.py
# and the models loaded once and passed around, not re-initialized by screenshot or agents. 