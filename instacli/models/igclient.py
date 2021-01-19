from instaclient import InstaClient
from instaclient.errors.common import InvaildPasswordError, InvalidUserError, SuspisciousLoginAttemptError, VerificationCodeNecessary
from .settings import Settings
import click

class IGClient(InstaClient):
    def __init__(self):
        settings = Settings()
        super().__init__(driver_path=settings.driver_path, debug=settings.logging, localhost_headless=not settings.driver_visible)

    def login(self, username: str, password: str) -> bool:
        while True:
            try:
                super().login(username, password)
                return True
            except InvalidUserError:
                username = click.prompt(f"The username {username} is invalid. Please enter it again: ")
                continue
            except InvaildPasswordError:
                password = click.prompt(f"The password you provided is invalid. Please enter it again: ")
                continue
            except SuspisciousLoginAttemptError as error:
                if error.mode == SuspisciousLoginAttemptError.EMAIL:
                    mode = 'email'
                else:
                    mode = 'SMS'
                code = click.prompt(f"Instagram detected suspicious activity. You have received a code via {mode}. Please enter it here: ")
            except VerificationCodeNecessary as error:
                click.echo("Please turn off Instagram two-step-security for the bot to work prperly.")
                return False