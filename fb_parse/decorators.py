# encoding:utf-8
from threading import Thread


def run_in_new_thread(fn):
    """
    :param fn:
    :return:
    :rtype:Thread
    """
    def wrapped(*args, **kwargs):
        new_process = Thread(target=fn, args=args, kwargs=kwargs)
        new_process.start()
        return new_process
    return wrapped