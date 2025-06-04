from .model_helpers import get_yolo_model, get_caption_model_processor

def initialize_omni_models(omni_device: str, som_model_path = "/weights/icon_detect/model.pt", caption_model_path = "/weights/icon_caption"):
    print(f"🧠 Initializing Omni models on device: {omni_device}")
    som_model = None
    caption_model_processor = None
    
    if get_yolo_model and get_caption_model_processor:
        try:
            if som_model_path is not None:
                som_model = get_yolo_model(som_model_path)
                if som_model:
                    som_model.to("cuda") 
                    print(f"👁️ SOM model loaded from {som_model_path} and moved to {omni_device}")
                else:
                    print(f"🔴 SOM model loading failed from {som_model_path}.")
            else:
                print("ℹ️ SOM model path not provided. Skipping SOM model initialization.")

            if caption_model_path is not None:
                caption_model_processor = get_caption_model_processor(model_name="florence2", model_name_or_path=caption_model_path, device=omni_device)
                if caption_model_processor:
                    print(f"🗣️ Caption model/processor loaded from {caption_model_path} and moved to {omni_device}")
                else:
                    print(f"🔴 Caption model/processor loading failed from {caption_model_path}.")
            else:
                print("ℹ️ Caption model path not provided. Skipping caption model initialization.")
                
        except Exception as e:
            print(f"🔴 Error initializing Omni models: {e}")
    else:
        print("🔴 Omni utility functions (get_yolo_model, get_caption_model_processor) not available. Skipping Omni model initialization.")
    return som_model, caption_model_processor