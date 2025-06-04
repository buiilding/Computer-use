#!/bin/bash

# download the model checkpoints to local directory OmniParser/weights/
for f in icon_detect/{train_args.yaml,model.pt,model.yaml} icon_caption/{config.json,generation_config.json,model.safetensors}; do
    huggingface-cli download microsoft/OmniParser-v2.0 "$f" --local-dir weights
done
mv weights/icon_caption weights/icon_caption_florence

# Create .env file from example if it doesn't exist
if [ ! -f .env ]; then
    cp .env_example .env
    echo "Created .env file from .env_example"
fi

