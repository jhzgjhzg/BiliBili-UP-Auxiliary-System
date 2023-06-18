"""
Bili-UAS.scripts.log_in

This module provides the function to log in to Bilibili, save and read credentials.
"""


__all__ = ['load_credential_from_json', "save_credential_to_json", "log_in_by_QR_code",
           "log_in_by_password", "log_in_by_verification_code"]


from bilibili_api import login, user, Credential
from bilibili_api import settings
from bilibili_api.exceptions import (CredentialNoBiliJctException, CredentialNoSessdataException,
                                     CredentialNoBuvid3Exception, CredentialNoDedeUserIDException)
import sys
import json
import os
from writer import log_writer as lw


async def load_credential_from_json(log_file: str) -> Credential:
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
        credential: Credential = Credential()
        return credential
    else:
        with open(config_file, "r") as f:
            credential_dict: dict = json.load(f)
            credential: Credential = Credential(sessdata=credential_dict["sessdata"],
                                                bili_jct=credential_dict["bili_jct"],
                                                buvid3=credential_dict["buvid3"],
                                                dedeuserid=credential_dict["dedeuserid"])
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
                             "dedeuserid": credential.dedeuserid}
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

    log.info("请扫描二维码...")
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

    log.info("请输入用户名（手机号/邮箱）：\n")
    user_name: str = str(sys.stdin.readline())
    log.info("请输入密码：\n")
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
    log.info("请输入手机号：\n")
    phone_number: str = str(sys.stdin.readline())
    login.send_sms(login.PhoneNumber(phone_number, country="+86"))
    log.info("请输入验证码：\n")
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
