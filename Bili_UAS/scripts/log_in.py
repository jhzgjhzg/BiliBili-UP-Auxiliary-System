"""
Bili_UAS.scripts.log_in

This module provides the function to log in to Bilibili, save and read credentials.
"""


from __future__ import annotations
from bilibili_api import login, user, Credential, sync
from bilibili_api import settings
from bilibili_api.exceptions import (CredentialNoBiliJctException, CredentialNoSessdataException,
                                     CredentialNoBuvid3Exception, CredentialNoDedeUserIDException)
import sys
import json
import os
from Bili_UAS.writer import log_writer as wlw
from Bili_UAS.utils.config_utils import load_language_from_txt
import enum
from typing import Union
import getpass


language: str = load_language_from_txt()


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
    file_handler: wlw.Handler = wlw.Handler("file")
    file_handler.set_level("WARNING", "ERROR")
    file_handler.set_file(log_file)

    sys_handler: wlw.Handler = wlw.Handler("sys")
    sys_handler.set_level("INFO", "WARNING")

    log: wlw.Logger = wlw.Logger()
    log.add_config(file_handler)
    log.add_config(sys_handler)

    config_file: str = ".config.json"
    if not os.path.exists(config_file):
        if language == "en":
            log.warning("No historical login records found, using empty credential!")
        else:
            log.warning("未找到历史登录记录，使用空登录数据！")
        return None
    else:
        with open(config_file, "r") as f:
            credential_dict: dict = json.load(f)
            credential: Credential = Credential(sessdata=credential_dict["sessdata"],
                                                bili_jct=credential_dict["bili_jct"],
                                                buvid3=credential_dict["buvid3"],
                                                dedeuserid=credential_dict["dedeuserid"],
                                                ac_time_value=credential_dict["ac_time_value"])
        if language == "en":
            log.info("Historical login records found, using historical credential.")
        else:
            log.info("找到历史登录记录，使用历史登录数据。")
        return credential


async def save_credential_to_json(credential: Credential, log_file: str) -> None:
    """
    Save credential to json file.

    Args:
        credential: logon credentials
        log_file: the log file
    """
    file_handler: wlw.Handler = wlw.Handler("file")
    file_handler.set_level("WARNING", "ERROR")
    file_handler.set_file(log_file)

    sys_handler: wlw.Handler = wlw.Handler("sys")
    sys_handler.set_level("INFO", "WARNING")

    log: wlw.Logger = wlw.Logger()
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
    if language == "en":
        log.info("Credential saved successfully.")
    else:
        log.info("登录数据保存成功。")


async def save_credential_by_parm_to_json(sessdata: str,
                                          bili_jct: str,
                                          buvid3: str,
                                          dedeuserid: str,
                                          ac_time_value: str,
                                          log_file: str) -> bool:
    """
    Save credential parameters to json file.

    Args:
        sessdata: credential sessdata
        bili_jct: credential bili_jct
        buvid3: credential buvid3
        dedeuserid: credential dedeuserid
        ac_time_value: credential ac_time_value
        log_file: the log file

    Returns:
        True if login successfully, False otherwise.
    """
    file_handler: wlw.Handler = wlw.Handler("file")
    file_handler.set_level("WARNING", "ERROR")
    file_handler.set_file(log_file)

    sys_handler: wlw.Handler = wlw.Handler("sys")
    sys_handler.set_level("INFO", "WARNING")

    log: wlw.Logger = wlw.Logger()
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
    if language == "en":
        log.info("Credential saved successfully.")
    else:
        log.info("登录数据保存成功。")
    return True


async def check_credential(credential: Credential, log: wlw.Logger) -> bool:
    """
    Check if the credential is valid.

    Args:
        credential: login credentials
        log: the logger class

    Returns:
        True if credential is valid, False otherwise.
    """
    try:
        credential.raise_for_no_sessdata()
    except CredentialNoSessdataException:
        if language == "en":
            log.error("Login failed! Missing sessdata.")
        else:
            log.error("登录失败！缺失 sessdata。")
        return False

    try:
        credential.raise_for_no_bili_jct()
    except CredentialNoBiliJctException:
        if language == "en":
            log.error("Login failed! Missing bili_jct.")
        else:
            log.error("登录失败！缺失 bili_jct。")
        return False

    try:
        credential.raise_for_no_buvid3()
    except CredentialNoBuvid3Exception:
        if language == "en":
            log.error("Login failed! Missing buvid3.")
        else:
            log.error("登录失败！缺失 buvid3。")
        return False

    try:
        credential.raise_for_no_dedeuserid()
    except CredentialNoDedeUserIDException:
        if language == "en":
            log.error("Login failed! Missing dedeuserid.")
        else:
            log.error("登录失败！缺失 dedeuserid。")
        return False

    try:
        credential.raise_for_no_ac_time_value()
    except CredentialNoDedeUserIDException:
        if language == "en":
            log.error("Login failed! Missing ac_time_value.")
        else:
            log.error("登录失败！缺失 ac_time_value。")
        return False

    return True


def log_in_by_QR_code(log_file: str) -> bool:
    """
    Login to a Bilibili account by scanning QR code.

    Args:
        log_file: the log file

    Returns:
        True if login successfully, False otherwise.
    """
    file_handler: wlw.Handler = wlw.Handler("file")
    file_handler.set_level("WARNING", "ERROR")
    file_handler.set_file(log_file)

    sys_handler: wlw.Handler = wlw.Handler("sys")
    sys_handler.set_level("INFO", "WARNING")

    log: wlw.Logger = wlw.Logger()
    log.add_config(file_handler)
    log.add_config(sys_handler)

    if language == "en":
        log.info("Please scan the QR code.")
    else:
        log.info("请扫描二维码。")
    credential: Credential = login.login_with_qrcode()

    if not sync(check_credential(credential, log)):
        return False

    user_info: dict = sync(user.get_self_info(credential))
    if language == "en":
        log.info(f"Login successfully! Welcome {user_info['name']}!")
    else:
        log.info(f"登录成功！欢迎您，{user_info['name']}！")
    sync(save_credential_to_json(credential, log_file))
    return True


def log_in_by_password(log_file: str) -> bool:
    """
    Login to a Bilibili account by entering the password.

    Args:
        log_file: the log file

    Returns:
        True if login successfully, False otherwise.
    """
    file_handler: wlw.Handler = wlw.Handler("file")
    file_handler.set_level("WARNING", "ERROR")
    file_handler.set_file(log_file)

    sys_handler: wlw.Handler = wlw.Handler("sys")
    sys_handler.set_level("INFO", "WARNING")

    log: wlw.Logger = wlw.Logger()
    log.add_config(file_handler)
    log.add_config(sys_handler)

    if language == "en":
        log.info("Please enter your username (phone number/email):")
    else:
        log.info("请输入您的用户名（手机号/邮箱）：")
    user_name: str = str(sys.stdin.readline()).removesuffix("\n")
    if language == "en":
        password: str = str(getpass.getpass("Please enter password:\n"))
    else:
        password: str = str(getpass.getpass("请输入密码：\n"))

    c = login.login_with_password(user_name, password)

    if isinstance(c, login.Check):
        if language == "en":
            log.error("Login failed! Still need to verify.")
        else:
            log.error("登录失败！仍需要验证。")
        return False
    else:
        credential: Credential = c
    credential.buvid3 = login.get_live_buvid()

    if not sync(check_credential(credential, log)):
        return False

    user_info: dict = sync(user.get_self_info(credential))
    if language == "en":
        log.info(f"Login successfully! Welcome {user_info['name']}!")
    else:
        log.info(f"登录成功！欢迎您，{user_info['name']}！")
    sync(save_credential_to_json(credential, log_file))
    return True


def log_in_by_verification_code(log_file: str) -> bool:
    """
    Login to a Bilibili account by using the verification code.

    Args:
        log_file: the log file

    Returns:
        True if login successfully, False otherwise.
    """
    file_handler: wlw.Handler = wlw.Handler("file")
    file_handler.set_level("WARNING", "ERROR")
    file_handler.set_file(log_file)

    sys_handler: wlw.Handler = wlw.Handler("sys")
    sys_handler.set_level("INFO", "WARNING")

    log: wlw.Logger = wlw.Logger()
    log.add_config(file_handler)
    log.add_config(sys_handler)

    settings.geetest_auto_open = False
    if language == "en":
        log.info("Please enter your phone number:")
    else:
        log.info("请输入您的手机号：")
    phone_number: str = str(sys.stdin.readline()).removesuffix("\n")
    if language == "en":
        log.info("Please wait for receiving the verification code...")
    else:
        log.info("请等待接收验证码...")
    login.send_sms(login.PhoneNumber(phone_number, country="+86"))
    if language == "en":
        code: str = str(getpass.getpass("Please enter the verification code:\n"))
    else:
        code: str = str(getpass.getpass("请输入验证码：\n"))
    c = login.login_with_sms(login.PhoneNumber(phone_number, country="+86"), code)

    if isinstance(c, login.Check):
        if language == "en":
            log.error("Login failed! Still need to verify.")
        else:
            log.error("登录失败！仍需要验证。")
        return False
    else:
        credential: Credential = c
    credential.buvid3 = login.get_live_buvid()

    if not sync(check_credential(credential, log)):
        return False

    user_info: dict = sync(user.get_self_info(credential))
    if language == "en":
        log.info(f"Login successfully! Welcome {user_info['name']}!")
    else:
        log.info(f"登录成功！欢迎您，{user_info['name']}！")
    sync(save_credential_to_json(credential, log_file))
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
    file_handler: wlw.Handler = wlw.Handler("file")
    file_handler.set_level("WARNING", "ERROR")
    file_handler.set_file(log_file)

    sys_handler: wlw.Handler = wlw.Handler("sys")
    sys_handler.set_level("INFO", "WARNING")

    log: wlw.Logger = wlw.Logger()
    log.add_config(file_handler)
    log.add_config(sys_handler)

    if await credential.check_refresh():
        await credential.refresh()
        if language == "en":
            log.info("Credential refreshed successfully.")
        else:
            log.info("登录数据刷新成功。")
    else:
        if language == "en":
            log.warning("Credential do not need to be refreshed.")
        else:
            log.warning("登录数据不需要刷新。")

    return credential
