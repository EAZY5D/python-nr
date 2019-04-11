
import nr.core.types.interface as interface
import pytest


def test_multi_implementation():

  class ParameterInterface(interface.Interface):
    params = interface.attr(dict)
    def __init__(self):
      self.params = {}
    def __constructed__(self):
      self.declare_parameters()
    def declare_parameters(self):
      pass

  class CalculateInterface(interface.Interface):
    inputs = interface.attr(list)
    outputs = interface.attr(dict)
    def __init__(self):
      self.inputs = []
      self.outputs = {}
    def __constructed__(self):
      self.declare_inputs_outputs()
    def declare_inputs_outputs(self):
      pass
    @property
    @interface.default
    def calculate_prop(self):
      return 'Foobar!'
    @calculate_prop.setter
    def calculate_prop(self, value):
      pass
    @interface.final
    def final_method(self):
      return 'Bar'

  class MyParameters(interface.Implementation):
    interface.implements(ParameterInterface, CalculateInterface)
    def declare_parameters(self):
      self.params['depth'] = 32
    def declare_inputs_outputs(self):
      self.inputs.append('foo')
      self.outputs['bar'] = 'spam'
    @CalculateInterface.calculate_prop.setter
    def calculate_prop(self, value):
      value.append(True)

  obj = MyParameters()

  assert obj.implements(ParameterInterface)
  assert obj.params['depth'] == 32

  assert obj.implements(CalculateInterface)
  assert obj.inputs == ['foo']
  assert obj.outputs == {'bar': 'spam'}

  assert obj.calculate_prop == 'Foobar!'
  value = []
  obj.calculate_prop = value
  assert value == [True]

  assert obj.final_method() == 'Bar'


class AFinalInterface(interface.Interface):
  @interface.final
  def final_method(self):
    pass


class BFinalInterface(interface.Interface):
  @interface.final
  def final_method(self):
    pass


def test_final():
  with pytest.raises(interface.ImplementationError):
    # Can not implement final_method().
    class Test(interface.Implementation):
      interface.implements(AFinalInterface)
      def final_method(self):
        pass


def test_conflict():
  with pytest.raises(interface.ConflictingInterfacesError):
    class Test(interface.Implementation):
      interface.implements(AFinalInterface, BFinalInterface)
