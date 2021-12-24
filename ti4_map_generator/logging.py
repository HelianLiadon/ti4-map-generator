import colorlog

formatter = colorlog.ColoredFormatter(
    "%(asctime)s [%(log_color)s%(levelname)s%(reset)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    reset=True,
    log_colors={
        'DEBUG':    'cyan',
        'INFO':     'green',
        'WARNING':  'yellow',
        'ERROR':    'red',
        'CRITICAL': 'red,bg_white',
    },
    secondary_log_colors={},
    style='%'
)

handler = colorlog.StreamHandler()
handler.setFormatter(formatter)


def get_logger(name):
    logger = colorlog.getLogger(name)
    logger.addHandler(handler)
    return logger
