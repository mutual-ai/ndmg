from ndmg.register import register
from pathlib import Path
import pytest

bval = Path('/Users/alex/Dropbox/NeuroData/ndmg-top/ndmg/examples/bval')
bvec = Path('/Users/alex/Dropbox/NeuroData/ndmg-top/ndmg/examples/bvec')
data = Path('/Users/alex/Dropbox/NeuroData/ndmg-top/ndmg/examples/data.nii.gz')

def test_register():
    pass

class TestClass(object):
    def test_one(self):
        x = "this"
        assert "h" in x

    def test_two(self):
        x = "this"
        assert type(x) == str

    def test_three(self, tmpdir):
        print(tmpdir)
        assert 0