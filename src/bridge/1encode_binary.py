from . import sound

elif modality == "sound":
    return sound.encode_sound_gray(features, target_bits)

from . import gravity

elif modality == "gravity":
    return gravity.encode_gravity_gray(features, target_bits)
