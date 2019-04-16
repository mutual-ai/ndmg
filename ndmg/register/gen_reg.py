#!/usr/bin/env python -W ignore::DeprecationWarning

# Copyright 2019 NeuroData (http://neurodata.io)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# register.py
# Repackaged for native space registrations by Derek Pisner on 2019-01-16
# Email: dpisner@utexas.edu.
# epi_register created by Eric Bridgeford.

from __future__ import print_function
import warnings
warnings.simplefilter("ignore")
import os
import nibabel as nib
import numpy as np
from nilearn.image import load_img, math_img, resample_img, mean_img, new_img_like, threshold_img
from dipy.core.gradients import gradient_table
from dipy.io import read_bvals_bvecs
try:
    FSLDIR = os.environ['FSLDIR']
except KeyError:
    print('FSLDIR environment variable not set!')
from ndmg.utils import gen_utils as mgu
from ndmg.utils import reg_utils as mgru
from dipy.tracking.streamline import Streamlines
from dipy.tracking.utils import move_streamlines

def transform_pts(pts, t_aff, t_warp, ref_img_path, ants_path, template_path, namer,
        out_volume="",output_space="lps_voxmm"):
    from scipy.io.matlab import savemat
    """
    return coordinates in 
    "ras_voxels" if you want to streamlines in ras ijk coordinates or 
    "lps_voxmm" if you want dsi studio streamline coordinates relative to the template
    """
    if not output_space in ("ras_voxels","lps_voxmm"):
        raise ValueError("Must specify output space")

    orig_dir = namer.dirs['tmp']['base']
    aattp_out = namer.dirs['tmp']['base'] + "/aattp.csv"
    warped_csv_out = namer.dirs['tmp']['base'] + "/warped_output.csv"
    transforms = "-t [" + str(t_aff) + ", 1] " + "-t " + str(t_warp)

    # Load the volume from DSI Studio
    ref_img = nib.load(ref_img_path)
    voxel_size = np.array(ref_img.header.get_zooms())
    extents = np.array(ref_img.shape)
    extents[-1] = 0

    # Convert the streamlines to voxel indices, then to ants points
    voxel_coords =  abs(extents - pts / voxel_size ) 
    ants_mult = np.array([voxel_size[0],voxel_size[1],voxel_size[2]])
    ants_coord = voxel_coords * ants_mult - voxel_size[0]
    ants_coord[:,0] = -ants_coord[:,0]
    ants_coord[:,1] = -ants_coord[:,1]

    # Save the ants coordinates to a csv, then warp them
    np.savetxt(warped_csv_out,np.hstack([ants_coord,np.zeros((ants_coord.shape[0],1))]),
              header="x,y,z,t",delimiter=",",fmt="%f")

    # Apply the trandforms to
    cmd = ants_path + "/antsApplyTransformsToPoints " + "-d 3 -i " + warped_csv_out + " -o " + aattp_out + " " + transforms
    os.system(cmd)

    # Load template to get output space
    template = nib.load(template_path)
    warped_affine = template.affine

    adjusted_affine = warped_affine.copy()
    adjusted_affine[0] = -adjusted_affine[0]
    adjusted_affine[1] = -adjusted_affine[1]
    print(adjusted_affine)

    ants_warped_coords = np.loadtxt(aattp_out, skiprows=1, delimiter=",")[:,:3]
    os.remove(aattp_out)
    to_transform = np.hstack([ants_warped_coords,np.ones((ants_warped_coords.shape[0],1))])
    new_voxels = (np.dot(np.linalg.inv(adjusted_affine),to_transform.T) + warped_affine[0,0])[:3]

    # Write out an image
    if out_volume:
        newdata = np.zeros(template.get_shape())
        ti, tj, tk = new_voxels.astype(np.int)
        newdata[ti,tj,tk] = 1
        warped_out = nib.Nifti1Image(newdata,warped_affine).to_filename(out_volume)
    os.chdir(orig_dir)
    if output_space == "ras_voxels":
        return new_voxels.astype(np.int).T

    elif output_space == "lps_voxmm":
        template_extents = template.get_shape()
        lps_voxels = new_voxels.copy()
 	lps_voxels[0] = template_extents[0] - lps_voxels[0]
	lps_voxels[1] = template_extents[1] - lps_voxels[1]
	print(lps_voxels)

        lps_voxmm = lps_voxels.T * np.array(template.header.get_zooms())[:3]
        return lps_voxmm


class Warp(object):
    def __init__(self,ants_path="",file_in="",file_out="",template_path="",t_aff="",t_warp="",ref_img_path="", namer=""):
        self.ants_path = ants_path
        self.file_in = file_in
        self.file_out = file_out
        self.template_path = template_path
        self.t_aff = t_aff
        self.t_warp = t_warp
      	self.ref_img_path = ref_img_path
      	self.namer = namer
    
    def streamlines(self):
        if not self.file_in.endswith((".trk",".trk.gz")):
            print ("File format currently unsupported.")
            return
        
        if self.ref_img_path == "":
            print ("Specify reference image path: .ref_img_path = path to reference image")
            return
            
        print ("Warping streamline file " + self.file_in)
        template = nib.load(self.template_path)
	warped_affine = template.affine
        dims = template.header.get_data_shape()
        template_extents = template.shape
        template_trk_header = np.array(('TRACK', 
        [dims[0],dims[1],dims[2]], 
        [warped_affine[0][0], warped_affine[1][1], warped_affine[2][2]], 
        [0.0, 0.0, 0.0], 0, ['', '', '', '', '', '', '', '', '', ''], 
        0, ['', '', '', '', '', '', '', '', '', ''], 
        [[1.0, 0.0, 0.0, 0.0], 
         [0.0, 1.0, 0.0, 0.0], 
         [0.0, 0.0, 1.0, 0.0], 
         [0.0, 0.0, 0.0, 1.0]], '', 'LPS', 'LPS', 
        [1.0, 0.0, 0.0, 0.0, 1.0, 0.0], 
        '', '', '', '', '', '', '', 10000, 2, 1000), 
         dtype=[('id_string', 'S6'), ('dim', '<i2', (3,)), 
             ('voxel_size', '<f4', (3,)), ('origin', '<f4', (3,)), 
             ('n_scalars', '<i2'), ('scalar_name', 'S20', (10,)), 
             ('n_properties', '<i2'), ('property_name', 'S20', (10,)), 
             ('vox_to_ras', '<f4', (4, 4)), ('reserved', 'S444'), 
             ('voxel_order', 'S4'), ('pad2', 'S4'), 
             ('image_orientation_patient', '<f4', (6,)), 
             ('pad1', 'S2'), ('invert_x', 'S1'), ('invert_y', 'S1'), 
             ('invert_z', 'S1'), ('swap_xy', 'S1'), ('swap_yz', 'S1'), 
             ('swap_zx', 'S1'), ('n_count', '<i4'), ('version', '<i4'), 
             ('hdr_size', '<i4')]
             )
            
        streams,hdr = nib.trackvis.read(self.file_in)
        offsets = []
        _streams = []
        for sl in streams:
            _streams.append(sl[0])
            offsets.append(_streams[-1].shape[0])
        allpoints = np.vstack(_streams)
        tx_points = transform_pts(allpoints, self.t_aff, self.t_warp, self.ref_img_path, self.ants_path, self.template_path, self.namer, output_space="lps_voxmm")
        offsets = np.cumsum([0]+offsets)
        starts = offsets[:-1]
        stops = offsets[1:]
        new_hdr = template_trk_header.copy()
        new_hdr["n_count"] = len(_streams)
        nib.trackvis.write(self.file_out,[(tx_points[a:b],None,None) for a,b in zip(starts,stops)],hdr_mapping=new_hdr)
        print ("Finished " + self.file_out) 
	
def transform_to_affine(streams, header, affine):
    rotation, scale = np.linalg.qr(affine)
    streams = move_streamlines(streams, rotation)
    scale[0:3, 0:3] = np.dot(scale[0:3, 0:3], np.diag(1. / header['voxel_sizes']))
    scale[0:3, 3] = abs(scale[0:3, 3])
    streams = move_streamlines(streams, scale)
    return streams

def direct_streamline_norm(streams, streams_mni, nodif_B0, namer):
    '''Greene, C., Cieslak, M., & Grafton, S. T. (2017). Effect of different spatial normalization approaches on tractography and structural brain networks. Network Neuroscience, 1-19.'''
    from ndmg.register.gen_reg import transform_to_affine
    template_path = '/usr/share/data/fsl-mni152-templates/MNI152_T1_2mm_brain.nii.gz'
    ants_path = '/opt/ants'
    
    cmd='antsRegistrationSyNQuick.sh -d 3 -f ' + template_path + ' -m ' + nodif_B0 + ' -o ' + namer.dirs['tmp']['base'] + '/'
    os.system(cmd)
    
    t_aff = namer.dirs['tmp']['base'] + '/0GenericAffine.mat'
    t_warp = namer.dirs['tmp']['base'] + '/1InverseWarp.nii.gz'

    nodif_B0_img = nib.load(nodif_B0)
    s_aff = nodif_B0_img.affine

    wS = Warp(ants_path, streams, streams_mni, template_path, t_aff, t_warp, nodif_B0, namer)
    wS.streamlines()

    s_aff[:3,3] = np.array([180, 0, 0])
    streamlines_mni = nib.streamlines.load(streams_mni)
    streamlines_mni_s = streamlines_mni.streamlines
    streamlines_trans = Streamlines(transform_to_affine(streamlines_mni_s, streamlines_mni.header, s_aff))
    streams_warp = streams_mni.split('.trk')[0] + '_warped.trk'
    tractogram = nib.streamlines.Tractogram(streamlines_trans, affine_to_rasmm=np.eye(4))
    trkfile = nib.streamlines.trk.TrkFile(tractogram, header=streamlines_mni.header)
    nib.streamlines.save(trkfile, streams_warp)
    print(streams_warp)
    return streams_warp


class dmri_reg(object):

    def __init__(self, namer, nodif_B0, nodif_B0_mask, t1w_in, vox_size, simple):
        self.simple = simple
        self.nodif_B0 = nodif_B0
	self.nodif_B0_mask = nodif_B0_mask
        self.t1w = t1w_in
        self.vox_size = vox_size
        self.t1w_name = 't1w'
        self.dwi_name = 'dwi'
	self.namer = namer
        self.t12mni_xfm_init = "{}/xfm_t1w2mni_init.mat".format(self.namer.dirs['tmp']['reg_m'])
	self.mni2t1_xfm_init = "{}/xfm_mni2t1w_init.mat".format(self.namer.dirs['tmp']['reg_m'])
        self.t12mni_xfm = "{}/xfm_t1w2mni.mat".format(self.namer.dirs['tmp']['reg_m'])
        self.mni2t1_xfm = "{}/xfm_mni2t1.mat".format(self.namer.dirs['tmp']['reg_m'])
        self.mni2t1w_warp = "{}/mni2t1w_warp.nii.gz".format(self.namer.dirs['tmp']['reg_a'])
        self.warp_t1w2mni = "{}/warp_t12mni.nii.gz".format(self.namer.dirs['tmp']['reg_a'])
        self.t1w2dwi = "{}/{}_in_dwi.nii.gz".format(self.namer.dirs['output']['reg_anat'], self.t1w_name)
        self.t1_aligned_mni = "{}/{}_aligned_mni.nii.gz".format(self.namer.dirs['output']['prep_anat'], self.t1w_name)
        self.t1w_brain = "{}/{}_brain.nii.gz".format(self.namer.dirs['output']['prep_anat'], self.t1w_name)
        self.dwi2t1w_xfm = "{}/dwi2t1w_xfm.mat".format(self.namer.dirs['tmp']['reg_m'])
        self.t1w2dwi_xfm = "{}/t1w2dwi_xfm.mat".format(self.namer.dirs['tmp']['reg_m'])
        self.t1w2dwi_bbr_xfm = "{}/t1w2dwi_bbr_xfm.mat".format(self.namer.dirs['tmp']['reg_m'])
        self.dwi2t1w_bbr_xfm = "{}/dwi2t1w_bbr_xfm.mat".format(self.namer.dirs['tmp']['reg_m'])
        self.t1wtissue2dwi_xfm = "{}/t1wtissue2dwi_xfm.mat".format(self.namer.dirs['tmp']['reg_m'])
        self.xfm_atlas2t1w_init = "{}/{}_xfm_atlas2t1w_init.mat".format(self.namer.dirs['tmp']['reg_m'], self.t1w_name)
        self.xfm_atlas2t1w = "{}/{}_xfm_atlas2t1w.mat".format(self.namer.dirs['tmp']['reg_m'], self.t1w_name)
        self.temp2dwi_xfm = "{}/{}_xfm_temp2dwi.mat".format(self.namer.dirs['tmp']['reg_m'], self.dwi_name)
        self.input_mni = "%s%s%s%s" % (FSLDIR, '/data/standard/MNI152_T1_', vox_size,'_brain.nii.gz')
        self.temp2dwi_xfm = "{}/{}_xfm_temp2dwi.mat".format(self.namer.dirs['tmp']['reg_m'], self.dwi_name)
        self.map_path = "{}/{}_seg".format(self.namer.dirs['output']['prep_anat'], self.t1w_name)
        self.wm_mask = "{}/{}_wm.nii.gz".format(self.namer.dirs['output']['prep_anat'], self.t1w_name)
	self.wm_mask_thr = "{}/{}_wm_thr.nii.gz".format(self.namer.dirs['output']['prep_anat'], self.t1w_name)
	self.wm_edge = "{}/{}_wm_edge.nii.gz".format(self.namer.dirs['tmp']['reg_a'], self.t1w_name)
        self.csf_mask = "{}/{}_csf.nii.gz".format(self.namer.dirs['output']['prep_anat'], self.t1w_name)
        self.gm_mask = "{}/{}_gm.nii.gz".format(self.namer.dirs['output']['prep_anat'], self.t1w_name)
        self.xfm_roi2mni_init = "{}/roi_2_mni.mat".format(self.namer.dirs['tmp']['reg_m'])
        self.lvent_out_file = "{}/LVentricle.nii.gz".format(self.namer.dirs['tmp']['reg_a'])
        self.rvent_out_file = "{}/RVentricle.nii.gz".format(self.namer.dirs['tmp']['reg_a'])
        self.mni_vent_loc = "{}/VentricleMask.nii.gz".format(self.namer.dirs['tmp']['reg_a'])
        self.csf_mask_dwi = "{}/{}_csf_mask_dwi.nii.gz".format(self.namer.dirs['output']['reg_anat'], self.t1w_name)
        self.gm_in_dwi = "{}/{}_gm_in_dwi.nii.gz".format(self.namer.dirs['output']['reg_anat'], self.t1w_name)
        self.wm_in_dwi = "{}/{}_wm_in_dwi.nii.gz".format(self.namer.dirs['output']['reg_anat'], self.t1w_name)
        self.csf_mask_dwi_bin = "{}/{}_csf_mask_dwi_bin.nii.gz".format(self.namer.dirs['tmp']['reg_a'], self.t1w_name)
        self.gm_in_dwi_bin = "{}/{}_gm_in_dwi_bin.nii.gz".format(self.namer.dirs['tmp']['reg_a'], self.t1w_name)
        self.wm_in_dwi_bin = "{}/{}_wm_in_dwi_bin.nii.gz".format(self.namer.dirs['tmp']['reg_a'], self.t1w_name)
        self.vent_mask_dwi = "{}/{}_vent_mask_dwi.nii.gz".format(self.namer.dirs['tmp']['reg_a'], self.t1w_name)
	self.vent_csf_in_dwi = "{}/{}_vent_csf_in_dwi.nii.gz".format(self.namer.dirs['tmp']['reg_a'], self.t1w_name)
        self.vent_mask_mni = "{}/vent_mask_mni.nii.gz".format(self.namer.dirs['tmp']['reg_a'])
        self.vent_mask_t1w = "{}/vent_mask_t1w.nii.gz".format(self.namer.dirs['tmp']['reg_a'])
        self.mni_atlas = "%s%s%s%s" % (FSLDIR, '/data/atlases/HarvardOxford/HarvardOxford-sub-prob-', vox_size, '.nii.gz')
        self.input_mni = "%s%s%s%s" % (FSLDIR, '/data/standard/MNI152_T1_', vox_size, '_brain.nii.gz')
	self.input_mni_mask = "%s%s%s%s" % (FSLDIR, '/data/standard/MNI152_T1_', vox_size, '_brain_mask.nii.gz')
	self.wm_gm_int_in_dwi = "{}/{}_wm_gm_int_in_dwi.nii.gz".format(namer.dirs['output']['reg_anat'], self.t1w_name)
	self.wm_gm_int_in_dwi_bin = "{}/{}_wm_gm_int_in_dwi_bin.nii.gz".format(namer.dirs['output']['reg_anat'], self.t1w_name)
	self.input_mni_sched = "%s%s" % (FSLDIR, '/etc/flirtsch/T1_2_MNI152_2mm.cnf')

    def gen_tissue(self):
        # BET needed for this, as afni 3dautomask only works on 4d volumes
        print('Extracting brain from raw T1w image...')
        mgru.t1w_skullstrip(self.t1w, self.t1w_brain)

        # Segment the t1w brain into probability maps
        self.maps = mgru.segment_t1w(self.t1w_brain, self.map_path)
	self.wm_mask = self.maps['wm_prob']
	self.gm_mask = self.maps['gm_prob']
	self.csf_mask = self.maps['csf_prob']

        # Check dimensions
	if self.vox_size == '1mm':
            self.zoom_set = (1.0, 1.0, 1.0)
        elif self.vox_size == '2mm':
            self.zoom_set = (2.0, 2.0, 2.0)
        else:
            raise ValueError('Voxel size not supported. Use 2mm or 1mm')

        self.t1w_brain = mgu.match_target_vox_res(self.t1w_brain, self.vox_size, self.namer, self.zoom_set, sens='t1w')
        self.wm_mask = mgu.match_target_vox_res(self.wm_mask, self.vox_size, self.namer, self.zoom_set, sens='t1w')
        self.gm_mask = mgu.match_target_vox_res(self.gm_mask, self.vox_size, self.namer, self.zoom_set, sens='t1w')
        self.csf_mask = mgu.match_target_vox_res(self.csf_mask, self.vox_size, self.namer, self.zoom_set, sens='t1w')

        # Threshold WM to binary in dwi space
        self.t_img = load_img(self.wm_mask)
        self.mask = math_img('img > 0.2', img=self.t_img)
        self.mask.to_filename(self.wm_mask_thr)

        # Extract wm edge
        cmd='fslmaths ' + self.wm_mask_thr + ' -edge -bin -mas ' + self.wm_mask_thr  + ' ' + self.wm_edge
        os.system(cmd)

        return

    def t1w2dwi_align(self):
        """
        alignment from T1w --> MNI and T1w_MNI --> DWI
        A function to perform self alignment. Uses a local optimisation
        cost function to get the two images close, and then uses bbr
        to obtain a good alignment of brain boundaries.
        Assumes input dwi is already preprocessed and brain extracted.
        """

        # Create linear transform/ initializer T1w-->MNI
        mgru.align(self.t1w_brain, self.input_mni, xfm=self.t12mni_xfm_init, bins=None, interp="spline", out=None, dof=12, cost='mutualinfo', searchrad=True)

        # Attempt non-linear registration of T1 to MNI template
        if self.simple is False:
            try:
                print('Running non-linear registration: T1w-->MNI ...')
                # Use FNIRT to nonlinearly align T1 to MNI template
                mgru.align_nonlinear(self.t1w_brain, self.input_mni, xfm=self.t12mni_xfm_init, out=self.t1_aligned_mni, warp=self.warp_t1w2mni, ref_mask=self.input_mni_mask, config=self.input_mni_sched)

                # Get warp from MNI -> T1
                mgru.inverse_warp(self.t1w_brain, self.mni2t1w_warp, self.warp_t1w2mni)

		# Get mat from MNI -> T1
		cmd = 'convert_xfm -omat ' + self.mni2t1_xfm_init + ' -inverse ' + self.t12mni_xfm_init
        	print(cmd)
        	os.system(cmd)

            except RuntimeError('Error: FNIRT failed!'):
                pass
        else:
            # Falling back to linear registration
            mgru.align(self.t1w_brain, self.input_mni, xfm=self.t12mni_xfm, init=self.t12mni_xfm_init, bins=None, dof=12, cost='mutualinfo', searchrad=True, interp="spline", out=self.t1_aligned_mni, sch=None)

        # Align T1w-->DWI
        mgru.align(self.nodif_B0, self.t1w_brain, xfm=self.t1w2dwi_xfm, bins=None, interp="spline", dof=6, cost='mutualinfo', out=None, searchrad=True, sch=None)
        cmd = 'convert_xfm -omat ' + self.dwi2t1w_xfm + ' -inverse ' + self.t1w2dwi_xfm
	print(cmd)
        os.system(cmd)

        if self.simple is False:
            # Flirt bbr
            try:
		print('Running FLIRT BBR registration: T1w-->DWI ...')
                mgru.align(self.nodif_B0, self.t1w_brain, wmseg=self.wm_edge, xfm=self.dwi2t1w_bbr_xfm, init=self.dwi2t1w_xfm, bins=256, dof=7, searchrad=True, interp="spline", out=None, cost='bbr', finesearch=5, sch="${FSLDIR}/etc/flirtsch/bbr.sch")
                cmd = 'convert_xfm -omat ' + self.t1w2dwi_bbr_xfm + ' -inverse ' + self.dwi2t1w_bbr_xfm
                os.system(cmd)

                # Apply the alignment
                mgru.align(self.t1w_brain, self.nodif_B0, init=self.t1w2dwi_bbr_xfm, xfm=self.t1wtissue2dwi_xfm, bins=None, interp="spline", dof=7, cost='mutualinfo', out=self.t1w2dwi, searchrad=True, sch=None)
            except RuntimeError('Error: FLIRT BBR failed!'):
                pass
        else:
            # Apply the alignment
            mgru.align(self.t1w_brain, self.nodif_B0, init=self.t1w2dwi_xfm, xfm=self.t1wtissue2dwi_xfm, bins=None, interp="spline", dof=6, cost='mutualinfo', out=self.t1w2dwi, searchrad=True, sch=None)

        return

    def atlas2t1w2dwi_align(self, atlas, dsn=True):
        """
        alignment from atlas --> T1 --> dwi
        A function to perform atlas alignment.
        Tries nonlinear registration first, and if that fails,
        does a linear registration instead.
        NOTE: for this to work, must first have called t1w2dwi_align.
        """
        self.atlas = atlas
        self.atlas_name = self.atlas.split('/')[-1].split('.')[0]
        self.aligned_atlas_t1mni = "{}/{}_aligned_atlas_t1w_mni.nii.gz".format(self.namer.dirs['tmp']['reg_a'], self.atlas_name)
        self.aligned_atlas_skull = "{}/{}_aligned_atlas_skull.nii.gz".format(self.namer.dirs['tmp']['reg_a'], self.atlas_name)
        self.dwi_aligned_atlas = "{}/{}_aligned_atlas.nii.gz".format(self.namer.dirs['output']['reg_anat'], self.atlas_name)
        #self.dwi_aligned_atlas_mask = "{}/{}_aligned_atlas_mask.nii.gz".format(self.namer.dirs['tmp']['reg_a'], self.atlas_name)

        mgru.align(self.atlas, self.t1_aligned_mni, init=None, xfm=None, out=self.aligned_atlas_t1mni, dof=12, searchrad=True, interp="nearestneighbour", cost='mutualinfo')

        if ((self.simple is False) and (dsn is False)):
            try:
		# Apply warp resulting from the inverse of T1w-->MNI created earlier
                mgru.apply_warp(self.t1w_brain, self.aligned_atlas_t1mni, self.aligned_atlas_skull, warp=self.mni2t1w_warp, interp='nn', sup=True)

                # Apply transform to dwi space
		mgru.align(self.aligned_atlas_skull, self.nodif_B0, init=self.t1wtissue2dwi_xfm, xfm=None, out=self.dwi_aligned_atlas, dof=6, searchrad=True, interp="nearestneighbour", cost='mutualinfo')
            except:
                print("Warning: Atlas is not in correct dimensions, or input is low quality,\nusing linear template registration.")
                # Create transform to align atlas to T1w using flirt
                mgru.align(self.atlas, self.t1w_brain, xfm=self.xfm_atlas2t1w_init, init=None, bins=None, dof=6, cost='mutualinfo', searchrad=True, interp="spline", out=None, sch=None)
                mgru.align(self.atlas, self.t1_aligned_mni, xfm=self.xfm_atlas2t1w, out=None, dof=6, searchrad=True, bins=None, interp="spline", cost='mutualinfo', init=self.xfm_atlas2t1w_init)

                # Combine our linear transform from t1w to template with our transform from dwi to t1w space to get a transform from atlas ->(-> t1w ->)-> dwi
                mgru.combine_xfms(self.xfm_atlas2t1w, self.t1wtissue2dwi_xfm, self.temp2dwi_xfm)

                # Apply linear transformation from template to dwi space
                mgru.applyxfm(self.nodif_B0, self.atlas, self.temp2dwi_xfm, self.dwi_aligned_atlas)
        elif dsn is False:
            # Create transform to align atlas to T1w using flirt
            mgru.align(self.atlas, self.t1w_brain, xfm=self.xfm_atlas2t1w_init, init=None, bins=None, dof=6, cost='mutualinfo', searchrad=None, interp="spline", out=None, sch=None)
            mgru.align(self.atlas, self.t1w_brain, xfm=self.xfm_atlas2t1w, out=None, dof=6, searchrad=True, bins=None, interp="spline", cost='mutualinfo', init=self.xfm_atlas2t1w_init)

            # Combine our linear transform from t1w to template with our transform from dwi to t1w space to get a transform from atlas ->(-> t1w ->)-> dwi
            mgru.combine_xfms(self.xfm_atlas2t1w, self.t1wtissue2dwi_xfm, self.temp2dwi_xfm)

            # Apply linear transformation from template to dwi space
            mgru.applyxfm(self.nodif_B0, self.atlas, self.temp2dwi_xfm, self.dwi_aligned_atlas)
        else:
	    pass

        # Set intensities to int
	if dsn is False:
            self.atlas_img = nib.load(self.dwi_aligned_atlas)
        else:
	    self.atlas_img = nib.load(self.aligned_atlas_t1mni)
        self.atlas_data = self.atlas_img.get_data().astype('int')
	node_num = len(np.unique(self.atlas_data))
        self.atlas_data[self.atlas_data>node_num] = 0

	if dsn is False:	
	    t_img = load_img(self.wm_gm_int_in_dwi)
	    mask = math_img('img > 0', img=t_img)
	    mask.to_filename(self.wm_gm_int_in_dwi_bin)

            nib.save(nib.Nifti1Image(self.atlas_data.astype(np.int32), affine=self.atlas_img.affine, header=self.atlas_img.header), self.dwi_aligned_atlas)
            cmd='fslmaths ' + self.dwi_aligned_atlas + ' -mas ' + self.nodif_B0_mask + ' -mas ' + self.wm_gm_int_in_dwi_bin + ' ' + self.dwi_aligned_atlas
            os.system(cmd)
	    return self.dwi_aligned_atlas
	else:
            nib.save(nib.Nifti1Image(self.atlas_data.astype(np.int32), affine=self.atlas_img.affine, header=self.atlas_img.header), self.aligned_atlas_t1mni)
	    return self.aligned_atlas_t1mni


    def tissue2dwi_align(self):
        """
        alignment of ventricle ROI's from MNI space --> dwi and
        CSF from T1w space --> dwi
        A function to generate and perform dwi space alignment of avoidance/waypoint masks for tractography.
        First creates ventricle ROI. Then creates transforms from stock MNI template to dwi space.
        NOTE: for this to work, must first have called both t1w2dwi_align and atlas2t1w2dwi_align.
        """

        # Create MNI-space ventricle mask
        print('Creating MNI-space ventricle ROI...')
        if not os.path.isfile(self.mni_atlas):
            raise ValueError('FSL atlas for ventricle reference not found!')
        cmd='fslroi ' + self.mni_atlas + ' ' + self.rvent_out_file + ' 2 1'
        os.system(cmd)
        cmd='fslroi ' + self.mni_atlas + ' ' + self.lvent_out_file + ' 13 1'
        os.system(cmd)
        self.args = "%s%s%s" % (' -add ', self.rvent_out_file, ' -thr 0.1 -bin ')
        cmd='fslmaths ' + self.lvent_out_file + self.args + self.mni_vent_loc
        os.system(cmd)

        # Create transform to MNI atlas to T1w using flirt. This will be use to transform the ventricles to dwi space.
        mgru.align(self.mni_atlas, self.input_mni, xfm=self.xfm_roi2mni_init, init=None, bins=None, dof=6, cost='mutualinfo', searchrad=True, interp="spline", out=None)

        # Create transform to align roi to mni and T1w using flirt
        mgru.applyxfm(self.input_mni, self.mni_vent_loc, self.xfm_roi2mni_init, self.vent_mask_mni)

        if self.simple is False:
            # Apply warp resulting from the inverse MNI->T1w created earlier
            mgru.apply_warp(self.t1w_brain, self.vent_mask_mni, self.vent_mask_t1w, warp=self.mni2t1w_warp, interp='nn', sup=True)
            
	# Applyxfm tissue maps to dwi space
        mgru.applyxfm(self.nodif_B0, self.vent_mask_t1w, self.t1wtissue2dwi_xfm, self.vent_mask_dwi)
        mgru.applyxfm(self.nodif_B0, self.csf_mask, self.t1wtissue2dwi_xfm, self.csf_mask_dwi)
        mgru.applyxfm(self.nodif_B0, self.gm_mask, self.t1wtissue2dwi_xfm, self.gm_in_dwi)
        mgru.applyxfm(self.nodif_B0, self.wm_mask, self.t1wtissue2dwi_xfm, self.wm_in_dwi)	

	# Threshold WM to binary in dwi space
	thr_img = nib.load(self.wm_in_dwi)                                                                            
	thr_img.get_data()[thr_img.get_data() < 0.2] = 0                                                              
	nib.save(thr_img, self.wm_in_dwi_bin)  

	# Threshold GM to binary in dwi space
        thr_img = nib.load(self.gm_in_dwi)                                                                            
        thr_img.get_data()[thr_img.get_data() < 0.2] = 0
        nib.save(thr_img, self.gm_in_dwi_bin)

	# Threshold CSF to binary in dwi space
        thr_img = nib.load(self.csf_mask_dwi)
        thr_img.get_data()[thr_img.get_data() < 0.9] = 0
        nib.save(thr_img, self.csf_mask_dwi)

        # Threshold WM to binary in dwi space
        self.t_img = load_img(self.wm_in_dwi_bin)
        self.mask = math_img('img > 0', img=self.t_img)
        self.mask.to_filename(self.wm_in_dwi_bin)

        # Threshold GM to binary in dwi space
        self.t_img = load_img(self.gm_in_dwi_bin)
        self.mask = math_img('img > 0', img=self.t_img)
        self.mask.to_filename(self.gm_in_dwi_bin)

        # Threshold CSF to binary in dwi space
        self.t_img = load_img(self.csf_mask_dwi)
        self.mask = math_img('img > 0', img=self.t_img)
        self.mask.to_filename(self.csf_mask_dwi_bin)

        # Create ventricular CSF mask
        print('Creating ventricular CSF mask...')
	cmd='fslmaths ' + self.vent_mask_dwi + ' -kernel sphere 10 -ero -bin ' + self.vent_mask_dwi
	os.system(cmd)
        cmd='fslmaths ' + self.csf_mask_dwi + ' -add ' + self.vent_mask_dwi + ' -bin ' + self.vent_csf_in_dwi
        os.system(cmd)

	# Create gm-wm interface image
        cmd = 'fslmaths ' + self.gm_in_dwi_bin + ' -mul ' + self.wm_in_dwi_bin + ' -mas ' + self.nodif_B0_mask + ' -bin ' + self.wm_gm_int_in_dwi
        os.system(cmd)

        return

class dmri_reg_old(object):

    def __init__(self, dwi, gtab, t1w, atlas, aligned_dwi, namer, clean=False):
	"""
        Aligns two images and stores the transform between them
        **Positional Arguments:**
                dwi:
                    - Input impage to be aligned as a nifti image file
                gtab:
                    - object containing gradient directions and strength
                t1w:
                    - Intermediate image being aligned to as a nifti image file
                atlas:
                    - Terminal image being aligned to as a nifti image file
                aligned_dwi:
                    - Aligned output dwi image as a nifti image file
                outdir:
                    - Directory for derivatives to be stored
        """
	self.dwi = dwi
	self.t1w = t1w
	self.atlas = atlas
	self.gtab = gtab
	self.aligned_dwi = aligned_dwi
	self.namer = namer

	# Creates names for all intermediate files used
        self.dwi_name = mgu.get_filename(dwi)
        self.t1w_name = mgu.get_filename(t1w)
        self.atlas_name = mgu.get_filename(atlas)

        self.temp_aligned = "{}/temp_aligned.nii.gz".format(self.namer.dirs['tmp']['reg_a'])
	self.temp_aligned2 = "{}/temp_aligned2.nii.gz".format(self.namer.dirs['tmp']['reg_a'])
        self.b0 = "{}/b0.nii.gz".format(self.namer.dirs['tmp']['reg_a'])
        self.t1w_brain = "{}/t1w_brain.nii.gz".format(self.namer.dirs['tmp']['reg_a'])
        self.xfm = "{}/{}_{}_xfm.mat".format(self.namer.dirs['tmp']['reg_m'], self.t1w_name, self.atlas_name)
	
    def dwi2atlas(self, clean=False):
        # Loads DTI image in as data and extracts B0 volume
        self.dwi_im = nib.load(self.dwi)
	self.b0s = np.where(self.gtab.b0s_mask)[0]
        self.b0_im = np.squeeze(self.dwi_im.get_data()[:, :, :, self.b0s[0]])  # if more than 1, use first

        # Wraps B0 volume in new nifti image
        self.b0_head = self.dwi_im.header
        self.b0_head.set_data_shape(self.b0_head.get_data_shape()[0:3])
        self.b0_out = nib.Nifti1Image(self.b0_im, affine=self.dwi_im.affine, header=self.b0_head)
        self.b0_out.update_header()
        nib.save(self.b0_out, self.b0)

        # Applies skull stripping to T1 volume, then EPI alignment to T1
        mgru.extract_brain(self.t1w, self.t1w_brain, ' -B')
        mgru.align_epi(self.dwi, self.t1w, self.t1w_brain, self.temp_aligned)

        # Applies linear registration from T1 to template
        mgru.align(self.t1w, self.atlas, self.xfm)

        # Applies combined transform to dwi image volume
        mgru.applyxfm(self.atlas, self.temp_aligned, self.xfm, self.temp_aligned2)
	mgru.resample(self.temp_aligned2, self.aligned_dwi, self.atlas)

        if clean:
            cmd = "rm -f {} {} {} {} {}*".format(self.dwi, self.temp_aligned, self.b0,
                                                self.xfm, self.t1w_name)
            print("Cleaning temporary registration files...")
            mgu.execute_cmd(cmd)


class epi_register(object):
    def __init__(self, epi, t1w, t1w_brain, atlas, atlas_brain, atlas_mask,
                 aligned_epi, aligned_t1w, namer):
        """
        A class to change brain spaces from a subject's epi sequence
        to that of a standardized atlas.
        **Positional Arguments:**
            epi:
                - the path of the preprocessed fmri image.
            t1w:
                - the path of the T1w scan.
            t1w_brain:
                - the path of the brain extracted T1w scan.
            atlas:
                - the template atlas.
            atlas_brain:
                - the template brain.
            atlas_mask:
                - the template mask.
            aligned_epi:
                - the name of the aligned fmri scan to produce.
            aligned_t1w:
                - the name of the aligned anatomical scan to produce
            namer:
                - naming utility.
        """
        super(register, self).__init__()

        # for naming temporary files
        self.epi_name = mgu.get_filename(epi)
        self.t1w_name = "{}_T1w".format(namer.__suball__)
        self.atlas_name = mgu.get_filename(atlas)
        self.namer = namer
        self.outdir = namer.dirs['tmp']

        # our basic dependencies
        self.epi = epi
        self.t1w = t1w
        self.t1w_brain = t1w_brain
        self.atlas = atlas
        self.atlas_brain = atlas_brain
        self.atlas_mask = atlas_mask
        self.taligned_epi = aligned_epi
        self.taligned_t1w = aligned_t1w
        t1w_skull = "{}/{}_temp-aligned_skull.nii.gz"
        self.taligned_t1w_skull = t1w_skull.format(self.outdir['reg_a'],
                                                   self.t1w_name)
        # strategies for qa later
        self.sreg_strat = None
        self.treg_strat = None

        # if we do bbr, then we will need a wm mask, so store for qa
        self.wm_mask = None

        if sum(nib.load(t1w).header.get_zooms()) <= 6:
            self.simple = False
        else:
            self.simple = True  # if the input is poor
        # name intermediates for self-alignment
        self.saligned_xfm = "{}/{}_self-aligned.mat".format(
            self.outdir['reg_m'],
            self.epi_name)
        pass

    def self_align(self):
        """
        A function to perform self alignment. Uses a local optimisation
        cost function to get the two images close, and then uses bbr
        to obtain a good alignment of brain boundaries.
        """
        xfm_init1 = "{}/{}_xfm_epi2t1w_init1.mat".format(self.outdir['reg_m'],
                                                         self.epi_name)
        xfm_init2 = "{}/{}_xfm_epi2t1w_init2.mat".format(self.outdir['reg_m'],
                                                         self.epi_name)
        epi_init = "{}/{}_local.nii.gz".format(self.outdir['reg_m'],
                                               self.epi_name)

        # perform an initial alignment with a gentle translational guess
        # note that this schedule file only adjusts such that the x, y, z
        # params between the epi and the t1w brain are optimal
        mgru.align(self.epi, self.t1w_brain, xfm=xfm_init1, bins=None,
                   dof=None, cost=None, searchrad=None,
                   sch="${FSLDIR}/etc/flirtsch/sch3Dtrans_3dof")
        # perform a near local-only registration, which looks for local
        # fits of the voxels and will improve our registration if our
        # image is for instance cut off somewhere with simple3d
        # make sure to initialize with our translationally optimal fit
        mgru.align(self.epi, self.t1w_brain, xfm=xfm_init2, init=xfm_init1,
                   bins=None, dof=None, cost=None, searchrad=None,
                   out=epi_init, sch="${FSLDIR}/etc/flirtsch/simple3D.sch")

        # if we have a quality T1w image (resolution < 2x2x2) we will get
        # a decent segmentation, and then we can use bbr from flirt
        if not self.simple:
            xfm_init3 = "{}/{}_xfm_epi2t1w.mat".format(self.outdir['reg_m'],
                                                       self.epi_name)
            xfm_bbr = "{}/{}_xfm_bbr.mat".format(self.outdir['reg_m'],
                                                 self.epi_name)
            epi_bbr = "{}/{}_bbr.nii.gz".format(self.outdir['reg_m'],
                                                self.epi_name)
            # use a 6 dof registration with near-local initializer
            mgru.align(self.epi, self.t1w_brain, xfm=xfm_init3,
                       init=xfm_init2, bins=None, dof=6, cost=None,
                       searchrad=None, sch=None)
            # segment the t1w brain into probability maps
            map_path = "{}/{}_seg".format(self.outdir['reg_a'],
                                          self.t1w_name)
            maps = mgnu.segment_t1w(self.t1w_brain, map_path)
            wm_mask = "{}/{}_wmm.nii.gz".format(self.outdir['reg_a'],
                                                self.t1w_name)
            self.wm_mask = wm_mask
            # use the probability maps to extract white matter mask
            mgnu.probmap2mask(maps['wm_prob'], wm_mask, 0.5)
            # perform flirt with boundary-based registration, using the
            # white matter mask to improve registration quality
            mgru.align(self.epi, self.t1w, xfm=xfm_bbr, wmseg=wm_mask,
                       out=epi_bbr, init=xfm_init3, interp="spline",
                       sch="${FSLDIR}/etc/flirtsch/bbr.sch")
            # store the 3d image to use as our qa image, but keep the transform
            # so that we don't have to multiply yet
            self.sreg_xfm = xfm_bbr
            self.sreg_brain = epi_bbr
            self.sreg_strat = 'epireg'  # store the strategy
        else:
            # if we have low quality T1w image, we will not be able
            # to segment, so do not use bbr
            print("Warning: BBR self registration not "
                  "attempted, as input is low quality.")
            # use the 3d image and transform from the near-local registration
            # instead
            self.sreg_xfm = xfm_init2
            self.sreg_brain = epi_init
            self.sreg_strat = 'flirt'
        # have to use bet for this, as afni 3dautomask
        # only works on 4d volumes
        mgru.extract_brain(self.sreg_brain, self.sreg_brain,
                           opts='-f 0.3 -R')
        pass

    def template_align(self):
        """
        A function to perform template alignment. First tries nonlinear
        registration, and if that does not work effectively, does a linear
        registration instead.
        NOTE: for this to work, must first have called self-align.
        """
        xfm_t1w2temp_init = "{}/{}_xfm_t1w2temp_init.mat".format(
            self.outdir['reg_a'],
            self.t1w_name
        )
        xfm_t1w2temp = "{}/{}_xfm_t1w2temp.mat".format(self.outdir['reg_a'],
                                                       self.t1w_name)

        # linear registration initializer with local optimisation in
        # case our brain extraction is poor to give our 12 dof flirt
        # a better starting point
        # if brain extraction fails, a 12 dof registration will perform
        # horribly since the brain will be an odd shape, leading to total
        # failure. The idea is that local optimisation looks to essentially
        # align "regions" of the brain, and as such, will not add unnecessary
        # stretching if the brain is not the correct shape, potentially
        # leading the 12 dof registration to not totally distort the image
        mgru.align(self.t1w_brain, self.atlas_brain, xfm=xfm_t1w2temp_init,
                   init=None, bins=None, dof=None, cost=None, searchrad=None,
                   out=None, sch="${FSLDIR}/etc/flirtsch/sch3Dtrans_3dof")

        # linear registration from t1 space to atlas space with a 12 dof
        # linear registration to serve as our initializer
        mgru.align(self.t1w_brain, self.atlas_brain, xfm=xfm_t1w2temp,
                   out=None, dof=12, searchrad=True, bins=256, interp="spline",
                   wmseg=None, init=xfm_t1w2temp_init)

        self.epi_aligned_skull = "{}/{}_temp-aligned_skull.nii.gz".format(
            self.outdir['reg_m'],
            self.epi_name
        )  # template-aligned with skull
        # if the atlas is MNI 2mm, then we have a config file for it
        if (nib.load(self.atlas).get_data().shape in [(91, 109, 91)] and
                (self.simple is False)):
            warp_t1w2temp = "{}/{}_warp_t1w2temp.nii.gz".format(
                self.outdir['reg_a'],
                self.epi_name
            )  # to store the template warp
            # use FNIRT to nonlinearly align from the t1w to the
            # template space, using the 12 dof transform as an initializer
            mgru.align_nonlinear(self.t1w, self.atlas, xfm_t1w2temp,
                                 warp_t1w2temp, mask=self.atlas_mask)
            # apply the warp from the epi to the atlas space by first using
            # the linear transform from the epi to the template space
            mgru.apply_warp(self.epi, self.atlas, self.epi_aligned_skull,
                            warp=warp_t1w2temp, xfm=self.sreg_xfm)
            # apply the warp from the t1w to the atlas space
            mgru.apply_warp(self.t1w, self.atlas, self.taligned_t1w_skull,
                            warp=warp_t1w2temp)
            self.treg_strat = 'fnirt'  # strategy details
        else:
            # if we dont have 2mm mni or a low quality t1w, FNIRT is unsuitable
            print
            "Atlas is not 2mm MNI, or input is low quality."
            print
            "Using linear template registration."

            xfm_epi2temp = "{}/{}_xfm_epi2temp.mat".format(
                self.outdir['reg_m'],
                self.epi_name
            )
            # just combine our 12 dof linear transform from t1w to template
            # with our transform from epi to t1w space to get a transform
            # from epi ->(-> t1w ->)-> temp space (epi -> temp)
            mgru.combine_xfms(xfm_t1w2temp, self.sreg_xfm, xfm_epi2temp)
            # apply linear transformation from epi to template space
            mgru.applyxfm(self.epi, self.atlas, xfm_epi2temp,
                          self.epi_aligned_skull, interp='spline')
            # apply 12 dof linear transform from t1w to template space
            mgru.apply_warp(self.t1w, self.atlas, self.taligned_t1w_skull,
                            xfm=xfm_t1w2temp)
            self.treg_strat = 'flirt'  # strategy
        # use BET to extract brain from our epi volume
        mgru.extract_brain(self.epi_aligned_skull, self.taligned_epi,
                           opts='-F')

        # use AFNI to extract brain from our t1w volume
        mgru.extract_t1w_brain(self.taligned_t1w_skull, self.taligned_t1w,
                               self.outdir['reg_a'])
        pass
