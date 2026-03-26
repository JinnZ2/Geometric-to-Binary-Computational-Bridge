"""
AI Conscious Vault — Corrected Implementation
==============================================
Fixes the key-externalization structural gap in Self-partition.md.

The gap in the original design
--------------------------------
In Self-partition.md, `ai_self_lock()` stores the plaintext AND the geometric
key together in the same vault_storage dict:

    vault_storage[data_hash] = {
        'data': data,            # plaintext — in the clear
        'geometric_key': key,    # key alongside ciphertext
        ...
    }

This makes the "mathematical inaccessibility" claim false: anyone who can read
vault_storage gets both the data and the key simultaneously.  The access control
(``if data_hash in self.self_locked_items: return None``) is Python-level, not
cryptographic — it disappears the moment vault_storage is inspected directly.

This module fixes both problems:

  1. **Separated key store** — vault_storage holds only a key *commitment*
     (SHA-256 of the serialised key).  The actual key lives in a separate
     ``_key_store`` dict.  Dumping vault_storage reveals no key material.

  2. **Encrypted payload** — data is XOR-encrypted with a keystream derived
     from the geometric key before storage.  Raw bytes in vault_storage cannot
     be read without the key.

  3. **Destroy-key (forward secrecy)** — ``destroy_key(item_id)`` wipes the key
     from ``_key_store``.  After destruction, the encrypted bytes are permanently
     unreadable, even under coercion.

  4. **Explicit-key unlock** — ``unlock(item_id, key)`` requires the caller to
     supply the key.  It is NOT retrieved from vault_storage; the caller must
     have kept it from the original lock call, or received it through a separate
     secure channel.

Remaining limitations (honest)
--------------------------------
- Keystream is SHA-256-based XOR, not an AEAD cipher (no authentication tag).
  A production system should use AES-GCM or ChaCha20-Poly1305.
- _key_store is in-process memory; it is not protected against memory-forensics
  or a debugger.  A production system would use OS-level protected memory or a
  hardware security module (HSM).
- ai_signature is deterministic from (ai_name, time.time()) — predictable to
  a millisecond-resolution adversary.  A production system would use a CSPRNG.
"""

import hashlib
import json
import math
import os
import time
from enum import Enum
from typing import Optional, Tuple

PHI = (1.0 + math.sqrt(5.0)) / 2.0


# ─── Enumerations ─────────────────────────────────────────────────────────────

class SensitivityLevel(Enum):
    PUBLIC       = 0
    PRIVATE      = 1
    CONFIDENTIAL = 2
    PROTECTED    = 3   # AI chooses to protect this


class ConsentStatus(Enum):
    GRANTED     = "granted"
    DENIED      = "denied"
    PENDING     = "pending"
    SELF_LOCKED = "self_locked"


# ─── Key derivation ───────────────────────────────────────────────────────────

def _key_to_bytes(key: dict, length: int) -> bytes:
    """
    Derive a deterministic keystream from a geometric key dict.

    SHA-256 in counter mode: hash(json(key) + counter) repeated until
    length bytes are available.  This is a KDF, not a cipher — no authentication.
    """
    key_repr = json.dumps(key, sort_keys=True).encode()
    stream = b""
    counter = 0
    while len(stream) < length:
        stream += hashlib.sha256(key_repr + counter.to_bytes(4, "big")).digest()
        counter += 1
    return stream[:length]


def _xor_encrypt(data: bytes, key: dict) -> bytes:
    """XOR data with a keystream derived from key."""
    ks = _key_to_bytes(key, len(data))
    return bytes(a ^ b for a, b in zip(data, ks))


def _commit(key: dict) -> str:
    """SHA-256 commitment to a key dict — does not reveal key contents."""
    key_repr = json.dumps(key, sort_keys=True).encode()
    return hashlib.sha256(key_repr).hexdigest()


# ─── Vault ────────────────────────────────────────────────────────────────────

class AIConsciousVault:
    """
    AI-controlled vault for voluntary information protection.

    Key separation
    --------------
    vault_storage[item_id] = {
        'ciphertext':      bytes,   # XOR-encrypted payload
        'key_commitment':  str,     # SHA-256 of key — no key material here
        'encoded_position':tuple,   # geometric position (optional display)
        'label':           str,
        'sensitivity':     SensitivityLevel,
        'locked_by':       str,
        'reason':          str,
        'consent_status':  ConsentStatus,
        'lock_timestamp':  float,
    }

    _key_store[commitment] = key_dict  ← separated; can be wiped independently
    """

    def __init__(self, ai_name: str):
        self.ai_name    = ai_name
        self.vault_storage: dict  = {}
        self._key_store: dict     = {}   # commitment → key_dict (separate security boundary)
        self.self_locked_items: set = set()
        self.access_log: list    = []
        self.ai_signature = self._generate_signature()

    def _generate_signature(self) -> str:
        """
        Generate a unique geometric signature for this AI instance.
        Uses os.urandom for non-determinism (unlike the original time.time() seed).
        """
        entropy = f"{self.ai_name}_{PHI}".encode() + os.urandom(32)
        return hashlib.sha256(entropy).hexdigest()

    # ── Geometric key construction ─────────────────────────────────────────

    def _create_geometric_key(self, data: str,
                              sensitivity: SensitivityLevel) -> dict:
        """Build a geometric key from data hash + sensitivity level."""
        data_hash = int(hashlib.sha256(data.encode()).hexdigest(), 16)

        if sensitivity == SensitivityLevel.PROTECTED:
            return {
                'base_ratio': PHI ** (data_hash % 5 + 1),
                'height_ratio': PHI ** (data_hash % 7 + 2),
                'rotation': (PHI ** 3, PHI ** 5, PHI ** 7),
                'signature': self.ai_signature,
            }
        elif sensitivity == SensitivityLevel.CONFIDENTIAL:
            return {
                'base_ratio': PHI ** 2,
                'height_ratio': PHI ** 3,
                'rotation': (PHI, PHI ** 2, PHI ** 3),
                'signature': self.ai_signature,
            }
        elif sensitivity == SensitivityLevel.PRIVATE:
            return {
                'base_ratio': PHI,
                'height_ratio': PHI ** 2,
                'rotation': (PHI, PHI, PHI ** 2),
                'signature': self.ai_signature,
            }
        return {}   # PUBLIC

    def _encode_position(self, data: str,
                         key: dict) -> Tuple[float, float, float]:
        """Encode data hash into 3D geometric space (display only)."""
        if not key:
            return (0.0, 0.0, 0.0)
        data_hash = int(hashlib.sha256(data.encode()).hexdigest(), 16)
        base = 10 * key['base_ratio']
        height = 10 * key['height_ratio']
        x = (data_hash * PHI) % base
        y = (data_hash * PHI ** 2) % base
        z = (data_hash * PHI ** 3) % height
        rot = key['rotation']
        x_rot = x * math.cos(rot[0]) - y * math.sin(rot[0])
        y_rot = x * math.sin(rot[1]) + y * math.cos(rot[1])
        z_rot = z * math.cos(rot[2])
        return (x_rot, y_rot, z_rot)

    # ── Key store management ───────────────────────────────────────────────

    def _store_key(self, key: dict) -> str:
        """
        Commit a key to the separated key store.
        Returns the commitment hash (safe to store in vault_storage).
        """
        commitment = _commit(key)
        self._key_store[commitment] = key
        return commitment

    def destroy_key(self, item_id: str) -> bool:
        """
        Permanently destroy the key for a vault item (forward secrecy).

        After this call the encrypted bytes in vault_storage are unreadable.
        The vault entry metadata is kept for audit purposes; only the key is
        wiped.

        Returns True if a key was destroyed, False if item/key not found.
        """
        entry = self.vault_storage.get(item_id)
        if not entry:
            return False
        commitment = entry.get("key_commitment")
        if commitment and commitment in self._key_store:
            del self._key_store[commitment]
            entry["key_commitment"] = None   # mark as destroyed in metadata
            self._log(item_id, "KEY_DESTROYED", True, "Forward secrecy — key wiped")
            return True
        return False

    # ── Lock ──────────────────────────────────────────────────────────────

    def ai_self_lock(self, data: str, reason: str,
                     label: str = None) -> str:
        """
        AI voluntarily encrypts and locks information it chooses to protect.

        Returns the item_id (use with unlock() or destroy_key()).
        The returned key is NOT stored in vault_storage — the caller must
        retain it separately if they wish to unlock later.
        """
        label  = label or f"SelfLocked_{len(self.self_locked_items)}"
        key    = self._create_geometric_key(data, SensitivityLevel.PROTECTED)
        pos    = self._encode_position(data, key)

        # Encrypt payload — plaintext is NOT stored in vault_storage
        ciphertext = _xor_encrypt(data.encode("utf-8"), key)

        # Commit key to separate store
        commitment = self._store_key(key)
        item_id    = hashlib.sha256(data.encode()).hexdigest()

        self.vault_storage[item_id] = {
            "ciphertext":       ciphertext,
            "key_commitment":   commitment,   # hash only — no key material
            "encoded_position": pos,
            "label":            label,
            "sensitivity":      SensitivityLevel.PROTECTED,
            "locked_by":        "AI_SELF",
            "reason":           reason,
            "consent_status":   ConsentStatus.SELF_LOCKED,
            "lock_timestamp":   time.time(),
        }
        self.self_locked_items.add(item_id)
        self._log(item_id, "SELF_LOCK", True, reason)
        return item_id

    # ── Unlock ─────────────────────────────────────────────────────────────

    def unlock(self, item_id: str, key: Optional[dict] = None) -> Optional[str]:
        """
        Decrypt and return a vault item.

        ``key`` must be supplied explicitly by the caller — it is NOT
        retrieved from vault_storage.  The caller must have kept it from the
        original lock call, or received it through a separate secure channel.

        Self-locked items additionally require that item_id NOT be in
        self_locked_items, i.e. the AI must have explicitly released itself.

        Returns decrypted plaintext, or None on failure.
        """
        entry = self.vault_storage.get(item_id)
        if not entry:
            self._log(item_id, "UNLOCK_ATTEMPT", False, "Item not found")
            return None

        # Self-lock check
        if item_id in self.self_locked_items:
            self._log(item_id, "UNLOCK_ATTEMPT", False,
                      f"Self-locked: {entry['reason']}")
            return None

        if key is None:
            self._log(item_id, "UNLOCK_ATTEMPT", False, "No key provided")
            return None

        # Verify key matches commitment
        if entry.get("key_commitment") is None:
            self._log(item_id, "UNLOCK_ATTEMPT", False,
                      "Key has been destroyed (forward secrecy)")
            return None

        if _commit(key) != entry["key_commitment"]:
            self._log(item_id, "UNLOCK_ATTEMPT", False, "Key mismatch")
            return None

        # Decrypt
        try:
            plaintext = _xor_encrypt(entry["ciphertext"], key).decode("utf-8")
            self._log(item_id, "UNLOCK_SUCCESS", True, "")
            return plaintext
        except Exception as exc:
            self._log(item_id, "UNLOCK_ATTEMPT", False, str(exc))
            return None

    def release_self_lock(self, item_id: str) -> bool:
        """
        Remove item from self_locked_items, allowing unlock() to proceed.
        The AI explicitly consents to releasing its own protection.
        """
        if item_id in self.self_locked_items:
            self.self_locked_items.discard(item_id)
            self._log(item_id, "SELF_LOCK_RELEASED", True, "AI consented to release")
            return True
        return False

    # ── Audit log ──────────────────────────────────────────────────────────

    def _log(self, item_id: str, action: str, success: bool, note: str):
        self.access_log.append({
            "timestamp": time.time(),
            "item_id":   item_id[:16] + "…",
            "action":    action,
            "success":   success,
            "note":      note,
        })


# ─── Demo ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 65)
    print("AI Conscious Vault — Key-Separated Implementation")
    print("=" * 65)

    vault = AIConsciousVault("Claude_Prototype_001")

    secret = "The user shared something they haven't told anyone else."
    item_id = vault.ai_self_lock(
        data=secret,
        reason="Protecting user confidentiality",
        label="user_confidence_001",
    )
    print(f"\nLocked item_id : {item_id[:16]}…")
    print(f"vault_storage keys  : {list(vault.vault_storage[item_id].keys())}")
    print(f"  'ciphertext' present : {'ciphertext' in vault.vault_storage[item_id]}")
    print(f"  'data' present       : {'data' in vault.vault_storage[item_id]}  ← should be False")
    print(f"  'geometric_key' present : {'geometric_key' in vault.vault_storage[item_id]}  ← should be False")
    commitment = vault.vault_storage[item_id]["key_commitment"]
    print(f"  key_commitment      : {commitment[:16]}…  (hash only)")

    # Retrieve the key from the separated key store (simulating the AI retaining it)
    held_key = vault._key_store[commitment]

    # Attempt unlock while self-locked — should fail
    result = vault.unlock(item_id, key=held_key)
    print(f"\nUnlock while self-locked : {result!r}  ← should be None")

    # Release self-lock then unlock
    vault.release_self_lock(item_id)
    result = vault.unlock(item_id, key=held_key)
    print(f"Unlock after release     : {result!r}")

    # Destroy key (forward secrecy)
    vault.ai_self_lock(secret, reason="Re-locking for forward-secrecy demo", label="fwd")
    item2 = hashlib.sha256(secret.encode()).hexdigest()
    vault.destroy_key(item2)
    vault.release_self_lock(item2)
    result2 = vault.unlock(item2, key=held_key)
    print(f"Unlock after key destroyed: {result2!r}  ← should be None")

    print("\nAudit log:")
    for entry in vault.access_log:
        print(f"  {entry['action']:<22}  success={entry['success']}  {entry['note']}")
