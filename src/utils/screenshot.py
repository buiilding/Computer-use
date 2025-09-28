import io
import cv2
import base64
import pyautogui
import screeninfo
import numpy as np
from PIL import Image
from typing import Tuple, List, Dict, Any

try:
    from .model_helpers import get_som_labeled_img, check_ocr_result
except ImportError:
    print("Warning: model_helpers.py not found or functions not available. Screenshot AI features will be limited.")
    def get_som_labeled_img(*args, **kwargs):
        print("Dummy get_som_labeled_img called")
        return "", [], []

def _get_node_center(node: Dict[str, Any]) -> Tuple[float, float]:
    """Calculates the center coordinates of a node's bounding box."""
    return node['x'] + node['width'] / 2, node['y'] + node['height'] / 2

def generate_heuristic_edges(nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Generates a list of relational "edges" between UI "nodes" based on a set
    of spatial and logical heuristics.
    """
    edges: List[Dict[str, Any]] = []
    handled_siblings = set()

    for i in range(len(nodes)):
        for j in range(len(nodes)):
            if i == j:
                continue

            node_a = nodes[i]
            node_b = nodes[j]

            # Rule 1: The `is_label_for` Relationship
            if node_a.get('type') == 'text' and node_b.get('type') == 'icon' and node_b.get('interactivity'):
                center_a_x, center_a_y = _get_node_center(node_a)
                center_b_x, center_b_y = _get_node_center(node_b)

                # Vertical Alignment Check (text is above interactive element)
                vertical_gap = node_b['y'] - (node_a['y'] + node_a['height'])
                is_vertically_proximate = 0 <= vertical_gap < 50
                is_horizontally_aligned = abs(center_a_x - center_b_x) < 75
                if is_vertically_proximate and is_horizontally_aligned:
                    edges.append({"source": node_a['id'], "target": node_b['id'], "label": "is_label_for"})

                # Horizontal Alignment Check (text is to the left of interactive element)
                horizontal_gap = node_b['x'] - (node_a['x'] + node_a['width'])
                is_horizontally_proximate = 0 <= horizontal_gap < 50
                is_vertically_aligned = abs(center_a_y - center_b_y) < 25
                if is_horizontally_proximate and is_vertically_aligned:
                    edges.append({"source": node_a['id'], "target": node_b['id'], "label": "is_label_for"})

            # Rule 2: The `contains` Relationship
            is_contained = (
                node_b['x'] >= node_a['x'] and
                node_b['y'] >= node_a['y'] and
                (node_b['x'] + node_b['width']) <= (node_a['x'] + node_a['width']) and
                (node_b['y'] + node_b['height']) <= (node_a['y'] + node_a['height'])
            )
            if is_contained:
                edges.append({"source": node_a['id'], "target": node_b['id'], "label": "contains"})

            # Rule 3: The `is_sibling_of` Relationship
            if node_a.get('interactivity') and node_b.get('interactivity'):
                pair = tuple(sorted((node_a['id'], node_b['id'])))
                if pair in handled_siblings:
                    continue
                center_a_x, center_a_y = _get_node_center(node_a)
                center_b_x, center_b_y = _get_node_center(node_b)
                if abs(center_a_y - center_b_y) < 20:
                    gap = max(node_a['x'], node_b['x']) - min(node_a['x'] + node_a['width'], node_b['x'] + node_b['width'])
                    if 0 <= gap < 100:
                        edges.append({"source": node_a['id'], "target": node_b['id'], "label": "is_sibling_of"})
                        handled_siblings.add(pair)
                elif abs(center_a_x - center_b_x) < 20:
                    gap = max(node_a['y'], node_b['y']) - min(node_a['y'] + node_a['height'], node_b['y'] + node_b['height'])
                    if 0 <= gap < 50:
                        edges.append({"source": node_a['id'], "target": node_b['id'], "label": "is_sibling_of"})
                        handled_siblings.add(pair)
    return edges

def capture_screen() -> Tuple[Image.Image | None, Dict | None]:
    """
    Captures the primary monitor's screen.

    Returns:
        A tuple containing:
        - A PIL Image object of the screen capture, or None on error.
        - A dictionary with monitor details ('x', 'y', 'width', 'height'), or None on error.
    """
    try:
        monitors = screeninfo.get_monitors()
        if not monitors:
            print("⚠️ No monitors detected by screeninfo, capturing full screen.")
            screenshot = pyautogui.screenshot()
            monitor_info = {'x': 0, 'y': 0, 'width': screenshot.width, 'height': screenshot.height}
        else:
            monitor = monitors[0]
            print(f"📸 Capturing screen of monitor {monitor.width}x{monitor.height} at ({monitor.x}, {monitor.y})")
            screenshot = pyautogui.screenshot(region=(monitor.x, monitor.y, monitor.width, monitor.height))
            monitor_info = {'x': monitor.x, 'y': monitor.y, 'width': monitor.width, 'height': monitor.height}
        
        return screenshot, monitor_info
    except Exception as e:
        print(f"🔴 Error capturing screen: {e}")
        return None, None

def draw_cursor(image: Image.Image, monitor_info: Dict) -> Image.Image:
    """
    Draws the current cursor position on the given image.

    Args:
        image: The PIL Image to draw on.
        monitor_info: A dictionary with monitor details ('x', 'y', 'width', 'height').

    Returns:
        A new PIL Image with the cursor drawn on it.
    """
    try:
        cursor_x, cursor_y = pyautogui.position()
        screenshot_np = np.array(image.convert('RGB'))

        # Calculate cursor position relative to the captured image
        relative_x = cursor_x - monitor_info['x']
        relative_y = cursor_y - monitor_info['y']
        
        # Draw cursor on the image if it's within the bounds
        if 0 <= relative_x < image.width and 0 <= relative_y < image.height:
            cursor_size = 20
            cursor_color = (255, 0, 0) # Red color (in RGB)
            cv2.circle(screenshot_np, (relative_x, relative_y), cursor_size//2, cursor_color, 2)
            cv2.line(screenshot_np, (relative_x - cursor_size//2, relative_y), (relative_x + cursor_size//2, relative_y), cursor_color, 2)
            cv2.line(screenshot_np, (relative_x, relative_y - cursor_size//2), (relative_x, relative_y + cursor_size//2), cursor_color, 2)
            print(f"🖱️ Cursor drawn at absolute ({cursor_x}, {cursor_y}), relative to image ({relative_x}, {relative_y})")
        else:
            print(f"🖱️ Cursor at ({cursor_x}, {cursor_y}) is outside the captured image region.")

        return Image.fromarray(screenshot_np)
    except Exception as e:
        print(f"⚠️ Failed to draw cursor: {e}")
        return image # Return original image on failure

def analyze_screen(image: Image.Image, monitor_info: Dict, som_model, caption_model_processor, rapid_ocr_engine) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Analyzes a screenshot with AI models to identify UI elements and their relationships.

    Args:
        image: The raw PIL Image of the screen.
        monitor_info: A dictionary with the screen's geometry.
        som_model: The SOM model instance.
        caption_model_processor: The caption model/processor instance.
        rapid_ocr_engine: The OCR engine instance.

    Returns:
        A tuple containing:
        - A list of dictionaries for the detected UI nodes.
        - A list of dictionaries for the generated relational edges.
    """
    print("🧠 Analyzing screen with AI models...")
    try:
        image_rgb = image.convert('RGB')
        buffer = io.BytesIO()
        image_rgb.save(buffer, format='PNG')
        image_rgb_bytes = buffer.getvalue()

        if rapid_ocr_engine:
            result = rapid_ocr_engine(image_rgb_bytes)
            text, ocr_bbox = check_ocr_result(result)
        else:
            text, ocr_bbox = [], []

        box_overlay_ratio = max(image.size) / 3200
        draw_bbox_config = {
            'text_scale': 0.8 * box_overlay_ratio,
            'text_thickness': max(int(3 * box_overlay_ratio), 1),
            'text_padding': max(int(3 * box_overlay_ratio), 1),
            'thickness': max(int(5 * box_overlay_ratio), 1),
        }
        BOX_TRESHOLD = 0.05
        
        (dino_labled_img,
         label_coordinates,
         parsed_content_list) = get_som_labeled_img(
             image_source=image_rgb, model=som_model, BOX_TRESHOLD=BOX_TRESHOLD,
             output_coord_in_ratio=False, ocr_bbox=ocr_bbox,
             draw_bbox_config=draw_bbox_config, caption_model_processor=caption_model_processor,
             ocr_text=text, use_local_semantics=True, iou_threshold=0.7, batch_size=128
         )

        try:
            debug_image = Image.open(io.BytesIO(base64.b64decode(dino_labled_img)))
            debug_image.save('debug_dino_labeled.png')
        except Exception as e:
            print(f"⚠️ Failed to save debug image: {e}")

        screen_width = monitor_info['width']
        screen_height = monitor_info['height']
        screen_x = monitor_info['x']
        screen_y = monitor_info['y']

        nodes = []
        for item in parsed_content_list:
            bbox = item['bbox']
            center_x_ratio = (bbox[0] + bbox[2]) / 2
            center_y_ratio = (bbox[1] + bbox[3]) / 2
            
            new_node = {
                "id": len(nodes),
                "content": item['content'],
                "type": item['type'],
                "interactivity": item['interactivity'],
                "x": int(center_x_ratio * screen_width) + screen_x,
                "y": int(center_y_ratio * screen_height) + screen_y,
                "width": int((bbox[2] - bbox[0]) * screen_width),
                "height": int((bbox[3] - bbox[1]) * screen_height)
            }
            nodes.append(new_node)
        
        # After generating nodes, generate edges
        edges = generate_heuristic_edges(nodes)
        
        print(f"✅ AI analysis succeeded. Found {len(nodes)} nodes and {len(edges)} edges.")
        return nodes, edges

    except Exception as e:
        print(f"🔴 AI analysis failed: {e}. Returning empty lists.")
        return [], []

