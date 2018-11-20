
from nr.powerline.plugins import Plugin


class CharactersPlugin(Plugin):

  CHARACTERS = dict(
    # Icons
    USER = 0xf007,
    DIRECTORY = 0xf413,
    BRANCH = 0xe0a0,
    GIT_FOLDER = 0xe5fb,

    # Shapes
    RIGHT_TRIANGLE = 0xe0b0,
    LEFT_TRIANGLE = 0xe0b2,
    UPPER_LEFT_TRIANGLE = 0xe0bc,
    LOWER_LEFT_TRIANGLE = 0xe0b8,
    UPPER_RIGHT_TRIANGLE = 0xe0be,
    LOWER_RIGHT_TRIANGLE = 0xe0ba
  )

  def __getattr__(self, name):
    try:
      return chr(self.CHARACTERS[name])
    except KeyError:
      raise AttributeError(name)
