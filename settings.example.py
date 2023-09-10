class Settings:
    # Basic
    server_ip = "127.0.0.1"
    server_password = ""  # leave empty if not required
    bot_nickname = "mumblebot"
    command_prefix = "."

    # Set these for the .youtube command to work
    youtube_key = ""
    youtube_cx = ""

    google_api_url = "https://www.googleapis.com/customsearch/v1?"
    google_cx = ""

    # Our specific private RTMP server stuff here, you can ignore these #
    enable_stream_announcements = True
    stream_alert_username = ""
    stream_alert_password = ""
    stream_alert_url = ""
    ignored_stream_keys = []
    announce_disconnects = False
    header_color = "#ff5558"

    hlds_server_ip = ""
    hlds_server_port = 27015

    minecraft_servers = [
        {"ip": "127.0.0.1", "port": 25565},
        {"ip": "mojang.com", "port": 42069}
    ]

    ag_records_url = ""
    get_map_url = ""

    # OpenWeatherMap.org app id, add this for .weather command to work
    openweathermap_appid = ""


