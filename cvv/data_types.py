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
