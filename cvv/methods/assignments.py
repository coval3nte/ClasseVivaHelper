"""assignments"""
from datetime import datetime, timedelta
from time import time
from typing import Dict
from requests import post
from ..data_types import Assignment


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
                datetime.now().year if self.cvv.args.start_month < 8
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
                item["end"]
            ))
        return parsed_assignments

    def get_assignment(self, index):
        """get assignment"""
        return self.cvv.assignments[index]

    def get_keys(self):
        """get subjects key"""
        return list(self.cvv.assignments.keys())
