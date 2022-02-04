"""absence"""
from requests import get, post
from lxml import html
from ..data_types import Absence


class Absences:
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
        """retrieve absences"""
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
        """justify absence"""
        return self._justify_absence(index, reason)

    def get_absences(self):
        """get absence"""
        return self.cvv.absences
