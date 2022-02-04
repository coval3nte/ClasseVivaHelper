"""lesson"""
from datetime import datetime
from requests import get
from lxml import html
from ..data_types import Lesson


class Lessons:
    """lesson parsing class"""

    def __init__(self, cvv, start_date=''):
        self.cvv = cvv
        self.start_date = start_date or datetime.now().strftime("%Y-%m-%d")

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
        """retrieve lessons"""
        tree = html.fromstring(self._do_lessons())
        trs = tree.xpath('(//table[@id="data_table"])[2]/tr')
        subjects = []
        for tr_xpath in trs:
            teacher_name = ''.join(tr_xpath.xpath(
                'td[@class="registro_firma_dett_docente"]//text()')
            ).strip()
            teacher_subject = ''.join(tr_xpath.xpath(
                'td[@class="registro_firma_dett_materia"]//text()')
            ).replace('\n', ' ').strip()
            hour = ''.join(
                tr_xpath.xpath(
                    'td[@class="registro_firma_dett_ora"]//text()')
            ).strip()
            topic = ''.join(
                tr_xpath.xpath(
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
        """get lessons"""
        return self.retrieve_lessons()
