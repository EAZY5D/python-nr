# Copyright (c) 2016  Niklas Rosenstein
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import unittest
import sys

if sys.version[:3] <= '2.6':
  raise unittest.SkipTest("nr.version requires Python 2.7 or Python 3")

from nose.tools import *
from nr.semver import Version, Specifier

def test_version():
  assert Version('1').parts == [1, 0, 0]
  assert Version('7.42').parts == [7, 42, 0]
  assert Version('3.9.1').parts == [3, 9, 1]
  assert Version('1.7.42.extension').parts == [1, 7, 42]
  assert Version('1.7.42.extension').extension == '.extension'
  assert Version('1.7.42-beta.-foo67.bar').extension == '-beta.-foo67.bar'
  assert Version('1.0') <= Version('1.0.19-alpha')
  assert Version('1.0.19-alpha') >= Version('1.0')
  assert Version('1.0.1') >= Version('1.0')
  assert not Version('1.0.1') < Version('1.0')
  assert not Version('1.32.0') <= Version('1.9.2')
  assert Version(Version('1.0.9.alpha')) == Version('1.0.9.alpha')
  assert Version(Version('1.0.9+alpha')) == Version('1.0.9.alpha')
  assert Version(Version('1.0.9+alpha')) != Version('1.0.9-alpha')
  assert Version(Version('1.0.9+alpha')) > Version('1.0.9')
  assert Version(Version('1.0.9+alpha')) > Version('1.0.9-alpha')
  assert Version(Version('1.0.9')) < Version('1.0.9+alpha')
  assert Version(Version('1.0.9-alpha')) < Version('1.0.9+alpha')
  assert Version(Version('1.0.9a')) > Version('1.0.9')
  assert Version(Version('1.0.9a')) == Version('1.0.9+a')
  assert str(Version('1.0.9a')) == '1.0.9a'

@raises(ValueError)
def test_version_invalid1():
  Version('1.0.42.')

def test_version_cmp():
  assert Version('1') == Version('1.0')
  assert Version('1') == Version('1.0.0')
  assert Version('1.1') > Version('1.0.0')
  assert Version('1.0.0') < Version('1.0.1')
  assert Version('1') <= Version('1.0.0')
  assert Version('1.0-alpha') < Version('1')
  assert Version('1.0-alpha') < Version('1.0.0')
  assert Version('1.0.alpha') > Version('1.0.0')
  assert Version('1.0+alpha') > Version('1')
  assert Version('1.0.0') > Version('1.0-alpha')

def test_version_satisfies():
  assert not Version('1.2.3').satisfies('=1.0')
  assert not Version('1.2.3').satisfies('=1.0 || >2.5')
  assert Version('1.2.3').satisfies('=1.0 || >2.5 || 0.9 - 1.3.0-rc1')
  assert Version('1.2.3-alpha').satisfies('0.9 - 1.3.0-rc1')

def test_version_attr():
  ver = Version('1.42.9-alpharc1')
  ver.major = 2
  ver.minor -= 2
  ver.patch += 1
  ver.extension = '-gammaray5'
  assert ver == Version('2.40.10-gammaray5')

def test_critera():
  with assert_raises(ValueError) as exc:
    Specifier('')

  assert Specifier('~ 1.0')(Version('1.0.1'))
  assert Specifier('~ 1.0')(Version('1.0.6'))
  assert Specifier('~ 1.0')(Version('1.0.19-alpha'))
  assert Specifier('~ 1.0')(Version('1.0.1.rc1'))
  assert Specifier('1.0 - 1.9.2')(Version('1.0'))
  assert Specifier('1.0 - 1.9.2')(Version('1.9.2'))
  assert Specifier('1.0 - 1.9.2')(Version('1.8-alpha'))
  assert not Specifier('1.0 - 1.9.2')(Version('1.32'))
  assert not Specifier('>2.5')(Version('1.2.3'))

  versions = [Version('1.9.3'), Version('1.2.3'), Version('1.2.6'), Version('1.2.7')]
  assert Specifier('~1.2.5').best_of(versions, is_sorted=True) == Version('1.2.6')
  assert Specifier('~1.2.5').best_of(versions) == Version('1.2.7')

  assert str(Specifier("1.x.9-alpha")) == "1.x.9-alpha", str(Specifier("1.x.9-alpha"))
  assert str(Specifier("1.x.9-x")) == "1.x.9-x"
  assert str(Specifier("1.x.9.alpha")) == "1.x.9.alpha"
  assert str(Specifier("1.x.9.x")) == "1.x.9.x"
  assert Specifier("1.x")(Version('1.9.224'))
  assert Specifier("1.x")(Version('1.9.224-alpha'))
  assert Specifier("1.9.224-x")(Version('1.9.224-alpha'))
  assert Specifier("1.9.224.x")(Version('1.9.224-alpha'))
  assert Specifier("1.x.x")(Version('1.9.224'))
  assert Specifier("1.x.x")(Version('1.3.224'))
  assert Specifier("x.6.x")(Version('5.6.2'))
  assert Specifier("x.6.x")(Version('1.6.9'))
  assert not Specifier("x.6.x")(Version('1.7.9'))

def test_critera_invalid1():
  assert_true(Specifier('~ 1.0')(Version('1.0.0.rc1')))
  assert_true(Specifier('~ 1.0')(Version('1.0.0+rc1')))
  assert_false(Specifier('~ 1.0')(Version('1.0.0-alpha')))
