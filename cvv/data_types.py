"""module datatypes"""
from dataclasses import dataclass


@dataclass
class File:
    """file datatype"""
    contenuto_id: str
    cksum: str
    teacher: str
    filename: str
    date: str


@dataclass
class Assignment:
    """assignment datatype"""
    desc: str
    date: str


@dataclass
class Grade:
    """grade datatype"""
    grade: str
    date: str


@dataclass
class Lesson:
    """lesson datatype"""
    teacher_name: str
    teacher_subject: str
    hour: str
    topic: str


@dataclass
class Absence:
    """Absence datatype"""
    absence: str
    data_start: str
    data_stop: str
    anno_scol: str
