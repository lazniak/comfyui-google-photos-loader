import aiohttp
from PIL import Image
import io
import torch
import numpy as np
import asyncio
from .logging_config import log_message

async def process_single_image(session, image_url, size_option, target_size, logger, check_cancelled, original_width, original_height):
    try:
        log_message(logger, f"Processing image from URL: {image_url}", 'debug')
        check_cancelled()

        # Add size parameters to URL
        if size_option == "Original Size":
            if original_width and original_height:
                image_url += f"=w{original_width}-h{original_height}"
            else:
                image_url += "=d"  # 'd' parameter requests the original image
        else:
            # For all other options, we request the image in the target size
            image_url += f"=w{target_size}-h{target_size}"

        async with session.get(image_url) as response:
            check_cancelled()
            response.raise_for_status()
            img_data = await response.read()
        
        check_cancelled()
        img = Image.open(io.BytesIO(img_data))
        
        # Verify that the loaded data is actually an image
        if not isinstance(img, Image.Image):
            raise ValueError("Loaded data is not a valid image")
        
        log_message(logger, f"Original image size: {img.size}, mode: {img.mode}", 'debug')
        
        img = img.convert('RGB')
        
        if size_option == "Scale to Size":
            img = scale_to_size(img, target_size)
        elif size_option == "Crop to Size":
            img = crop_to_size(img, target_size)
        elif size_option == "Fill to Size":
            img = fill_with_size(img, target_size)
        
        log_message(logger, f"Processed image size: {img.size}", 'debug')
        
        check_cancelled()
        img_tensor = pil_to_tensor(img)
        return img_tensor
    except asyncio.CancelledError:
        log_message(logger, "Operation cancelled", 'warning')
        raise
    except Exception as e:
        log_message(logger, f"Error processing image from URL {image_url}: {str(e)}", 'error')
        return None

def scale_to_size(img, target_size):
    aspect_ratio = img.width / img.height
    if img.width > img.height:
        new_width = target_size
        new_height = int(target_size / aspect_ratio)
    else:
        new_height = target_size
        new_width = int(target_size * aspect_ratio)
    return img.resize((new_width, new_height), Image.LANCZOS)

def crop_to_size(img, target_size):
    aspect_ratio = img.width / img.height
    if aspect_ratio > 1:
        # Wider than tall
        new_width = int(target_size * aspect_ratio)
        new_height = target_size
        img = img.resize((new_width, new_height), Image.LANCZOS)
        left = (img.width - target_size) // 2
        top = 0
        right = left + target_size
        bottom = target_size
    else:
        # Taller than wide
        new_width = target_size
        new_height = int(target_size / aspect_ratio)
        img = img.resize((new_width, new_height), Image.LANCZOS)
        left = 0
        top = (img.height - target_size) // 2
        right = target_size
        bottom = top + target_size
    return img.crop((left, top, right, bottom))

def fill_with_size(img, target_size):
    aspect_ratio = img.width / img.height
    if aspect_ratio > 1:
        # Image is wider than tall
        new_width = target_size
        new_height = int(target_size / aspect_ratio)
    else:
        # Image is taller than wide or square
        new_height = target_size
        new_width = int(target_size * aspect_ratio)
    
    # Scale image preserving aspect ratio
    img_resized = img.resize((new_width, new_height), Image.LANCZOS)
    
    # Create a new image with target_size x target_size dimensions and black background
    new_img = Image.new('RGB', (target_size, target_size), (0, 0, 0))
    
    # Calculate position to paste the scaled image
    paste_x = (target_size - new_width) // 2
    paste_y = (target_size - new_height) // 2
    
    # Paste the scaled image onto the black background
    new_img.paste(img_resized, (paste_x, paste_y))
    
    return new_img

def pil_to_tensor(image):
    np_image = np.array(image).astype(np.float32) / 255.0
    tensor = torch.from_numpy(np_image)
    
    if len(tensor.shape) == 2:
        tensor = tensor.unsqueeze(0)
    
    if len(tensor.shape) == 3:
        tensor = tensor.unsqueeze(0)
    
    if tensor.shape[1] == 3:
        tensor = tensor.permute(0, 2, 3, 1)
    
    return tensor

def get_largest_image_url(base_url, original_size):
    # Google Photos API uses 'w' and 'h' parameters for image size
    # We'll use a large size that should cover most cases, or the original size if known
    if original_size and original_size > 0:
        return f"{base_url}=w{original_size}-h{original_size}"
    else:
        return f"{base_url}=w2048-h2048"  # Use a large default size