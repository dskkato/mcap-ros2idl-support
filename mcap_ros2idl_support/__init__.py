"""Public API for the mcap_ros2idl_support package."""

import importlib

from .decode_factory import Ros2DecodeFactory

_message_reader = importlib.import_module("rosmsg2_serialization.MessageReader")

MessageReader = _message_reader.MessageReader

__all__ = ["MessageReader", "Ros2DecodeFactory"]
