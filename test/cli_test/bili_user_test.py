"""
Test for bili_user.py
"""


from Bili_UAS import bili_user as bu
from Bili_UAS.cli import user_cli as cuc


def update_test():
    """
    Main function for update test.
    """
    print("Update test:")
    config: cuc.BiliUserConfigUpdate = cuc.BiliUserConfigUpdate()
    config.name = "..."
    bu.sync_tyro_main(config)


if __name__ == '__main__':
    update_test()
    pass
