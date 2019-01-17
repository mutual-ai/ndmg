from ndmg.register import register
from pathlib import Path
import pytest
import os

# Not immediately sure how to do relative pathnames

# TODO: make paths relative
# TODO: figure out how to assert the existence of FSLDIR in terminal

# Define paths for basic input data
t1w_in = '/Users/alex/Dropbox/NeuroData/ndmg-top/ndmg/examples/s002_anat.nii.gz'
outdir_base_in = '/Users/alex/Dropbox/NeuroData/ndmg-top/ndmg/scratch'
dwi_in = '/Users/alex/Dropbox/NeuroData/ndmg-top/ndmg/examples/data.nii.gz'
fbval_in = '/Users/alex/Dropbox/NeuroData/ndmg-top/ndmg/examples/bval'
fbvec_in = '/Users/alex/Dropbox/NeuroData/ndmg-top/ndmg/examples/bvec'
atlas_in = '/Users/alex/Dropbox/NeuroData/ndmg-top/ndmg/examples/desikan_res-1x1x1.nii.gz'
vox_size = '2mm'

def test_register():
    """ 
    Huge class.

    Four methods:
    - gen_tissue
    - t1d2dwi_align
    - atlas2t1w2dwi_align
    - tissue2dwi_align

    Plan:
    - Assert that all of the input attributes are the type I expect
    - For each of the methods, run through that method in a jupyter notebook
    - Then, write tests for that method
    - Make the above more specific as I learn more about unit testing
    """

    # Assert FSL exists
    # assert FSLDIR, "FSLDIR environment variable not set!"

    reg = register.register(outdir_base_in, dwi_in, t1w_in, vox_size, simple=True)

    # Assert both of the output directories have been made
    assert os.path.exists(os.path.join(reg.outdir_base, 'reg_a'))
    assert os.path.exists(os.path.join(reg.outdir_base, 'reg_m'))
    
    # Assert that all of the default attributes of the reg object are the types I expect
    assert type(reg.outdir) == dict
    assert type(reg.outdir_base) == str
    assert type(reg.simple) == bool

    # register.register.gen_tissue(reg)