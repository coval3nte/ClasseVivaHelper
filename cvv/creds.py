"""creds helper module"""
from pathlib import Path
from os import path
from colorama import Fore
from yaml import dump, load, Loader
CRED_FILE = str(Path.home()) + '/cvv-credentials.yml'


class Creds:
    """creds helper class"""

    def __init__(self):
        self.creds = {}
        if path.exists(CRED_FILE):
            self._load()
        else:
            self._write()

    def _write_yaml(self):
        with open(CRED_FILE, 'w', encoding='utf-8') as file:
            dump(self.creds, file)

    def _load(self):
        with open(CRED_FILE, 'r', encoding='utf-8') as file:
            self.creds = load(file, Loader)

    def _write(self):
        self.creds = {
            'mail': input('email: '),
            'password': input('password: '),
            'session': '',
        }

        self._write_yaml()

        print(f'{Fore.GREEN}credentials{Fore.RESET} saved at: '
              f'{Fore.MAGENTA}{CRED_FILE}{Fore.RESET}')

    def get_creds(self):
        """get creds"""
        return self.creds.items()

    def write_session(self, session):
        """writes php session"""
        self.creds["session"] = session
        self._write_yaml()
