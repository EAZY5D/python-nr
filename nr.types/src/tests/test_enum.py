
from nr.types.enum import Enumeration


def test_enum():
  assert hasattr(Enumeration, 'Data')

  class Color(Enumeration):
    Red = 0
    Green = 2
    Blue = 1
    Fav = Enumeration.Data('Purple')

  assert not hasattr(Color, 'Data')
  assert Color.Fav == 'Purple'
  assert Color.Red == Color(0)
  assert Color.Green == Color(2)
  assert Color.Blue == Color(1)
  assert set([Color.Red, Color.Green, Color.Blue]) == set(Color)
  assert set([Color.Red, Color.Green, Color.Blue]) == set(Color.__values__())
