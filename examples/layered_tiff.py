# psdtags/examples/layered_tiff.py

"""Create layered TIFF file from individual layer images.

This Python script creates a layered TIFF file from individual layer images
using the `psdtags <https://pypi.org/project/psdtags/>`_,
`tifffile <https://pypi.org/project/tifffile/>`_, and
`imagecodecs <https://pypi.org/project/imagecodecs/>`_ libraries.

See https://github.com/cgohlke/psdtags/issues/4

"""

from __future__ import annotations

import numpy
import imagecodecs
import tifffile

from psdtags import (
    __version__,
    PsdBlendMode,
    PsdChannel,
    PsdChannelId,
    PsdClippingType,
    PsdColorSpaceType,
    PsdCompressionType,
    PsdEmpty,
    PsdFilterMask,
    PsdFormat,
    PsdKey,
    PsdLayer,
    PsdLayerFlag,
    PsdLayerMask,
    PsdLayers,
    PsdRectangle,
    PsdString,
    PsdUserMask,
    TiffImageSourceData,
    overlay,
)

# canvas height and width
shape = (256, 256)

# use a white, opaque background that covers the canvas
background = numpy.empty((*shape, 4), numpy.uint8)
background.fill(255)

# read individual layer images from files
reflection: numpy.ndarray = imagecodecs.imread('reflection.png')
shadow: numpy.ndarray = imagecodecs.imread('shadow.png')
product: numpy.ndarray = imagecodecs.imread('product.png')

# positions of layers in canvas
background_offset = (0, 0)
reflection_offset = (168, 80)
shadow_offset = (164, 86)
product_offset = (79, 83)

# create the ImageSourceData structure for the layered TIFF
image_source_data = TiffImageSourceData(
    name='Layered TIFF',
    psdformat=PsdFormat.LE32BIT,
    layers=PsdLayers(
        key=PsdKey.LAYER,
        has_transparency=False,
        layers=[
            PsdLayer(
                name='Background',
                rectangle=PsdRectangle(
                    background_offset[0],
                    background_offset[1],
                    background_offset[0] + background.shape[0],
                    background_offset[1] + background.shape[1],
                ),
                channels=[
                    PsdChannel(
                        channelid=PsdChannelId.CHANNEL0,
                        compression=PsdCompressionType.ZIP_PREDICTED,
                        data=background[..., 0],
                    ),
                    PsdChannel(
                        channelid=PsdChannelId.CHANNEL1,
                        compression=PsdCompressionType.ZIP_PREDICTED,
                        data=background[..., 1],
                    ),
                    PsdChannel(
                        channelid=PsdChannelId.CHANNEL2,
                        compression=PsdCompressionType.ZIP_PREDICTED,
                        data=background[..., 2],
                    ),
                ],
                mask=PsdLayerMask(),
                opacity=255,
                blendmode=PsdBlendMode.NORMAL,
                blending_ranges=(),
                clipping=PsdClippingType.BASE,
                flags=PsdLayerFlag.PHOTOSHOP5
                | PsdLayerFlag.TRANSPARENCY_PROTECTED,
                info=[
                    PsdString(PsdKey.UNICODE_LAYER_NAME, 'Background'),
                ],
            ),
            PsdLayer(
                name='Reflection',
                rectangle=PsdRectangle(
                    reflection_offset[0],
                    reflection_offset[1],
                    reflection_offset[0] + reflection.shape[0],
                    reflection_offset[1] + reflection.shape[1],
                ),
                channels=[
                    PsdChannel(
                        channelid=PsdChannelId.TRANSPARENCY_MASK,
                        compression=PsdCompressionType.ZIP_PREDICTED,
                        data=reflection[..., 3],
                    ),
                    PsdChannel(
                        channelid=PsdChannelId.CHANNEL0,
                        compression=PsdCompressionType.ZIP_PREDICTED,
                        data=reflection[..., 0],
                    ),
                    PsdChannel(
                        channelid=PsdChannelId.CHANNEL1,
                        compression=PsdCompressionType.ZIP_PREDICTED,
                        data=reflection[..., 1],
                    ),
                    PsdChannel(
                        channelid=PsdChannelId.CHANNEL2,
                        compression=PsdCompressionType.ZIP_PREDICTED,
                        data=reflection[..., 2],
                    ),
                ],
                mask=PsdLayerMask(),
                opacity=255,
                blendmode=PsdBlendMode.NORMAL,
                blending_ranges=(),
                clipping=PsdClippingType.BASE,
                flags=PsdLayerFlag.PHOTOSHOP5,
                info=[
                    PsdString(PsdKey.UNICODE_LAYER_NAME, 'Reflection'),
                ],
            ),
            PsdLayer(
                name='Shadow',
                rectangle=PsdRectangle(
                    shadow_offset[0],
                    shadow_offset[1],
                    shadow_offset[0] + shadow.shape[0],
                    shadow_offset[1] + shadow.shape[1],
                ),
                channels=[
                    PsdChannel(
                        channelid=PsdChannelId.TRANSPARENCY_MASK,
                        compression=PsdCompressionType.ZIP_PREDICTED,
                        data=shadow[..., 3],
                    ),
                    PsdChannel(
                        channelid=PsdChannelId.CHANNEL0,
                        compression=PsdCompressionType.ZIP_PREDICTED,
                        data=shadow[..., 0],
                    ),
                    PsdChannel(
                        channelid=PsdChannelId.CHANNEL1,
                        compression=PsdCompressionType.ZIP_PREDICTED,
                        data=shadow[..., 1],
                    ),
                    PsdChannel(
                        channelid=PsdChannelId.CHANNEL2,
                        compression=PsdCompressionType.ZIP_PREDICTED,
                        data=shadow[..., 2],
                    ),
                ],
                mask=PsdLayerMask(),
                opacity=255,
                blendmode=PsdBlendMode.NORMAL,
                blending_ranges=(),
                clipping=PsdClippingType.BASE,
                flags=PsdLayerFlag.PHOTOSHOP5,
                info=[
                    PsdString(PsdKey.UNICODE_LAYER_NAME, 'Shadow'),
                ],
            ),
            PsdLayer(
                name='Product',
                rectangle=PsdRectangle(
                    product_offset[0],
                    product_offset[1],
                    product_offset[0] + product.shape[0],
                    product_offset[1] + product.shape[1],
                ),
                channels=[
                    PsdChannel(
                        channelid=PsdChannelId.TRANSPARENCY_MASK,
                        compression=PsdCompressionType.ZIP_PREDICTED,
                        data=product[..., 3],
                    ),
                    PsdChannel(
                        channelid=PsdChannelId.CHANNEL0,
                        compression=PsdCompressionType.ZIP_PREDICTED,
                        data=product[..., 0],
                    ),
                    PsdChannel(
                        channelid=PsdChannelId.CHANNEL1,
                        compression=PsdCompressionType.ZIP_PREDICTED,
                        data=product[..., 1],
                    ),
                    PsdChannel(
                        channelid=PsdChannelId.CHANNEL2,
                        compression=PsdCompressionType.ZIP_PREDICTED,
                        data=product[..., 2],
                    ),
                ],
                mask=PsdLayerMask(),
                opacity=255,
                blendmode=PsdBlendMode.NORMAL,
                blending_ranges=(),
                clipping=PsdClippingType.BASE,
                flags=PsdLayerFlag.PHOTOSHOP5,
                info=[
                    PsdString(PsdKey.UNICODE_LAYER_NAME, 'Product'),
                ],
            ),
        ],
    ),
    usermask=PsdUserMask(
        colorspace=PsdColorSpaceType.RGB,
        components=(65535, 0, 0, 0),
        opacity=50,
    ),
    info=[
        PsdEmpty(PsdKey.PATTERNS),
        PsdFilterMask(
            colorspace=PsdColorSpaceType.RGB,
            components=(65535, 0, 0, 0),
            opacity=50,
        ),
    ],
)

# create a composite of the layers
composite = overlay(
    (background, background_offset),
    (reflection, reflection_offset),
    (shadow, shadow_offset),
    (product, product_offset),
    shape=shape,
)

# write a layered TIFF file
tifffile.imwrite(
    'layered.tif',
    # write composite as main TIFF image, accessible to regular TIFF readers
    composite,
    photometric='rgb',
    compression='adobe_deflate',
    # 72 dpi resolution
    resolution=((720000, 10000), (720000, 10000)),
    resolutionunit='inch',
    # do not write tifffile specific metadata
    metadata=None,
    # write layers and sRGB profile as extra tags
    extratags=[
        # ImageSourceData tag
        image_source_data.tifftag(),
        # InterColorProfile tag
        (34675, 7, None, imagecodecs.cms_profile('srgb'), True),
    ],
)

# read the ImageSourceData structure from the TIFF file
isd = TiffImageSourceData.fromtiff('layered.tif')
print(isd)
print(f'psdtags {__version__}')

# plot the layer and composite images in the TIFF file
for layer in isd.layers:
    tifffile.imshow(layer.asarray(), title=layer.name)
tifffile.imshow(tifffile.imread('layered.tif'), title='Composite', show=True)
