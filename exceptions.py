class APIUnexpectedHTTPStatus(Exception):
    pass

class MessageSendError(Exception):
    pass

class KeyNotFoundError(Exception):
    pass

class APIFormatError(Exception):
    pass

class UnavailableToken(Exception):
    pass
class NotWorkingError(Exception):
    pass

class JSONError(Exception):
    pass