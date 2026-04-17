"""
S1 SDK Package - Pre-configured for MachineType.S1

This package provides S1-specific wrappers for GalbotNavigation, GalbotMotion, 
and GalbotRobot that automatically initialize with MachineType.S1.

Usage:
    from galbot_sdk.s1 import GalbotNavigation, GalbotMotion, GalbotRobot

    nav = GalbotNavigation()
    nav.init()

    motion = GalbotMotion()
    motion.init()

    robot = GalbotRobot()
    robot.init()
"""

from .. import (
    MachineType,
    GalbotNavigation as _BaseGalbotNavigation,
    GalbotMotion as _BaseGalbotMotion,
    GalbotRobot as _BaseGalbotRobot,
)
from .. import *  # noqa: F401, F403


class GalbotNavigation:
    """
    S1-specific GalbotNavigation wrapper.
    Automatically initialized with MachineType.S1 - no need to pass it explicitly.
    """
    _instance = None
    _py_instance = None

    def __new__(cls):
        if cls._py_instance is None:
            cls._py_instance = super().__new__(cls)
        return cls._py_instance

    def __init__(self):
        if GalbotNavigation._instance is None:
            GalbotNavigation._instance = _BaseGalbotNavigation.get_instance(MachineType.S1)
            self._impl = GalbotNavigation._instance

    def __getattr__(self, name):
        return getattr(self._impl, name)


class GalbotMotion:
    """
    S1-specific GalbotMotion wrapper.
    Automatically initialized with MachineType.S1 - no need to pass it explicitly.
    """
    _instance = None
    _py_instance = None

    def __new__(cls):
        if cls._py_instance is None:
            cls._py_instance = super().__new__(cls)
        return cls._py_instance

    def __init__(self):
        if GalbotMotion._instance is None:
            GalbotMotion._instance = _BaseGalbotMotion.get_instance(MachineType.S1)
            self._impl = GalbotMotion._instance

    def __getattr__(self, name):
        return getattr(self._impl, name)


class GalbotRobot:
    """
    S1 的 GalbotRobot 包装，与 GalbotNavigation、GalbotMotion 用法一致。
    robot = GalbotRobot()
    robot.init()
    """
    _instance = None
    _py_instance = None

    def __new__(cls):
        if cls._py_instance is None:
            cls._py_instance = super().__new__(cls)
        return cls._py_instance

    def __init__(self):
        if GalbotRobot._instance is None:
            GalbotRobot._instance = _BaseGalbotRobot.get_instance(MachineType.S1)
            self._impl = GalbotRobot._instance

    def __getattr__(self, name):
        return getattr(self._impl, name)


# 暴露所有从父包导入的公开符号 + 本文件定义的 S1 包装类
__all__ = [name for name in globals().keys() if not name.startswith("_")]
