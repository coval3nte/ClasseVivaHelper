"""classeviva api"""

from os import path, makedirs
from re import findall
from datetime import datetime, timedelta
from time import time
from typing import Dict
from requests import post, get
from lxml import html
from .data_types import Assignment, File, Grade


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

    def __init__(self, args, mail, password):
        self.endpoint = "https://web.spaggiari.eu"
        self.mail = mail
        self.password = password
        self.args = args
        self.headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:47.0) "
                          "Gecko/20100101 Firefox/47.0"
        }
        self.cookies = {}
        self._login()

        self.assignments = {}

    def _login(self) -> None:
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

        if login.status_code == 200 and "data" in login.json():
            if login.json()["data"]["auth"]["verified"]:
                self.cookies["PHPSESSID"] = login.cookies.get_dict()[
                    "PHPSESSID"]
            else:
                raise self.AuthError(
                    ', '.join(login.json()["data"]["auth"]["errors"]))
        else:
            raise self.AuthError(', '.join(login.json()["error"]))

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

    def get_average(self, index, subject):
        """get average"""
        return self.Grades(self).get_average(index, subject)

    def download_file(self, filename, contenuto_id, cksum):
        """download file"""
        return self.Files(self).download_file(filename, contenuto_id, cksum)

    class Grades:
        """grades parsing class"""
        def __init__(self, cvv):
            self.cvv = cvv
            self.grades = {}
            self.retrieve_grades()

        def _do_grades(self):
            grades = get(self.cvv.endpoint +
                         '/cvv/app/default/genitori_voti.php',
                         cookies=self.cvv.cookies,
                         headers=self.cvv.headers)
            if grades.status_code != 200:
                raise self.cvv.GenericError
            return grades.text

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
                        grades_dict[subject].append(Grade(
                            voto.xpath(
                                'div/p')[0].text_content(),
                            voto.xpath('span')[0].text_content()))
                if len(grades_dict):
                    self.grades[term] = grades_dict

            return self.grades

        def get_grades(self):
            """get grades"""
            return self.grades

        def get_terms_keys(self):
            """get school terms keys"""
            return list(self.grades.keys())

        def get_subject_keys(self, index):
            """get subject keys"""
            return list(self.grades[index].keys())

        def get_average(self, index, subject):
            """get average"""
            bad_words = ['+', '-', '½']
            avg = 0.0
            for grade in self.grades[index][subject]:
                if bad_words[0] in grade.grade:
                    avg += 0.25
                if bad_words[0] in grade.grade:
                    avg -= 0.25
                if bad_words[2] in grade.grade:
                    avg += 0.5
                avg += int(grade.grade.strip().rstrip(''.join(bad_words)))
            return avg / len(self.grades[index][subject])

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
                    datetime.now().year, self.cvv.args.start_month, 1, 0, 0
                ).timestamp())

            end_date = int(time())
            if self.cvv.args.months:
                end_date += int(timedelta(weeks=self.cvv.args.months *
                                4).total_seconds())
            elif self.cvv.args.tomorrow:
                end_date += int(timedelta(days=1).total_seconds())
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
