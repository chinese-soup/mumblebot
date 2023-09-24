import datetime
import re

import pycountry
import pytz
import requests

# BeautifulSoup
from bs4 import BeautifulSoup

# GeoIP
from geoip import geolite2

# Import bot settings
from tabulate import tabulate

# Import required compiled regular expressions
from regexp import (
    _interval_regex,
    _named_interval_regex,
    _prefix_regex,
    _regex_scoreboard,
)
from settings import Settings


class Utils:
    past_publish = {}
    past_records = []  # FIFO, up to 35 elements, used for AG server records

    @staticmethod
    def get_current_time(location):
        try:
            timezones = pytz.country_timezones(location)
            if timezones:
                timezone = pytz.timezone(timezones[0])
                current_time = pytz.utc.localize(datetime.datetime.utcnow()).astimezone(
                    timezone
                )
                # return f"Current time in {timezone}: {current_time.strftime('%H:%M:%S %Z (%z) %Y-%m-%d')} {timezone}"
                return [
                    str(timezone),
                    current_time.strftime("%Z"),
                    current_time.strftime("%H:%M:%S"),
                    current_time.strftime("%z"),
                    current_time.strftime("%Y-%m-%d"),
                ]
            else:
                return [f"Timezone not found for {location}"]

        except KeyError:
            country = pycountry.countries.search_fuzzy(location)[0]
            country_code = country.alpha_2
            timezones = pytz.country_timezones(country_code)[0]

            if timezones:
                timezone = pytz.timezone(timezones)
                current_time = pytz.utc.localize(datetime.datetime.utcnow()).astimezone(
                    timezone
                )
                return [
                    str(timezone),
                    current_time.strftime("%Z"),
                    current_time.strftime("%H:%M:%S"),
                    current_time.strftime("%z"),
                    current_time.strftime("%Y-%m-%d"),
                ]
            else:
                return [f"Timezone not found for {location}"]

    @staticmethod
    def get_url(match):
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:35.0) Gecko/20100101 Firefox/35.0"
            }
            r = requests.get(
                match.group(1),
                headers=headers,
                allow_redirects=True,
                stream=True,
                timeout=2,
            )
        except Exception as e:
            return  # 'URL Error: {}'.format(e)

        domain = match.group(3)
        if r.status_code != 404:
            content_type = r.headers["Content-Type"]
            try:
                encoding = r.headers["content-encoding"]
            except:
                encoding = ""

            if content_type.find("html") != -1:  # and content_type is not 'gzip':
                data = ""
                for chunk in r.iter_content(chunk_size=1024):
                    data += chunk.decode("utf-8")
                    if len(data) > 48336:
                        break

                # body = html.fromstring(data)
                soup = BeautifulSoup(data, "lxml")

                try:
                    title = soup.find("title").get_text()

                    if (
                        "youtube.com" in title.lower()
                    ):  # We get youtube.com seperately with video likes etc.
                        return
                    else:
                        return "<b>{}</b>".format(title)

                except:
                    return "URL No Title ({})".format(domain)

            else:
                try:
                    length = 0

                    if r.headers["Content-Length"]:
                        length = int(r.headers["Content-Length"])
                        print("Length= {}".format(length))
                        if length < 0:
                            length = "Unknown size"
                        else:
                            length = length = "{} bytes".format(length)
                    else:
                        length = "?"

                except Exception as e:
                    print(e)
                    length = "Unknown size"

                if "503 B" in length:
                    length = ""
                if length is None:
                    length = ""
                return "URL {} Size: {} ({})".format(content_type, length, domain)
        else:
            return "HTTP 404 returned."

    @staticmethod
    def get_youtube_url(match):
        base_url = "https://www.googleapis.com/youtube/v3/"
        search_api_url = base_url + "search?part=id,snippet"
        api_url = base_url + "videos?part=snippet,statistics,contentDetails"
        # video_url = "%s"
        youtube_re = re.compile(
            r".*(?:youtube.*?(?:v=|/v/)|youtu\.be/|yooouuutuuube.*?id=)([-_a-zA-Z0-9]+)",
            re.I,
        )

        try:
            print("URL = {}".format(match))

            youtube_match = youtube_re.match(match)
            print("youtube_match = {}".format(youtube_match.groups()))
            video_id = youtube_match.group(1)  # lol

        except Exception as e:
            print(e)
            return

        inp = " ".join(match)
        payload = {"key": Settings.youtube_key, "id": video_id}
        request = requests.get(api_url, params=payload)

        print(request.text)
        json_res = request.json()

        if "error" in request.text:
            return "Error performing search."

        if json_res["pageInfo"]["totalResults"] == 0:
            return "No results found."

        print(json_res)

        json_snippet = json_res["items"][0]["snippet"]
        video_title = json_snippet["title"]
        video_desc = json_snippet["description"]

        json_stats = json_res["items"][0]["statistics"]
        viewCount = json_stats["viewCount"]
        try:
            likes = json_stats["likeCount"]
            # dislikes = json_stats['dislikeCount']

        except KeyError:
            likes = "disabled"
            dislikes = "disabled"
            percent = 0
        # video_channel_title = json_res['items'][0]['channelTitle']

        return "[YouTube] <b>{0}</b> | <strong>Views:</strong> {1:,} | <span style='color: green'>👍: {2:,}</span> | <span style='color: orange;'>👎: ?</span> ".format(
            video_title, int(viewCount), int(likes)
        )

    @staticmethod
    def strip_nick(name):
        """TODO: MOve to util"""
        return re.sub(r"\^\d", "", name)

    @staticmethod
    def get_wiki_result(langcode, word):
        try:
            # quote by měl bejt v py3 fixnutej na unikód, jestli neni tak rip
            req = requests.get(
                f"https://{langcode}.wikipedia.org/w/api.php?action=opensearch&format=json&search={word}",
                timeout=3,
            )
        except Exception as e:
            print(f"Error sending request to wikipedia's API. Reason: {e}")
            return "Unknown error.".format()

        # parsed = json.loads(req.read().decode("utf-8"))
        parsed = req.json()
        if parsed[1] and parsed[2] and parsed[3]:
            article = parsed[1][0]
            shortinfo = (
                parsed[2][0]
                if parsed[2][0] != ""
                else "No short description available."
            )
            url = parsed[3][0]
            return "<b>{0}</b>: {1} (<a href='{2}'>{2}</a>)".format(
                article, shortinfo, url
            )
        else:
            return "Nothing found."

    @staticmethod
    def get_geoip(ip_addr):
        try:
            match = geolite2.lookup(ip_addr)
            return "{0} ({1} | {2})".format(
                match.country, match.timezone, list(match.subdivisions)[0]
            )

        except Exception as e:
            print("Exception at getting GeoIP: {0}".format(e))
            return None

    @staticmethod
    def get_map(mapname, number):
        req = requests.get(Settings.get_map_url.format(mapname=mapname))
        if req.status_code == 200:
            orig = req.text
            tuples_list = _regex_scoreboard.findall(orig)
            final = [list(x) for x in tuples_list]
            try:
                for i, x in enumerate(final):
                    date_out = datetime.datetime.fromtimestamp(int(x[2]))
                    final[i][2] = date_out.strftime("%d.%m. %Y %H:%M")
            except:
                print("Failed to date memes")

            final.insert(0, ["name", "time", "timestamp"])
            final = final[0 : number + 1]
            return (
                f"Map: {mapname}\n<pre>"
                f"<span style='font-family: monospace'>"
                f"{tabulate(final, tablefmt='fancy_grid', headers='firstrow')}</span>"
                f"</pre>"
            )

        elif req.status_code == 404:
            return 404
        else:
            return 500

    @staticmethod
    def _parse_time(data):
        from datetime import datetime, time, timedelta

        dt = datetime.now()

        if re.match("^@.+$", data):
            # Specific date/time
            m = re.search(_prefix_regex, data)
            if m:
                r = m.groupdict()
                # Set default values for missing one and
                # convert existing ones to int
                for key, value in r.items():
                    if key == "data":
                        continue
                    if value is None:
                        if key == "second":
                            r[key] = 0
                        else:
                            r[key] = getattr(dt, key)
                    else:
                        r[key] = int(value)

                try:
                    return (
                        datetime(
                            r["year"],
                            r["month"],
                            r["day"],
                            r["hour"],
                            r["minute"],
                            r["second"],
                        ),
                        r["data"],
                    )
                except:
                    return None, None
        else:
            # Time interval
            m = re.search(_named_interval_regex, data)
            if not m:
                m = re.search(_interval_regex, data)

            if m:
                r = m.groupdict()
                # Set 0 as default value and convert existing values to int
                for key, value in r.items():
                    if key == "data":
                        continue
                    if value is None:
                        r[key] = 0
                    else:
                        r[key] = int(value)

                # Set missing default values
                if "w" not in r:
                    r["w"] = 0
                if "d" not in r:
                    r["d"] = 0

                try:
                    td = timedelta(
                        weeks=r["w"],
                        days=r["d"],
                        hours=r["hr"],
                        minutes=r["min"],
                        seconds=r["sec"],
                    )
                    if td == 0:
                        return None, None
                    else:
                        return dt + td, r["data"]
                except Exception as e:
                    return None, None

        return None, None
