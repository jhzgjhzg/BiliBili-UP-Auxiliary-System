"""
Test for bili_login.py
"""


from Bili_UAS import bili_login as bl


def QR_test():
    """
    Main function for QR code login test.
    """
    print("QR code login test:")
    bl.sync_tyro_main()


def password_test():
    """
    Main function for password login test.
    """
    print("Password login test:")
    bl.sync_tyro_main(2)


def verification_test():
    """
    Main function for verification code login test.
    """
    print("Verification code login test:")
    bl.sync_tyro_main(3)


def parameter_test():
    """
    Main function for parameter login test.
    """
    print("Parameter login test:")
    bl.sync_tyro_main(4, "sessdata", "bili_jct", "buvid3", "dedeuserid", "ac_time_value")


if __name__ == "__main__":
    # QR_test()
    password_test()
    # verification_test()
    # parameter_test()
    pass
