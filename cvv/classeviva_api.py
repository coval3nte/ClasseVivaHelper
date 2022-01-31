"""classeviva api"""

from os import path, makedirs
from re import findall
from datetime import datetime, timedelta
from time import time
from typing import Dict
from warnings import warn
import numpy as np
from requests import post, get
from lxml import html
from .data_types import Assignment, File, Grade, Lesson, Absence
from .creds import Creds


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
        return self.Grades(self).sanitize_grade(grade)

    def get_lessons(self, start_date=''):
        """get today"""
        return self.Lesson(self, start_date).get_lessons()

    def get_assignment(self, index):
        """get assignment"""
        return self.Assignments(self).get_assignment(index)

    def get_assignments_keys(self):
        """get assignment keys"""
        return self.Assignments(self).get_keys()

    def get_files(self):
        """get files"""
        return list(reversed(self.Files(self).retrieve_files()))

    def get_grades(self):
        """get grades"""
        return self.Grades(self).get_grades()

    def get_terms_keys(self):
        """get terms keys"""
        return self.Grades(self).get_terms_keys()

    def get_subject_keys(self, index):
        """get subject keys"""
        return self.Grades(self).get_subject_keys(index)

    def get_average(self, index):
        """get average"""
        return self.Grades(self).get_average(index)

    def get_subject_average(self, index, subject):
        """get subject average"""
        return self.Grades(self).get_subject_average(index, subject)

    def get_trend(self, index, subject):
        """get trend"""
        return self.Grades(self).get_trend(index, subject)

    def get_absences(self):
        return self.Absence(self).get_absences()

    def justify_absence(self, index, reason):
        return self.Absence(self).justify_absence(index, reason)

    def download_file(self, filename, contenuto_id, cksum):
        """download file"""
        return self.Files(self).download_file(filename, contenuto_id, cksum)

    class Absence:
        """absence parsing class"""

        def __init__(self, cvv):
            self.cvv = cvv
            if not self.cvv.absences:
                self.cvv.absences = self.retrieve_absences()

        def _do_absence(self):
            params = {
                'evento': 'A'
            }

            req = get(self.cvv.endpoint +
                      "/fml/app/default/librettoweb_eventi.php",
                      cookies=self.cvv.cookies,
                      headers=self.cvv.headers,
                      params=params)
            if req.status_code != 200:
                raise self.cvv.GenericError
            return req.text

        def retrieve_absences(self):
            absences_list = []

            tree = html.fromstring(self._do_absence())
            absences = tree.xpath(
                '//table[@id="data_table"]'
                '//tr[@style="vertical-align: middle;"]')
            for absence in absences:
                absence_text = absence.xpath(
                    '//div[@style="width: 100%; "]'
                    '/span[@class="open_sans_semibold font_size_12"]'
                )[0].text_content().strip()
                absence_elem = absence.xpath(
                    '//div[@class="my_button gray_button'
                    ' cursor_pointer btn_assenza"]'
                )[0]
                data_start = absence_elem.xpath('@data_start')[0]
                data_stop = absence_elem.xpath('@data_stop')[0]
                anno_scol = absence_elem.xpath('@anno_scol')[0]
                absences_list.append(Absence(absence_text,
                                             data_start,
                                             data_stop,
                                             anno_scol
                                             ))
            return absences_list

        def _justify_absence(self, index, reason):
            absence = self.cvv.absences[index]
            params = {
                'a': 'insertGiu',
                'evento_codice': 'A',
                'tipo_giustifica': '0',
                'causale': 'C',
                'inizio_assenza': absence.data_start,
                'fine_assenza': absence.data_stop,
                'motivazione_assenza': reason,
                'giorno_entrata_uscita': absence.data_start,
                'ora_entrata_uscita': '',
                'motivazione_entrata_uscita': '',
                'accompagnatore': '',
                'flag_parziale': '',
            }
            req = post(self.cvv.endpoint +
                       "/fml/app/default/librettoweb_eventi_io.php",
                       data=params,
                       cookies=self.cvv.cookies,
                       headers=self.cvv.headers,
                       )
            if req.status_code != 200:
                raise self.cvv.GenericError
            if 'OK' in req.text:
                return True
            return False

        def justify_absence(self, index, reason):
            return self._justify_absence(index, reason)

        def get_absences(self):
            return self.cvv.absences

    class Lesson:
        """lesson parsing class"""

        def __init__(self, cvv, start_date=''):
            self.cvv = cvv
            self.start_date = start_date

        def _do_lessons(self):
            params = {
                'data_start': self.start_date,
            }
            today = get(self.cvv.endpoint +
                        "/fml/app/default/regclasse.php",
                        cookies=self.cvv.cookies,
                        headers=self.cvv.headers,
                        params=params)
            if today.status_code != 200:
                raise self.cvv.GenericError
            return today.text

        def retrieve_lessons(self):
            tree = html.fromstring(self._do_lessons())
            trs = tree.xpath('(//table[@id="data_table"])[2]/tr')
            subjects = []
            for tr in trs:
                teacher_name = ''.join(tr.xpath(
                    'td[@class="registro_firma_dett_docente"]//text()')
                ).strip()
                teacher_subject = ''.join(tr.xpath(
                    'td[@class="registro_firma_dett_materia"]//text()')
                ).replace('\n', ' ').strip()
                hour = ''.join(
                    tr.xpath('td[@class="registro_firma_dett_ora"]//text()')
                ).strip()
                topic = ''.join(
                    tr.xpath(
                        'td[@class="registro_firma_dett_argomento_lezione'
                        ' bluetext"]/*[2]/text()')).strip()
                if hour == '':
                    continue
                subjects.append(Lesson(
                    teacher_name,
                    teacher_subject,
                    hour,
                    topic,
                ))
            return subjects

        def get_lessons(self):
            return self.retrieve_lessons()

    class Grades:
        """grades parsing class"""

        def __init__(self, cvv):
            self.cvv = cvv
            if not self.cvv.grades:
                self.retrieve_grades()

        def _do_grades(self):
            grades = get(self.cvv.endpoint +
                         '/cvv/app/default/genitori_voti.php',
                         cookies=self.cvv.cookies,
                         headers=self.cvv.headers)
            if grades.status_code != 200:
                raise self.cvv.GenericError
            return grades.text

        @classmethod
        def sanitize_grade(cls, grade):
            bad_words = ['+', '-', '½']
            irc = {
                'o': 10,
                'd': 8,
                'b': 7,
                's': 6,
                'ns': 5
            }
            grade = grade.strip().rstrip(''.join(bad_words))

            if grade in irc:
                return irc[grade]

            grade_new = int(grade)
            if bad_words[0] in grade:
                grade_new += 0.25
            if bad_words[1] in grade:
                grade_new -= 0.25
            if bad_words[2] in grade:
                grade_new += 0.5
            return grade_new

        @classmethod
        def _trend(cls, grades_list):
            coeffs = np.polyfit(range(1, len(grades_list)+1), grades_list, 1)
            slope = coeffs[-2]
            return float(slope)

        def retrieve_grades(self):
            """parse grades"""
            tree = html.fromstring(self._do_grades())
            school_terms = tree.xpath('//*[@class="outer"]/@id')

            for term in school_terms:
                grades_dict = {}
                trs = tree.xpath(
                    f"//*[@id=\"{term}\"]//"
                    f"table[@sessione=\"{term}\"]//"
                    f"tr[contains(@sessione, \"{term}\") and "
                    f"contains(@class, \"riga_materia_componente\")]"
                )
                for xpath_tr in trs:
                    subject = xpath_tr.xpath(
                        'td')[0].text_content().strip().capitalize()
                    grades_dict[subject] = []

                    voti = xpath_tr.xpath(
                        'td[@class="registro cella_voto :sfondocella:"]')
                    for voto in voti:
                        grade_date = voto.xpath('span')[0].text_content()
                        if int(grade_date.split('/')[1]) > 8:
                            grade_year = datetime.now().year-1
                        else:
                            grade_year = datetime.now().year

                        grades_dict[subject].append(Grade(
                            voto.xpath(
                                'div/p')[0].text_content(),
                            f'{grade_date}/{grade_year}'))
                if len(grades_dict):
                    self.cvv.grades[term] = grades_dict

            return self.cvv.grades

        def get_grades(self):
            """get grades"""
            return self.cvv.grades

        def get_terms_keys(self):
            """get school terms keys"""
            return list(self.get_grades().keys())

        def get_subject_keys(self, index):
            """get subject keys"""
            return list(self.get_grades()[index].keys())

        def _get_all_grades(self, index):
            grades = []
            if not self.get_grades()[index]:
                return 0.0
            for subject in self.get_grades()[index]:
                for grade in self.get_grades()[index][subject]:
                    grades.append(self.sanitize_grade(grade.grade))
            return grades

        def get_subject_average(self, index, subject):
            """get subject average"""
            if not self.get_grades()[index][subject]:
                return 0.0
            return np.average([self.sanitize_grade(grade.grade) for grade
                               in self.get_grades()[index][subject]])

        def get_average(self, index):
            """get average"""
            return np.average(self._get_all_grades(index))

        def get_trend(self, index, subject):
            """get trend"""
            grades = [self.sanitize_grade(x.grade)
                      for x in self.get_grades()[index][subject]]
            if len(grades) <= 1 or len(set(grades)) == 1:
                return None
            trend = self._trend(grades)

            return trend > 0 < trend

    class Files:
        """files downloader class"""

        def __init__(self, cvv):
            self.cvv = cvv

        def _do_files(self, params):
            files = get(self.cvv.endpoint +
                        '/fml/app/default/didattica_genitori_new.php',
                        params=params,
                        cookies=self.cvv.cookies,
                        headers=self.cvv.headers
                        )

            if files.status_code != 200:
                raise self.cvv.GenericError
            return files.text

        def _do_pages(self):
            params = {
                'p': 1
            }

            files_pages = []
            init = self._do_files(params)
            files_pages.append(init)
            length = int(init.split("Pagina 1/")[1][0:1]) - 1

            for _ in range(length):
                params['p'] += 1
                files_pages.append(self._do_files(params))

            return files_pages

        def download_file(self, filename, contenuto_id, cksum):
            """download file"""
            params = {
                'a': 'downloadContenuto',
                'contenuto_id': contenuto_id,
                'cksum': cksum
            }
            resp = get(self.cvv.endpoint +
                       '/fml/app/default/didattica_genitori.php',
                       params=params,
                       cookies=self.cvv.cookies,
                       headers=self.cvv.headers)
            if resp.status_code != 200:
                raise self.cvv.GenericError

            save_folder = self.cvv.args.save_folder.rstrip('/')
            if not path.exists(save_folder):
                makedirs(save_folder)
            with open(save_folder+"/"+filename+'.' +
                      findall("filename=(.+)",
                              resp.headers['content-disposition']
                              )[0].split('.')[-1],
                      'wb') as file:
                file.write(resp.content)

        def retrieve_files(self):
            """retrieve files"""
            files_pages = self._do_pages()
            files_list = []

            for files in files_pages:
                tree = html.fromstring(files)
                trs = tree.xpath('//*[@id="data_table"]/*[@contenuto_id]')

                for xpath_tr in trs:
                    tds = xpath_tr.xpath('td')
                    files_list.append(File(
                        xpath_tr.xpath('@contenuto_id')[0],
                        xpath_tr.xpath('*/div/@cksum')[0],
                        tds[1].text_content().strip(),
                        path.splitext(tds[3].text_content(
                        ).strip().split('\n')[0].rstrip())[0],
                        tds[5].text_content().strip())
                    )

            return files_list

    class Assignments:
        """assignment parsing class"""

        def __init__(self, cvv):
            self.cvv = cvv
            if not self.cvv.assignments:
                if self.cvv.args.start_month or \
                        self.cvv.args.months or self.cvv.args.tomorrow:
                    self._get_assignments()
                else:
                    raise self.cvv.MissingArgs(
                        "specify at least one of start-month or months")

        def _assignment_request(self, start_date, end_date):
            params = {
                "ope": "get_events"
            }

            data = {
                "classe_id": "",
                "gruppo_id": "",
                "nascondi_av": "0",
                "start": start_date,
                "end": end_date
            }

            assignments = post(self.cvv.endpoint +
                               '/fml/app/default/agenda_studenti.php',
                               params=params,
                               data=data,
                               cookies=self.cvv.cookies,
                               headers=self.cvv.headers)

            if assignments.status_code == 200:
                self.cvv.assignments = self._parse_assignments(
                    assignments.json()
                )

        def _get_assignments(self):
            start_date = int(time())
            if self.cvv.args.start_month:
                start_date = int(datetime(
                    datetime.now().year if datetime.now().month > 8
                    else datetime.now().year-1,
                    self.cvv.args.start_month, 1, 0, 0
                ).timestamp())

            end_date = int(time())
            if self.cvv.args.months:
                end_date += int(timedelta(weeks=self.cvv.args.months *
                                4).total_seconds())
            elif self.cvv.args.tomorrow:
                end_date += int(
                    timedelta(days=1).total_seconds()*2 - datetime.now().hour
                )
            else:
                end_date += int(timedelta(weeks=4).total_seconds())

            self._assignment_request(start_date, end_date)

        @classmethod
        def _parse_assignments(cls, assignments):
            parsed_assignments: Dict[str, Assignment] = {}
            for item in assignments:
                if item["autore_desc"] not in parsed_assignments:
                    parsed_assignments[item["autore_desc"]] = []
                parsed_assignments[item["autore_desc"]].append(Assignment(
                    item["nota_2"],
                    # item["data_inserimento"]
                    item["end"]
                ))
            return parsed_assignments

        def get_assignment(self, index):
            """get assignment"""
            return self.cvv.assignments[index]

        def get_keys(self):
            """get subjects key"""
            return list(self.cvv.assignments.keys())
