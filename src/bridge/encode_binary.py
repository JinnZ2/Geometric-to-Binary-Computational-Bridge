from . import magnetic
from . import light
# (geometry module can be added here as well)

def encode(modality: str, features: dict, target_bits: int = 256) -> str:
    """
    Unified entry point: encode features → binary bitstring.
    
    Args:
        modality (str): "magnetic", "light", (later: "geometry", "sound", etc.)
        features (dict): extracted feature dictionary
        target_bits (int): length of output bitstring
    
    Returns:
        str: binary string of given length
    """
    if modality == "magnetic":
        return magnetic.encode_magnetic_gray(features, target_bits)
    elif modality == "light":
        return light.encode_light_gray(features, target_bits)
    # future expansion:
    # elif modality == "geometry":
    #     return geometry.encode_geometry_gray(features, target_bits)
    else:
        raise ValueError(f"Unsupported modality: {modality}")
