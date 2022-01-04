"""classeviva main"""
from argparse import ArgumentParser
from asyncio import get_event_loop
from sys import exit as sexit
from colorama import Fore
from .classeviva_api import CVV
from .creds import Creds

(mail, password, session) = (val[1] for val in Creds().get_creds())


def display_indexes(keys):
    """arrays indexes"""
    output = []
    for idx in enumerate(keys):
        output.append(f"{idx[0]}: {idx[1]}")
    return output


def get_grades(cvv, keys):
    """parse grades API"""
    terms = input("Term (index): ").rstrip().split(",")
    for term in terms:
        subjects = cvv.get_grades()[keys[int(term)]]
        for subject in subjects:
            avg = cvv.get_average(keys[int(term)], subject)
            print(
                f"{Fore.RED}{subject} - {Fore.GREEN if avg > 6.0 else ''}"
                f"{avg}{Fore.RESET}"
            )
            print(
                *(f"{Fore.RESET}{grade.date}: "
                  f"{Fore.BLUE}{grade.grade}{Fore.RESET}"
                  for grade in subjects[subject]),
                sep='\n'
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


def main():
    """main function"""
    parser = ArgumentParser(description="CVV")
    parser.add_argument("--assignment", "-a",
                        help="get school assignments", action='store_true')
    parser.add_argument("--files", "-f",
                        help="download teacher files", action='store_true')
    parser.add_argument("--grades", "-g",
                        help="get school grades", action='store_true')
    parser.add_argument("--download-all", "-d",
                        help="download ALL teacher files", action='store_true')
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
    elif not (args.files or args.assignment or args.grades):
        parser.error("Choose at least one action between files, assignments"
                     ", grades!")

    cvv = CVV(args, mail, password, session)

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

    while True:
        try:
            if args.assignment:
                get_assignment(cvv, keys)
            elif args.grades:
                get_grades(cvv, keys)
            elif args.files:
                get_files(args, cvv, files, loop)
        except KeyboardInterrupt:
            print('bye...')
            sexit()
        except (ValueError, IndexError):
            pass


if __name__ == '__main__':
    main()
