"""Active Directory specific"""
from datetime import datetime
from enum import IntFlag
from typing import Any

from pytz import UTC

from authentik.core.models import User
from authentik.sources.ldap.sync.base import BaseLDAPSynchronizer


class UserAccountControl(IntFlag):
    """UserAccountControl attribute for Active directory users"""

    # https://docs.microsoft.com/en-us/troubleshoot/windows-server/identity
    #   /useraccountcontrol-manipulate-account-properties

    SCRIPT = 1
    ACCOUNTDISABLE = 2
    HOMEDIR_REQUIRED = 8
    LOCKOUT = 16
    PASSWD_NOTREQD = 32
    PASSWD_CANT_CHANGE = 64
    ENCRYPTED_TEXT_PWD_ALLOWED = 128
    TEMP_DUPLICATE_ACCOUNT = 256
    NORMAL_ACCOUNT = 512
    INTERDOMAIN_TRUST_ACCOUNT = 2048
    WORKSTATION_TRUST_ACCOUNT = 4096
    SERVER_TRUST_ACCOUNT = 8192
    DONT_EXPIRE_PASSWORD = 65536
    MNS_LOGON_ACCOUNT = 131072
    SMARTCARD_REQUIRED = 262144
    TRUSTED_FOR_DELEGATION = 524288
    NOT_DELEGATED = 1048576
    USE_DES_KEY_ONLY = 2097152
    DONT_REQ_PREAUTH = 4194304
    PASSWORD_EXPIRED = 8388608
    TRUSTED_TO_AUTH_FOR_DELEGATION = 16777216
    PARTIAL_SECRETS_ACCOUNT = 67108864


class MicrosoftActiveDirectory(BaseLDAPSynchronizer):
    """Microsoft-specific LDAP"""

    def sync(self, attributes: dict[str, Any], user: User, created: bool):
        self.ms_check_pwd_last_set(attributes, user, created)
        self.ms_check_uac(attributes, user)

    def ms_check_pwd_last_set(self, attributes: dict[str, Any], user: User, created: bool):
        """Check pwdLastSet"""
        pwd_last_set: datetime = attributes.get("pwdLastSet", datetime.now())
        pwd_last_set = pwd_last_set.replace(tzinfo=UTC)
        if created or pwd_last_set >= user.password_change_date:
            self.message(f"'{user.username}': Reset user's password")
            self._logger.debug(
                "Reset user's password",
                user=user.username,
                created=created,
                pwd_last_set=pwd_last_set,
            )
            user.set_unusable_password()
            user.save()

    def ms_check_uac(self, attributes: dict[str, Any], user: User):
        """Check userAccountControl"""
        if uac_bit := attributes.get("userAccountControl", None):
            # uac_bit: int = attributes.get("userAccountControl")
            uac = UserAccountControl(uac_bit)
            user.is_active = UserAccountControl.ACCOUNTDISABLE not in uac
            user.save()
