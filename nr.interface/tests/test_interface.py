
import nr.interface
from nose.tools import *

def test_multi_implementation():

  class ParameterInterface(nr.interface.Interface):
    params = nr.interface.attr(dict)
    def __init__(self):
      self.params = {}
    def __constructed__(self):
      self.declare_parameters()
    def declare_parameters(self):
      pass

  class CalculateInterface(nr.interface.Interface):
    inputs = nr.interface.attr(list)
    outputs = nr.interface.attr(dict)
    def __init__(self):
      self.inputs = []
      self.outputs = {}
    def __constructed__(self):
      self.declare_inputs_outputs()
    def declare_inputs_outputs(self):
      pass
    @property
    @nr.interface.default
    def calculate_prop(self):
      return 'Foobar!'
    @calculate_prop.setter
    def calculate_prop(self, value):
      pass
    @nr.interface.final
    def final_method(self):
      return 'Bar'

  class MyParameters(nr.interface.Implementation):
    nr.interface.implements(ParameterInterface, CalculateInterface)
    def declare_parameters(self):
      self.params['depth'] = 32
    def declare_inputs_outputs(self):
      self.inputs.append('foo')
      self.outputs['bar'] = 'spam'
    @CalculateInterface.calculate_prop.setter
    def calculate_prop(self, value):
      value.append(True)

  obj = MyParameters()

  assert_true(obj.implements(ParameterInterface))
  assert_equals(obj.params['depth'], 32)

  assert_true(obj.implements(CalculateInterface))
  assert_equals(obj.inputs, ['foo'])
  assert_equals(obj.outputs, {'bar': 'spam'})

  assert_equals(obj.calculate_prop, 'Foobar!')
  value = []
  obj.calculate_prop = value
  assert_equals(value, [True])

  assert_equals(obj.final_method(), 'Bar')


class AFinalInterface(nr.interface.Interface):
  @nr.interface.final
  def final_method(self):
    pass


class BFinalInterface(nr.interface.Interface):
  @nr.interface.final
  def final_method(self):
    pass


def test_final():
  with assert_raises(nr.interface.ImplementationError):
    # Can not implement final_method().
    class Test(nr.interface.Implementation):
      nr.interface.implements(AFinalInterface)
      def final_method(self):
        pass


def test_conflict():
  with assert_raises(nr.interface.ConflictingInterfacesError):
    class Test(nr.interface.Implementation):
      nr.interface.implements(AFinalInterface, BFinalInterface)
