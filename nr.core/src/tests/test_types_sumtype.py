
from nr.core.types.sumtype import Sumtype


def test_sumtypes():

  class Result(Sumtype):
    Loading = Sumtype.Constructor('progress')
    Error = Sumtype.Constructor('message')
    Ok = Sumtype.Constructor('filename', 'load')

    @Sumtype.MemberOf([Loading])
    def alert(self):
      return 'Progress: ' + str(self.progress)

    static_error_member = Sumtype.MemberOf([Error], 'This is a member on Error!')

  assert not hasattr(Result, 'Constructor')
  assert not hasattr(Result, 'alert')
  assert not hasattr(Result, 'static_error_member')

  x = Result.Loading(0.5)
  assert isinstance(x, Result)
  assert x.is_loading()
  assert not x.is_error()
  assert not x.is_ok()
  assert hasattr(x, 'alert')
  assert not hasattr(x, 'static_error_member')
  assert x.alert() == 'Progress: 0.5'
  assert x.progress == 0.5
