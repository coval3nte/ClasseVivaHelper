from lxml import html
from re import findall
from os import path, makedirs
from requests import post, get
from datetime import datetime, timedelta
from time import time
from typing import List, Dict
from data_types import Assignment, File, Grade


class CVV(object):
    class AuthError(Exception):
        def __init__(self, message):
            super().__init__(message)

    class GenericError(Exception):
        def __init__(self):
            super().__init__("something went wrong while communicating with CVV API's")

    class MissingArgs(Exception):
        def __init__(self, message):
            super().__init__(message)

    def __init__(self, args, mail, password):
        self.mail = mail
        self.password = password
        self.args = args
        self._headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:47.0) Gecko/20100101 Firefox/47.0"
        }
        self._cookies = {}
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

        login = post('https://web.spaggiari.eu/auth-p7/app/default/AuthApi4.php',
                     params=params,
                     data=data,
                     headers=self._headers)

        if login.status_code == 200 and "data" in login.json():
            if login.json()["data"]["auth"]["verified"]:
                self._cookies["PHPSESSID"] = login.cookies.get_dict()[
                    "PHPSESSID"]
            else:
                raise self.AuthError(
                    ', '.join(login.json()["data"]["auth"]["errors"]))
        else:
            raise self.AuthError(', '.join(login.json()["error"]))

    def get_assignment(self, index):
        return self.Assignments(self).get_assignment(index)

    def get_assignments_keys(self):
        return self.Assignments(self).get_keys()

    def get_files(self):
        return list(reversed(self.Files(self).retrieve_files()))

    def get_grades(self):
        return self.Grades(self).get_grades()

    def get_terms_keys(self):
        return self.Grades(self).get_terms_keys()

    def get_subject_keys(self, index):
        return self.Grades(self).get_subject_keys(index)

    def get_average(self, index, subject):
        return self.Grades(self).get_average(index, subject)

    def download_file(self, filename, contenuto_id, cksum):
        return self.Files(self).download_file(filename, contenuto_id, cksum)

    class Grades(object):
        def __init__(self, cvv):
            self.cvv = cvv
            self.grades = {}
            self.retrieve_grades()

        def _do_grades(self):
            grades = get('https://web.spaggiari.eu/cvv/app/default/genitori_voti.php',
                         cookies=self.cvv._cookies,
                         headers=self.cvv._headers)
            if grades.status_code != 200:
                raise self.GenericError
            return grades.text

        def retrieve_grades(self):
            tree = html.fromstring(self._do_grades())
            school_terms = tree.xpath('//*[@class="outer"]/@id')

            for term in school_terms:
                grades_dict = {}
                trs = tree.xpath(
                    f"//*[@id=\"{term}\"]//table[@sessione=\"{term}\"]//tr[contains(@sessione, \"{term}\") and contains(@class, \"riga_materia_componente\")]")
                for tr in trs:
                    subject = tr.xpath(
                        'td')[0].text_content().strip().capitalize()
                    grades_dict[subject] = []

                    voti = tr.xpath(
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
            return self.grades

        def get_terms_keys(self):
            return list(self.grades.keys())

        def get_subject_keys(self, index):
            return list(self.grades[index].keys())

        def get_average(self, index, subject):
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

    class Files(object):
        def __init__(self, cvv):
            self.cvv = cvv

        def _do_files(self, params):
            files = get('https://web.spaggiari.eu/fml/app/default/didattica_genitori_new.php',
                        params=params,
                        cookies=self.cvv._cookies,
                        headers=self.cvv._headers)

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
            params = {
                'a': 'downloadContenuto',
                'contenuto_id': contenuto_id,
                'cksum': cksum
            }
            resp = get('https://web.spaggiari.eu/fml/app/default/didattica_genitori.php',
                       params=params,
                       cookies=self.cvv._cookies,
                       headers=self.cvv._headers)
            if resp.status_code != 200:
                raise self.cvv.GenericError

            if not path.exists("files"):
                makedirs("files")
            with open("files/"+filename+'.'+findall("filename=(.+)", resp.headers['content-disposition'])[0].split('.')[-1], 'wb') as f:
                f.write(resp.content)

        def retrieve_files(self):
            files_pages = self._do_pages()
            files_list = []

            for files in files_pages:
                tree = html.fromstring(files)
                trs = tree.xpath('//*[@id="data_table"]/*[@contenuto_id]')

                for tr in trs:
                    tds = tr.xpath('td')
                    files_list.append(File(
                        tr.xpath('@contenuto_id')[0],
                        tr.xpath('*/div/@cksum')[0],
                        tds[1].text_content().strip(),
                        path.splitext(tds[3].text_content(
                        ).strip().split('\n')[0].rstrip())[0],
                        tds[5].text_content().strip())
                    )

            return files_list

    class Assignments(object):
        def __init__(self, cvv):
            self.cvv = cvv
            if self.cvv.args.start_month or self.cvv.args.months or self.cvv.args.tomorrow:
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

            assignments = post('https://web.spaggiari.eu/fml/app/default/agenda_studenti.php',
                               params=params,
                               data=data,
                               cookies=self.cvv._cookies,
                               headers=self.cvv._headers)

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

        def _parse_assignments(self, assignments) -> Dict[str, List[str]]:
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
            return self.cvv.assignments[index]

        def get_keys(self):
            return list(self.cvv.assignments.keys())