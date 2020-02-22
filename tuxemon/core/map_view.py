class MapView(object):

    def initialize_renderer(self):
        """ Initialize the renderer for the map and sprites

        :rtype: pyscroll.BufferedRenderer
        """
        # TODO: Use self.edges == "stitched" here when implementing seamless maps
        visual_data = pyscroll.data.TiledMapData(self.data)
        clamp = (self.edges == "clamped")
        return pyscroll.BufferedRenderer(visual_data, prepare.SCREEN_SIZE, clamp_camera=clamp, tall_sprites=2)

    def load(self):
        # Scale the loaded tiles if enabled
        if prepare.CONFIG.scaling:
            self.data = pytmx.TiledMap(filename,
                                       image_loader=scaled_image_loader,
                                       pixelalpha=True)
            self.data.tilewidth, self.data.tileheight = prepare.TILE_SIZE
        else:
            self.data = load_pygame(filename, pixelalpha=True)

    def draw(self, surface):
        # TODO: move all drawing into a "WorldView" widget
        # interlace player sprites with tiles surfaces.
        # eventually, maybe use pygame sprites or something similar
        world_surfaces = list()

        # get player coords to center map
        cx, cy = nearest(self.project(self.player1.tile_pos))

        # offset center point for player sprite
        cx += prepare.TILE_SIZE[0] // 2
        cy += prepare.TILE_SIZE[1] // 2

        # center the map on center of player sprite
        # must center map before getting sprite coordinates
        self.current_map.renderer.center((cx, cy))

        # get npc surfaces/sprites
        for npc in self.npcs:
            world_surfaces.extend(self.npcs[npc].get_sprites())

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
        self.rect = self.current_map.renderer.draw(surface, surface.get_rect(), screen_surfaces)

        # If we want to draw the collision map for debug purposes
        if prepare.CONFIG.collision_map:
            self.debug_drawing(surface)

    def get_sprites(self):
        """ Get the surfaces and layers for the sprite

        Used to render the player

        :return:
        """

        def get_frame(d, ani):
            frame = d[ani]
            try:
                surface = frame.getCurrentFrame()
                frame.rate = self.moverate / CONFIG.player_walkrate
                return surface
            except AttributeError:
                return frame

        # TODO: move out to the world renderer
        frame_dict = self.sprite if self.moving else self.standing
        state = animation_mapping[self.moving][self.facing]
        return [(get_frame(frame_dict, state), self.tile_pos, 2)]

    def load_sprites(self):
        """ Load sprite graphics

        :return:
        """
        # TODO: refactor animations into renderer
        # Get all of the player's standing animation images.
        self.standing = {}
        for standing_type in facing:
            filename = "{}_{}.png".format(self.sprite_name, standing_type)
            path = os.path.join("sprites", filename)
            self.standing[standing_type] = load_and_scale(path)

        self.playerWidth, self.playerHeight = self.standing["front"].get_size()  # The player's sprite size in pixels

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

    ####################################################
    #                Debug Drawing                     #
    ####################################################
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
        box_iter = imap(self._collision_box_to_pgrect, self.collision_map)

        # Next, deal with solid NPCs.
        npc_iter = imap(self._npc_to_pgrect, self.npcs.values())

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
