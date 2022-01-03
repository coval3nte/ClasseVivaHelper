from dataclasses import dataclass


@dataclass
class File:
    contenuto_id: str
    cksum: str
    teacher: str
    filename: str
    date: str


@dataclass
class Assignment:
    desc: str
    date: str


@dataclass
class Grade:
    grade: str
    date: str
