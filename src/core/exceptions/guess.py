class GuessNotification(Exception):
    default_message = 'Достигнут лимит совпадений'

    def __init__(self, message):
        print(message)
