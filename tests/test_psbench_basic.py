import pytest
import py_sci_bench

def test_version():
    assert hasattr(py_sci_bench, '__version__')

