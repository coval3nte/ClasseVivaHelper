"""classeviva main"""
from argparse import ArgumentParser
from asyncio import get_event_loop
from sys import exit as sexit
from os import get_terminal_size
from datetime import datetime, timedelta
from matplotlib import pyplot as plt
from matplotlib import dates as mdates
import mplcursors
import numpy as np
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


def filter_dates(dates):
    """filter near dates"""
    j = 0
    while j < len(dates):
        date = dates[j]
        i = 3
        j += 1
        while True:
            date += timedelta(days=1)
            if date in dates:
                i += 1
            else:
                if i > 2:
                    del dates[j:j+i-1]
                break
    return dates


def graph_grades(cvv, keys):
    """generate a dates graph"""
    terms = input("Term (index): ").rstrip().split(",")
    ax_plt = plt.gca()
    ax_plt.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m/%Y"))
    ax_plt.xaxis.set_major_locator(mdates.DayLocator())

    grades = {}
    for term in terms:
        subjects = cvv.get_grades()[keys[int(term)]]
        ax_plt.set_prop_cycle(
            color=[plt.get_cmap('Paired')(1.*i/(len(subjects)+1)
                                          ) for i in range(
                (len(subjects)+1))])
        for subject in subjects:
            subject_grades, subject_dates = [], []
            for grade in subjects[subject]:
                date = datetime.strptime(grade.date, "%d/%m/%Y").date()
                subject_grades.append(cvv.sanitize_grade(grade.grade))
                subject_dates.append(date)

                if date not in grades:
                    grades[date] = []
                grades[date].append(
                    cvv.sanitize_grade(grade.grade)
                )

            plt.plot(subject_dates, subject_grades, marker='o', label=subject)

        if len(list(grades.values())) > 0:
            averages_y = [list(dict(sorted(grades.items())).values())[0][0]]
            for count, _ in enumerate(grades):
                if len(list(grades.values())[:count]) > 0:
                    averages_y.append(np.average(
                        sum(list(dict(sorted(grades.items())).values()
                                 )[:count],
                            [])))

            plt.plot(dict(sorted(grades.items())).keys(),
                     averages_y, marker='o', label="mean", linestyle='dashed')
            ax_plt.set_xticks(filter_dates((sorted(list(grades.keys())))))
            ax_plt.tick_params(axis='x', rotation=45, which='major')
            ax_plt.legend()
            mplcursors.cursor(hover=True)
            plt.title("Grades Plot")
            plt.xlabel("Time")
            plt.ylabel("Grade")
    plt.show()


def get_grades(cvv, keys, total):
    """parse grades API"""
    terms = input("Term (index): ").rstrip().split(",")
    avgs = {}
    general_mean = [cvv.get_average(keys[int(term)]) for term in terms]
    for term in terms:
        general_trend = cvv.get_average(keys[int(term)])
        not_sufficient, min_grade = [], []
        subjects = cvv.get_grades()[keys[int(term)]]
        print(f"{Fore.MAGENTA}Trend - {term} - {general_trend}"
              f"{text_trend(general_trend > SUFFICIENCY)}{Fore.RESET}"
              )
        for subject in subjects:
            avg = cvv.get_subject_average(keys[int(term)], subject)

            if total:
                if subject not in avgs:
                    avgs[subject] = []
                avgs[subject].append(avg)
                continue

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
    if total:
        print(f"{Fore.MAGENTA}General Trend - ",
              sum(general_mean)/len(general_mean),
              f"{text_trend(general_trend > SUFFICIENCY)}{Fore.RESET}"
              )
        for subject in avgs:
            avg = sum(avgs[subject])/len(avgs[subject])
            print(
                f"{Fore.RED}{subject}"
                f"{Fore.GREEN + ' - ' if avg > 6.0 else ' - '}"
                f"{avg}{Fore.RESET}"
            )


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


def cli(args, cvv):
    """cli functions"""
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
    elif args.check_bacheca:
        cvv.check_bacheca()

    while True:
        try:
            if args.assignment:
                get_assignment(cvv, keys)
            elif args.grades:
                if args.grades_chart:
                    graph_grades(cvv, keys)
                else:
                    get_grades(cvv, keys, args.total_mean)
            elif args.files:
                get_files(args, cvv, files, loop)
            elif args.absences:
                justify_absences(cvv, absences)
            else:
                sexit()
        except KeyboardInterrupt:
            print('bye...')
            sexit()
        except (ValueError, IndexError):
            pass


def main():
    """main function"""
    parser = ArgumentParser(description="CVV")
    parser.add_argument("--grades", "-g",
                        help="get school grades", action='store_true')
    parser.add_argument("--grades-chart", "-gm",
                        help="show grades chart", action='store_true')
    parser.add_argument("--total-mean", "-tm",
                        help="get total mean", action='store_true')
    parser.add_argument("--lessons", "-l",
                        help="see what teacher explained today",
                        action='store_true')
    parser.add_argument("--lessons-date", '-ld',
                        help="date format: 2022-01-14", type=str,
                        default='')
    parser.add_argument("--absences", "-abs",
                        help="see your absences",
                        action='store_true')
    parser.add_argument("--absence-justify", "-absj",
                        help="justify absences",
                        action='store_true')
    parser.add_argument("--files", "-f",
                        help="download teacher files", action='store_true')
    parser.add_argument("--save-folder", "-save",
                        help="folder to download file ", type=str,
                        default='files')
    parser.add_argument("--download-all", "-d",
                        help="download ALL teacher files", action='store_true')
    parser.add_argument("--assignment", "-a",
                        help="get school assignments", action='store_true')
    parser.add_argument('--start-month', "-s",
                        help="get assignment from (month)", type=int)
    parser.add_argument('--months', "-m",
                        help="get upcoming assignment to (month)", type=int)
    parser.add_argument('--tomorrow', "-t",
                        help="get upcoming assignment for tomorrow",
                        action='store_true')
    parser.add_argument("--check-bacheca", "-cb",
                        help="check new documents", action='store_true')

    args = parser.parse_args()
    if not any(vars(args).values()):
        parser.error('No arguments provided.')
    elif not (args.files or args.assignment or args.grades or
              args.lessons or args.absences or args.check_bacheca):
        parser.error("Choose at least one action between files, assignments"
                     ", grades, check bacheca!")

    cvv = CVV(args=args, mail=mail, password=password, session=session)
    cli(args, cvv)


if __name__ == '__main__':
    main()
