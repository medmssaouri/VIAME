import argparse
import glob
import itertools as itt

import numpy as np
import scipy.optimize
from skimage import (
    io as skio,
    transform as sktr,
)
import tqdm

def read_homog_file(path):
    """Read a homography output file into an Nx3x3 array.
    Coordinate order is Y, X, Z.
    Also returns the reference frame for each frame.

    """
    with open(path) as f:
        # "start" will contain the starting index
        start = None
        result = []
        refs = []
        for i, line in enumerate(f):
            *matrix, fromf, tof = line.split()
            if start is None:
                start = int(fromf)
            assert len(matrix) == 9
            assert int(fromf) == i + start
            result.append(list(map(float, matrix)))
            refs.append(int(tof))
    swap_xy = np.array([[0, 1, 0], [1, 0, 0], [0, 0, 1]])
    result = swap_xy @ np.array(result).reshape((-1, 3, 3)) @ swap_xy
    return result, np.array(refs)

def transform_homog(homog, coords):
    """Signature (n+1, n+1), n -> n"""
    ones = np.ones(coords.shape[:-1] + (1,), dtype=coords.dtype)
    coords = np.concatenate((coords, ones), axis=-1)[..., np.newaxis]
    tcoords = homog @ coords
    tcoords = np.squeeze(tcoords, -1)
    return tcoords[..., :-1] / tcoords[..., -1:]

def get_image_box(im_size):
    y, x = im_size
    y -= 1; x -= 1
    return np.array([[0, 0], [y, 0], [0, x], [y, x]])

def score_homog(homog, im_size):
    """Signature (3, 3) -> () (fixing size as a pair)"""
    box = get_image_box(im_size)
    def get_dists(x):
        """Signature (n, m) -> (n, n)"""
        diffs = np.expand_dims(x, -3) - np.expand_dims(x, -2)
        return (diffs ** 2).sum(-1) ** .5
    tbox = transform_homog(np.expand_dims(homog, -3), box)
    return ((get_dists(tbox) - get_dists(box)) ** 2).sum((-1, -2))

def optimize_homog_fit(homogs, im_size):
    """Return a homography that, when applied after the provided ndarray
    of homographies, minimizes the distortion of images of the given
    size

    """
    def embed(x):
        result = np.empty((3, 3), dtype=x.dtype)
        result.flat[:-1] = x
        result[2, 2] = 1
        return result
    def score(x):
        return score_homog(embed(x) @ homogs, im_size).sum()
    result = scipy.optimize.minimize(
        score, np.eye(3).flat[:-1], method='Nelder-Mead',
    )
    if result.success:
        return embed(result.x)
    else:
        raise RuntimeError(
            "Optimization failed with the message: " + result.message,
        )

def get_extreme_coordinates(homogs, im_size):
    """Return a pair of the UL and BR coordinates"""
    box = get_image_box(im_size)
    transformed = transform_homog(homogs[:, np.newaxis], box)
    min_yx = np.floor(transformed.min((0, 1))).astype(int)
    max_yx = np.ceil(transformed.max((0, 1))).astype(int)
    return tuple(min_yx), tuple(max_yx)

def translator(offset):
    """Return a matrix that translates homogeneous coordinates by the
    given offset.

    """
    result = np.identity(len(offset) + 1)
    result[:-1, -1] = offset
    return result

def paste(dest, src, src_to_dest):
    """Copy src into dest, transformed as described by src_to_dest, a
    projective matrix that maps a (2D homogeneous) coordinate in src
    to one in dest.

    """
    # Sanity checks
    assert src.ndim == 3 and src.shape[2] in (3, 4)
    if dest.dtype != np.uint8 or src.dtype != np.uint8:
        raise ValueError("Only 8-bit (per channel) images supported")
    bbox = get_image_box(src.shape[:2])
    trans_bbox = transform_homog(src_to_dest, bbox)
    trans_ul, trans_br = trans_bbox.min(0), trans_bbox.max(0)
    # Round outward
    trans_ul = np.floor(trans_ul).astype(int)
    trans_br = np.ceil(trans_br).astype(int)
    # Adjust and create
    src_to_dest_adj = translator(-trans_ul) @ src_to_dest
    dest_to_src_adj = np.linalg.inv(src_to_dest_adj)
    # "warp" expects an X,Y coordinate order
    swap_xy = np.array([[0, 1, 0], [1, 0, 0], [0, 0, 1]])
    dest_to_src_adj = swap_xy @ dest_to_src_adj @ swap_xy
    oshape = tuple(trans_br - trans_ul + 1)

    mask = sktr.warp(
        np.ones(src.shape[:2]), dest_to_src_adj, output_shape=oshape,
    ) > 0.5
    trans = sktr.warp(
        src, dest_to_src_adj, output_shape=oshape,
    )
    # Convert everything back to uint8 (warp converts to double)
    trans = (trans * 255).round().astype(np.uint8)

    dest_slice = dest[tuple(slice(ul, br + 1) for ul, br in zip(trans_ul, trans_br))]
    np.copyto(dest_slice, trans, where=mask[..., np.newaxis])

def paste_many(homogs, ims, im0):
    """Given a sequence of homographies, an iterable of images, and a
    template image, produce a mosaic image

    """
    im_size = im0.shape[:2]
    ul, br = get_extreme_coordinates(homogs, im_size)
    # XXX The extra + 1 is a hack
    dest = np.zeros(tuple(np.array(br) - ul + 1 + 1) + (im0.shape[2],), dtype=im0.dtype)
    for hom, im in zip(homogs, ims):
        assert im.shape[:2] == im_size
        hom = translator(tuple(-x for x in ul)) @ hom
        paste(dest, im, hom)
    return dest

def peek_iterable(it):
    it = iter(it)
    x = next(it)
    return x, itt.chain([x], it)

def main(out_file, homog_file, image_glob, frames=None, start=None, stop=None, step=None, optimize_fit=None):
    image_files = sorted(glob.iglob(image_glob))[start:stop]
    homogs, refs = (x[start:stop] for x in read_homog_file(homog_file))
    length = min(len(image_files), len(homogs))
    if (frames is None) == (step is None):
        raise ValueError("Exactly one of frames and step must be specified")
    if frames is not None:
        frame_numbers = [(length - 1) * i // (frames - 1) for i in range(frames)]
    else:
        frame_numbers = range(0, length, step)
    if len(np.unique(refs[frame_numbers])) > 1:
        raise ValueError("Requested frames do not all have the same reference")
    images = (skio.imread(image_files[i]) for i in tqdm.tqdm(frame_numbers))
    im0, images = peek_iterable(images)
    rel_homogs = homogs[frame_numbers]
    if optimize_fit:
        rel_homogs = np.linalg.inv(rel_homogs[0]) @ rel_homogs
        fit_homog = optimize_homog_fit(rel_homogs, im0.shape[:2])
        rel_homogs = fit_homog @ rel_homogs
    skio.imsave(out_file, paste_many(rel_homogs, images, im0))

def create_parser():
    p = argparse.ArgumentParser()
    p.add_argument('out_file', help='Path to output file')
    p.add_argument('homog_file', help='Path to homography file')
    p.add_argument('image_glob', help='(Quoted) glob for input images')
    p.add_argument('--frames', type=int, help='Number of frames represented in output')
    p.add_argument('--start', type=int, metavar='N', help='Ignore first N frames')
    p.add_argument('--stop', type=int, metavar='N', help='Ignore frames after the Nth')
    p.add_argument('--step', type=int, metavar='N', help='Write every Nth frame')
    p.add_argument('--optimize-fit', action='store_true', help='Apply an additional transformation to all images to minimize distortion')
    return p

if __name__ == '__main__':
    main(**vars(create_parser().parse_args()))
