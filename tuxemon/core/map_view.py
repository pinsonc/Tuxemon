"""

Anything that is rendered to the screen is handled here.
Any visual representation of a game object should be handled here.

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import itertools
import os

import pygame
import pyscroll
import pytmx
from pytmx.util_pygame import load_pygame

from tuxemon.core import prepare, pyganim
from tuxemon.core.graphics import scaled_image_loader, load_and_scale
from tuxemon.core.map import facing
from tuxemon.core.prepare import CONFIG
from tuxemon.core.tools import nearest

# reference direction and movement states to animation names
# this dictionary is kinda wip, idk
animation_mapping = {
    True: {
        'up': 'back_walk',
        'down': 'front_walk',
        'left': 'left_walk',
        'right': 'right_walk'},
    False: {
        'up': 'back',
        'down': 'front',
        'left': 'left',
        'right': 'right'}
}


class MapSprite(object):
    """ WIP.  View of an NPC on the map

    This is largely the code from the NPC class

    """

    def __init__(self, sprite_name):
        self.sprite_name = sprite_name
        self.standing = dict()
        self.sprite = dict()
        self.width = 0
        self.height = 0
        self.moveConductor = pyganim.PygConductor()

    def load_sprites(self):
        """ Load sprite graphics

        :return:
        """
        # Get all of the standing animation images
        self.standing = {}
        for standing_type in facing:
            filename = "{}_{}.png".format(self.sprite_name, standing_type)
            path = os.path.join("sprites", filename)
            self.standing[standing_type] = load_and_scale(path)

        # this is the size used for collision testing
        self.width, self.height = self.standing["front"].get_size()

        # avoid cutoff frames when steps don't line up with tile movement
        frames = 3
        frame_duration = (1000 / CONFIG.player_walkrate) / frames / 1000 * 2

        # Load all of the player's sprite animations
        anim_types = ['front_walk', 'back_walk', 'left_walk', 'right_walk']
        for anim_type in anim_types:
            images = [
                'sprites/%s_%s.%s.png' % (
                    self.sprite_name,
                    anim_type,
                    str(num).rjust(3, str('0'))
                )
                for num in range(4)
            ]

            frames = []
            for image in images:
                surface = load_and_scale(image)
                frames.append((surface, frame_duration))

            self.sprite[anim_type] = pyganim.PygAnimation(frames, loop=True)

        # Have the animation objects managed by a conductor.
        # With the conductor, we can call play() and stop() on all the animation objects
        # at the same time, so that way they'll always be in sync with each other.
        self.moveConductor.add(self.sprite)

    def get_current_npc_surface(self, npc, layer):
        """ Get the surfaces and layers for the sprite

        :param int layer: The layer to draw the sprite on.
        :return:
        """

        def get_frame(d, ani):
            frame = d[ani]
            try:
                surface = frame.getCurrentFrame()
                frame.rate = npc.moverate / CONFIG.player_walkrate
                return surface
            except AttributeError:
                return frame

        frame_dict = self.sprite if npc.moving else self.standing
        state = animation_mapping[npc.moving][npc.facing]
        return [(get_frame(frame_dict, state), npc.tile_pos, layer)]


class MapView(object):
    """

    Render a map, npcs, etc

    use `follow()` to keep the camera on a game object/npc

    """

    def __init__(self, rect, world):
        """ Constructor

        :param Rect rect: Area of screen to draw the map
        :param World world: World to draw
        """
        self.rect = rect
        self.world = world
        self.map_animations = dict()
        self.tracked_npc = None
        self._sprites = dict()  # npc => sprite/avatar mapping
        self.renderer = None

    def initialize_renderer(self, filename):
        """ Initialize the renderer for the map and sprites
        """
        # TODO: load tiles from the internal game format (pending
        if prepare.CONFIG.scaling:
            map_data = pytmx.TiledMap(filename,
                                      image_loader=scaled_image_loader,
                                      pixelalpha=True)
            map_data.tilewidth, map_data.tileheight = prepare.TILE_SIZE
        else:
            map_data = load_pygame(filename, pixelalpha=True)

        self.map_animations = dict()
        visual_data = pyscroll.data.TiledMapData(map_data)
        clamp = True
        return pyscroll.BufferedRenderer(visual_data, prepare.SCREEN_SIZE, clamp_camera=clamp, tall_sprites=2)

    def follow(self, entity):
        self.tracked_npc = entity

    def draw(self, rect, surface):
        """ Draw the view

        :param Rect rect: Area to draw to
        :param Surface surface: Target surface
        """
        if self.tracked_npc is not None:
            # Renderers are specific to a single map.  If a map is not set,
            # there will be no renderer and there is no need to draw anything.
            if self.renderer is None:
                map_name = self.tracked_npc.map_name
                filename = prepare.fetch("maps", map_name)
                self.renderer = self.initialize_renderer(filename)

        # interlace player sprites with tiles surfaces.
        world_surfaces = list()

        # get player coords to center map
        cx, cy = nearest(self.project(self.tracked_npc.tile_pos))

        print(self.tracked_npc.tile_pos)

        # offset center point for player sprite
        cx += prepare.TILE_SIZE[0] // 2
        cy += prepare.TILE_SIZE[1] // 2

        # center the map on center of player sprite
        # must center map before getting sprite coordinates
        self.renderer.center((cx, cy))

        # get npc surfaces/sprites
        # TODO: filter by map
        for npc in self.world.get_all_entities_on_map(None):
            sprite = MapSprite(npc.sprite_name)
            sprite.load_sprites()
            world_surfaces.extend(sprite.get_current_npc_surface(npc, 5))

        # get map_animations
        for anim_data in self.map_animations.values():
            anim = anim_data['animation']
            if not anim.isFinished() and anim.visibility:
                frame = (anim.getCurrentFrame(), anim_data["position"], anim_data['layer'])
                world_surfaces.append(frame)

        # position the surfaces correctly
        # pyscroll expects surfaces in screen coords, so they are
        # converted from world to screen coords here
        screen_surfaces = list()
        for frame in world_surfaces:
            s, c, l = frame

            # project to pixel/screen coords
            c = self.get_pos_from_tilepos(c)

            # TODO: better handling of tall sprites
            # handle tall sprites
            h = s.get_height()
            if h > prepare.TILE_SIZE[1]:
                # offset for center and image height
                c = nearest((c[0], c[1] - h // 2))

            screen_surfaces.append((s, c, l))

        # draw the map and sprites
        self.rect = self.renderer.draw(surface, surface.get_rect(), screen_surfaces)

        # If we want to draw the collision map for debug purposes
        if prepare.CONFIG.collision_map:
            self.debug_drawing(surface)

    def get_pos_from_tilepos(self, tile_position):
        """ Returns the map pixel coordinate based on tile position.

        USE this to draw to the screen

        :param List tile_position: An [x, y] tile position.

        :rtype: Tuple[int, int]
        """
        cx, cy = self.renderer.get_center_offset()
        px, py = self.project(tile_position)
        x = px + cx
        y = py + cy
        return x, y

    def project(self, position):
        self.tile_size = prepare.TILE_SIZE
        return position[0] * self.tile_size[0], position[1] * self.tile_size[1]

    def _collision_box_to_pgrect(self, box):
        """Returns a pygame.Rect (in screen-coords) version of a collision box (in world-coords).
        """

        # For readability
        x, y = self.get_pos_from_tilepos(box)
        tw, th = self.tile_size

        return pygame.Rect(x, y, tw, th)

    def _npc_to_pgrect(self, npc):
        """Returns a pygame.Rect (in screen-coords) version of an NPC's bounding box.
        """
        pos = self.get_pos_from_tilepos(npc.tile_pos)
        return pygame.Rect(pos, self.tile_size)

    def debug_drawing(self, surface):
        from pygame.gfxdraw import box

        surface.lock()

        # draw events
        for event in self.game.events:
            topleft = self.get_pos_from_tilepos((event.x, event.y))
            size = self.project((event.w, event.h))
            rect = topleft, size
            box(surface, rect, (0, 255, 0, 128))

        # We need to iterate over all collidable objects.  So, let's start
        # with the walls/collision boxes.
        box_iter = itertools.imap(self._collision_box_to_pgrect, self.collision_map)

        # Next, deal with solid NPCs.
        npc_iter = itertools.imap(self._npc_to_pgrect, self.npcs.values())

        # draw noc and wall collision tiles
        red = (255, 0, 0, 128)
        for item in itertools.chain(box_iter, npc_iter):
            box(surface, item, red)

        # draw center lines to verify camera is correct
        w, h = surface.get_size()
        cx, cy = w // 2, h // 2
        pygame.draw.line(surface, (255, 50, 50), (cx, 0), (cx, h))
        pygame.draw.line(surface, (255, 50, 50), (0, cy), (w, cy))

        surface.unlock()
