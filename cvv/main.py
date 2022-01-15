"""classeviva main"""
from argparse import ArgumentParser
from asyncio import get_event_loop
from sys import exit as sexit
from os import get_terminal_size
from colorama import Fore
from .classeviva_api import CVV
from .creds import Creds

SUFFICIENCY = 6
MIN_GRADE = 2
(mail, password, session) = (val[1] for val in Creds().get_creds())


def divisor():
    """terminal divisor"""
    return '-'*get_terminal_size()[0] + '\n'


def display_indexes(keys):
    """arrays indexes"""
    output = []
    for idx in enumerate(keys):
        output.append(f"{idx[0]}: {idx[1]}")
    return output


def text_trend(trend):
    """text trend"""
    if not isinstance(trend, bool):
        return ''
    if trend:
        return ' - 📈'

    return ' - 📉'


def get_grades(cvv, keys):
    """parse grades API"""
    terms = input("Term (index): ").rstrip().split(",")
    for term in terms:
        general_trend = cvv.get_average(keys[int(term)])
        not_sufficient, min_grade = [], []
        subjects = cvv.get_grades()[keys[int(term)]]
        print(f"{Fore.MAGENTA}General Trend - {general_trend}"
              f"{text_trend(general_trend > SUFFICIENCY)}{Fore.RESET}"
              )
        for subject in subjects:
            avg = cvv.get_subject_average(keys[int(term)], subject)
            trend = text_trend(cvv.get_trend(keys[int(term)], subject))

            if avg < SUFFICIENCY:
                not_sufficient.append(subject)
            if len(subjects[subject]) < MIN_GRADE:
                min_grade.append(subject)

            print(
                f"{Fore.RED}{subject}"
                f"{Fore.GREEN + ' - ' if avg > 6.0 else ' - '}"
                f"{avg}{trend}{Fore.RESET}"
            )
            print(
                *(f"{Fore.RESET}{grade.date}: "
                  f"{Fore.BLUE}{grade.grade}{Fore.RESET}"
                  for grade in subjects[subject]),
                sep='\n'
            )

        if not_sufficient:
            print(divisor() +
                  f"Gaps in:\n- {Fore.RED}" +
                  f'\n{Fore.RESET}-{Fore.RED} '.join(not_sufficient) +
                  Fore.RESET)
        if min_grade:
            print(divisor() +
                  f"Few grades in:\n- {Fore.RED}" +
                  f'\n{Fore.RESET}-{Fore.RED} '.join(min_grade) +
                  Fore.RESET)


def get_files(args, cvv, files, loop):
    """parse files API"""
    if args.download_all:
        input_files = range(len(files))
    else:
        input_files = input("File (index): ").rstrip().split(",")

    for input_file in input_files:
        print(
            f"{Fore.RED}downloading{Fore.RESET} → "
            f"{args.save_folder}/{files[int(input_file)].filename}..."
        )
        loop.run_in_executor(None, cvv.download_file,
                             files[int(input_file)].filename,
                             files[int(input_file)].contenuto_id,
                             files[int(input_file)].cksum)

    if args.download_all:
        sexit()


def get_assignment(cvv, keys):
    """parse assignment API"""
    subjects = input("Subject (index): ").rstrip().split(",")
    for subject in subjects:
        subject_name = keys[int(subject)]
        assignments = cvv.get_assignment(subject_name)
        print(
            f"{Fore.RED}{subject_name}{Fore.RESET}"
        )
        print(
            *(f"{Fore.RESET}{assignment.date.split(' ')[0]}: "
              f"{Fore.GREEN}{assignment.desc}{Fore.RESET}"
              for assignment in assignments),
            sep='\n'
        )


def justify_absences(cvv, absences):
    """justify absences"""
    absences_input = input("Absence (index): ").rstrip().split(",")
    reason = input("Reason: ").rstrip()
    for absence in absences_input:
        if cvv.justify_absence(int(absence), reason):
            print(f"{Fore.MAGENTA}Absence{Fore.RESET}:"
                  f" {absence} {Fore.GREEN}Successfully Justified{Fore.RESET}"
                  )
        else:
            print("{Fore.MAGENTA}Something went wrong while justifying"
                  f"{Fore.RESET}:"
                  f" {absences[absence].absence}")


def main():
    """main function"""
    parser = ArgumentParser(description="CVV")
    parser.add_argument("--assignment", "-a",
                        help="get school assignments", action='store_true')
    parser.add_argument("--files", "-f",
                        help="download teacher files", action='store_true')
    parser.add_argument("--grades", "-g",
                        help="get school grades", action='store_true')
    parser.add_argument("--lessons", "-l",
                        help="see what teacher explained today",
                        action='store_true')
    parser.add_argument("--absences", "-abs",
                        help="see your absences",
                        action='store_true')
    parser.add_argument("--absence-justify", "-absj",
                        help="justify absences",
                        action='store_true')
    parser.add_argument("--download-all", "-d",
                        help="download ALL teacher files", action='store_true')
    parser.add_argument("--lessons-date", '-ld',
                        help="date format: 2022-01-14", type=str,
                        default='')
    parser.add_argument("--save-folder", "-save",
                        help="folder to download file ", type=str,
                        default='files')
    parser.add_argument('--start-month', "-s",
                        help="get assignment from (month)", type=int)
    parser.add_argument('--months', "-m",
                        help="get upcoming assignment to (month)", type=int)
    parser.add_argument('--tomorrow', "-t",
                        help="get upcoming assignment for tomorrow",
                        action='store_true')

    args = parser.parse_args()
    if not any(vars(args).values()):
        parser.error('No arguments provided.')
    elif not (args.files or args.assignment or args.grades or
              args.lessons or args.absences):
        parser.error("Choose at least one action between files, assignments"
                     ", grades!")

    cvv = CVV(args=args, mail=mail, password=password, session=session)

    if args.assignment:
        keys = cvv.get_assignments_keys()
        print('\n'.join(display_indexes(keys)))
    elif args.grades:
        keys = cvv.get_terms_keys()
        print('\n'.join(display_indexes(keys)))
    elif args.files:
        loop = get_event_loop()
        files = cvv.get_files()
        for idx in enumerate(files):
            print(
                f"{idx[0]}: {idx[1].date} {idx[1].teacher} "
                f"{Fore.GREEN}{idx[1].filename}{Fore.RESET}"
            )
    elif args.lessons:
        lessons = cvv.get_lessons(start_date=args.lessons_date)
        for lesson in lessons:
            print(
                f"{Fore.GREEN}{lesson.hour.split(' ')[0]} {Fore.RED}"
                f"{lesson.teacher_name}"
                f"{Fore.RESET}"
                f":{Fore.GREEN}"
                f"{lesson.teacher_subject.split('(')[:-1][0].strip()}"
                f"{Fore.RESET}",
                (f" → {Fore.BLUE}{lesson.topic}{Fore.RESET}" if
                 lesson.topic else "")
            )
        sexit()
    elif args.absences:
        absences = cvv.get_absences()
        for absence in enumerate(absences):
            print(f"{absence[0]}: {Fore.RED}{absence[1].absence}{Fore.RESET}")
        if not args.absence_justify:
            sexit()

    while True:
        try:
            if args.assignment:
                get_assignment(cvv, keys)
            elif args.grades:
                get_grades(cvv, keys)
            elif args.files:
                get_files(args, cvv, files, loop)
            elif args.absences:
                justify_absences(cvv, absences)
        except KeyboardInterrupt:
            print('bye...')
            sexit()
        except (ValueError, IndexError):
            pass


if __name__ == '__main__':
    main()
