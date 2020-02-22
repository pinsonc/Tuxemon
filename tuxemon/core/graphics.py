"""

General "tools" code for pygame graphics operations that don't
have a home in any specific place

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import operator
import re

import pygame
from tuxemon.compat import Rect
from tuxemon.core import prepare
from tuxemon.core.tools import transform_resource_filename, scale_sequence, scale_rect, logger


def strip_from_sheet(sheet, start, size, columns, rows=1):
    """Strips individual frames from a sprite sheet given a start location,
    sprite size, and number of columns and rows."""
    frames = []
    for j in range(rows):
        for i in range(columns):
            location = (start[0] + size[0] * i, start[1] + size[1] * j)
            frames.append(sheet.subsurface(Rect(location, size)))
    return frames


def strip_coords_from_sheet(sheet, coords, size):
    """Strip specific coordinates from a sprite sheet."""
    frames = []
    for coord in coords:
        location = (coord[0] * size[0], coord[1] * size[1])
        frames.append(sheet.subsurface(Rect(location, size)))
    return frames


def cursor_from_image(image):
    """Take a valid image and create a mouse cursor."""
    colors = {(0, 0, 0, 255): "X",
              (255, 255, 255, 255): "."}
    rect = image.get_rect()
    icon_string = []
    for j in range(rect.height):
        this_row = []
        for i in range(rect.width):
            pixel = tuple(image.get_at((i, j)))
            this_row.append(colors.get(pixel, " "))
        icon_string.append("".join(this_row))
    return icon_string


def load_and_scale(filename):
    """ Load an image and scale it according to game settings

    * Filename will be transformed to be loaded from game resource folder
    * Will be converted if needed.
    * Scale factor will match game setting.

    :param filename:
    :rtype: pygame.Surface
    """
    return scale_surface(load_image(filename), prepare.SCALE)


def smart_convert(image):
    """ Given an unconverted file, determine if it has transparent pixels
    and return a converted image, with per-pixel alpha if needed.

    :param image: pygame.Surface
    :rtype: pygame.Surface
    """
    # get number of opaque pixels in the image
    px = pygame.mask.from_surface(image, 127).count()

    # there are no transparent pixels in the image because
    # the number of pixels matches the number of opaque pixels
    if px == operator.mul(*image.get_size()):
        return image.convert()

    return image.convert_alpha()


def load_image(filename):
    """ Load image from the resources folder

    * Filename will be transformed to be loaded from game resource folder
    * Will be converted if needed.

    This is a "smart" loader, and will convert files in the best way,
    but is slightly slower than just loading.  Its important that
    this is not called too often (like once per draw!)

    :param filename: String
    :rtype: pygame.Surface
    """
    filename = transform_resource_filename(filename)
    return smart_convert(pygame.image.load(filename))


def load_sprite(filename, **rect_kwargs):
    """ Load an image from disk and return a pygame sprite

    Image name will be transformed and converted
    Rect attribute will be set

    Any keyword arguments will be passed to the get_rect method
    of the image for positioning the rect.

    :param filename: Filename to load
    :rtype: core.sprite.Sprite
    """
    import tuxemon.core.sprite
    sprite = tuxemon.core.sprite.Sprite()
    sprite.image = load_and_scale(filename)
    sprite.rect = sprite.image.get_rect(**rect_kwargs)
    return sprite


def scale_surface(surface, factor):
    """ Scale a surface.  Just a shortcut.

    :returns: Scaled surface
    :rtype: pygame.Surface
    """
    return pygame.transform.scale(surface, [int(i * factor) for i in surface.get_size()])


def load_frames_files(directory, name):
    """ Load animation that is a collection of frames

    For example, water00.png, water01.png, water03.png

    :type directory: str
    :type name: str

    :rtype: generator
    """
    scale = prepare.SCALE
    for animation_frame in os.listdir(directory):
        pattern = name + "\.[0-9].*"
        if re.findall(pattern, animation_frame):
            frame = pygame.image.load(directory + "/" + animation_frame).convert_alpha()
            frame = pygame.transform.scale(frame, (frame.get_width() * scale, frame.get_height() * scale))
            yield frame


def create_animation(frames, duration, loop):
    """ Create animation from frames, a list of surfaces

    :param frames:
    :param duration:
    :param loop:
    :return:
    """
    from tuxemon.core import pyganim
    data = [(f, duration) for f in frames]
    animation = pyganim.PygAnimation(data, loop=loop)
    conductor = pyganim.PygConductor({'animation': animation})
    return animation, conductor


def load_animation_from_frames(directory, name, duration, loop=False):
    """ Load animation from a collection of frame files

    :param directory:
    :param name:
    :param duration:
    :param loop:

    :return:
    """
    frames = load_frames_files(directory, name)
    return create_animation(frames, duration, loop)


def scale_tile(surface, tile_size):
    """ Scales a map tile based on resolution.

    :type surface: pygame.Surface
    :type tile_size: int
    :rtype: pygame.Surface
    """
    if type(surface) is pygame.Surface:
        surface = pygame.transform.scale(surface, tile_size)
    else:
        surface.scale(tile_size)

    return surface


def scale_sprite(sprite, ratio):
    """ Scale a sprite's image in place

    :type sprite: pygame.Sprite
    :param ratio: amount to scale by
    :rtype: core.sprite.Sprite
    """
    center = sprite.rect.center
    sprite.rect.width *= ratio
    sprite.rect.height *= ratio
    sprite.rect.center = center
    sprite._original_image = pygame.transform.scale(sprite._original_image, sprite.rect.size)
    sprite._needs_update = True


def convert_alpha_to_colorkey(surface, colorkey=(255, 0, 255)):
    """ Convert image with perpixel alpha to normal surface with colorkey

    This is a crude hack that only works well with images that do not
    have alpha blended antialiased edges.  Using this function on such
    images will result in discoloration of edges.

    :param surface: Some image to change
    :type surface: pygame.Surface
    :param colorkey: Colorkey to use for transparency
    :type colorkey: Sequence or pygame.Color

    :returns: Modified surface
    :rtype: pygame.Surface
    """
    image = pygame.Surface(surface.get_size())
    image.fill(colorkey)
    image.set_colorkey(colorkey)
    image.blit(surface, (0, 0))
    return image


def scaled_image_loader(filename, colorkey, **kwargs):
    """ pytmx image loader for pygame

    Modified to load images at a scaled size

    :param filename:
    :param colorkey:
    :param kwargs:
    :return:
    """
    from pytmx.util_pygame import smart_convert, handle_transformation

    if colorkey:
        colorkey = pygame.Color('#{0}'.format(colorkey))

    pixelalpha = kwargs.get('pixelalpha', True)

    # load the tileset image
    image = pygame.image.load(filename)

    # scale the tileset image to match game scale
    scaled_size = scale_sequence(image.get_size())
    image = pygame.transform.scale(image, scaled_size)

    def load_image(rect=None, flags=None):
        if rect:
            # scale the rect to match the scaled image
            rect = scale_rect(rect)
            try:
                tile = image.subsurface(rect)
            except ValueError:
                logger.error('Tile bounds outside bounds of tileset image')
                raise
        else:
            tile = image.copy()

        if flags:
            tile = handle_transformation(tile, flags)

        tile = smart_convert(tile, colorkey, pixelalpha)
        return tile

    return load_image