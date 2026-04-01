def rotate_encryption_keys(network_state, old_cipher, new_cipher):
    """
    Re-encrypt network with new keys while maintaining geometric proxies
    """
    # Decrypt with old key
    decrypted = old_cipher.decrypt_network_state(network_state)
    
    # Re-encrypt with new key, preserving geometric relationships
    reencrypted = new_cipher.encrypt_network_state(decrypted)
    
    return reencrypted
