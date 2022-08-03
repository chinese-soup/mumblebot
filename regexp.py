import re

re_intensify = re.compile(r"^\[(.*)\]$")  # ^\[(.*)\]$

_stream_all_regex = re.compile(
    r"^(.*) \[info\]\s+[0-9]+\#[0-9]+\:\s+\*([0-9]+)\s+((publish)\:\s+name='(.*\w)\'|(deleteStream)).*\:\s+(.*)\,.*$",
    re.IGNORECASE | re.MULTILINE)

_regex_scoreboard = re.compile(r'\"STEAM[^"]+\"\s+\"([^"]+)\"\s+[0-9]\s+[0-9]+\s+([^\s]+)\s+(.*)')

_wiki_language_codes = ["en", "sv", "de", "nl", "fr", "war", "ru", "ceb", "it", "es", "vi", "pl", "ja", "pt", "zh",
                        "uk", "ca", "fa", "sh", "no", "ar", "fi", "id", "ro", "cs", "hu", "sr", "ko", "ms", "tr", "min",
                        "eo", "kk", "eu", "da", "sk", "bg", "he", "hy", "lt", "hr", "sl", "et", "uz", "gl", "nn", "vo",
                        "la", "simple", "el", "hi"]

link_re = re.compile(r'.*(https?://([-\w\.]+)+(:\d+)?(/([\S/_\.]*(\?\S+)?)?)?)', re.I)
re_implying = re.compile(r"^[&]gt[;](.*\.(gif|GIF|jpg|JPG|jpeg|JPEG|png|PNG|tiff|TIFF|bmp|BMP))\s?(\d+)?")

_wiki_regex = re.compile("^((" + "|".join(_wiki_language_codes) + "|)\s)?(.*)$")  # jsem retard no, nasrat :^)

_interval_regex = re.compile(
    "^((?P<hr>[0-9]+)\:)?"
    "(?P<min>[0-9]+)"
    "(\:(?P<sec>[0-9]{1,2}))?"
    "[ ]+(?P<data>.+)[ ]*$",
    re.IGNORECASE)

_named_interval_regex = re.compile(
    "^((?P<w>[0-9]+)[ ]*(w|weeks?))?[ ]*"
    "((?P<d>[0-9]+)[ ]*(d|days?))?[ ]*"
    "((?P<hr>[0-9]+)[ ]*(h|hours?))?[ ]*"
    "((?P<min>[0-9]+)[ ]*(m|mins?|minutes?))?[ ]*"
    "((?P<sec>[0-9]+)[ ]*(s|secs?|seconds?))?"
    "[ ]+(?P<data>.+)[ ]*$",
    re.IGNORECASE)

_prefix_regex = re.compile(
    "^@((?P<day>[0-9]{1,2})\."
    "(?P<month>[0-9]{1,2})\."
    "(?P<year>[0-9]{4})[ ]+)?"
    "(?P<hour>[0-9]{1,2})\:"
    "(?P<minute>[0-9]{1,2})"
    "(\:(?P<second>[0-9]{1,2}))?"
    "[ ]+(?P<data>.+)[ ]*$",
    re.IGNORECASE)