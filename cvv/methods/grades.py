"""grades"""
from datetime import datetime
import numpy as np
from requests import get
from lxml import html
from ..data_types import Grade


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
        """sanitize grade"""
        bad_words = ['+', '-', '½']
        irc = {
            'o': 10,
            'd': 8,
            'b': 7,
            's': 6,
            'ns': 5
        }

        if grade in irc:
            return irc[grade]

        grade_new = int(grade.strip().rstrip(''.join(bad_words)))
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
