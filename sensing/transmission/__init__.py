"""
transmission — ship Primitives over whatever link is available.

Three thin wrappers + one queue manager:

* :mod:`queue_manager` — persistent FIFO that holds Primitives when
  no link is available. Survives reboots (file-backed).
* :mod:`lora_transmit` — send via a LoRa radio. Stub by default;
  pass a real ``send`` callable to wire in pyLoRa or RadioHead.
* :mod:`ham_kiss_wrapper` — packet-radio (KISS) over a TNC. Stub
  by default; needs an APRS / packet-radio client to be wired in,
  and only run by licensed operators.
* :mod:`cb_relay_format` — frame a Primitive for spoken relay over
  CB channel 19 (or any voice channel). Returns a short text string;
  voice modulation is the operator's job.
"""

from sensing.transmission.queue_manager import QueueManager
from sensing.transmission.lora_transmit import LoRaTransmitter
from sensing.transmission.ham_kiss_wrapper import HamKissTransmitter
from sensing.transmission.cb_relay_format import format_for_cb_relay

__all__ = [
    "QueueManager",
    "LoRaTransmitter",
    "HamKissTransmitter",
    "format_for_cb_relay",
]
