#!/bin/bash

# Check if model checkpoints are already downloaded
if [ -d "weights/icon_caption_florence" ] && [ -d "weights/icon_detect" ] && \
   [ -f "weights/icon_detect/train_args.yaml" ] && \
   [ -f "weights/icon_detect/model.pt" ] && \
   [ -f "weights/icon_detect/model.yaml" ] && \
   [ -f "weights/icon_caption_florence/config.json" ] && \
   [ -f "weights/icon_caption_florence/generation_config.json" ] && \
   [ -f "weights/icon_caption_florence/model.safetensors" ]; then
    echo "Model checkpoints already exist, skipping download..."
else
    echo "Downloading model checkpoints..."
    # download the model checkpoints to local directory OmniParser/weights/
    for f in icon_detect/{train_args.yaml,model.pt,model.yaml} icon_caption/{config.json,generation_config.json,model.safetensors}; do
        huggingface-cli download microsoft/OmniParser-v2.0 "$f" --local-dir weights
    done
    mv weights/icon_caption weights/icon_caption_florence
    echo "Download completed!"
fi

# Create .env file from example if it doesn't exist
if [ ! -f .env ]; then
    cp .env_example .env
    echo "Created .env file from .env_example"
fi

