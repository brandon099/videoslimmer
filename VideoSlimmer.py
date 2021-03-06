import argparse
import json
import logging
import logging.handlers
import os
import re
import subprocess
import sys
from distutils.version import StrictVersion

# set videoslimmer version numbers
latest_vs_version = "1.0.3"

# define path to videoslimmer root
videoslimmer_root_path_uni = os.path.dirname(os.path.realpath(__file__)).decode("utf-8")

# define path to videoslimmer logs folder
videoslimmer_logs_path_uni = os.path.join(videoslimmer_root_path_uni, u"logs")

# check version of python is 2.6.x or 2.7.x
if sys.version_info < (2, 6, 0) or sys.version_info >= (3, 0, 0):

    sys.stderr.write(u"videoslimmer requires python 2.6.x/2.7.x installed, your running version %s"), sys.version_info
    sys.exit()

else:

    # create full path to modules
    sitepackages_modules_full_path = os.path.join(videoslimmer_root_path_uni, u"modules/argparse")
    sitepackages_modules_full_path = os.path.normpath(sitepackages_modules_full_path)

    # append full path to sys
    sys.path.insert(1, sitepackages_modules_full_path)


# used to decode byte strings to unicode, either utf-8 (normally used on linux) or cp1252 (windows)
def byte_to_uni(name):

    # if type is byte string then decode to unicode, otherwise assume already unicode
    if isinstance(name, str) and name is not None:

        try:
            # linux default encode
            name = name.decode('utf8')

        except UnicodeEncodeError:
            # windows default encode
            name = name.decode('windows-1252')

    return name


# used to encode unicode to byte strings, either utf-8 (normally used on linux) or cp1252 (windows)
def uni_to_byte(name):

    # if type is unicode then encode to byte string, otherwise assume already byte string
    if isinstance(name, unicode) and name is not None:

        if os.name == "nt":
            try:
                # windows default encode
                name = name.encode('windows-1252')

            except UnicodeEncodeError:
                # linux default encode
                name = name.encode('utf8')

        else:
            try:
                # linux default encode
                name = name.encode('utf8')

            except UnicodeEncodeError:
                # windows default encode
                name = name.encode('windows-1252')

    return name


# custom argparse to redirect user to help if unknown argument specified
class ArgparseCustom(argparse.ArgumentParser):

    def error(self, message):

        sys.stderr.write('\n')
        sys.stderr.write('error: %s\n' % message)
        sys.stderr.write('\n')
        self.print_help()
        sys.exit(2)


# setup argparse description and usage, also increase spacing for help to 50
commandline_parser = ArgparseCustom(prog="VideoSlimmer",
                                    description="%(prog)s " + latest_vs_version,
                                    usage="%(prog)s [--help] --mkvmerge <path> --media <path> "
                                          "--lang <code> [--dry-run yes] [--log <level>]"
                                          "[--keep-all-subtitles] [--version]",
                                    formatter_class=lambda prog: argparse.HelpFormatter(prog, max_help_position=70))
commandline_parser.add_argument(u"--mkvmerge", metavar=u"<path>", required=True,
                                help=u"specify the path to mkvmerge")
commandline_parser.add_argument(u"--media",  metavar=u"<path>", required=True,
                                help=u"specify the path to your media")
commandline_parser.add_argument(u"--lang", metavar=u"<code>", required=True,
                                help=u"specify the language you want to keep e.g. --lang eng")
commandline_parser.add_argument(u"--dry-run", metavar=u"no",
                                help=u"specify whether you want to perform a dry run e.g. --dry-run yes")
commandline_parser.add_argument(u"--logpath", metavar=u"<path>",
                                help=u"specify the path to your log files")
commandline_parser.add_argument(u"--loglevel", metavar=u"<level>",
                                help=u"specify the logging level: debug, info, warning, error")
commandline_parser.add_argument(u"--keep-all-subtitles", action=u"store_true",
                                help=u"Keep all subtitles regardless of language")
commandline_parser.add_argument(u"--version", action=u"version", version=latest_vs_version)

# save arguments in dictionary
args = vars(commandline_parser.parse_args())

# save mkvmerge location
if os.path.exists(args["mkvmerge"]):

    mkvmerge_cli_str = args["mkvmerge"]
    mkvmerge_cli_uni = byte_to_uni(mkvmerge_cli_str)
    mkvmerge_cli_utf8 = uni_to_byte(mkvmerge_cli_uni)

else:

    sys.stderr.write(u"mkvmerge location does not exist")
    sys.exit()

# save media location
if os.path.exists(args["media"]):

    media_root_path_str = args["media"]
    media_root_path_uni = byte_to_uni(media_root_path_str)
    media_root_path_utf8 = uni_to_byte(media_root_path_uni)

else:

    sys.stderr.write(u"media location does not exist")
    sys.exit()

# save preferred language
if len(args["lang"]) == 3:

    preferred_lang_str = args["lang"]
    preferred_lang_uni = byte_to_uni(preferred_lang_str)
    preferred_lang_utf8 = uni_to_byte(preferred_lang_uni)

else:

    sys.stderr.write(u"language code incorrect length, should be 3 characters")
    sys.exit()

# if enabled then perform dry run
if args["dry_run"] == "yes":

    dry_run = True

else:

    dry_run = False

# save log path
if args["logpath"] is None:

    videoslimmer_logs_file_uni = os.path.join(videoslimmer_logs_path_uni, u"videoslimmer.log")

else:

    logs_path_uni = byte_to_uni(args["logpath"])

    if not os.path.exists(logs_path_uni):

        os.makedirs(logs_path_uni)

    videoslimmer_logs_file_uni = os.path.join(logs_path_uni, u"videoslimmer.log")

# save log level
if args["loglevel"] is None:

    log_level = u"info"

elif args["loglevel"] in ["debug", "info", "warning", "error"]:

    log_level = args["loglevel"]
    log_level = byte_to_uni(log_level)

else:

    sys.stderr.write(u"incorrect logging level specified, defaulting to log level 'info'")
    log_level = u"info"

# check version of mkvmerge is 6.5.0 or greater
cmd = [mkvmerge_cli_str, "-V"]
mkvmerge = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
stdout, stderr = mkvmerge.communicate()

mkmerge_version = re.compile(r"(?<=v)[\d.]+").search(stdout)

# if min version not met, then exit
if StrictVersion(mkmerge_version.group()) < StrictVersion("6.5.0"):

    sys.stderr.write(u"mkvmerge version is less than 6.5.0, please upgrade")
    sys.exit()

###########
# logging #
###########


def videoslimmer_logging():

    # setup formatting for log messages
    videoslimmer_formatter = logging.Formatter(u"%(asctime)s %(levelname)s %(module)s %(funcName)s :: %(message)s")

    # setup logger for videoslimmer
    videoslimmer_logger = logging.getLogger(u"videoslimmer")

    # add rotating log handler
    videoslimmer_rotatingfilehandler = logging.handlers.RotatingFileHandler(videoslimmer_logs_file_uni, "a",
                                                                            maxBytes=10485760, backupCount=3,
                                                                            encoding="utf-8")

    # set formatter for videoslimmer
    videoslimmer_rotatingfilehandler.setFormatter(videoslimmer_formatter)

    # add the log message handler to the logger
    videoslimmer_logger.addHandler(videoslimmer_rotatingfilehandler)

    # setup logging to console
    console_streamhandler = logging.StreamHandler()

    # set formatter for console
    console_streamhandler.setFormatter(videoslimmer_formatter)

    # add handler for formatter to the console
    videoslimmer_logger.addHandler(console_streamhandler)

    # set level of logging
    if log_level == u"debug":

        console_streamhandler.setLevel(logging.DEBUG)
        videoslimmer_logger.setLevel(logging.DEBUG)

    elif log_level == u"info":

        console_streamhandler.setLevel(logging.INFO)
        videoslimmer_logger.setLevel(logging.INFO)

    elif log_level == u"warning":

        console_streamhandler.setLevel(logging.WARNING)
        videoslimmer_logger.setLevel(logging.WARNING)

    elif log_level == u"exception":

        console_streamhandler.setLevel(logging.ERROR)
        videoslimmer_logger.setLevel(logging.ERROR)

    else:

        console_streamhandler.setLevel(logging.INFO)
        videoslimmer_logger.setLevel(logging.INFO)

    return videoslimmer_logger


# store the logger instances
vs_log = videoslimmer_logging()


def audio_tracks(mkvmerge_info_stdout_uni):

    # create empty lists for audio to remove and preferred audio
    remove_audio_list = []
    pref_audio_list = []
    audio_track_list = []

    media_metadata = json.loads(mkvmerge_info_stdout_uni)

    # search for audio tracks using regex
    for track in media_metadata['tracks']:
        if track['type'] == 'audio':
            print track['properties']['language']
            audio_track_list.append(track)

    # find audio to remove and keep
    if audio_track_list:

        # find audio tracks to remove, if not found then skip
        for audio_track in audio_track_list:
            audio_lang = audio_track['properties']['language']

            if audio_lang is not None and audio_lang != preferred_lang_str:

                    if audio_track['id'] is not None:
                        remove_audio_list.append(audio_track['id'])

        if not remove_audio_list:
            vs_log.info(u"no audio tracks to remove")

        else:
            vs_log.info(u"audio track id(s) that dont match preferred are %s" % (byte_to_uni(
                ', '.join(str(e) for e in remove_audio_list))))

            # find audio tracks with preferred language, if not found then skip
            for audio_track in audio_track_list:
                audio_lang = audio_track['properties']['language']

                if audio_lang is not None and audio_lang == preferred_lang_str:

                        if audio_track['id'] is not None:
                            pref_audio_list.append(audio_track['id'])

            if not pref_audio_list:
                vs_log.info(u"no audio tracks with preferred language, skipping removal")

            else:
                vs_log.info(u"preferred audio track present, marking for removal of other audio tracks")

    else:
        vs_log.info(u"no audio tracks present")

    return remove_audio_list, pref_audio_list


def subtitle_tracks(mkvmerge_info_stdout_uni):

    if args['keep_all_subtitles']:
        vs_log.info(u"--keep-all-subtitles flags is set. Any existing subtitles will be kept")
        return [], []

    # create empty lists for subtitles to remove and preferred subtitles
    remove_subtitle_list = []
    pref_subtitle_list = []
    subtitle_track_list = []

    media_metadata = json.loads(mkvmerge_info_stdout_uni)

    # search for subtitle tracks using regex
    for track in media_metadata['tracks']:
        if track['type'] == 'subtitles':
            subtitle_track_list.append(track)

    # find subtitle to remove and keep
    if subtitle_track_list:

        # find subtitle tracks to remove, if not found then skip
        for subtitle_track in subtitle_track_list:
            subtitle_lang = subtitle_track['properties']['language']

            if subtitle_lang is not None and subtitle_lang != preferred_lang_str:

                    if subtitle_track['id'] is not None:
                        remove_subtitle_list.append(subtitle_track['id'])

        if not remove_subtitle_list:
            vs_log.info(u"no subtitles to remove")

        else:
            vs_log.info(
                u"subtitle id(s) that dont match preferred are %s" % (byte_to_uni(
                    ", ".join(str(e) for e in remove_subtitle_list))))

            # find subtitle tracks with preferred language, if not found then skip
            for subtitle_track in subtitle_track_list:
                subtitle_lang = subtitle_track['properties']['language']

                if subtitle_lang is not None and subtitle_lang == preferred_lang_str:

                        if subtitle_track['id'] is not None:
                            pref_subtitle_list.append(subtitle_track['id'])

            if not pref_subtitle_list:
                vs_log.info(u"no subtitle with preferred language, skipping removal")

            else:
                vs_log.info(u"preferred subtitle present, marking for removal of other subtitles")

    else:
        vs_log.info(u"no subtitles present")

    return remove_subtitle_list, pref_subtitle_list


def videoslimmer():

    vs_log.info(u"[BEGIN] VideoSlimmer processing started")

    # walk media root path, convert to byte string before walk
    for root, dirs, files in os.walk(media_root_path_uni):

        for media_filename in files:

            # filter out non mkv files
            if not media_filename.endswith(u".mkv"):
                vs_log.warning(u"File \"%s\" does not have an mkv extension, skipping file" % media_filename)
                continue

            # create filename minus extension
            media_file_bare = os.path.splitext(media_filename)[0]

            vs_log.debug(u"filename without extension is \"%s\"" % media_file_bare)

            if dry_run is True:

                vs_log.info(u"[DRY RUN] No files will be modified")

            # create full path to media file
            media_file_path_uni = os.path.join(root, media_filename)
            media_file_path_str = uni_to_byte(media_file_path_uni)

            vs_log.info(u"Processing file %s" % media_file_path_uni)

            # create full path to temporary file
            temp_file_path_uni = (u"%s.temp" % media_file_path_uni)
            temp_file_path_str = uni_to_byte(temp_file_path_uni)

            # create temporary file
            temp_file_uni = u"%s.temp" % media_filename

            # delete any previously failed merge files
            if os.path.exists(temp_file_path_str):

                os.remove(temp_file_path_str)
                vs_log.debug(u"deleted temporary file %s" % temp_file_path_uni)

            vs_log.debug(u"analysing file \"%s\"" % media_filename)
            vs_log.debug(u"path to file is \"%s\"" % root)

            # build command line
            mkvmerge_cmd = [mkvmerge_cli_uni, u"-J", media_file_path_uni]
            vs_log.debug(u"mkvmerge command to query file is \"%s\"" % mkvmerge_cmd)

            # get file system encoding type and then encode all items in the list
            file_system_encoding = sys.getfilesystemencoding()
            mkvmerge_cmd = [x.encode(file_system_encoding) for x in mkvmerge_cmd]

            # use mkvmerge to get info for file
            mkvmerge_info = subprocess.Popen(mkvmerge_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            mkvmerge_info_stdout, mkvmerge_info_stderr = mkvmerge_info.communicate()

            mkvmerge_info_stdout_uni = byte_to_uni(mkvmerge_info_stdout)

            if mkvmerge_info.returncode != 0:

                vs_log.warning(u"mkvmerge failed to identify file %s"), media_file_path_uni
                continue

            remove_audio_list, pref_audio_list = audio_tracks(mkvmerge_info_stdout_uni)
            remove_subtitle_list, pref_subtitle_list = subtitle_tracks(mkvmerge_info_stdout_uni)

            # if no audio or subtitles to remove then skip to next iteration
            if not (pref_audio_list and remove_audio_list):

                if not (pref_subtitle_list and remove_subtitle_list):

                    vs_log.info(u"No audio, subtitles or metadata to change")
                    vs_log.info(u"[SKIPPED] Processing finished")
                    continue

            # build command line
            mkvmerge_cmd = [mkvmerge_cli_uni, u"-o", temp_file_path_uni]

            # check preferred audio exists, and there are audio tracks to remove
            if pref_audio_list and remove_audio_list:

                mkvmerge_cmd += [u"--audio-tracks", u"%s" % (u",".join(str(e) for e in pref_audio_list))]
                mkvmerge_cmd += [u"--default-track", u"%s" % (pref_audio_list[0])]

            # check preferred subtitle exists, and there are subtitles to remove
            if pref_subtitle_list and remove_subtitle_list:

                mkvmerge_cmd += [u"--subtitle-tracks", u"%s" % (u",".join(str(e) for e in pref_subtitle_list))]
                mkvmerge_cmd += [u"--default-track", u"%s" % (pref_subtitle_list[0])]

            mkvmerge_cmd += [media_file_path_uni]

            vs_log.debug(u"mkvmerge command to edit file is \"%s\"" % mkvmerge_cmd)

            file_system_encoding = sys.getfilesystemencoding()
            mkvmerge_cmd = [x.encode(file_system_encoding) for x in mkvmerge_cmd]

            if dry_run is True:

                vs_log.info(u"[DRY RUN] mkvmerge command is %s" % mkvmerge_cmd)

            else:

                # process file
                mkvmerge_info = subprocess.Popen(mkvmerge_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                mkvmerge_info_stdout, mkvmerge_info_stderr = mkvmerge_info.communicate()

                if mkvmerge_info.returncode != 0:

                    vs_log.warning(u"[FAILED] output from mkvmerge is %s" % (byte_to_uni(mkvmerge_info_stdout)))

                    if os.path.exists(temp_file_path_str):

                        # if failed then delete temp file
                        os.remove(temp_file_path_str)
                        vs_log.debug(u"deleted temporary file %s" % temp_file_uni)

                    vs_log.warning(u"[FAILED] mkvmerge returned non zero return code")
                    continue

                vs_log.debug(u"mkvmerge returned success")

                # remove source file and rename temp
                os.remove(media_file_path_str)
                vs_log.debug(u"removed source file \"%s\"" % media_file_path_uni)

                os.rename(temp_file_path_str, media_file_path_str)
                vs_log.debug(u"renamed temporary file from \"%s\" to \"%s\"" % (temp_file_uni, media_filename))

            vs_log.info(u"[SUCCESS] Processing finished")

    vs_log.info(u"[EXIT] VideoSlimmer finished")


if __name__ == '__main__':

    # run main function
    videoslimmer()
