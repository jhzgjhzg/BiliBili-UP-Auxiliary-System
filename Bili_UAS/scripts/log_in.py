"""
Bili_UAS.scripts.log_in

This module provides the function to log in to Bilibili, save and read credentials.
"""


from __future__ import annotations
from bilibili_api import login, user, Credential
from bilibili_api import settings
from bilibili_api.exceptions import (CredentialNoBiliJctException, CredentialNoSessdataException,
                                     CredentialNoBuvid3Exception, CredentialNoDedeUserIDException)
import sys
import json
import os
from Bili_UAS.writer import log_writer as lw
import enum
from typing import Union


class LoginMode(enum.Enum):
    """
    Login method Enumeration Class
    """
    QR = 1
    PASSWORD = 2
    VERIFICATION = 3
    PARAMETER = 4


async def load_credential_from_json(log_file: str) -> Union[Credential, None]:
    """
    Load credential from json file.

    Args:
        log_file: the log file
    """
    file_handler: lw.Handler = lw.Handler("file")
    file_handler.set_level("WARNING", "ERROR")
    file_handler.set_file(log_file)

    sys_handler: lw.Handler = lw.Handler("sys")
    sys_handler.set_level("INFO", "WARNING")

    log: lw.Logger = lw.Logger()
    log.add_config(file_handler)
    log.add_config(sys_handler)

    config_file: str = ".config.json"
    if not os.path.exists(config_file):
        log.warning("No historical login records found, using empty credential!")
        return None
    else:
        with open(config_file, "r") as f:
            credential_dict: dict = json.load(f)
            credential: Credential = Credential(sessdata=credential_dict["sessdata"],
                                                bili_jct=credential_dict["bili_jct"],
                                                buvid3=credential_dict["buvid3"],
                                                dedeuserid=credential_dict["dedeuserid"],
                                                ac_time_value=credential_dict["ac_time_value"])
        log.info("Historical login records found, using historical credential.")
        return credential


async def save_credential_to_json(credential: Credential, log_file: str) -> None:
    """
    Save credential to json file.

    Args:
        credential: logon credentials
        log_file: the log file
    """
    file_handler: lw.Handler = lw.Handler("file")
    file_handler.set_level("WARNING", "ERROR")
    file_handler.set_file(log_file)

    sys_handler: lw.Handler = lw.Handler("sys")
    sys_handler.set_level("INFO", "WARNING")

    log: lw.Logger = lw.Logger()
    log.add_config(file_handler)
    log.add_config(sys_handler)

    config_file: str = ".config.json"
    credential_dict: dict = {"sessdata": credential.sessdata,
                             "bili_jct": credential.bili_jct,
                             "buvid3": credential.buvid3,
                             "dedeuserid": credential.dedeuserid,
                             "ac_time_value": credential.ac_time_value}
    with open(config_file, "w") as f:
        json.dump(credential_dict, f, indent=4)
    log.info("Credential saved successfully.")


async def save_credential_by_parm_to_json(sessdata: str,
                                          bili_jct: str,
                                          buvid3: str,
                                          dedeuserid: str,
                                          ac_time_value: str,
                                          log_file: str) -> None:
    """
    Save credential parameters to json file.

    Args:
        sessdata: credential sessdata
        bili_jct: credential bili_jct
        buvid3: credential buvid3
        dedeuserid: credential dedeuserid
        ac_time_value: credential ac_time_value
        log_file: the log file
    """
    file_handler: lw.Handler = lw.Handler("file")
    file_handler.set_level("WARNING", "ERROR")
    file_handler.set_file(log_file)

    sys_handler: lw.Handler = lw.Handler("sys")
    sys_handler.set_level("INFO", "WARNING")

    log: lw.Logger = lw.Logger()
    log.add_config(file_handler)
    log.add_config(sys_handler)

    config_file: str = ".config.json"
    credential_dict: dict = {"sessdata": sessdata,
                             "bili_jct": bili_jct,
                             "buvid3": buvid3,
                             "dedeuserid": dedeuserid,
                             "ac_time_value": ac_time_value}
    with open(config_file, "w") as f:
        json.dump(credential_dict, f, indent=4)
    log.info("Credential saved successfully.")


async def log_in_by_QR_code(log_file: str) -> bool:
    """
    Login to a Bilibili account by scanning QR code.

    Args:
        log_file: the log file

    Returns:
        True if login successfully, False otherwise.
    """
    file_handler: lw.Handler = lw.Handler("file")
    file_handler.set_level("WARNING", "ERROR")
    file_handler.set_file(log_file)

    sys_handler: lw.Handler = lw.Handler("sys")
    sys_handler.set_level("INFO", "WARNING")

    log: lw.Logger = lw.Logger()
    log.add_config(file_handler)
    log.add_config(sys_handler)

    log.info("Please scan the QR code.")
    credential: Credential = login.login_with_qrcode()

    try:
        await credential.raise_for_no_sessdata()
    except CredentialNoSessdataException:
        log.error("Login failed!")
        return False

    try:
        await credential.raise_for_no_bili_jct()
    except CredentialNoBiliJctException:
        log.error("Login failed!")
        return False

    try:
        await credential.raise_for_no_buvid3()
    except CredentialNoBuvid3Exception:
        log.error("Login failed!")
        return False

    try:
        await credential.raise_for_no_dedeuserid()
    except CredentialNoDedeUserIDException:
        log.error("Login failed!")
        return False

    user_info: dict = await user.get_self_info(credential)
    log.info(f"Login successfully! Welcome {user_info['name']}!")
    await save_credential_to_json(credential, log_file)
    return True


async def log_in_by_password(log_file: str) -> bool:
    """
    Login to a Bilibili account by entering the password.

    Args:
        log_file: the log file

    Returns:
        True if login successfully, False otherwise.
    """
    file_handler: lw.Handler = lw.Handler("file")
    file_handler.set_level("WARNING", "ERROR")
    file_handler.set_file(log_file)

    sys_handler: lw.Handler = lw.Handler("sys")
    sys_handler.set_level("INFO", "WARNING")

    log: lw.Logger = lw.Logger()
    log.add_config(file_handler)
    log.add_config(sys_handler)

    log.info("Please enter your username (phone number/email):\n")
    user_name: str = str(sys.stdin.readline())
    log.info("Please enter password:\n")
    password: str = str(sys.stdin.readline())

    c = login.login_with_password(user_name, password)

    if isinstance(c, login.Check):
        log.error("Login failed!")
        return False
    else:
        credential: Credential = c

    try:
        await credential.raise_for_no_sessdata()
    except CredentialNoSessdataException:
        log.error("Login failed!")
        return False

    try:
        await credential.raise_for_no_bili_jct()
    except CredentialNoBiliJctException:
        log.error("Login failed!")
        return False

    try:
        await credential.raise_for_no_buvid3()
    except CredentialNoBuvid3Exception:
        log.error("Login failed!")
        return False

    try:
        await credential.raise_for_no_dedeuserid()
    except CredentialNoDedeUserIDException:
        log.error("Login failed!")
        return False

    user_info: dict = await user.get_self_info(credential)
    log.info(f"Login successfully! Welcome {user_info['name']}!")
    await save_credential_to_json(credential, log_file)
    return True


async def log_in_by_verification_code(log_file: str) -> bool:
    """
    Login to a Bilibili account by using the verification code.

    Args:
        log_file: the log file

    Returns:
        True if login successfully, False otherwise.
    """
    file_handler: lw.Handler = lw.Handler("file")
    file_handler.set_level("WARNING", "ERROR")
    file_handler.set_file(log_file)

    sys_handler: lw.Handler = lw.Handler("sys")
    sys_handler.set_level("INFO", "WARNING")

    log: lw.Logger = lw.Logger()
    log.add_config(file_handler)
    log.add_config(sys_handler)

    settings.geetest_auto_open = False
    log.info("Please enter your phone number:\n")
    phone_number: str = str(sys.stdin.readline())
    log.info("Please wait for receiving the verification code...")
    login.send_sms(login.PhoneNumber(phone_number, country="+86"))
    log.info("Please enter the verification code:\n")
    code: str = str(sys.stdin.readline())
    c = login.login_with_sms(login.PhoneNumber(phone_number, country="+86"), code)

    if isinstance(c, login.Check):
        log.error("Login failed!")
        return False
    else:
        credential: Credential = c

    try:
        await credential.raise_for_no_sessdata()
    except CredentialNoSessdataException:
        log.error("Login failed!")
        return False

    try:
        await credential.raise_for_no_bili_jct()
    except CredentialNoBiliJctException:
        log.error("Login failed!")
        return False

    try:
        await credential.raise_for_no_buvid3()
    except CredentialNoBuvid3Exception:
        log.error("Login failed!")
        return False

    try:
        await credential.raise_for_no_dedeuserid()
    except CredentialNoDedeUserIDException:
        log.error("Login failed!")
        return False

    user_info: dict = await user.get_self_info(credential)
    log.info(f"Login successfully! Welcome {user_info['name']}!")
    await save_credential_to_json(credential, log_file)
    return True


async def refresh_credential(credential: Credential, log_file: str) -> Credential:
    """
    Refresh the credential.

    Args:
        credential: logon credentials
        log_file: the log file

    Returns:
        refreshed credential
    """
    file_handler: lw.Handler = lw.Handler("file")
    file_handler.set_level("WARNING", "ERROR")
    file_handler.set_file(log_file)

    sys_handler: lw.Handler = lw.Handler("sys")
    sys_handler.set_level("INFO", "WARNING")

    log: lw.Logger = lw.Logger()
    log.add_config(file_handler)
    log.add_config(sys_handler)

    if credential.chcek_refresh():
        await credential.refresh()
        log.info("Credential refreshed successfully.")
    else:
        log.warning("Credential do not need to be refreshed.")

    return credential
