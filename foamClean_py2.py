# -*- coding: UTF-8 -*-
import os
import re
import argparse
import shutil
import sys


def readOptions(args):
    parser = argparse.ArgumentParser(description="Decomposed openFOAM case cleaner utility.")

    subparsers = parser.add_subparsers(dest="command", help='Get subcommand help form more information', required=True)

    # Timesteps subcommand parser
    p_ts = subparsers.add_parser('timesteps', help='Cleans specified timesteps by removing specified timesteps')
    exgr_ts = p_ts.add_mutually_exclusive_group()
    exgr_ts.add_argument("--time", nargs="+", type=float, help="Inclusive start and exclusive end times to remove. "
                                                               "Second timestep can be omitted to include last "
                                                               "timestep")
    exgr_ts.add_argument("--index", nargs="+", type=int, help="Inclusive start and exclusive end timestep indices to "
                                                              "remove. Second index can be omitted to include last "
                                                              "timestep.")
    exgr_ts.add_argument("--timeList", nargs="+", type=float, help="List of times to remove")
    exgr_ts.add_argument("--indexList", nargs="+", type=int, help="List of indices to remove")
    # exgr_ts.add_argument("--regex", nargs="+", type=str, help="List of regex expressions to remove")
    p_ts.add_argument("--path", type=str, help="Relative path to the case directory.")
    p_ts.add_argument("--sim", action="store_true", help="Simulates deletion process")
    p_ts.add_argument("--force", action="store_true", help="Skips user confirmation.")
    # p_ts.add_argument("--copy", type=str, help="Copies to a specified location instead of removal.")
    p_ts.set_defaults(which='timesteps')

    # Fields
    p_f = subparsers.add_parser('fields', help='Removes all fields except for ones specified from all timesteps '
                                               'except zero and last')
    # exgr_f = p_ts.add_mutually_exclusive_group()
    p_f.add_argument("fields", nargs="+", type=str,
                     help="List of field names to be kept")
    # exgr_f.add_argument("--regex", nargs="+", type=str,
    #                        help="List of regular expressions to match field names")
    p_f.add_argument("--removeLast", action="store_true", help="Also deletes the last time step.")
    p_f.add_argument("--removeZero", action="store_true", help="Also deletes zero timestep.")
    p_f.add_argument("--path", type=str, help="Path to the case directory.")
    p_f.add_argument("--sim", action="store_true", help="Simulates deletion process.")
    p_f.add_argument("--force", action="store_true", help="Skips user confirmation.")
    # p_f.add_argument("--copy", type=str, help="Copies to a specified location instead of removal.")
    p_f.set_defaults(which='fields')

    opts = parser.parse_args(args)
    return opts


class TDir:
    def __init__(self, name, time):
        self.name = name
        self.time = time


def confirmDelete(opts):
    """
    Prompts user to confirm an action.

    :param opts: Options parsed from command line arguments
    :return: True if user confirms, False otherwise.
    """
    if opts.force:
        return True

    answer = str(raw_input("Do you wish to continue? "))

    if answer == "y" or answer == "yes":
        return True
    elif answer == "n" or answer == "no":
        return False
    else:
        return False


# Print iterations progress
def printProgressBar(iteration, total, prefix='', suffix='', decimals=1, length=100, fill='█', printEnd="\r"):
    """
    Call in a loop to create terminal progress bar.
    Credit https://stackoverflow.com/questions/3173320/text-progress-bar-in-the-console.

    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : positive number of decimals in percent complete (Int)
        length      - Optional  : character length of bar (Int)
        fill        - Optional  : bar fill character (Str)
        printEnd    - Optional  : end character (e.g. "\r", "\r\n") (Str)
    """
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + '-' * (length - filledLength)
    print '\r%s |%s| %s%% %s\r' % (prefix, bar, percent, suffix),
    # Print New Line on Complete
    if iteration == total:
        print()


def getProcessors(case_path):
    """
    Gets names of all processor folders within a given case folder.

    :param case_path: Path to the openFOAM case.
    :return: Sorted list of processor folder names
    """
    print("Case path: " + str(case_path))

    try:
        filenames = os.listdir(case_path)
    except OSError as err:
        print(err)
        return []

    p = re.compile('processor\d+')
    proc_dirs = [name for name in filenames if p.match(name)]
    proc_dirs.sort()
    print("Found " + str(len(proc_dirs)) + " processor folders.")
    return proc_dirs


def _getTimeList(proc_path):
    """
    Helper function. Returns a sorted list of all timestep folder names within a given processor path

    :param proc_path: Path to the processorN within openFOAM case.
    :return: Sorted list of all timesteps
    """
    time_dirs = []
    try:
        filenames = os.listdir(proc_path)
    except OSError as err:
        print(err)
        return time_dirs

    for name in filenames:

        # Skip files, we are only interested in folders
        if os.path.isfile(os.path.join(proc_path, name)):
            continue

        try:
            # Skip folders which names are not cannot be parsed as a float
            time_dirs.append(TDir(name, float(name)))
        except ValueError as err:
            continue

    if time_dirs:
        # Sort timestep directories
        time_dirs.sort(key=lambda x: x.time)

    return time_dirs


def getTimes(proc_path, opts):
    """
    Gets a sorted list of timestep folder names to be removed, kept and list of 0 and -1 timesteps used to figure out
                        which fields will be deleted.

    :param proc_path: Path to the processor directory within openFOAM case.
    :param opts: Options parsed from command line arguments
    :return: Sorted list of timestep folder names to be removed, kept, zero and last timesteps used to figure out
                        which fields will be deleted.
    """
    time_dirs = _getTimeList(proc_path)
    time_dirs_rm = []
    time_dirs_keep = []
    time_zero = ""
    time_last = ""

    # If there are not timestep directories there is nothing to do
    if time_dirs:

        # If we are in timestep clean up mode
        if opts.which == "timesteps":
            # If we are removing timesteps within specified range of times
            if opts.time:
                # If there are more then 2 times, ignore the rest
                if len(opts.time) >= 2:
                    time_dirs_rm = [td for td in time_dirs if opts.time[0] <= td.time < opts.time[1]]
                # If there is a single time specified
                else:
                    time_dirs_rm = [td for td in time_dirs if opts.time[0] <= td.time]
            # If we are removing timesteps within specified range of indices
            elif opts.index:
                # If there are more then 2 indices, ignore the rest
                if len(opts.index) >= 2:
                    time_dirs_rm = time_dirs[opts.index[0]:opts.index[1]]
                # If there is a single index specified
                else:
                    time_dirs_rm = time_dirs[opts.index[0]:]
            # If we are removing timesteps based on a list of times
            elif opts.timeList:
                # Strip only times from Dir objects
                time_dirs_times = [td.time for td in time_dirs]
                ind_remove = []

                # Essentially converting a list of times into a list of indices
                for timeEntry in opts.timeList:
                    try:
                        ind_remove.append(time_dirs_times.index(timeEntry))
                    except ValueError:
                        continue

                # Sort list of indices in descending order so they con be removed from the list
                ind_remove.sort(reverse=True)
                for ind in ind_remove:
                    time_dirs_rm.append(time_dirs[ind])
            # If we are removing timesteps based on a list of indices
            elif opts.indexList:
                # Sort list of indices in descending order so they con be removed from the list
                opts.indexList.sort(reverse=True)
                for ind in opts.indexList:
                    try:
                        time_dirs_rm.append(time_dirs[ind])
                    except IndexError:
                        continue

            time_dirs_rm = set(time_dirs_rm)
            time_dirs_keep = list(set(time_dirs) - time_dirs_rm)
            time_dirs_rm = list(time_dirs_rm)

        if opts.which == "fields":
            time_zero = time_dirs[0].name
            time_last = time_dirs[-1].name

            # Keeping timestep 0 unaffected, unless --removeZero specified.
            # Also check that the first time step is 0
            if time_dirs[0].time == 0:
                if not opts.removeZero:
                    time_dirs_keep.append(time_dirs[0])

            # Keeping last timestep unaffected, unless --removeLast specified.
            # Also check that the last time step is not 0
            if (not opts.removeLast) and (time_dirs[-1].time != 0):
                time_dirs_keep.append(time_dirs[-1])

            time_dirs_keep = set(time_dirs_keep)
            time_dirs_rm = list(set(time_dirs) - time_dirs_keep)
            time_dirs_keep = list(time_dirs_keep)

        time_dirs_rm.sort(key=lambda x: x.time)
        time_dirs_keep.sort(key=lambda x: x.time)

        time_dirs_rm = [time_dir.name for time_dir in time_dirs_rm]
        time_dirs_keep = [time_dir.name for time_dir in time_dirs_keep]

    print(" ---- Timesteps ---- ")
    if opts.which == "fields":
        print("Unaffected: " + str(time_dirs_keep))
        print("Affected: " + str(time_dirs_rm))
        return time_dirs_rm, time_zero, time_last
    else:
        print("Keep: " + str(time_dirs_keep))
        print("Remove: " + str(time_dirs_rm))
        return time_dirs_rm


def _getFieldList(time_path):
    """
    Gets a list of sorted fields from the timestep path. It also indicates whether fields are compressed.

    :param time_path: Path to a timestep folder
    :return: Sorted list of sorted fields from the timestep path and whether files are compressed or not.
    """
    fields = []
    try:
        filenames = os.listdir(time_path)
    except OSError as err:
        print(err)
        return fields

    for name in filenames:

        # Skip folders
        if os.path.isdir(os.path.join(time_path, name)):
            continue
        else:
            fields.append(name)

    compressed = False
    if fields:
        fields.sort()
        if fields[0].endswith(".gz"):
            compressed = True

    return compressed, fields


def getFields(time_path_zero, time_path_last, opts):
    """
    Convenient wrapper around _getFieldList()

    :param time_path_zero: Zero timestep path used to figure out which timesteps to keep
    :param time_path_last: Last timestep path used to figure out which timesteps to keep
    :param opts: Options parsed from command line arguments
    :return: Sorted list of fields to be removed
    """
    compressed_zero, fields_zero = _getFieldList(time_path_zero)
    compressed_last, fields_last = _getFieldList(time_path_last)

    if compressed_zero or compressed_last:
        opts.fields = [field + ".gz" for field in opts.fields]

    fields = fields_zero + fields_last
    fields = list(set(fields))

    fields_rm = []
    fields_keep = []
    for field in fields:
        if field in opts.fields:
            fields_keep.append(field)
        else:
            fields_rm.append(field)

    fields_rm.sort()
    fields_keep.sort()

    print(" ---- Fields ---- ")
    print("Keep: " + str(fields_keep))
    print("Remove: " + str(fields_rm))

    return fields_rm


def cleanTimesteps(opts):
    """


    :param opts: Options parsed from command line arguments
    :return: True if operation was successful, False otherwise.
    """
    # If path parameter is not specified assume current directory
    if opts.path:
        case_path = opts.path
    else:
        case_path = "."

    # Get processorN directories
    proc_dirs = getProcessors(case_path)

    # Check to make sure they are not empty
    if not proc_dirs:
        print("Nothing to do...")
        return True

    # Get timestep directories from processorN. I am assuming that all the cases have the same
    # timesteps. Otherwise your case if damaged. Using last processor step helps in cases where deletion process got
    # interrupted.
    time_dirs_rm = getTimes(os.path.join(case_path, proc_dirs[-1]), opts)

    if not time_dirs_rm:
        print("Nothing to do...")
        return True

    if not confirmDelete(opts):
        print("Aborting...")
        return True

    if not opts.sim:
        N = len(proc_dirs) * len(time_dirs_rm)
        printProgressBar(0, N, prefix='Progress:', suffix='Complete', length=50)
        i = 0

    for proc_dir in proc_dirs:
        for time_dir in time_dirs_rm:
            final_path = os.path.join(case_path, proc_dir, time_dir)
            if opts.sim:
                print("Removing " + str(final_path))
            else:
                shutil.rmtree(final_path, ignore_errors=True)
                printProgressBar(i + 1, N, prefix='Progress:', suffix='Complete', length=50)
                i += 1

    return True


def cleanFields(opts):
    """
    Removes all fields not specified in opts.fields from all processor directories.
    By default is keeps 0th and last timesteps unaffected. This can be overridden with --removeZero --removeLast.

    :param opts: Options parsed from command line arguments
    :return: True if operation was successful, False otherwise.
    """
    # If path parameter is not specified assume current directory
    if opts.path:
        case_path = opts.path
    else:
        case_path = "."

    # Get processorN directories
    proc_dirs = getProcessors(case_path)

    # Check to make sure they are not empty
    if not proc_dirs:
        print("Nothing to do...")
        return True

    # Get timestep directories from processorN. I am assuming that all the cases have the same
    # timesteps. Otherwise your case if damaged. Using last processor step helps in cases where deletion process got
    # interrupted.
    time_dirs_rm, time_zero, time_last = getTimes(os.path.join(case_path, proc_dirs[-1]), opts)

    if not time_dirs_rm:
        print("Nothing to do...")
        return True

    # Get fields to be removed from processo0/timestep. There are a couple of options:
    # 1) If --removeLast is selected then 0 is 1st timestep and -1 is last timestep
    # 2) If --removeZero is selected then 0 is 0th timestep and -1 is second to last timestep
    # 3) If both keys present, then 0 is 0th timestep and -1 is the last timestep
    # 4) If non are selected (default), then 0 is 1st timestep and -1 is the second to last timestep
    # Either way, the set of unique fields from 0 and -1 is the most number of fields any timestep can have.
    fields = getFields(os.path.join(case_path, proc_dirs[0], time_zero),
                       os.path.join(case_path, proc_dirs[0], time_last), opts)

    if not fields:
        print("Nothing to do.")
        return True

    if not confirmDelete(opts):
        print("Aborting...")
        return True

    # Show progress bar if we are not in simulation mode
    if not opts.sim:
        N = len(proc_dirs) * len(time_dirs_rm)
        printProgressBar(0, N, prefix='Progress:', suffix='Complete', length=50)
        i = 0

    for proc_dir in proc_dirs:
        for time_dir in time_dirs_rm:

            path = os.path.join(case_path, proc_dir, time_dir)
            for field in fields:
                final_path = os.path.join(path, field)

                # Print file path if in simulation mode. Remove otherwise
                if opts.sim:
                    print("Removing " + str(final_path))
                else:
                    try:
                        os.remove(final_path)
                    except OSError as err:
                        continue

            # Show progress bar if we are not in simulation mode
            if not opts.sim:
                printProgressBar(i + 1, N, prefix='Progress:', suffix='Complete', length=50)
                i += 1

    return True


if __name__ == '__main__':
    try:
        opts = readOptions(sys.argv[1:])
    except Exception as err:
        print(err)
        exit()

    print("\n")
    if opts.which == 'timesteps':
        print("Entering timestep clean up mode...")
        if cleanTimesteps(opts):
            print("Success!")
        else:
            print("Something went wrong")
    elif opts.which == 'fields':
        print("Entering field clean up mode...")
        if cleanFields(opts):
            print("Success!")
        else:
            print("Something went wrong")
    else:
        print("Wrong cleaning mode '" + str(opts.which) + "'")

    print("Exiting...")
    print("\n")
