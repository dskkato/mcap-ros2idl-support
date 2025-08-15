from __future__ import annotations

import re
from dataclasses import replace
from typing import List

from mcap_ros2idl_support.message_definition import (
    AggregatedKind,
    MessageDefinition,
    MessageDefinitionField,
    UnionCase,
)
from mcap_ros2idl_support.omgidl_parser.process import (
    IDLModuleDefinition,
    IDLStructDefinition,
    IDLUnionDefinition,
    parse_idl_message_definitions,
)

ROS2IDL_HEADER = re.compile(r"={80}\nIDL: [a-zA-Z][\w]*(?:\/[a-zA-Z][\w]*)*")


def parse_ros2idl(message_definition: str) -> List[MessageDefinition]:
    """Parse ros2idl schema into message definitions."""

    idl_conformed = ROS2IDL_HEADER.sub("", message_definition)
    idl_defs = parse_idl_message_definitions(idl_conformed)

    message_defs: List[MessageDefinition] = []
    for defn in idl_defs:
        if isinstance(defn, IDLStructDefinition):
            fields: List[MessageDefinitionField] = []
            for field in defn.definitions:
                f = replace(field)
                f.type = _normalize_name(f.type)
                if f.enumType:
                    f.enumType = _normalize_name(f.enumType)
                fields.append(f)
            message_defs.append(
                MessageDefinition(
                    name=_normalize_name(defn.name),
                    definitions=fields,
                    aggregatedKind=AggregatedKind.STRUCT,
                )
            )
        elif isinstance(defn, IDLModuleDefinition):
            fields = []
            for field in defn.definitions:
                f = replace(field)
                f.type = _normalize_name(f.type)
                if f.enumType:
                    f.enumType = _normalize_name(f.enumType)
                fields.append(f)
            message_defs.append(
                MessageDefinition(
                    name=_normalize_name(defn.name),
                    definitions=fields,
                    aggregatedKind=AggregatedKind.MODULE,
                )
            )
        elif isinstance(defn, IDLUnionDefinition):
            cases: List[UnionCase] = []
            for case in defn.cases:
                f = replace(case.type)
                f.type = _normalize_name(f.type)
                if f.enumType:
                    f.enumType = _normalize_name(f.enumType)
                cases.append(UnionCase(predicates=case.predicates, type=f))
            default_case = None
            if defn.defaultCase is not None:
                f = replace(defn.defaultCase)
                f.type = _normalize_name(f.type)
                if f.enumType:
                    f.enumType = _normalize_name(f.enumType)
                default_case = f
            message_defs.append(
                MessageDefinition(
                    name=_normalize_name(defn.name),
                    aggregatedKind=AggregatedKind.UNION,
                    switchType=_normalize_name(defn.switchType),
                    cases=cases,
                    defaultCase=default_case,
                )
            )

    for msg in message_defs:
        if msg.name in (
            "builtin_interfaces/msg/Time",
            "builtin_interfaces/msg/Duration",
        ):
            for field in msg.definitions:
                if field.name == "nanosec":
                    field.name = "nsec"

    return message_defs


def _normalize_name(name: str) -> str:
    s = str(name)
    return s.replace("::", "/") if "::" in s else s


__all__ = [
    "parse_ros2idl",
    "AggregatedKind",
    "MessageDefinition",
    "MessageDefinitionField",
]
