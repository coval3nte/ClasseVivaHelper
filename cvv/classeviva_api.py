"""classeviva api"""

from warnings import warn
from requests import post, get
from .creds import Creds
from .methods import Absences, Lessons, Grades, Files, Assignments


class CVV:
    """interact classeviva api"""
    class AuthError(Exception):
        """auth exception"""

        def __init__(self, message):
            super().__init__(self, message)

    class GenericError(Exception):
        """generic exception"""

        def __init__(self):
            super().__init__(self, "something went wrong "
                             "while communicating with CVV API's")

    class MissingArgs(Exception):
        """missing args exception"""

        def __init__(self, message):
            super().__init__(self, message)

    def __getattr__(self, name):
        """avoid pylint E1101"""
        warn(f'No member "{name}" contained in settings config.')
        return ''

    def __init__(self, **kwargs):
        # args, mail, password, session
        self.__dict__.update(kwargs)
        self.endpoint = "https://web.spaggiari.eu"
        self.headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:47.0) "
                          "Gecko/20100101 Firefox/47.0"
        }
        self.cookies = {"PHPSESSID": self.session}
        if (not self.session) or (not self._test_session()):
            self._login()

        self.assignments = {}
        self.grades, self.absences = {}, {}

    def _test_session(self):
        return get(self.endpoint +
                   '/home/app/default/menu_webinfoschool_studenti.php',
                   cookies=self.cookies,
                   headers=self.headers,
                   allow_redirects=False
                   ).status_code == 200

    def _login(self):
        params = {
            "a": "aLoginPwd"
        }

        data = {
            "cid": "",
            "uid": self.mail,
            "pwd": self.password,
            "pin": "",
            "target": ""
        }

        login = post(self.endpoint + '/auth-p7/app/default/AuthApi4.php',
                     params=params,
                     data=data,
                     headers=self.headers)

        if login.status_code == 200:
            if "data" in login.json():
                if login.json()["data"]["auth"]["verified"]:
                    self.cookies["PHPSESSID"] = login.cookies.get_dict()[
                        "PHPSESSID"]
                    Creds().write_session(self.cookies["PHPSESSID"])
                else:
                    raise self.AuthError(
                        ', '.join(login.json()["data"]["auth"]["errors"]))
        else:
            raise self.AuthError(login.text)

    def sanitize_grade(self, grade):
        """sanitize grade"""
        return Grades(self).sanitize_grade(grade)

    def get_lessons(self, start_date=''):
        """get today"""
        return Lessons(self, start_date).get_lessons()

    def get_assignment(self, index):
        """get assignment"""
        return Assignments(self).get_assignment(index)

    def get_assignments_keys(self):
        """get assignment keys"""
        return Assignments(self).get_keys()

    def get_files(self):
        """get files"""
        return list(reversed(Files(self).retrieve_files()))

    def get_grades(self):
        """get grades"""
        return Grades(self).get_grades()

    def get_terms_keys(self):
        """get terms keys"""
        return Grades(self).get_terms_keys()

    def get_subject_keys(self, index):
        """get subject keys"""
        return Grades(self).get_subject_keys(index)

    def get_average(self, index):
        """get average"""
        return Grades(self).get_average(index)

    def get_subject_average(self, index, subject):
        """get subject average"""
        return Grades(self).get_subject_average(index, subject)

    def get_trend(self, index, subject):
        """get trend"""
        return Grades(self).get_trend(index, subject)

    def get_absences(self):
        """get absences"""
        return Absences(self).get_absences()

    def justify_absence(self, index, reason):
        """justify absence"""
        return Absences(self).justify_absence(index, reason)

    def download_file(self, filename, contenuto_id, cksum):
        """download file"""
        return Files(self).download_file(filename, contenuto_id, cksum)
