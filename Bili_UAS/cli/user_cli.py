"""
Bili_UAS.cli.user_cli

This module provides user command line interface configuration.
"""


import tyro
from typing import Union, Literal
from dataclasses import dataclass


@dataclass
class BiliUserConfigUpdate(object):
    """

    """
    name: Union[str, None] = None
    """username, either name or uid must be filled in"""
    uid: Union[str, None] = None
    """user uid, either name or uid must be filled in"""


@dataclass
class BiliUserConfigAddress(object):
    """

    """
    name: Union[str, None] = None
    """username, either name or uid must be filled in"""
    uid: Union[str, None] = None
    """user uid, either name or uid must be filled in"""
    mode: Literal[1, 2] = 1
    """address process mode, 1 for send, 2 for receive"""


mode_configs: dict[str, Union[BiliUserConfigUpdate, BiliUserConfigAddress]] = {}

descriptions: dict[str, str] = {
    "update": "Update user fan number, guard number, charging number.",
    "address": "Count the guard's address."
}

mode_configs["update"] = BiliUserConfigUpdate()
mode_configs["address"] = BiliUserConfigAddress()

UserConfigUnion = tyro.conf.SuppressFixed[
    tyro.conf.FlagConversionOff[
        tyro.extras.subcommand_type_from_defaults(defaults=mode_configs, descriptions=descriptions)
    ]
]
