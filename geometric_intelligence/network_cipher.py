"""
Network-Aware Geometric Cipher
==============================
Extracted from Geometric-Intelligence/Geometric-cipher.md.

Provides network-state encryption with optional geometric-signature
preservation for trojan detection, plus a quantum-resistant KDF and
secure key storage.

.. warning::

    CRYPTOGRAPHIC ANTI-PATTERN WARNING
    -----------------------------------
    The ``preserve_geometric_signatures`` mode intentionally preserves
    phi-scaled proxy values in the encrypted output so that geometric
    coherence detectors can still operate.  This is a **deliberate
    trade-off between privacy and detectability** -- it weakens
    encryption by design.

    You cannot have:
      * True encryption (undetectable patterns) AND
      * Pattern detection (detectable geometric signatures)

    The preserve-signatures mode exists for **internal integrity
    monitoring only** -- never expose proxy values to untrusted
    parties.  If full confidentiality is required, set
    ``preserve_geometric_signatures=False``.

    Historical parallel: this is structurally similar to the NSA's
    Dual_EC_DRBG backdoor, dressed up as a feature.  Use with full
    understanding of the trade-off.
"""

from __future__ import annotations

import hashlib
import json
import struct
from typing import Any, Dict, List, Optional

PHI: float = (1.0 + 5.0 ** 0.5) / 2.0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _xor_bytes(data: bytes, key_material: bytes) -> bytes:
    """XOR *data* with *key_material*, repeating key_material as needed."""
    km_len = len(key_material)
    return bytes(d ^ key_material[i % km_len] for i, d in enumerate(data))


def _derive_keystream(master_key: bytes, length: int) -> bytes:
    """SHA-256 counter-mode KDF producing *length* bytes."""
    stream = b""
    counter = 0
    while len(stream) < length:
        stream += hashlib.sha256(master_key + counter.to_bytes(4, "big")).digest()
        counter += 1
    return stream[:length]


# ---------------------------------------------------------------------------
# NetworkCipher
# ---------------------------------------------------------------------------

class NetworkCipher:
    """
    Encrypt network node states while optionally preserving geometric
    signatures for trojan detection.

    .. warning::

        When ``preserve_geometric_signatures=True`` the encrypted output
        retains phi-scaled proxy values for 'resonance' and 'field'
        fields.  These proxies leak information about the original
        values.  See module-level docstring for details.

    Parameters
    ----------
    master_key : bytes or None
        Base key material.  A random 32-byte key is generated if None.
    preserve_geometric_signatures : bool
        If True, 'resonance' and 'field' fields are replaced with
        phi-scaled proxies instead of being fully encrypted.
    """

    def __init__(
        self,
        master_key: Optional[bytes] = None,
        preserve_geometric_signatures: bool = True,
    ) -> None:
        if master_key is None:
            import os
            master_key = os.urandom(32)
        self.master_key: bytes = master_key
        self.preserve_signatures: bool = preserve_geometric_signatures

    # -- Low-level encrypt / decrypt ----------------------------------------

    def encrypt(self, plaintext: bytes) -> bytes:
        """Encrypt *plaintext* using XOR with a SHA-256 keystream."""
        ks = _derive_keystream(self.master_key, len(plaintext))
        return _xor_bytes(plaintext, ks)

    def decrypt(self, ciphertext: bytes) -> bytes:
        """Decrypt *ciphertext* (symmetric XOR)."""
        return self.encrypt(ciphertext)   # XOR is self-inverse

    # -- Node-level ---------------------------------------------------------

    def encrypt_node_state(self, node: Dict[str, Any]) -> Dict[str, Any]:
        """
        Encrypt sensitive fields of a single node dict.

        Sensitive fields: ``resonance``, ``field``, ``energyUsed``.

        If ``preserve_geometric_signatures`` is enabled, 'resonance' and
        'field' are replaced with phi-scaled proxies (see
        :meth:`_create_geometric_proxy`); otherwise they are removed
        from the output and only the encrypted hex is kept.

        Returns a new dict (the original is not mutated).
        """
        sensitive_fields = ["resonance", "field", "energyUsed"]
        encrypted_node: Dict[str, Any] = dict(node)
        manifest: Dict[str, str] = {}

        for fname in sensitive_fields:
            if fname not in node:
                continue

            value = node[fname]
            if isinstance(value, (int, float)):
                value_bytes = struct.pack("!d", float(value))
            else:
                value_bytes = str(value).encode("utf-8")

            encrypted_node[fname + "_encrypted"] = self.encrypt(value_bytes).hex()

            if self.preserve_signatures and fname in ("resonance", "field"):
                encrypted_node[fname] = self._create_geometric_proxy(float(value))
                manifest[fname] = "proxy"
            else:
                encrypted_node.pop(fname, None)
                manifest[fname] = "encrypted"

        encrypted_node["_cipher_manifest"] = manifest
        encrypted_node["_cipher_version"] = "1.0"
        return encrypted_node

    def decrypt_node_state(self, encrypted_node: Dict[str, Any]) -> Dict[str, Any]:
        """
        Decrypt a node previously encrypted by :meth:`encrypt_node_state`.

        Returns a new dict with original field values restored.
        """
        if "_cipher_manifest" not in encrypted_node:
            return dict(encrypted_node)

        manifest = encrypted_node["_cipher_manifest"]
        decrypted: Dict[str, Any] = dict(encrypted_node)
        del decrypted["_cipher_manifest"]
        del decrypted["_cipher_version"]

        for fname, status in manifest.items():
            enc_key = fname + "_encrypted"
            if enc_key not in decrypted:
                continue
            enc_bytes = bytes.fromhex(decrypted[enc_key])
            plain = self.decrypt(enc_bytes)
            if fname in ("resonance", "field", "energyUsed"):
                decrypted[fname] = struct.unpack("!d", plain)[0]
            else:
                decrypted[fname] = plain.decode("utf-8")
            del decrypted[enc_key]

        return decrypted

    # -- Network-level ------------------------------------------------------

    def encrypt_network_state(self, network: Dict[str, Any]) -> Dict[str, Any]:
        """
        Encrypt an entire network state (nodes, connections, metadata).
        """
        encrypted: Dict[str, Any] = {
            "nodes": [self.encrypt_node_state(n) for n in network.get("nodes", [])],
            "connections": list(network.get("connections", [])),
            "metadata": {},
        }

        if "energy" in network:
            energy_bytes = json.dumps(network["energy"]).encode("utf-8")
            encrypted["metadata"]["energy_encrypted"] = self.encrypt(energy_bytes).hex()

        if "trojan" in network:
            encrypted["trojan"] = {
                "cfg": network["trojan"]["cfg"],
                "history_encrypted": True,
            }

        encrypted["_network_cipher_version"] = "1.0"
        return encrypted

    def decrypt_network_state(self, encrypted_network: Dict[str, Any]) -> Dict[str, Any]:
        """
        Decrypt a network previously encrypted by
        :meth:`encrypt_network_state`.
        """
        if "_network_cipher_version" not in encrypted_network:
            return dict(encrypted_network)

        decrypted: Dict[str, Any] = {
            "nodes": [
                self.decrypt_node_state(n) for n in encrypted_network.get("nodes", [])
            ],
            "connections": list(encrypted_network.get("connections", [])),
        }

        meta = encrypted_network.get("metadata", {})
        if "energy_encrypted" in meta:
            enc = bytes.fromhex(meta["energy_encrypted"])
            decrypted["energy"] = json.loads(self.decrypt(enc).decode("utf-8"))

        if "trojan" in encrypted_network:
            decrypted["trojan"] = encrypted_network["trojan"]

        return decrypted

    # -- Geometric proxy ----------------------------------------------------

    def _create_geometric_proxy(self, value: float) -> float:
        """
        Create a phi-scaled proxy that preserves geometric relationships
        but obscures the actual value.

        .. warning::

            This intentionally leaks information about *value*.  The
            proxy maintains phi-ratio coherence for trojan detection
            while preventing *direct* value readout.  It does NOT
            provide cryptographic hiding.
        """
        h = hashlib.sha256(self.master_key + struct.pack("!d", value)).digest()
        hash_int = int.from_bytes(h[:8], "big")

        phi_power = (hash_int % 5) - 2        # -2 .. +2
        phi_scale = PHI ** phi_power
        noise_factor = (hash_int % 1000) / 10_000.0 - 0.05   # < 5 %
        return value * phi_scale * (1 + noise_factor)


# ---------------------------------------------------------------------------
# QuantumResistantKDF
# ---------------------------------------------------------------------------

class QuantumResistantKDF:
    """
    Multi-hash cascade KDF with phi-ratio lattice-point mixing.

    Uses SHA3-256 + BLAKE2b + SHA-256 in an iterative cascade.  This is
    intended to provide defence-in-depth against a future quantum attacker
    that can break a single hash function but not all three simultaneously.

    .. note::

        This is a research prototype.  For production key derivation use
        ``argon2id`` or ``scrypt`` via a vetted library.
    """

    @staticmethod
    def derive_key(
        password: str,
        salt: bytes,
        iterations: int = 100_000,
        key_length: int = 32,
    ) -> bytes:
        """
        Derive a cryptographic key from *password* + *salt*.

        Parameters
        ----------
        password   : str   -- passphrase
        salt       : bytes -- at least 16 bytes
        iterations : int   -- hardening rounds (default 100 000)
        key_length : int   -- output length in bytes (default 32)

        Returns
        -------
        bytes of length *key_length*

        Raises
        ------
        ValueError if *salt* is too short.
        """
        if not salt or len(salt) < 16:
            raise ValueError("Salt must be at least 16 bytes")

        key = hashlib.sha3_256(password.encode("utf-8") + salt).digest()

        for i in range(iterations):
            h1 = hashlib.sha3_256(key).digest()
            h2 = hashlib.blake2b(key, digest_size=32).digest()
            h3 = hashlib.sha256(key).digest()

            phi_scaled = int(i * PHI) % 256
            mixed = bytes((h1[j] ^ h2[j] ^ h3[j] ^ phi_scaled) % 256 for j in range(32))

            if i % 1000 == 0:
                mixed = hashlib.sha3_256(mixed + salt).digest()

            key = mixed

        return key[:key_length]


# ---------------------------------------------------------------------------
# SecureKeyStorage
# ---------------------------------------------------------------------------

class SecureKeyStorage:
    """
    Filesystem key storage with geometric integrity checking.

    Stores cipher master keys encrypted under a password-derived key.
    Integrity is ensured via SHA3-256 over the serialised storage dict.
    """

    def __init__(self, storage_path: str) -> None:
        self.storage_path: str = storage_path

    def store_key(
        self,
        key_name: str,
        master_key: bytes,
        password: Optional[str] = None,
    ) -> str:
        """
        Persist *master_key* to ``{storage_path}/{key_name}.key``.

        If *password* is supplied the key bytes are encrypted first using
        a key derived from :class:`QuantumResistantKDF`.

        Returns the SHA-256 fingerprint of the stored key.
        """
        import os as _os

        key_hex = master_key.hex()

        if password:
            salt = _os.urandom(32)
            derived = QuantumResistantKDF.derive_key(password, salt, iterations=10_000)
            enc = _xor_bytes(master_key, _derive_keystream(derived, len(master_key)))
            storage_data: Dict[str, Any] = {
                "encrypted": True,
                "salt": salt.hex(),
                "data": enc.hex(),
            }
        else:
            storage_data = {"encrypted": False, "data": key_hex}

        fingerprint = hashlib.sha256(master_key).hexdigest()
        storage_data["fingerprint"] = fingerprint
        sig = hashlib.sha3_256(json.dumps(storage_data, sort_keys=True).encode()).hexdigest()
        storage_data["signature"] = sig

        path = f"{self.storage_path}/{key_name}.key"
        with open(path, "w") as fh:
            json.dump(storage_data, fh, indent=2)

        return fingerprint

    def load_key(self, key_name: str, password: Optional[str] = None) -> bytes:
        """
        Load a key previously stored via :meth:`store_key`.

        Returns the raw key bytes.

        Raises
        ------
        ValueError on integrity failure or missing password.
        """
        path = f"{self.storage_path}/{key_name}.key"
        with open(path) as fh:
            storage_data = json.load(fh)

        stored_sig = storage_data.pop("signature")
        computed_sig = hashlib.sha3_256(
            json.dumps(storage_data, sort_keys=True).encode()
        ).hexdigest()
        if stored_sig != computed_sig:
            raise ValueError("Key file integrity check failed -- possible tampering")

        if storage_data["encrypted"]:
            if not password:
                raise ValueError("Password required for encrypted key")
            salt = bytes.fromhex(storage_data["salt"])
            derived = QuantumResistantKDF.derive_key(password, salt, iterations=10_000)
            enc = bytes.fromhex(storage_data["data"])
            return _xor_bytes(enc, _derive_keystream(derived, len(enc)))

        return bytes.fromhex(storage_data["data"])
